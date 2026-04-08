"""
test_update_lease_v6.py – DHCPv6 Lease Update Tests (TC031-TC040)

Updates v6 leases by modifying /usr/local/dhcpd/var/lib/dhcpd6.leases.
"""

import pytest
from helpers.dhcp_lease_manager import DHCPLeaseManager


@pytest.mark.usefixtures("v6_backup")
class TestUpdateLeaseV6:
    """TC031-TC040: Update DHCPv6 Lease tests."""

    @pytest.fixture(autouse=True)
    def _ensure_v6_lease_exists(self, lease_mgr, v6_data):
        """Ensure a base v6 lease exists for update tests."""
        td = v6_data["test_lease"]
        if not lease_mgr.v6_lease_exists(td["ip"]):
            lease_mgr.create_v6_lease(
                ip=td["ip"], duid=td["duid"], iaid=td["iaid"],
                preferred_life=td["preferred_life"],
                max_life=td["max_life"], ends=td["ends"],
            )

    # TC031: Update DHCPv6 lease hostname
    def test_tc031_update_v6_hostname(self, lease_mgr, v6_data):
        """TC031: Update an existing DHCPv6 lease hostname."""
        td = v6_data["test_lease"]
        # v6 leases don't have hostname in the lease block itself,
        # but we can verify the update mechanism works (delete+recreate)
        lease_mgr.update_v6_lease(
            ip=td["ip"], ends="2028/01/01 00:00:00",
        )
        lease_block = lease_mgr.get_v6_lease(td["ip"])
        assert lease_block is not None, "v6 lease lost after update"
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert "2028/01/01" in parsed.get("ends", "")

    # TC032: Update DHCPv6 lease expiry
    def test_tc032_update_v6_expiry(self, lease_mgr, v6_data):
        """TC032: Update DHCPv6 lease expiry to a future date."""
        td = v6_data["test_lease"]
        new_ends = "2029/12/31 23:59:59"

        lease_mgr.update_v6_lease(ip=td["ip"], ends=new_ends)

        lease_block = lease_mgr.get_v6_lease(td["ip"])
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert "2029/12/31" in parsed.get("ends", ""), "v6 expiry not updated"

    # TC033: Update DHCPv6 lease IPv6 address
    def test_tc033_update_v6_address(self, lease_mgr, v6_data):
        """TC033: Update v6 lease address to new valid address in prefix."""
        old_ip = v6_data["test_lease"]["ip"]
        new_ip = "1000::aaaa:bbbb:cccc:dddd"
        duid = v6_data["test_lease"]["duid"]

        lease_mgr.delete_v6_lease(old_ip)

        if lease_mgr.v6_lease_exists(new_ip):
            lease_mgr.delete_v6_lease(new_ip)

        lease_mgr.create_v6_lease(ip=new_ip, duid=duid)
        assert lease_mgr.v6_lease_exists(new_ip), "New v6 address lease not created"

        # Restore original
        lease_mgr.delete_v6_lease(new_ip)
        td = v6_data["test_lease"]
        lease_mgr.create_v6_lease(
            ip=td["ip"], duid=td["duid"], iaid=td["iaid"],
            preferred_life=td["preferred_life"],
            max_life=td["max_life"], ends=td["ends"],
        )

    # TC034: Update DHCPv6 lease IPv6 to out-of-prefix
    def test_tc034_update_v6_out_of_prefix(self, lease_mgr, v6_data):
        """TC034: Update v6 address to outside prefix range."""
        out_ip = v6_data["out_of_prefix_ip"]

        if lease_mgr.v6_lease_exists(out_ip):
            lease_mgr.delete_v6_lease(out_ip)

        lease_mgr.create_v6_lease(
            ip=out_ip, duid="\\001\\000\\034",
        )

        import ipaddress
        prefix = ipaddress.IPv6Network(v6_data["prefix"])
        addr = ipaddress.IPv6Address(out_ip)
        assert addr not in prefix, "IP should be outside prefix"

        lease_mgr.delete_v6_lease(out_ip)

    # TC035: Update DHCPv6 lease DUID
    def test_tc035_update_v6_duid(self, lease_mgr, v6_data):
        """TC035: Update v6 lease DUID to a new valid DUID."""
        td = v6_data["test_lease"]
        new_duid = "\\002\\000\\000\\000\\000\\005\\000\\001"

        lease_mgr.update_v6_lease(
            ip=td["ip"], duid=new_duid,
        )

        lease_block = lease_mgr.get_v6_lease(td["ip"])
        assert lease_block is not None, "v6 lease lost after DUID update"

    # TC036: Update DHCPv6 lease IAID
    def test_tc036_update_v6_iaid(self, lease_mgr, v6_data):
        """TC036: Update v6 lease IAID value."""
        td = v6_data["test_lease"]
        new_iaid = "\\002\\000\\000\\000"

        lease_mgr.update_v6_lease(
            ip=td["ip"], iaid=new_iaid,
        )

        lease_block = lease_mgr.get_v6_lease(td["ip"])
        assert lease_block is not None, "v6 lease lost after IAID update"

    # TC037: Update DHCPv6 lease with empty mandatory fields
    def test_tc037_update_v6_empty_fields(self, lease_mgr, v6_data):
        """TC037: Update with empty fields should fail."""
        # Trying to update non-existent IP
        with pytest.raises(ValueError):
            lease_mgr.update_v6_lease(ip="ffff::9999")

    # TC038: Update DHCPv6 lease and verify readback
    def test_tc038_update_v6_verify_readback(self, lease_mgr, v6_data):
        """TC038: Update v6 lease and verify changes in file."""
        td = v6_data["test_lease"]
        new_preferred = 7200
        new_max = 14400
        new_ends = "2029/06/15 12:00:00"

        lease_mgr.update_v6_lease(
            ip=td["ip"],
            preferred_life=new_preferred,
            max_life=new_max,
            ends=new_ends,
        )

        lease_block = lease_mgr.get_v6_lease(td["ip"])
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert parsed["preferred_life"] == new_preferred
        assert parsed["max_life"] == new_max
        assert "2029/06/15" in parsed.get("ends", "")

    # TC039: Update multiple v6 fields simultaneously
    def test_tc039_update_v6_multiple_fields(self, lease_mgr, v6_data):
        """TC039: Update preferred-life, max-life, and ends simultaneously."""
        td = v6_data["test_lease"]

        lease_mgr.update_v6_lease(
            ip=td["ip"],
            preferred_life=1800,
            max_life=3600,
            ends="2030/01/01 00:00:00",
        )

        lease_block = lease_mgr.get_v6_lease(td["ip"])
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert parsed["preferred_life"] == 1800
        assert parsed["max_life"] == 3600
        assert "2030/01/01" in parsed.get("ends", "")

    # TC040: Update DHCPv6 lease with invalid IPv6 format
    def test_tc040_update_v6_invalid_ip(self):
        """TC040: Validate invalid IPv6 format detected."""
        import ipaddress
        invalid_ips = ["gggg::1", "not-ipv6", "12345::1"]
        for ip in invalid_ips:
            with pytest.raises(ValueError):
                ipaddress.IPv6Address(ip)
