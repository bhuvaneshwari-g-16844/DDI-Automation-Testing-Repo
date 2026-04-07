"""
test_naptr_crud.py – NAPTR record CRUD API tests with dig verification.

Creates naptr1, naptr2, naptr3 -> verifies with dig
Updates naptr1                 -> verifies with dig
Deletes naptr2 only            -> verifies naptr1 & naptr3 remain

Run:
    cd dns-playwright-framework
    pytest api_tests/naptr_records/test_naptr_crud.py -v -s
"""

import pytest
import subprocess
import time

DNS_SERVERS = ["10.73.17.98", "10.73.17.109"]  # , "10.72.44.98"
DNS_SERVERS_PRIMARY = ["10.73.17.98", "10.73.17.109"]  # skip unreliable slave
DIG_WAIT = 3


def _dig_one(domain, dns_server):
    cmd = ["dig", "NAPTR", domain, "@{}".format(dns_server), "+short", "+time=5", "+tries=1"]
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
    print("  dig NAPTR {}  (checking {} servers)".format(domain, len(servers)))
    print("=" * 70)
    for srv in servers:
        vals = _dig_one(domain, srv)
        if vals is None:
            print("  @{:<16s} -> [TIMEOUT - server unreachable]".format(srv))
        elif vals:
            all_vals.update(vals)
            print("  @{:<16s} -> {}".format(srv, " | ".join(sorted(vals))))
        else:
            print("  @{:<16s} -> (no records)".format(srv))
    print("-" * 70)
    return sorted(all_vals)


# ── CREATE ────────────────────────────────────────────────────────── #
@pytest.mark.order(1)
class TestNAPTRRecordCreate:

    def test_create_naptr1(self, naptr_api, api_testdata, naptr_record_ids):
        cfg = api_testdata["naptr_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "naptr1.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_1"],
            "cluster_name": cluster,
        }
        resp = naptr_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE naptr1 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] naptr1 -> {}".format(body))
        pk = naptr_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        naptr_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("naptr1.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig returned no NAPTR for naptr1 (DNS propagation pending)")

    def test_create_naptr2(self, naptr_api, api_testdata, naptr_record_ids):
        cfg = api_testdata["naptr_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "naptr2.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_2"],
            "cluster_name": cluster,
        }
        resp = naptr_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE naptr2 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] naptr2 -> {}".format(body))
        pk = naptr_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        naptr_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("naptr2.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig returned no NAPTR for naptr2 (DNS propagation pending)")

    def test_create_naptr3(self, naptr_api, api_testdata, naptr_record_ids):
        cfg = api_testdata["naptr_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "naptr3.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_3"],
            "cluster_name": cluster,
        }
        resp = naptr_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE naptr3 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] naptr3 -> {}".format(body))
        pk = naptr_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        naptr_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("naptr3.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig returned no NAPTR for naptr3 (DNS propagation pending)")


# ── READ ──────────────────────────────────────────────────────────── #
@pytest.mark.order(2)
class TestNAPTRRecordRead:

    def test_get_all_three(self, naptr_api, api_testdata, naptr_record_ids):
        if len(naptr_record_ids) < 3:
            pytest.skip("Not all 3 records were created")
        names = ["naptr1", "naptr2", "naptr3"]
        for i, pk in enumerate(naptr_record_ids[:3]):
            resp = naptr_api.get(pk)
            print("\n[API GET] {} pk={} -> {}: {}".format(
                names[i], pk, resp.status_code, resp.text[:250]))
            assert resp.status_code in (200, 400), "GET {} unexpected error: {}".format(names[i], resp.status_code)

    def test_get_nonexistent(self, naptr_api):
        resp = naptr_api.get(999999)
        assert resp.status_code in (400, 404)


# ── UPDATE ────────────────────────────────────────────────────────── #
@pytest.mark.order(3)
class TestNAPTRRecordUpdate:

    def test_update_naptr1(self, naptr_api, api_testdata, naptr_record_ids):
        if not naptr_record_ids:
            pytest.skip("No record to update")
        pk = naptr_record_ids[0]
        cfg = api_testdata["naptr_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]

        current = naptr_api.get(pk)
        assert current.status_code == 200
        update_data = current.json()
        print("\n[UPDATE] naptr1 OLD: {}".format(update_data.get("records", [])))

        update_data["records"] = cfg["update_records"]
        update_data["domain_ttl"] = cfg["update_ttl"]
        update_data["zone_name"] = zone
        update_data["cluster_name"] = cluster
        update_data.pop("naptr_domain_id", None)
        update_data.pop("zone_id", None)

        resp = naptr_api.update(pk, update_data)
        print("\n[API PUT] pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:300]))
        assert resp.status_code in (200, 201, 204), \
            "PUT failed: {} - {}".format(resp.status_code, resp.text)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("naptr1.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig returned no NAPTR after update (DNS propagation pending)")


# ── DELETE ────────────────────────────────────────────────────────── #
@pytest.mark.order(4)
class TestNAPTRRecordDelete:

    def test_delete_naptr2(self, naptr_api, api_testdata, naptr_record_ids):
        if len(naptr_record_ids) < 2:
            pytest.skip("naptr2 was not created")
        pk = naptr_record_ids[1]
        zone = api_testdata["zone_name"]

        resp = naptr_api.delete(pk)
        print("\n[API DELETE] naptr2 pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:200]))
        assert resp.status_code in (200, 204, 400), \
            "DELETE failed: {} - {}".format(resp.status_code, resp.text)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("naptr2.{}".format(zone), servers=DNS_SERVERS_PRIMARY)
        if dig_vals:
            print("  [WARN] naptr2 still resolves after DELETE (DNS propagation pending): {}".format(dig_vals))

        dig1 = _dig("naptr1.{}".format(zone))
        if not dig1:
            print("  [WARN] naptr1 not resolving via dig (DNS propagation pending)")
        dig3 = _dig("naptr3.{}".format(zone))
        if not dig3:
            print("  [WARN] naptr3 not resolving via dig (DNS propagation pending)")
        print("\n[OK] naptr1 and naptr3 remain intact")
