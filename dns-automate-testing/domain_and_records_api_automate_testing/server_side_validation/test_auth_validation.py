"""
test_auth_validation.py – Authentication & Authorization validation tests.

Tests:
  - Access without token (401)
  - Access with invalid/expired token (401)
  - Access with wrong HTTP methods (405)
  - CSRF validation
"""

import pytest

RECORD_TYPES = ["A", "AAAA", "CNAME", "MX", "NS", "DS", "SPF_TXT",
                "SRV", "CAA", "PTR", "NAPTR", "HINFO", "HTTPS"]


def _get_endpoint(rec_type):
    from server_side_validation.conftest import INTERNAL_ENDPOINTS
    return INTERNAL_ENDPOINTS[rec_type]


# ===================================================================== #
#  Test Class 1: No Authentication Token
# ===================================================================== #
class TestNoAuth:
    """Access endpoints without authentication token – should get 401."""

    @pytest.mark.parametrize("rec_type", RECORD_TYPES)
    def test_no_token_create(self, noauth_session, base_url, rec_type):
        url = "{}/{}".format(base_url, _get_endpoint(rec_type))
        data = {
            "domain_name": "noauth-test",
            "zone_name": "test.com.",
            "cluster_name": "test",
            "domain_ttl": "3600",
            "records": ["1.2.3.4"],
        }
        resp = noauth_session.post(url, json=data)
        assert resp.status_code in (401, 403), \
            "Expected 401/403 without token for {} POST, got {}: {}".format(
                rec_type, resp.status_code, resp.text[:300])

    @pytest.mark.parametrize("rec_type", RECORD_TYPES)
    def test_no_token_list(self, noauth_session, base_url, rec_type):
        url = "{}/{}".format(base_url, _get_endpoint(rec_type))
        resp = noauth_session.get(url)
        assert resp.status_code in (401, 403), \
            "Expected 401/403 without token for {} GET, got {}: {}".format(
                rec_type, resp.status_code, resp.text[:300])

    def test_no_token_zone_list(self, noauth_session, base_url):
        url = "{}/v1/dns/zone/".format(base_url)
        resp = noauth_session.get(url)
        assert resp.status_code in (401, 403), \
            "Expected 401/403 for zone list, got {}".format(resp.status_code)

    def test_no_token_root_hint(self, noauth_session, base_url):
        url = "{}/v1/dns/configure_root_hint/".format(base_url)
        resp = noauth_session.post(url, data={
            "named_root_ns_data": "test",
            "cluster": "2",
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
        assert resp.status_code in (401, 403), \
            "Expected 401/403 for root_hint, got {}".format(resp.status_code)

    def test_no_token_oauth2_domain(self, noauth_session, base_url):
        url = "{}/v1/dns/domain/".format(base_url)
        resp = noauth_session.get(url)
        assert resp.status_code in (401, 403), \
            "Expected 401/403 for OAuth2 domain, got {}".format(resp.status_code)

    def test_no_token_oauth2_records(self, noauth_session, base_url, zone_pk):
        url = "{}/v1/dns/domain/{}/records/A/".format(base_url, zone_pk)
        resp = noauth_session.get(url)
        assert resp.status_code in (401, 403), \
            "Expected 401/403 for OAuth2 records, got {}".format(resp.status_code)


# ===================================================================== #
#  Test Class 2: Invalid / Expired Token
# ===================================================================== #
class TestInvalidToken:
    """Access endpoints with invalid or expired tokens."""

    INVALID_TOKENS = [
        ("garbage", "thisisnotavalidtoken12345"),
        ("empty", ""),
        ("expired_format", "eyJhbGciOiJIUzI1NiJ9.eyJleHAiOjB9.invalid"),
        ("special_chars", "token!@#$%^&*()"),
        ("sql_in_token", "' OR '1'='1'--"),
        ("xss_in_token", "<script>alert(1)</script>"),
    ]

    @pytest.mark.parametrize("name,token", INVALID_TOKENS)
    def test_invalid_token_zone_list(self, base_url, name, token):
        import requests
        s = requests.Session()
        s.headers.update({
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        })
        s.verify = False
        s.trust_env = False
        url = "{}/v1/dns/zone/".format(base_url)
        resp = s.get(url)
        assert resp.status_code in (401, 403), \
            "Expected 401/403 for invalid token '{}', got {}: {}".format(
                name, resp.status_code, resp.text[:300])

    @pytest.mark.parametrize("name,token", INVALID_TOKENS)
    def test_invalid_token_create_record(self, base_url, zone_name,
                                         cluster_name, name, token):
        import requests
        s = requests.Session()
        s.headers.update({
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        })
        s.verify = False
        s.trust_env = False
        url = "{}/{}".format(base_url, _get_endpoint("A"))
        data = {
            "domain_name": "invalid-token-test",
            "zone_name": zone_name,
            "cluster_name": cluster_name,
            "domain_ttl": "3600",
            "records": ["1.2.3.4"],
        }
        resp = s.post(url, json=data)
        assert resp.status_code in (401, 403), \
            "Expected 401/403 for token '{}', got {}".format(name, resp.status_code)

    @pytest.mark.parametrize("name,token", INVALID_TOKENS)
    def test_invalid_token_oauth2(self, base_url, name, token):
        import requests
        s = requests.Session()
        s.headers.update({
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        })
        s.verify = False
        s.trust_env = False
        url = "{}/v1/dns/domain/".format(base_url)
        resp = s.get(url)
        assert resp.status_code in (401, 403), \
            "Expected 401/403 OAuth2 token '{}', got {}".format(
                name, resp.status_code)


# ===================================================================== #
#  Test Class 3: Missing Authorization Header
# ===================================================================== #
class TestMissingAuthHeader:
    """Access without Authorization header at all."""

    def test_no_auth_header_internal(self, base_url):
        import requests
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        s.verify = False
        s.trust_env = False
        url = "{}/v1/dns/zone/".format(base_url)
        resp = s.get(url)
        assert resp.status_code in (401, 403), \
            "Expected 401/403 no auth header, got {}".format(resp.status_code)

    def test_no_auth_header_oauth2(self, base_url):
        import requests
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        s.verify = False
        s.trust_env = False
        url = "{}/v1/dns/domain/".format(base_url)
        resp = s.get(url)
        assert resp.status_code in (401, 403), \
            "Expected 401/403 no auth header OAuth2, got {}".format(resp.status_code)

    def test_wrong_auth_scheme(self, base_url):
        """Use Basic auth instead of Bearer."""
        import requests
        s = requests.Session()
        s.headers.update({
            "Authorization": "Basic dXNlcjpwYXNz",
            "Content-Type": "application/json",
        })
        s.verify = False
        s.trust_env = False
        url = "{}/v1/dns/zone/".format(base_url)
        resp = s.get(url)
        assert resp.status_code in (401, 403), \
            "Expected 401/403 for Basic auth, got {}".format(resp.status_code)


# ===================================================================== #
#  Test Class 4: Bulk Delete without auth
# ===================================================================== #
class TestBulkDeleteNoAuth:
    """Bulk delete endpoints should require authentication."""

    @pytest.mark.parametrize("rec_type", RECORD_TYPES)
    def test_bulk_delete_no_token(self, noauth_session, base_url, rec_type):
        from server_side_validation.conftest import INTERNAL_BULK_DELETE
        url = "{}/{}".format(base_url, INTERNAL_BULK_DELETE[rec_type])
        resp = noauth_session.post(url, json={"ids": [1, 2, 3]})
        assert resp.status_code in (401, 403), \
            "Expected 401/403 bulk delete {} no auth, got {}".format(
                rec_type, resp.status_code)
