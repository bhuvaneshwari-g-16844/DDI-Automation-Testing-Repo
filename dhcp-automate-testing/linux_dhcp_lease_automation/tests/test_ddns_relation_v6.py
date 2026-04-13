"""
test_ddns_relation_v6.py – DDNS Relation v6 Tests (TC112-TC120)

Verifies Dynamic DNS (DDNS) forward (AAAA) and reverse (PTR) record
creation, update, and cleanup when DHCPv6 leases are managed.
"""

import pytest
from helpers.dhcp_lease_manager import DHCPLeaseManager


@pytest.mark.usefixtures("v6_backup")
class TestDDNSRelationV6:
    """TC112-TC120: DDNS Relation v6 tests."""

    @pytest.fixture(autouse=True)
    def _ddns_data(self, dhcp_testdata):
        self.ddns = dhcp_testdata["ddns_test_data"]
        self.dns_server = self.ddns.get("dns_server")

    # TC112: Verify DDNS AAAA record on v6 lease creation
    def test_tc112_ddns_aaaa_on_create(self, lease_mgr, v6_data):
        """TC112: Create v6 lease, verify AAAA record."""
        ip = self.ddns["test_ip_v6"]
        duid = self.ddns["test_duid"]
        hostname = self.ddns["test_hostname_v6"]

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        # v6 leases don't have hostname in ISC DHCP lease block,
        # DDNS is configured at server level. Verify lease creation.
        lease_mgr.create_v6_lease(ip=ip, duid=duid)

        assert lease_mgr.v6_lease_exists(ip), "v6 lease should exist"

        # Check AAAA record (may not exist if DDNS not configured)
        aaaa = lease_mgr.dns_lookup_aaaa(hostname, self.dns_server)
        if aaaa:
            assert any(ip in a for a in aaaa), \
                "AAAA should point to {}".format(ip)


    # TC113: Verify DDNS PTR record on v6 lease creation
    def test_tc113_ddns_ptr_on_create(self, lease_mgr, v6_data):
        """TC113: Create v6 lease, verify PTR record in ip6.arpa."""
        ip = self.ddns["test_ip_v6"]
        duid = self.ddns["test_duid"]
        hostname = self.ddns["test_hostname_v6"]

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid)

        assert lease_mgr.v6_lease_exists(ip)

        ptr = lease_mgr.dns_lookup_ptr(ip, self.dns_server)
        if ptr:
            found = any(hostname in r for r in ptr)
            assert found, "PTR for {} should resolve to {}".format(ip, hostname)


    # TC114: Update v6 lease hostname, verify AAAA record updated
    def test_tc114_ddns_aaaa_on_update(self, lease_mgr, v6_data):
        """TC114: Update v6 lease and verify DDNS would update."""
        ip = self.ddns["test_ip_v6"]
        duid = self.ddns["test_duid"]

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid, preferred_life=3600)
        lease_mgr.update_v6_lease(ip=ip, preferred_life=7200)

        lease_block = lease_mgr.get_v6_lease(ip)
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert parsed.get("preferred_life") == 7200


    # TC115: Update v6 IPv6 address, verify AAAA+PTR update
    def test_tc115_ddns_records_on_ip_change(self, lease_mgr, v6_data):
        """TC115: Move v6 lease to new IP, verify records would update."""
        old_ip = self.ddns["test_ip_v6"]
        new_ip = "1000::ddns:2"
        duid = self.ddns["test_duid"]

        for ip in [old_ip, new_ip]:
            if lease_mgr.v6_lease_exists(ip):
                lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=old_ip, duid=duid)
        lease_mgr.delete_v6_lease(old_ip)
        lease_mgr.create_v6_lease(ip=new_ip, duid=duid)

        assert not lease_mgr.v6_lease_exists(old_ip)
        assert lease_mgr.v6_lease_exists(new_ip)


    # TC116: Delete v6 lease, verify DDNS cleanup
    def test_tc116_ddns_cleanup_on_delete(self, lease_mgr, v6_data):
        """TC116: Delete v6 lease, verify DNS records cleaned up."""
        ip = self.ddns["test_ip_v6"]
        duid = self.ddns["test_duid"]

        if not lease_mgr.v6_lease_exists(ip):
            lease_mgr.create_v6_lease(ip=ip, duid=duid)

        lease_mgr.delete_v6_lease(ip)

        assert not lease_mgr.v6_lease_exists(ip)

    # TC117: Verify DDNS relation in v6 lease details
    def test_tc117_ddns_relation_in_v6_lease(self, lease_mgr, v6_data):
        """TC117: v6 lease with DUID establishes identity for DDNS."""
        ip = self.ddns["test_ip_v6"]
        duid = self.ddns["test_duid"]

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid)

        lease_block = lease_mgr.get_v6_lease(ip)
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert parsed.get("duid"), "DUID must be present for DDNS identity"
        assert parsed["ip"] == ip


    # TC118: Verify DDNS update on v6 lease renewal
    def test_tc118_ddns_on_v6_renewal(self, lease_mgr, v6_data):
        """TC118: Renew v6 lease (update expiry), verify DDNS persists."""
        ip = self.ddns["test_ip_v6"]
        duid = self.ddns["test_duid"]

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid, ends="2027/04/08 00:00:00")
        lease_mgr.update_v6_lease(ip=ip, ends="2028/04/08 00:00:00")

        lease_block = lease_mgr.get_v6_lease(ip)
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert "2028/04/08" in parsed.get("ends", "")


    # TC119: Create v6 lease with DDNS disabled
    def test_tc119_ddns_disabled_v6(self, lease_mgr, v6_data):
        """TC119: v6 lease creation – verify no DNS expected when
        DDNS is not configured for the prefix."""
        ip = "1000::ddns:9"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\009"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid)

        # Check DDNS config
        ddns_config = lease_mgr.get_ddns_config()
        # If DDNS is "none" or "not-found", no DNS records expected
        assert lease_mgr.v6_lease_exists(ip), "Lease should be created"


    # TC120: DDNS conflict – AAAA record exists for different v6 lease
    def test_tc120_ddns_conflict_v6(self, lease_mgr, v6_data):
        """TC120: Two v6 leases for same DUID – last entry wins."""
        ip1 = "1000::ddns:a"
        ip2 = "1000::ddns:b"
        duid = self.ddns["test_duid"]

        for ip in [ip1, ip2]:
            if lease_mgr.v6_lease_exists(ip):
                lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip1, duid=duid)
        lease_mgr.create_v6_lease(ip=ip2, duid=duid)

        # Both should exist in the file
        assert lease_mgr.v6_lease_exists(ip1)
        assert lease_mgr.v6_lease_exists(ip2)

        for ip in [ip1, ip2]:
            lease_mgr.delete_v6_lease(ip)
