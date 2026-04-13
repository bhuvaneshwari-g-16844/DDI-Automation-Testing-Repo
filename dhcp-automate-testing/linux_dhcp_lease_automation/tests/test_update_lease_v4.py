"""
test_update_lease_v4.py – DHCPv4 Lease Update Tests (TC021-TC030)

Updates leases by modifying /usr/local/dhcpd/var/lib/dhcpd.leases.
When a lease is updated, the old entry becomes history and the new entry
is appended.
"""

import pytest
from helpers.dhcp_lease_manager import DHCPLeaseManager


@pytest.mark.usefixtures("v4_backup")
class TestUpdateLeaseV4:
    """TC021-TC030: Update DHCPv4 Lease tests."""

    @pytest.fixture(autouse=True)
    def _ensure_lease_exists(self, lease_mgr, v4_data):
        """Ensure a base lease exists for update tests."""
        td = v4_data["test_lease"]
        if not lease_mgr.v4_lease_exists(td["ip"]):
            lease_mgr.create_v4_lease(
                ip=td["ip"], mac=td["mac"],
                starts=td["starts"], ends=td["ends"],
            )

    # TC021: Update an existing DHCPv4 lease hostname
    def test_tc021_update_v4_hostname(self, lease_mgr, v4_data):
        """TC021: Update DHCPv4 lease hostname."""
        td = v4_data["test_lease"]
        new_hostname = "updated-hostname-v4"

        lease_mgr.update_v4_lease(
            ip=td["ip"], hostname=new_hostname,
        )

        lease_block = lease_mgr.get_v4_lease(td["ip"])
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed.get("hostname") == new_hostname, \
            "Hostname not updated: expected {}, got {}".format(
                new_hostname, parsed.get("hostname"))

    # TC022: Update DHCPv4 lease expiry time
    def test_tc022_update_v4_expiry(self, lease_mgr, v4_data):
        """TC022: Update DHCPv4 lease expiry to a future date."""
        td = v4_data["test_lease"]
        new_ends = "2028/12/31 23:59:59"

        lease_mgr.update_v4_lease(ip=td["ip"], ends=new_ends)

        lease_block = lease_mgr.get_v4_lease(td["ip"])
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert "2028/12/31" in parsed.get("ends", ""), \
            "Expiry not updated to 2028/12/31"

    # TC023: Update DHCPv4 lease IP to new valid IP
    def test_tc023_update_v4_ip(self, lease_mgr, v4_data):
        """TC023: Update lease IP by deleting old and creating new."""
        old_ip = v4_data["test_lease"]["ip"]
        new_ip = "3.3.228.170"
        mac = v4_data["test_lease"]["mac"]

        # Delete old
        lease_mgr.delete_v4_lease(old_ip)

        # Create with new IP
        if lease_mgr.v4_lease_exists(new_ip):
            lease_mgr.delete_v4_lease(new_ip)
        lease_mgr.create_v4_lease(ip=new_ip, mac=mac)

        assert lease_mgr.v4_lease_exists(new_ip), "New IP lease not created"
        assert not lease_mgr.v4_lease_exists(old_ip), "Old IP should be removed"

        # Restore original for subsequent tests
        lease_mgr.delete_v4_lease(new_ip)
        lease_mgr.create_v4_lease(
            ip=old_ip, mac=mac,
            starts=v4_data["test_lease"]["starts"],
            ends=v4_data["test_lease"]["ends"],
        )

    # TC024: Update DHCPv4 lease IP to out-of-scope
    def test_tc024_update_v4_ip_out_of_scope(self, lease_mgr, v4_data):
        """TC024: Update IP to out-of-scope – file accepts it."""
        td = v4_data["test_lease"]
        out_ip = v4_data["out_of_scope_ip"]

        # Create out-of-scope lease to simulate the update
        if lease_mgr.v4_lease_exists(out_ip):
            lease_mgr.delete_v4_lease(out_ip)
        lease_mgr.create_v4_lease(ip=out_ip, mac=td["mac"])

        assert lease_mgr.v4_lease_exists(out_ip), \
            "Out-of-scope IP lease should exist in file"


    # TC025: Update DHCPv4 lease IP to one already assigned
    def test_tc025_update_v4_ip_conflict(self, lease_mgr, v4_data):
        """TC025: Update to IP already used – both entries exist."""
        td = v4_data["test_lease"]
        conflict_ip = "3.3.228.101"

        # Ensure conflict IP has a lease
        if not lease_mgr.v4_lease_exists(conflict_ip):
            lease_mgr.create_v4_lease(ip=conflict_ip, mac="00:11:22:33:44:01")

        # Try to create another lease with the same IP (different MAC)
        lease_mgr.create_v4_lease(ip=conflict_ip, mac="FF:FF:FF:FF:FF:01")

        # ISC DHCP keeps both; last entry wins
        history = lease_mgr.get_v4_lease_history(conflict_ip)
        assert len(history) >= 2, "Conflict should create multiple entries"

    # TC026: Update DHCPv4 lease scope ID
    def test_tc026_update_v4_scope(self, lease_mgr, v4_data):
        """TC026: Update lease scope by moving IP to different range.
        (Scope change = delete from old scope, create in new)."""
        td = v4_data["test_lease"]
        # Simulate scope change by creating in different subnet
        new_scope_ip = "10.10.10.100"
        mac = td["mac"]

        if lease_mgr.v4_lease_exists(new_scope_ip):
            lease_mgr.delete_v4_lease(new_scope_ip)

        lease_mgr.create_v4_lease(ip=new_scope_ip, mac=mac)
        assert lease_mgr.v4_lease_exists(new_scope_ip), "New scope lease not created"


    # TC027: Update DHCPv4 lease with empty mandatory fields
    def test_tc027_update_v4_empty_fields(self, lease_mgr, v4_data):
        """TC027: Update with empty MAC keeps existing MAC (no error)."""
        td = v4_data["test_lease"]

        # Empty MAC means "keep existing" – verify lease still has a valid MAC
        lease_mgr.update_v4_lease(ip=td["ip"], mac="")
        lease_block = lease_mgr.get_v4_lease(td["ip"])
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed.get("mac"), "MAC should be preserved from existing lease"

    # TC028: Update DHCPv4 lease and verify readback
    def test_tc028_update_v4_verify_readback(self, lease_mgr, v4_data):
        """TC028: Update lease and verify changes in file."""
        td = v4_data["test_lease"]
        new_hostname = "verify-update"
        new_ends = "2029/01/01 00:00:00"

        lease_mgr.update_v4_lease(
            ip=td["ip"], hostname=new_hostname, ends=new_ends,
        )

        lease_block = lease_mgr.get_v4_lease(td["ip"])
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed.get("hostname") == new_hostname
        assert "2029/01/01" in parsed.get("ends", "")

    # TC029: Update multiple fields simultaneously
    def test_tc029_update_v4_multiple_fields(self, lease_mgr, v4_data):
        """TC029: Update hostname, expiry, and MAC simultaneously."""
        td = v4_data["test_lease"]
        new_mac = "AA:BB:CC:DD:EE:29"
        new_hostname = "multi-update"
        new_ends = "2028/06/15 12:00:00"

        lease_mgr.update_v4_lease(
            ip=td["ip"], mac=new_mac, hostname=new_hostname, ends=new_ends,
        )

        lease_block = lease_mgr.get_v4_lease(td["ip"])
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed["mac"] == new_mac
        assert parsed.get("hostname") == new_hostname
        assert "2028/06/15" in parsed.get("ends", "")

    # TC030: Update DHCPv4 lease expiry to past date
    def test_tc030_update_v4_past_expiry(self, lease_mgr, v4_data):
        """TC030: Update expiry to past date – lease becomes expired."""
        td = v4_data["test_lease"]
        past_ends = "2020/01/01 00:00:00"

        lease_mgr.update_v4_lease(ip=td["ip"], ends=past_ends)

        lease_block = lease_mgr.get_v4_lease(td["ip"])
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert "2020/01/01" in parsed.get("ends", ""), \
            "Past expiry should be written to file"
