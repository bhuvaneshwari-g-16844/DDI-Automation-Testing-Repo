"""
test_delete_lease_v6.py – DHCPv6 Lease Deletion Tests (TC049-TC056)

Deletes v6 leases by removing entries from /usr/local/dhcpd/var/lib/dhcpd6.leases.
"""

import pytest
from helpers.dhcp_lease_manager import DHCPLeaseManager


@pytest.mark.usefixtures("v6_backup")
class TestDeleteLeaseV6:
    """TC049-TC056: Delete DHCPv6 Lease tests."""

    # TC049: Delete a single DHCPv6 lease
    def test_tc049_delete_v6_single(self, lease_mgr, v6_data):
        """TC049: Delete a single DHCPv6 lease from the prefix."""
        ip = "1000::e001"
        duid = "\\001\\000\\000\\049"

        if not lease_mgr.v6_lease_exists(ip):
            lease_mgr.create_v6_lease(ip=ip, duid=duid)

        assert lease_mgr.v6_lease_exists(ip), "Pre-condition: v6 lease must exist"

        result = lease_mgr.delete_v6_lease(ip)
        assert result, "delete_v6_lease returned False"
        assert not lease_mgr.v6_lease_exists(ip), \
            "v6 lease {} still exists after deletion".format(ip)

    # TC050: Delete multiple DHCPv6 leases in batch
    def test_tc050_delete_v6_batch(self, lease_mgr):
        """TC050: Delete multiple v6 leases in batch."""
        batch = [
            {"ip": "1000::e010", "duid": "\\001\\000\\050\\001"},
            {"ip": "1000::e011", "duid": "\\001\\000\\050\\002"},
            {"ip": "1000::e012", "duid": "\\001\\000\\050\\003"},
        ]

        for l in batch:
            if not lease_mgr.v6_lease_exists(l["ip"]):
                lease_mgr.create_v6_lease(ip=l["ip"], duid=l["duid"])

        for l in batch:
            lease_mgr.delete_v6_lease(l["ip"])

        for l in batch:
            assert not lease_mgr.v6_lease_exists(l["ip"]), \
                "v6 batch lease {} still exists".format(l["ip"])

    # TC051: Delete all DHCPv6 leases from prefix
    def test_tc051_delete_v6_all_in_prefix(self, lease_mgr):
        """TC051: Delete all test v6 leases."""
        test_ips = ["1000::e020", "1000::e021", "1000::e022"]
        for i, ip in enumerate(test_ips):
            if not lease_mgr.v6_lease_exists(ip):
                lease_mgr.create_v6_lease(
                    ip=ip, duid="\\001\\000\\051\\{:03d}".format(i))

        for ip in test_ips:
            lease_mgr.delete_v6_lease(ip)

        for ip in test_ips:
            assert not lease_mgr.v6_lease_exists(ip)

    # TC052: Delete v6 lease and verify IPv6 released
    def test_tc052_delete_v6_ip_released(self, lease_mgr):
        """TC052: Delete lease and verify IPv6 can be reused."""
        ip = "1000::e030"
        duid1 = "\\001\\000\\052\\001"
        duid2 = "\\001\\000\\052\\002"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid1)
        lease_mgr.delete_v6_lease(ip)
        assert not lease_mgr.v6_lease_exists(ip)

        # Reuse
        lease_mgr.create_v6_lease(ip=ip, duid=duid2)
        assert lease_mgr.v6_lease_exists(ip), "IPv6 should be reusable"

        lease_mgr.delete_v6_lease(ip)

    # TC053: Verify deletion happens
    def test_tc053_delete_v6_confirm(self, lease_mgr):
        """TC053: Verify v6 lease is actually removed from file."""
        ip = "1000::e040"
        duid = "\\001\\000\\053"

        if not lease_mgr.v6_lease_exists(ip):
            lease_mgr.create_v6_lease(ip=ip, duid=duid)

        count_before = lease_mgr.count_v6_leases()
        lease_mgr.delete_v6_lease(ip)
        count_after = lease_mgr.count_v6_leases()

        assert count_after < count_before, \
            "v6 count should decrease: before={}, after={}".format(
                count_before, count_after)

    # TC054: Cancel deletion (no-op)
    def test_tc054_cancel_delete_v6(self, lease_mgr):
        """TC054: Verify v6 lease still exists when NOT deleted."""
        ip = "1000::e050"
        duid = "\\001\\000\\054"

        if not lease_mgr.v6_lease_exists(ip):
            lease_mgr.create_v6_lease(ip=ip, duid=duid)

        # Do NOT delete
        assert lease_mgr.v6_lease_exists(ip), "v6 lease should still exist"

        lease_mgr.delete_v6_lease(ip)

    # TC055: Delete v6 lease and verify removed from list
    def test_tc055_delete_v6_verify_removed(self, lease_mgr):
        """TC055: Delete v6 lease and verify removed from lease list."""
        ip = "1000::e060"
        duid = "\\001\\000\\055"

        if not lease_mgr.v6_lease_exists(ip):
            lease_mgr.create_v6_lease(ip=ip, duid=duid)

        all_before = lease_mgr.get_all_v6_leases()
        found_before = [l for l in all_before if ip in l]
        assert len(found_before) >= 1

        lease_mgr.delete_v6_lease(ip)

        all_after = lease_mgr.get_all_v6_leases()
        found_after = [l for l in all_after if ip in l]
        assert len(found_after) == 0, "v6 lease should not be in list after delete"

    # TC056: Delete non-existent v6 lease
    def test_tc056_delete_v6_nonexistent(self, lease_mgr):
        """TC056: Delete a non-existent v6 lease – should return False."""
        fake_ip = "ffff::dead:beef"
        assert not lease_mgr.v6_lease_exists(fake_ip)

        result = lease_mgr.delete_v6_lease(fake_ip)
        assert not result, "Deleting non-existent v6 lease should return False"
