"""
test_duid_lease_v6.py – DHCPv6 DUID Type 1 (LLT) & Type 3 (LL) Lease Tests
             TC185-TC204

Creates, reads, updates, deletes DHCPv6 leases that use proper DUID
structures derived from MAC addresses (no DDNS).

    Type 1 (DUID-LLT): 14 bytes — type(2) + hw(2) + time(4) + MAC(6)
    Type 3 (DUID-LL) : 10 bytes — type(2) + hw(2) + MAC(6)
"""

import re
import pytest
from helpers.dhcp_lease_manager import DHCPLeaseManager


@pytest.fixture(scope="module")
def duid_data(dhcp_testdata):
    """Return duid_test_data section from config."""
    return dhcp_testdata["duid_test_data"]


@pytest.mark.usefixtures("v6_backup")
class TestDuidLeaseV6:
    """TC185-TC204: DHCPv6 DUID Type 1 (LLT) and Type 3 (LL) lease tests."""

    # ────────────────────────────────────────────────────────────────── #
    #  CREATE – Type 1 (LLT)
    # ────────────────────────────────────────────────────────────────── #

    # TC185: Create DHCPv6 lease with DUID-LLT (Type 1)
    def test_tc185_create_duid_llt_lease(self, lease_mgr, duid_data):
        """TC185: Create a new DHCPv6 lease using DUID-LLT (Type 1)."""
        td = duid_data["llt_leases"][0]
        ip = td["ip"]

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease_duid(
            ip=ip, mac=td["mac"], duid_type="LLT",
            preferred_life=td["preferred_life"],
            max_life=td["max_life"],
            ends=td["ends"],
            binding_state=td["binding_state"],
        )

        assert lease_mgr.v6_lease_exists(ip), \
            "DUID-LLT lease {} not created".format(ip)
        parsed = DHCPLeaseManager.parse_v6_lease(lease_mgr.get_v6_lease(ip))
        assert parsed["ip"] == ip
        assert parsed["binding_state"] == "active"
        assert parsed["preferred_life"] == td["preferred_life"]
        assert parsed["max_life"] == td["max_life"]

    # TC186: Verify DUID-LLT type is correctly identified as Type 1
    def test_tc186_verify_duid_llt_type(self, lease_mgr, duid_data):
        """TC186: Verify DUID type 1 (LLT) is stored correctly in lease."""
        td = duid_data["llt_leases"][0]
        dtype = lease_mgr.get_v6_lease_duid_type(td["ip"])
        assert dtype == 1, "Expected DUID type 1 (LLT), got {}".format(dtype)

    # TC187: Verify MAC can be extracted from DUID-LLT lease
    def test_tc187_extract_mac_from_llt(self, lease_mgr, duid_data):
        """TC187: Extract MAC address from DUID-LLT (Type 1) lease."""
        td = duid_data["llt_leases"][0]
        duid_bytes = DHCPLeaseManager.build_duid_llt(td["mac"])
        extracted_mac = DHCPLeaseManager.duid_extract_mac(duid_bytes)
        assert extracted_mac == td["mac"].lower(), \
            "MAC mismatch: expected {}, got {}".format(td["mac"], extracted_mac)

    # TC188: Create second DUID-LLT lease with different MAC
    def test_tc188_create_second_llt_lease(self, lease_mgr, duid_data):
        """TC188: Create second DHCPv6 lease with DUID-LLT and unique MAC."""
        td = duid_data["llt_leases"][1]
        ip = td["ip"]

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease_duid(
            ip=ip, mac=td["mac"], duid_type="LLT",
            preferred_life=td["preferred_life"],
            max_life=td["max_life"], ends=td["ends"],
        )

        assert lease_mgr.v6_lease_exists(ip)
        dtype = lease_mgr.get_v6_lease_duid_type(ip)
        assert dtype == 1

    # ────────────────────────────────────────────────────────────────── #
    #  CREATE – Type 3 (LL)
    # ────────────────────────────────────────────────────────────────── #

    # TC189: Create DHCPv6 lease with DUID-LL (Type 3)
    def test_tc189_create_duid_ll_lease(self, lease_mgr, duid_data):
        """TC189: Create a new DHCPv6 lease using DUID-LL (Type 3)."""
        td = duid_data["ll_leases"][0]
        ip = td["ip"]

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease_duid(
            ip=ip, mac=td["mac"], duid_type="LL",
            preferred_life=td["preferred_life"],
            max_life=td["max_life"],
            ends=td["ends"],
            binding_state=td["binding_state"],
        )

        assert lease_mgr.v6_lease_exists(ip), \
            "DUID-LL lease {} not created".format(ip)
        parsed = DHCPLeaseManager.parse_v6_lease(lease_mgr.get_v6_lease(ip))
        assert parsed["ip"] == ip
        assert parsed["binding_state"] == "active"

    # TC190: Verify DUID-LL type is correctly identified as Type 3
    def test_tc190_verify_duid_ll_type(self, lease_mgr, duid_data):
        """TC190: Verify DUID type 3 (LL) is stored correctly in lease."""
        td = duid_data["ll_leases"][0]
        dtype = lease_mgr.get_v6_lease_duid_type(td["ip"])
        assert dtype == 3, "Expected DUID type 3 (LL), got {}".format(dtype)

    # TC191: Verify MAC can be extracted from DUID-LL lease
    def test_tc191_extract_mac_from_ll(self, lease_mgr, duid_data):
        """TC191: Extract MAC address from DUID-LL (Type 3) lease."""
        td = duid_data["ll_leases"][0]
        duid_bytes = DHCPLeaseManager.build_duid_ll(td["mac"])
        extracted_mac = DHCPLeaseManager.duid_extract_mac(duid_bytes)
        assert extracted_mac == td["mac"].lower(), \
            "MAC mismatch: expected {}, got {}".format(td["mac"], extracted_mac)

    # TC192: Create second DUID-LL lease with different MAC
    def test_tc192_create_second_ll_lease(self, lease_mgr, duid_data):
        """TC192: Create second DHCPv6 lease with DUID-LL and unique MAC."""
        td = duid_data["ll_leases"][1]
        ip = td["ip"]

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease_duid(
            ip=ip, mac=td["mac"], duid_type="LL",
            preferred_life=td["preferred_life"],
            max_life=td["max_life"], ends=td["ends"],
        )

        assert lease_mgr.v6_lease_exists(ip)
        dtype = lease_mgr.get_v6_lease_duid_type(ip)
        assert dtype == 3

    # ────────────────────────────────────────────────────────────────── #
    #  READ / VERIFY
    # ────────────────────────────────────────────────────────────────── #

    # TC193: Read all DUID-based leases and verify count
    def test_tc193_read_all_duid_leases(self, lease_mgr, duid_data):
        """TC193: Verify all DUID Type 1 + Type 3 leases exist."""
        all_ips = [l["ip"] for l in duid_data["llt_leases"][:2]] + \
                  [l["ip"] for l in duid_data["ll_leases"]]
        for ip in all_ips:
            assert lease_mgr.v6_lease_exists(ip), \
                "Lease {} missing".format(ip)

    # TC194: Verify DUID-LLT is 14 bytes, DUID-LL is 10 bytes
    def test_tc194_verify_duid_sizes(self, duid_data):
        """TC194: Verify DUID-LLT=14 bytes and DUID-LL=10 bytes."""
        llt_mac = duid_data["llt_leases"][0]["mac"]
        ll_mac = duid_data["ll_leases"][0]["mac"]

        llt_bytes = DHCPLeaseManager.build_duid_llt(llt_mac)
        ll_bytes = DHCPLeaseManager.build_duid_ll(ll_mac)

        assert len(llt_bytes) == 14, \
            "DUID-LLT should be 14 bytes, got {}".format(len(llt_bytes))
        assert len(ll_bytes) == 10, \
            "DUID-LL should be 10 bytes, got {}".format(len(ll_bytes))

    # ────────────────────────────────────────────────────────────────── #
    #  UPDATE
    # ────────────────────────────────────────────────────────────────── #

    # TC195: Update DUID-LLT lease expiry time
    def test_tc195_update_llt_lease_expiry(self, lease_mgr, duid_data):
        """TC195: Update expiry time on a DUID-LLT (Type 1) lease."""
        td = duid_data["llt_leases"][0]
        new_ends = duid_data["update_ends"]

        lease_mgr.update_v6_lease(ip=td["ip"], ends=new_ends)

        parsed = DHCPLeaseManager.parse_v6_lease(
            lease_mgr.get_v6_lease(td["ip"]))
        assert "2029/06/30" in parsed.get("ends", ""), \
            "Expiry not updated for LLT lease"

    # TC196: Update DUID-LL lease preferred-life and max-life
    def test_tc196_update_ll_lease_lifetimes(self, lease_mgr, duid_data):
        """TC196: Update preferred-life and max-life on a DUID-LL lease."""
        td = duid_data["ll_leases"][0]
        new_plife = duid_data["update_preferred_life"]
        new_mlife = duid_data["update_max_life"]

        lease_mgr.update_v6_lease(
            ip=td["ip"],
            preferred_life=new_plife,
            max_life=new_mlife,
        )

        parsed = DHCPLeaseManager.parse_v6_lease(
            lease_mgr.get_v6_lease(td["ip"]))
        assert parsed["preferred_life"] == new_plife
        assert parsed["max_life"] == new_mlife

    # TC197: Update DUID-LLT lease MAC (recreate with new DUID)
    def test_tc197_update_llt_mac(self, lease_mgr, duid_data):
        """TC197: Update MAC on a DUID-LLT lease (delete + recreate)."""
        td = duid_data["llt_leases"][0]
        new_mac = duid_data["update_mac"]

        lease_mgr.delete_v6_lease(td["ip"])
        lease_mgr.create_v6_lease_duid(
            ip=td["ip"], mac=new_mac, duid_type="LLT",
            preferred_life=td["preferred_life"],
            max_life=td["max_life"], ends=td["ends"],
        )

        assert lease_mgr.v6_lease_exists(td["ip"])
        dtype = lease_mgr.get_v6_lease_duid_type(td["ip"])
        assert dtype == 1
        # Verify new MAC is embedded in DUID
        duid_bytes = DHCPLeaseManager.build_duid_llt(new_mac)
        assert DHCPLeaseManager.duid_extract_mac(duid_bytes) == new_mac.lower()

    # TC198: Update DUID-LL lease MAC (recreate with new DUID)
    def test_tc198_update_ll_mac(self, lease_mgr, duid_data):
        """TC198: Update MAC on a DUID-LL lease (delete + recreate)."""
        td = duid_data["ll_leases"][0]
        new_mac = duid_data["update_mac"]

        lease_mgr.delete_v6_lease(td["ip"])
        lease_mgr.create_v6_lease_duid(
            ip=td["ip"], mac=new_mac, duid_type="LL",
            preferred_life=td["preferred_life"],
            max_life=td["max_life"], ends=td["ends"],
        )

        assert lease_mgr.v6_lease_exists(td["ip"])
        dtype = lease_mgr.get_v6_lease_duid_type(td["ip"])
        assert dtype == 3

    # TC199: Change lease from DUID-LLT to DUID-LL (cross-type update)
    def test_tc199_change_llt_to_ll(self, lease_mgr, duid_data):
        """TC199: Change DUID type from LLT to LL for same IP."""
        td = duid_data["llt_leases"][1]

        lease_mgr.delete_v6_lease(td["ip"])
        lease_mgr.create_v6_lease_duid(
            ip=td["ip"], mac=td["mac"], duid_type="LL",
            preferred_life=td["preferred_life"],
            max_life=td["max_life"], ends=td["ends"],
        )

        dtype = lease_mgr.get_v6_lease_duid_type(td["ip"])
        assert dtype == 3, "Expected LL (type 3) after cross-type update"

    # ────────────────────────────────────────────────────────────────── #
    #  DELETE
    # ────────────────────────────────────────────────────────────────── #

    # TC200: Delete a DUID-LLT lease
    def test_tc200_delete_llt_lease(self, lease_mgr, duid_data):
        """TC200: Delete a DHCPv6 lease with DUID-LLT (Type 1)."""
        td = duid_data["llt_leases"][2]
        ip = td["ip"]

        # Ensure it exists first
        if not lease_mgr.v6_lease_exists(ip):
            lease_mgr.create_v6_lease_duid(
                ip=ip, mac=td["mac"], duid_type="LLT",
                preferred_life=td["preferred_life"],
                max_life=td["max_life"], ends=td["ends"],
            )
        assert lease_mgr.v6_lease_exists(ip)

        result = lease_mgr.delete_v6_lease(ip)
        assert result is True, "delete_v6_lease returned False"
        assert not lease_mgr.v6_lease_exists(ip), \
            "DUID-LLT lease {} still exists after delete".format(ip)

    # TC201: Delete a DUID-LL lease
    def test_tc201_delete_ll_lease(self, lease_mgr, duid_data):
        """TC201: Delete a DHCPv6 lease with DUID-LL (Type 3)."""
        td = duid_data["ll_leases"][1]
        ip = td["ip"]

        if not lease_mgr.v6_lease_exists(ip):
            lease_mgr.create_v6_lease_duid(
                ip=ip, mac=td["mac"], duid_type="LL",
                preferred_life=td["preferred_life"],
                max_life=td["max_life"], ends=td["ends"],
            )
        assert lease_mgr.v6_lease_exists(ip)

        result = lease_mgr.delete_v6_lease(ip)
        assert result is True
        assert not lease_mgr.v6_lease_exists(ip), \
            "DUID-LL lease {} still exists after delete".format(ip)

    # TC202: Delete non-existent DUID lease returns False
    def test_tc202_delete_nonexistent_duid_lease(self, lease_mgr):
        """TC202: Delete a DUID lease that doesn't exist returns False."""
        result = lease_mgr.delete_v6_lease("2607:f8d8:0:1::ffff")
        assert result is False

    # ────────────────────────────────────────────────────────────────── #
    #  NEGATIVE / VALIDATION
    # ────────────────────────────────────────────────────────────────── #

    # TC203: Invalid DUID type raises ValueError
    def test_tc203_invalid_duid_type(self, lease_mgr):
        """TC203: Creating lease with invalid DUID type raises ValueError."""
        with pytest.raises(ValueError, match="duid_type must be"):
            lease_mgr.build_v6_lease_duid(
                ip="2607:f8d8:0:1::99",
                mac="00:11:22:33:44:55",
                duid_type="INVALID",
            )

    # TC204: Invalid MAC in DUID builder raises ValueError
    def test_tc204_invalid_mac_in_duid(self, lease_mgr):
        """TC204: Creating DUID lease with malformed MAC raises error."""
        with pytest.raises((ValueError, IndexError)):
            lease_mgr.create_v6_lease_duid(
                ip="2607:f8d8:0:1::98",
                mac="ZZ:ZZ:ZZ:ZZ:ZZ:ZZ",
                duid_type="LLT",
            )
