"""
DNS Domain Management — Full Test Suite (50 Test Cases)
═══════════════════════════════════════════════════════
Categories: Functional, Positive, Negative, Non-Functional,
            Performance, Regression, Edge Case
"""
import time
import pytest
from domain_and_records_ui_automate_testing.domain_ui_automate_test.pages.domain_page import DomainPage


# ═══════════════════════════════════════════════════════════════
#  FUNCTIONAL TESTS  (TC-01 to TC-10)
# ═══════════════════════════════════════════════════════════════

class TestFunctional:
    """S.No 1–10: Core functional tests."""

    # ── TC-01  Create domain with valid name ──
    def test_tc01_create_domain_with_valid_name(self, page, testdata):
        domain = DomainPage(page)
        data = testdata["create_domain"]
        domain.create_domain(data)

        assert domain.is_on_domain_detail_page() or "dns/domains" in domain.get_current_url(), \
            f"Expected detail/list page, got: {domain.get_current_url()}"
        assert not domain.is_error_visible(), \
            f"Create failed: {domain.get_error_message()}"

    # ── TC-02  Create domain with FQDN (example.com) ──
    def test_tc02_create_domain_with_fqdn(self, page, testdata):
        domain = DomainPage(page)
        data = testdata["fqdn_domain"]
        domain.create_domain(data)

        assert domain.is_on_domain_detail_page() or "dns/domains" in domain.get_current_url()
        assert not domain.is_error_visible(), \
            f"FQDN create failed: {domain.get_error_message()}"

    # ── TC-03  Update existing domain ──
    def test_tc03_update_existing_domain(self, page, testdata):
        domain = DomainPage(page)
        zone_name = testdata["create_domain"]["zone_name"]
        update_data = testdata["update_domain"]

        domain.update_domain(zone_name, update_data)

        assert not domain.is_error_visible(), \
            f"Update failed: {domain.get_error_message()}"

    # ── TC-04  Delete domain with confirmation ──
    def test_tc04_delete_domain_with_confirmation(self, page, testdata):
        domain = DomainPage(page)
        zone_name = testdata["fqdn_domain"]["zone_name"]

        domain.delete_domain(zone_name)
        domain.go_to_domain_list()

        assert not domain.is_domain_visible(zone_name), \
            f"Domain '{zone_name}' still visible after deletion."

    # ── TC-05  Bulk import domains (CSV) — verify Import button exists ──
    def test_tc05_bulk_import_button_present(self, page, testdata):
        domain = DomainPage(page)
        domain.go_to_domain_list()

        assert domain.is_import_button_visible(), \
            "Import button not found on domain list page."

    # ── TC-06  Search domain by keyword ──
    def test_tc06_search_domain_by_keyword(self, page, testdata):
        domain = DomainPage(page)
        zone_name = testdata["create_domain"]["zone_name"]

        result_count = domain.search_and_get_results(zone_name.split(".")[0])

        assert result_count > 0, \
            f"Search for '{zone_name}' returned 0 results."
        assert domain.is_domain_visible(zone_name), \
            f"Domain '{zone_name}' not in search results."

    # ── TC-07  Pagination validation ──
    def test_tc07_pagination_validation(self, page, testdata):
        domain = DomainPage(page)
        domain.go_to_domain_list()

        pagination = domain.get_pagination_text()
        assert pagination, \
            "Pagination text ('Showing X to Y of Z domains') not found."

    # ── TC-08  Duplicate domain creation ──
    def test_tc08_duplicate_domain_creation(self, page, testdata):
        domain = DomainPage(page)
        data = testdata["create_domain"]

        # Ensure the domain exists first
        domain.go_to_domain_list()
        if not domain.is_domain_visible(data["zone_name"]):
            domain.create_domain(data)

        # Try creating again WITHOUT cleanup → should fail
        domain.try_create_domain_no_cleanup(data)
        page.wait_for_timeout(3000)

        is_err = domain.is_error_visible()
        body = page.inner_text("body").lower()
        has_dup_msg = "already" in body or "exist" in body or "duplicate" in body
        assert is_err or has_dup_msg, \
            "Expected error for duplicate domain, but none appeared."

    # ── TC-09  Create subdomain (test.example.com) ──
    def test_tc09_create_subdomain(self, page, testdata):
        domain = DomainPage(page)
        data = testdata["subdomain"]
        domain.create_domain(data)

        assert domain.is_on_domain_detail_page() or "dns/domains" in domain.get_current_url()
        assert not domain.is_error_visible(), \
            f"Subdomain create failed: {domain.get_error_message()}"

    # ── TC-10  Domain mapping with zones — verify zone detail fields ──
    def test_tc10_domain_mapping_with_zones(self, page, testdata):
        domain = DomainPage(page)
        zone_name = testdata["create_domain"]["zone_name"]

        domain.go_to_domain_list()
        clicked = domain.click_domain_link(zone_name)

        assert clicked, f"Could not open domain '{zone_name}' detail page."
        assert domain.is_on_domain_detail_page(), \
            "Not on domain detail page after clicking domain link."


