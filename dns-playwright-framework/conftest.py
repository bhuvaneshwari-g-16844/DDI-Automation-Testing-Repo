import pytest
import json
from playwright.sync_api import sync_playwright


BASE_URL = "https://10.73.17.95:9443"


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
            page.screenshot(path=f"screenshots/{item.name}.png")