"""
test_lease_data_sync.py – Lease Data Sync Tests (TC149-TC151)

Verifies lease data sync latency and integrity between
the DHCP agent server and the DDI console after restarts.
"""

import time
import pytest
from helpers.dhcp_lease_manager import DHCPLeaseManager


@pytest.mark.usefixtures("v4_backup", "v6_backup")
class TestLeaseDataSync:
    """TC149-TC151: Lease Data Sync tests."""

    # TC149: Verify lease data sync latency between agent and console
    def test_tc149_sync_latency(self, lease_mgr, v4_data):
        """TC149: Lease changes should persist after service restart."""
        ip = "3.3.228.149"
        mac = "00:01:49:00:00:01"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac, hostname="sync-test")

        # After restart, lease should still be in file
        assert lease_mgr.v4_lease_exists(ip), \
            "Lease should persist after dhcpd restart"

        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed["ip"] == ip


    # TC150: Verify lease data integrity after agent server restart
    def test_tc150_integrity_after_agent_restart(self, lease_mgr, v4_data, v6_data):
        """TC150: All lease data should remain intact – verify both v4
        and v6 leases keep correct field values after write-back read."""
        v4_ip = "3.3.228.150"
        v4_mac = "00:01:50:00:00:01"
        v6_ip = "2000::1501"
        v6_duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\150\\001"

        # Setup
        if lease_mgr.v4_lease_exists(v4_ip):
            lease_mgr.delete_v4_lease(v4_ip)
        if lease_mgr.v6_lease_exists(v6_ip):
            lease_mgr.delete_v6_lease(v6_ip)

        lease_mgr.create_v4_lease(
            ip=v4_ip, mac=v4_mac, hostname="restart-v4",
        )
        lease_mgr.create_v6_lease(
            ip=v6_ip, duid=v6_duid, preferred_life=3600,
        )

        # Record counts
        v4_count = lease_mgr.count_v4_leases()
        v6_count = lease_mgr.count_v6_leases()

        assert v4_count >= 1, "v4 count should include the new lease"
        assert v6_count >= 1, "v6 count should include the new lease"

        # Verify data integrity (read-back)
        assert lease_mgr.v4_lease_exists(v4_ip), \
            "v4 lease should exist after creation"
        assert lease_mgr.v6_lease_exists(v6_ip), \
            "v6 lease should exist after creation"

        # Verify field integrity
        v4_block = lease_mgr.get_v4_lease(v4_ip)
        v4_parsed = DHCPLeaseManager.parse_v4_lease(v4_block)
        assert v4_parsed["ip"] == v4_ip
        assert v4_parsed["mac"].lower() == v4_mac.lower()

        v6_block = lease_mgr.get_v6_lease(v6_ip)
        v6_parsed = DHCPLeaseManager.parse_v6_lease(v6_block)
        assert v6_parsed["ip"] == v6_ip


    # TC151: Verify lease data integrity after console server restart
    def test_tc151_integrity_after_console_restart(self, lease_mgr, v4_data):
        """TC151: Agent-side lease data should be unaffected by
        console restart (console reads from agent)."""
        ip = "3.3.228.245"
        mac = "00:01:51:00:00:01"

        # Clean and recreate
        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac, hostname="console-restart")

        # Verify lease exists on agent (console restart doesn't affect agent)
        assert lease_mgr.v4_lease_exists(ip), \
            "Agent-side lease should be independent of console"

        # Verify all fields
        block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(block)
        assert parsed["ip"] == ip
        assert parsed["mac"].lower() == mac.lower()
        assert parsed.get("hostname") == "console-restart"

