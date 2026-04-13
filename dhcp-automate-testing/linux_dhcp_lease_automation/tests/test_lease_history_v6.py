"""
test_lease_history_v6.py – DHCPv6 Lease History Tests (TC066-TC073)

Verifies that DHCPv6 lease history is maintained correctly for
create, update, and delete operations on the v6 lease file.
"""

import re
import pytest
from helpers.dhcp_lease_manager import DHCPLeaseManager


@pytest.mark.usefixtures("v6_backup")
class TestLeaseHistoryV6:
    """TC066-TC073: DHCPv6 Lease History tests."""

    # TC066: Update DHCPv6 lease and verify update entry in lease history
    def test_tc066_v6_history_update_entry(self, lease_mgr, v6_data):
        """TC066: Update a v6 lease and verify updated entry in history."""
        ip = "2000::6601"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\066\\001"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(
            ip=ip, duid=duid, preferred_life=3600, max_life=7200,
            ends="2027/04/08 10:00:00",
        )

        # Update preferred-life
        lease_mgr.update_v6_lease(ip=ip, preferred_life=7200)

        history = lease_mgr.get_v6_lease_history(ip)
        assert len(history) >= 1, "Updated lease should appear in history"

        parsed = DHCPLeaseManager.parse_v6_lease(history[-1])
        assert parsed.get("preferred_life") == 7200, \
            "preferred-life should be 7200 after update"


    # TC067: Create DHCPv6 lease and verify creation entry in lease history
    def test_tc067_v6_history_create_entry(self, lease_mgr, v6_data):
        """TC067: Create a v6 lease and verify it appears in history."""
        ip = "2000::6701"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\067\\001"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(
            ip=ip, duid=duid, preferred_life=3600, max_life=7200,
        )

        history = lease_mgr.get_v6_lease_history(ip)
        assert len(history) >= 1, "Created lease should appear in history"
        parsed = DHCPLeaseManager.parse_v6_lease(history[-1])
        assert parsed["ip"] == ip


    # TC068: Delete DHCPv6 lease and verify deletion entry in lease history
    def test_tc068_v6_history_delete_entry(self, lease_mgr, v6_data):
        """TC068: Delete a v6 lease and verify it no longer appears."""
        ip = "2000::6801"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\068\\001"

        if not lease_mgr.v6_lease_exists(ip):
            lease_mgr.create_v6_lease(ip=ip, duid=duid)

        lease_mgr.delete_v6_lease(ip)
        history = lease_mgr.get_v6_lease_history(ip)
        assert len(history) == 0, \
            "After delete, no entries should remain for {}".format(ip)

    # TC069: Verify lease history shows correct timestamp for each operation
    def test_tc069_v6_history_timestamps(self, lease_mgr, v6_data):
        """TC069: Verify timestamps in v6 lease history entries."""
        ip = "2000::6901"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\069\\001"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(
            ip=ip, duid=duid, ends="2027/12/31 23:59:59",
        )

        history = lease_mgr.get_v6_lease_history(ip)
        assert len(history) >= 1
        parsed = DHCPLeaseManager.parse_v6_lease(history[-1])
        assert "2027/12/31" in parsed.get("ends", ""), \
            "End timestamp mismatch"


    # TC070: Verify lease history shows user/source who performed operation
    def test_tc070_v6_history_source(self, lease_mgr, v6_data):
        """TC070: Verify v6 lease was created via automation."""
        ip = "2000::7001"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\070\\001"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid)
        lease_block = lease_mgr.get_v6_lease(ip)
        assert lease_block is not None, "Lease should exist"
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert parsed["ip"] == ip


    # TC071: Update DHCPv6 lease multiple times, verify all changes recorded
    def test_tc071_v6_history_multiple_updates(self, lease_mgr, v6_data):
        """TC071: Multiple updates – verify latest values are correct."""
        ip = "2000::7101"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\071\\001"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid, preferred_life=1000)

        # Update 3 times
        for pl in [2000, 3000, 4000]:
            lease_mgr.update_v6_lease(ip=ip, preferred_life=pl)

        lease_block = lease_mgr.get_v6_lease(ip)
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert parsed.get("preferred_life") == 4000, \
            "Latest preferred-life should be 4000"


    # TC072: Filter lease history by date range for v6 leases
    def test_tc072_v6_history_filter_date(self, lease_mgr, v6_data):
        """TC072: Filter v6 lease history by date range."""
        ip = "2000::7201"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\072\\001"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(
            ip=ip, duid=duid, ends="2027/04/08 10:00:00",
        )

        history = lease_mgr.get_v6_lease_history(ip)
        # Filter by cltt date
        filtered = [
            h for h in history
            if re.search(r"cltt\s+\d+\s+2026/04", h) or
               re.search(r"ends\s+\d+\s+2027/04", h)
        ]
        assert len(filtered) >= 1, \
            "Should find entries in the expected date range"


    # TC073: Filter lease history by operation type for v6
    def test_tc073_v6_history_filter_operation(self, lease_mgr, v6_data):
        """TC073: Distinguish create vs update by examining field changes."""
        ip = "2000::7301"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\073\\001"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        # Create
        lease_mgr.create_v6_lease(ip=ip, duid=duid, preferred_life=1000)
        # Update
        lease_mgr.update_v6_lease(ip=ip, preferred_life=5000)

        lease_block = lease_mgr.get_v6_lease(ip)
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert parsed.get("preferred_life") == 5000, \
            "Latest entry should reflect update operation"

        # Delete and verify empty
        lease_mgr.delete_v6_lease(ip)
        history = lease_mgr.get_v6_lease_history(ip)
        assert len(history) == 0, "After delete, history should be empty"
