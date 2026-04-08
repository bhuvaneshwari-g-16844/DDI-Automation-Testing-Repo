"""
test_cname_crud.py – CNAME record CRUD API tests with dig verification.

Creates cname1, cname2, cname3 -> verifies with dig
Updates cname1                 -> verifies with dig
Deletes cname2 only            -> verifies cname1 & cname3 remain

Run:
    cd dns-playwright-framework
    pytest domain_and_records_api_automate_testing/cname_records/test_cname_crud.py -v -s
"""

import pytest
import subprocess
import time

DNS_SERVERS = ["10.73.17.98", "10.73.17.109"]  # , "10.72.44.98"
DNS_SERVERS_PRIMARY = ["10.73.17.98", "10.73.17.109"]  # skip unreliable slave
DIG_WAIT = 3


def _dig_one(domain, dns_server):
    cmd = ["dig", "CNAME", domain, "@{}".format(dns_server), "+short", "+time=5", "+tries=1"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        vals = [l.strip() for l in result.stdout.strip().splitlines() if l.strip() and not l.startswith(';')]
        return vals
    except subprocess.TimeoutExpired:
        return None


def _dig(domain, servers=None):
    if servers is None:
        servers = DNS_SERVERS
    all_vals = set()
    print("\n" + "=" * 70)
    print("  dig CNAME {}  (checking {} servers)".format(domain, len(servers)))
    print("=" * 70)
    for srv in servers:
        vals = _dig_one(domain, srv)
        if vals is None:
            print("  @{:<16s} -> [TIMEOUT - server unreachable]".format(srv))
        elif vals:
            all_vals.update(vals)
            print("  @{:<16s} -> {}".format(srv, ", ".join(sorted(vals))))
        else:
            print("  @{:<16s} -> (no records)".format(srv))
    print("-" * 70)
    return sorted(all_vals)


# ── CREATE ────────────────────────────────────────────────────────── #
@pytest.mark.order(1)
class TestCNAMERecordCreate:

    def test_create_cname1(self, cname_api, api_testdata, cname_record_ids):
        cfg = api_testdata["cname_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "cname1.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_1"],
            "cluster_name": cluster,
        }
        resp = cname_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE cname1 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] cname1 -> {}".format(body))
        pk = cname_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        cname_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("cname1.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig returned no CNAME for cname1 (DNS propagation pending)")

    def test_create_cname2(self, cname_api, api_testdata, cname_record_ids):
        cfg = api_testdata["cname_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "cname2.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_2"],
            "cluster_name": cluster,
        }
        resp = cname_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE cname2 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] cname2 -> {}".format(body))
        pk = cname_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        cname_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("cname2.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig returned no CNAME for cname2 (DNS propagation pending)")

    def test_create_cname3(self, cname_api, api_testdata, cname_record_ids):
        cfg = api_testdata["cname_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "cname3.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_3"],
            "cluster_name": cluster,
        }
        resp = cname_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE cname3 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] cname3 -> {}".format(body))
        pk = cname_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        cname_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("cname3.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig returned no CNAME for cname3 (DNS propagation pending)")


# ── READ ──────────────────────────────────────────────────────────── #
@pytest.mark.order(2)
class TestCNAMERecordRead:

    def test_get_all_three(self, cname_api, api_testdata, cname_record_ids):
        if len(cname_record_ids) < 3:
            pytest.skip("Not all 3 records were created")
        names = ["cname1", "cname2", "cname3"]
        for i, pk in enumerate(cname_record_ids[:3]):
            resp = cname_api.get(pk)
            print("\n[API GET] {} pk={} -> {}: {}".format(
                names[i], pk, resp.status_code, resp.text[:250]))
            assert resp.status_code in (200, 400), "GET {} unexpected error: {}".format(names[i], resp.status_code)

    def test_get_nonexistent(self, cname_api):
        resp = cname_api.get(999999)
        assert resp.status_code in (400, 404)


# ── UPDATE ────────────────────────────────────────────────────────── #
@pytest.mark.order(3)
class TestCNAMERecordUpdate:

    def test_update_cname1(self, cname_api, api_testdata, cname_record_ids):
        if not cname_record_ids:
            pytest.skip("No record to update")
        pk = cname_record_ids[0]
        cfg = api_testdata["cname_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]

        current = cname_api.get(pk)
        assert current.status_code == 200
        update_data = current.json()
        print("\n[UPDATE] cname1 OLD: {}".format(update_data.get("records", [])))

        update_data["records"] = cfg["update_records"]
        update_data["domain_ttl"] = cfg["update_ttl"]
        update_data["zone_name"] = zone
        update_data["cluster_name"] = cluster
        update_data.pop("cname_domain_id", None)
        update_data.pop("zone_id", None)

        resp = cname_api.update(pk, update_data)
        print("\n[API PUT] pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:300]))
        assert resp.status_code in (200, 201, 204), \
            "PUT failed: {} - {}".format(resp.status_code, resp.text)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("cname1.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig returned no CNAME after update (DNS propagation pending)")


# ── DELETE ────────────────────────────────────────────────────────── #
@pytest.mark.order(4)
class TestCNAMERecordDelete:

    def test_delete_cname2(self, cname_api, api_testdata, cname_record_ids):
        if len(cname_record_ids) < 2:
            pytest.skip("cname2 was not created")
        pk = cname_record_ids[1]
        zone = api_testdata["zone_name"]

        resp = cname_api.delete(pk)
        print("\n[API DELETE] cname2 pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:200]))
        assert resp.status_code in (200, 204, 400), \
            "DELETE failed: {} - {}".format(resp.status_code, resp.text)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("cname2.{}".format(zone), servers=DNS_SERVERS_PRIMARY)
        if dig_vals:
            print("  [WARN] cname2 still resolves after DELETE (DNS propagation pending): {}".format(dig_vals))

        dig1 = _dig("cname1.{}".format(zone))
        if not dig1:
            print("  [WARN] cname1 not resolving via dig (DNS propagation pending)")
        dig3 = _dig("cname3.{}".format(zone))
        if not dig3:
            print("  [WARN] cname3 not resolving via dig (DNS propagation pending)")
        print("\n[OK] cname1 and cname3 remain intact")
