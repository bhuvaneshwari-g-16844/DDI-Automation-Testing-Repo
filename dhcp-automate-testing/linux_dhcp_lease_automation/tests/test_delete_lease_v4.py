"""
test_delete_lease_v4.py – DHCPv4 Lease Deletion Tests (TC041-TC048)

Deletes v4 leases by removing entries from /usr/local/dhcpd/var/lib/dhcpd.leases.
"""

import pytest
from helpers.dhcp_lease_manager import DHCPLeaseManager


@pytest.mark.usefixtures("v4_backup")
class TestDeleteLeaseV4:
    """TC041-TC048: Delete DHCPv4 Lease tests."""

    # TC041: Delete a single DHCPv4 lease
    def test_tc041_delete_v4_single(self, lease_mgr, v4_data):
        """TC041: Delete a single DHCPv4 lease from the scope."""
        ip = "2.2.228.180"
        mac = "00:00:41:00:00:01"

        # Setup: create a lease to delete
        if not lease_mgr.v4_lease_exists(ip):
            lease_mgr.create_v4_lease(ip=ip, mac=mac)

        assert lease_mgr.v4_lease_exists(ip), "Pre-condition: lease must exist"

        # Delete
        result = lease_mgr.delete_v4_lease(ip)
        assert result, "delete_v4_lease returned False – nothing removed"

        # Verify removed
        assert not lease_mgr.v4_lease_exists(ip), \
            "Lease {} still exists after deletion".format(ip)

    # TC042: Delete multiple DHCPv4 leases in batch
    def test_tc042_delete_v4_batch(self, lease_mgr):
        """TC042: Delete multiple leases in batch."""
        batch_ips = ["2.2.228.181", "2.2.228.182", "2.2.228.183"]

        # Setup: create leases
        for i, ip in enumerate(batch_ips):
            if not lease_mgr.v4_lease_exists(ip):
                lease_mgr.create_v4_lease(
                    ip=ip, mac="00:00:42:00:00:{:02x}".format(i + 1))

        # Delete all
        for ip in batch_ips:
            lease_mgr.delete_v4_lease(ip)

        # Verify all removed
        for ip in batch_ips:
            assert not lease_mgr.v4_lease_exists(ip), \
                "Batch lease {} still exists after deletion".format(ip)

    # TC043: Delete all DHCPv4 leases from a scope
    def test_tc043_delete_v4_all_in_scope(self, lease_mgr):
        """TC043: Delete all leases from scope (2.2.228.x)."""
        # Create a few test leases
        test_ips = ["2.2.228.190", "2.2.228.191", "2.2.228.192"]
        for i, ip in enumerate(test_ips):
            if not lease_mgr.v4_lease_exists(ip):
                lease_mgr.create_v4_lease(
                    ip=ip, mac="00:00:43:00:00:{:02x}".format(i + 1))

        # Delete each one
        for ip in test_ips:
            lease_mgr.delete_v4_lease(ip)

        # Verify
        for ip in test_ips:
            assert not lease_mgr.v4_lease_exists(ip), \
                "Lease {} should be deleted".format(ip)

    # TC044: Delete lease and verify IP is released
    def test_tc044_delete_v4_ip_released(self, lease_mgr):
        """TC044: Delete lease and verify IP can be reused."""
        ip = "2.2.228.193"
        mac1 = "00:00:44:00:00:01"
        mac2 = "00:00:44:00:00:02"

        # Create, delete, recreate with different MAC
        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac1)
        lease_mgr.delete_v4_lease(ip)
        assert not lease_mgr.v4_lease_exists(ip), "IP not released"

        # Reuse the IP
        lease_mgr.create_v4_lease(ip=ip, mac=mac2)
        assert lease_mgr.v4_lease_exists(ip), "IP should be reusable"

        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed["mac"] == mac2, "New MAC not assigned after reuse"

        lease_mgr.delete_v4_lease(ip)

    # TC045: Verify deletion happens (no UI confirmation in file mode)
    def test_tc045_delete_v4_confirm(self, lease_mgr):
        """TC045: Verify lease is actually removed from file."""
        ip = "2.2.228.194"
        mac = "00:00:45:00:00:01"

        if not lease_mgr.v4_lease_exists(ip):
            lease_mgr.create_v4_lease(ip=ip, mac=mac)

        count_before = lease_mgr.count_v4_leases()
        lease_mgr.delete_v4_lease(ip)
        count_after = lease_mgr.count_v4_leases()

        assert count_after < count_before, \
            "Lease count should decrease: before={}, after={}".format(
                count_before, count_after)

    # TC046: Cancel deletion (skip – file-based, no cancel dialog)
    def test_tc046_cancel_delete_v4(self, lease_mgr):
        """TC046: Verify lease still exists when NOT deleted (no-op test)."""
        ip = "2.2.228.195"
        mac = "00:00:46:00:00:01"

        if not lease_mgr.v4_lease_exists(ip):
            lease_mgr.create_v4_lease(ip=ip, mac=mac)

        # Do NOT delete – just verify it still exists
        assert lease_mgr.v4_lease_exists(ip), "Lease should still exist"

        lease_mgr.delete_v4_lease(ip)

    # TC047: Delete lease and verify count decreased
    def test_tc047_delete_v4_verify_removed(self, lease_mgr):
        """TC047: Delete lease and verify it is removed from list."""
        ip = "2.2.228.196"
        mac = "00:00:47:00:00:01"

        if not lease_mgr.v4_lease_exists(ip):
            lease_mgr.create_v4_lease(ip=ip, mac=mac)

        all_before = lease_mgr.get_all_v4_leases()
        ips_before = [l for l in all_before if ip in l]
        assert len(ips_before) >= 1, "Lease should be in list before delete"

        lease_mgr.delete_v4_lease(ip)

        all_after = lease_mgr.get_all_v4_leases()
        ips_after = [l for l in all_after if ip in l]
        assert len(ips_after) == 0, "Lease should NOT be in list after delete"

    # TC048: Attempt to delete non-existent lease
    def test_tc048_delete_v4_nonexistent(self, lease_mgr):
        """TC048: Delete a non-existent lease – should return False."""
        fake_ip = "99.99.99.99"
        assert not lease_mgr.v4_lease_exists(fake_ip), \
            "Pre-condition: IP should not exist"

        result = lease_mgr.delete_v4_lease(fake_ip)
        assert not result, "Deleting non-existent lease should return False"