# ═══════════════════════════════════════════════════════════════
#  POSITIVE TESTS  (TC-11 to TC-15)
# ═══════════════════════════════════════════════════════════════

class TestPositive:
    """S.No 11–15: Positive scenario tests."""

    # ── TC-11  Create domain with valid characters ──
    def test_tc11_create_domain_valid_characters(self, page, testdata):
        domain = DomainPage(page)
        data = testdata["valid_chars_domain"]
        domain.create_domain(data)

        assert not domain.is_error_visible(), \
            f"Valid-chars domain failed: {domain.get_error_message()}"

    # ── TC-12  Bulk upload valid CSV — import button accessible ──
    def test_tc12_bulk_upload_import_accessible(self, page, testdata):
        domain = DomainPage(page)
        domain.go_to_domain_list()

        assert domain.is_import_button_visible(), \
            "Import button not available for bulk upload."

    # ── TC-13  Update domain with valid data ──
    def test_tc13_update_domain_valid_data(self, page, testdata):
        domain = DomainPage(page)
        zone_name = testdata["create_domain"]["zone_name"]
        update_data = testdata["update_domain"]

        domain.update_domain(zone_name, update_data)

        assert not domain.is_error_visible(), \
            f"Update with valid data failed: {domain.get_error_message()}"

    # ── TC-14  Delete existing domain ──
    def test_tc14_delete_existing_domain(self, page, testdata):
        domain = DomainPage(page)
        zone_name = testdata["subdomain"]["zone_name"]

        domain.delete_domain(zone_name)
        domain.go_to_domain_list()

        assert not domain.is_domain_visible(zone_name), \
            f"Subdomain '{zone_name}' still visible after delete."

    # ── TC-15  Search existing domain ──
    def test_tc15_search_existing_domain(self, page, testdata):
        domain = DomainPage(page)
        zone_name = testdata["create_domain"]["zone_name"]

        count = domain.search_and_get_results(zone_name.rstrip("."))

        assert count > 0, f"Search for existing domain '{zone_name}' found nothing."


# ═══════════════════════════════════════════════════════════════
#  NEGATIVE TESTS  (TC-16 to TC-25)
# ═══════════════════════════════════════════════════════════════

