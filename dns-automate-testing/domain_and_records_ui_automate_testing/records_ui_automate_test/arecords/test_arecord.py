"""
DNS A-Record UI Management — Test Suite
═══════════════════════════════════════════════════════
Covers CRUD flow plus positive / negative scenarios
for A-records on the zone detail page.

Navigates DIRECTLY to /#/dns/domains/showdomain/<zone_pk> — does not
touch the domain list or create/update the parent zone.
Pre-req: the zone identified by ``arecord_ui.zone_pk`` must already exist.
"""
import pytest
from domain_and_records_ui_automate_testing.records_ui_automate_test.arecords.pages.arecord_page import (
    ARecordPage,
)


# ═══════════════════════════════════════════════════════════════
#  FUNCTIONAL TESTS  (TC-01 to TC-08)
# ═══════════════════════════════════════════════════════════════

class TestFunctional:
    """Core A-record CRUD."""

    # ── TC-01  Create A record with valid prefix + IP ──
    def test_tc01_create_a_record_with_valid_data(self, page, testdata):
        cfg = testdata["arecord_ui"]
        arec = ARecordPage(page, testdata)
        arec.create_record(cfg["zone_pk"], cfg["create_record"])

        assert not arec.is_error_visible(), \
            f"Create failed: {arec.get_error_message()}"
        assert arec.is_record_visible(cfg["create_record"]["domain_prefix"]), \
            "Created A-record not visible in list."

    # ── TC-02  Create A record with a single IP ──
    def test_tc02_create_a_record_single_ip(self, page, testdata):
        cfg = testdata["arecord_ui"]
        arec = ARecordPage(page, testdata)
        arec.create_record(cfg["zone_pk"], cfg["create_record_single"])

        assert not arec.is_error_visible(), \
            f"Single-IP create failed: {arec.get_error_message()}"
        assert arec.is_record_visible(cfg["create_record_single"]["domain_prefix"])

    # ── TC-03  Create apex A record (@) ──
    def test_tc03_create_apex_a_record(self, page, testdata):
        cfg = testdata["arecord_ui"]
        arec = ARecordPage(page, testdata)
        arec.create_record(cfg["zone_pk"], cfg["create_record_apex"])

        assert not arec.is_error_visible(), \
            f"Apex create failed: {arec.get_error_message()}"

    # ── TC-04  Update existing A record ──
    def test_tc04_update_a_record(self, page, testdata):
        cfg = testdata["arecord_ui"]
        arec = ARecordPage(page, testdata)
        update = cfg["update_record"]

        arec.update_record(cfg["zone_pk"], update["domain_prefix"], update)

        assert not arec.is_error_visible(), \
            f"Update failed: {arec.get_error_message()}"

    # ── TC-05  Delete A record with confirmation ──
    def test_tc05_delete_a_record(self, page, testdata):
        cfg = testdata["arecord_ui"]
        arec = ARecordPage(page, testdata)
        prefix = cfg["create_record_single"]["domain_prefix"]

        arec.delete_record(cfg["zone_pk"], prefix)
        arec.go_to_a_records_tab(cfg["zone_pk"])

        assert not arec.is_record_visible(prefix), \
            f"Record '{prefix}' still visible after delete."

    # ── TC-06  Search A record by prefix ──
    def test_tc06_search_a_record(self, page, testdata):
        cfg = testdata["arecord_ui"]
        arec = ARecordPage(page, testdata)
        prefix = cfg["create_record"]["domain_prefix"]

        arec.go_to_a_records_tab(cfg["zone_pk"])
        arec.search_record(prefix)

        assert arec.is_record_visible(prefix), \
            f"Search for '{prefix}' returned no match."

    # ── TC-07  Zone detail page opens A-records tab ──
    def test_tc07_open_a_records_tab(self, page, testdata):
        cfg = testdata["arecord_ui"]
        arec = ARecordPage(page, testdata)
        arec.go_to_a_records_tab(cfg["zone_pk"])

        assert arec.is_on_zone_detail_page(), \
            f"Not on zone detail page, got: {arec.get_current_url()}"

    # ── TC-08  Duplicate A record creation blocked ──
    def test_tc08_duplicate_a_record(self, page, testdata):
        cfg = testdata["arecord_ui"]
        arec = ARecordPage(page, testdata)
        data = cfg["create_record"]

        # Ensure the record exists first
        arec.go_to_a_records_tab(cfg["zone_pk"])
        if not arec.is_record_visible(data["domain_prefix"]):
            arec.create_record(cfg["zone_pk"], data)

        # Attempt duplicate WITHOUT cleanup
        arec.try_create_record_no_cleanup(cfg["zone_pk"], data)
        page.wait_for_timeout(3000)

        body = page.inner_text("body").lower()
        has_dup_msg = "already" in body or "exist" in body or "duplicate" in body
        assert arec.is_error_visible() or has_dup_msg, \
            "Expected duplicate A-record error, but none appeared."


