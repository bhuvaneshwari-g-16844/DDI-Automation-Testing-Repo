from playwright.sync_api import sync_playwright


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    # context = browser.new_context()
    # page = context.new_page()
    # page.goto('https://www.redbus.in/')


    
    browser = p.chromium.launch(headless=False)

    context = browser.new_context()
    page = context.new_page()
    page.goto('https://www.redbus.in/')

    # Gives all the cookies
    
    my_cookies = page.context.cookies()
    print(my_cookies)

    # # Clear the all the cookies

    # page.context.clear_cookies()

    # new_cookies = {
    #     'name' : 'ravi',
    #     "udid" : 'ytwghejhwejrkjwerjkkjrwe'
    # }

    # # To pass the new cookies to the page
    # page.context.add_cookies([new_cookies])

    # # Taking screenshot
    # # page.screenshot(path='test.png')


    # my_cookies = page.context.cookies()

    # Clearing all the cookies.
    page.context.clear_cookies()

    # Setting new cookies to page.
    page.context.add_cookies([new_cookies])

    # Taking screenshot and storing the path
    page.screenshot(path='test.png',full_page=True)
    page.wait_for_timeout(2000)
