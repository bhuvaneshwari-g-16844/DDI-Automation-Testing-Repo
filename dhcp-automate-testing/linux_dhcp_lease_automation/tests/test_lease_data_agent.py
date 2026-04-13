"""
test_lease_data_agent.py – Lease Data Agent Tests (TC145-TC148)

Verifies that DHCP lease data is accessible on the agent server
and matches what is shown in the lease files.
"""

import pytest
from helpers.dhcp_lease_manager import DHCPLeaseManager


@pytest.mark.usefixtures("v4_backup", "v6_backup")
class TestLeaseDataAgent:
    """TC145-TC148: Lease Data Agent tests."""

    # TC145: Verify v4 lease data accessible on agent via CLI
    def test_tc145_v4_data_accessible(self, lease_mgr, v4_data):
        """TC145: Verify v4 lease data is retrievable from agent."""
        ip = "3.3.228.145"
        mac = "00:01:45:00:00:01"
        hostname = "agent-check-v4"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(ip=ip, mac=mac, hostname=hostname)

        # Read raw file
        raw = lease_mgr.get_v4_lease_file_raw()
        assert ip in raw, "IP should appear in raw lease file"
        assert mac in raw, "MAC should appear in raw lease file"

        # Parse via API
        lease_block = lease_mgr.get_v4_lease(ip)
        assert lease_block is not None
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)
        assert parsed["ip"] == ip
        assert parsed["mac"].lower() == mac.lower()
        assert parsed.get("hostname") == hostname


    # TC146: Verify v4 lease fields on agent match expected values
    def test_tc146_v4_fields_match(self, lease_mgr, v4_data):
        """TC146: All v4 lease fields should match what was created."""
        ip = "3.3.228.146"
        mac = "00:01:46:00:00:01"
        hostname = "fields-match-v4"
        starts = "2026/04/08 09:00:00"
        ends = "2027/04/08 09:00:00"
        binding_state = "active"

        if lease_mgr.v4_lease_exists(ip):
            lease_mgr.delete_v4_lease(ip)

        lease_mgr.create_v4_lease(
            ip=ip, mac=mac, hostname=hostname,
            starts=starts, ends=ends, binding_state=binding_state,
        )

        lease_block = lease_mgr.get_v4_lease(ip)
        parsed = DHCPLeaseManager.parse_v4_lease(lease_block)

        assert parsed["ip"] == ip, "IP mismatch"
        assert parsed["mac"].lower() == mac.lower(), "MAC mismatch"
        assert parsed.get("hostname") == hostname, "Hostname mismatch"
        assert "2026/04/08" in parsed.get("starts", ""), "Starts mismatch"
        assert "2027/04/08" in parsed.get("ends", ""), "Ends mismatch"
        assert parsed.get("binding_state") == binding_state, "State mismatch"


    # TC147: Verify v6 lease data accessible on agent via CLI
    def test_tc147_v6_data_accessible(self, lease_mgr, v6_data):
        """TC147: Verify v6 lease data is retrievable from agent."""
        ip = "2000::1471"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\147\\001"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(
            ip=ip, duid=duid, preferred_life=3600, max_life=7200,
        )

        # Read raw file
        raw = lease_mgr.get_v6_lease_file_raw()
        assert ip in raw, "IPv6 should appear in raw lease file"

        # Parse
        lease_block = lease_mgr.get_v6_lease(ip)
        assert lease_block is not None
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)
        assert parsed["ip"] == ip
        assert parsed.get("preferred_life") == 3600
        assert parsed.get("max_life") == 7200


    # TC148: Verify v6 lease fields on agent match expected values
    def test_tc148_v6_fields_match(self, lease_mgr, v6_data):
        """TC148: All v6 lease fields should match what was created."""
        ip = "2000::1481"
        duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\148\\001"
        plife = 5000
        mlife = 10000
        ends = "2028/01/01 00:00:00"
        state = "active"

        if lease_mgr.v6_lease_exists(ip):
            lease_mgr.delete_v6_lease(ip)

        lease_mgr.create_v6_lease(
            ip=ip, duid=duid, preferred_life=plife, max_life=mlife,
            ends=ends, binding_state=state,
        )

        lease_block = lease_mgr.get_v6_lease(ip)
        parsed = DHCPLeaseManager.parse_v6_lease(lease_block)

        assert parsed["ip"] == ip, "IP mismatch"
        assert parsed.get("preferred_life") == plife, "preferred-life mismatch"
        assert parsed.get("max_life") == mlife, "max-life mismatch"
        assert "2028/01/01" in parsed.get("ends", ""), "Ends mismatch"
        assert parsed.get("binding_state") == state, "State mismatch"