# ═══════════════════════════════════════════════════════════════
#  NEGATIVE TESTS  (TC-09 to TC-14)
# ═══════════════════════════════════════════════════════════════

class TestNegative:
    """Invalid-input tests."""

    # ── TC-09  Create with empty prefix ──
    def test_tc09_create_empty_prefix(self, page, testdata):
        cfg = testdata["arecord_ui"]
        arec = ARecordPage(page, testdata)

        arec.try_create_record_no_cleanup(cfg["zone_pk"], cfg["negative_empty_prefix"])
        page.wait_for_timeout(2000)

        assert arec.is_error_visible() or arec.is_add_record_form_visible(), \
            "Expected validation error for empty prefix."

    # ── TC-10  Create with empty IP list ──
    def test_tc10_create_empty_ip(self, page, testdata):
        cfg = testdata["arecord_ui"]
        arec = ARecordPage(page, testdata)

        arec.try_create_record_no_cleanup(cfg["zone_pk"], cfg["negative_empty_ip"])
        page.wait_for_timeout(2000)

        assert arec.is_error_visible() or arec.is_add_record_form_visible(), \
            "Expected validation error for empty IP list."

    # ── TC-11  Create with invalid IP format ──
    def test_tc11_create_invalid_ip(self, page, testdata):
        cfg = testdata["arecord_ui"]
        arec = ARecordPage(page, testdata)

        arec.try_create_record_no_cleanup(cfg["zone_pk"], cfg["negative_invalid_ip"])
        page.wait_for_timeout(2000)

        assert arec.is_error_visible() or arec.is_add_record_form_visible(), \
            "Expected validation error for invalid IP '999.999.999.999'."

    # ── TC-12  Create with invalid prefix characters ──
    def test_tc12_create_invalid_prefix(self, page, testdata):
        cfg = testdata["arecord_ui"]
        arec = ARecordPage(page, testdata)

        arec.try_create_record_no_cleanup(cfg["zone_pk"], cfg["negative_invalid_prefix"])
        page.wait_for_timeout(2000)

        assert arec.is_error_visible() or arec.is_add_record_form_visible(), \
            "Expected validation error for invalid prefix characters."

    # ── TC-13  Create with non-numeric TTL ──
    def test_tc13_create_invalid_ttl(self, page, testdata):
        cfg = testdata["arecord_ui"]
        arec = ARecordPage(page, testdata)

        arec.try_create_record_no_cleanup(cfg["zone_pk"], cfg["negative_invalid_ttl"])
        page.wait_for_timeout(2000)

        assert arec.is_error_visible() or arec.is_add_record_form_visible(), \
            "Expected validation error for non-numeric TTL."

    # ── TC-14  Save empty Add-Record form ──
    def test_tc14_save_empty_form(self, page, testdata):
        cfg = testdata["arecord_ui"]
        arec = ARecordPage(page, testdata)

        arec.try_save_empty_form(cfg["zone_pk"])
        page.wait_for_timeout(2000)

        assert arec.is_error_visible() or arec.is_add_record_form_visible(), \
            "Expected error when saving empty Add-Record form."


# ═══════════════════════════════════════════════════════════════
#  NON-FUNCTIONAL TESTS  (TC-15)
# ═══════════════════════════════════════════════════════════════

class TestNonFunctional:
    """UI and reliability checks."""

    # ── TC-15  Page reload preserves A-records tab ──
    def test_tc15_page_reload_recovers(self, page, testdata):
        cfg = testdata["arecord_ui"]
        arec = ARecordPage(page, testdata)
        arec.go_to_a_records_tab(cfg["zone_pk"])

        page.reload(wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)

        assert arec.is_on_zone_detail_page(), \
            "Zone detail page did not recover after reload."
