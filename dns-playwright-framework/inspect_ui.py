"""
Smart UI Inspector - Navigates the real Ember.js app flows to capture
actual web elements for Create, Read, Update, Delete operations.
"""
import json
from playwright.sync_api import sync_playwright

BASE_URL = "https://10.73.17.95:9443"

with open("config/testdata.json") as f:
    td = json.load(f)


def dump(page, label):
    print(f"\n{'='*80}")
    print(f"  {label}  |  URL: {page.url}")
    print(f"{'='*80}")
    for tag in ["input", "select", "textarea"]:
        els = page.query_selector_all(tag)
        if els:
            print(f"\n  <{tag}> ({len(els)}):")
            for el in els:
                a = {}
                for attr in ["name", "type", "id", "placeholder", "class", "value"]:
                    v = el.get_attribute(attr)
                    if v:
                        a[attr] = v
                vis = el.is_visible()
                print(f"    visible={vis!s:5s} {a}")
    btns = page.query_selector_all("button, a.btn, .btn, [role='button'], input[type='submit']")
    if btns:
        print(f"\n  BUTTONS ({len(btns)}):")
        for b in btns:
            t = (b.text_content() or "").strip().replace("\n", " ")[:50]
            vis = b.is_visible()
            eid = b.get_attribute("id") or ""
            cls = b.get_attribute("class") or ""
            href = b.get_attribute("href") or ""
            tag = b.evaluate("e => e.tagName")
            print(f"    visible={vis!s:5s} <{tag}> id={eid!r:20s} class={cls!r:45s} href={href!r:5s} text={t!r}")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(ignore_https_errors=True, viewport={"width": 1920, "height": 1080})
    page = ctx.new_page()

    # ─── LOGIN ───
    print("🔐 LOGIN")
    page.goto(f"{BASE_URL}/#/login", timeout=60000, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    page.wait_for_selector('//input[@name="username"]').fill(td["username"])
    page.wait_for_selector('button.btn-login').click()
    page.wait_for_timeout(1000)
    page.wait_for_selector('//input[@name="password"]').fill(td["password"])
    page.wait_for_selector('button.btn-login').click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(5000)
    print(f"  Post-login URL: {page.url}")

    # Handle setting_up
    if "setting_up" in page.url:
        print("  ⚠️ On setting_up page, waiting...")
        page.wait_for_timeout(10000)
        if "setting_up" in page.url:
            page.goto(f"{BASE_URL}/#/dashboard", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(5000)
    print(f"  Ready URL: {page.url}")

    # ─── SIDEBAR NAVIGATION ───
    print("\n📋 SIDEBAR LINKS:")
    sidebar = page.query_selector_all("nav a, .sidebar a, .nav-link, .menu-item a, a[class*='nav'], a[class*='menu'], .leftbar a, .left-nav a, aside a")
    for s in sidebar:
        t = (s.text_content() or "").strip().replace("\n", " ")[:50]
        href = s.get_attribute("href") or ""
        cls = s.get_attribute("class") or ""
        vis = s.is_visible()
        if t:
            print(f"  visible={vis!s:5s} text={t!r:30s} href={href!r:40s} class={cls!r}")

    # Also check all anchor tags with 'domain' or 'dns' in href
    print("\n🔗 ALL LINKS WITH 'domain' or 'dns':")
    all_links = page.query_selector_all("a")
    for a in all_links:
        href = a.get_attribute("href") or ""
        if "domain" in href.lower() or "dns" in href.lower():
            t = (a.text_content() or "").strip()[:50]
            cls = a.get_attribute("class") or ""
            print(f"  text={t!r:30s} href={href!r:50s} class={cls!r}")

    # ─── DOMAIN LIST ───
    print("\n📋 NAVIGATING TO DOMAIN LIST")
    # Try clicking sidebar link first
    dns_link = page.query_selector("a[href*='dns/domains'], a[href*='#/dns']")
    if dns_link and dns_link.is_visible():
        print("  Clicking sidebar DNS/Domains link...")
        dns_link.click()
        page.wait_for_timeout(5000)
    else:
        page.goto(f"{BASE_URL}/#/dns/domains", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(5000)

    print(f"  Domain list URL: {page.url}")
    page.screenshot(path="screenshots/smart_01_domain_list.png", full_page=True)
    dump(page, "DOMAIN LIST PAGE")

    # Table structure
    print("\n  📊 TABLE STRUCTURE:")
    headers = page.query_selector_all("table thead th, table th")
    for i, h in enumerate(headers):
        print(f"    TH[{i}]: {(h.text_content() or '').strip()!r}")
    rows = page.query_selector_all("table tbody tr")
    print(f"  Rows: {len(rows)}")
    if rows:
        cells = rows[0].query_selector_all("td")
        for i, c in enumerate(cells):
            t = (c.text_content() or "").strip()[:40]
            inner = c.inner_html()[:100]
            print(f"    TD[{i}]: text={t!r:30s} html={inner!r}")

    # ─── CLICK '+ Add Domain' ───
    print("\n➕ CLICKING '+ Add Domain' BUTTON")
    add_btn = page.query_selector(".btn-Addd") or \
              page.query_selector("button:has-text('Add Domain')") or \
              page.query_selector("a:has-text('Add Domain')") or \
              page.query_selector("text='+ Add Domain'")
    if add_btn:
        vis = add_btn.is_visible()
        print(f"  Found add button, visible={vis}")
        if vis:
            add_btn.click()
            page.wait_for_timeout(5000)
            print(f"  After click URL: {page.url}")
            page.screenshot(path="screenshots/smart_02_add_form_top.png", full_page=True)
            dump(page, "ADD DOMAIN FORM")

            # Scroll to bottom
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
            page.screenshot(path="screenshots/smart_03_add_form_bottom.png", full_page=True)

            # Save full HTML
            with open("screenshots/smart_add_form.html", "w") as f:
                f.write(page.content())
            print("  Saved HTML → screenshots/smart_add_form.html")
        else:
            print("  ⚠️ Add button exists but NOT visible")
    else:
        print("  ⚠️ '+ Add Domain' button NOT FOUND")
        # Dump ALL buttons on page for debug
        print("  ALL buttons on page:")
        for b in page.query_selector_all("button, a, .btn"):
            t = (b.text_content() or "").strip()[:40]
            cls = b.get_attribute("class") or ""
            if t:
                print(f"    text={t!r} class={cls!r}")

    # ─── DOMAIN DETAIL (click domain name) ───
    print("\n🔍 DOMAIN DETAIL — clicking a domain name")
    page.goto(f"{BASE_URL}/#/dns/domains", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(5000)
    rows = page.query_selector_all("table tbody tr")
    if rows and len(rows) > 0:
        # Find anchor/link inside the row
        link = rows[0].query_selector("a")
        if link:
            href = link.get_attribute("href") or ""
            text = (link.text_content() or "").strip()
            print(f"  Clicking link: text={text!r} href={href!r}")
            link.click()
        else:
            # Click 2nd td (domain name column)
            tds = rows[0].query_selector_all("td")
            if len(tds) > 1:
                print(f"  Clicking TD[1]: {(tds[1].text_content() or '').strip()!r}")
                tds[1].click()
            else:
                rows[0].click()
        page.wait_for_timeout(5000)
        print(f"  Detail URL: {page.url}")
        page.screenshot(path="screenshots/smart_04_domain_detail.png", full_page=True)
        dump(page, "DOMAIN DETAIL / SHOW PAGE")
    else:
        print("  No rows in domain table")

    # ─── DELETE FLOW: Actions dropdown ───
    print("\n🗑️ DELETE FLOW")
    page.goto(f"{BASE_URL}/#/dns/domains", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(5000)

    # Check a checkbox
    checks = page.query_selector_all('input[name="check"]')
    print(f"  Checkboxes found: {len(checks)}")
    if checks:
        checks[0].click(force=True)
        page.wait_for_timeout(1000)
        page.screenshot(path="screenshots/smart_05_checked.png", full_page=True)

    # Find and click Actions
    actions = page.query_selector("text='Actions'")
    if not actions:
        actions = page.query_selector(".btn-dns")
    if not actions:
        actions = page.query_selector("[class*='dropdown'][class*='dns']")
    if actions:
        print(f"  Actions btn found, visible={actions.is_visible()}")
        actions.click(force=True)
        page.wait_for_timeout(2000)
        page.screenshot(path="screenshots/smart_06_actions_open.png", full_page=True)

        # Dump dropdown items
        items = page.query_selector_all(".dropdown-menu li, .dropdown-menu a, .dropdown-menu button, .dropdown-item, ul.dropdown-menu > *")
        print(f"  Dropdown items ({len(items)}):")
        for it in items:
            t = (it.text_content() or "").strip()
            cls = it.get_attribute("class") or ""
            tag = it.evaluate("e => e.tagName")
            vis = it.is_visible()
            print(f"    visible={vis!s:5s} <{tag}> class={cls!r:30s} text={t!r}")

        # Try clicking Delete
        del_link = page.query_selector(".dropdown-menu >> text='Delete'") or \
                   page.query_selector(".dropdown-menu a:has-text('Delete')") or \
                   page.query_selector("a:has-text('Delete Zone')")
        if del_link:
            print(f"  Clicking delete: {(del_link.text_content() or '').strip()!r}")
            del_link.click()
            page.wait_for_timeout(3000)
            page.screenshot(path="screenshots/smart_07_delete_confirm.png", full_page=True)
            dump(page, "DELETE CONFIRMATION DIALOG")

            # Don't confirm — just cancel
            cancel = page.query_selector(".swal2-cancel") or \
                     page.query_selector("button:has-text('Cancel')") or \
                     page.query_selector("button:has-text('No')")
            if cancel and cancel.is_visible():
                cancel.click()
                page.wait_for_timeout(1000)
        else:
            print("  ⚠️ Delete item not found in dropdown")
    else:
        print("  ⚠️ Actions button NOT found")

    ctx.close()
    browser.close()
    print("\n✅ DONE — check screenshots/ folder")
