"""
test_xss_validation.py – XSS (Cross-Site Scripting) validation tests.

Tests XSS payloads against all record type endpoints to verify:
  - Script tags are not reflected or stored unescaped
  - No HTML injection in API responses
  - Responses properly escape or reject malicious HTML/JS
"""

import pytest

# ── XSS Payloads ────────────────────────────────────────────────────── #
XSS_PAYLOADS = [
    ("script_alert", "<script>alert(1)</script>"),
    ("img_onerror", '<img src=x onerror="alert(1)">'),
    ("svg_onload", '<svg onload="alert(1)">'),
    ("iframe_src", '<iframe src="javascript:alert(1)">'),
    ("body_onload", '<body onload="alert(1)">'),
    ("event_handler", '" onfocus="alert(1)" autofocus="'),
    ("javascript_uri", "javascript:alert(document.cookie)"),
    ("encoded_script", "%3Cscript%3Ealert(1)%3C%2Fscript%3E"),
    ("double_encoded", "%253Cscript%253Ealert(1)%253C%252Fscript%253E"),
    ("null_byte", "test\x00<script>alert(1)</script>"),
]

XSS_KEYWORDS = [
    "<script>", "onerror=", "onload=", "onfocus=",
    "javascript:", "<iframe", "<svg", "<img src=x",
]

RECORD_TYPES = ["A", "AAAA", "CNAME", "MX", "NS", "DS", "SPF_TXT",
                "SRV", "CAA", "PTR", "NAPTR", "HINFO", "HTTPS"]


def _has_reflected_xss(response, payload):
    """Check if XSS payload is reflected unescaped in response."""
    try:
        text = response.text
    except Exception:
        return False
    # Check if any raw XSS keywords appear in response
    for keyword in XSS_KEYWORDS:
        if keyword.lower() in text.lower():
            # Verify it's actually reflected (not just an error message mentioning it)
            if payload.lower() in text.lower():
                return True
    return False


# ===================================================================== #
#  Test Class 1: XSS in domain_name via Internal UI API
# ===================================================================== #
class TestXSSInternalDomainName:
    """Inject XSS payloads into domain_name field."""

    @pytest.mark.parametrize("rec_type", RECORD_TYPES)
    @pytest.mark.parametrize("name,payload", XSS_PAYLOADS)
    def test_xss_domain_name(self, auth_session, base_url, zone_name,
                             cluster_name, rec_type, name, payload):
        from server_side_validation.conftest import INTERNAL_ENDPOINTS
        url = "{}/{}".format(base_url, INTERNAL_ENDPOINTS[rec_type])
        data = {
            "domain_name": payload,
            "zone_name": zone_name,
            "cluster_name": cluster_name,
            "domain_ttl": "3600",
        }
        if rec_type == "A":
            data["records"] = ["1.2.3.4"]
        elif rec_type == "AAAA":
            data["records"] = ["2001:db8::1"]
        elif rec_type == "CNAME":
            data["records"] = ["target.example.com."]
        elif rec_type == "MX":
            data["records"] = [{"value": "mail.example.com.", "priority": "10"}]
        elif rec_type == "NS":
            data["records"] = ["ns1.example.com."]
        elif rec_type == "DS":
            data["records"] = [{"key_tag": "12345", "algorithm": "8",
                                "digest_type": "2", "digest": "AABBCCDD"}]
        elif rec_type == "SPF_TXT":
            data["records"] = ["v=spf1 ~all"]
        elif rec_type == "SRV":
            data["records"] = [{"priority": "10", "weight": "20",
                                "port": "443", "value": "srv.example.com."}]
        elif rec_type == "CAA":
            data["records"] = [{"flag": "0", "tag": "issue",
                                "value": "letsencrypt.org."}]
        elif rec_type == "PTR":
            data["records"] = ["ptr.example.com."]
        elif rec_type == "NAPTR":
            data["records"] = [{"order": "100", "preference": "10",
                                "flags": "S", "service": "SIP+D2U",
                                "regexp": "", "replacement": "sip.example.com."}]
        elif rec_type == "HINFO":
            data["records"] = [{"cpu": "Intel", "os": "Linux"}]
        elif rec_type == "HTTPS":
            data["records"] = [{"priority": "1", "value": "h.example.com.",
                                "params": ""}]

        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 XSS {} {}: {}".format(rec_type, name, resp.text[:300])
        assert not _has_reflected_xss(resp, payload), \
            "Reflected XSS in {} {}: {}".format(rec_type, name, resp.text[:300])


