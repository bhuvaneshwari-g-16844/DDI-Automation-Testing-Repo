

# # css selector-id-#,class-,attribute tagname[attribute = "value"];
# from playwright.sync_api import sync_playwright

# with sync_playwright() as p:
#     browser = p.chromium.launch(headless=False)
#     page = browser.new_page()
#     # page.goto('https://demo.automationtesting.in/Index.html')
#     page.goto('https://127.0.0.0:9443/#/login')

    
#     # # Wait for the selector
#     # email_txtbox = page.wait_for_selector('#email')
#     # email_txtbox.type('data@gmail.com')
#     # buttonlogin=page.wait_for_selector('#enterimg')
#     # buttonlogin.click()
#     # page.wait_for_timeout(3000)

#     #tagname[atribute="value"]

#     username=page.wait_for_selector('input[name="username"]')
#     username.type('Admin')
#     password=page.wait_for_selector('input[type="password"]')
#     password.type('admin123')
#     loginbutton=page.wait_for_selector('button[type="submit"]')
#     loginbutton.click()
#     page.wait_for_timeout(9000)

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # Launch the browser
    browser = p.chromium.launch(headless=False)  # No ignore_https_errors here
    # Create a new page with SSL errors ignored
    page = browser.new_page(ignore_https_errors=True)  
    # ignore_https_errors is applied here

    # Navigate to the login page
    page.goto('https://127.0.0.1:9443/#/login', timeout=60000, wait_until='domcontentloaded')

    # Wait for the username input field and type the username
    username_input = page.wait_for_selector('input[name="username"]')
    username_input.fill('admin')  # Replace 'your_username' with the actual username you want to test

    # Wait for the Next button and click it
    next_button = page.wait_for_selector('button.btn-login')
    next_button.click()

    password_input = page.wait_for_selector('input[name="password"]')
    password_input.fill('Bhuvana@02') 
    login_button = page.wait_for_selector('button.btn-login')
    login_button.click()

    # Wait for some time to observe the result
    page.wait_for_timeout(5000)

    # Optionally close the browser
    browser.close()

