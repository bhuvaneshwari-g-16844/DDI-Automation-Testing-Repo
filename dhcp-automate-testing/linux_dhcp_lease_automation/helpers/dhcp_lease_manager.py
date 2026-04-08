"""
dhcp_lease_manager.py – Manage DHCP leases via SSH on the DHCP server.

Creates, updates, deletes, and reads leases by directly manipulating
the ISC DHCP lease files:
  v4: /usr/local/dhcpd/var/lib/dhcpd.leases
  v6: /usr/local/dhcpd/var/lib/dhcpd6.leases

Uses paramiko for SSH connections.
"""

import re
import time
from datetime import datetime

import paramiko


class DHCPLeaseManager(object):
    """Manage DHCP lease files on a remote server via SSH."""

    def __init__(self, host, username, password=None, key_file=None, port=22,
                 v4_lease_file="/usr/local/dhcpd/var/lib/dhcpd.leases",
                 v6_lease_file="/usr/local/dhcpd/var/lib/dhcpd6.leases",
                 restart_cmd="systemctl restart dhcpd",
                 restart_v6_cmd="systemctl restart dhcpd6"):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_file = key_file
        self.v4_lease_file = v4_lease_file
        self.v6_lease_file = v6_lease_file
        self.restart_cmd = restart_cmd
        self.restart_v6_cmd = restart_v6_cmd
        self._client = None

    def _sudo_prefix(self):
        """Return a sudo command prefix that provides the password via stdin."""
        if self.password:
            return "echo '{}' | sudo -S".format(self.password)
        return "sudo"

    # ── SSH Connection ───────────────────────────────────────────────── #
    def connect(self):
        """Establish SSH connection to DHCP server."""
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_kwargs = {
            "hostname": self.host,
            "port": self.port,
            "username": self.username,
            "timeout": 15,
        }
        if self.key_file:
            connect_kwargs["key_filename"] = self.key_file
        elif self.password:
            connect_kwargs["password"] = self.password
        self._client.connect(**connect_kwargs)
        return self

    def close(self):
        """Close SSH connection."""
        if self._client:
            self._client.close()
            self._client = None

    def _exec(self, cmd):
        """Execute a command via SSH and return (stdout, stderr, exit_code)."""
        if not self._client:
            self.connect()
        stdin, stdout, stderr = self._client.exec_command(cmd, timeout=30)
        exit_code = stdout.channel.recv_exit_status()
        return stdout.read().decode("utf-8"), stderr.read().decode("utf-8"), exit_code

    def _read_file(self, filepath):
        """Read a remote file via SSH."""
        out, err, code = self._exec("cat {}".format(filepath))
        if code != 0:
            raise IOError("Failed to read {}: {}".format(filepath, err))
        return out

    def _write_file(self, filepath, content):
        """Write content to a remote file via SSH (uses sudo)."""
        # Write to a temp file first, then sudo mv to target
        tmp = "/tmp/_dhcp_lease_tmp_{}".format(id(content) % 100000)
        sftp = self._client.open_sftp()
        try:
            with sftp.file(tmp, "w") as f:
                f.write(content)
        finally:
            sftp.close()
        sudo_prefix = self._sudo_prefix()
        self._exec("{} bash -c 'cp {} {}' && rm {}".format(sudo_prefix, tmp, filepath, tmp))

    def _append_file(self, filepath, content):
        """Append content to a remote file via SSH (uses sudo)."""
        tmp = "/tmp/_dhcp_lease_append_{}".format(id(content) % 100000)
        sftp = self._client.open_sftp()
        try:
            with sftp.file(tmp, "w") as f:
                f.write(content)
        finally:
            sftp.close()
        sudo_prefix = self._sudo_prefix()
        self._exec("{} bash -c 'cat {} >> {}' && rm {}".format(
            sudo_prefix, tmp, filepath, tmp))

    # ── DHCPv4 Lease Operations ──────────────────────────────────────── #
    @staticmethod
    def build_v4_lease(ip, mac, starts=None, ends=None, hostname=None,
                       binding_state="active", tstp=None, cltt=None):
        """
        Build a DHCPv4 lease block string.

        Example output:
            lease 2.2.228.102 {
              starts 1 2026/02/23 06:33:10;
              ends 1 2027/01/04 00:00:00;
              tstp 1 2027/01/04 00:00:00;
              cltt 1 2026/02/23 06:33:10;
              binding state active;
              hardware ethernet 00:00:23:df:5e:f1;
            }
        """
        now_str = datetime.utcnow().strftime("%Y/%m/%d %H:%M:%S")
        if not ip:
            raise ValueError("ip is required")
        if not mac:
            raise ValueError("mac is required")
        if not starts:
            starts = now_str
        if not ends:
            ends = "2027/04/07 00:00:00"
        if not tstp:
            tstp = ends
        if not cltt:
            cltt = starts

        # weekday number: 0=Sun ... 6=Sat
        lines = []
        lines.append("lease {} {{".format(ip))
        lines.append("  starts 1 {};".format(starts))
        lines.append("  ends 1 {};".format(ends))
        lines.append("  tstp 1 {};".format(tstp))
        lines.append("  cltt 1 {};".format(cltt))
        lines.append("  binding state {};".format(binding_state))
        if hostname:
            lines.append('  client-hostname "{}";'.format(hostname))
        lines.append("  hardware ethernet {};".format(mac))
        lines.append("}")
        return "\n".join(lines)

    def create_v4_lease(self, ip, mac, starts=None, ends=None,
                        hostname=None, binding_state="active"):
        """Create a DHCPv4 lease by appending to the lease file."""
        lease_block = self.build_v4_lease(
            ip=ip, mac=mac, starts=starts, ends=ends,
            hostname=hostname, binding_state=binding_state
        )
        self._append_file(self.v4_lease_file, "\n" + lease_block + "\n")
        return lease_block

    def get_v4_lease(self, ip):
        """Read and return a specific v4 lease block by IP."""
        content = self._read_file(self.v4_lease_file)
        pattern = r"lease\s+{}\s*\{{[^}}]+\}}".format(re.escape(ip))
        matches = re.findall(pattern, content, re.DOTALL)
        return matches[-1] if matches else None

    def get_all_v4_leases(self):
        """Return all v4 lease blocks as a list of strings."""
        content = self._read_file(self.v4_lease_file)
        return re.findall(r"lease\s+[\d.]+\s*\{[^}]+\}", content, re.DOTALL)

    def v4_lease_exists(self, ip):
        """Check if a v4 lease with the given IP exists."""
        return self.get_v4_lease(ip) is not None

    def delete_v4_lease(self, ip):
        """Delete a v4 lease by removing it from the lease file."""
        content = self._read_file(self.v4_lease_file)
        pattern = r"\n?lease\s+{}\s*\{{[^}}]+\}}\n?".format(re.escape(ip))
        new_content = re.sub(pattern, "\n", content, flags=re.DOTALL)
        self._write_file(self.v4_lease_file, new_content)
        return content != new_content  # True if something was removed

    def update_v4_lease(self, ip, mac=None, starts=None, ends=None,
                        hostname=None, binding_state=None):
        """Update a v4 lease: delete old, write new."""
        existing = self.get_v4_lease(ip)
        if not existing:
            raise ValueError("Lease for {} not found".format(ip))

        # Parse existing values as defaults
        old_mac = mac
        if not mac:
            m = re.search(r"hardware ethernet ([^;]+);", existing)
            old_mac = m.group(1) if m else "00:00:00:00:00:00"
        old_state = binding_state
        if not binding_state:
            m = re.search(r"binding state (\w+);", existing)
            old_state = m.group(1) if m else "active"

        self.delete_v4_lease(ip)
        return self.create_v4_lease(
            ip=ip, mac=old_mac, starts=starts, ends=ends,
            hostname=hostname, binding_state=old_state
        )

    def count_v4_leases(self):
        """Count total v4 leases in the file."""
        return len(self.get_all_v4_leases())

    # ── DHCPv6 Lease Operations ──────────────────────────────────────── #
    @staticmethod
    def build_v6_lease(ip, duid, iaid=None, preferred_life=3600,
                       max_life=7200, ends=None, binding_state="active",
                       cltt=None):
        """
        Build a DHCPv6 lease block string.

        Example output:
            ia-na "\\001\\000..." {
              cltt 2 2025/12/09 07:33:25;
              iaaddr 1000::9465:cf2d:ef86:df42 {
                binding state active;
                preferred-life 3600;
                max-life 7200;
                ends 1 2027/03/09 13:06:16;
              }
            }
        """
        now_str = datetime.utcnow().strftime("%Y/%m/%d %H:%M:%S")
        if not ip:
            raise ValueError("ip is required")
        if not duid:
            raise ValueError("duid is required")
        if not ends:
            ends = "2027/04/07 00:00:00"
        if not cltt:
            cltt = now_str
        if not iaid:
            iaid = "\\001\\000\\000\\000"

        duid_str = "{}{}".format(iaid, duid)

        lines = []
        lines.append('ia-na "{}" {{'.format(duid_str))
        lines.append("  cltt 2 {};".format(cltt))
        lines.append("  iaaddr {} {{".format(ip))
        lines.append("    binding state {};".format(binding_state))
        lines.append("    preferred-life {};".format(preferred_life))
        lines.append("    max-life {};".format(max_life))
        lines.append("    ends 1 {};".format(ends))
        lines.append("  }")
        lines.append("}")
        return "\n".join(lines)

    def create_v6_lease(self, ip, duid, iaid=None, preferred_life=3600,
                        max_life=7200, ends=None, binding_state="active"):
        """Create a DHCPv6 lease by appending to the v6 lease file."""
        lease_block = self.build_v6_lease(
            ip=ip, duid=duid, iaid=iaid, preferred_life=preferred_life,
            max_life=max_life, ends=ends, binding_state=binding_state
        )
        self._append_file(self.v6_lease_file, "\n" + lease_block + "\n")
        return lease_block

    def get_v6_lease(self, ip):
        """Read and return a specific v6 lease block by IPv6 address."""
        content = self._read_file(self.v6_lease_file)
        pattern = r"ia-na\s+\"[^\"]*\"\s*\{{[^}}]*iaaddr\s+{}\s*\{{[^}}]+\}}[^}}]*\}}".format(
            re.escape(ip)
        )
        matches = re.findall(pattern, content, re.DOTALL)
        return matches[-1] if matches else None

    def get_all_v6_leases(self):
        """Return all v6 lease blocks."""
        content = self._read_file(self.v6_lease_file)
        return re.findall(
            r"ia-na\s+\"[^\"]*\"\s*\{[^}]*iaaddr\s+[^\{]+\{[^}]+\}[^}]*\}",
            content, re.DOTALL
        )

    def v6_lease_exists(self, ip):
        """Check if a v6 lease with the given IPv6 exists."""
        return self.get_v6_lease(ip) is not None

    def delete_v6_lease(self, ip):
        """Delete a v6 lease by removing it from the lease file."""
        content = self._read_file(self.v6_lease_file)
        pattern = r"\n?ia-na\s+\"[^\"]*\"\s*\{{[^}}]*iaaddr\s+{}\s*\{{[^}}]+\}}[^}}]*\}}\n?".format(
            re.escape(ip)
        )
        new_content = re.sub(pattern, "\n", content, flags=re.DOTALL)
        self._write_file(self.v6_lease_file, new_content)
        return content != new_content

    def update_v6_lease(self, ip, duid=None, iaid=None, preferred_life=None,
                        max_life=None, ends=None, binding_state=None):
        """Update a v6 lease: delete old, write new."""
        existing = self.get_v6_lease(ip)
        if not existing:
            raise ValueError("v6 Lease for {} not found".format(ip))

        if not duid:
            m = re.search(r'ia-na "([^"]*)"', existing)
            duid = m.group(1) if m else ""
        if not binding_state:
            m = re.search(r"binding state (\w+);", existing)
            binding_state = m.group(1) if m else "active"
        if not preferred_life:
            m = re.search(r"preferred-life (\d+);", existing)
            preferred_life = int(m.group(1)) if m else 3600
        if not max_life:
            m = re.search(r"max-life (\d+);", existing)
            max_life = int(m.group(1)) if m else 7200

        self.delete_v6_lease(ip)
        return self.create_v6_lease(
            ip=ip, duid=duid, iaid=iaid, preferred_life=preferred_life,
            max_life=max_life, ends=ends, binding_state=binding_state
        )

    def count_v6_leases(self):
        """Count total v6 leases."""
        return len(self.get_all_v6_leases())

    # ── Service Management ───────────────────────────────────────────── #
    def restart_dhcpd(self):
        """Restart DHCPv4 service."""
        sudo_prefix = self._sudo_prefix()
        out, err, code = self._exec("{} {}".format(sudo_prefix, self.restart_cmd))
        time.sleep(2)  # Allow service to start
        return code == 0

    def restart_dhcpd6(self):
        """Restart DHCPv6 service."""
        sudo_prefix = self._sudo_prefix()
        out, err, code = self._exec("{} {}".format(sudo_prefix, self.restart_v6_cmd))
        time.sleep(2)
        return code == 0

    def dhcpd_status(self):
        """Check DHCPv4 service status."""
        out, err, code = self._exec("systemctl is-active dhcpd")
        return out.strip()

    def dhcpd6_status(self):
        """Check DHCPv6 service status."""
        out, err, code = self._exec("systemctl is-active dhcpd6")
        return out.strip()

    # ── Backup / Restore ─────────────────────────────────────────────── #
    def backup_v4_leases(self):
        """Backup the v4 lease file. Returns the content."""
        return self._read_file(self.v4_lease_file)

    def restore_v4_leases(self, content):
        """Restore v4 lease file from backup content."""
        self._write_file(self.v4_lease_file, content)

    def backup_v6_leases(self):
        """Backup the v6 lease file."""
        return self._read_file(self.v6_lease_file)

    def restore_v6_leases(self, content):
        """Restore v6 lease file from backup content."""
        self._write_file(self.v6_lease_file, content)

    # ── Lease History (read lease file for moved entries) ────────────── #
    def get_v4_lease_history(self, ip):
        """Get all lease entries for an IP (including historical/superseded)."""
        content = self._read_file(self.v4_lease_file)
        pattern = r"lease\s+{}\s*\{{[^}}]+\}}".format(re.escape(ip))
        return re.findall(pattern, content, re.DOTALL)

    def get_v6_lease_history(self, ip):
        """Get all v6 lease entries for an IPv6 address."""
        content = self._read_file(self.v6_lease_file)
        pattern = r"ia-na\s+\"[^\"]*\"\s*\{{[^}}]*iaaddr\s+{}\s*\{{[^}}]+\}}[^}}]*\}}".format(
            re.escape(ip)
        )
        return re.findall(pattern, content, re.DOTALL)

    # ── Parse lease fields ───────────────────────────────────────────── #
    @staticmethod
    def parse_v4_lease(lease_block):
        """Parse a v4 lease block into a dict."""
        info = {}
        m = re.search(r"lease\s+([\d.]+)", lease_block)
        if m:
            info["ip"] = m.group(1)
        m = re.search(r"starts\s+\d+\s+([^;]+);", lease_block)
        if m:
            info["starts"] = m.group(1)
        m = re.search(r"ends\s+\d+\s+([^;]+);", lease_block)
        if m:
            info["ends"] = m.group(1)
        m = re.search(r"binding state (\w+);", lease_block)
        if m:
            info["binding_state"] = m.group(1)
        m = re.search(r"hardware ethernet ([^;]+);", lease_block)
        if m:
            info["mac"] = m.group(1)
        m = re.search(r'client-hostname "([^"]+)";', lease_block)
        if m:
            info["hostname"] = m.group(1)
        m = re.search(r"cltt\s+\d+\s+([^;]+);", lease_block)
        if m:
            info["cltt"] = m.group(1)
        return info

    @staticmethod
    def parse_v6_lease(lease_block):
        """Parse a v6 lease block into a dict."""
        info = {}
        m = re.search(r'ia-na "([^"]*)"', lease_block)
        if m:
            info["duid"] = m.group(1)
        m = re.search(r"iaaddr\s+(\S+)\s*\{", lease_block)
        if m:
            info["ip"] = m.group(1)
        m = re.search(r"binding state (\w+);", lease_block)
        if m:
            info["binding_state"] = m.group(1)
        m = re.search(r"preferred-life (\d+);", lease_block)
        if m:
            info["preferred_life"] = int(m.group(1))
        m = re.search(r"max-life (\d+);", lease_block)
        if m:
            info["max_life"] = int(m.group(1))
        m = re.search(r"ends\s+\d+\s+([^;]+);", lease_block)
        if m:
            info["ends"] = m.group(1)
        m = re.search(r"cltt\s+\d+\s+([^;]+);", lease_block)
        if m:
            info["cltt"] = m.group(1)
        return info
