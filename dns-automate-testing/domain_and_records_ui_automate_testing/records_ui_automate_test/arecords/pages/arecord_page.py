"""Page Object for DNS A-Record CRUD operations (UI).

Uses the REAL routes discovered by UI inspection:
  /#/dns/domains/showdomain/<zone_pk>   — A-record list page
  /#/dns/a_add/<zone_pk>                — Add A-record form
  (Edit opens via clicking the pencil icon on a row.)

Real form selectors (from the live Ember app):
  input[name="domain_name"]   — record prefix/name
  input[name="domain_ttl"]    — TTL
  span.addRec                 — "Add IP" button (repeat per IP)
  #saveBttn                   — Save / Save and Continue
  tr#a_<id>                   — record row
  td.actions i.fa-edit        — edit icon
  td.actions i.fa-trash-alt   — delete icon
  .cusCnfrmBtn_yes            — confirm-delete button

IMPORTANT: goto() to /#/dns/domains/showdomain/<pk> gets redirected to
/#/dashboard by Ember's router. ``window.location.href = ...`` works.
"""

import json
import os
import re


class ARecordPage:
    """Page Object for A-record CRUD on the zone detail page."""

    BASE_URL = "https://10.72.51.96:9443"
    DASHBOARD_URL = BASE_URL + "/#/dashboard"
    DOMAINS_URL = BASE_URL + "/#/dns/domains"

    def __init__(self, page, testdata=None):
        self.page = page
        self._testdata = testdata

    # ─────────── SESSION / RE-LOGIN ───────────

    def _get_credentials(self):
        if self._testdata:
            return self._testdata
        config_path = os.path.normpath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "..", "config", "testdata.json"
        ))
        if os.path.exists(config_path):
            with open(config_path) as f:
                return json.load(f)
        return None

    def _is_on_login_page(self):
        url = self.page.url.lower()
        if "login" in url:
            return True
        username_input = self.page.locator('//input[@name="username"]')
        login_btn = self.page.locator('button.btn-login')
        return username_input.count() > 0 and login_btn.count() > 0

    def _wait_out_setting_up(self, max_wait_s=60):
        """The DDI backend briefly redirects to /#/setting_up; wait it out."""
        for _ in range(max_wait_s // 2):
            if "setting_up" not in self.page.url and "login" not in self.page.url:
                return
            self.page.wait_for_timeout(2000)

    def _dismiss_page_tips(self):
        """Close the 'Page Tips?' help modal that overlays Add/Edit forms.

        The Ember DDI app pops up a ``custom-overlay-model`` help dialog with a
        red X close button on many pages (observed on /#/dns/a_add/<pk> and
        /#/dns/domains/showdomain/<pk>). It intercepts every click until
        dismissed.
        """
        try:
            clicked = self.page.evaluate("""() => {
                const selectors = [
                    '.custom-overlay-model .fa-times',
                    '.custom-overlay-model .close',
                    '.custom-overlay-model [class*="close"]',
                    '.pageTips .fa-times',
                    '.pageTips .close',
                    '.tip-close',
                    '.page-tip-close',
                ];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el && el.offsetParent !== null) {
                        el.click();
                        return true;
                    }
                }
                // Fallback: any visible fa-times inside an overlay-model
                const overlay = document.querySelector('.custom-overlay-model');
                if (overlay) {
                    const icon = overlay.querySelector('i, span, button, a');
                    if (icon) { icon.click(); return true; }
                }
                return false;
            }""")
            if clicked:
                self.page.wait_for_timeout(800)
        except Exception:
            pass

    def _wait_for_overlay_gone(self, max_wait_s=20):
        """Wait for (or dismiss) the custom-overlay-model that blocks clicks.

        First tries to close the Page Tips dialog. If it persists, force-hides
        the overlay via CSS so the test can interact with underlying controls.
        """
        # First attempt: click the close button on the Page Tips dialog
        self._dismiss_page_tips()

        for _ in range(max_wait_s * 4):
            gone = self.page.evaluate("""() => {
                const els = document.querySelectorAll('.custom-overlay-model, .loader-overlay, .loading-overlay, .pageTips');
                for (const el of els) {
                    const s = window.getComputedStyle(el);
                    if (s.display !== 'none' && s.visibility !== 'hidden' && el.offsetParent !== null) {
                        return false;
                    }
                }
                return true;
            }""")
            if gone:
                return True
            self.page.wait_for_timeout(250)

        # Last resort: force-hide so the test can proceed
        self.page.evaluate("""() => {
            document.querySelectorAll('.custom-overlay-model, .loader-overlay, .loading-overlay, .pageTips')
                .forEach(el => {
                    el.style.setProperty('display', 'none', 'important');
                    el.style.setProperty('pointer-events', 'none', 'important');
                });
        }""")
        return False

    def _re_login(self):
        creds = self._get_credentials()
        if not creds:
            return
        self.page.goto(f"{self.BASE_URL}/#/login", timeout=60000,
                       wait_until="domcontentloaded")
        self.page.wait_for_timeout(2000)

        self.page.evaluate("""() => {
            const selects = document.querySelectorAll('select');
            for (const sel of selects) {
                for (const opt of sel.options) {
                    if (opt.text.toLowerCase().includes('local')) {
                        sel.value = opt.value;
                        sel.dispatchEvent(new Event('change', { bubbles: true }));
                        break;
                    }
                }
            }
        }""")
        self.page.wait_for_timeout(500)

        self.page.wait_for_selector('//input[@name="username"]').fill(creds["username"])
        self.page.wait_for_selector('button.btn-login').click()
        self.page.wait_for_timeout(1000)
        self.page.wait_for_selector('//input[@name="password"]').fill(creds["password"])
        self.page.wait_for_selector('button.btn-login').click()
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(3000)
        self._wait_out_setting_up()

    def _ensure_logged_in(self):
        if self._is_on_login_page():
            self._re_login()

    # ─────────── NAVIGATION ───────────

    def go_to_records_list(self, zone_pk):
        """Navigate directly to the A-record list page for ``zone_pk``.

        Must use ``window.location.href`` — playwright ``goto`` gets redirected
        back to ``/#/dashboard`` by Ember's auth router.
        """
        self._wait_out_setting_up()
        target = f"{self.BASE_URL}/#/dns/domains/showdomain/{zone_pk}"
        self.page.evaluate(f"window.location.href = '{target}'")
        self.page.wait_for_timeout(5000)
        self._ensure_logged_in()

        if f"showdomain/{zone_pk}" not in self.page.url:
            self.page.evaluate(f"window.location.href = '{target}'")
            self.page.wait_for_timeout(5000)
        self._wait_for_overlay_gone()

    # Alias kept for backward compatibility with existing tests
    def go_to_a_records_tab(self, zone_pk):
        self.go_to_records_list(zone_pk)
        return True

    def go_to_add_record_form(self, zone_pk):
        """Navigate to the Add-A-Record form at /#/dns/a_add/<zone_pk>."""
        self._wait_out_setting_up()
        target = f"{self.BASE_URL}/#/dns/a_add/{zone_pk}"
        self.page.evaluate(f"window.location.href = '{target}'")
        self.page.wait_for_timeout(5000)
        self._ensure_logged_in()

        if f"a_add/{zone_pk}" not in self.page.url:
            self.page.evaluate(f"window.location.href = '{target}'")
            self.page.wait_for_timeout(5000)
        self._wait_for_overlay_gone()

    # ─────────── FORM HELPERS ───────────

    def _safe_fill(self, selector, value):
        loc = self.page.locator(selector)
        if loc.count() > 0 and loc.first.is_visible():
            loc.first.fill("")
            loc.first.fill(str(value))
            return True
        return False

    def _scroll_and_click_save(self):
        """Scroll to bottom and click the visible Save button (#saveBttn).

        Uses JS ``.click()`` dispatch directly, which bypasses Playwright's
        actionability check (pointer-event interception by the Page Tips
        overlay was blocking the standard click path).
        """
        self._wait_for_overlay_gone()
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        self.page.wait_for_timeout(600)

        clicked = self.page.evaluate("""() => {
            const btns = document.querySelectorAll('#saveBttn, button#saveBttn, .btn#saveBttn');
            for (const btn of btns) {
                if (btn.offsetParent !== null && !btn.disabled) {
                    btn.scrollIntoView({ block: 'center' });
                    btn.click();
                    return true;
                }
            }
            // Fallback: any visible button whose text says Save (not Save and Continue)
            const all = [...document.querySelectorAll('button, input[type="submit"], .btn')];
            const save = all.find(b => b.offsetParent !== null &&
                /^\s*save\s*$/i.test((b.innerText || b.value || '').trim()));
            if (save) { save.click(); return true; }
            return false;
        }""")

        if not clicked:
            # Last-ditch Playwright attempt with force=True
            try:
                self.page.locator("#saveBttn").first.click(force=True, timeout=5000)
            except Exception:
                pass

        self.page.wait_for_timeout(4000)

    def _add_ip(self, ip, is_first=False):
        """Fill an IP value into the form.

        The Add-A-Record form has one IP input pre-rendered. Additional IP
        rows are added by clicking ``span.addRec``. Ember uses two-way data
        binding, so we must fill via real keystrokes (``Playwright.fill``) —
        plain JS ``.value =`` is NOT picked up by the controller.
        """
        self._wait_for_overlay_gone()

        if not is_first:
            # Add a new IP row via JS click to bypass overlay interception.
            self.page.evaluate("""() => {
                const spans = document.querySelectorAll('span.addRec');
                for (const s of spans) {
                    if (s.offsetParent !== null) {
                        s.scrollIntoView({ block: 'center' });
                        s.click();
                        return true;
                    }
                }
                return false;
            }""")
            self.page.wait_for_timeout(800)

        # Tag the target IP input with a unique id via JS, then use Playwright
        # fill() so Ember's two-way binding fires input/change events properly.
        tag_id = f"__ip_target_{abs(hash(ip)) % 100000}"
        tagged = self.page.evaluate("""({tagId}) => {
            const all = [...document.querySelectorAll(
                'input[type=\"text\"], input[type=\"tel\"], input:not([type])'
            )].filter(n =>
                n.name !== 'domain_name' &&
                n.name !== 'domain_ttl' &&
                n.offsetParent !== null
            );
            if (all.length === 0) return false;
            const empty = all.filter(n => !n.value);
            const target = empty.length ? empty[empty.length - 1] : all[all.length - 1];
            target.id = tagId;
            return true;
        }""", {"tagId": tag_id})

        if tagged:
            try:
                loc = self.page.locator(f"#{tag_id}")
                loc.scroll_into_view_if_needed()
                # Click then press-by-press-type so Ember's keyup/input
                # handlers fire (plain fill() does not trigger Ember's
                # observer on newly-rendered IP rows).
                loc.click()
                self.page.wait_for_timeout(150)
                # Clear any pre-existing value via select-all + delete
                loc.press("Control+a")
                loc.press("Delete")
                loc.type(str(ip), delay=25)
                loc.press("Tab")
                # Clear the temp id so next call finds the next empty input
                self.page.evaluate(
                    "(id) => { const el = document.getElementById(id); if (el) el.removeAttribute('id'); }",
                    tag_id,
                )
            except Exception:
                self.page.keyboard.type(str(ip), delay=25)
                self.page.keyboard.press("Tab")
        else:
            self.page.keyboard.type(str(ip), delay=25)
            self.page.keyboard.press("Tab")

        self.page.wait_for_timeout(500)

    def fill_a_record_form(self, data):
        """Fill the Add/Edit A-record form with provided data."""
        self._wait_for_overlay_gone()

        if "domain_prefix" in data:
            self._safe_fill('input[name="domain_name"]', data["domain_prefix"])

        if "domain_ttl" in data:
            self._safe_fill('input[name="domain_ttl"]', data["domain_ttl"])

        ips = data.get("ip_records") or []
        for idx, ip in enumerate(ips):
            self._add_ip(ip, is_first=(idx == 0))

    # ─────────── CRUD ───────────

    def create_record(self, zone_pk, data):
        """Full CREATE flow: list → cleanup dup → add form → fill → save."""
        self.cleanup_existing_record(zone_pk, data.get("domain_prefix", ""))
        self.go_to_add_record_form(zone_pk)
        self.fill_a_record_form(data)
        self._scroll_and_click_save()

    def try_create_record_no_cleanup(self, zone_pk, data):
        """Create WITHOUT pre-cleanup (for duplicate / negative tests)."""
        self.go_to_add_record_form(zone_pk)
        self.fill_a_record_form(data)
        self._scroll_and_click_save()

    def try_save_empty_form(self, zone_pk):
        """Navigate to Add form and click Save without filling anything."""
        self.go_to_add_record_form(zone_pk)
        self.page.wait_for_timeout(1000)
        self._scroll_and_click_save()

    def update_record(self, zone_pk, domain_prefix, update_data):
        """Full UPDATE flow: list → click edit icon on row → fill → save."""
        self.go_to_records_list(zone_pk)
        if self._click_edit_icon(domain_prefix):
            self.page.wait_for_timeout(3000)
            self.fill_a_record_form(update_data)
            self._scroll_and_click_save()

    def delete_record(self, zone_pk, domain_prefix):
        """Full DELETE flow: list → trash icon on row → confirm yes."""
        self.go_to_records_list(zone_pk)
        self._delete_record_by_trash_icon(domain_prefix)

    def cleanup_existing_record(self, zone_pk, domain_prefix):
        """Delete a record with the same prefix to avoid duplicates."""
        if not domain_prefix:
            return
        self.go_to_records_list(zone_pk)
        for _ in range(3):
            if not self.is_record_visible(domain_prefix):
                return
            self._delete_record_by_trash_icon(domain_prefix)
            self.page.wait_for_timeout(2000)
            self.page.reload(wait_until="networkidle", timeout=30000)
            self.page.wait_for_timeout(3000)

    # ─────────── ROW HELPERS ───────────

    def _find_record_row(self, domain_prefix):
        if not domain_prefix:
            return None
        row = self.page.locator(f"tr:has-text('{domain_prefix}')")
        if row.count() > 0:
            return row.first
        return None

    def _click_edit_icon(self, domain_prefix):
        self._wait_for_overlay_gone()
        if not domain_prefix:
            return False
        clicked = self.page.evaluate("""(prefix) => {
            const rows = [...document.querySelectorAll('tr')];
            const row = rows.find(r => r.innerText && r.innerText.includes(prefix));
            if (!row) return false;
            const icon = row.querySelector('i.fa-edit, i.editdomain, i[title="Edit"]');
            if (!icon) return false;
            icon.scrollIntoView({ block: 'center' });
            icon.click();
            return true;
        }""", domain_prefix)
        if not clicked:
            return False
        self.page.wait_for_timeout(3000)
        self._wait_for_overlay_gone()
        return True

    def _delete_record_by_trash_icon(self, domain_prefix):
        self._wait_for_overlay_gone()
        if not domain_prefix:
            return
        clicked = self.page.evaluate("""(prefix) => {
            const rows = [...document.querySelectorAll('tr')];
            const row = rows.find(r => r.innerText && r.innerText.includes(prefix));
            if (!row) return false;
            const icon = row.querySelector('i.fa-trash-alt, i.fa-trash, i[title="Delete"]');
            if (!icon) return false;
            icon.scrollIntoView({ block: 'center' });
            icon.click();
            return true;
        }""", domain_prefix)
        if not clicked:
            return
        self.page.wait_for_timeout(2000)
        self._handle_confirm_dialog()
        self.page.wait_for_timeout(2000)
        self._wait_for_overlay_gone()

    def _handle_confirm_dialog(self):
        # Try JS click first; fall back to Playwright locator.
        clicked = self.page.evaluate("""() => {
            const selectors = [
                '.cusCnfrmBtn_yes',
                '.swal2-confirm',
            ];
            for (const sel of selectors) {
                const btn = document.querySelector(sel);
                if (btn && btn.offsetParent !== null) { btn.click(); return true; }
            }
            const fallback = [...document.querySelectorAll('button')].find(b =>
                b.offsetParent !== null && /^(yes|ok|confirm)$/i.test((b.innerText || '').trim()));
            if (fallback) { fallback.click(); return true; }
            return false;
        }""")
        if clicked:
            self.page.wait_for_timeout(2000)
            return
        for selector in ['.swal2-confirm', 'button:has-text("Yes")',
                         'button:has-text("OK")']:
            btn = self.page.locator(selector)
            if btn.count() > 0 and btn.first.is_visible():
                btn.first.click()
                self.page.wait_for_timeout(2000)
                return

    # ─────────── READ / VALIDATION ───────────

    def is_record_visible(self, domain_prefix):
        self.page.wait_for_timeout(1500)
        if not domain_prefix:
            return False
        body = self.page.inner_text("body")
        return domain_prefix in body

    def is_add_record_form_visible(self):
        return (self.page.locator('input[name="domain_name"]').count() > 0
                and self.page.locator('input[name="domain_ttl"]').count() > 0)

    def is_on_zone_detail_page(self):
        url = self.page.url
        return ("dns/domains/showdomain/" in url
                or "dns/domains/edit/" in url
                or "dns/a_add/" in url
                or "dns/a_edit/" in url)

    def is_on_records_list(self):
        return "dns/domains/showdomain/" in self.page.url

    def get_current_url(self):
        return self.page.url

    def get_error_message(self):
        loc = self.page.locator(
            ".toast-error, .alert-danger, [class*='error'], [class*='invalid'], "
            ".nerrorDiv, .notifyDiv.nerrorDiv"
        )
        if loc.count() > 0 and loc.first.is_visible():
            return loc.first.text_content()
        return ""

    def is_error_visible(self):
        self.page.wait_for_timeout(1000)
        return self.page.locator(
            ".toast-error, .alert-danger, [class*='error'], "
            ".invalid-feedback, .nerrorDiv, .notifyDiv.nerrorDiv"
        ).count() > 0

    def get_record_count(self):
        self.page.wait_for_timeout(1000)
        return self.page.locator("table tbody tr").count()

    def search_record(self, query):
        loc = self.page.locator('input[type="search"], input[placeholder*="Search"]')
        if loc.count() > 0 and loc.first.is_visible():
            loc.first.fill("")
            loc.first.fill(query)
            self.page.wait_for_timeout(2000)
            return self.get_record_count()
        return 0

    def get_pagination_text(self):
        self.page.wait_for_timeout(1000)
        body = self.page.inner_text("body")
        m = re.search(r'Showing\s+\d+\s+to\s+\d+\s+of\s+\d+', body)
        return m.group(0) if m else ""
