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
        # Set by conftest autouse fixture before each test so every
        # lease written to the file is stamped with the TC number.
        self._current_tc_tag = None

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

    @staticmethod
    def _normalize_content(content):
        """Collapse 3+ consecutive blank lines into 1 and strip edges."""
        # Collapse runs of blank lines (3+ newlines → 2 newlines = 1 blank line)
        content = re.sub(r"\n{3,}", "\n\n", content)
        return content.strip() + "\n"

    def _write_file(self, filepath, content):
        """Write content to a remote file via SSH (uses sudo).

        Uses ``cat tmp > dest`` instead of ``cp`` so the file inode is
        preserved and services that have the file open continue to see
        changes.
        """
        tmp = "/tmp/_dhcp_lease_tmp_{}".format(id(content) % 100000)
        sftp = self._client.open_sftp()
        try:
            with sftp.file(tmp, "w") as f:
                f.write(content)
        finally:
            sftp.close()
        sudo_prefix = self._sudo_prefix()
        self._exec(
            "{sudo} bash -c 'cat {tmp} > {dst} && chmod 666 {dst}' && rm -f {tmp}".format(
                sudo=sudo_prefix, tmp=tmp, dst=filepath))

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
                       binding_state="active", tstp=None, cltt=None,
                       tc_tag=None):
        """
        Build a DHCPv4 lease block string.

        When *tc_tag* is supplied (e.g. "TC001") a comment line is
        prepended so the lease is easily identifiable in the file:

            # [AUTOTEST] TC001 | 2026/04/08 14:30:00
            lease 3.3.228.102 {
              ...
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
        if tc_tag:
            lines.append("# [AUTOTEST] {} | {}".format(tc_tag, now_str))
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
                        hostname=None, binding_state="active", tc_tag=None):
        """Create a DHCPv4 lease by appending to the lease file.

        Pass *tc_tag* (e.g. ``"TC001"``) to stamp the lease with an
        ``# [AUTOTEST]`` comment so you can tell at a glance which
        test case wrote it.  Falls back to ``_current_tc_tag`` when
        not supplied (set automatically by conftest autouse fixture).
        """
        tag = tc_tag or self._current_tc_tag
        lease_block = self.build_v4_lease(
            ip=ip, mac=mac, starts=starts, ends=ends,
            hostname=hostname, binding_state=binding_state,
            tc_tag=tag,
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
        """Delete **all** v4 lease entries for *ip* from the lease file.

        Removes every ``lease <ip> { ... }`` block (there may be
        duplicates from repeated test runs) together with any preceding
        ``# [AUTOTEST]`` comment line, then normalizes blank lines so
        the file stays clean.
        """
        content = self._read_file(self.v4_lease_file)
        # Match optional AUTOTEST comment + lease block
        pattern = r"\n?(?:#\s*\[AUTOTEST\][^\n]*\n)?lease\s+{}\s*\{{[^}}]+\}}\n?".format(
            re.escape(ip))
        new_content = re.sub(pattern, "\n", content, flags=re.DOTALL)
        if new_content == content:
            return False
        new_content = self._normalize_content(new_content)
        self._write_file(self.v4_lease_file, new_content)
        return True

    def update_v4_lease(self, ip, mac=None, starts=None, ends=None,
                        hostname=None, binding_state=None, tc_tag=None):
        """Update a v4 lease: delete old, write new.

        Any field that is *None* is carried forward from the existing
        lease so callers only need to specify the fields they want to
        change.
        """
        tag = tc_tag or self._current_tc_tag
        existing = self.get_v4_lease(ip)
        if not existing:
            raise ValueError("Lease for {} not found".format(ip))

        # Parse existing values as defaults
        if not mac:
            m = re.search(r"hardware ethernet ([^;]+);", existing)
            mac = m.group(1) if m else "00:00:00:00:00:00"
        if not binding_state:
            m = re.search(r"binding state (\w+);", existing)
            binding_state = m.group(1) if m else "active"
        if hostname is None:
            m = re.search(r'client-hostname "([^"]*)";', existing)
            hostname = m.group(1) if m else None

        self.delete_v4_lease(ip)
        return self.create_v4_lease(
            ip=ip, mac=mac, starts=starts, ends=ends,
            hostname=hostname, binding_state=binding_state,
            tc_tag=tag,
        )

    def count_v4_leases(self):
        """Count total v4 leases in the file."""
        return len(self.get_all_v4_leases())

    # ── DHCPv6 Lease Operations ──────────────────────────────────────── #
    @staticmethod
    def build_v6_lease(ip, duid, iaid=None, preferred_life=3600,
                       max_life=7200, ends=None, binding_state="active",
                       cltt=None, tc_tag=None):
        """
        Build a DHCPv6 lease block string.

        When *tc_tag* is supplied a comment line is prepended:

            # [AUTOTEST] TC011 | 2026/04/08 14:30:00
            ia-na "..." {
              ...
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
        if tc_tag:
            lines.append("# [AUTOTEST] {} | {}".format(tc_tag, now_str))
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
                        max_life=7200, ends=None, binding_state="active",
                        tc_tag=None):
        """Create a DHCPv6 lease by appending to the v6 lease file.

        Falls back to ``_current_tc_tag`` when *tc_tag* is not supplied.
        """
        tag = tc_tag or self._current_tc_tag
        lease_block = self.build_v6_lease(
            ip=ip, duid=duid, iaid=iaid, preferred_life=preferred_life,
            max_life=max_life, ends=ends, binding_state=binding_state,
            tc_tag=tag,
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
        """Delete **all** v6 lease entries for *ip* from the lease file.

        Removes every ``ia-na ... { iaaddr <ip> { ... } }`` block
        together with any preceding ``# [AUTOTEST]`` comment, then
        normalizes blank lines.
        """
        content = self._read_file(self.v6_lease_file)
        pattern = r"\n?(?:#\s*\[AUTOTEST\][^\n]*\n)?ia-na\s+\"[^\"]*\"\s*\{{[^}}]*iaaddr\s+{}\s*\{{[^}}]+\}}[^}}]*\}}\n?".format(
            re.escape(ip)
        )
        new_content = re.sub(pattern, "\n", content, flags=re.DOTALL)
        if new_content == content:
            return False
        new_content = self._normalize_content(new_content)
        self._write_file(self.v6_lease_file, new_content)
        return True

    def update_v6_lease(self, ip, duid=None, iaid=None, preferred_life=None,
                        max_life=None, ends=None, binding_state=None,
                        tc_tag=None):
        """Update a v6 lease: delete old, write new."""
        tag = tc_tag or self._current_tc_tag
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
            max_life=max_life, ends=ends, binding_state=binding_state,
            tc_tag=tag,
        )

    def count_v6_leases(self):
        """Count total v6 leases."""
        return len(self.get_all_v6_leases())

    # ── DUID Type Helpers ────────────────────────────────────────────── #
    @staticmethod
    def build_duid_llt(mac, timestamp_hex="5f3c6a00"):
        """Build DUID-LLT (Type 1) bytes from MAC and timestamp hex.

        Structure: type(2) + hw_type(2) + time(4) + MAC(6) = 14 bytes
        Returns list of ints (byte values).
        """
        ts = [int(timestamp_hex[i:i+2], 16) for i in range(0, 8, 2)]
        mac_bytes = [int(b, 16) for b in mac.split(":")]
        return [0, 1, 0, 1] + ts + mac_bytes

    @staticmethod
    def build_duid_ll(mac):
        """Build DUID-LL (Type 3) bytes from MAC.

        Structure: type(2) + hw_type(2) + MAC(6) = 10 bytes
        Returns list of ints (byte values).
        """
        mac_bytes = [int(b, 16) for b in mac.split(":")]
        return [0, 3, 0, 1] + mac_bytes

    @staticmethod
    def duid_bytes_to_escaped(duid_bytes, iaid_bytes=None):
        """Convert DUID byte list to ISC DHCP escaped string.

        If *iaid_bytes* is provided it is prepended (default IAID
        ``[1, 0, 0, 0]``).
        """
        if iaid_bytes is None:
            iaid_bytes = [1, 0, 0, 0]
        octets = list(iaid_bytes) + list(duid_bytes)
        parts = []
        for b in octets:
            ch = chr(b)
            if 0x21 <= b <= 0x7E and ch not in '"\\;{}':
                parts.append(ch)
            else:
                parts.append("\\{:03o}".format(b))
        return "".join(parts)

    @staticmethod
    def duid_bytes_to_hex(duid_bytes):
        """Convert DUID byte list to colon-separated hex string."""
        return ":".join("{:02x}".format(b) for b in duid_bytes)

    @staticmethod
    def duid_type_from_bytes(duid_bytes):
        """Return DUID type number from a byte list (first 2 bytes)."""
        if len(duid_bytes) < 2:
            return None
        return (duid_bytes[0] << 8) | duid_bytes[1]

    @staticmethod
    def duid_extract_mac(duid_bytes):
        """Extract MAC address from DUID-LLT (type 1) or DUID-LL (type 3).

        Returns MAC string or None if not a MAC-bearing DUID type.
        """
        if len(duid_bytes) < 4:
            return None
        dtype = (duid_bytes[0] << 8) | duid_bytes[1]
        if dtype == 1 and len(duid_bytes) >= 14:
            # LLT: skip type(2)+hw(2)+time(4), last 6 bytes are MAC
            mac_bytes = duid_bytes[8:14]
        elif dtype == 3 and len(duid_bytes) >= 10:
            # LL: skip type(2)+hw(2), last 6 bytes are MAC
            mac_bytes = duid_bytes[4:10]
        else:
            return None
        return ":".join("{:02x}".format(b) for b in mac_bytes)

    def build_v6_lease_duid(self, ip, mac, duid_type="LLT",
                            iaid_bytes=None, preferred_life=3600,
                            max_life=7200, ends=None,
                            binding_state="active", cltt=None,
                            tc_tag=None):
        """Build a DHCPv6 lease block using a real DUID from a MAC.

        *duid_type* must be ``"LLT"`` (Type 1) or ``"LL"`` (Type 3).
        Returns the lease block string.
        """
        now_str = datetime.utcnow().strftime("%Y/%m/%d %H:%M:%S")
        if not ip:
            raise ValueError("ip is required")
        if not mac:
            raise ValueError("mac is required")
        if duid_type.upper() == "LLT":
            duid_bytes = self.build_duid_llt(mac)
        elif duid_type.upper() == "LL":
            duid_bytes = self.build_duid_ll(mac)
        else:
            raise ValueError("duid_type must be 'LLT' or 'LL', got {}".format(duid_type))

        if not ends:
            ends = "2027/04/07 00:00:00"
        if not cltt:
            cltt = now_str

        duid_str = self.duid_bytes_to_escaped(duid_bytes, iaid_bytes)
        tag = tc_tag or self._current_tc_tag

        lines = []
        if tag:
            lines.append("# [AUTOTEST] {} | {}".format(tag, now_str))
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

    def create_v6_lease_duid(self, ip, mac, duid_type="LLT",
                             iaid_bytes=None, preferred_life=3600,
                             max_life=7200, ends=None,
                             binding_state="active", tc_tag=None):
        """Create a DHCPv6 lease using a real DUID built from MAC.

        Convenience wrapper around build_v6_lease_duid + _append_file.
        """
        tag = tc_tag or self._current_tc_tag
        block = self.build_v6_lease_duid(
            ip=ip, mac=mac, duid_type=duid_type, iaid_bytes=iaid_bytes,
            preferred_life=preferred_life, max_life=max_life,
            ends=ends, binding_state=binding_state, tc_tag=tag,
        )
        self._append_file(self.v6_lease_file, "\n" + block + "\n")
        return block

    def get_v6_lease_duid_type(self, ip):
        """Read a v6 lease and return its DUID type number (1, 2, 3, 4).

        Parses the ia-na escaped DUID string, skips 4-byte IAID,
        reads the DUID type from the first 2 bytes of the DUID portion.
        Returns None when the lease is not found.
        """
        block = self.get_v6_lease(ip)
        if not block:
            return None
        m = re.search(r'ia-na "([^"]*)"', block)
        if not m:
            return None
        raw = m.group(1)
        # Decode the escaped string to bytes
        octets = []
        i = 0
        while i < len(raw):
            if raw[i] == '\\' and i + 3 < len(raw) and raw[i+1:i+4].isdigit():
                octets.append(int(raw[i+1:i+4], 8))
                i += 4
            elif raw[i] == '\\' and i + 1 < len(raw):
                octets.append(ord(raw[i+1]))
                i += 2
            else:
                octets.append(ord(raw[i]))
                i += 1
        # Skip 4-byte IAID, DUID starts at byte 4
        if len(octets) < 6:
            return None
        duid_bytes = octets[4:]
        return self.duid_type_from_bytes(duid_bytes)

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

    # ── Hardware Type helpers ────────────────────────────────────────── #
    @staticmethod
    def build_v4_lease_with_hw_type(ip, mac, hw_type="ethernet", starts=None,
                                     ends=None, hostname=None,
                                     binding_state="active", tc_tag=None):
        """Build a v4 lease block with a custom hardware type."""
        now_str = datetime.utcnow().strftime("%Y/%m/%d %H:%M:%S")
        if not ip:
            raise ValueError("ip is required")
        if not mac:
            raise ValueError("mac is required")
        if not starts:
            starts = now_str
        if not ends:
            ends = "2027/04/07 00:00:00"
        lines = []
        if tc_tag:
            lines.append("# [AUTOTEST] {} | {}".format(tc_tag, now_str))
        lines.append("lease {} {{".format(ip))
        lines.append("  starts 1 {};".format(starts))
        lines.append("  ends 1 {};".format(ends))
        lines.append("  tstp 1 {};".format(ends))
        lines.append("  cltt 1 {};".format(starts))
        lines.append("  binding state {};".format(binding_state))
        if hostname:
            lines.append('  client-hostname "{}";'.format(hostname))
        lines.append("  hardware {} {};".format(hw_type, mac))
        lines.append("}")
        return "\n".join(lines)

    def create_v4_lease_with_hw_type(self, ip, mac, hw_type="ethernet",
                                      starts=None, ends=None, hostname=None,
                                      binding_state="active", tc_tag=None):
        """Create a v4 lease with a custom hardware type."""
        tag = tc_tag or self._current_tc_tag
        block = self.build_v4_lease_with_hw_type(
            ip=ip, mac=mac, hw_type=hw_type, starts=starts, ends=ends,
            hostname=hostname, binding_state=binding_state, tc_tag=tag,
        )
        self._append_file(self.v4_lease_file, "\n" + block + "\n")
        return block

    @staticmethod
    def parse_v4_hardware(lease_block):
        """Parse hardware type and address from a v4 lease block."""
        m = re.search(r"hardware\s+(\S+)\s+([^;]+);", lease_block)
        if m:
            return {"hw_type": m.group(1), "hw_address": m.group(2)}
        return {"hw_type": None, "hw_address": None}

    # ── DNS Lookup helpers (via dig on the remote server) ────────────── #
    @staticmethod
    def _filter_dig(lines):
        """Remove dig error/comment lines, return only record data."""
        return [
            l for l in lines
            if l and not l.startswith(";") and "timed out" not in l
            and "connection refused" not in l.lower()
        ]

    def dns_lookup_a(self, hostname, server=None):
        """Lookup A record for hostname. Returns list of IPs."""
        cmd = "dig +short A {}".format(hostname)
        if server:
            cmd = "dig +short @{} A {}".format(server, hostname)
        out, err, code = self._exec(cmd)
        raw = [line.strip() for line in out.strip().split("\n") if line.strip()]
        return self._filter_dig(raw)

    def dns_lookup_aaaa(self, hostname, server=None):
        """Lookup AAAA record for hostname. Returns list of IPv6 addresses."""
        cmd = "dig +short AAAA {}".format(hostname)
        if server:
            cmd = "dig +short @{} AAAA {}".format(server, hostname)
        out, err, code = self._exec(cmd)
        raw = [line.strip() for line in out.strip().split("\n") if line.strip()]
        return self._filter_dig(raw)

    def dns_lookup_ptr(self, ip, server=None):
        """Lookup PTR record for IP. Returns list of hostnames."""
        cmd = "dig +short -x {}".format(ip)
        if server:
            cmd = "dig +short @{} -x {}".format(server, ip)
        out, err, code = self._exec(cmd)
        raw = [line.strip() for line in out.strip().split("\n") if line.strip()]
        return self._filter_dig(raw)

    def get_ddns_config(self):
        """Check if DDNS is enabled in dhcpd.conf."""
        out, err, code = self._exec(
            "grep -i 'ddns-update-style' /etc/dhcp/dhcpd.conf 2>/dev/null "
            "|| grep -i 'ddns-update-style' /usr/local/dhcpd/etc/dhcpd.conf 2>/dev/null "
            "|| echo 'not-found'"
        )
        return out.strip()

    # ── Lease file raw content (for sync verification) ───────────────── #
    def get_v4_lease_file_raw(self):
        """Return the raw content of the v4 lease file."""
        return self._read_file(self.v4_lease_file)

    def get_v6_lease_file_raw(self):
        """Return the raw content of the v6 lease file."""
        return self._read_file(self.v6_lease_file)
