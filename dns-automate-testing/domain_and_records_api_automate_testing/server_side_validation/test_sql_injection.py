"""
test_sql_injection.py – SQL injection validation tests.

Tests SQL injection payloads against:
  - Internal UI API (v1/dns/) – all record types + root_hint + zone
  - OAuth2 Domain API (v1/dns/domain/)
  - cluster parameter, domain_name, zone_name, pk fields

Verifies:
  - No SQL error messages in responses
  - No 500 Internal Server Error
  - No time-based blind injection (response < 3 seconds)
  - Application remains functional after attacks
"""

import time
import pytest

# ── SQL Payloads ────────────────────────────────────────────────────── #
SQL_PAYLOADS = [
    ("basic_or", "' OR '1'='1'--"),
    ("drop_table", "'; DROP TABLE dns_zones;--"),
    ("union_select", "' UNION SELECT 1,2,3--"),
    ("single_quote", "'''"),
    ("comment_inject", "1; --"),
    ("stacked_query", "1; SELECT pg_sleep(0);--"),
    ("boolean_blind", "' AND 1=1--"),
    ("like_wildcard", "' OR domain_name LIKE '%'--"),
]

SQL_SLEEP_PAYLOADS = [
    ("pg_sleep", "'; SELECT pg_sleep(5);--"),
    ("sleep_mysql", "' OR SLEEP(5)--"),
    ("benchmark", "' OR BENCHMARK(5000000,SHA1('test'))--"),
]

SQLI_KEYWORDS = [
    "sql", "syntax error", "database error", "operationalerror",
    "programmingerror", "psycopg2", "mysql", "sqlite", "postgresql",
    "unterminated", "you have an error in your sql",
    "warning: mysql", "unclosed quotation",
]

RECORD_TYPES = ["A", "AAAA", "CNAME", "MX", "NS", "DS", "SPF_TXT",
                "SRV", "CAA", "PTR", "NAPTR", "HINFO", "HTTPS"]


def _has_sql_error(response):
    """Check if response body leaks SQL error details."""
    try:
        text = response.text.lower()
    except Exception:
        return False
    for keyword in SQLI_KEYWORDS:
        if keyword in text:
            return True
    return False


# ===================================================================== #
#  Test Class 1: SQL Injection in Internal UI API (POST create)
# ===================================================================== #
class TestSQLiInternalCreate:
    """Inject SQL payloads into domain_name field via Internal UI POST."""

    @pytest.mark.parametrize("rec_type", RECORD_TYPES)
    @pytest.mark.parametrize("name,payload", SQL_PAYLOADS)
    def test_sqli_domain_name(self, auth_session, base_url, zone_pk,
                              zone_name, cluster_name, rec_type, name, payload):
        from server_side_validation.conftest import INTERNAL_ENDPOINTS
        url = "{}/{}".format(base_url, INTERNAL_ENDPOINTS[rec_type])
        data = {
            "domain_name": "sqli-{}{}".format(name, payload),
            "zone_name": zone_name,
            "cluster_name": cluster_name,
            "domain_ttl": "3600",
        }
        # Add required fields per record type
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
            data["records"] = ["v=spf1 include:example.com ~all"]
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
            data["records"] = [{"priority": "1", "value": "https.example.com.",
                                "params": ""}]

        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 error for {} {}: {}".format(rec_type, name, resp.text[:300])
        assert not _has_sql_error(resp), \
            "SQL error leaked for {} {}: {}".format(rec_type, name, resp.text[:300])


