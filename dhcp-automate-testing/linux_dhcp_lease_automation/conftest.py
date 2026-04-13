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
#  CLI option: --keep-leases
# ────────────────────────────────────────────────────────────────────── #
def pytest_addoption(parser):
    parser.addoption(
        "--keep-leases",
        action="store_true",
        default=False,
        help="Skip lease-file backup/restore so leases remain on the "
             "DHCP server after the run.  Useful for manual DDI verification.",
    )

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

    A ``Result`` indicator column is maintained automatically:
        Pass  → ``✅ PASS``
        Fail  → ``❌ FAIL``
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

    # Ensure Result column exists
    if "Result" not in header:
        header.append("Result")
        for row in rows[1:]:
            s = row[status_col].strip() if len(row) > status_col else ""
            if s.lower() == "fail":
                row.append("❌ FAIL")
            elif s.lower() == "pass":
                row.append("✅ PASS")
            else:
                row.append("")
    result_col = header.index("Result")

    today = datetime.now().strftime("%m/%d/%Y")
    updated = False

    for row in rows[1:]:
        if len(row) > tc_col and row[tc_col].strip() == tc_no:
            # Only overwrite with Fail, or Pass when not already Fail
            if status == "Fail" or row[status_col].strip() != "Fail":
                row[status_col] = status
            row[tester_col] = tester
            row[date_col] = today
            # Update Result indicator
            while len(row) <= result_col:
                row.append("")
            row[result_col] = "❌ FAIL" if row[status_col].strip() == "Fail" else "✅ PASS"
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

    # ── Auto-marker: write proof lease to BOTH v4 and v6 after pass ──
    if not all_passed:
        return
    tc_num = int(tc_no[2:])
    if tc_num in _marker_written:
        return
    mgr = _session_lease_mgr
    if mgr is None:
        return

    # Always write v4 marker for every TC
    marker_ip = "3.3.227.{}".format(tc_num)
    marker_mac = "00:00:FE:{:02X}:{:02X}:01".format(
        tc_num // 256, tc_num % 256)
    try:
        mgr.create_v4_lease(
            ip=marker_ip, mac=marker_mac,
            hostname="tc{:03d}-validated".format(tc_num),
            binding_state="active", ends="2027/04/07 00:00:00",
            tc_tag=tc_no,
        )
    except Exception:
        pass

    # Always write v6 marker for every TC
    marker_ip6 = "2000::ff{:02x}".format(tc_num)
    marker_duid = "\\001\\000\\000\\000\\000\\003\\000\\001\\000\\000\\376\\{:03d}".format(
        tc_num)
    try:
        mgr.create_v6_lease(
            ip=marker_ip6, duid=marker_duid,
            preferred_life=3600, max_life=7200,
            ends="2027/04/07 00:00:00", binding_state="active",
            tc_tag=tc_no,
        )
    except Exception:
        pass

    _marker_written.add(tc_num)


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
    {"ip": "3.3.228.151", "mac": "00:00:23:aa:bb:01",
     "hostname": "persistent-v4-1", "binding_state": "active",
     "starts": "2026/04/08 00:00:00", "ends": "2027/04/08 00:00:00"},
    {"ip": "3.3.228.152", "mac": "00:00:23:aa:bb:02",
     "hostname": "persistent-v4-2", "binding_state": "active",
     "starts": "2026/04/08 00:00:00", "ends": "2027/04/08 00:00:00"},
]

