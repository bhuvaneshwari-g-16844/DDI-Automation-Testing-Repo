import pytest
import json
import csv
import re
import os
import getpass
from datetime import datetime
from playwright.sync_api import sync_playwright


# Allow overriding the target appliance via env var:
#   DNS_BASE_URL=https://10.63.14.98:9443 pytest ...
BASE_URL = os.environ.get("DNS_BASE_URL", "https://10.72.51.96:9443").rstrip("/")


@pytest.fixture(scope="session")
def testdata():
    with open("config/testdata.json") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=300,
            args=["--start-maximized"]
        )
        yield browser
        browser.close()


@pytest.fixture(scope="session")
def logged_in_page(browser, testdata):
    """Login once, reuse the same page for all tests."""
    context = browser.new_context(
        ignore_https_errors=True,
        no_viewport=True,
        record_video_dir="videos/"
    )
    page = context.new_page()

    # Login
    page.goto(f"{BASE_URL}/#/login", timeout=60000, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    # Click user/authentication dropdown and select "Local Authentication"
    auth_dropdown = page.locator('select, .dropdown, [class*="auth"], [class*="login-type"]')
    if auth_dropdown.count() > 0 and auth_dropdown.first.is_visible():
        auth_dropdown.first.click()
        page.wait_for_timeout(500)
        local_auth = page.locator('text=Local Authentication, option:has-text("Local"), text=local authentication')
        if local_auth.count() > 0:
            local_auth.first.click()
            page.wait_for_timeout(500)
        else:
            # Try select element approach
            page.evaluate("""() => {
                const selects = document.querySelectorAll('select');
                for (const sel of selects) {
                    for (const opt of sel.options) {
                        if (opt.text.toLowerCase().includes('local')) {
                            sel.value = opt.value;
                            sel.dispatchEvent(new Event('change', { bubbles: true }));
                            break;
                        }
                    }
                }
            }""")
            page.wait_for_timeout(500)

    page.wait_for_selector('//input[@name="username"]').fill(testdata["username"])
    page.wait_for_selector('button.btn-login').click()
    page.wait_for_timeout(1000)

    page.wait_for_selector('//input[@name="password"]').fill(testdata["password"])
    page.wait_for_selector('button.btn-login').click()

    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    # Handle /#/setting_up redirect — if the app lands on setup page,
    # wait for it to resolve or navigate to dashboard.
    if "setting_up" in page.url:
        page.wait_for_timeout(5000)
        # If still on setting_up, navigate to dashboard
        if "setting_up" in page.url:
            page.goto(f"{BASE_URL}/#/dashboard", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)

    # Ensure we're past the setup page before proceeding
    page.wait_for_timeout(2000)

    yield page
    context.close()


@pytest.fixture(scope="function")
def page(logged_in_page):
    """Each test gets the already-logged-in page."""
    yield logged_in_page


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item):
    outcome = yield
    rep = outcome.get_result()

    if rep.when == "call" and rep.failed:
        page = item.funcargs.get("page")
        if page:
            try:
                page.screenshot(path=f"screenshots/{item.name}.png")
            except Exception:
                pass

    # ── Collect result in memory (written to CSV once at session end) ──
    if rep.when == "call":
        # Group results by the CSV file that owns the test (domain vs A-record …)
        csv_path = _csv_path_for_item(item)
        if csv_path:
            _test_results.setdefault(csv_path, {})[item.name] = \
                "PASS" if rep.passed else "FAIL"


def pytest_sessionfinish(session, exitstatus):
    """Write all collected test results to CSV once at the end of the session."""
    for csv_path, results in _test_results.items():
        if results:
            _flush_csv_results(csv_path, results)


# ── CSV auto-update helper ──

# { csv_path: { test_name: status } }
_test_results = {}

_HERE = os.path.dirname(__file__)

# Map a test-file directory → its CSV.  Resolved per-test via ``_csv_path_for_item``.
_CSV_MAP = {
    os.path.join(_HERE, "domain_ui_automate_test"):
        os.path.join(_HERE, "domain_ui_automate_test", "domain_testcases.csv"),
    os.path.join(_HERE, "records_ui_automate_test", "arecords"):
        os.path.join(_HERE, "records_ui_automate_test", "arecords",
                     "arecord_testcases.csv"),
}


def _csv_path_for_item(item):
    """Pick the CSV that belongs to the test's source file."""
    try:
        test_file = str(item.fspath)
    except Exception:
        return None
    for prefix, csv_path in _CSV_MAP.items():
        if test_file.startswith(prefix):
            return csv_path
    return None

def _extract_tc_number(test_name):
    """Extract TC number from test function name like test_tc01_... → TC_001."""
    m = re.search(r"test_tc(\d+)", test_name)
    if m:
        return f"TC_{int(m.group(1)):03d}"
    return None


def _flush_csv_results(csv_path, results):
    """Write collected results to the given CSV in a single write."""
    if not os.path.exists(csv_path):
        return

    today = datetime.now().strftime("%d-%m-%Y")
    tester = getpass.getuser()

    # Build lookup: TC_001 → PASS/FAIL
    tc_status = {}
    for test_name, status in results.items():
        tc_no = _extract_tc_number(test_name)
        if tc_no:
            tc_status[tc_no] = status

    if not tc_status:
        return

    try:
        with open(csv_path, newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            return

        header = rows[0]
        tc_col = header.index("TC No") if "TC No" in header else None
        status_col = header.index("Status") if "Status" in header else None
        testby_col = header.index("TestBy") if "TestBy" in header else None
        date_col = header.index("Date") if "Date" in header else None

        if tc_col is None or status_col is None:
            return

        for row in rows[1:]:
            if len(row) > tc_col and row[tc_col].strip() in tc_status:
                while len(row) <= max(status_col, testby_col or 0, date_col or 0):
                    row.append("")
                row[status_col] = tc_status[row[tc_col].strip()]
                if date_col is not None:
                    row[date_col] = today
                if testby_col is not None:
                    row[testby_col] = tester

        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
    except Exception:
        pass