# ===================================================================== #
#  Test Class 2: XSS in zone_name and cluster_name
# ===================================================================== #
class TestXSSZoneCluster:
    """Inject XSS payloads into zone_name and cluster_name."""

    @pytest.mark.parametrize("name,payload", XSS_PAYLOADS[:5])
    def test_xss_zone_name(self, auth_session, base_url, cluster_name,
                           name, payload):
        from server_side_validation.conftest import INTERNAL_ENDPOINTS
        url = "{}/{}".format(base_url, INTERNAL_ENDPOINTS["A"])
        data = {
            "domain_name": "xss-zone-test",
            "zone_name": payload,
            "cluster_name": cluster_name,
            "domain_ttl": "3600",
            "records": ["1.2.3.4"],
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 XSS zone_name {}: {}".format(name, resp.text[:300])
        assert not _has_reflected_xss(resp, payload), \
            "XSS zone_name {}: {}".format(name, resp.text[:300])

    @pytest.mark.parametrize("name,payload", XSS_PAYLOADS[:5])
    def test_xss_cluster_name(self, auth_session, base_url, zone_name,
                              name, payload):
        from server_side_validation.conftest import INTERNAL_ENDPOINTS
        url = "{}/{}".format(base_url, INTERNAL_ENDPOINTS["A"])
        data = {
            "domain_name": "xss-cluster-test",
            "zone_name": zone_name,
            "cluster_name": payload,
            "domain_ttl": "3600",
            "records": ["1.2.3.4"],
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 XSS cluster {}: {}".format(name, resp.text[:300])
        assert not _has_reflected_xss(resp, payload), \
            "XSS cluster {}: {}".format(name, resp.text[:300])


# ===================================================================== #
#  Test Class 3: XSS in Root Hint configuration
# ===================================================================== #
class TestXSSRootHint:
    """Inject XSS payloads into Root Hint configure endpoint."""

    @pytest.mark.parametrize("name,payload", XSS_PAYLOADS)
    def test_xss_root_hint_data(self, auth_session, base_url, name, payload):
        url = "{}/v1/dns/configure_root_hint/".format(base_url)
        resp = auth_session.post(url, data={
            "named_root_ns_data": ". 3600000 NS {}\n{} 3600000 A 1.2.3.4".format(
                payload, payload),
            "cluster": "2",
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
        assert resp.status_code != 500, \
            "500 XSS root_hint {}: {}".format(name, resp.text[:300])
        assert not _has_reflected_xss(resp, payload), \
            "XSS root_hint {}: {}".format(name, resp.text[:300])


# ===================================================================== #
#  Test Class 4: XSS in record value fields
# ===================================================================== #
class TestXSSRecordValues:
    """Inject XSS into record-specific value fields (TXT, HINFO, SPF)."""

    @pytest.mark.parametrize("name,payload", XSS_PAYLOADS[:5])
    def test_xss_txt_record_value(self, auth_session, base_url, zone_name,
                                  cluster_name, name, payload):
        from server_side_validation.conftest import INTERNAL_ENDPOINTS
        url = "{}/{}".format(base_url, INTERNAL_ENDPOINTS["SPF_TXT"])
        data = {
            "domain_name": "xss-txt-test",
            "zone_name": zone_name,
            "cluster_name": cluster_name,
            "domain_ttl": "3600",
            "records": [payload],
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 XSS TXT value {}: {}".format(name, resp.text[:300])

    @pytest.mark.parametrize("name,payload", XSS_PAYLOADS[:5])
    def test_xss_hinfo_cpu_os(self, auth_session, base_url, zone_name,
                              cluster_name, name, payload):
        from server_side_validation.conftest import INTERNAL_ENDPOINTS
        url = "{}/{}".format(base_url, INTERNAL_ENDPOINTS["HINFO"])
        data = {
            "domain_name": "xss-hinfo-test",
            "zone_name": zone_name,
            "cluster_name": cluster_name,
            "domain_ttl": "3600",
            "records": [{"cpu": payload, "os": payload}],
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 XSS HINFO {}: {}".format(name, resp.text[:300])


# ===================================================================== #
#  Test Class 5: XSS in OAuth2 Domain API
# ===================================================================== #
class TestXSSOAuth2:
    """Inject XSS payloads via OAuth2 Domain API."""

    @pytest.mark.parametrize("name,payload", XSS_PAYLOADS[:5])
    def test_xss_oauth2_a_record(self, auth_session, base_url, zone_pk,
                                 name, payload):
        url = "{}/v1/dns/domain/{}/records/A/".format(base_url, zone_pk)
        data = {"domain_name": payload, "records": ["1.2.3.4"]}
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 OAuth2 XSS A {}: {}".format(name, resp.text[:300])
        assert not _has_reflected_xss(resp, payload), \
            "OAuth2 XSS A {}: {}".format(name, resp.text[:300])

    @pytest.mark.parametrize("name,payload", XSS_PAYLOADS[:5])
    def test_xss_oauth2_zone_create(self, auth_session, base_url,
                                    name, payload):
        url = "{}/v1/dns/domain/".format(base_url)
        data = {"zone_name": payload}
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 OAuth2 XSS zone {}: {}".format(name, resp.text[:300])
        assert not _has_reflected_xss(resp, payload), \
            "OAuth2 XSS zone {}: {}".format(name, resp.text[:300])