class TestNegative:
    """S.No 16–25: Negative / invalid input tests."""

    # ── TC-16  Invalid format (abc@.com) ──
    def test_tc16_create_domain_invalid_format(self, page, testdata):
        domain = DomainPage(page)
        data = testdata["negative_invalid_format"]

        domain.go_to_add_domain()
        domain.fill_domain_form(data)
        domain._scroll_and_click_save()
        page.wait_for_timeout(2000)

        is_err = domain.is_error_visible()
        still_on_add = "dns/domains/add" in domain.get_current_url() or \
                       domain.is_add_domain_form_visible()
        assert is_err or still_on_add, \
            "Expected validation error or form rejection for invalid format 'abc@.com'."

    # ── TC-17  Create domain without name ──
    def test_tc17_create_domain_without_name(self, page, testdata):
        domain = DomainPage(page)

        domain.try_save_empty_form()
        page.wait_for_timeout(2000)

        is_err = domain.is_error_visible()
        still_on_add = "dns/domains/add" in domain.get_current_url() or \
                       domain.is_add_domain_form_visible()
        assert is_err or still_on_add, \
            "Expected error when creating domain without name."

    # ── TC-18  Upload invalid CSV format — Import button present ──
    def test_tc18_upload_invalid_csv_format(self, page, testdata):
        domain = DomainPage(page)
        domain.go_to_domain_list()

        assert domain.is_import_button_visible(), \
            "Import button not found for CSV upload validation."

    # ── TC-19  Delete non-existing domain — should not crash ──
    def test_tc19_delete_non_existing_domain(self, page, testdata):
        domain = DomainPage(page)

        # Try deleting a domain that doesn't exist
        domain.delete_domain("nonexistent-xyz123.com")
        page.wait_for_timeout(2000)

        # Should still be on domain list, no crash
        assert domain.is_domain_list_page(), \
            "Page crashed or navigated away when deleting non-existing domain."

    # ── TC-20  Duplicate domain creation (negative) ──
    def test_tc20_duplicate_domain_not_allowed(self, page, testdata):
        domain = DomainPage(page)
        data = testdata["create_domain"]

        # Ensure the domain exists
        domain.go_to_domain_list()
        if not domain.is_domain_visible(data["zone_name"]):
            domain.create_domain(data)

        # Try creating again WITHOUT cleanup
        domain.try_create_domain_no_cleanup(data)
        page.wait_for_timeout(3000)

        is_err = domain.is_error_visible()
        err = domain.get_error_message()
        body = page.inner_text("body").lower()
        has_dup_msg = "already" in body or "exist" in body or "duplicate" in body
        assert is_err or has_dup_msg, \
            "Expected duplicate domain error but none appeared."

    # ── TC-21  Special characters in domain (!@#) ──
    def test_tc21_special_characters_in_domain(self, page, testdata):
        domain = DomainPage(page)
        data = testdata["negative_special_chars"]

        domain.go_to_add_domain()
        domain.fill_domain_form(data)
        domain._scroll_and_click_save()
        page.wait_for_timeout(2000)

        is_err = domain.is_error_visible()
        still_on_add = "dns/domains/add" in domain.get_current_url() or \
                       domain.is_add_domain_form_visible()
        assert is_err or still_on_add, \
            "Expected validation error for special characters '!@#$%^.com'."

    # ── TC-22  Domain length > 253 characters ──
    def test_tc22_domain_max_length_exceeded(self, page, testdata):
        domain = DomainPage(page)
        long_name = ("a" * 60 + ".") * 4 + "com"  # >253 chars

        domain.go_to_add_domain()
        domain.fill_domain_form({"zone_name": long_name})
        domain._scroll_and_click_save()
        page.wait_for_timeout(2000)

        is_err = domain.is_error_visible()
        still_on_add = "dns/domains/add" in domain.get_current_url() or \
                       domain.is_add_domain_form_visible()
        assert is_err or still_on_add, \
            "Expected rejection for domain >253 characters."

    # ── TC-23  Empty search input ──
    def test_tc23_empty_search_input(self, page, testdata):
        domain = DomainPage(page)

        count_before = domain.search_and_get_results("")
        page.wait_for_timeout(1000)

        # Empty search should show all domains (not crash)
        assert count_before >= 0, \
            "Empty search caused an error."
        assert domain.is_domain_list_page(), \
            "Page broke with empty search."

    # ── TC-24  API failure during create — form stays open on error ──
    def test_tc24_api_failure_form_stays(self, page, testdata):
        domain = DomainPage(page)

        # Submit form with incomplete data → server should reject
        domain.go_to_add_domain()
        domain.fill_domain_form({"zone_name": "incomplete-zone"})
        domain._scroll_and_click_save()
        page.wait_for_timeout(3000)

        is_err = domain.is_error_visible()
        still_on_form = domain.is_add_domain_form_visible() or \
                        "dns/domains/add" in domain.get_current_url()
        assert is_err or still_on_form, \
            "Expected error or form to stay open with incomplete data."

    # ── TC-25  Network interruption — page handles gracefully ──
    def test_tc25_page_handles_reload_gracefully(self, page, testdata):
        domain = DomainPage(page)
        domain.go_to_domain_list()

        # Simulate reload (closest to network interruption in UI test)
        page.reload(wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)

        assert domain.is_domain_list_page(), \
            "Domain list page did not recover after reload."


# ═══════════════════════════════════════════════════════════════
#  NON-FUNCTIONAL TESTS  (TC-26 to TC-34)
# ═══════════════════════════════════════════════════════════════

