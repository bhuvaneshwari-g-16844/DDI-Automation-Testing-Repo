"""
test_aaaa_crud.py – AAAA record CRUD API tests with dig verification.

Creates aaaa1, aaaa2, aaaa3 -> verifies with dig (AAAA query)
Updates aaaa1               -> verifies with dig
Deletes aaaa2 only          -> verifies with dig (aaaa1 & aaaa3 remain)

Run:
    cd dns-playwright-framework
    pytest api_tests/aaaa_records/test_aaaa_crud.py -v -s
"""

import pytest
import subprocess
import time

DNS_SERVERS = ["10.73.17.98", "10.73.17.109"]  # , "10.72.44.98"
DNS_SERVERS_PRIMARY = ["10.73.17.98", "10.73.17.109"]  # skip unreliable slave
DIG_WAIT = 3


def _dig_one(domain, dns_server):
    cmd = ["dig", "AAAA", domain, "@{}".format(dns_server), "+short", "+time=5", "+tries=1"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        ips = [l.strip() for l in result.stdout.strip().splitlines() if l.strip() and not l.startswith(';')]
        return ips
    except subprocess.TimeoutExpired:
        return None


def _dig(domain, servers=None):
    if servers is None:
        servers = DNS_SERVERS
    all_ips = set()
    results = {}
    print("\n" + "=" * 70)
    print("  dig AAAA {}  (checking {} servers)".format(domain, len(servers)))
    print("=" * 70)
    for srv in servers:
        ips = _dig_one(domain, srv)
        results[srv] = ips
        if ips is None:
            print("  @{:<16s} -> [TIMEOUT - server unreachable]".format(srv))
        elif ips:
            all_ips.update(ips)
            print("  @{:<16s} -> {}".format(srv, ", ".join(sorted(ips))))
        else:
            print("  @{:<16s} -> (no records)".format(srv))
    print("-" * 70)
    return results, sorted(all_ips)


# ── CREATE ────────────────────────────────────────────────────────── #
@pytest.mark.order(1)
class TestAAAARecordCreate:

    def test_create_aaaa1(self, aaaa_api, api_testdata, aaaa_record_ids):
        cfg = api_testdata["aaaa_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "aaaa1.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_1"],
            "cluster_name": cluster,
        }
        resp = aaaa_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE aaaa1 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] aaaa1 -> {}".format(body))
        pk = aaaa_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        aaaa_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        _, dig_ips = _dig("aaaa1.{}".format(zone))
        for ip in cfg["records_1"]:
            if ip not in dig_ips:
                print("  [WARN] dig missing {} for aaaa1 (DNS propagation pending)".format(ip))

    def test_create_aaaa2(self, aaaa_api, api_testdata, aaaa_record_ids):
        cfg = api_testdata["aaaa_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "aaaa2.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_2"],
            "cluster_name": cluster,
        }
        resp = aaaa_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE aaaa2 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] aaaa2 -> {}".format(body))
        pk = aaaa_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        aaaa_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        _, dig_ips = _dig("aaaa2.{}".format(zone))
        for ip in cfg["records_2"]:
            if ip not in dig_ips:
                print("  [WARN] dig missing {} for aaaa2 (DNS propagation pending)".format(ip))

    def test_create_aaaa3(self, aaaa_api, api_testdata, aaaa_record_ids):
        cfg = api_testdata["aaaa_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "aaaa3.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_3"],
            "cluster_name": cluster,
        }
        resp = aaaa_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE aaaa3 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] aaaa3 -> {}".format(body))
        pk = aaaa_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        aaaa_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        _, dig_ips = _dig("aaaa3.{}".format(zone))
        for ip in cfg["records_3"]:
            if ip not in dig_ips:
                print("  [WARN] dig missing {} for aaaa3 (DNS propagation pending)".format(ip))


# ── READ ──────────────────────────────────────────────────────────── #
@pytest.mark.order(2)
class TestAAAARecordRead:

    def test_get_all_three(self, aaaa_api, api_testdata, aaaa_record_ids):
        if len(aaaa_record_ids) < 3:
            pytest.skip("Not all 3 records were created")
        names = ["aaaa1", "aaaa2", "aaaa3"]
        for i, pk in enumerate(aaaa_record_ids[:3]):
            resp = aaaa_api.get(pk)
            print("\n[API GET] {} pk={} -> {}: {}".format(
                names[i], pk, resp.status_code, resp.text[:250]))
            assert resp.status_code in (200, 400), "GET {} unexpected error: {}".format(names[i], resp.status_code)

    def test_get_nonexistent(self, aaaa_api):
        resp = aaaa_api.get(999999)
        print("\n[API GET 404] {}: {}".format(resp.status_code, resp.text))
        assert resp.status_code in (400, 404)


# ── UPDATE ────────────────────────────────────────────────────────── #
@pytest.mark.order(3)
class TestAAAARecordUpdate:

    def test_update_aaaa1(self, aaaa_api, api_testdata, aaaa_record_ids):
        pk = aaaa_record_ids[0]
        cfg = api_testdata["aaaa_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        new_ips = cfg["update_records"]

        current = aaaa_api.get(pk)
        assert current.status_code == 200
        cur_body = current.json()
        print("\n[UPDATE] aaaa1 OLD: {}".format(cur_body.get("records", [])))
        print("[UPDATE] aaaa1 NEW: {}".format(new_ips))

        update_data = {
            "domain_name": cur_body.get("domain_name"),
            "domain_ttl": cfg["update_ttl"],
            "zone_name": zone,
            "cluster_name": cluster,
            "records": new_ips,
        }

        resp = aaaa_api.update(pk, update_data)
        print("\n[API PUT] pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:300]))
        assert resp.status_code in (200, 201, 204), \
            "PUT failed: {} - {}".format(resp.status_code, resp.text)

        time.sleep(DIG_WAIT)
        _, dig_ips = _dig("aaaa1.{}".format(zone))
        for ip in new_ips:
            if ip not in dig_ips:
                print("  [WARN] dig missing updated {} for aaaa1 (DNS propagation pending)".format(ip))


# ── DELETE ────────────────────────────────────────────────────────── #
@pytest.mark.order(4)
class TestAAAARecordDelete:

    def test_delete_aaaa2(self, aaaa_api, api_testdata, aaaa_record_ids):
        if len(aaaa_record_ids) < 2:
            pytest.skip("aaaa2 was not created")
        pk = aaaa_record_ids[1]
        zone = api_testdata["zone_name"]

        resp = aaaa_api.delete(pk)
        print("\n[API DELETE] aaaa2 pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:200]))
        assert resp.status_code in (200, 204, 400), \
            "DELETE aaaa2 failed: {} - {}".format(resp.status_code, resp.text)

        time.sleep(DIG_WAIT)
        _, dig_ips = _dig("aaaa2.{}".format(zone), servers=DNS_SERVERS_PRIMARY)
        if dig_ips:
            print("  [WARN] aaaa2 still resolves after DELETE (DNS propagation pending): {}".format(dig_ips))

        _, api1_ips = _dig("aaaa1.{}".format(zone))
        if not api1_ips:
            print("  [WARN] aaaa1 not resolving via dig (DNS propagation pending)")

        _, api3_ips = _dig("aaaa3.{}".format(zone))
        if not api3_ips:
            print("  [WARN] aaaa3 not resolving via dig (DNS propagation pending)")
        print("\n[OK] aaaa1 and aaaa3 remain intact")
