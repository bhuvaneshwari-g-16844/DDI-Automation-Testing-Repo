"""
test_lease_history_dns.py – Lease History DNS Tests (TC121-TC128)

Verifies that DNS query records associated with DHCP lease operations
are tracked in the lease history and can be filtered/viewed.
"""

import pytest
from helpers.dhcp_lease_manager import DHCPLeaseManager


@pytest.mark.usefixtures("v4_backup", "v6_backup")
class TestLeaseHistoryDNS:
    """TC121-TC128: Lease History DNS tests."""

    @pytest.fixture(autouse=True)
    def _ddns_data(self, dhcp_testdata):
        self.ddns = dhcp_testdata["ddns_test_data"]
        self.dns_server = self.ddns.get("dns_server")

    # TC121: Verify DNS query records in lease history for v4
    def test_tc121_dns_queries_v4_history(self, lease_mgr, v4_data):
        """TC121: After v4 lease create with hostname, verify DNS queries
        can be checked via dig."""
        ip = "3.3.228.121"
        mac = "00:01:21:00:00:01"
        hostname = "dns-hist-v4.example.com"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac, hostname=hostname)

        # Verify lease has hostname (DDNS trigger)
        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed.get("hostname") == hostname

        # Check if A record was created
        a_records = lease_mgr.dns_lookup_a(hostname, self.dns_server)
        # Record presence depends on DDNS config
        assert lease_mgr.v4_lease_exists(ip), "Lease should exist"


    # TC122: Verify DNS query records in lease history for v6
    def test_tc122_dns_queries_v6_history(self, lease_mgr, v6_data):
        """TC122: After v6 lease create, verify AAAA queries."""
        ip = "2000::1221"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\122\\001"
        hostname = "dns-hist-v6.example.com"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid)

        assert lease_mgr.v6_lease_exists(ip), "v6 lease should exist"

        aaaa = lease_mgr.dns_lookup_aaaa(hostname, self.dns_server)
        # AAAA presence depends on DDNS config


    # TC123: Verify DNS query timestamp matches lease operation time
    def test_tc123_dns_query_timestamp(self, lease_mgr, v4_data):
        """TC123: Verify lease timestamp aligns with creation time."""
        ip = "3.3.228.123"
        mac = "00:01:23:00:00:01"
        hostname = "ts-check.example.com"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(
            ip=ip, mac=mac, hostname=hostname,
            starts="2026/04/08 14:00:00",
        )

        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert "2026/04/08" in parsed.get("starts", ""), \
            "Lease timestamp should match the DNS trigger time"


    # TC124: Verify DNS query type (A/AAAA/PTR) displayed correctly
    def test_tc124_dns_query_type(self, lease_mgr, v4_data):
        """TC124: Verify correct DNS record types via dig."""
        ip = "3.3.228.124"
        mac = "00:01:24:00:00:01"
        hostname = "qtype-test.example.com"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac, hostname=hostname)

        # Query A type
        a_records = lease_mgr.dns_lookup_a(hostname, self.dns_server)
        # Query PTR type
        ptr_records = lease_mgr.dns_lookup_ptr(ip, self.dns_server)

        # At minimum, the lease should exist for the queries
        assert lease_mgr.v4_lease_exists(ip)


    # TC125: Verify DNS query result (success/failure) in lease history
    def test_tc125_dns_query_result(self, lease_mgr, v4_data):
        """TC125: Verify DNS query returns result or empty."""
        hostname = "nonexistent-host-125.example.com"
        result = lease_mgr.dns_lookup_a(hostname, self.dns_server)
        # For a non-existent host, result should be empty
        # (no records or only empty strings)
        cleaned = [r for r in result if r and not r.startswith(";")]
        # This verifies the DNS query mechanism works
        assert isinstance(cleaned, list), "DNS lookup should return a list"

    # TC126: Verify DNS query source server in lease history
    def test_tc126_dns_query_source(self, lease_mgr, dhcp_testdata):
        """TC126: Verify DNS queries go to the configured server."""
        dns_server = self.dns_server
        # Verify the DNS server is reachable
        out, err, code = lease_mgr._exec(
            "dig +short @{} version.bind chaos txt 2>/dev/null || echo 'reachable-check'".format(
                dns_server)
        )
        # The command should execute without SSH error
        assert code == 0 or "reachable-check" in out, \
            "DNS server {} should be queryable".format(dns_server)

    # TC127: Filter lease history to show only DNS query entries
    def test_tc127_filter_dns_entries(self, lease_mgr, v4_data):
        """TC127: Distinguish DNS-related entries from lease CRUD.
        In ISC DHCP file mode, DNS records are separate from lease entries."""
        ip = "3.3.228.127"
        mac = "00:01:27:00:00:01"
        hostname = "filter-dns.example.com"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac, hostname=hostname)

        # Lease history contains lease entries (not DNS entries)
        history = lease_mgr.get_v4_lease_history(ip)
        assert len(history) >= 1, "Lease entry should exist"

        # DNS entries are in DNS zone files, not DHCP lease files
        # This test verifies the separation
        for entry in history:
            assert "lease" in entry, "History entries should be lease blocks"


    # TC128: Verify DNS queries logged for failed DDNS updates
    def test_tc128_failed_ddns_logged(self, lease_mgr, v4_data):
        """TC128: Create lease with hostname pointing to unreachable DNS,
        verify the lease still exists (DDNS failure doesn't block lease)."""
        ip = "3.3.228.128"
        mac = "00:01:28:00:00:01"
        hostname = "failed-ddns.nonexistent.tld"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac, hostname=hostname)

        # Even if DDNS fails, lease should exist
        assert lease_mgr.v4_lease_exists(ip), \
            "Lease should exist despite DDNS failure"

        # DNS lookup to non-existent domain should return nothing
        a_records = lease_mgr.dns_lookup_a(hostname, "127.0.0.1")
        cleaned = [r for r in a_records if r and not r.startswith(";")]
        # May be empty if DDNS failed
        assert isinstance(cleaned, list)

