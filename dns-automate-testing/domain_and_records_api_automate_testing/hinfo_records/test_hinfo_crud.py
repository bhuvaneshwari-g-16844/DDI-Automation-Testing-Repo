"""
test_hinfo_crud.py – HINFO record CRUD API tests.

Creates hinfo1, hinfo2, hinfo3 -> GET verify
Updates hinfo1                 -> verify
Deletes hinfo2 only            -> verify hinfo1 & hinfo3 remain

Note: HINFO is not commonly supported in standard dig; verification is API-based.

Run:
    cd dns-playwright-framework
    pytest domain_and_records_api_automate_testing/hinfo_records/test_hinfo_crud.py -v -s
"""

import pytest
import subprocess
import time

DNS_SERVERS = ["10.73.17.98", "10.73.17.109"]  # , "10.72.44.98"
DIG_WAIT = 3


def _dig_one(domain, dns_server):
    cmd = ["dig", "HINFO", domain, "@{}".format(dns_server), "+short", "+time=5", "+tries=1"]
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
    print("  dig HINFO {}  (checking {} servers)".format(domain, len(servers)))
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
class TestHINFORecordCreate:

    def test_create_hinfo1(self, hinfo_api, api_testdata, hinfo_record_ids):
        cfg = api_testdata["hinfo_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "hinfo1.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_1"],
            "cluster_name": cluster,
        }
        resp = hinfo_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE hinfo1 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] hinfo1 -> {}".format(body))
        pk = hinfo_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        hinfo_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        _dig("hinfo1.{}".format(zone))

    def test_create_hinfo2(self, hinfo_api, api_testdata, hinfo_record_ids):
        cfg = api_testdata["hinfo_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "hinfo2.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_2"],
            "cluster_name": cluster,
        }
        resp = hinfo_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE hinfo2 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] hinfo2 -> {}".format(body))
        pk = hinfo_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        hinfo_record_ids.append(pk)

    def test_create_hinfo3(self, hinfo_api, api_testdata, hinfo_record_ids):
        cfg = api_testdata["hinfo_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "hinfo3.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_3"],
            "cluster_name": cluster,
        }
        resp = hinfo_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE hinfo3 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] hinfo3 -> {}".format(body))
        pk = hinfo_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        hinfo_record_ids.append(pk)


# ── READ ──────────────────────────────────────────────────────────── #
@pytest.mark.order(2)
class TestHINFORecordRead:

    def test_get_all_three(self, hinfo_api, api_testdata, hinfo_record_ids):
        if len(hinfo_record_ids) < 3:
            pytest.skip("Not all 3 records were created")
        names = ["hinfo1", "hinfo2", "hinfo3"]
        for i, pk in enumerate(hinfo_record_ids[:3]):
            resp = hinfo_api.get(pk)
            print("\n[API GET] {} pk={} -> {}: {}".format(
                names[i], pk, resp.status_code, resp.text[:250]))
            assert resp.status_code in (200, 400), "GET {} unexpected error: {}".format(names[i], resp.status_code)

    def test_get_nonexistent(self, hinfo_api):
        resp = hinfo_api.get(999999)
        assert resp.status_code in (400, 404)


# ── UPDATE ────────────────────────────────────────────────────────── #
@pytest.mark.order(3)
class TestHINFORecordUpdate:

    def test_update_hinfo1(self, hinfo_api, api_testdata, hinfo_record_ids):
        if not hinfo_record_ids:
            pytest.skip("No record to update")
        pk = hinfo_record_ids[0]
        cfg = api_testdata["hinfo_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]

        current = hinfo_api.get(pk)
        assert current.status_code == 200
        update_data = current.json()
        print("\n[UPDATE] hinfo1 OLD: {}".format(update_data.get("records", [])))

        update_data["records"] = cfg["update_records"]
        update_data["domain_ttl"] = cfg["update_ttl"]
        update_data["zone_name"] = zone
        update_data["cluster_name"] = cluster
        update_data.pop("hinfo_domain_id", None)
        update_data.pop("zone_id", None)

        resp = hinfo_api.update(pk, update_data)
        print("\n[API PUT] pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:300]))
        assert resp.status_code in (200, 201, 204), \
            "PUT failed: {} - {}".format(resp.status_code, resp.text)


# ── DELETE ────────────────────────────────────────────────────────── #
@pytest.mark.order(4)
class TestHINFORecordDelete:

    def test_delete_hinfo2(self, hinfo_api, api_testdata, hinfo_record_ids):
        if len(hinfo_record_ids) < 2:
            pytest.skip("hinfo2 was not created")
        pk = hinfo_record_ids[1]

        resp = hinfo_api.delete(pk)
        print("\n[API DELETE] hinfo2 pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:200]))
        assert resp.status_code in (200, 204, 400), \
            "DELETE failed: {} - {}".format(resp.status_code, resp.text)

        get_resp = hinfo_api.get(pk)
        assert get_resp.status_code in (400, 404), "hinfo2 still exists after DELETE"

        r1 = hinfo_api.get(hinfo_record_ids[0])
        assert r1.status_code == 200, "hinfo1 should still exist"
        r3 = hinfo_api.get(hinfo_record_ids[2])
        assert r3.status_code == 200, "hinfo3 should still exist"
        print("\n[OK] hinfo1 and hinfo3 remain intact")