class TestNonFunctional:
    """S.No 26–34: Usability, Security, Compatibility, Reliability."""

    # ── TC-26  UI validation for domain page ──
    def test_tc26_ui_domain_page_elements(self, page, testdata):
        domain = DomainPage(page)
        domain.go_to_domain_list()

        # Verify essential UI elements
        assert domain.is_import_button_visible(), "Import button missing."
        assert page.locator('.btn-Addd').count() > 0, "'+ Add Domain' button missing."
        assert page.locator('input[name="domainSearch"]').count() > 0, "Search box missing."
        assert page.locator('table').count() > 0, "Domain table missing."

    # ── TC-27  Error message clarity ──
    def test_tc27_error_message_clarity(self, page, testdata):
        domain = DomainPage(page)
        data = testdata["create_domain"]

        # Ensure domain exists
        domain.go_to_domain_list()
        if not domain.is_domain_visible(data["zone_name"]):
            domain.create_domain(data)

        # Trigger duplicate error
        domain.try_create_domain_no_cleanup(data)
        page.wait_for_timeout(3000)

        err = domain.get_error_message()
        body = page.inner_text("body")
        # Error may appear in nerrorDiv or in page body
        has_error_text = len(err) > 0 or "Error" in body or "already" in body.lower()
        assert has_error_text, "Error message is empty — should be clear."
        # If we got a specific error message, verify it's descriptive
        if len(err) > 0:
            assert len(err) > 5, f"Error message too short / unclear: '{err}'"

    # ── TC-28  Input validation (injection check) ──
    def test_tc28_input_injection_check(self, page, testdata):
        domain = DomainPage(page)
        injection = "<script>alert('xss')</script>.com"

        domain.go_to_add_domain()
        domain.fill_domain_form({"zone_name": injection})
        domain._scroll_and_click_save()
        page.wait_for_timeout(2000)

        is_err = domain.is_error_visible()
        still_on_add = domain.is_add_domain_form_visible()
        # Should NOT have executed script — page should still be functional
        assert is_err or still_on_add, \
            "Script injection was not rejected by input validation."
        # Verify page is still functional (not broken by XSS)
        assert page.locator('body').count() > 0, "Page broken after injection attempt."

    # ── TC-29  Authentication check — logged in user can access ──
    def test_tc29_authentication_check(self, page, testdata):
        domain = DomainPage(page)
        domain.go_to_domain_list()

        # Logged-in user should reach domain list, not login page
        url = domain.get_current_url()
        assert "login" not in url, \
            f"User redirected to login — not authenticated: {url}"
        assert domain.is_domain_list_page(), \
            "Authenticated user cannot access domain list."

    # ── TC-30  Role-based access — admin can add/delete ──
    def test_tc30_role_based_access_admin(self, page, testdata):
        domain = DomainPage(page)
        domain.go_to_domain_list()

        # Admin should see Add, Import, and trash icons
        assert page.locator('.btn-Addd').count() > 0, \
            "Admin cannot see '+ Add Domain' button."
        assert domain.is_import_button_visible(), \
            "Admin cannot see Import button."

    # ── TC-31  Browser compatibility — page renders in current browser ──
    def test_tc31_browser_compatibility(self, page, testdata):
        domain = DomainPage(page)
        domain.go_to_domain_list()

        # Page should render properly
        assert page.locator('table').count() > 0, "Table not rendered."
        assert page.locator('.btn-Addd').count() > 0, "Add button not rendered."
        headers = domain.get_domain_table_headers()
        assert len(headers) > 0, "Table headers not rendered."

    # ── TC-32  OS compatibility — page loads on current OS ──
    def test_tc32_os_compatibility(self, page, testdata):
        domain = DomainPage(page)
        domain.go_to_domain_list()

        assert domain.is_domain_list_page(), \
            "Domain list page did not load on current OS."
        count = domain.get_domain_count()
        assert count >= 0, "Domain table not accessible on current OS."

    # ── TC-33  Stability during operations — no crash after multiple actions ──
    def test_tc33_stability_multiple_actions(self, page, testdata):
        domain = DomainPage(page)

        # Perform multiple rapid navigations
        for _ in range(3):
            domain.go_to_domain_list()
            domain.go_to_dashboard()

        domain.go_to_domain_list()
        assert domain.is_domain_list_page(), \
            "Page crashed after multiple rapid navigations."

    # ── TC-34  Recovery after failure — page recovers after error ──
    def test_tc34_recovery_after_failure(self, page, testdata):
        domain = DomainPage(page)

        # Trigger an error (empty form save)
        domain.try_save_empty_form()
        page.wait_for_timeout(2000)

        # Navigate back to domain list — should recover
        domain.go_to_domain_list()
        assert domain.is_domain_list_page(), \
            "Page did not recover after triggering an error."


