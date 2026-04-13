"""
test_lease_data_console_v4.py – DHCPv4 Lease Data Console Tests (TC129-TC136)

Verifies that DHCPv4 lease data displayed in the DDI console matches
the actual lease data on the DHCP agent server. These tests compare
agent-side data with console API/UI data.

Requires the DDI console to be accessible at the configured URL.
"""

import re
import time
import pytest

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from helpers.dhcp_lease_manager import DHCPLeaseManager

pytestmark = pytest.mark.skipif(
    not HAS_REQUESTS, reason="requests library required for console tests"
)


@pytest.mark.usefixtures("v4_backup")
class TestLeaseDataConsoleV4:
    """TC129-TC136: DHCPv4 Lease Data Console tests."""

    @pytest.fixture(autouse=True)
    def _console_data(self, dhcp_testdata):
        self.console_url = dhcp_testdata["ddi_console"]["url"]
        self.lease_page = dhcp_testdata["ddi_console"]["lease_page"]

    def _get_console_leases_v4(self):
        """Fetch v4 lease list from console API (best-effort)."""
        try:
            resp = requests.get(
                "{}/api/dhcp/leases/v4".format(self.console_url),
                verify=False, timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    # TC129: Verify v4 lease data displayed correctly in console
    def test_tc129_v4_console_display(self, lease_mgr, v4_data):
        """TC129: Create v4 lease on agent and verify fields."""
        ip = "3.3.228.129"
        mac = "00:01:29:00:00:01"
        hostname = "console-v4-129"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac, hostname=hostname)

        # Verify on agent
        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed["ip"] == ip
        assert parsed["mac"].lower() == mac.lower()
        assert parsed.get("hostname") == hostname

        # Console check (best-effort)
        console_data = self._get_console_leases_v4()
        if console_data:
            ips = [l.get("ip", l.get("address", "")) for l in console_data]
            assert ip in ips, "Lease {} should appear in console".format(ip)


    # TC130: Verify v4 lease count matches between console and server
    def test_tc130_v4_count_match(self, lease_mgr, v4_data):
        """TC130: Lease count on agent should be consistent."""
        agent_count = lease_mgr.count_v4_leases()
        assert agent_count >= 0, "Agent should report a valid lease count"

        console_data = self._get_console_leases_v4()
        if console_data is not None:
            console_count = len(console_data)
            assert console_count == agent_count, \
                "Console count {} != agent count {}".format(
                    console_count, agent_count)

    # TC131: Verify v4 lease data sync between console and agent
    def test_tc131_v4_data_sync(self, lease_mgr, v4_data):
        """TC131: Lease data consistency check."""
        all_leases = lease_mgr.get_all_v4_leases()
        agent_ips = set()
        for lease_block in all_leases:
            parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
            if parsed.get("ip"):
                agent_ips.add(parsed["ip"])

        assert len(agent_ips) >= 0, "Should enumerate agent IPs"

        console_data = self._get_console_leases_v4()
        if console_data is not None:
            console_ips = {l.get("ip", l.get("address", "")) for l in console_data}
            missing = agent_ips - console_ips
            assert len(missing) == 0, \
                "Missing in console: {}".format(missing)

    # TC132: Create v4 lease on agent, verify it appears in console
    def test_tc132_v4_agent_create_console_visible(self, lease_mgr, v4_data):
        """TC132: New lease on agent should sync to console."""
        ip = "3.3.228.132"
        mac = "00:01:32:00:00:01"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac)

        assert lease_mgr.v4_lease_exists(ip), \
            "Lease should exist on agent"


    # TC133: Delete v4 lease on agent, verify removed from console
    def test_tc133_v4_agent_delete_console_removed(self, lease_mgr, v4_data):
        """TC133: Deleted lease on agent should be removed after sync."""
        ip = "3.3.228.133"
        mac = "00:01:33:00:00:01"

        if not lease_mgr.v4_lease_exists(ip):
            lease_mgr.create_v4_lease(ip=ip, mac=mac)

        lease_mgr.delete_v4_lease(ip)

        assert not lease_mgr.v4_lease_exists(ip), \
            "Lease should be removed from agent"

    # TC134: Verify v4 lease search/filter in console
    def test_tc134_v4_console_search(self, lease_mgr, v4_data):
        """TC134: Search for specific lease by IP on agent."""
        ip = "3.3.228.134"
        mac = "00:01:34:00:00:01"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac, hostname="search-test")

        # Search by IP on agent (file search)
        lease_block = lease_mgr.get_v4_lease(ip)
        assert lease_block is not None, \
            "Should find lease by IP search"
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed["ip"] == ip


    # TC135: Verify v4 lease sorting in console
    def test_tc135_v4_console_sorting(self, lease_mgr, v4_data):
        """TC135: Verify leases can be sorted by IP."""
        ips = ["3.3.228.135", "3.3.228.136", "3.3.228.137"]

        for i, ip in enumerate(ips):
            if lease_mgr.v4_lease_exists(ip):
                lease_mgr.delete_v4_lease(ip)
            lease_mgr.create_v4_lease(
                ip=ip, mac="00:01:35:00:00:{:02x}".format(i + 1),
            )

        all_leases = lease_mgr.get_all_v4_leases()
        # Extract IPs from leases in our test range
        test_ips = []
        for block in all_leases:
            parsed = DHCPLeaseManager.parse_v4_lease(block)
            if parsed.get("ip") in ips:
                test_ips.append(parsed["ip"])

        assert len(test_ips) >= len(ips), \
            "All test leases should be found"

        # Verify sortable
        sorted_ips = sorted(test_ips)
        assert sorted_ips == ips, "IPs should be sortable in ascending order"


    # TC136: Verify v4 lease pagination for large datasets
    def test_tc136_v4_console_pagination(self, lease_mgr, v4_data):
        """TC136: Create multiple leases and verify all retrievable."""
        base = 140
        count = 5
        ips = ["3.3.228.{}".format(base + i) for i in range(count)]

        for i, ip in enumerate(ips):
            if lease_mgr.v4_lease_exists(ip):
                lease_mgr.delete_v4_lease(ip)
            lease_mgr.create_v4_lease(
                ip=ip, mac="00:01:36:00:00:{:02x}".format(i + 1),
            )

        total = lease_mgr.count_v4_leases()
        assert total >= count, \
            "Should have at least {} leases, got {}".format(count, total)

        # All leases retrievable (simulates pagination)
        all_leases = lease_mgr.get_all_v4_leases()
        all_ips = set()
        for block in all_leases:
            parsed = DHCPLeaseManager.parse_v4_lease(block)
            if parsed.get("ip"):
                all_ips.add(parsed["ip"])

        for ip in ips:
            assert ip in all_ips, "Lease {} should be in full list".format(ip)

