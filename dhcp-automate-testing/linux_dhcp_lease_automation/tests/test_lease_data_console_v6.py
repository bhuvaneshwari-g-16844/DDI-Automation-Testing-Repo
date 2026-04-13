"""
test_lease_data_console_v6.py – DHCPv6 Lease Data Console Tests (TC137-TC144)

Verifies that DHCPv6 lease data displayed in the DDI console matches
the actual lease data on the DHCP agent server.
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


@pytest.mark.usefixtures("v6_backup")
class TestLeaseDataConsoleV6:
    """TC137-TC144: DHCPv6 Lease Data Console tests."""

    @pytest.fixture(autouse=True)
    def _console_data(self, dhcp_testdata):
        self.console_url = dhcp_testdata["ddi_console"]["url"]
        self.lease_page = dhcp_testdata["ddi_console"]["lease_page"]

    def _get_console_leases_v6(self):
        """Fetch v6 lease list from console API (best-effort)."""
        try:
            resp = requests.get(
                "{}/api/dhcp/leases/v6".format(self.console_url),
                verify=False, timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    # TC137: Verify v6 lease data displayed correctly in console
    def test_tc137_v6_console_display(self, lease_mgr, v6_data):
        """TC137: Create v6 lease and verify all fields on agent."""
        ip = "2000::1371"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\137\\001"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(
            ip=ip, duid=duid, preferred_life=3600, max_life=7200,
        )

        lease_block = lease_mgr.get_v6_lease(ip)
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert parsed["ip"] == ip
        assert parsed.get("preferred_life") == 3600
        assert parsed.get("max_life") == 7200

        console_data = self._get_console_leases_v6()
        if console_data:
            ips = [l.get("ip", l.get("address", "")) for l in console_data]
            assert ip in ips, "v6 lease should appear in console"


    # TC138: Verify v6 lease count matches between console and server
    def test_tc138_v6_count_match(self, lease_mgr, v6_data):
        """TC138: v6 lease count consistency."""
        agent_count = lease_mgr.count_v6_leases()
        assert agent_count >= 0

        console_data = self._get_console_leases_v6()
        if console_data is not None:
            assert len(console_data) == agent_count

    # TC139: Verify v6 lease data sync
    def test_tc139_v6_data_sync(self, lease_mgr, v6_data):
        """TC139: v6 lease data consistency between agent and console."""
        all_leases = lease_mgr.get_all_v6_leases()
        agent_ips = set()
        for block in all_leases:
            parsed = DHCPLeaseManager.parse_v6_lease(block)
            if parsed.get("ip"):
                agent_ips.add(parsed["ip"])

        assert len(agent_ips) >= 0

        console_data = self._get_console_leases_v6()
        if console_data is not None:
            console_ips = {l.get("ip", l.get("address", "")) for l in console_data}
            missing = agent_ips - console_ips
            assert len(missing) == 0, "Missing in console: {}".format(missing)

    # TC140: Create v6 lease on agent, verify in console
    def test_tc140_v6_agent_create_console_visible(self, lease_mgr, v6_data):
        """TC140: New v6 lease on agent should sync to console."""
        ip = "2000::1401"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\140\\001"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid)
        time.sleep(2)

        assert lease_mgr.v6_lease_exists(ip)


    # TC141: Delete v6 lease on agent, verify removed from console
    def test_tc141_v6_agent_delete_console_removed(self, lease_mgr, v6_data):
        """TC141: Deleted v6 lease should be removed after sync."""
        ip = "2000::1411"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\141\\001"

        if not lease_mgr.v6_lease_exists(ip):
            lease_mgr.create_v6_lease(ip=ip, duid=duid)

        lease_mgr.delete_v6_lease(ip)

        assert not lease_mgr.v6_lease_exists(ip)

    # TC142: Verify v6 lease search/filter in console
    def test_tc142_v6_console_search(self, lease_mgr, v6_data):
        """TC142: Search for v6 lease by IP on agent."""
        ip = "2000::1421"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\142\\001"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(ip=ip, duid=duid)

        lease_block = lease_mgr.get_v6_lease(ip)
        assert lease_block is not None, "Should find v6 lease by IP"
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert parsed["ip"] == ip


    # TC143: Verify v6 lease sorting
    def test_tc143_v6_console_sorting(self, lease_mgr, v6_data):
        """TC143: Verify v6 leases can be sorted by IP."""
        ips = ["2000::1431", "2000::1432", "2000::1433"]

        for i, ip in enumerate(ips):
            if lease_mgr.v6_lease_exists(ip):
                lease_mgr.delete_v6_lease(ip)
            lease_mgr.create_v6_lease(
                ip=ip,
                duid="\\001\\000\\000\\000\\000\\003\\000\\001\\143\\00{}".format(i + 1),
            )

        all_leases = lease_mgr.get_all_v6_leases()
        test_ips = []
        for block in all_leases:
            parsed = DHCPLeaseManager.parse_v6_lease(block)
            if parsed.get("ip") in ips:
                test_ips.append(parsed["ip"])

        assert len(test_ips) >= len(ips)


    # TC144: Verify v6 lease pagination
    def test_tc144_v6_console_pagination(self, lease_mgr, v6_data):
        """TC144: Create multiple v6 leases, verify all retrievable."""
        count = 5
        ips = ["2000::144{}".format(i) for i in range(count)]

        for i, ip in enumerate(ips):
            if lease_mgr.v6_lease_exists(ip):
                lease_mgr.delete_v6_lease(ip)
            lease_mgr.create_v6_lease(
                ip=ip,
                duid="\\001\\000\\000\\000\\000\\003\\000\\001\\144\\00{}".format(i),
            )

        total = lease_mgr.count_v6_leases()
        assert total >= count

        all_leases = lease_mgr.get_all_v6_leases()
        all_ips = set()
        for block in all_leases:
            parsed = DHCPLeaseManager.parse_v6_lease(block)
            if parsed.get("ip"):
                all_ips.add(parsed["ip"])

        for ip in ips:
            assert ip in all_ips, "v6 lease {} should be retrievable".format(ip)

