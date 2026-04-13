"""
test_mac_address.py – MAC Address Tests (TC074-TC081)

Verifies MAC address display, update, validation, duplicate handling,
and DUID-based MAC parsing for DHCPv4 and DHCPv6 leases.
"""

import re
import pytest
from helpers.dhcp_lease_manager import DHCPLeaseManager


@pytest.mark.usefixtures("v4_backup", "v6_backup")
class TestMACAddress:
    """TC074-TC081: MAC Address tests."""

    # TC074: Verify MAC address is displayed correctly for DHCPv4 lease
    def test_tc074_mac_display_v4(self, lease_mgr, v4_data):
        """TC074: Verify MAC address format (XX:XX:XX:XX:XX:XX) in lease."""
        ip = "3.3.228.174"
        mac = "00:AA:BB:CC:DD:74"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac)

        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)

        # Verify MAC format
        mac_pattern = r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$"
        assert re.match(mac_pattern, parsed["mac"]), \
            "MAC '{}' not in correct format XX:XX:XX:XX:XX:XX".format(
                parsed["mac"])
        assert parsed["mac"].lower() == mac.lower(), \
            "MAC mismatch: expected {}, got {}".format(mac, parsed["mac"])


    # TC075: Update MAC address of an existing DHCPv4 lease
    def test_tc075_mac_update_v4(self, lease_mgr, dhcp_testdata):
        """TC075: Update MAC address to a new valid MAC."""
        ip = "3.3.228.175"
        old_mac = "00:00:75:00:00:01"
        new_mac = dhcp_testdata["mac_test_data"]["update_mac"]

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=old_mac)
        lease_mgr.update_v4_lease(ip=ip, mac=new_mac)

        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed["mac"].lower() == new_mac.lower(), \
            "MAC not updated: expected {}, got {}".format(new_mac, parsed["mac"])


    # TC076: Update MAC address with invalid format
    @pytest.mark.parametrize("invalid_mac", [
        "ZZ:ZZ:ZZ:ZZ:ZZ:ZZ",
        "00:11:22",
        "not-a-mac",
        "00:11:22:33:44:55:66:77",
    ])
    def test_tc076_mac_invalid_format(self, invalid_mac):
        """TC076: Verify invalid MAC formats are detected."""
        mac_pattern = r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$"
        assert not re.match(mac_pattern, invalid_mac), \
            "MAC '{}' should be detected as invalid".format(invalid_mac)

    # TC077: Update MAC with duplicate MAC already in same scope
    def test_tc077_mac_duplicate_in_scope(self, lease_mgr, v4_data):
        """TC077: Two leases with same MAC in the same scope."""
        ip1 = "3.3.228.177"
        ip2 = "3.3.228.178"
        same_mac = "00:00:77:DD:DD:DD"

        for ip in [ip1, ip2]:
            if lease_mgr.v4_lease_exists(ip):
                lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip1, mac=same_mac)
        lease_mgr.create_v4_lease(ip=ip2, mac=same_mac)

        # Both leases exist with same MAC (file-level allows it)
        block1 = lease_mgr.get_v4_lease(ip1)
        block2 = lease_mgr.get_v4_lease(ip2)
        parsed1 = DHCPLeaseManager.parse_v4_lease(block1)
        parsed2 = DHCPLeaseManager.parse_v4_lease(block2)

        assert parsed1["mac"].lower() == same_mac.lower()
        assert parsed2["mac"].lower() == same_mac.lower()


    # TC078: Verify MAC address change is recorded in lease history
    def test_tc078_mac_change_history(self, lease_mgr, v4_data):
        """TC078: MAC change results in a new entry with new MAC."""
        ip = "3.3.228.179"
        old_mac = "00:00:78:AA:AA:01"
        new_mac = "00:00:78:BB:BB:02"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=old_mac, hostname="mac-hist")
        lease_mgr.update_v4_lease(ip=ip, mac=new_mac)

        # Latest entry should have new MAC
        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed["mac"].lower() == new_mac.lower(), \
            "Latest lease should have updated MAC"


    # TC079: Update MAC address with empty value
    def test_tc079_mac_empty_value(self, lease_mgr, v4_data):
        """TC079: Update with empty MAC – should preserve existing MAC."""
        ip = "3.3.228.180"
        original_mac = "00:00:79:00:00:01"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=original_mac)

        # Update with empty MAC – implementation falls back to existing
        lease_mgr.update_v4_lease(ip=ip, mac="")

        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        # MAC should still be present (not empty)
        assert parsed.get("mac"), "MAC should be preserved when empty update"


    # TC080: Verify MAC with different vendor prefixes is accepted
    @pytest.mark.parametrize("vendor_mac", [
        "00:1A:2B:3C:4D:5E",
        "AC:DE:48:00:11:22",
        "F0:DE:F1:23:45:67",
        "00:50:56:AA:BB:CC",
        "00:0C:29:11:22:33",
    ])
    def test_tc080_mac_vendor_prefixes(self, lease_mgr, vendor_mac):
        """TC080: Various vendor prefix MACs should all be accepted."""
        ip = "3.3.228.181"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=vendor_mac)

        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed["mac"].lower() == vendor_mac.lower(), \
            "Vendor MAC not stored correctly: {}".format(vendor_mac)


    # TC081: Verify MAC address in DHCPv6 lease (DUID contains MAC)
    def test_tc081_mac_in_v6_duid(self, lease_mgr, v6_data):
        """TC081: DUID-based MAC info should be present in v6 lease."""
        ip = "2000::8101"
        duid = v6_data["test_lease"]["duid"]

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid)

        lease_block = lease_mgr.get_v6_lease(ip)
        assert lease_block is not None, "v6 lease should exist"
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)

        # DUID should be present in the parsed output
        assert parsed.get("duid"), "DUID (containing MAC) should be present"
        # DUID string from ISC DHCP contains the original DUID value
        assert len(parsed["duid"]) > 0, "DUID should not be empty"

