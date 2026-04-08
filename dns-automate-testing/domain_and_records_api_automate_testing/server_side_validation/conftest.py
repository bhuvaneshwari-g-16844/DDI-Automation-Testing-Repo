"""
conftest.py – Fixtures for server-side validation tests.

Provides raw requests.Session objects for both Internal UI API (v1/dns/)
and OAuth2 Domain API (v1/dns/domain/) endpoints.
"""

import json
import os
import sys
import pytest
import requests

try:
    from urllib3.exceptions import InsecureRequestWarning
    import urllib3
    urllib3.disable_warnings(InsecureRequestWarning)
except Exception:
    pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from authtok import get_bearer


@pytest.fixture(scope="session")
def api_testdata():
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "config", "api_testdata.json"
    )
    with open(config_path, "r") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def base_url(api_testdata):
    return api_testdata.get("base_url", "https://10.73.17.95:9443").rstrip("/")


@pytest.fixture(scope="session")
def zone_pk(api_testdata):
    return api_testdata.get("zone_pk", 6)


@pytest.fixture(scope="session")
def zone_name(api_testdata):
    return api_testdata.get("zone_name", "bhuvana-ddns.com.")


@pytest.fixture(scope="session")
def cluster_name(api_testdata):
    return api_testdata.get("cluster_name", "linux_agent")


@pytest.fixture(scope="session")
def bearer_token(base_url):
    return get_bearer(host=base_url)


@pytest.fixture(scope="session")
def auth_session(bearer_token):
    """Authenticated requests.Session with Bearer token."""
    s = requests.Session()
    s.headers.update({
        "Authorization": "Bearer {}".format(bearer_token),
        "Content-Type": "application/json",
    })
    s.verify = False
    s.trust_env = False
    return s


@pytest.fixture(scope="session")
def noauth_session():
    """Unauthenticated requests.Session (no token)."""
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    s.verify = False
    s.trust_env = False
    return s


# ── Internal UI API endpoint builders (v1/dns/) ─────────────────────── #
# These map to the System 1 URLs captured from the browser.

INTERNAL_ENDPOINTS = {
    "zone":   "v1/dns/zone/",
    "A":      "v1/dns/adomain/",
    "AAAA":   "v1/dns/aaaadomain/",
    "CNAME":  "v1/dns/cnamedomain/",
    "MX":     "v1/dns/mxdomain/",
    "NS":     "v1/dns/nsdomain/",
    "DS":     "v1/dns/dsdomain/",
    "SPF_TXT": "v1/dns/spftxtdomain/",
    "SRV":    "v1/dns/srvdomain/",
    "CAA":    "v1/dns/caadomain/",
    "PTR":    "v1/dns/ptrdomain/",
    "NAPTR":  "v1/dns/naptrdomain/",
    "HINFO":  "v1/dns/hinfodomain/",
    "HTTPS":  "v1/dns/httpsdomain/",
    "root_hint": "v1/dns/configure_root_hint/",
}

INTERNAL_SPECIFIC = {
    "A":      "v1/dns/adomain_specific/",
    "AAAA":   "v1/dns/aaaadomain_specific/",
    "CNAME":  "v1/dns/cnamedomain_specific/",
    "MX":     "v1/dns/mxdomain_specific/",
    "NS":     "v1/dns/nsdomain_specific/",
    "DS":     "v1/dns/dsdomain_specific/",
    "SPF_TXT": "v1/dns/spftxtdomain_specific/",
    "SRV":    "v1/dns/srvdomain_specific/",
    "CAA":    "v1/dns/caadomain_specific/",
    "PTR":    "v1/dns/ptrdomain_specific/",
    "NAPTR":  "v1/dns/naptrdomain_specific/",
    "HINFO":  "v1/dns/hinfodomain_specific/",
    "HTTPS":  "v1/dns/httpsdomain_specific/",
}

INTERNAL_BULK_DELETE = {
    "A":      "v1/dns/adomain_bulk_delete/",
    "AAAA":   "v1/dns/aaaadomain_bulk_delete/",
    "CNAME":  "v1/dns/cnamedomain_bulk_delete/",
    "MX":     "v1/dns/mxdomain_bulk_delete/",
    "NS":     "v1/dns/nsdomain_bulk_delete/",
    "DS":     "v1/dns/dsdomain_bulk_delete/",
    "SPF_TXT": "v1/dns/spftxtdomain_bulk_delete/",
    "SRV":    "v1/dns/srvdomain_bulk_delete/",
    "CAA":    "v1/dns/caadomain_bulk_delete/",
    "PTR":    "v1/dns/ptrdomain_bulk_delete/",
    "NAPTR":  "v1/dns/naptrdomain_bulk_delete/",
    "HINFO":  "v1/dns/hinfodomain_bulk_delete/",
    "HTTPS":  "v1/dns/httpsdomain_bulk_delete/",
}

# OAuth2 Domain API (System 2)
OAUTH2_RECORD_TYPES = ["A", "AAAA", "Cname", "Aname", "MX", "NS", "DS", "SPF_TXT", "SRV", "CAA", "PTR"]


@pytest.fixture(scope="session")
def internal_url(base_url):
    """Build Internal UI API URL for a given endpoint key."""
    def _build(record_type, pk=None):
        endpoint = INTERNAL_ENDPOINTS[record_type]
        if pk is not None:
            return "{}/{}{}/".format(base_url, endpoint.rstrip("/"), pk)
        return "{}/{}".format(base_url, endpoint)
    return _build


@pytest.fixture(scope="session")
def oauth2_url(base_url):
    """Build OAuth2 Domain API URL."""
    def _build(zone_pk, record_type=None, record_pk=None):
        if record_type and record_pk:
            return "{}/v1/dns/domain/{}/records/{}/{}/".format(
                base_url, zone_pk, record_type, record_pk)
        elif record_type:
            return "{}/v1/dns/domain/{}/records/{}/".format(
                base_url, zone_pk, record_type)
        else:
            return "{}/v1/dns/domain/{}/".format(base_url, zone_pk)
    return _build
