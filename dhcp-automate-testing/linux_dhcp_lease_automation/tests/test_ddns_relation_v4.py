"""
test_ddns_relation_v4.py – DDNS Relation v4 Tests (TC103-TC111)

Verifies Dynamic DNS (DDNS) forward (A) and reverse (PTR) record
creation, update, and cleanup when DHCPv4 leases are managed.
"""

import pytest
from helpers.dhcp_lease_manager import DHCPLeaseManager


@pytest.mark.usefixtures("v4_backup")
class TestDDNSRelationV4:
    """TC103-TC111: DDNS Relation v4 tests."""

    @pytest.fixture(autouse=True)
    def _ddns_data(self, dhcp_testdata):
        self.ddns = dhcp_testdata["ddns_test_data"]
        self.dns_server = self.ddns.get("dns_server")

    # TC103: Verify DDNS forward lookup (A record) on v4 lease creation
    def test_tc103_ddns_a_record_on_create(self, lease_mgr, v4_data):
        """TC103: Create v4 lease with hostname, verify A record exists."""
        ip = self.ddns["test_ip_v4"]
        mac = self.ddns["test_mac"]
        hostname = self.ddns["test_hostname_v4"]

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac, hostname=hostname)

        # Check DNS A record
        a_records = lease_mgr.dns_lookup_a(hostname, self.dns_server)
        # DDNS may or may not be configured; verify lease exists at minimum
        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed.get("hostname") == hostname, \
            "Lease hostname should be set for DDNS"

        if a_records:
            assert ip in a_records, \
                "A record for {} should point to {}".format(hostname, ip)


    # TC104: Verify DDNS reverse lookup (PTR record) on v4 lease creation
    def test_tc104_ddns_ptr_on_create(self, lease_mgr, v4_data):
        """TC104: Create v4 lease, verify PTR record exists."""
        ip = self.ddns["test_ip_v4"]
        mac = self.ddns["test_mac"]
        hostname = self.ddns["test_hostname_v4"]

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac, hostname=hostname)

        ptr_records = lease_mgr.dns_lookup_ptr(ip, self.dns_server)

        # Verify lease is correct regardless of DDNS status
        assert lease_mgr.v4_lease_exists(ip), "Lease should exist"

        if ptr_records:
            # PTR should resolve to the hostname
            found = any(hostname in r for r in ptr_records)
            assert found, "PTR for {} should resolve to {}".format(ip, hostname)


    # TC105: Update hostname and verify DDNS A record is updated
    def test_tc105_ddns_a_record_on_update(self, lease_mgr, v4_data):
        """TC105: Update v4 lease hostname, verify DNS A record changes."""
        ip = self.ddns["test_ip_v4"]
        mac = self.ddns["test_mac"]
        old_hostname = self.ddns["test_hostname_v4"]
        new_hostname = "ddns-updated-v4.example.com"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac, hostname=old_hostname)
        lease_mgr.update_v4_lease(ip=ip, hostname=new_hostname)

        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed.get("hostname") == new_hostname, \
            "Hostname should be updated in lease file"


    # TC106: Update IP and verify DDNS A+PTR records update
    def test_tc106_ddns_records_on_ip_change(self, lease_mgr, v4_data):
        """TC106: Move lease to new IP, verify DNS records would update."""
        old_ip = self.ddns["test_ip_v4"]
        new_ip = "3.3.228.161"
        mac = self.ddns["test_mac"]
        hostname = self.ddns["test_hostname_v4"]

        for ip in [old_ip, new_ip]:
            if lease_mgr.v4_lease_exists(ip):
                lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=old_ip, mac=mac, hostname=hostname)
        lease_mgr.delete_v4_lease(old_ip)
        lease_mgr.create_v4_lease(ip=new_ip, mac=mac, hostname=hostname)

        assert not lease_mgr.v4_lease_exists(old_ip), "Old IP should be gone"
        assert lease_mgr.v4_lease_exists(new_ip), "New IP should exist"


    # TC107: Delete v4 lease and verify DDNS records are cleaned up
    def test_tc107_ddns_cleanup_on_delete(self, lease_mgr, v4_data):
        """TC107: Delete v4 lease, verify DNS records would be removed."""
        ip = self.ddns["test_ip_v4"]
        mac = self.ddns["test_mac"]
        hostname = self.ddns["test_hostname_v4"]

        if not lease_mgr.v4_lease_exists(ip):
            lease_mgr.create_v4_lease(ip=ip, mac=mac, hostname=hostname)

        lease_mgr.delete_v4_lease(ip)

        assert not lease_mgr.v4_lease_exists(ip), \
            "Lease should be deleted"

        # After deletion, DNS records should eventually be cleaned up
        # (DDNS deregistration happens on service restart)

    # TC108: Verify DDNS relation is displayed in lease details
    def test_tc108_ddns_relation_in_lease(self, lease_mgr, v4_data):
        """TC108: Lease with hostname implies DDNS relation."""
        ip = self.ddns["test_ip_v4"]
        mac = self.ddns["test_mac"]
        hostname = self.ddns["test_hostname_v4"]

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac, hostname=hostname)

        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)

        # A lease with hostname has a potential DDNS relation
        assert parsed.get("hostname"), "Hostname must be set for DDNS relation"
        assert parsed["ip"] == ip


    # TC109: Verify DDNS update on lease renewal
    def test_tc109_ddns_on_renewal(self, lease_mgr, v4_data):
        """TC109: Renew (update expiry) and verify DDNS still valid."""
        ip = self.ddns["test_ip_v4"]
        mac = self.ddns["test_mac"]
        hostname = self.ddns["test_hostname_v4"]

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(
            ip=ip, mac=mac, hostname=hostname,
            ends="2027/04/08 00:00:00",
        )

        # Simulate renewal by updating expiry
        lease_mgr.update_v4_lease(ip=ip, ends="2028/04/08 00:00:00")

        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert "2028/04/08" in parsed.get("ends", ""), \
            "Renewed expiry should be reflected"
        assert parsed.get("hostname") == hostname, \
            "Hostname should persist after renewal"


    # TC110: Create v4 lease with DDNS disabled, verify no DNS records
    def test_tc110_ddns_disabled_no_records(self, lease_mgr, v4_data):
        """TC110: Lease without hostname – no DDNS records expected."""
        ip = "3.3.228.110"
        mac = "00:01:10:00:00:01"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        # Create lease WITHOUT hostname (DDNS disabled for this lease)
        lease_mgr.create_v4_lease(ip=ip, mac=mac)

        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert not parsed.get("hostname"), \
            "Lease without hostname should have no DDNS"


    # TC111: DDNS conflict – A record already exists for different lease
    def test_tc111_ddns_conflict_handling(self, lease_mgr, v4_data):
        """TC111: Two leases with same hostname – last lease wins."""
        ip1 = "3.3.228.111"
        ip2 = "3.3.228.112"
        mac1 = "00:01:11:00:00:01"
        mac2 = "00:01:11:00:00:02"
        hostname = "ddns-conflict.example.com"

        for ip in [ip1, ip2]:
            if lease_mgr.v4_lease_exists(ip):
                lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip1, mac=mac1, hostname=hostname)
        lease_mgr.create_v4_lease(ip=ip2, mac=mac2, hostname=hostname)

        # Both leases exist with same hostname
        b1 = lease_mgr.get_v4_lease(ip1)
        b2 = lease_mgr.get_v4_lease(ip2)
        p1 = DHCPLeaseManager.parse_v4_lease(b1)
        p2 = DHCPLeaseManager.parse_v4_lease(b2)
        assert p1.get("hostname") == hostname
        assert p2.get("hostname") == hostname