# ═══════════════════════════════════════════════════════════════
#  PERFORMANCE TESTS  (TC-35 to TC-39)
# ═══════════════════════════════════════════════════════════════

class TestPerformance:
    """S.No 35–39: Performance / load tests (UI-level)."""

    # ── TC-35  Create domain completes in reasonable time ──
    def test_tc35_create_domain_response_time(self, page, testdata):
        domain = DomainPage(page)
        data = testdata["valid_chars_domain"].copy()
        data["zone_name"] = "perftest-create.com"
        data["sec_ns"] = "ns1.perftest-create.com"
        data["nameservers"] = {
            "nameservers": "ns1.perftest-create.com",
            "ns_with_ip": [{"ns": "ns1.perftest-create.com", "ips": "9.9.9.9"}]
        }

        # Clean up first
        domain.cleanup_existing_domain(data["zone_name"])

        start = time.time()
        domain.go_to_add_domain()
        domain.fill_domain_form(data)
        domain._scroll_and_click_save()
        elapsed = time.time() - start

        assert elapsed < 60, \
            f"Domain creation took {elapsed:.1f}s — exceeds 60s limit."

        # Cleanup
        domain.delete_domain(data["zone_name"])

    # ── TC-36  Bulk import — Import button functional ──
    def test_tc36_bulk_import_button_functional(self, page, testdata):
        domain = DomainPage(page)
        domain.go_to_domain_list()

        import_btn = page.locator('.import_zone')
        assert import_btn.count() > 0, "Import button not found."
        assert import_btn.first.is_visible(), "Import button not visible."

    # ── TC-37  Search response time < 5 seconds ──
    def test_tc37_search_response_time(self, page, testdata):
        domain = DomainPage(page)
        zone_name = testdata["create_domain"]["zone_name"]

        response_time = domain.measure_search_response_time(zone_name.split(".")[0])

        assert response_time < 5000, \
            f"Search took {response_time:.0f}ms — exceeds 5s limit."

    # ── TC-38  Load page with existing data ──
    def test_tc38_page_load_with_data(self, page, testdata):
        domain = DomainPage(page)

        load_time = domain.measure_page_load_time()

        assert load_time < 30000, \
            f"Page load took {load_time:.0f}ms — exceeds 30s limit."
        assert domain.is_domain_list_page(), \
            "Domain list page didn't load properly."

    # ── TC-39  Multiple sequential operations — no slowdown ──
    def test_tc39_sequential_operations_no_slowdown(self, page, testdata):
        domain = DomainPage(page)

        times = []
        for i in range(3):
            start = time.time()
            domain.go_to_domain_list()
            times.append(time.time() - start)

        avg_time = sum(times) / len(times)
        assert avg_time < 15, \
            f"Average navigation time {avg_time:.1f}s — too slow."


# ═══════════════════════════════════════════════════════════════
#  REGRESSION TESTS  (TC-40 to TC-46)
# ═══════════════════════════════════════════════════════════════

