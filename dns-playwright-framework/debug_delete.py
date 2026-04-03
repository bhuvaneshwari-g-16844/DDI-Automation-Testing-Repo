"""Debug: Inspect the info box that appears after clicking trash icon."""
import json
from playwright.sync_api import sync_playwright

BASE_URL = "https://10.73.17.95:9443"

with open("config/testdata.json") as f:
    td = json.load(f)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=500)
    ctx = browser.new_context(ignore_https_errors=True, no_viewport=True)
    page = ctx.new_page()

    # Login
    page.goto(f"{BASE_URL}/#/login", timeout=60000, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    page.wait_for_selector('//input[@name="username"]').fill(td["username"])
    page.wait_for_selector('button.btn-login').click()
    page.wait_for_timeout(1000)
    page.wait_for_selector('//input[@name="password"]').fill(td["password"])
    page.wait_for_selector('button.btn-login').click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)
    if "setting_up" in page.url:
        page.wait_for_timeout(5000)
        if "setting_up" in page.url:
            page.goto(f"{BASE_URL}/#/dashboard", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)

    # Go to domain list
    page.goto(f"{BASE_URL}/#/dns/domains", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)

    # Find apple.com row and click trash
    row = page.locator("tr:has-text('apple.com')")
    print(f"=== Rows with apple.com: {row.count()}")
    if row.count() > 0:
        trash = row.first.locator('i.fa-trash-alt, i[title="Delete"]')
        print(f"=== Trash icons in row: {trash.count()}")
        if trash.count() > 0:
            print(f"=== Trash HTML: {trash.first.evaluate('el => el.outerHTML')}")
            trash.first.click(force=True)
            page.wait_for_timeout(3000)
            page.screenshot(path="screenshots/debug_infobox.png")

            # Capture entire page HTML looking for dialogs
            info = page.evaluate("""() => {
                const result = {};
                const selectors = [
                    '.swal2-container', '.swal2-popup', '.swal2-modal',
                    '.modal', '.modal-dialog', '.modal-content',
                    '[role="dialog"]', '[role="alertdialog"]',
                    '.info_box', '.infobox', '.confirm-box', '.confirm-dialog',
                    '.bootbox', '.bootbox-confirm',
                    '.noty_body', '.noty_bar',
                    '.sweet-alert', '.sweet-overlay',
                    '.jconfirm', '.jconfirm-box',
                    '.ember-modal-dialog', '.ember-modal-overlay',
                    '.popup', '.overlay',
                ];
                for (const sel of selectors) {
                    const els = document.querySelectorAll(sel);
                    if (els.length > 0) {
                        result[sel] = [];
                        for (const el of els) {
                            result[sel].push({
                                visible: el.offsetParent !== null || getComputedStyle(el).display !== 'none',
                                text: el.textContent.substring(0, 300),
                                html: el.innerHTML.substring(0, 500),
                                classes: el.className
                            });
                        }
                    }
                }
                result['_visible_buttons'] = [];
                document.querySelectorAll('button, a.btn, .btn, input[type="button"]').forEach(b => {
                    if (b.offsetParent !== null) {
                        result['_visible_buttons'].push({
                            tag: b.tagName,
                            text: b.textContent.trim().substring(0, 100),
                            classes: b.className,
                            type: b.type || '',
                            id: b.id || ''
                        });
                    }
                });
                return result;
            }""")

            for key, val in info.items():
                print(f"\n=== {key}: {len(val)} element(s)")
                for item in val[:5]:
                    print(f"    {json.dumps(item, indent=2)[:300]}")

    page.wait_for_timeout(2000)
    ctx.close()
    browser.close()
