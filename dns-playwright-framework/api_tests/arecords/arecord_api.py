"""
arecord_api.py – Service class that wraps all A-record REST API endpoints.

Endpoints (relative to base_url):
    POST   /api/dns/zone/{zone_pk}/A/           → Create an A record
    GET    /api/dns/zone/{zone_pk}/A/{pk}/       → Retrieve a single A record
    PUT    /api/dns/zone/{zone_pk}/A/{pk}/       → Update an A record
    DELETE /api/dns/zone/{zone_pk}/A/{pk}/       → Delete an A record
"""

import requests
import time

try:
    from urllib3.exceptions import InsecureRequestWarning
    import urllib3
    urllib3.disable_warnings(InsecureRequestWarning)
except Exception:
    pass


class ARecordAPI:
    """Thin wrapper around the /api/dns/zone/{zone_pk}/A/ REST API."""

    def __init__(self, base_url, token, zone_pk, verify=False):
        self.base_url = base_url.rstrip("/")
        self.zone_pk = zone_pk
        self.verify = verify
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        })
        self.session.verify = self.verify
        # Bypass any system proxy for the API server
        self.session.trust_env = False

    # ------------------------------------------------------------------ #
    #  Helper
    # ------------------------------------------------------------------ #
    def _url(self, record_pk=None):
        """
        Build the full URL.
        Collection : /api/dns/zone/{zone_pk}/A/
        Single item: /api/dns/zone/{zone_pk}/A/{pk}/
        """
        if record_pk is not None:
            return "{}/api/dns/zone/{}/A/{}/".format(
                self.base_url, self.zone_pk, record_pk
            )
        return "{}/api/dns/zone/{}/A/".format(self.base_url, self.zone_pk)

    # ------------------------------------------------------------------ #
    #  CRUD operations
    # ------------------------------------------------------------------ #
    def create(self, payload):
        """POST /api/dns/zone/{zone_pk}/A/ – Create a new A record."""
        return self.session.post(self._url(), json=payload)

    def get(self, record_pk):
        """GET /api/dns/zone/{zone_pk}/A/{pk}/ – Retrieve a single A record."""
        return self.session.get(self._url(record_pk))

    def update(self, record_pk, payload):
        """PUT /api/dns/zone/{zone_pk}/A/{pk}/ – Update an A record."""
        return self.session.put(self._url(record_pk), json=payload)

    def list_all(self, params=None):
        """GET /api/dns/zone/{zone_pk}/A/ – List all A records."""
        return self.session.get(self._url(), params=params)

    def extract_pk(self, body):
        """Extract the A-record primary key from the API response."""
        return body.get("a_domain_id") or body.get("id") or body.get("pk")

    def delete(self, record_pk):
        """DELETE /api/dns/zone/{zone_pk}/A/{pk}/ – Remove an A record."""
        return self.session.delete(self._url(record_pk))

    def create_or_replace(self, payload):
        """
        Create an A record. If it already exists (400), find the old one
        by domain_name, delete it, then retry the create.
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
                                time.sleep(2)  # allow server to process delete
                                break
                resp = self.create(payload)
        return resp
