"""
dns_record_api.py – Generic service class for any DNS record type API.

Works for: A, AAAA, CAA, CNAME, MX, NS, SRV, PTR, SPF_TXT, DS, NAPTR, HINFO, HTTPS

Endpoints (relative to base_url):
    POST   /api/dns/zone/{zone_pk}/{record_type}/           -> Create
    GET    /api/dns/zone/{zone_pk}/{record_type}/            -> List (with query params)
    GET    /api/dns/zone/{zone_pk}/{record_type}/{pk}/       -> Get single
    PUT    /api/dns/zone/{zone_pk}/{record_type}/{pk}/       -> Update
    DELETE /api/dns/zone/{zone_pk}/{record_type}/{pk}/       -> Delete
"""

import requests
import time

try:
    from urllib3.exceptions import InsecureRequestWarning
    import urllib3
    urllib3.disable_warnings(InsecureRequestWarning)
except Exception:
    pass


class DnsRecordAPI(object):
    """Generic wrapper around /api/dns/zone/{zone_pk}/{record_type}/ REST API."""

    # Map record type -> pk field name in response
    PK_FIELDS = {
        "A":        "a_domain_id",
        "AAAA":     "aaaa_domain_id",
        "CAA":      "caa_domain_id",
        "CNAME":    "cname_domain_id",
        "MX":       "mx_domain_id",
        "NS":       "ns_domain_id",
        "SRV":      "srv_domain_id",
        "PTR":      "ptr_domain_id",
        "SPF_TXT":  "spf_txt_domain_id",
        "DS":       "ds_domain_id",
        "NAPTR":    "naptr_domain_id",
        "HINFO":    "hinfo_domain_id",
        "HTTPS":    "https_domain_id",
    }

    def __init__(self, base_url, token, zone_pk, record_type, verify=False):
        """
        Parameters
        ----------
        base_url : str       – e.g. "https://10.73.17.95:9443"
        token : str          – Bearer access token
        zone_pk : int        – Zone primary key (e.g. 361)
        record_type : str    – One of A, AAAA, CAA, CNAME, MX, NS, SRV, PTR,
                               SPF_TXT, DS, NAPTR, HINFO, HTTPS
        verify : bool        – SSL verification (default False)
        """
        self.base_url = base_url.rstrip("/")
        self.zone_pk = zone_pk
        self.record_type = record_type
        self.pk_field = self.PK_FIELDS.get(record_type, "{}_domain_id".format(record_type.lower()))
        self.verify = verify
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        })
        self.session.verify = self.verify
        self.session.trust_env = False  # bypass system proxy

    def _url(self, record_pk=None):
        """Build full URL for collection or single item."""
        if record_pk is not None:
            return "{}/api/dns/zone/{}/{}/{}/".format(
                self.base_url, self.zone_pk, self.record_type, record_pk
            )
        return "{}/api/dns/zone/{}/{}/".format(
            self.base_url, self.zone_pk, self.record_type
        )

    def extract_pk(self, body):
        """Extract record primary key from API response body."""
        return body.get(self.pk_field) or body.get("id") or body.get("pk")

    # ── CRUD ─────────────────────────────────────────────────────────── #
    def create(self, payload):
        """POST – Create a new record."""
        return self.session.post(self._url(), json=payload)

    def get(self, record_pk):
        """GET – Retrieve a single record."""
        return self.session.get(self._url(record_pk))

    def list_all(self, params=None):
        """GET collection – List all records (optionally with query params)."""
        return self.session.get(self._url(), params=params)

    def update(self, record_pk, payload):
        """PUT – Update a record."""
        return self.session.put(self._url(record_pk), json=payload)

    def delete(self, record_pk):
        """DELETE – Remove a record."""
        return self.session.delete(self._url(record_pk))

    def create_or_replace(self, payload):
        """
        Create a record. If it already exists (400), find the old one
        by domain_name, delete it, then retry the create.
        This makes tests re-runnable without manual cleanup.
        """
        resp = self.create(payload)
        if resp.status_code == 400:
            domain_name = payload.get("domain_name", "")
            zone_name = payload.get("zone_name", "")
            cluster_name = payload.get("cluster_name", "")
            list_resp = self.list_all(params={
                "zone_name": zone_name,
                "cluster_name": cluster_name,
            })
            if list_resp.status_code == 200:
                records = list_resp.json()
                if isinstance(records, list):
                    for rec in records:
                        if rec.get("domain_name") == domain_name:
                            pk = self.extract_pk(rec)
                            if pk:
                                print("  [CLEANUP] deleting existing {} pk={}".format(
                                    domain_name, pk))
                                self.delete(pk)
                                break
                resp = self.create(payload)
        return resp