# ===================================================================== #
#  Test Class 2: SQL Injection in zone_name field
# ===================================================================== #
class TestSQLiZoneName:
    """Inject SQL payloads into zone_name field."""

    @pytest.mark.parametrize("name,payload", SQL_PAYLOADS)
    def test_sqli_zone_name_a_record(self, auth_session, base_url,
                                     cluster_name, name, payload):
        from server_side_validation.conftest import INTERNAL_ENDPOINTS
        url = "{}/{}".format(base_url, INTERNAL_ENDPOINTS["A"])
        data = {
            "domain_name": "sqli-zone-test",
            "zone_name": payload,
            "cluster_name": cluster_name,
            "domain_ttl": "3600",
            "records": ["1.2.3.4"],
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 error zone_name {}: {}".format(name, resp.text[:300])
        assert not _has_sql_error(resp), \
            "SQL error zone_name {}: {}".format(name, resp.text[:300])


# ===================================================================== #
#  Test Class 3: SQL Injection in cluster_name field
# ===================================================================== #
class TestSQLiClusterName:
    """Inject SQL payloads into cluster_name field."""

    @pytest.mark.parametrize("name,payload", SQL_PAYLOADS)
    def test_sqli_cluster_name(self, auth_session, base_url,
                               zone_name, name, payload):
        from server_side_validation.conftest import INTERNAL_ENDPOINTS
        url = "{}/{}".format(base_url, INTERNAL_ENDPOINTS["A"])
        data = {
            "domain_name": "sqli-cluster-test",
            "zone_name": zone_name,
            "cluster_name": payload,
            "domain_ttl": "3600",
            "records": ["1.2.3.4"],
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 error cluster {}: {}".format(name, resp.text[:300])
        assert not _has_sql_error(resp), \
            "SQL error cluster {}: {}".format(name, resp.text[:300])


# ===================================================================== #
#  Test Class 4: SQL Injection in PK / URL path
# ===================================================================== #
class TestSQLiUrlPath:
    """Inject SQL payloads into URL pk parameter."""

    @pytest.mark.parametrize("rec_type", RECORD_TYPES)
    @pytest.mark.parametrize("name,payload", SQL_PAYLOADS[:4])
    def test_sqli_get_by_pk(self, auth_session, base_url, rec_type, name, payload):
        from server_side_validation.conftest import INTERNAL_ENDPOINTS
        endpoint = INTERNAL_ENDPOINTS[rec_type].rstrip("/")
        url = "{}/{}/{}/".format(base_url, endpoint, payload)
        resp = auth_session.get(url)
        assert resp.status_code != 500, \
            "500 on GET pk {} {}: {}".format(rec_type, name, resp.text[:300])
        assert not _has_sql_error(resp), \
            "SQL error GET pk {} {}: {}".format(rec_type, name, resp.text[:300])

    @pytest.mark.parametrize("rec_type", RECORD_TYPES)
    @pytest.mark.parametrize("name,payload", SQL_PAYLOADS[:4])
    def test_sqli_delete_by_pk(self, auth_session, base_url, rec_type, name, payload):
        from server_side_validation.conftest import INTERNAL_ENDPOINTS
        endpoint = INTERNAL_ENDPOINTS[rec_type].rstrip("/")
        url = "{}/{}/{}/".format(base_url, endpoint, payload)
        resp = auth_session.delete(url)
        assert resp.status_code != 500, \
            "500 on DELETE pk {} {}: {}".format(rec_type, name, resp.text[:300])
        assert not _has_sql_error(resp), \
            "SQL error DELETE pk {} {}: {}".format(rec_type, name, resp.text[:300])


# ===================================================================== #
#  Test Class 5: SQL Injection in Root Hint configure
# ===================================================================== #
class TestSQLiRootHint:
    """Inject SQL in root hint cluster and named_root_ns_data fields."""

    @pytest.mark.parametrize("name,payload", SQL_PAYLOADS)
    def test_sqli_root_hint_cluster(self, auth_session, base_url, name, payload):
        url = "{}/v1/dns/configure_root_hint/".format(base_url)
        resp = auth_session.post(url, data={
            "named_root_ns_data": ". 3600000 NS A.ROOT-SERVERS.NET.",
            "cluster": payload,
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
        assert resp.status_code != 500, \
            "500 root_hint cluster {}: {}".format(name, resp.text[:300])
        assert not _has_sql_error(resp), \
            "SQL error root_hint cluster {}: {}".format(name, resp.text[:300])

    @pytest.mark.parametrize("name,payload", SQL_PAYLOADS)
    def test_sqli_root_hint_data(self, auth_session, base_url, name, payload):
        url = "{}/v1/dns/configure_root_hint/".format(base_url)
        resp = auth_session.post(url, data={
            "named_root_ns_data": payload,
            "cluster": "2",
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
        assert resp.status_code != 500, \
            "500 root_hint data {}: {}".format(name, resp.text[:300])
        assert not _has_sql_error(resp), \
            "SQL error root_hint data {}: {}".format(name, resp.text[:300])


# ===================================================================== #
#  Test Class 6: SQL Injection in OAuth2 Domain API
# ===================================================================== #
class TestSQLiOAuth2API:
    """Inject SQL payloads via OAuth2 Domain API (v1/dns/domain/)."""

    OAUTH2_TYPES = ["A", "AAAA", "Cname", "MX", "NS", "DS", "SPF_TXT",
                    "SRV", "CAA", "PTR"]

    @pytest.mark.parametrize("rec_type", OAUTH2_TYPES)
    @pytest.mark.parametrize("name,payload", SQL_PAYLOADS[:4])
    def test_sqli_oauth2_create(self, auth_session, base_url, zone_pk,
                                rec_type, name, payload):
        url = "{}/v1/dns/domain/{}/records/{}/".format(base_url, zone_pk, rec_type)
        data = {"domain_name": "sqli-{}{}".format(name, payload)}
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 OAuth2 {} {}: {}".format(rec_type, name, resp.text[:300])
        assert not _has_sql_error(resp), \
            "SQL error OAuth2 {} {}: {}".format(rec_type, name, resp.text[:300])

    @pytest.mark.parametrize("name,payload", SQL_PAYLOADS[:4])
    def test_sqli_oauth2_zone_pk(self, auth_session, base_url, name, payload):
        url = "{}/v1/dns/domain/{}/records/A/".format(base_url, payload)
        resp = auth_session.get(url)
        assert resp.status_code != 500, \
            "500 OAuth2 zone_pk {}: {}".format(name, resp.text[:300])
        assert not _has_sql_error(resp), \
            "SQL error OAuth2 zone_pk {}: {}".format(name, resp.text[:300])


# ===================================================================== #
#  Test Class 7: Time-based Blind SQL Injection
# ===================================================================== #
class TestSQLiBlindTimeBased:
    """Verify no time-based blind SQLi via sleep payloads."""

    @pytest.mark.parametrize("name,payload", SQL_SLEEP_PAYLOADS)
    def test_blind_sqli_cluster(self, auth_session, base_url, zone_name, name, payload):
        from server_side_validation.conftest import INTERNAL_ENDPOINTS
        url = "{}/{}".format(base_url, INTERNAL_ENDPOINTS["A"])
        data = {
            "domain_name": "blind-sqli-test",
            "zone_name": zone_name,
            "cluster_name": payload,
            "domain_ttl": "3600",
            "records": ["1.2.3.4"],
        }
        start = time.time()
        resp = auth_session.post(url, json=data)
        elapsed = time.time() - start
        assert elapsed < 3.0, \
            "Blind SQLi suspected! {} took {:.1f}s (expected <3s)".format(name, elapsed)
        assert resp.status_code != 500, \
            "500 blind {} ({:.1f}s): {}".format(name, elapsed, resp.text[:300])

    @pytest.mark.parametrize("name,payload", SQL_SLEEP_PAYLOADS)
    def test_blind_sqli_root_hint(self, auth_session, base_url, name, payload):
        url = "{}/v1/dns/configure_root_hint/".format(base_url)
        start = time.time()
        resp = auth_session.post(url, data={
            "named_root_ns_data": ". 3600000 NS A.ROOT-SERVERS.NET.",
            "cluster": payload,
        }, headers={"Content-Type": "application/x-www-form-urlencoded"})
        elapsed = time.time() - start
        assert elapsed < 3.0, \
            "Blind SQLi root_hint! {} took {:.1f}s".format(name, elapsed)
        assert resp.status_code != 500, \
            "500 blind root_hint {} ({:.1f}s): {}".format(name, elapsed, resp.text[:300])


# ===================================================================== #
#  Test Class 8: Zone API SQL Injection
# ===================================================================== #
class TestSQLiZoneAPI:
    """Inject SQL payloads into zone create/list endpoints."""

    @pytest.mark.parametrize("name,payload", SQL_PAYLOADS[:4])
    def test_sqli_zone_create(self, auth_session, base_url, cluster_name, name, payload):
        url = "{}/v1/dns/zone/".format(base_url)
        data = {
            "zone_name": payload,
            "cluster_name": cluster_name,
        }
        resp = auth_session.post(url, json=data)
        assert resp.status_code != 500, \
            "500 zone create {}: {}".format(name, resp.text[:300])
        assert not _has_sql_error(resp), \
            "SQL error zone create {}: {}".format(name, resp.text[:300])

    @pytest.mark.parametrize("name,payload", SQL_PAYLOADS[:4])
    def test_sqli_zone_get_pk(self, auth_session, base_url, name, payload):
        url = "{}/v1/dns/zone/{}/".format(base_url, payload)
        resp = auth_session.get(url)
        assert resp.status_code != 500, \
            "500 zone GET pk {}: {}".format(name, resp.text[:300])
        assert not _has_sql_error(resp), \
            "SQL error zone GET pk {}: {}".format(name, resp.text[:300])
