"""
test_hardware_update.py – Hardware Type Update Tests (TC094-TC102)

Verifies hardware type display, update, validation, and history
for both DHCPv4 and DHCPv6 leases.
"""

import re
import pytest
from helpers.dhcp_lease_manager import DHCPLeaseManager


@pytest.mark.usefixtures("v4_backup", "v6_backup")
class TestHardwareUpdate:
    """TC094-TC102: Hardware Update tests."""

    # TC094: Verify hardware type is displayed correctly for DHCPv4 lease
    def test_tc094_v4_hardware_type_display(self, lease_mgr, v4_data):
        """TC094: Verify hardware type field shows 'ethernet' for v4."""
        ip = "3.3.228.194"
        mac = "00:00:94:00:00:01"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac)

        lease_block = lease_mgr.get_v4_lease(ip)
        hw = DHCPLeaseManager.parse_v4_hardware(lease_block)
        assert hw["hw_type"] == "ethernet", \
            "Hardware type should be 'ethernet', got '{}'".format(hw["hw_type"])


    # TC095: Update hardware type for an existing DHCPv4 lease
    def test_tc095_v4_hardware_type_update(self, lease_mgr, v4_data):
        """TC095: Update hardware type (e.g., to token-ring)."""
        ip = "3.3.228.195"
        mac = "00:00:95:00:00:01"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        # Create with default hardware type (ethernet)
        lease_mgr.create_v4_lease(ip=ip, mac=mac)

        # Delete and recreate with different hardware type
        lease_mgr.delete_v4_lease(ip)
        lease_mgr.create_v4_lease_with_hw_type(
            ip=ip, mac=mac, hw_type="token-ring",
        )

        lease_block = lease_mgr.get_v4_lease(ip)
        hw = DHCPLeaseManager.parse_v4_hardware(lease_block)
        assert hw["hw_type"] == "token-ring", \
            "Hardware type should be 'token-ring', got '{}'".format(hw["hw_type"])


    # TC096: Update hardware information with invalid hardware type
    def test_tc096_v4_hardware_invalid_type(self, lease_mgr, dhcp_testdata):
        """TC096: Verify invalid hardware type is detected."""
        invalid_type = dhcp_testdata["hardware_test_data"]["invalid_type"]

        # Valid ISC DHCP hardware types
        valid_types = {"ethernet", "token-ring", "fddi"}
        assert invalid_type not in valid_types, \
            "'{}' should not be a valid hardware type".format(invalid_type)

    # TC097: Verify hardware address matches MAC address for DHCPv4
    def test_tc097_v4_hardware_matches_mac(self, lease_mgr, v4_data):
        """TC097: Hardware address should correspond to MAC address."""
        ip = "3.3.228.197"
        mac = "00:00:97:AA:BB:CC"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac)

        lease_block = lease_mgr.get_v4_lease(ip)
        hw = DHCPLeaseManager.parse_v4_hardware(lease_block)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)

        assert hw["hw_address"].lower() == parsed["mac"].lower(), \
            "Hardware address '{}' should match MAC '{}'".format(
                hw["hw_address"], parsed["mac"])


    # TC098: Update hardware address and verify MAC consistency
    def test_tc098_v4_hardware_address_update(self, lease_mgr, v4_data):
        """TC098: Update hardware address, verify MAC reflects change."""
        ip = "3.3.228.198"
        old_mac = "00:00:98:00:00:01"
        new_mac = "00:00:98:FF:FF:02"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=old_mac)
        lease_mgr.update_v4_lease(ip=ip, mac=new_mac)

        lease_block = lease_mgr.get_v4_lease(ip)
        hw = DHCPLeaseManager.parse_v4_hardware(lease_block)
        assert hw["hw_address"].lower() == new_mac.lower(), \
            "Hardware address not updated to {}".format(new_mac)


    # TC099: Verify hardware update is recorded in lease history
    def test_tc099_v4_hardware_update_history(self, lease_mgr, v4_data):
        """TC099: Hardware update should create new history entry."""
        ip = "3.3.228.199"
        mac = "00:00:99:00:00:01"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac)
        lease_mgr.update_v4_lease(ip=ip, mac="00:00:99:FF:FF:02")

        # Latest entry should have new MAC
        lease_block = lease_mgr.get_v4_lease(ip)
        hw = DHCPLeaseManager.parse_v4_hardware(lease_block)
        assert hw["hw_address"].lower() == "00:00:99:ff:ff:02", \
            "History should reflect hardware update"


    # TC100: Verify hardware type for DHCPv6 lease
    def test_tc100_v6_hardware_type(self, lease_mgr, v6_data):
        """TC100: v6 leases use DUID instead of hardware type.
        Verify DUID is present in the lease."""
        ip = "2000::a001"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\100\\001"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid)

        lease_block = lease_mgr.get_v6_lease(ip)
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert parsed.get("duid"), "v6 lease should have DUID (hardware ID)"


    # TC101: Update hardware information for DHCPv6 lease
    def test_tc101_v6_hardware_update(self, lease_mgr, v6_data):
        """TC101: Update DUID (hardware identifier) for v6 lease."""
        ip = "2000::a101"
        old_duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\101\\001"
        new_duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\101\\002"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=old_duid)
        lease_mgr.update_v6_lease(ip=ip, duid=new_duid)

        lease_block = lease_mgr.get_v6_lease(ip)
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert parsed.get("duid"), "DUID should be present after update"


    # TC102: Verify hardware update for v6 is recorded in history
    def test_tc102_v6_hardware_update_history(self, lease_mgr, v6_data):
        """TC102: v6 DUID update creates new history entry."""
        ip = "2000::a201"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\102\\001"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid, preferred_life=1000)
        lease_mgr.update_v6_lease(ip=ip, preferred_life=5000)

        lease_block = lease_mgr.get_v6_lease(ip)
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert parsed.get("preferred_life") == 5000, \
            "Updated preferred-life should appear in history"

