from playwright.sync_api import sync_playwright


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    context = browser.new_context()
    page = context.new_page()
    page.goto('https://demo.automationtesting.in/Windows.html')

    page.wait_for_selector('//button[contains(text(),"      click  ")]').click()
    page.wait_for_timeout(3000)
    
    # HOw to find the total pages = list
    
    total_pages = context.pages()
    print(len(total_pages))

    for i in total_pages:
        print(i)
    print(page.title())
    new_page = total_pages[1]

    # How to switch to new page:
    new_page.bring_to_front()
    page.wait_for_timeout(4000)
    print(new_page.title())
    new_page.close()
    page.wait_for_timeout(4000)
    browser.close()
