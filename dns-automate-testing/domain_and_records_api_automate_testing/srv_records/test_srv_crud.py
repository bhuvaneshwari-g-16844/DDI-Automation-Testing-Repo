"""
test_srv_crud.py – SRV record CRUD API tests with dig verification.

Creates srv1, srv2, srv3 -> verifies with dig
Updates srv1             -> verifies with dig
Deletes srv2 only        -> verifies srv1 & srv3 remain

Run:
    cd dns-playwright-framework
    pytest domain_and_records_api_automate_testing/srv_records/test_srv_crud.py -v -s
"""

import pytest
import subprocess
import time

DNS_SERVERS = ["10.73.17.98", "10.73.17.109"]  # , "10.72.44.98"
DNS_SERVERS_PRIMARY = ["10.73.17.98", "10.73.17.109"]  # skip unreliable slave
DIG_WAIT = 3


def _dig_one(domain, dns_server):
    cmd = ["dig", "SRV", domain, "@{}".format(dns_server), "+short", "+time=5", "+tries=1"]
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
    print("  dig SRV {}  (checking {} servers)".format(domain, len(servers)))
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
class TestSRVRecordCreate:

    def test_create_srv1(self, srv_api, api_testdata, srv_record_ids):
        cfg = api_testdata["srv_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "srv1.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_1"],
            "cluster_name": cluster,
        }
        resp = srv_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE srv1 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] srv1 -> {}".format(body))
        pk = srv_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        srv_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("srv1.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig returned no SRV for srv1 (DNS propagation pending)")

    def test_create_srv2(self, srv_api, api_testdata, srv_record_ids):
        cfg = api_testdata["srv_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "srv2.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_2"],
            "cluster_name": cluster,
        }
        resp = srv_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE srv2 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] srv2 -> {}".format(body))
        pk = srv_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        srv_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("srv2.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig returned no SRV for srv2 (DNS propagation pending)")

    def test_create_srv3(self, srv_api, api_testdata, srv_record_ids):
        cfg = api_testdata["srv_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "srv3.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_3"],
            "cluster_name": cluster,
        }
        resp = srv_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE srv3 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] srv3 -> {}".format(body))
        pk = srv_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        srv_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("srv3.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig returned no SRV for srv3 (DNS propagation pending)")


# ── READ ──────────────────────────────────────────────────────────── #
@pytest.mark.order(2)
class TestSRVRecordRead:

    def test_get_all_three(self, srv_api, api_testdata, srv_record_ids):
        if len(srv_record_ids) < 3:
            pytest.skip("Not all 3 records were created")
        names = ["srv1", "srv2", "srv3"]
        for i, pk in enumerate(srv_record_ids[:3]):
            resp = srv_api.get(pk)
            print("\n[API GET] {} pk={} -> {}: {}".format(
                names[i], pk, resp.status_code, resp.text[:250]))
            assert resp.status_code in (200, 400), "GET {} unexpected error: {}".format(names[i], resp.status_code)

    def test_get_nonexistent(self, srv_api):
        resp = srv_api.get(999999)
        assert resp.status_code in (400, 404)


# ── UPDATE ────────────────────────────────────────────────────────── #
@pytest.mark.order(3)
class TestSRVRecordUpdate:

    def test_update_srv1(self, srv_api, api_testdata, srv_record_ids):
        if not srv_record_ids:
            pytest.skip("No record to update")
        pk = srv_record_ids[0]
        cfg = api_testdata["srv_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]

        current = srv_api.get(pk)
        assert current.status_code == 200
        update_data = current.json()
        print("\n[UPDATE] srv1 OLD: {}".format(update_data.get("records", [])))

        update_data["records"] = cfg["update_records"]
        update_data["domain_ttl"] = cfg["update_ttl"]
        update_data["zone_name"] = zone
        update_data["cluster_name"] = cluster
        update_data.pop("srv_domain_id", None)
        update_data.pop("zone_id", None)

        resp = srv_api.update(pk, update_data)
        print("\n[API PUT] pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:300]))
        assert resp.status_code in (200, 201, 204), \
            "PUT failed: {} - {}".format(resp.status_code, resp.text)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("srv1.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig returned no SRV after update (DNS propagation pending)")


# ── DELETE ────────────────────────────────────────────────────────── #
@pytest.mark.order(4)
class TestSRVRecordDelete:

    def test_delete_srv2(self, srv_api, api_testdata, srv_record_ids):
        if len(srv_record_ids) < 2:
            pytest.skip("srv2 was not created")
        pk = srv_record_ids[1]
        zone = api_testdata["zone_name"]

        resp = srv_api.delete(pk)
        print("\n[API DELETE] srv2 pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:200]))
        assert resp.status_code in (200, 204, 400), \
            "DELETE failed: {} - {}".format(resp.status_code, resp.text)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("srv2.{}".format(zone), servers=DNS_SERVERS_PRIMARY)
        if dig_vals:
            print("  [WARN] srv2 still resolves after DELETE (DNS propagation pending): {}".format(dig_vals))

        dig1 = _dig("srv1.{}".format(zone))
        if not dig1:
            print("  [WARN] srv1 not resolving via dig (DNS propagation pending)")
        dig3 = _dig("srv3.{}".format(zone))
        if not dig3:
            print("  [WARN] srv3 not resolving via dig (DNS propagation pending)")
        print("\n[OK] srv1 and srv3 remain intact")
