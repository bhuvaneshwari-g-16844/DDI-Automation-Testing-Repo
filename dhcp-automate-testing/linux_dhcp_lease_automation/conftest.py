"""
conftest.py – Shared fixtures for DHCP lease automation tests.

Provides:
    dhcp_testdata     – parsed config/dhcp_testdata.json
    lease_mgr         – DHCPLeaseManager instance (session-scoped, connected)
    v4_backup         – backup of v4 lease file before tests
    v6_backup         – backup of v6 lease file before tests

Also includes a pytest hook that:
    - Updates DHCP_Lease_TestCases.csv Status column after each test
    - Prints a live summary line per test case to the terminal
"""

import csv
import json
import os
import re
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from helpers.dhcp_lease_manager import DHCPLeaseManager

# ────────────────────────────────────────────────────────────────────── #
#  CSV path
# ────────────────────────────────────────────────────────────────────── #
CSV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "DHCP_Lease_TestCases.csv"
)


# ────────────────────────────────────────────────────────────────────── #
#  Helper: extract TC number from test nodeid
# ────────────────────────────────────────────────────────────────────── #
_TC_RE = re.compile(r"test_tc(\d+)", re.IGNORECASE)


def _extract_tc(nodeid):
    """Return e.g. 'TC001' from '...::test_tc001_create_v4_...[param]'."""
    m = _TC_RE.search(nodeid)
    if m:
        return "TC{:03d}".format(int(m.group(1)))
    return None


# ────────────────────────────────────────────────────────────────────── #
#  Helper: update one row in the CSV
# ────────────────────────────────────────────────────────────────────── #
def _update_csv(tc_no, status, tester="Automation"):
    """Set Status and Tested By for *tc_no* in the CSV file.

    If a parametrized test has multiple sub-cases for the same TC number,
    the row is only marked Pass when ALL sub-cases pass; a single Fail
    keeps it as Fail.
    """
    if not os.path.isfile(CSV_PATH):
        return

    with open(CSV_PATH, "r", newline="") as f:
        rows = list(csv.reader(f))

    header = rows[0]
    tc_col = header.index("TC No")
    status_col = header.index("Status")
    tester_col = header.index("Tested By")
    date_col = header.index("Date")

    today = datetime.now().strftime("%m/%d/%Y")
    updated = False

    for row in rows[1:]:
        if len(row) > tc_col and row[tc_col].strip() == tc_no:
            # Only overwrite with Fail, or Pass when not already Fail
            if status == "Fail" or row[status_col].strip() != "Fail":
                row[status_col] = status
            row[tester_col] = tester
            row[date_col] = today
            updated = True
            break

    if updated:
        with open(CSV_PATH, "w", newline="") as f:
            csv.writer(f).writerows(rows)


# ────────────────────────────────────────────────────────────────────── #
#  Track parametrized sub-results per TC
# ────────────────────────────────────────────────────────────────────── #
# key = TC number, value = list of booleans (True = passed)
_tc_results = {}


# ────────────────────────────────────────────────────────────────────── #
#  Pytest hook: runs after every test
# ────────────────────────────────────────────────────────────────────── #
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    # We only care about the "call" phase (not setup / teardown)
    if report.when != "call":
        return

    tc_no = _extract_tc(item.nodeid)
    if not tc_no:
        return

    passed = report.passed

    # Collect parametrized sub-results
    _tc_results.setdefault(tc_no, []).append(passed)

    # Determine overall status for this TC so far
    all_passed = all(_tc_results[tc_no])
    status = "Pass" if all_passed else "Fail"

    # Update CSV immediately
    _update_csv(tc_no, status)

    # Print live summary to terminal
    short_name = item.name
    icon = "\033[92mPASS\033[0m" if passed else "\033[91mFAIL\033[0m"
    csv_icon = "\033[92m CSV→Pass\033[0m" if all_passed else "\033[91m CSV→Fail\033[0m"
    terminal = item.config.pluginmanager.get_plugin("terminalreporter")
    if terminal:
        terminal.write_line(
            "  [{icon}] {tc} | {name} |{csv}".format(
                icon=icon, tc=tc_no, name=short_name, csv=csv_icon
            )
        )


# ────────────────────────────────────────────────────────────────────── #
#  Test data
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def dhcp_testdata():
    """Load DHCP test configuration."""
    config_path = os.path.join(
        os.path.dirname(__file__), "config", "dhcp_testdata.json"
    )
    with open(config_path, "r") as f:
        return json.load(f)


