from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('https://demo.automationtesting.in/Index.html')
    # page.goto('https://127.0.0.0:9443/#/login')

    
    #Select Drop
    # 1.Find the select location
    #Select_dropdown=page.query_selector('//select[@id="Skills"]')
    #2. Select the option
    #select_dropdown.select_option(label='Art Design')

    # page.select_option('//select[@id="Skills"]',label="AutoCAD")
    # page.wait_for_timeout(9000)


    # Radio Button
    radio_button = page.query_selector('//input[@value="FeMale"]')

    # click and check
    radio_button.Click()
    # radio_button.check()

    # if statement - python
    if radio_button.is_checked():
        print("Passed")
    else:
        print("Failed")

    # CheckBox
    checkbox = page.query_selector('//input[@value="Cricket"]')
    checkbox.Check()

    if checkbox.is_checked():
        print("Passed")
    else:
        print("Failed")
    page.wait_for_timeout(9000)

