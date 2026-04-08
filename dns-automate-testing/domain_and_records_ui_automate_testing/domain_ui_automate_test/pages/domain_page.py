class DomainPage:
    """Page Object for DNS Domain CRUD operations.

    Real navigation flow (Ember.js app):
      Login → /#/setting_up → /#/dashboard
        → sidebar DNS link → Domain List (/#/dns/domains)
          → click '+ Add Domain' btn → Add Domain Form (/#/dns/domains/add)
          → click domain name <a> → Edit Domain (/#/dns/domains/edit/<id>)
    """

    BASE_URL = "https://10.73.17.95:9443"
    DASHBOARD_URL = BASE_URL + "/#/dashboard"
    DOMAINS_URL = BASE_URL + "/#/dns/domains"

    def __init__(self, page):
        self.page = page

    # ─────────── NAVIGATION ───────────

    def go_to_dashboard(self):
        """Navigate to dashboard page."""
        self.page.goto(self.DASHBOARD_URL, wait_until="networkidle", timeout=30000)
        self.page.wait_for_timeout(2000)

    def go_to_domain_list(self):
        """Navigate to the domain list page."""
        self.page.goto(self.DOMAINS_URL, wait_until="networkidle", timeout=30000)
        self.page.wait_for_timeout(3000)
        # Verify we landed on domain list (check for '+ Add Domain' button)
        if self.page.locator(".btn-Addd").count() == 0:
            # Fallback: JS hash navigation
            self.page.evaluate("window.location.hash = '#/dns/domains'")
            self.page.wait_for_timeout(5000)

    def go_to_add_domain(self):
        """Navigate to domain list, then click '+ Add Domain' button.
        Direct URL to /#/dns/domains/add does NOT work (Ember redirects to dashboard).
        """
        self.go_to_domain_list()
        add_btn = self.page.locator(".btn-Addd")
        add_btn.wait_for(state="visible", timeout=10000)
        add_btn.click()
        self.page.wait_for_timeout(3000)

    # ─────────── FORM HELPERS ───────────

    def _safe_fill(self, selector, value):
        """Fill an input field if it exists and is visible."""
        loc = self.page.locator(selector)
        if loc.count() > 0 and loc.first.is_visible():
            loc.first.fill("")
            loc.first.fill(str(value))
            return True
        return False

    def _select_ember_chosen(self, select_name, value):
        """Select an option in an Ember Chosen dropdown by value.
        Ember Chosen hides the real <select> and renders a custom UI.
        We use JS to set the value and trigger the change event.
        """
        self.page.evaluate(f"""() => {{
            const sel = document.querySelector('select[name="{select_name}"]');
            if (!sel) return;
            // For multi-select, add the option
            if (sel.multiple) {{
                for (let opt of sel.options) {{
                    if (opt.value === '{value}') {{
                        opt.selected = true;
                    }}
                }}
            }} else {{
                sel.value = '{value}';
            }}
            // Trigger Ember/jQuery change events
            sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
            if (typeof jQuery !== 'undefined') {{
                jQuery(sel).trigger('chosen:updated').trigger('change');
            }}
        }}""")
        self.page.wait_for_timeout(500)

    def _toggle_ddns(self, enable):
        """Toggle the DDNS switch button.
        The DDNS control is a custom <span class='switchBtn'> wrapping
        a hidden <input name='ddns' type='hidden'>.
        """
        ddns_input = self.page.locator('input[name="ddns"]')
        if ddns_input.count() == 0:
            return

        current_val = ddns_input.get_attribute("value")
        is_enabled = current_val == "true"

        if enable and not is_enabled:
            self.page.locator(".switchBtn").click()
            self.page.wait_for_timeout(500)
        elif not enable and is_enabled:
            self.page.locator(".switchBtn").click()
            self.page.wait_for_timeout(500)

    def _scroll_and_click_save(self):
        """Scroll to bottom and click the visible Save button (#saveBttn).
        After clicking, waits for redirect to showdomain, edit, or domain list.
        """
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        self.page.wait_for_timeout(1000)

        # Click the VISIBLE Save button (there are two #saveBttn, one hidden)
        save_btns = self.page.locator("#saveBttn")
        for i in range(save_btns.count()):
            if save_btns.nth(i).is_visible():
                save_btns.nth(i).scroll_into_view_if_needed()
                save_btns.nth(i).click()
                break
        else:
            # JS fallback
            self.page.evaluate("""() => {
                const btns = document.querySelectorAll('#saveBttn');
                for (const btn of btns) {
                    if (btn.offsetParent !== null) { btn.click(); break; }
                }
            }""")

        # Wait for redirect — could be showdomain/{id}, edit/{id}, or domain list
        try:
            self.page.wait_for_url("**/dns/domains/showdomain/**", timeout=15000)
        except Exception:
            try:
                self.page.wait_for_url("**/dns/domains/edit/**", timeout=5000)
            except Exception:
                try:
                    self.page.wait_for_url("**/dns/domains", timeout=5000)
                except Exception:
                    self.page.wait_for_timeout(5000)

    def _click_cancel(self):
        """Click Cancel button."""
        cancel = self.page.locator(".bttn.btn-cancel")
        if cancel.count() > 0 and cancel.first.is_visible():
            cancel.first.click()
        else:
            self.page.evaluate("""() => {
                const btns = [...document.querySelectorAll('button')];
                const btn = btns.find(b => b.textContent.trim() === 'Cancel');
                if (btn) btn.click();
            }""")
        self.page.wait_for_timeout(1000)

    # ─────────── FILL FORM ───────────

    def fill_domain_form(self, data):
        """Fill the Create/Edit Domain form with provided data.

        Real form elements (from UI inspection):
          input[name='zone_name']     — text, placeholder='Enter Name'
          select[name='type']         — Ember Chosen (1=Authoritative, 3=Forward, 2=RPZ)
          input[name='zone_ttl']      — text, default 86400
          input[name='sec_ns']        — text, placeholder='Enter NS Records'
          input[name='zone_contact']  — text, placeholder='Enter Email'
          input[name='refresh']       — text, default 43200
          input[name='retry']         — text, default 3600
          input[name='expiry']        — text, default 1209600
          input[name='minimum']       — text, default 180
          select[name='master']       — Ember Chosen multi-select (primary servers)
          select[name='slave']        — Ember Chosen multi-select (secondary servers)
          select[name='tsig']         — Ember Chosen (TSIG key)
          input[name='ddns']          — hidden, toggled via .switchBtn
          select[name='options']      — Ember Chosen (zone options)
        """
        # ZONE NAME
        if "zone_name" in data:
            self._safe_fill('input[name="zone_name"]', data["zone_name"])

        # ZONE TYPE via Ember Chosen (value "1"=Authoritative)
        if data.get("zone_type"):
            self._select_ember_chosen("type", data["zone_type"])

        # TTL
        if data.get("zone_ttl"):
            self._safe_fill('input[name="zone_ttl"]', data["zone_ttl"])

        # NS RECORDS — fill value, press Enter, then fill IP(s) in the
        # zone_ns_container that appears dynamically
        if data.get("sec_ns"):
            ns_input = self.page.locator('input[name="sec_ns"]')
            if ns_input.count() > 0 and ns_input.first.is_visible():
                ns_input.first.fill("")
                ns_input.first.fill(str(data["sec_ns"]))
                # Press Enter to trigger the NS Records IP(s) section
                ns_input.first.press("Enter")
                self.page.wait_for_timeout(2000)

                # Wait for the zone_ns_container to appear
                ns_container = self.page.locator('.zone_ns_container')
                if ns_container.count() > 0:
                    ns_container.first.wait_for(state="visible", timeout=10000)
                    self.page.wait_for_timeout(1000)

                    # Fill the IP address(es) from nameservers.ns_with_ip
                    ns_with_ip = data.get("nameservers", {}).get("ns_with_ip", [])
                    ns_ip_inputs = ns_container.locator('input[id^="ip_f"]')
                    for idx, ns_entry in enumerate(ns_with_ip):
                        ip_field = ns_ip_inputs.nth(idx)
                        if ip_field.count() > 0 and ip_field.is_visible():
                            ip_field.fill(str(ns_entry["ips"]))
                            ip_field.press("Enter")
                            self.page.wait_for_timeout(500)

        # ZONE CONTACT / EMAIL
        if "zone_contact" in data:
            self._safe_fill('input[name="zone_contact"]', data["zone_contact"])

        # REFRESH
        if data.get("refresh"):
            self._safe_fill('input[name="refresh"]', data["refresh"])

        # RETRY
        if data.get("retry"):
            self._safe_fill('input[name="retry"]', data["retry"])

        # EXPIRY
        if data.get("expiry"):
            self._safe_fill('input[name="expiry"]', data["expiry"])

        # MINIMUM
        if data.get("minimum"):
            self._safe_fill('input[name="minimum"]', data["minimum"])

        # MASTER SERVER via Ember Chosen multi-select
        if data.get("master_servers"):
            self._select_ember_chosen("master", data["master_servers"])

        # DDNS toggle (custom switch button)
        if "ddns_zone" in data:
            self._toggle_ddns(data["ddns_zone"])

    # ─────────── CREATE ───────────

    def cleanup_existing_domain(self, zone_name):
        """If the zone already exists in the domain list, delete it first
        to avoid duplicate zone creation errors.
        Retries up to 3 times to ensure the zone is fully removed.
        """
        for attempt in range(3):
            self.go_to_domain_list()
            if not self.is_domain_visible(zone_name):
                return  # Zone is gone, nothing to clean up

            # Zone still exists → delete it
            self._delete_zone_by_trash_icon(zone_name)

            # Wait for server to process the deletion
            self.page.wait_for_timeout(3000)

            # Reload domain list and verify
            self.page.reload(wait_until="networkidle", timeout=30000)
            self.page.wait_for_timeout(3000)

            if not self.is_domain_visible(zone_name):
                return  # Successfully deleted

    def create_domain(self, data):
        """Full CREATE flow:
        1. Delete existing zone if present (avoid duplicates)
        2. Domain List → '+ Add Domain' → Fill form → Save
        Returns the zone ID from the redirect URL, or None.
        """
        # Remove existing zone to avoid duplicate errors
        if "zone_name" in data:
            self.cleanup_existing_domain(data["zone_name"])

        self.go_to_add_domain()
        self.fill_domain_form(data)
        self._scroll_and_click_save()
        return self.get_zone_id_from_url()

    # ─────────── READ ───────────

    def is_domain_visible(self, domain_name):
        """Check if domain name appears on the current page.
        Handles trailing dot (e.g. 'apple.com' vs 'apple.com.').
        """
        self.page.wait_for_timeout(2000)
        page_text = self.page.inner_text("body")
        domain_with_dot = domain_name if domain_name.endswith(".") else domain_name + "."
        domain_without_dot = domain_name.rstrip(".")
        return domain_without_dot in page_text or domain_with_dot in page_text

    def search_domain(self, domain_name):
        """Search for a domain using the search box on domain list page."""
        self.go_to_domain_list()
        search = self.page.locator('input[name="domainSearch"]')
        if search.count() > 0 and search.first.is_visible():
            search.first.fill("")
            search.first.fill(domain_name)
            self.page.wait_for_timeout(3000)

    def get_domain_count(self):
        """Count rows in the domain table."""
        self.page.wait_for_timeout(1000)
        return self.page.locator("table tbody tr").count()

    def click_domain_link(self, domain_name):
        """Click the domain name <a> link in a table row to open edit page.
        Real table rows contain <a href='#/dns/domains/edit/{id}'> links.
        """
        domain_without_dot = domain_name.rstrip(".")
        domain_with_dot = domain_name if domain_name.endswith(".") else domain_name + "."

        # Try to find the row containing the domain name
        for variant in [domain_with_dot, domain_without_dot]:
            row = self.page.locator(f"tr:has-text('{variant}')")
            if row.count() > 0:
                # Click the <a> link inside the row (the domain name link)
                link = row.first.locator("a[href*='dns/domains/edit']")
                if link.count() > 0:
                    link.first.click()
                    self.page.wait_for_timeout(3000)
                    return True
                # Fallback: click the 3rd td (domain name column, index 2)
                tds = row.first.locator("td")
                if tds.count() > 2:
                    tds.nth(2).click()
                    self.page.wait_for_timeout(3000)
                    return True
        return False

    # ─────────── UPDATE ───────────

    def update_domain(self, domain_name, update_data):
        """Full UPDATE flow:
        Domain List → click domain name link → Edit form → Fill → Save
        """
        self.go_to_domain_list()

        if self.click_domain_link(domain_name):
            self.page.wait_for_timeout(2000)
            self.fill_domain_form(update_data)
            self._scroll_and_click_save()

    # ─────────── DELETE ───────────

    def delete_domain(self, domain_name):
        """Full DELETE flow:
        Domain List → find domain row → click trash icon (fa-trash-alt, title='Delete').
        The trash icon is in the last <td> of each row on the domain list page.
        """
        self.go_to_domain_list()
        self._delete_zone_by_trash_icon(domain_name)

    def _delete_zone_by_trash_icon(self, domain_name):
        """Click the trash icon for the given domain on the current page
        (must already be on domain list) and confirm deletion.
        The app may use a native browser confirm() dialog or a custom info box.
        """
        domain_without_dot = domain_name.rstrip(".")
        domain_with_dot = domain_name if domain_name.endswith(".") else domain_name + "."

        # Find the row containing the domain
        row = None
        for variant in [domain_with_dot, domain_without_dot]:
            r = self.page.locator(f"tr:has-text('{variant}')")
            if r.count() > 0:
                row = r.first
                break

        if not row:
            return

        # Click the trash icon (fa-trash-alt, title='Delete') in this row
        trash_icon = row.locator('i.fa-trash-alt, i[title="Delete"]')
        if trash_icon.count() == 0:
            return

        trash_icon.first.scroll_into_view_if_needed()
        self.page.wait_for_timeout(500)
        trash_icon.first.click()
        self.page.wait_for_timeout(2000)

        # Click 'yes' in the custom Confirmation info box
        self._handle_confirm_dialog()
        self.page.wait_for_timeout(3000)

    def _handle_confirm_dialog(self):
        """Handle the custom Confirmation info box that appears after clicking trash.
        The app shows: <h3>Confirmation</h3> with:
          <div class="cusCnfrmBtn cusCnfrmBtn_yes">yes</div>
          <div class="cusCnfrmBtn cusCnfrmBtn_no">no</div>
        Click the 'yes' button to confirm deletion.
        """
        # Wait for the custom confirm box to appear
        yes_btn = self.page.locator('.cusCnfrmBtn_yes')
        try:
            yes_btn.wait_for(state="visible", timeout=5000)
            yes_btn.click()
            self.page.wait_for_timeout(3000)
            return
        except Exception:
            pass

        # Fallback: try other confirm-like buttons
        for selector in ['.swal2-confirm', 'button:has-text("Yes")', 'button:has-text("OK")']:
            btn = self.page.locator(selector)
            if btn.count() > 0 and btn.first.is_visible():
                btn.first.click()
                self.page.wait_for_timeout(2000)
                return

    # ─────────── URL HELPERS ───────────

    def get_zone_id_from_url(self):
        """Extract zone ID from showdomain or edit URL.
        Patterns: /#/dns/domains/showdomain/<id> or /#/dns/domains/edit/<id>
        """
        import re
        current = self.page.url
        m = re.search(r'/dns/domains/(?:showdomain|edit)/([^/?#]+)', current)
        return m.group(1) if m else None

    def is_on_show_domain_page(self):
        """Return True if on showdomain detail page."""
        return "dns/domains/showdomain/" in self.page.url

    def is_on_edit_domain_page(self):
        """Return True if on edit domain page."""
        return "dns/domains/edit/" in self.page.url

    def is_on_domain_detail_page(self):
        """Return True if on any domain detail page (showdomain or edit)."""
        url = self.page.url
        return "dns/domains/showdomain/" in url or "dns/domains/edit/" in url

    # ─────────── VALIDATION HELPERS ───────────

    def get_success_message(self):
        loc = self.page.locator(".toast-success, .alert-success, [class*='success']")
        if loc.count() > 0 and loc.first.is_visible():
            return loc.first.text_content()
        return ""

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

    def is_success_visible(self):
        self.page.wait_for_timeout(1000)
        return self.page.locator(
            ".toast-success, .alert-success, [class*='success']"
        ).count() > 0

    def get_current_url(self):
        return self.page.url

    def take_screenshot(self, name):
        self.page.screenshot(path=f"screenshots/{name}.png")

    # ─────────── EXTENDED HELPERS (for full test suite) ───────────

    def is_add_domain_form_visible(self):
        """Return True if the Add Domain form is currently displayed."""
        return self.page.locator('input[name="zone_name"]').count() > 0

    def try_create_domain_no_cleanup(self, data):
        """Create domain WITHOUT cleaning up first.
        Used for duplicate domain tests and negative tests.
        """
        self.go_to_add_domain()
        self.fill_domain_form(data)
        self._scroll_and_click_save()

    def try_save_empty_form(self):
        """Navigate to Add Domain form and click Save without filling anything.
        Used for negative test: create without name.
        """
        self.go_to_add_domain()
        self.page.wait_for_timeout(1000)
        self._scroll_and_click_save()

    def get_all_validation_errors(self):
        """Return text of all visible validation / error messages."""
        self.page.wait_for_timeout(1000)
        errors = []
        for sel in [".toast-error", ".alert-danger", "[class*='error']",
                    ".invalid-feedback", ".help-block", ".error-message",
                    ".form-error", ".checkSpl.error", ".field-error"]:
            locs = self.page.locator(sel)
            for i in range(locs.count()):
                if locs.nth(i).is_visible():
                    txt = locs.nth(i).text_content().strip()
                    if txt:
                        errors.append(txt)
        return errors

    def get_pagination_text(self):
        """Return the 'Showing X to Y of Z domains' text if present."""
        self.page.wait_for_timeout(1000)
        body = self.page.inner_text("body")
        import re
        m = re.search(r'Showing\s+\d+\s+to\s+\d+\s+of\s+\d+\s+domains', body)
        return m.group(0) if m else ""

    def get_total_domain_count_from_pagination(self):
        """Parse total domain count from pagination text."""
        import re
        text = self.get_pagination_text()
        m = re.search(r'of\s+(\d+)\s+domains', text)
        return int(m.group(1)) if m else 0

    def search_and_get_results(self, keyword):
        """Search domain list and return count of visible rows."""
        self.go_to_domain_list()
        search = self.page.locator('input[name="domainSearch"]')
        if search.count() > 0 and search.first.is_visible():
            search.first.fill("")
            search.first.fill(keyword)
            self.page.wait_for_timeout(3000)
        return self.get_domain_count()

    def clear_search(self):
        """Clear the search filter."""
        clear_btn = self.page.locator('#clearSearch')
        if clear_btn.count() > 0 and clear_btn.first.is_visible():
            clear_btn.first.click()
            self.page.wait_for_timeout(2000)

    def is_domain_list_page(self):
        """Return True if on the domain list page."""
        return "dns/domains" in self.page.url and \
               self.page.locator(".btn-Addd").count() > 0

    def get_page_title_text(self):
        """Return any heading / title text on the page."""
        for sel in ["h1", "h2", "h3", ".page-title", ".heading"]:
            loc = self.page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                return loc.first.text_content().strip()
        return ""

    def get_domain_table_headers(self):
        """Return list of table header texts.
        The domain table uses <td> in the first <tr>, not <th>/<thead>.
        """
        headers = []
        # Try thead th first, then fall back to first row tds
        ths = self.page.locator("table thead th")
        if ths.count() == 0:
            ths = self.page.locator("table tr:first-child td")
        for i in range(ths.count()):
            txt = ths.nth(i).text_content().strip()
            if txt:
                headers.append(txt)
        return headers

    def is_import_button_visible(self):
        """Check if the Import button is visible on domain list."""
        return self.page.locator('.import_zone').count() > 0

    def get_zone_name_input_value(self):
        """Get the current value of the zone_name input field."""
        loc = self.page.locator('input[name="zone_name"]')
        if loc.count() > 0:
            return loc.first.input_value()
        return ""

    def is_form_field_visible(self, field_name):
        """Check if a form field is visible by name attribute."""
        loc = self.page.locator(f'input[name="{field_name}"], select[name="{field_name}"]')
        return loc.count() > 0 and loc.first.is_visible()

    def measure_page_load_time(self):
        """Measure time to load domain list page (in ms)."""
        import time
        start = time.time()
        self.go_to_domain_list()
        end = time.time()
        return (end - start) * 1000

    def measure_search_response_time(self, keyword):
        """Measure time for search to return results (in ms)."""
        import time
        self.go_to_domain_list()
        search = self.page.locator('input[name="domainSearch"]')
        if search.count() > 0 and search.first.is_visible():
            start = time.time()
            search.first.fill(keyword)
            self.page.wait_for_timeout(2000)
            end = time.time()
            return (end - start) * 1000
        return 0