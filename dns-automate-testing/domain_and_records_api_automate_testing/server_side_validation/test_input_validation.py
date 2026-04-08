"""
test_input_validation.py – Server-side input validation tests.

Tests that the server properly validates:
  - Invalid IP addresses (loopback, zero, reserved, malformed)
  - Special characters in hostnames
  - Oversized fields (boundary limits)
  - Empty/missing required fields
  - Invalid data types
  - Malformed JSON payloads
"""

import pytest

RECORD_TYPES = ["A", "AAAA", "CNAME", "MX", "NS", "DS", "SPF_TXT",
                "SRV", "CAA", "PTR", "NAPTR", "HINFO", "HTTPS"]


def _get_endpoint(rec_type):
    from server_side_validation.conftest import INTERNAL_ENDPOINTS
    return INTERNAL_ENDPOINTS[rec_type]


# ===================================================================== #
#  Test Class 1: Invalid IP address validation (A records)
# ===================================================================== #
class TestInvalidIPv4:
    """Server should reject invalid IPv4 addresses."""

    INVALID_IPS = [
        ("zero_ip", "0.0.0.0"),
        ("loopback", "127.0.0.1"),
        ("broadcast", "255.255.255.255"),
        ("out_of_range", "999.999.999.999"),
        ("negative", "-1.0.0.1"),
        ("alpha", "abc.def.ghi.jkl"),
        ("too_many_octets", "1.2.3.4.5"),
        ("too_few_octets", "1.2.3"),
        ("empty_string", ""),
        ("spaces", "  "),
        ("ipv6_in_v4", "2001:db8::1"),
    ]

    @pytest.mark.parametrize("name,ip", INVALID_IPS)
    def test_invalid_ipv4_a_record(self, auth_session, base_url, zone_name,
                                   cluster_name, name, ip):
        url = "{}/{}".format(base_url, _get_endpoint("A"))
        data = {
            "domain_name": "invalid-ip-{}".format(name),
            "zone_name": zone_name,
            "cluster_name": cluster_name,
            "domain_ttl": "3600",
            "records": [ip],
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 for invalid IPv4 {}: {}".format(name, resp.text[:300])
        assert resp.status_code in (400, 422), \
            "Expected 400/422 for invalid IPv4 '{}', got {}: {}".format(
                ip, resp.status_code, resp.text[:300])


# ===================================================================== #
#  Test Class 2: Invalid IPv6 validation (AAAA records)
# ===================================================================== #
class TestInvalidIPv6:
    """Server should reject invalid IPv6 addresses."""

    INVALID_V6 = [
        ("loopback_v6", "::1"),
        ("zero_v6", "::"),
        ("malformed", "gggg::1"),
        ("too_many_groups", "2001:db8:1:2:3:4:5:6:7:8:9"),
        ("ipv4_in_v6", "192.168.1.1"),
        ("empty", ""),
        ("spaces", "   "),
    ]

    @pytest.mark.parametrize("name,ip", INVALID_V6)
    def test_invalid_ipv6_aaaa_record(self, auth_session, base_url, zone_name,
                                      cluster_name, name, ip):
        url = "{}/{}".format(base_url, _get_endpoint("AAAA"))
        data = {
            "domain_name": "invalid-v6-{}".format(name),
            "zone_name": zone_name,
            "cluster_name": cluster_name,
            "domain_ttl": "3600",
            "records": [ip],
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 for invalid IPv6 {}: {}".format(name, resp.text[:300])


# ===================================================================== #
#  Test Class 3: Special characters in domain_name
# ===================================================================== #
class TestSpecialCharsDomainName:
    """Server should reject special characters in domain names."""

    SPECIAL_CHARS = [
        ("exclamation", "test!domain"),
        ("at_sign", "test@domain"),
        ("hash", "test#domain"),
        ("dollar", "test$domain"),
        ("percent", "test%domain"),
        ("caret", "test^domain"),
        ("ampersand", "test&domain"),
        ("parentheses", "test(domain)"),
        ("braces", "test{domain}"),
        ("brackets", "test[domain]"),
        ("pipe", "test|domain"),
        ("backslash", "test\\domain"),
        ("semicolon", "test;domain"),
        ("colon", "test:domain"),
        ("quotes", 'test"domain'),
        ("single_quote", "test'domain"),
        ("comma", "test,domain"),
        ("less_than", "test<domain"),
        ("greater_than", "test>domain"),
        ("space_in_name", "test domain"),
        ("tab_in_name", "test\tdomain"),
        ("newline_in_name", "test\ndomain"),
    ]

    @pytest.mark.parametrize("rec_type", ["A", "AAAA", "CNAME", "MX"])
    @pytest.mark.parametrize("name,domain", SPECIAL_CHARS)
    def test_special_chars_domain_name(self, auth_session, base_url, zone_name,
                                       cluster_name, rec_type, name, domain):
        url = "{}/{}".format(base_url, _get_endpoint(rec_type))
        data = {
            "domain_name": domain,
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

        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 special chars {} {}: {}".format(rec_type, name, resp.text[:300])


# ===================================================================== #
#  Test Class 4: Boundary values – oversized fields
# ===================================================================== #
class TestBoundaryValues:
    """Test field length limits and boundary conditions."""

    def test_domain_name_255_chars(self, auth_session, base_url, zone_name,
                                   cluster_name):
        url = "{}/{}".format(base_url, _get_endpoint("A"))
        long_name = "a" * 255
        data = {
            "domain_name": long_name,
            "zone_name": zone_name,
            "cluster_name": cluster_name,
            "domain_ttl": "3600",
            "records": ["1.2.3.4"],
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 for 255-char domain: {}".format(resp.text[:300])

    def test_domain_name_1000_chars(self, auth_session, base_url, zone_name,
                                    cluster_name):
        url = "{}/{}".format(base_url, _get_endpoint("A"))
        long_name = "a" * 1000
        data = {
            "domain_name": long_name,
            "zone_name": zone_name,
            "cluster_name": cluster_name,
            "domain_ttl": "3600",
            "records": ["1.2.3.4"],
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 for 1000-char domain: {}".format(resp.text[:300])
        assert resp.status_code in (400, 422), \
            "Expected 400/422 for 1000-char domain, got {}".format(resp.status_code)

    def test_ttl_negative(self, auth_session, base_url, zone_name, cluster_name):
        url = "{}/{}".format(base_url, _get_endpoint("A"))
        data = {
            "domain_name": "ttl-neg-test",
            "zone_name": zone_name,
            "cluster_name": cluster_name,
            "domain_ttl": "-1",
            "records": ["1.2.3.4"],
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 for negative TTL: {}".format(resp.text[:300])

    def test_ttl_extremely_large(self, auth_session, base_url, zone_name,
                                 cluster_name):
        url = "{}/{}".format(base_url, _get_endpoint("A"))
        data = {
            "domain_name": "ttl-big-test",
            "zone_name": zone_name,
            "cluster_name": cluster_name,
            "domain_ttl": "99999999999999",
            "records": ["1.2.3.4"],
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 for huge TTL: {}".format(resp.text[:300])

    def test_ttl_non_numeric(self, auth_session, base_url, zone_name,
                             cluster_name):
        url = "{}/{}".format(base_url, _get_endpoint("A"))
        data = {
            "domain_name": "ttl-alpha-test",
            "zone_name": zone_name,
            "cluster_name": cluster_name,
            "domain_ttl": "abc",
            "records": ["1.2.3.4"],
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 for non-numeric TTL: {}".format(resp.text[:300])

    def test_mx_priority_negative(self, auth_session, base_url, zone_name,
                                  cluster_name):
        url = "{}/{}".format(base_url, _get_endpoint("MX"))
        data = {
            "domain_name": "mx-neg-pri",
            "zone_name": zone_name,
            "cluster_name": cluster_name,
            "domain_ttl": "3600",
            "records": [{"value": "mail.example.com.", "priority": "-1"}],
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 for negative MX priority: {}".format(resp.text[:300])

    def test_mx_priority_over_65535(self, auth_session, base_url, zone_name,
                                    cluster_name):
        url = "{}/{}".format(base_url, _get_endpoint("MX"))
        data = {
            "domain_name": "mx-big-pri",
            "zone_name": zone_name,
            "cluster_name": cluster_name,
            "domain_ttl": "3600",
            "records": [{"value": "mail.example.com.", "priority": "99999"}],
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 for oversized MX priority: {}".format(resp.text[:300])

    def test_srv_port_over_65535(self, auth_session, base_url, zone_name,
                                 cluster_name):
        url = "{}/{}".format(base_url, _get_endpoint("SRV"))
        data = {
            "domain_name": "_sip._tcp.srv-big-port",
            "zone_name": zone_name,
            "cluster_name": cluster_name,
            "domain_ttl": "3600",
            "records": [{"priority": "10", "weight": "20",
                         "port": "99999", "value": "srv.example.com."}],
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 for oversized SRV port: {}".format(resp.text[:300])

    def test_caa_flag_over_255(self, auth_session, base_url, zone_name,
                               cluster_name):
        url = "{}/{}".format(base_url, _get_endpoint("CAA"))
        data = {
            "domain_name": "caa-big-flag",
            "zone_name": zone_name,
            "cluster_name": cluster_name,
            "domain_ttl": "3600",
            "records": [{"flag": "999", "tag": "issue",
                         "value": "letsencrypt.org."}],
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 for oversized CAA flag: {}".format(resp.text[:300])


# ===================================================================== #
#  Test Class 5: Empty / missing required fields
# ===================================================================== #
class TestMissingFields:
    """Server should reject requests with missing required fields."""

    @pytest.mark.parametrize("rec_type", RECORD_TYPES)
    def test_empty_body(self, auth_session, base_url, rec_type):
        url = "{}/{}".format(base_url, _get_endpoint(rec_type))
        resp = auth_session.post(url, json={})
        assert resp.status_code != 500, \
            "500 empty body {}: {}".format(rec_type, resp.text[:300])
        assert resp.status_code in (400, 422), \
            "Expected 400/422 for empty body {}, got {}".format(
                rec_type, resp.status_code)

    @pytest.mark.parametrize("rec_type", RECORD_TYPES)
    def test_missing_domain_name(self, auth_session, base_url, zone_name,
                                 cluster_name, rec_type):
        url = "{}/{}".format(base_url, _get_endpoint(rec_type))
        data = {
            "zone_name": zone_name,
            "cluster_name": cluster_name,
            "domain_ttl": "3600",
            "records": ["1.2.3.4"],
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 missing domain_name {}: {}".format(rec_type, resp.text[:300])

    @pytest.mark.parametrize("rec_type", RECORD_TYPES)
    def test_missing_records(self, auth_session, base_url, zone_name,
                             cluster_name, rec_type):
        url = "{}/{}".format(base_url, _get_endpoint(rec_type))
        data = {
            "domain_name": "missing-records-test",
            "zone_name": zone_name,
            "cluster_name": cluster_name,
            "domain_ttl": "3600",
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 missing records {}: {}".format(rec_type, resp.text[:300])

    def test_null_values(self, auth_session, base_url, zone_name, cluster_name):
        url = "{}/{}".format(base_url, _get_endpoint("A"))
        data = {
            "domain_name": None,
            "zone_name": None,
            "cluster_name": None,
            "domain_ttl": None,
            "records": None,
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 null values: {}".format(resp.text[:300])


# ===================================================================== #
#  Test Class 6: Malformed JSON / Content-Type
# ===================================================================== #
class TestMalformedPayload:
    """Server should handle malformed requests gracefully."""

    def test_invalid_json(self, auth_session, base_url):
        url = "{}/{}".format(base_url, _get_endpoint("A"))
        resp = auth_session.post(url, data="{{invalid json}}")
        assert resp.status_code != 500, \
            "500 invalid JSON: {}".format(resp.text[:300])

    def test_xml_instead_of_json(self, auth_session, base_url):
        url = "{}/{}".format(base_url, _get_endpoint("A"))
        resp = auth_session.post(url, data="<xml><domain>test</domain></xml>",
                                 headers={"Content-Type": "application/xml"})
        assert resp.status_code != 500, \
            "500 XML payload: {}".format(resp.text[:300])

    def test_very_large_payload(self, auth_session, base_url, zone_name,
                                cluster_name):
        url = "{}/{}".format(base_url, _get_endpoint("A"))
        data = {
            "domain_name": "large-payload-test",
            "zone_name": zone_name,
            "cluster_name": cluster_name,
            "domain_ttl": "3600",
            "records": ["1.2.3.4"] * 10000,
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 large payload: {}".format(resp.text[:300])

    @pytest.mark.parametrize("rec_type", RECORD_TYPES)
    def test_wrong_http_method_patch(self, auth_session, base_url, rec_type):
        url = "{}/{}".format(base_url, _get_endpoint(rec_type))
        resp = auth_session.patch(url, json={"test": "test"})
        assert resp.status_code != 500, \
            "500 PATCH {}: {}".format(rec_type, resp.text[:300])
        assert resp.status_code in (400, 404, 405), \
            "Expected 400/404/405 for PATCH {}, got {}".format(
                rec_type, resp.status_code)