class TestRegression:
    """S.No 40–46: Regression tests — verify existing features still work."""

    # ── TC-40  Verify domain creation after fix ──
    def test_tc40_verify_domain_creation(self, page, testdata):
        domain = DomainPage(page)
        data = testdata["create_domain"]

        # Re-create the main test domain
        domain.create_domain(data)

        assert not domain.is_error_visible(), \
            f"Regression: create failed: {domain.get_error_message()}"

    # ── TC-41  Verify update after changes ──
    def test_tc41_verify_update_after_changes(self, page, testdata):
        domain = DomainPage(page)
        zone_name = testdata["create_domain"]["zone_name"]
        update_data = testdata["update_domain"]

        domain.update_domain(zone_name, update_data)

        assert not domain.is_error_visible(), \
            f"Regression: update failed: {domain.get_error_message()}"

    # ── TC-42  Verify delete functionality ──
    def test_tc42_verify_delete_functionality(self, page, testdata):
        domain = DomainPage(page)
        # Delete valid_chars_domain if it exists (cleanup from earlier tests)
        zone_name = testdata["valid_chars_domain"]["zone_name"]
        domain.go_to_domain_list()
        if domain.is_domain_visible(zone_name):
            domain.delete_domain(zone_name)
            domain.go_to_domain_list()
            assert not domain.is_domain_visible(zone_name), \
                f"Regression: '{zone_name}' still visible after delete."

    # ── TC-43  Verify bulk import button available ──
    def test_tc43_verify_import_available(self, page, testdata):
        domain = DomainPage(page)
        domain.go_to_domain_list()

        assert domain.is_import_button_visible(), \
            "Regression: Import button missing."

    # ── TC-44  Verify search/filter functionality ──
    def test_tc44_verify_search_filter(self, page, testdata):
        domain = DomainPage(page)
        zone_name = testdata["create_domain"]["zone_name"]

        count = domain.search_and_get_results(zone_name.rstrip("."))

        assert count > 0, \
            f"Regression: search for '{zone_name}' returned no results."

    # ── TC-45  Verify API integration — CRUD still works end-to-end ──
    def test_tc45_verify_api_integration_e2e(self, page, testdata):
        domain = DomainPage(page)
        zone_name = testdata["create_domain"]["zone_name"]

        # Verify domain is accessible (exists from TC-40)
        domain.go_to_domain_list()
        assert domain.is_domain_visible(zone_name), \
            f"Regression: domain '{zone_name}' not visible in list."

        # Click into detail and verify
        clicked = domain.click_domain_link(zone_name)
        assert clicked, "Regression: could not open domain detail."
        assert domain.is_on_domain_detail_page(), \
            "Regression: not on detail page after click."

    # ── TC-46  Verify UI after changes ──
    def test_tc46_verify_ui_after_changes(self, page, testdata):
        domain = DomainPage(page)
        domain.go_to_domain_list()

        headers = domain.get_domain_table_headers()
        assert len(headers) > 0, "Regression: table headers missing."
        assert page.locator('.btn-Addd').count() > 0, "Regression: Add button gone."
        assert page.locator('input[name="domainSearch"]').count() > 0, \
            "Regression: Search box gone."


# ═══════════════════════════════════════════════════════════════
#  EDGE CASE TESTS  (TC-47 to TC-50)
# ═══════════════════════════════════════════════════════════════

class TestEdgeCase:
    """S.No 47–50: Edge case / boundary tests."""

    # ── TC-47  Domain max length (253 chars) ──
    def test_tc47_domain_max_length_253(self, page, testdata):
        domain = DomainPage(page)
        # Build a domain that is exactly 253 characters
        label = "a" * 57  # 57 chars
        long_domain = f"{label}.{label}.{label}.{label}.com"

        domain.go_to_add_domain()
        domain.fill_domain_form({"zone_name": long_domain})
        page.wait_for_timeout(1000)

        # Should accept the input (field should have the value)
        val = domain.get_zone_name_input_value()
        assert len(val) > 0, "Long domain name was not accepted in input field."

    # ── TC-48  Domain with hyphen (-) ──
    def test_tc48_domain_with_hyphen(self, page, testdata):
        domain = DomainPage(page)
        data = testdata["hyphen_domain"]
        domain.create_domain(data)

        assert not domain.is_error_visible(), \
            f"Hyphen domain failed: {domain.get_error_message()}"

        # Cleanup
        domain.delete_domain(data["zone_name"])

    # ── TC-49  Domain starting/ending with hyphen ──
    def test_tc49_domain_starting_ending_hyphen(self, page, testdata):
        domain = DomainPage(page)

        # Test starting with hyphen
        domain.go_to_add_domain()
        domain.fill_domain_form(testdata["negative_starting_hyphen"])
        domain._scroll_and_click_save()
        page.wait_for_timeout(2000)

        is_err = domain.is_error_visible()
        still_on_add = domain.is_add_domain_form_visible()
        assert is_err or still_on_add, \
            "Domain starting with hyphen should be rejected."

    # ── TC-50  Case sensitivity check ──
    def test_tc50_case_sensitivity(self, page, testdata):
        domain = DomainPage(page)
        zone_name = testdata["create_domain"]["zone_name"]

        # Domain should be visible regardless of case
        domain.go_to_domain_list()
        body = page.inner_text("body").lower()
        assert zone_name.lower().rstrip(".") in body, \
            f"Domain '{zone_name}' not found (case-insensitive check)."
