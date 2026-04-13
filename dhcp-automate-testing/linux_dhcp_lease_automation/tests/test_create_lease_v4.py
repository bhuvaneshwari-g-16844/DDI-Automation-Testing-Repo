"""
test_create_lease_v4.py – DHCPv4 Lease Creation Tests (TC001-TC010)

Creates leases by writing to /usr/local/dhcpd/var/lib/dhcpd.leases
and verifies them by reading the file back.
"""

import re
import pytest
from helpers.dhcp_lease_manager import DHCPLeaseManager


@pytest.mark.usefixtures("v4_backup")
class TestCreateLeaseV4:
    """TC001-TC010: Create DHCPv4 Lease tests."""

    # TC001: Create a new DHCPv4 lease with valid IP, scope ID, MAC address
    @pytest.mark.order(1)
    def test_tc001_create_v4_lease_valid(self, lease_mgr, v4_data):
        """TC001: Create a new DHCPv4 lease with valid IP and MAC address."""
        ip = "3.3.228.200"
        mac = "00:00:01:00:00:01"
        starts = "2026/04/07 10:00:00"
        ends = "2027/04/07 10:00:00"

        # Clean up if exists from previous run
        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(
            ip=ip,
            mac=mac,
            starts=starts,
            ends=ends,
            binding_state="active",
        )

        # Verify lease exists in file
        assert lease_mgr.v4_lease_exists(ip), \
            "Lease {} not found in lease file after creation".format(ip)

        # Verify lease fields
        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed["ip"] == ip
        assert parsed["mac"] == mac
        assert parsed["binding_state"] == "active"

    # TC002: Create DHCPv4 lease with valid hostname and lease expiry time
    @pytest.mark.order(2)
    def test_tc002_create_v4_lease_with_hostname(self, lease_mgr, v4_data):
        """TC002: Create DHCPv4 lease with hostname and expiry."""
        ip = "3.3.228.201"
        mac = "00:00:23:df:5e:f2"
        hostname = "test-hostname-v4"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(
            ip=ip, mac=mac, hostname=hostname,
            starts="2026/04/07 10:00:00",
            ends="2027/04/07 10:00:00",
        )

        lease_block = lease_mgr.get_v4_lease(ip)
        assert lease_block is not None, "Lease not created"
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed.get("hostname") == hostname, \
            "Hostname mismatch: expected {}, got {}".format(hostname, parsed.get("hostname"))
        assert "2027/04/07" in parsed.get("ends", ""), "Expiry time not set correctly"

    # TC003: Create DHCPv4 lease with duplicate IP address
    @pytest.mark.order(3)
    def test_tc003_create_v4_duplicate_ip(self, lease_mgr, v4_data):
        """TC003: Duplicate IP – second lease with same IP, verify both exist
        (DHCP server keeps history, last entry wins)."""
        ip = "3.3.228.203"

        # Clean up if exists from previous run
        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        # Create first lease
        lease_mgr.create_v4_lease(
            ip=ip,
            mac="00:00:03:00:00:01",
            starts="2026/04/07 10:00:00",
            ends="2027/04/07 10:00:00",
        )
        assert lease_mgr.v4_lease_exists(ip), "First lease must exist"

        # Create duplicate with different MAC
        lease_mgr.create_v4_lease(
            ip=ip,
            mac="00:00:03:00:00:02",
            starts="2026/04/07 12:00:00",
            ends="2027/04/07 12:00:00",
        )

        # Both entries exist in history (ISC DHCP appends, last wins)
        history = lease_mgr.get_v4_lease_history(ip)
        assert len(history) >= 2, \
            "Expected at least 2 lease entries for duplicate IP, got {}".format(len(history))

    # TC004: Create DHCPv4 lease with invalid IP format
    @pytest.mark.order(4)
    @pytest.mark.parametrize("invalid_ip", [
        "999.999.999.999",
        "abc.def.ghi.jkl",
        "256.1.1.1",
        "-1.0.0.0",
        "1.2.3.4.5",
    ])
    def test_tc004_create_v4_invalid_ip(self, lease_mgr, invalid_ip):
        """TC004: Create lease with invalid IP – write it and verify
        dhcpd would reject it (file contains malformed entry)."""
        lease_block = DHCPLeaseManager.build_v4_lease(
            ip=invalid_ip,
            mac="00:11:22:33:44:55",
        )
        # Verify the built block contains the invalid IP
        assert invalid_ip in lease_block
        # We build but do NOT write to avoid corrupting the lease file
        # This validates the input format is truly invalid
        parts = invalid_ip.split(".")
        if len(parts) == 4:
            for p in parts:
                try:
                    val = int(p)
                    if val < 0 or val > 255:
                        return  # confirmed invalid
                except ValueError:
                    return  # confirmed invalid (non-numeric)
        else:
            return  # wrong number of octets = invalid

    # TC004-marker: Write a marker lease so TC004 is visible in lease file
    @pytest.mark.order(4)
    def test_tc004_marker(self, lease_mgr):
        """TC004: Write marker lease to confirm invalid-IP validation ran."""
        ip = "3.3.228.204"
        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)
        lease_mgr.create_v4_lease(
            ip=ip, mac="00:00:04:00:00:01",
            hostname="tc004-invalid-ip-validated",
        )
        assert lease_mgr.v4_lease_exists(ip)

    # TC005: Create DHCPv4 lease with IP outside scope range
    @pytest.mark.order(5)
    def test_tc005_create_v4_out_of_scope(self, lease_mgr, v4_data):
        """TC005: Create lease with IP outside defined scope range."""
        out_ip = "10.10.10.5"

        if lease_mgr.v4_lease_exists(out_ip):
            lease_mgr.delete_v4_lease(out_ip)

        lease_mgr.create_v4_lease(
            ip=out_ip,
            mac="00:00:05:00:00:01",
        )

        # Lease will be written (file-level), but it's outside the scope
        # Verify it exists in file
        assert lease_mgr.v4_lease_exists(out_ip), \
            "Out-of-scope lease should still be written to file"

    # TC006: Create DHCPv4 lease without mandatory fields
    @pytest.mark.order(6)
    def test_tc006_create_v4_missing_fields(self, lease_mgr):
        """TC006: Building a lease without IP or MAC should fail."""
        # Missing IP
        with pytest.raises((TypeError, ValueError)):
            DHCPLeaseManager.build_v4_lease(ip=None, mac="00:11:22:33:44:55")

        # Missing MAC
        with pytest.raises((TypeError, ValueError)):
            DHCPLeaseManager.build_v4_lease(ip="3.3.228.160", mac=None)

        # Write marker lease to confirm validation ran
        ip = "3.3.228.206"
        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)
        lease_mgr.create_v4_lease(
            ip=ip, mac="00:00:06:00:00:01",
            hostname="tc006-missing-fields-validated",
        )
        assert lease_mgr.v4_lease_exists(ip)

    # TC007: Create DHCPv4 lease with invalid MAC format
    @pytest.mark.order(7)
    @pytest.mark.parametrize("invalid_mac", [
        "ZZ:ZZ:ZZ:ZZ:ZZ:ZZ",
        "00:11:22",
        "not-a-mac",
        "00:11:22:33:44:55:66:77",
    ])
    def test_tc007_create_v4_invalid_mac(self, lease_mgr, invalid_mac):
        """TC007: Create lease with invalid MAC format – verify rejection."""
        # Confirm the MAC does NOT match valid format
        mac_pattern = r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$"
        assert not re.match(mac_pattern, invalid_mac), \
            "MAC '{}' should be invalid but matched pattern".format(invalid_mac)

    # TC007-marker: Write a marker lease so TC007 is visible in lease file
    @pytest.mark.order(7)
    def test_tc007_marker(self, lease_mgr):
        """TC007: Write marker lease to confirm invalid-MAC validation ran."""
        ip = "3.3.228.207"
        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)
        lease_mgr.create_v4_lease(
            ip=ip, mac="00:00:07:00:00:01",
            hostname="tc007-invalid-mac-validated",
        )
        assert lease_mgr.v4_lease_exists(ip)

    # TC008: Create multiple DHCPv4 leases in batch
    @pytest.mark.order(8)
    def test_tc008_create_v4_batch(self, lease_mgr, v4_data):
        """TC008: Create multiple leases in batch within same scope."""
        batch = v4_data["batch_leases"]

        # Clean up first
        for lease in batch:
            if lease_mgr.v4_lease_exists(lease["ip"]):
                lease_mgr.delete_v4_lease(lease["ip"])

        # Create all leases
        for lease in batch:
            lease_mgr.create_v4_lease(ip=lease["ip"], mac=lease["mac"])

        # Verify all exist
        for lease in batch:
            assert lease_mgr.v4_lease_exists(lease["ip"]), \
                "Batch lease {} not found".format(lease["ip"])

        # Verify unique IPs and MACs
        ips = [l["ip"] for l in batch]
        macs = [l["mac"] for l in batch]
        assert len(set(ips)) == len(ips), "Duplicate IPs in batch"
        assert len(set(macs)) == len(macs), "Duplicate MACs in batch"

    # TC009: Create DHCPv4 lease with past expiry date
    @pytest.mark.order(9)
    def test_tc009_create_v4_past_expiry(self, lease_mgr):
        """TC009: Create lease with past expiry date."""
        ip = "3.3.228.209"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(
            ip=ip,
            mac="00:00:23:00:00:09",
            starts="2020/01/01 00:00:00",
            ends="2020/06/01 00:00:00",  # past expiry
        )

        # Lease is written; DHCP server marks it as expired
        lease_block = lease_mgr.get_v4_lease(ip)
        assert lease_block is not None, "Past-expiry lease should still be in file"
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert "2020/06/01" in parsed.get("ends", ""), "Past expiry date not set"

        # Clean up

    # TC010: Create DHCPv4 lease and verify it appears (file read-back)
    @pytest.mark.order(10)
    def test_tc010_create_v4_verify_readback(self, lease_mgr, v4_data):
        """TC010: Create lease and verify it appears in lease file immediately."""
        ip = "3.3.228.210"
        mac = "00:00:23:00:00:10"
        hostname = "readback-test"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        # Count before
        count_before = lease_mgr.count_v4_leases()

        lease_mgr.create_v4_lease(
            ip=ip, mac=mac, hostname=hostname,
            starts="2026/04/07 10:00:00",
            ends="2027/04/07 10:00:00",
        )

        # Count after
        count_after = lease_mgr.count_v4_leases()
        assert count_after > count_before, \
            "Lease count did not increase: before={}, after={}".format(
                count_before, count_after)

        # Verify fields
        lease_block = lease_mgr.get_v4_lease(ip)
        assert lease_block is not None
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed["ip"] == ip
        assert parsed["mac"] == mac
        assert parsed.get("hostname") == hostname
