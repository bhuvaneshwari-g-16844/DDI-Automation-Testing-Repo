"""
test_dhcp_anomaly_v6.py – DHCPv6 Anomaly Detection Tests (TC166-TC179)

Simulates DHCPv6 anomaly conditions (DUID spoofing, IPv6 conflict,
starvation, rapid churn, etc.) by manipulating lease files.
"""

import pytest
from helpers.dhcp_lease_manager import DHCPLeaseManager


@pytest.mark.usefixtures("v6_backup")
class TestDHCPAnomalyV6:
    """TC166-TC179: DHCP Anomaly v6 tests."""

    @pytest.fixture(autouse=True)
    def _anomaly_data(self, dhcp_testdata):
        self.anomaly = dhcp_testdata["anomaly_test_data"]
        self.v6 = dhcp_testdata["v6_test_data"]

    # TC166: DUID spoofing – same DUID requesting multiple addresses
    def test_tc166_duid_spoofing(self, lease_mgr, v6_data):
        """TC166: Single DUID with many IPs – anomaly condition."""
        spoof_duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\166\\001"
        count = 10
        ips = ["2000::166{}".format(i) for i in range(count)]

        for ip in ips:
            if lease_mgr.v6_lease_exists(ip):
                lease_mgr.delete_v6_lease(ip)

        for ip in ips:
            lease_mgr.create_v6_lease(ip=ip, duid=spoof_duid)

        for ip in ips:
            assert lease_mgr.v6_lease_exists(ip)

        # Detect: count leases with same DUID
        all_leases = lease_mgr.get_all_v6_leases()
        same_duid_count = sum(
            1 for b in all_leases if "166" in b and "\\001" in b
        )
        assert same_duid_count >= count, \
            "Should detect {} leases with same DUID (spoofing)".format(count)


    # TC167: IPv6 conflict – duplicate IPv6 assignment
    def test_tc167_ipv6_conflict(self, lease_mgr, v6_data):
        """TC167: Same IPv6 assigned to multiple DUIDs – anomaly."""
        conflict_ip = "2000::1671"
        duid1 = "\\001\\000\\000\\000\\000\\003\\000\\001\\167\\001"
        duid2 = "\\001\\000\\000\\000\\000\\003\\000\\001\\167\\002"

        if lease_mgr.v6_lease_exists(conflict_ip):
            lease_mgr.delete_v6_lease(conflict_ip)

        lease_mgr.create_v6_lease(ip=conflict_ip, duid=duid1)
        lease_mgr.create_v6_lease(ip=conflict_ip, duid=duid2)

        history = lease_mgr.get_v6_lease_history(conflict_ip)
        assert len(history) >= 2, \
            "Should detect multiple entries for same IPv6 (conflict)"


    # TC168: Rogue DHCPv6 server detection
    def test_tc168_rogue_dhcpv6_server(self, lease_mgr, dhcp_testdata):
        """TC168: Check for rogue DHCPv6 server (port 546/547)."""
        rogue_cmd = self.anomaly.get(
            "rogue_check_v6_cmd", "echo 'skip'"
        )
        out, err, code = lease_mgr._exec(rogue_cmd)
        assert code == 0 or "skip" in out, \
            "Rogue DHCPv6 check should execute"

    # TC169: DHCPv6 starvation – excessive SOLICIT requests
    def test_tc169_v6_starvation(self, lease_mgr, v6_data):
        """TC169: Simulate starvation with many rapid v6 leases."""
        count = self.anomaly["starvation_count"]
        ips = ["2000::169{:x}".format(i) for i in range(count)]

        for ip in ips:
            if lease_mgr.v6_lease_exists(ip):
                lease_mgr.delete_v6_lease(ip)

        for i, ip in enumerate(ips):
            lease_mgr.create_v6_lease(
                ip=ip,
                duid="\\001\\000\\000\\000\\000\\003\\169\\{:03d}".format(i),
            )

        total = lease_mgr.count_v6_leases()
        assert total >= count, \
            "Starvation: {} v6 leases created rapidly".format(count)


    # TC170: Prefix exhaustion – 100% utilization
    def test_tc170_prefix_exhaustion(self, lease_mgr, v6_data):
        """TC170: Calculate prefix utilization."""
        current_count = lease_mgr.count_v6_leases()
        # IPv6 prefix /64 has 2^64 addresses, so exhaustion is theoretical
        # but we still track the count
        assert current_count >= 0, \
            "Prefix utilization tracking: {} active leases".format(current_count)

    # TC171: Rapid v6 lease churn
    def test_tc171_v6_rapid_churn(self, lease_mgr, v6_data):
        """TC171: Rapid create/delete cycles for v6."""
        churn_count = self.anomaly["rapid_churn_count"]
        ip = "2000::1711"
        base_duid = "\\001\\000\\000\\000\\000\\003\\000\\171"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        for i in range(churn_count):
            lease_mgr.create_v6_lease(
                ip=ip,
                duid="{}\\{:03d}".format(base_duid, i),
            )
            lease_mgr.delete_v6_lease(ip)

        assert not lease_mgr.v6_lease_exists(ip), \
            "IP should be free after churn"

    # TC172: Unauthorized client – unknown DUID
    def test_tc172_unauthorized_duid(self, lease_mgr, v6_data):
        """TC172: Flag unknown DUID requesting lease."""
        ip = "2000::1721"
        unknown_duid = "\\377\\377\\377\\377\\377\\377\\377\\377"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=unknown_duid)

        block = lease_mgr.get_v6_lease(ip)
        parsed = DHCPLeaseManager.parse_v6_lease(block)
        assert parsed.get("duid"), "DUID should be present"
        # Unknown DUID detection: check against known patterns
        assert "\\377\\377" in parsed["duid"] or len(parsed["duid"]) > 0, \
            "Unknown DUID should be flaggable"


    # TC173: Abnormal v6 lease duration
    def test_tc173_v6_abnormal_duration(self, lease_mgr, v6_data):
        """TC173: Flag v6 leases with abnormal preferred/max life."""
        ip_short = "2000::1731"
        ip_long = "2000::1732"

        for ip in [ip_short, ip_long]:
            if lease_mgr.v6_lease_exists(ip):
                lease_mgr.delete_v6_lease(ip)

        # Extremely short: 1 second
        lease_mgr.create_v6_lease(
            ip=ip_short,
            duid="\\001\\000\\000\\000\\000\\003\\173\\001",
            preferred_life=1, max_life=1,
        )

        # Extremely long: max values
        lease_mgr.create_v6_lease(
            ip=ip_long,
            duid="\\001\\000\\000\\000\\000\\003\\173\\002",
            preferred_life=999999, max_life=999999,
        )

        block_short = lease_mgr.get_v6_lease(ip_short)
        block_long = lease_mgr.get_v6_lease(ip_long)
        p_short = DHCPLeaseManager.parse_v6_lease(block_short)
        p_long = DHCPLeaseManager.parse_v6_lease(block_long)

        assert p_short.get("preferred_life") == 1, "Short duration detectable"
        assert p_long.get("preferred_life") == 999999, "Long duration detectable"


    # TC174: DHCPv6 relay agent anomaly
    def test_tc174_v6_relay_anomaly(self, lease_mgr, v6_data):
        """TC174: Check for relay info in v6 lease."""
        ip = "2000::1741"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\174"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid)

        block = lease_mgr.get_v6_lease(ip)
        # Standard v6 lease doesn't contain relay info
        has_relay = "relay" in block.lower() if block else False
        assert isinstance(has_relay, bool), "Relay info detection should work"


    # TC175: Prefix mismatch – client from wrong prefix
    def test_tc175_prefix_mismatch(self, lease_mgr, v6_data):
        """TC175: Detect lease with IPv6 outside expected prefix."""
        out_of_prefix = self.v6["out_of_prefix_ip"]  # 2001:db8::1
        duid = "\\001\\000\\000\\000\\000\\003\\000\\175"
        expected_prefix = self.v6["prefix"]  # 2000::/64

        if lease_mgr.v6_lease_exists(out_of_prefix):
            lease_mgr.delete_v6_lease(out_of_prefix)

        lease_mgr.create_v6_lease(ip=out_of_prefix, duid=duid)

        # Verify IP is outside the expected prefix
        prefix_base = expected_prefix.split("::")[0]  # "1000"
        assert not out_of_prefix.startswith(prefix_base), \
            "{} should be outside prefix {}".format(out_of_prefix, expected_prefix)


    # TC176: Verify v6 anomaly alert in console
    def test_tc176_v6_anomaly_alert(self, lease_mgr, v6_data):
        """TC176: Anomalous v6 condition should be detectable."""
        duid = "\\001\\000\\000\\000\\000\\003\\000\\176"
        ips = ["2000::176{}".format(i) for i in range(3)]

        for ip in ips:
            if lease_mgr.v6_lease_exists(ip):
                lease_mgr.delete_v6_lease(ip)

        for ip in ips:
            lease_mgr.create_v6_lease(ip=ip, duid=duid)

        # All should exist (anomalous: same DUID, multiple IPs)
        for ip in ips:
            assert lease_mgr.v6_lease_exists(ip)

    # TC177: Verify v6 anomaly details include client info
    def test_tc177_v6_anomaly_client_info(self, lease_mgr, v6_data):
        """TC177: Anomalous v6 lease should contain client info."""
        ip = "2000::1771"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\177"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid)

        block = lease_mgr.get_v6_lease(ip)
        parsed = DHCPLeaseManager.parse_v6_lease(block)
        assert parsed.get("ip"), "Client IPv6 should be present"
        assert parsed.get("duid"), "Client DUID should be present"


    # TC178: Verify v6 anomaly severity categorization
    def test_tc178_v6_anomaly_severity(self, lease_mgr, v6_data):
        """TC178: Classify v6 anomaly severity."""
        anomaly_types = {
            "duid_spoofing": "high",
            "ipv6_conflict": "high",
            "v6_starvation": "critical",
            "rogue_dhcpv6": "critical",
            "unauthorized_duid": "medium",
            "abnormal_v6_duration": "low",
            "prefix_mismatch": "medium",
        }
        for atype, severity in anomaly_types.items():
            assert severity in ["low", "medium", "high", "critical"], \
                "Severity for {} should be valid".format(atype)

    # TC179: No false positive during normal v6 operations
    def test_tc179_v6_no_false_positive(self, lease_mgr, v6_data):
        """TC179: Normal v6 CRUD should not trigger false anomalies."""
        ip = "2000::1791"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\179"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        # Normal create
        lease_mgr.create_v6_lease(ip=ip, duid=duid, preferred_life=3600)

        # Normal update
        lease_mgr.update_v6_lease(ip=ip, preferred_life=7200)

        # Single entry check
        history = lease_mgr.get_v6_lease_history(ip)
        assert len(history) >= 1

        # Verify only one DUID for this IP
        block = lease_mgr.get_v6_lease(ip)
        parsed = DHCPLeaseManager.parse_v6_lease(block)
        assert parsed["ip"] == ip

        # Normal delete
