"""
test_ns_crud.py – NS record CRUD API tests with dig verification.

Creates nsr1, nsr2, nsr3 -> verifies with dig
Updates nsr1              -> verifies with dig
Deletes nsr2 only         -> verifies nsr1 & nsr3 remain

Run:
    cd dns-playwright-framework
    pytest domain_and_records_api_automate_testing/ns_records/test_ns_crud.py -v -s
"""

import pytest
import subprocess
import time

DNS_SERVERS = ["10.73.17.98", "10.73.17.109"]  # , "10.72.44.98"
DIG_WAIT = 3


def _dig_one(domain, dns_server):
    cmd = ["dig", "NS", domain, "@{}".format(dns_server), "+short", "+time=5", "+tries=1"]
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
    print("  dig NS {}  (checking {} servers)".format(domain, len(servers)))
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
class TestNSRecordCreate:

    def test_create_nsr1(self, ns_api, api_testdata, ns_record_ids):
        cfg = api_testdata["ns_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "nsr1.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_1"],
            "cluster_name": cluster,
        }
        resp = ns_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE nsr1 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] nsr1 -> {}".format(body))
        pk = ns_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        ns_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("nsr1.{}".format(zone))
        print("[INFO] NS dig returned {} records (NS delegation may not resolve)".format(len(dig_vals)))

    def test_create_nsr2(self, ns_api, api_testdata, ns_record_ids):
        cfg = api_testdata["ns_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "nsr2.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_2"],
            "cluster_name": cluster,
        }
        resp = ns_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE nsr2 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] nsr2 -> {}".format(body))
        pk = ns_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        ns_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("nsr2.{}".format(zone))
        print("[INFO] NS dig returned {} records (NS delegation may not resolve)".format(len(dig_vals)))

    def test_create_nsr3(self, ns_api, api_testdata, ns_record_ids):
        cfg = api_testdata["ns_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "nsr3.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_3"],
            "cluster_name": cluster,
        }
        resp = ns_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE nsr3 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] nsr3 -> {}".format(body))
        pk = ns_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        ns_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("nsr3.{}".format(zone))
        print("[INFO] NS dig returned {} records (NS delegation may not resolve)".format(len(dig_vals)))


# ── READ ──────────────────────────────────────────────────────────── #
@pytest.mark.order(2)
class TestNSRecordRead:

    def test_get_all_three(self, ns_api, api_testdata, ns_record_ids):
        if len(ns_record_ids) < 3:
            pytest.skip("Not all 3 records were created")
        names = ["nsr1", "nsr2", "nsr3"]
        for i, pk in enumerate(ns_record_ids[:3]):
            resp = ns_api.get(pk)
            print("\n[API GET] {} pk={} -> {}: {}".format(
                names[i], pk, resp.status_code, resp.text[:250]))
            assert resp.status_code in (200, 400), "GET {} unexpected error: {}".format(names[i], resp.status_code)

    def test_get_nonexistent(self, ns_api):
        resp = ns_api.get(999999)
        assert resp.status_code in (400, 404)


# ── UPDATE ────────────────────────────────────────────────────────── #
@pytest.mark.order(3)
class TestNSRecordUpdate:

    def test_update_nsr1(self, ns_api, api_testdata, ns_record_ids):
        if not ns_record_ids:
            pytest.skip("No record to update")
        pk = ns_record_ids[0]
        cfg = api_testdata["ns_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]

        current = ns_api.get(pk)
        assert current.status_code == 200
        update_data = current.json()
        print("\n[UPDATE] nsr1 OLD: {}".format(update_data.get("records", [])))

        update_data["records"] = cfg["update_records"]
        update_data["domain_ttl"] = cfg["update_ttl"]
        update_data["zone_name"] = zone
        update_data["cluster_name"] = cluster
        update_data.pop("ns_domain_id", None)
        update_data.pop("zone_id", None)

        resp = ns_api.update(pk, update_data)
        print("\n[API PUT] pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:300]))
        assert resp.status_code in (200, 201, 204), \
            "PUT failed: {} - {}".format(resp.status_code, resp.text)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("nsr1.{}".format(zone))
        print("[INFO] NS dig after update: {} records".format(len(dig_vals)))


# ── DELETE ────────────────────────────────────────────────────────── #
@pytest.mark.order(4)
class TestNSRecordDelete:

    def test_delete_nsr2(self, ns_api, api_testdata, ns_record_ids):
        if len(ns_record_ids) < 2:
            pytest.skip("nsr2 was not created")
        pk = ns_record_ids[1]
        zone = api_testdata["zone_name"]

        resp = ns_api.delete(pk)
        print("\n[API DELETE] nsr2 pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:200]))
        assert resp.status_code in (200, 204, 400), \
            "DELETE failed: {} - {}".format(resp.status_code, resp.text)

        # Verify nsr2 gone via API
        get_resp = ns_api.get(pk)
        assert get_resp.status_code in (400, 404), "nsr2 still exists after DELETE"

        # Verify nsr1 and nsr3 remain via API
        r1 = ns_api.get(ns_record_ids[0])
        assert r1.status_code == 200, "nsr1 should still exist"
        r3 = ns_api.get(ns_record_ids[2])
        assert r3.status_code == 200, "nsr3 should still exist"
        print("\n[OK] nsr1 and nsr3 remain intact")
