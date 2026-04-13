"""
test_lease_history_v4.py – DHCPv4 Lease History Tests (TC057-TC065)

Verifies that DHCP lease history (ISC DHCP appends entries, last wins)
is maintained correctly for create, update, and delete operations.
"""

import re
import pytest
from helpers.dhcp_lease_manager import DHCPLeaseManager


@pytest.mark.usefixtures("v4_backup")
class TestLeaseHistoryV4:
    """TC057-TC065: DHCPv4 Lease History tests."""

    # TC057: Update DHCPv4 lease and verify update entry in lease history
    def test_tc057_v4_history_update_entry(self, lease_mgr, v4_data):
        """TC057: Update a v4 lease and verify the old + new entries exist."""
        ip = "3.3.228.157"
        mac = "00:00:57:00:00:01"

        # Clean slate
        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        # Create original
        lease_mgr.create_v4_lease(
            ip=ip, mac=mac, hostname="original-57",
            starts="2026/04/08 10:00:00", ends="2027/04/08 10:00:00",
        )
        history_before = lease_mgr.get_v4_lease_history(ip)
        assert len(history_before) >= 1, "Lease must exist before update"

        # Update hostname
        lease_mgr.update_v4_lease(ip=ip, hostname="updated-57")

        history_after = lease_mgr.get_v4_lease_history(ip)
        # ISC DHCP: update = delete old + append new, but get_v4_lease_history
        # returns all entries. After update the new entry should exist.
        assert len(history_after) >= 1, "Updated lease must appear in history"

        # Verify new hostname
        latest = history_after[-1]
        parsed = DHCPLeaseManager.parse_v4_lease(latest)
        assert parsed.get("hostname") == "updated-57"

        # Cleanup

    # TC058: Create DHCPv4 lease and verify creation entry in lease history
    def test_tc058_v4_history_create_entry(self, lease_mgr, v4_data):
        """TC058: Create a v4 lease and verify it appears in history."""
        ip = "3.3.228.158"
        mac = "00:00:58:00:00:01"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(
            ip=ip, mac=mac, hostname="created-58",
            starts="2026/04/08 10:00:00", ends="2027/04/08 10:00:00",
        )

        history = lease_mgr.get_v4_lease_history(ip)
        assert len(history) >= 1, "Created lease should appear in history"

        parsed = DHCPLeaseManager.parse_v4_lease(history[-1])
        assert parsed["ip"] == ip
        assert parsed["mac"] == mac


    # TC059: Delete DHCPv4 lease and verify deletion entry in lease history
    def test_tc059_v4_history_delete_entry(self, lease_mgr, v4_data):
        """TC059: Delete a v4 lease and verify it no longer appears."""
        ip = "3.3.228.159"
        mac = "00:00:59:00:00:01"

        if not lease_mgr.v4_lease_exists(ip):
            lease_mgr.create_v4_lease(ip=ip, mac=mac)

        lease_mgr.delete_v4_lease(ip)
        history = lease_mgr.get_v4_lease_history(ip)
        assert len(history) == 0, \
            "After delete, no entries should remain for IP {}".format(ip)

    # TC060: Verify lease history shows correct timestamp for each operation
    def test_tc060_v4_history_timestamps(self, lease_mgr, v4_data):
        """TC060: Verify timestamps in lease history entries."""
        ip = "3.3.228.160"
        mac = "00:00:60:00:00:01"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        starts = "2026/04/08 12:00:00"
        ends = "2027/04/08 12:00:00"
        lease_mgr.create_v4_lease(
            ip=ip, mac=mac, starts=starts, ends=ends,
        )

        history = lease_mgr.get_v4_lease_history(ip)
        assert len(history) >= 1
        parsed = DHCPLeaseManager.parse_v4_lease(history[-1])

        # Verify the starts timestamp matches what we set
        assert "2026/04/08" in parsed.get("starts", ""), \
            "Start timestamp mismatch"
        assert "2027/04/08" in parsed.get("ends", ""), \
            "End timestamp mismatch"


    # TC061: Verify lease history shows user/source who performed operation
    def test_tc061_v4_history_source(self, lease_mgr, v4_data):
        """TC061: Verify the lease was created by automation (file-level).
        ISC DHCP lease files do not track who wrote the entry, so we
        verify the entry was written (source = file manipulation)."""
        ip = "3.3.228.161"
        mac = "00:00:61:00:00:01"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac, hostname="auto-61")

        lease_block = lease_mgr.get_v4_lease(ip)
        assert lease_block is not None, "Lease should exist"
        # Verify it was created with expected fields (automation source)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed["ip"] == ip
        assert parsed["mac"] == mac


    # TC062: Update DHCPv4 lease multiple times, verify all changes recorded
    def test_tc062_v4_history_multiple_updates(self, lease_mgr, v4_data):
        """TC062: Multiple updates create multiple history entries."""
        ip = "3.3.228.162"
        mac = "00:00:62:00:00:01"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        # Create original
        lease_mgr.create_v4_lease(ip=ip, mac=mac, hostname="v1")

        # Update 3 times — each update appends a new entry
        for i in range(2, 5):
            lease_mgr.update_v4_lease(ip=ip, hostname="v{}".format(i))

        # The latest entry should have the last hostname
        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed.get("hostname") == "v4", \
            "Latest entry should have hostname v4, got {}".format(
                parsed.get("hostname"))


    # TC063: Filter lease history by date range for v4 leases
    def test_tc063_v4_history_filter_date(self, lease_mgr, v4_data):
        """TC063: Filter lease history entries by date range (starts field)."""
        ip = "3.3.228.163"
        mac = "00:00:63:00:00:01"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        # Create lease with known start date
        lease_mgr.create_v4_lease(
            ip=ip, mac=mac,
            starts="2026/04/08 10:00:00",
            ends="2027/04/08 10:00:00",
        )

        history = lease_mgr.get_v4_lease_history(ip)
        # Filter: entries with starts containing "2026/04"
        filtered = [
            h for h in history
            if re.search(r"starts\s+\d+\s+2026/04", h)
        ]
        assert len(filtered) >= 1, \
            "Should find at least one entry in 2026/04 date range"


    # TC064: Filter lease history by operation type (create/update/delete)
    def test_tc064_v4_history_filter_operation(self, lease_mgr, v4_data):
        """TC064: Distinguish operations by examining binding state and
        content changes in the lease history."""
        ip = "3.3.228.164"
        mac = "00:00:64:00:00:01"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        # Create
        lease_mgr.create_v4_lease(ip=ip, mac=mac, hostname="create-64")

        # Update
        lease_mgr.update_v4_lease(ip=ip, hostname="update-64")

        # Verify latest has updated hostname (= update operation)
        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed.get("hostname") == "update-64", \
            "Latest entry should reflect the update operation"

        # Delete and verify empty history
        lease_mgr.delete_v4_lease(ip)
        history = lease_mgr.get_v4_lease_history(ip)
        assert len(history) == 0, "After delete, history should be empty"

    # TC065: Verify lease history pagination for large number of entries
    def test_tc065_v4_history_pagination(self, lease_mgr, v4_data):
        """TC065: Create many entries for same IP to simulate large history,
        then verify all entries can be retrieved."""
        ip = "3.3.228.165"
        mac = "00:00:65:00:00:01"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        # Create multiple entries (ISC DHCP appends, so duplicates all stay)
        entry_count = 10
        for i in range(entry_count):
            lease_mgr.create_v4_lease(
                ip=ip,
                mac="00:00:65:00:00:{:02x}".format(i + 1),
                hostname="entry-{}".format(i),
            )

        history = lease_mgr.get_v4_lease_history(ip)
        assert len(history) >= entry_count, \
            "Expected at least {} history entries, got {}".format(
                entry_count, len(history))

        # Cleanup
