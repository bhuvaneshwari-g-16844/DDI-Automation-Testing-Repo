"""
conftest.py – Shared fixtures for all API tests.

Provides:
    api_testdata       – parsed config/api_testdata.json
    bearer_token       – OAuth2 Bearer token (session-scoped)
    arecord_api        – ready-to-use ARecordAPI client (A records)
    created_record_ids – mutable list to share A-record ids across tests
    aaaa_api / aaaa_record_ids   – AAAA record API client and id store
    caa_api  / caa_record_ids    – CAA  record API client and id store
    cname_api / cname_record_ids – CNAME record API client and id store
    mx_api   / mx_record_ids     – MX   record API client and id store
    ns_api   / ns_record_ids     – NS   record API client and id store
    srv_api  / srv_record_ids    – SRV  record API client and id store
    ptr_api  / ptr_record_ids    – PTR  record API client and id store
    txt_api  / txt_record_ids    – TXT (SPF_TXT) record API client and id store
    ds_api   / ds_record_ids     – DS   record API client and id store
    naptr_api / naptr_record_ids – NAPTR record API client and id store
    hinfo_api / hinfo_record_ids – HINFO record API client and id store
    https_api / https_record_ids – HTTPS record API client and id store
"""

import json
import sys
import os
import pytest

# Make the project root importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from authtok import get_bearer
from api_tests.arecords.arecord_api import ARecordAPI
from api_tests.dns_record_api import DnsRecordAPI


# ────────────────────────────────────────────────────────────────────── #
#  Test data
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def api_testdata():
    """Load the API test data JSON once per session."""
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "config", "api_testdata.json"
    )
    with open(config_path, "r") as f:
        return json.load(f)


# ────────────────────────────────────────────────────────────────────── #
#  Auth
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def bearer_token(api_testdata):
    """Fetch a Bearer token once for the whole test session."""
    base_url = api_testdata.get("base_url", "https://10.73.17.95:9443")
    token = get_bearer(host=base_url)
    return token


# ────────────────────────────────────────────────────────────────────── #
#  A-record API client (legacy – kept for existing tests)
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def arecord_api(api_testdata, bearer_token):
    """Return an ARecordAPI client configured for the test session."""
    base_url = api_testdata.get("base_url", "https://10.73.17.95:9443")
    zone_pk = api_testdata.get("zone_pk", 361)
    return ARecordAPI(base_url=base_url, token=bearer_token, zone_pk=zone_pk)


@pytest.fixture(scope="session")
def created_record_ids():
    """Mutable list to share A-record ids across tests."""
    return []


# ────────────────────────────────────────────────────────────────────── #
#  Generic helper to build a DnsRecordAPI for any record type
# ────────────────────────────────────────────────────────────────────── #
def _make_dns_api(api_testdata, bearer_token, record_type):
    base_url = api_testdata.get("base_url", "https://10.73.17.95:9443")
    zone_pk = api_testdata.get("zone_pk", 361)
    return DnsRecordAPI(
        base_url=base_url,
        token=bearer_token,
        zone_pk=zone_pk,
        record_type=record_type,
    )


# ────────────────────────────────────────────────────────────────────── #
#  AAAA
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def aaaa_api(api_testdata, bearer_token):
    return _make_dns_api(api_testdata, bearer_token, "AAAA")

@pytest.fixture(scope="session")
def aaaa_record_ids():
    return []


# ────────────────────────────────────────────────────────────────────── #
#  CAA
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def caa_api(api_testdata, bearer_token):
    return _make_dns_api(api_testdata, bearer_token, "CAA")

@pytest.fixture(scope="session")
def caa_record_ids():
    return []


# ────────────────────────────────────────────────────────────────────── #
#  CNAME
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def cname_api(api_testdata, bearer_token):
    return _make_dns_api(api_testdata, bearer_token, "CNAME")

@pytest.fixture(scope="session")
def cname_record_ids():
    return []


# ────────────────────────────────────────────────────────────────────── #
#  MX
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def mx_api(api_testdata, bearer_token):
    return _make_dns_api(api_testdata, bearer_token, "MX")

@pytest.fixture(scope="session")
def mx_record_ids():
    return []


# ────────────────────────────────────────────────────────────────────── #
#  NS
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def ns_api(api_testdata, bearer_token):
    return _make_dns_api(api_testdata, bearer_token, "NS")

@pytest.fixture(scope="session")
def ns_record_ids():
    return []


# ────────────────────────────────────────────────────────────────────── #
#  SRV
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def srv_api(api_testdata, bearer_token):
    return _make_dns_api(api_testdata, bearer_token, "SRV")

@pytest.fixture(scope="session")
def srv_record_ids():
    return []


# ────────────────────────────────────────────────────────────────────── #
#  PTR
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def ptr_api(api_testdata, bearer_token):
    return _make_dns_api(api_testdata, bearer_token, "PTR")

@pytest.fixture(scope="session")
def ptr_record_ids():
    return []


# ────────────────────────────────────────────────────────────────────── #
#  TXT (SPF_TXT endpoint)
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def txt_api(api_testdata, bearer_token):
    return _make_dns_api(api_testdata, bearer_token, "SPF_TXT")

@pytest.fixture(scope="session")
def txt_record_ids():
    return []


# ────────────────────────────────────────────────────────────────────── #
#  SPF (SPF_TXT endpoint with record_type=SPF)
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def spf_api(api_testdata, bearer_token):
    return _make_dns_api(api_testdata, bearer_token, "SPF_TXT")

@pytest.fixture(scope="session")
def spf_record_ids():
    return []


# ────────────────────────────────────────────────────────────────────── #
#  DS
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def ds_api(api_testdata, bearer_token):
    return _make_dns_api(api_testdata, bearer_token, "DS")

@pytest.fixture(scope="session")
def ds_record_ids():
    return []


# ────────────────────────────────────────────────────────────────────── #
#  NAPTR
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def naptr_api(api_testdata, bearer_token):
    return _make_dns_api(api_testdata, bearer_token, "NAPTR")

@pytest.fixture(scope="session")
def naptr_record_ids():
    return []


# ────────────────────────────────────────────────────────────────────── #
#  HINFO
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def hinfo_api(api_testdata, bearer_token):
    return _make_dns_api(api_testdata, bearer_token, "HINFO")

@pytest.fixture(scope="session")
def hinfo_record_ids():
    return []


# ────────────────────────────────────────────────────────────────────── #
#  HTTPS
# ────────────────────────────────────────────────────────────────────── #
@pytest.fixture(scope="session")
def https_api(api_testdata, bearer_token):
    return _make_dns_api(api_testdata, bearer_token, "HTTPS")

@pytest.fixture(scope="session")
def https_record_ids():
    return []