# ────────────────────────────────────────────────────────────────────── #
#  DHCP Lease Manager (SSH connection)
# ────────────────────────────────────────────────────────────────────── #
# ────────────────────────────────────────────────────────────────────── #
#  Persistent leases: 2 v4 + 2 v6 remain after tests for DDI console
# ────────────────────────────────────────────────────────────────────── #
_PERSISTENT_V4 = [
    {"ip": "2.2.228.151", "mac": "00:00:23:aa:bb:01",
     "hostname": "persistent-v4-1", "binding_state": "active",
     "starts": "2026/04/08 00:00:00", "ends": "2027/04/08 00:00:00"},
    {"ip": "2.2.228.152", "mac": "00:00:23:aa:bb:02",
     "hostname": "persistent-v4-2", "binding_state": "active",
     "starts": "2026/04/08 00:00:00", "ends": "2027/04/08 00:00:00"},
]

_PERSISTENT_V6 = [
    {"ip": "1000::f001", "duid": "\\001\\000\\000\\000\\000\\003\\000\\001",
     "preferred_life": 3600, "max_life": 7200,
     "ends": "2027/04/08 00:00:00", "binding_state": "active"},
    {"ip": "1000::f002", "duid": "\\001\\000\\000\\000\\000\\003\\000\\002",
     "preferred_life": 3600, "max_life": 7200,
     "ends": "2027/04/08 00:00:00", "binding_state": "active"},
]


@pytest.fixture(scope="session")
def lease_mgr(dhcp_testdata):
    """Create and connect DHCPLeaseManager for the session."""
    server = dhcp_testdata["dhcp_server"]
    lease_files = dhcp_testdata["lease_files"]
    svc = dhcp_testdata["dhcpd_service"]

    mgr = DHCPLeaseManager(
        host=server["host"],
        username=server["username"],
        password=server.get("password"),
        key_file=server.get("key_file"),
        port=server.get("port", 22),
        v4_lease_file=lease_files["v4"],
        v6_lease_file=lease_files["v6"],
        restart_cmd=svc["restart_cmd"],
        restart_v6_cmd=svc["restart_v6_cmd"],
    )
    mgr.connect()
    yield mgr
    mgr.close()


# ────────────────────────────────────────────────────────────────────── #
#  Session finish hook: seed 2 v4 + 2 v6 persistent leases
# ────────────────────────────────────────────────────────────────────── #
def pytest_sessionfinish(session, exitstatus):
    """After ALL fixtures tear down, seed persistent leases."""
    config_path = os.path.join(
        os.path.dirname(__file__), "config", "dhcp_testdata.json"
    )
    with open(config_path, "r") as f:
        data = json.load(f)
    server = data["dhcp_server"]
    lease_files = data["lease_files"]
    svc = data["dhcpd_service"]

    mgr = DHCPLeaseManager(
        host=server["host"],
        username=server["username"],
        password=server.get("password"),
        v4_lease_file=lease_files["v4"],
        v6_lease_file=lease_files["v6"],
        restart_cmd=svc["restart_cmd"],
        restart_v6_cmd=svc["restart_v6_cmd"],
    )
    mgr.connect()
    for lease in _PERSISTENT_V4:
        if not mgr.v4_lease_exists(lease["ip"]):
            mgr.create_v4_lease(**lease)
    for lease in _PERSISTENT_V6:
        if not mgr.v6_lease_exists(lease["ip"]):
            mgr.create_v6_lease(**lease)
    mgr.restart_dhcpd()
    mgr.restart_dhcpd6()
    mgr.close()


# ────────────────────────────────────────────────────────────────────── #
#  Backup / Restore lease files
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def v4_backup(lease_mgr):
    """Backup v4 lease file at session start, restore at end."""
    backup = lease_mgr.backup_v4_leases()
    yield backup
    lease_mgr.restore_v4_leases(backup)


@pytest.fixture(scope="session")
def v6_backup(lease_mgr):
    """Backup v6 lease file at session start, restore at end."""
    backup = lease_mgr.backup_v6_leases()
    yield backup
    lease_mgr.restore_v6_leases(backup)


# ────────────────────────────────────────────────────────────────────── #
#  Shortcut fixtures for test data
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def v4_data(dhcp_testdata):
    return dhcp_testdata["v4_test_data"]


@pytest.fixture(scope="session")
def v6_data(dhcp_testdata):
    return dhcp_testdata["v6_test_data"]
