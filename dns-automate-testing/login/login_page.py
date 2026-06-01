import os


class LoginPage:

    DEFAULT_BASE_URL = os.environ.get("DNS_BASE_URL", "https://10.73.17.95:9443").rstrip("/")

    def __init__(self, page, base_url=None):
        self.page = page
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")

    def login(self, username, password):

        # Open login page
        self.page.goto(
            f"{self.base_url}/#/login",
            timeout=60000,
            wait_until="domcontentloaded"
        )

        # Username
        username_input = self.page.wait_for_selector(
            '//input[@name="username"]'
        )
        username_input.fill(username)

        # Next button
        next_button = self.page.wait_for_selector(
            'button.btn-login'
        )
        next_button.click()

        # Password
        password_input = self.page.wait_for_selector(
            '//input[@name="password"]'
        )
        password_input.fill(password)

        # Login button
        login_button = self.page.wait_for_selector(
            'button.btn-login'
        )
        login_button.click()

        # wait dashboard load
        self.page.wait_for_load_state("networkidle")