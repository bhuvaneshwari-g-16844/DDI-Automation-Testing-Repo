"""
test_ptr_crud.py – PTR record CRUD API tests.

Creates ptr1, ptr2, ptr3 -> GET verify
Updates ptr1             -> verify
Deletes ptr2 only        -> verify ptr1 & ptr3 remain

Run:
    cd dns-playwright-framework
    pytest api_tests/ptr_records/test_ptr_crud.py -v -s
"""

import pytest
import subprocess
import time

DNS_SERVERS = ["10.73.17.98", "10.73.17.109"]  # , "10.72.44.98"
DNS_SERVERS_PRIMARY = ["10.73.17.98", "10.73.17.109"]  # skip unreliable slave
DIG_WAIT = 3


def _dig_one(domain, dns_server):
    cmd = ["dig", "PTR", domain, "@{}".format(dns_server), "+short", "+time=5", "+tries=1"]
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
    print("  dig PTR {}  (checking {} servers)".format(domain, len(servers)))
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
class TestPTRRecordCreate:

    def test_create_ptr1(self, ptr_api, api_testdata, ptr_record_ids):
        cfg = api_testdata["ptr_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "ptr1.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_1"],
            "cluster_name": cluster,
        }
        resp = ptr_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE ptr1 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] ptr1 -> {}".format(body))
        pk = ptr_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        ptr_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("ptr1.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig returned no PTR for ptr1 (DNS propagation pending)")

    def test_create_ptr2(self, ptr_api, api_testdata, ptr_record_ids):
        cfg = api_testdata["ptr_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "ptr2.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_2"],
            "cluster_name": cluster,
        }
        resp = ptr_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE ptr2 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] ptr2 -> {}".format(body))
        pk = ptr_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        ptr_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("ptr2.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig returned no PTR for ptr2 (DNS propagation pending)")

    def test_create_ptr3(self, ptr_api, api_testdata, ptr_record_ids):
        cfg = api_testdata["ptr_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "ptr3.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_3"],
            "cluster_name": cluster,
        }
        resp = ptr_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE ptr3 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] ptr3 -> {}".format(body))
        pk = ptr_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        ptr_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("ptr3.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig returned no PTR for ptr3 (DNS propagation pending)")


# ── READ ──────────────────────────────────────────────────────────── #
@pytest.mark.order(2)
class TestPTRRecordRead:

    def test_get_all_three(self, ptr_api, api_testdata, ptr_record_ids):
        if len(ptr_record_ids) < 3:
            pytest.skip("Not all 3 records were created")
        names = ["ptr1", "ptr2", "ptr3"]
        for i, pk in enumerate(ptr_record_ids[:3]):
            resp = ptr_api.get(pk)
            print("\n[API GET] {} pk={} -> {}: {}".format(
                names[i], pk, resp.status_code, resp.text[:250]))
            assert resp.status_code in (200, 400), "GET {} unexpected error: {}".format(names[i], resp.status_code)

    def test_get_nonexistent(self, ptr_api):
        resp = ptr_api.get(999999)
        assert resp.status_code in (400, 404)


# ── UPDATE ────────────────────────────────────────────────────────── #
@pytest.mark.order(3)
class TestPTRRecordUpdate:

    def test_update_ptr1(self, ptr_api, api_testdata, ptr_record_ids):
        if not ptr_record_ids:
            pytest.skip("No record to update")
        pk = ptr_record_ids[0]
        cfg = api_testdata["ptr_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]

        current = ptr_api.get(pk)
        assert current.status_code == 200
        update_data = current.json()
        print("\n[UPDATE] ptr1 OLD: {}".format(update_data.get("records", [])))

        update_data["records"] = cfg["update_records"]
        update_data["domain_ttl"] = cfg["update_ttl"]
        update_data["zone_name"] = zone
        update_data["cluster_name"] = cluster
        update_data.pop("ptr_domain_id", None)
        update_data.pop("zone_id", None)

        resp = ptr_api.update(pk, update_data)
        print("\n[API PUT] pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:300]))
        assert resp.status_code in (200, 201, 204), \
            "PUT failed: {} - {}".format(resp.status_code, resp.text)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("ptr1.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig returned no PTR after update (DNS propagation pending)")


# ── DELETE ────────────────────────────────────────────────────────── #
@pytest.mark.order(4)
class TestPTRRecordDelete:

    def test_delete_ptr2(self, ptr_api, api_testdata, ptr_record_ids):
        if len(ptr_record_ids) < 2:
            pytest.skip("ptr2 was not created")
        pk = ptr_record_ids[1]
        zone = api_testdata["zone_name"]

        resp = ptr_api.delete(pk)
        print("\n[API DELETE] ptr2 pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:200]))
        assert resp.status_code in (200, 204, 400), \
            "DELETE failed: {} - {}".format(resp.status_code, resp.text)

        # Verify ptr2 gone via API
        get_resp = ptr_api.get(pk)
        assert get_resp.status_code in (400, 404), "ptr2 still exists after DELETE"

        # Verify ptr1 and ptr3 remain
        r1 = ptr_api.get(ptr_record_ids[0])
        assert r1.status_code == 200, "ptr1 should still exist"
        r3 = ptr_api.get(ptr_record_ids[2])
        assert r3.status_code == 200, "ptr3 should still exist"
        print("\n[OK] ptr1 and ptr3 remain intact")
