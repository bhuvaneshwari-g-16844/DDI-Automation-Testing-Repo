class LoginPage:

    def __init__(self, page):
        self.page = page

    def login(self, username, password):

        # Open login page
        self.page.goto(
            "https://10.73.17.95:9443/#/login",
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