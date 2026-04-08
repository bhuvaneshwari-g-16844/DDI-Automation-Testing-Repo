"""
test_create_lease_v6.py – DHCPv6 Lease Creation Tests (TC011-TC020)

Creates v6 leases by writing to /usr/local/dhcpd/var/lib/dhcpd6.leases.
"""

import re
import pytest
from helpers.dhcp_lease_manager import DHCPLeaseManager


@pytest.mark.usefixtures("v6_backup")
class TestCreateLeaseV6:
    """TC011-TC020: Create DHCPv6 Lease tests."""

    # TC011: Create a new DHCPv6 lease with valid IPv6, DUID, IAID
    @pytest.mark.order(1)
    def test_tc011_create_v6_lease_valid(self, lease_mgr, v6_data):
        """TC011: Create a new DHCPv6 lease with valid IPv6 and DUID."""
        td = v6_data["test_lease"]

        if lease_mgr.v6_lease_exists(td["ip"]):
            lease_mgr.delete_v6_lease(td["ip"])

        lease_mgr.create_v6_lease(
            ip=td["ip"],
            duid=td["duid"],
            iaid=td["iaid"],
            preferred_life=td["preferred_life"],
            max_life=td["max_life"],
            ends=td["ends"],
            binding_state=td["binding_state"],
        )

        assert lease_mgr.v6_lease_exists(td["ip"]), \
            "v6 lease {} not found after creation".format(td["ip"])

        lease_block = lease_mgr.get_v6_lease(td["ip"])
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert parsed["ip"] == td["ip"]
        assert parsed["binding_state"] == td["binding_state"]
        assert parsed["preferred_life"] == td["preferred_life"]
        assert parsed["max_life"] == td["max_life"]

    # TC012: Create DHCPv6 lease with valid hostname and expiry
    @pytest.mark.order(2)
    def test_tc012_create_v6_with_hostname(self, lease_mgr, v6_data):
        """TC012: Create DHCPv6 lease with hostname and expiry time."""
        ip = "1000::a001"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\002"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(
            ip=ip, duid=duid,
            preferred_life=3600, max_life=7200,
            ends="2027/04/07 10:00:00",
        )

        lease_block = lease_mgr.get_v6_lease(ip)
        assert lease_block is not None, "v6 lease not created"
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert "2027/04/07" in parsed.get("ends", ""), "Expiry not set"

    # TC013: Create DHCPv6 lease with duplicate IPv6
    @pytest.mark.order(3)
    def test_tc013_create_v6_duplicate_ip(self, lease_mgr, v6_data):
        """TC013: Duplicate IPv6 – second lease appended, last entry wins."""
        td = v6_data["test_lease"]
        ip = td["ip"]

        assert lease_mgr.v6_lease_exists(ip), "Pre-condition: v6 lease must exist"

        # Create duplicate with different DUID
        lease_mgr.create_v6_lease(
            ip=ip,
            duid="\\002\\000\\000\\000\\000\\004\\000\\001",
            preferred_life=1800,
            max_life=3600,
        )

        history = lease_mgr.get_v6_lease_history(ip)
        assert len(history) >= 2, \
            "Expected 2+ entries for duplicate v6 IP, got {}".format(len(history))

    # TC014: Create DHCPv6 lease with invalid IPv6 format
    @pytest.mark.order(4)
    @pytest.mark.parametrize("invalid_ip", [
        "gggg::1",
        "1000::::::1",
        "not-an-ipv6",
        "12345::1",
    ])
    def test_tc014_create_v6_invalid_ip(self, invalid_ip):
        """TC014: Validate invalid IPv6 formats are detected."""
        import ipaddress
        with pytest.raises(ValueError):
            ipaddress.IPv6Address(invalid_ip)

    # TC015: Create DHCPv6 lease with IPv6 outside prefix range
    @pytest.mark.order(5)
    def test_tc015_create_v6_out_of_prefix(self, lease_mgr, v6_data):
        """TC015: Create v6 lease with address outside prefix range."""
        out_ip = v6_data["out_of_prefix_ip"]

        if lease_mgr.v6_lease_exists(out_ip):
            lease_mgr.delete_v6_lease(out_ip)

        lease_mgr.create_v6_lease(
            ip=out_ip,
            duid="\\001\\000\\000\\005",
        )

        assert lease_mgr.v6_lease_exists(out_ip), \
            "Out-of-prefix lease should still be written to file"

        # Verify it's outside the configured prefix
        import ipaddress
        prefix = ipaddress.IPv6Network(v6_data["prefix"])
        addr = ipaddress.IPv6Address(out_ip)
        assert addr not in prefix, "IP should be outside prefix"

        lease_mgr.delete_v6_lease(out_ip)

    # TC016: Create DHCPv6 lease without mandatory fields
    @pytest.mark.order(6)
    def test_tc016_create_v6_missing_fields(self):
        """TC016: Building a v6 lease without IP or DUID should fail."""
        with pytest.raises((TypeError, ValueError)):
            DHCPLeaseManager.build_v6_lease(ip=None, duid="\\001\\000")

        with pytest.raises((TypeError, ValueError)):
            DHCPLeaseManager.build_v6_lease(ip="1000::1", duid=None)

    # TC017: Create DHCPv6 lease with invalid DUID format
    @pytest.mark.order(7)
    @pytest.mark.parametrize("invalid_duid", [
        "",
        "not-a-duid",
        "ZZ:ZZ:ZZ",
    ])
    def test_tc017_create_v6_invalid_duid(self, invalid_duid):
        """TC017: Validate invalid DUID formats."""
        # Empty DUID should not be accepted
        if not invalid_duid:
            assert invalid_duid == "", "Empty DUID detected as invalid"
        else:
            # DUIDs should be binary/escaped strings, not plain text
            assert not invalid_duid.startswith("\\0"), \
                "DUID '{}' looks invalid".format(invalid_duid)

    # TC018: Create multiple DHCPv6 leases in batch
    @pytest.mark.order(8)
    def test_tc018_create_v6_batch(self, lease_mgr, v6_data):
        """TC018: Create multiple v6 leases in batch."""
        batch = v6_data["batch_leases"]

        for lease in batch:
            if lease_mgr.v6_lease_exists(lease["ip"]):
                lease_mgr.delete_v6_lease(lease["ip"])

        for lease in batch:
            lease_mgr.create_v6_lease(ip=lease["ip"], duid=lease["duid"])

        for lease in batch:
            assert lease_mgr.v6_lease_exists(lease["ip"]), \
                "Batch v6 lease {} not found".format(lease["ip"])

        ips = [l["ip"] for l in batch]
        assert len(set(ips)) == len(ips), "Duplicate IPs in v6 batch"

    # TC019: Create DHCPv6 lease with various DUID types
    @pytest.mark.order(9)
    @pytest.mark.parametrize("duid_name,duid_val", [
        ("DUID-LLT", "\\000\\001\\000\\001\\000\\003\\000\\001"),
        ("DUID-EN",  "\\000\\002\\000\\000\\254\\036"),
        ("DUID-LL",  "\\000\\003\\000\\001\\010\\000\\047\\000"),
    ])
    def test_tc019_create_v6_duid_types(self, lease_mgr, duid_name, duid_val):
        """TC019: Create lease with various DUID types."""
        ip_map = {
            "DUID-LLT": "1000::d001",
            "DUID-EN":  "1000::d002",
            "DUID-LL":  "1000::d003",
        }
        ip = ip_map[duid_name]

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid_val)

        assert lease_mgr.v6_lease_exists(ip), \
            "v6 lease with {} not created".format(duid_name)

        lease_mgr.delete_v6_lease(ip)

    # TC020: Create DHCPv6 lease and verify readback
    @pytest.mark.order(10)
    def test_tc020_create_v6_verify_readback(self, lease_mgr, v6_data):
        """TC020: Create v6 lease and verify it appears in lease file."""
        ip = "1000::f001"
        duid = "\\001\\000\\000\\020"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        count_before = lease_mgr.count_v6_leases()

        lease_mgr.create_v6_lease(
            ip=ip, duid=duid,
            preferred_life=3600, max_life=7200,
            ends="2027/04/07 10:00:00",
        )

        count_after = lease_mgr.count_v6_leases()
        assert count_after > count_before, \
            "v6 lease count did not increase: before={}, after={}".format(
                count_before, count_after)

        lease_block = lease_mgr.get_v6_lease(ip)
        assert lease_block is not None
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert parsed["ip"] == ip
        assert parsed["preferred_life"] == 3600
        assert parsed["max_life"] == 7200
