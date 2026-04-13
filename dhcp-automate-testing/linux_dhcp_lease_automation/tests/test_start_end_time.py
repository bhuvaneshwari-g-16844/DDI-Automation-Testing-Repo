"""
test_start_end_time.py – Lease Start/End Time Tests (TC082-TC093)

Verifies correct handling of start and end (expiry) timestamps
for both DHCPv4 and DHCPv6 leases.
"""

import re
import pytest
from helpers.dhcp_lease_manager import DHCPLeaseManager


@pytest.mark.usefixtures("v4_backup", "v6_backup")
class TestStartEndTime:
    """TC082-TC093: Lease Start/End Time tests."""

    # TC082: Verify lease start time is displayed correctly for DHCPv4
    def test_tc082_v4_start_time_display(self, lease_mgr, v4_data):
        """TC082: Verify start time in v4 lease matches what was set."""
        ip = "3.3.228.182"
        mac = "00:00:82:00:00:01"
        starts = "2026/04/08 08:30:00"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac, starts=starts)

        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert "2026/04/08" in parsed.get("starts", ""), \
            "Start time not displayed correctly"


    # TC083: Verify lease end time (expiry) is displayed correctly for DHCPv4
    def test_tc083_v4_end_time_display(self, lease_mgr, v4_data):
        """TC083: Verify end time in v4 lease matches configured expiry."""
        ip = "3.3.228.183"
        mac = "00:00:83:00:00:01"
        ends = "2027/12/31 23:59:59"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac, ends=ends)

        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert "2027/12/31" in parsed.get("ends", ""), \
            "End time not displayed correctly"


    # TC084: Update DHCPv4 lease start time to a valid date
    def test_tc084_v4_update_start_time(self, lease_mgr, v4_data, dhcp_testdata):
        """TC084: Update start time to a valid future date."""
        ip = "3.3.228.184"
        mac = "00:00:84:00:00:01"
        new_start = dhcp_testdata["time_test_data"]["valid_future_start"]

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac)

        # Update by delete + create with new start time
        lease_mgr.delete_v4_lease(ip)
        lease_mgr.create_v4_lease(ip=ip, mac=mac, starts=new_start)

        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert "2026/06/01" in parsed.get("starts", ""), \
            "Start time not updated correctly"


    # TC085: Update DHCPv4 lease end time to a valid future date
    def test_tc085_v4_update_end_time(self, lease_mgr, v4_data, dhcp_testdata):
        """TC085: Update end time to a valid future date."""
        ip = "3.3.228.185"
        mac = "00:00:85:00:00:01"
        new_end = dhcp_testdata["time_test_data"]["valid_future_end"]

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac)
        lease_mgr.update_v4_lease(ip=ip, ends=new_end)

        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert "2027/06/01" in parsed.get("ends", ""), \
            "End time not updated: got {}".format(parsed.get("ends"))


    # TC086: Update DHCPv4 lease end time to a date before start time
    def test_tc086_v4_end_before_start(self, lease_mgr, v4_data, dhcp_testdata):
        """TC086: End time before start time – file accepts it but it's
        logically invalid (expired at creation)."""
        ip = "3.3.228.186"
        mac = "00:00:86:00:00:01"
        td = dhcp_testdata["time_test_data"]
        start = td["end_before_start_start"]  # 2027/06/01
        end = td["end_before_start_end"]      # 2026/01/01

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac, starts=start, ends=end)

        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)

        # Verify file wrote it (even though logically invalid)
        assert "2027/06/01" in parsed.get("starts", "")
        assert "2026/01/01" in parsed.get("ends", "")


    # TC087: Verify lease start time is displayed correctly for DHCPv6
    def test_tc087_v6_start_time_display(self, lease_mgr, v6_data):
        """TC087: Verify cltt (start time) in v6 lease."""
        ip = "2000::8701"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\087\\001"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid)

        lease_block = lease_mgr.get_v6_lease(ip)
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        # cltt should be set (defaults to now)
        assert parsed.get("cltt"), "cltt (start time) should be present"


    # TC088: Verify lease end time (expiry) for DHCPv6
    def test_tc088_v6_end_time_display(self, lease_mgr, v6_data):
        """TC088: Verify end time in v6 lease matches configured expiry."""
        ip = "2000::8801"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\088\\001"
        ends = "2028/06/30 12:00:00"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid, ends=ends)

        lease_block = lease_mgr.get_v6_lease(ip)
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert "2028/06/30" in parsed.get("ends", ""), \
            "v6 end time not displayed correctly"


    # TC089: Update DHCPv6 lease start time to a valid date
    def test_tc089_v6_update_start_time(self, lease_mgr, v6_data):
        """TC089: Update v6 lease cltt to a valid date."""
        ip = "2000::8901"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\089\\001"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid)

        # Recreate with new cltt by delete + create
        lease_mgr.delete_v6_lease(ip)
        # build_v6_lease uses cltt param
        block = DHCPLeaseManager.build_v6_lease(
            ip=ip, duid=duid, cltt="2026/06/01 08:00:00",
            ends="2027/06/01 08:00:00",
        )
        lease_mgr._append_file(lease_mgr.v6_lease_file, "\n" + block + "\n")

        lease_block = lease_mgr.get_v6_lease(ip)
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert "2026/06/01" in parsed.get("cltt", ""), \
            "v6 start time (cltt) not updated"


    # TC090: Update DHCPv6 lease end time to a valid future date
    def test_tc090_v6_update_end_time(self, lease_mgr, v6_data):
        """TC090: Update v6 lease end time to a future date."""
        ip = "2000::9001"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\090\\001"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid)
        lease_mgr.update_v6_lease(ip=ip, ends="2029/01/01 00:00:00")

        lease_block = lease_mgr.get_v6_lease(ip)
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert "2029/01/01" in parsed.get("ends", ""), \
            "v6 end time not updated"


    # TC091: Update DHCPv6 lease end time to before start time
    def test_tc091_v6_end_before_start(self, lease_mgr, v6_data):
        """TC091: End time before start (cltt) – file accepts it."""
        ip = "2000::9101"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\091\\001"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        # cltt defaults to now (~2026), set ends to 2020
        block = DHCPLeaseManager.build_v6_lease(
            ip=ip, duid=duid,
            cltt="2027/01/01 00:00:00",
            ends="2025/01/01 00:00:00",
        )
        lease_mgr._append_file(lease_mgr.v6_lease_file, "\n" + block + "\n")

        lease_block = lease_mgr.get_v6_lease(ip)
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert "2025/01/01" in parsed.get("ends", "")
        assert "2027/01/01" in parsed.get("cltt", "")


    # TC092: Verify start and end time formats are consistent across v4/v6
    def test_tc092_time_format_consistency(self, lease_mgr, v4_data, v6_data):
        """TC092: Date format should be YYYY/MM/DD HH:MM:SS for both."""
        v4_ip = "3.3.228.192"
        v4_mac = "00:00:92:00:00:01"
        v6_ip = "2000::9201"
        v6_duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\092\\001"

        for ip in [v4_ip]:
            if lease_mgr.v4_lease_exists(ip):
                lease_mgr.delete_v4_lease(ip)
        if lease_mgr.v6_lease_exists(v6_ip):
            lease_mgr.delete_v6_lease(v6_ip)

        lease_mgr.create_v4_lease(
            ip=v4_ip, mac=v4_mac,
            starts="2026/04/08 10:00:00", ends="2027/04/08 10:00:00",
        )
        lease_mgr.create_v6_lease(
            ip=v6_ip, duid=v6_duid, ends="2027/04/08 10:00:00",
        )

        # Check v4 format
        v4_block = lease_mgr.get_v4_lease(v4_ip)
        v4_parsed = DHCPLeaseManager.parse_v4_lease(v4_block)
        date_pattern = r"\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}"
        assert re.match(date_pattern, v4_parsed.get("starts", "")), \
            "v4 starts format mismatch"
        assert re.match(date_pattern, v4_parsed.get("ends", "")), \
            "v4 ends format mismatch"

        # Check v6 format
        v6_block = lease_mgr.get_v6_lease(v6_ip)
        v6_parsed = DHCPLeaseManager.parse_v6_lease(v6_block)
        assert re.match(date_pattern, v6_parsed.get("ends", "")), \
            "v6 ends format mismatch"
        assert re.match(date_pattern, v6_parsed.get("cltt", "")), \
            "v6 cltt format mismatch"


    # TC093: Update start/end time and verify changes in history
    def test_tc093_time_change_history(self, lease_mgr, v4_data):
        """TC093: Update start/end and verify new values in history."""
        ip = "3.3.228.193"
        mac = "00:00:93:00:00:01"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(
            ip=ip, mac=mac,
            starts="2026/01/01 00:00:00", ends="2027/01/01 00:00:00",
        )

        # Update times
        lease_mgr.update_v4_lease(
            ip=ip, starts="2026/06/01 00:00:00", ends="2028/06/01 00:00:00",
        )

        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert "2026/06/01" in parsed.get("starts", ""), \
            "Updated start time not reflected"
        assert "2028/06/01" in parsed.get("ends", ""), \
            "Updated end time not reflected"

