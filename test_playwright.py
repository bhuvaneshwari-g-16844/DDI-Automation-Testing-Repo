from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('https://www.google.com')
    print(page.title())
    page.wait_for_timeout(9000)
    browser.close()

with sync_playwright() as playwright:
    run(playwright)
