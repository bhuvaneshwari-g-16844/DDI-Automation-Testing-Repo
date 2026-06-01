"""
UI Test — Settings ▸ Servers ▸ Configuration ▸ Edit (id=3)
==========================================================
Target URL pattern (the host comes from DNS_BASE_URL):
    {BASE_URL}/#/settings/servers/configuration/edit/3

Run:
    DNS_BASE_URL=https://10.63.14.98:9443 \
        pytest -s domain_and_records_ui_automate_testing/test_server_configuration_edit.py
"""
import os
import re
import pytest


BASE_URL = os.environ.get("DNS_BASE_URL", "https://10.72.51.96:9443").rstrip("/")
SERVER_ID = os.environ.get("DNS_SERVER_CONFIG_ID", "3")
EDIT_URL = f"{BASE_URL}/#/settings/servers/configuration/edit/{SERVER_ID}"


def _goto_edit_page(page):
    page.goto(EDIT_URL, wait_until="domcontentloaded", timeout=60000)
    # SPA route — wait for the editor to actually render
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2500)


# ─────────────────────────────────────────────────────────────────
#  TC-01  Page loads on the expected URL
# ─────────────────────────────────────────────────────────────────
def test_tc01_edit_page_loads(page):
    _goto_edit_page(page)

    current = page.url
    assert f"/settings/servers/configuration/edit/{SERVER_ID}" in current, \
        f"Did not land on edit page. Current URL: {current}"


# ─────────────────────────────────────────────────────────────────
#  TC-02  Edit form is rendered (at least one input + Save button)
# ─────────────────────────────────────────────────────────────────
def test_tc02_edit_form_is_visible(page):
    _goto_edit_page(page)

    inputs = page.locator("input:visible, select:visible, textarea:visible")
    assert inputs.count() > 0, "Edit form has no visible inputs."

    save = page.locator(
        'button:has-text("Save"), button:has-text("Update"), '
        'button[type="submit"]:visible'
    )
    assert save.count() > 0, "Save/Update button not found on edit page."


# ─────────────────────────────────────────────────────────────────
#  TC-03  Cancel returns to the configuration list
# ─────────────────────────────────────────────────────────────────
def test_tc03_cancel_returns_to_list(page):
    _goto_edit_page(page)

    cancel = page.locator(
        'button:has-text("Cancel"), a:has-text("Cancel"), '
        'button:has-text("Back"), a:has-text("Back")'
    )
    if cancel.count() == 0:
        pytest.skip("No Cancel/Back control rendered on this page.")

    cancel.first.click()
    page.wait_for_timeout(2000)

    assert "edit/" not in page.url, \
        f"Still on edit page after Cancel: {page.url}"


# ─────────────────────────────────────────────────────────────────
#  TC-04  Save without changes does not surface an error
# ─────────────────────────────────────────────────────────────────
def test_tc04_save_without_changes_is_clean(page):
    _goto_edit_page(page)

    save = page.locator(
        'button:has-text("Save"), button:has-text("Update"), button[type="submit"]'
    ).filter(has_not=page.locator("[disabled]"))

    visible_save = None
    for i in range(save.count()):
        btn = save.nth(i)
        try:
            if btn.is_visible():
                visible_save = btn
                break
        except Exception:
            continue

    if visible_save is None:
        pytest.skip("No visible Save/Update button rendered.")

    try:
        visible_save.scroll_into_view_if_needed(timeout=3000)
    except Exception:
        pass
    visible_save.click(timeout=5000)
    page.wait_for_timeout(3000)

    body = page.inner_text("body").lower()
    has_error = bool(re.search(r"\b(error|failed|invalid)\b", body))
    # A toast/banner with the word "success" is also acceptable
    has_success = "success" in body or "updated" in body or "saved" in body

    assert has_success or not has_error, \
        f"Save reported an error without any changes (no success banner either). URL={page.url}"
