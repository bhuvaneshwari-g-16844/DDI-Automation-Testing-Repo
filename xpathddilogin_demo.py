from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # Launch the browser
    browser = p.chromium.launch(headless=False)  # No ignore_https_errors here
    # Create a new page with SSL errors ignored
    page = browser.new_page(ignore_https_errors=True)  # ignore_https_errors is applied here

    # Navigate to the login page
    page.goto('https://10.73.17.95:9443/#/login', timeout=60000, wait_until='domcontentloaded')

    #xpath -Relative xpath '//'
    #Using attribute-//tagname[@attributename="value"]


    # # Wait for the username input field and type the username
    # username_input = page.wait_for_selector('//input[@name="username"]')
    # username_input.fill('admin')  # Replace 'your_username' with the actual username you want to test

    # # Wait for the Next button and click it
    # next_button = page.wait_for_selector('button.btn-login')
    # next_button.click()

    # password_input = page.wait_for_selector('//input[@name="password"]')
    # password_input.fill('Bhuvana@02') 
    # login_button = page.wait_for_selector('button.btn-login')
    # login_button.click()

    # # Wait for some time to observe the result
    # page.wait_for_timeout(5000)
# =================================================================
    #text - //tagname[text()="text"]
    
    username_input = page.wait_for_selector('//input[@name="username"]')
    username_input.fill('admin')  # Replace 'your_username' with the actual username you want to test

    # Wait for the Next button and click it
    next_button = page.wait_for_selector('button.btn-login')
    next_button.click()

    password_input = page.wait_for_selector('//input[@name="password"]')
    password_input.fill('Admin@123') 
    
    # forgot_password_link = page.wait_for_selector('text="Forgot Password?"')  # Using text selector
    # forgot_password_link.click()
    
    login_button = page.wait_for_selector('button.btn-login')
    login_button.click()

    page.wait_for_timeout(5000)
    # Optionally close the browser

    #contains
    #attributes - // tagname[contains(@attribute,"value")]
    #//input[contains(@placeholder,"User")]
    #text- // tagname[contains(text(),"Forgot your")]
    #// label[contains(text(),"Username")]
    #dynamic - prasanth123,prasanth13454,prasanth987
    #startswith - //tagname[starts-with(@id,'prasanth')]
    #endswith - 2343user

    #family
    #parent - //tagname[@id = "xy"]/parent::input[]
    #child - //tagname[@id = "xy"]/child::input[]
    browser.close()