_PERSISTENT_V6 = [
    {"ip": "2000::f001", "duid": "\\001\\000\\000\\000\\000\\003\\000\\001",
     "preferred_life": 3600, "max_life": 7200,
     "ends": "2027/04/08 00:00:00", "binding_state": "active"},
    {"ip": "2000::f002", "duid": "\\001\\000\\000\\000\\000\\003\\000\\002",
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
    # Store reference for the auto-marker hook
    global _session_lease_mgr
    _session_lease_mgr = mgr
    # Store connection info for the terminal summary hook (runs after
    # fixture teardown, so _session_lease_mgr will already be None)
    global _session_mgr_config
    _session_mgr_config = {
        "host": server["host"],
        "username": server["username"],
        "password": server.get("password"),
        "key_file": server.get("key_file"),
        "port": server.get("port", 22),
        "v4_lease_file": lease_files["v4"],
        "v6_lease_file": lease_files["v6"],
        "restart_cmd": svc["restart_cmd"],
        "restart_v6_cmd": svc["restart_v6_cmd"],
    }
    yield mgr
    mgr.close()
    _session_lease_mgr = None

# Global reference to lease_mgr used by the auto-marker hook
_session_lease_mgr = None
# Connection config for terminal summary hook (survives fixture teardown)
_session_mgr_config = None


# ────────────────────────────────────────────────────────────────────── #
#  Backup / Restore lease files
#
#  Persistent leases (2 v4 + 2 v6) are seeded AFTER restore so they
#  always survive on the server for DDI console verification.
#
#  With --keep-leases ALL test leases also remain (no restore at all).
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def v4_backup(lease_mgr, request):
    """Backup v4 lease file at session start, restore at end.

    When ``--keep-leases`` is passed, the backup is still taken but
    restore is **skipped** so ALL leases remain on the server for DDI
    verification.

    Persistent v4 leases are always seeded after restore.
    """
    backup = lease_mgr.backup_v4_leases()
    yield backup
    if not request.config.getoption("--keep-leases"):
        lease_mgr.restore_v4_leases(backup)
    # Seed persistent v4 leases so DDI console always has something.
    # Do NOT restart dhcpd afterwards – ISC DHCP discards manually-
    # written leases on restart; they are readable from the file as-is.
    for lease in _PERSISTENT_V4:
        if not lease_mgr.v4_lease_exists(lease["ip"]):
            lease_mgr.create_v4_lease(**lease)


@pytest.fixture(scope="session")
def v6_backup(lease_mgr, request):
    """Backup v6 lease file at session start, restore at end.

    When ``--keep-leases`` is passed, restore is skipped.

    Persistent v6 leases are always seeded after restore.
    """
    backup = lease_mgr.backup_v6_leases()
    yield backup
    if not request.config.getoption("--keep-leases"):
        lease_mgr.restore_v6_leases(backup)
    # Seed persistent v6 leases (no restart – see v4_backup comment)
    for lease in _PERSISTENT_V6:
        if not lease_mgr.v6_lease_exists(lease["ip"]):
            lease_mgr.create_v6_lease(**lease)


# ────────────────────────────────────────────────────────────────────── #
#  Shortcut fixtures for test data
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def v4_data(dhcp_testdata):
    return dhcp_testdata["v4_test_data"]


@pytest.fixture(scope="session")
def v6_data(dhcp_testdata):
    return dhcp_testdata["v6_test_data"]


# ────────────────────────────────────────────────────────────────────── #
#  Auto TC-tag fixture – extracts TC number from running test name
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture
def tc_tag(request):
    """Return e.g. 'TC001' extracted from the current test name,
    or None when the test name has no TC number."""
    return _extract_tc(request.node.nodeid)


@pytest.fixture(autouse=True)
def _auto_tc_tag(request, lease_mgr):
    """Autouse fixture: before each test, set the TC tag on the
    session-scoped lease_mgr so every lease it writes is tagged
    with ``# [AUTOTEST] TC0XX …`` automatically.

    After the test, the tag is cleared back to None.
    """
    tag = _extract_tc(request.node.nodeid)
    lease_mgr._current_tc_tag = tag
    yield
    lease_mgr._current_tc_tag = None


# ────────────────────────────────────────────────────────────────────── #
#  Auto-marker: writes a proof-of-execution lease for EVERY TC
#
#  After each test PASSES, a small marker lease is written to the
#  appropriate conf/lease file so you can verify from the file alone
#  that every TC (positive, negative, validation) was executed.
#
#  v4 marker IP: 3.3.227.{tc_num}   (TC001→3.3.227.1 … TC184→3.3.227.184)
#  v6 marker IP: 2000::ff{tc_num:02x} (TC001→2000::ff01 … TC184→2000::ffb8)
# ────────────────────────────────────────────────────────────────────── #
# TC ranges that belong to v4 or v6 lease files
_V4_TC_RANGES = [
    (1, 10), (21, 30), (41, 48), (57, 65), (74, 80),
    (82, 86), (93, 99), (103, 111), (121, 121),
    (123, 128), (129, 136), (145, 146), (149, 151),
    (152, 165), (180, 184),
]
_V6_TC_RANGES = [
    (11, 20), (31, 40), (49, 56), (66, 73), (81, 81),
    (87, 92), (100, 102), (112, 120), (122, 122),
    (137, 144), (147, 148), (166, 179), (180, 180),
    (185, 204),
]

# Track which TCs already got a marker this session (avoid duplicates
# from parametrized sub-tests)
_marker_written = set()


def _tc_is_v4(tc_num):
    return any(lo <= tc_num <= hi for lo, hi in _V4_TC_RANGES)


def _tc_is_v6(tc_num):
    return any(lo <= tc_num <= hi for lo, hi in _V6_TC_RANGES)


class _TaggedLeaseManager:
    """Thin wrapper around DHCPLeaseManager that auto-injects tc_tag
    into every create / update call so each lease block in the config
    file is stamped with the test case that wrote it.

    Example line in dhcpd.leases:
        # [AUTOTEST] TC001 | 2026/04/08 14:30:00
        lease 3.3.228.150 {
          ...
        }
    """

    def __init__(self, mgr, tag):
        self._mgr = mgr
        self._tag = tag

    def __getattr__(self, name):
        attr = getattr(self._mgr, name)
        if name in (
            "create_v4_lease", "update_v4_lease",
            "create_v6_lease", "update_v6_lease",
            "create_v4_lease_with_hw_type",
        ):
            # Wrap the method to inject tc_tag when caller didn't pass it
            import functools

            @functools.wraps(attr)
            def _wrapper(*args, **kwargs):
                if "tc_tag" not in kwargs or kwargs["tc_tag"] is None:
                    kwargs["tc_tag"] = self._tag
                return attr(*args, **kwargs)
            return _wrapper
        return attr


@pytest.fixture
def tagged_mgr(lease_mgr, tc_tag):
    """Lease manager that automatically stamps every lease it creates
    with the current test case number (e.g. ``# [AUTOTEST] TC042``)
    inside the lease config file."""
    return _TaggedLeaseManager(lease_mgr, tc_tag)


# ────────────────────────────────────────────────────────────────────── #
#  Delete-IP reference table – all IPs used by delete test cases
# ────────────────────────────────────────────────────────────────────── #
_DELETE_IPS_V4 = [
    ("TC041", "3.3.228.220", "00:00:41:00:00:01", "Delete single lease", False),
    ("TC042", "3.3.228.221", "00:00:42:00:00:01", "Delete batch (1/3)", False),
    ("TC042", "3.3.228.222", "00:00:42:00:00:02", "Delete batch (2/3)", False),
    ("TC042", "3.3.228.223", "00:00:42:00:00:03", "Delete batch (3/3)", False),
    ("TC043", "3.3.228.224", "00:00:43:00:00:01", "Delete all scope (1/3)", False),
    ("TC043", "3.3.228.225", "00:00:43:00:00:02", "Delete all scope (2/3)", False),
    ("TC043", "3.3.228.226", "00:00:43:00:00:03", "Delete all scope (3/3)", False),
    ("TC044", "3.3.228.227", "00:00:44:00:00:01", "Deleted+reused new MAC", True),
    ("TC045", "3.3.228.228", "00:00:45:00:00:01", "Delete+count decreased", False),
    ("TC046", "3.3.228.229", "00:00:46:00:00:01", "Cancel (NOT deleted)", True),
    ("TC047", "3.3.228.196", "00:00:47:00:00:01", "Delete+verify removed", False),
    ("TC048", "99.99.99.99", "N/A", "Non-existent", None),
]

_DELETE_IPS_V6 = [
    ("TC049", "2000::e001", "Delete single v6 lease", False),
    ("TC050", "2000::e010", "Delete batch (1/3)", False),
    ("TC050", "2000::e011", "Delete batch (2/3)", False),
    ("TC050", "2000::e012", "Delete batch (3/3)", False),
    ("TC051", "2000::e020", "Delete all prefix (1/3)", False),
    ("TC051", "2000::e021", "Delete all prefix (2/3)", False),
    ("TC051", "2000::e022", "Delete all prefix (3/3)", False),
    ("TC052", "2000::e030", "Deleted+reused new DUID", True),
    ("TC053", "2000::e040", "Delete+count decreased", False),
    ("TC054", "2000::e050", "Cancel (NOT deleted)", True),
    ("TC055", "2000::e060", "Delete+verify removed", False),
    ("TC056", "ffff::dead:beef", "Non-existent", None),
]

_DELETE_IPS_DUID = [
    ("TC200", "2607:f8d8:0:1::14", "DUID-LLT (Type 1)", False),
    ("TC201", "2607:f8d8:0:1::13", "DUID-LL  (Type 3)", False),
    ("TC202", "2607:f8d8:0:1::ffff", "Non-existent", None),
]


# ────────────────────────────────────────────────────────────────────── #
#  pytest_terminal_summary – print delete IP verification + write to
#  both lease config files after the entire test session.
# ────────────────────────────────────────────────────────────────────── #
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """After all tests, show which delete-test IPs still exist on the
    DHCP server and write a reference block into both lease files."""
    from helpers.dhcp_lease_manager import DHCPLeaseManager as _Mgr

    cfg = _session_mgr_config
    if cfg is None:
        return

    try:
        mgr = _Mgr(
            host=cfg["host"], username=cfg["username"],
            password=cfg.get("password"), key_file=cfg.get("key_file"),
            port=cfg.get("port", 22),
            v4_lease_file=cfg["v4_lease_file"],
            v6_lease_file=cfg["v6_lease_file"],
            restart_cmd=cfg.get("restart_cmd", ""),
            restart_v6_cmd=cfg.get("restart_v6_cmd", ""),
        )
        mgr.connect()
    except Exception as exc:
        terminalreporter.section("DELETE IP VERIFICATION REPORT")
        terminalreporter.write_line(
            "  [WARN] Could not connect to DHCP server: {}".format(exc))
        return

    ts = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    sep = "=" * 90
    dash = "-" * 90

    terminalreporter.section("DELETE IP VERIFICATION REPORT")
    terminalreporter.write_line(sep)

    # ── V4 ────────────────────────────────────────────────────────── #
    terminalreporter.write_line(
        "  DHCPv4 DELETE IPs  (TC041-TC048)  |  Scope: 3.3.228.0/24")
    terminalreporter.write_line(dash)
    terminalreporter.write_line(
        "{:<7} {:<17} {:<20} {:<28} {:<8} {:<8}".format(
            "TC", "IP", "MAC", "Operation", "Exists?", "Status"))
    terminalreporter.write_line(dash)

    v4_ref_lines = []
    for tc, ip, mac, desc, should_exist in _DELETE_IPS_V4:
        if should_exist is None:
            exists = False
            status_str = "N/A"
            v4_ref_lines.append(
                "# {}  {}  {}  {}  -> N/A".format(tc, ip, mac, desc))
        else:
            try:
                exists = mgr.v4_lease_exists(ip)
            except Exception:
                exists = None
            if exists is None:
                status_str = "ERR"
            elif should_exist and exists:
                status_str = "\033[92mOK\033[0m"
            elif not should_exist and not exists:
                status_str = "\033[92mOK\033[0m"
            else:
                status_str = "\033[91mFAIL\033[0m"
            expect_tag = "SHOULD EXIST" if should_exist else "SHOULD NOT EXIST"
            exist_tag = "YES" if exists else "NO"
            v4_ref_lines.append(
                "# {}  {}  {}  {}  -> {} [{}]".format(
                    tc, ip, mac, desc, expect_tag, exist_tag))
        exist_disp = "YES" if exists else "NO"
        terminalreporter.write_line(
            "{:<7} {:<17} {:<20} {:<28} {:<8} {}".format(
                tc, ip, mac, desc, exist_disp, status_str))

    terminalreporter.write_line("")

    # ── V6 ────────────────────────────────────────────────────────── #
    terminalreporter.write_line(
        "  DHCPv6 DELETE IPs  (TC049-TC056)  |  Prefix: 2000::/64")
    terminalreporter.write_line(dash)
    terminalreporter.write_line(
        "{:<7} {:<22} {:<28} {:<8} {:<8}".format(
            "TC", "IPv6", "Operation", "Exists?", "Status"))
    terminalreporter.write_line(dash)

    v6_ref_lines = []
    for tc, ip, desc, should_exist in _DELETE_IPS_V6:
        if should_exist is None:
            exists = False
            status_str = "N/A"
            v6_ref_lines.append(
                "# {}  {}  {}  -> N/A".format(tc, ip, desc))
        else:
            try:
                exists = mgr.v6_lease_exists(ip)
            except Exception:
                exists = None
            if exists is None:
                status_str = "ERR"
            elif should_exist and exists:
                status_str = "\033[92mOK\033[0m"
            elif not should_exist and not exists:
                status_str = "\033[92mOK\033[0m"
            else:
                status_str = "\033[91mFAIL\033[0m"
            expect_tag = "SHOULD EXIST" if should_exist else "SHOULD NOT EXIST"
            exist_tag = "YES" if exists else "NO"
            v6_ref_lines.append(
                "# {}  {}  {}  -> {} [{}]".format(
                    tc, ip, desc, expect_tag, exist_tag))
        exist_disp = "YES" if exists else "NO"
        terminalreporter.write_line(
            "{:<7} {:<22} {:<28} {:<8} {}".format(
                tc, ip, desc, exist_disp, status_str))

    terminalreporter.write_line("")

    # ── DUID ──────────────────────────────────────────────────────── #
    terminalreporter.write_line(
        "  DUID DELETE IPs (TC200-TC202)  |  Prefix: 2607:f8d8:0:1::/64")
    terminalreporter.write_line(dash)
    terminalreporter.write_line(
        "{:<7} {:<26} {:<22} {:<8} {:<8}".format(
            "TC", "IPv6", "DUID Type", "Exists?", "Status"))
    terminalreporter.write_line(dash)

    duid_ref_lines = []
    for tc, ip, desc, should_exist in _DELETE_IPS_DUID:
        if should_exist is None:
            exists = False
            status_str = "N/A"
            duid_ref_lines.append(
                "# {}  {}  {}  -> N/A".format(tc, ip, desc))
        else:
            try:
                exists = mgr.v6_lease_exists(ip)
            except Exception:
                exists = None
            if exists is None:
                status_str = "ERR"
            elif should_exist and exists:
                status_str = "\033[92mOK\033[0m"
            elif not should_exist and not exists:
                status_str = "\033[92mOK\033[0m"
            else:
                status_str = "\033[91mFAIL\033[0m"
            expect_tag = "SHOULD EXIST" if should_exist else "SHOULD NOT EXIST"
            exist_tag = "YES" if exists else "NO"
            duid_ref_lines.append(
                "# {}  {}  {}  -> {} [{}]".format(
                    tc, ip, desc, expect_tag, exist_tag))
        exist_disp = "YES" if exists else "NO"
        terminalreporter.write_line(
            "{:<7} {:<26} {:<22} {:<8} {}".format(
                tc, ip, desc, exist_disp, status_str))

    terminalreporter.write_line(sep)
    terminalreporter.write_line(
        "  OK = delete verified  |  FAIL = lease state mismatch  |  "
        "Timestamp: {}".format(ts))
    terminalreporter.write_line(sep)

    # ── Write reference blocks into lease config files ────────────── #
    try:
        v4_block = "\n".join([
            "",
            "# " + "=" * 68,
            "# DELETE TEST IP REFERENCE  —  {}".format(ts),
            "# OK=verified  |  FAIL=mismatch  |  Auto-generated by pytest",
            "# " + "=" * 68,
        ] + v4_ref_lines + [
            "# " + "=" * 68,
            "",
        ])
        mgr._append_file(mgr.v4_lease_file, v4_block)

        v6_block = "\n".join([
            "",
            "# " + "=" * 68,
            "# DELETE TEST IP REFERENCE  —  {}".format(ts),
            "# OK=verified  |  FAIL=mismatch  |  Auto-generated by pytest",
            "# " + "=" * 68,
        ] + v6_ref_lines + [
            "# " + "-" * 68,
            "# DUID DELETE TESTS  (Prefix: 2607:f8d8:0:1::/64)",
            "# " + "-" * 68,
        ] + duid_ref_lines + [
            "# " + "=" * 68,
            "",
        ])
        mgr._append_file(mgr.v6_lease_file, v6_block)

        terminalreporter.write_line(
            "  [Written] Delete IP reference appended to v4 + v6 lease files")
    except Exception as exc:
        terminalreporter.write_line(
            "  [WARN] Could not write reference to lease files: {}".format(exc))

    mgr.close()
