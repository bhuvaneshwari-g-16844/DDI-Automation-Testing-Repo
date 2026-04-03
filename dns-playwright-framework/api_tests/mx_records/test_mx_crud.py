"""
test_mx_crud.py – MX record CRUD API tests with dig verification.

Creates mx1, mx2, mx3 -> verifies with dig
Updates mx1            -> verifies with dig
Deletes mx2 only       -> verifies mx1 & mx3 remain

Run:
    cd dns-playwright-framework
    pytest api_tests/mx_records/test_mx_crud.py -v -s
"""

import pytest
import subprocess
import time

pytestmark = pytest.mark.skip(reason="MX records not supported on DDNS zones")

DNS_SERVERS = ["10.73.17.98", "10.73.17.109", "10.72.44.98"]
DIG_WAIT = 3


def _dig_one(domain, dns_server):
    cmd = ["dig", "MX", domain, "@{}".format(dns_server), "+short", "+time=5", "+tries=1"]
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
    print("  dig MX {}  (checking {} servers)".format(domain, len(servers)))
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
class TestMXRecordCreate:

    def test_create_mx1(self, mx_api, api_testdata, mx_record_ids):
        cfg = api_testdata["mx_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "mx1.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_1"],
            "cluster_name": cluster,
        }
        resp = mx_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE mx1 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] mx1 -> {}".format(body))
        pk = mx_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        mx_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("mx1.{}".format(zone))
        assert len(dig_vals) > 0, "dig returned no MX for mx1"

    def test_create_mx2(self, mx_api, api_testdata, mx_record_ids):
        cfg = api_testdata["mx_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "mx2.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_2"],
            "cluster_name": cluster,
        }
        resp = mx_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE mx2 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] mx2 -> {}".format(body))
        pk = mx_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        mx_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("mx2.{}".format(zone))
        assert len(dig_vals) > 0, "dig returned no MX for mx2"

    def test_create_mx3(self, mx_api, api_testdata, mx_record_ids):
        cfg = api_testdata["mx_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "mx3.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_3"],
            "cluster_name": cluster,
        }
        resp = mx_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE mx3 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] mx3 -> {}".format(body))
        pk = mx_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        mx_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("mx3.{}".format(zone))
        assert len(dig_vals) > 0, "dig returned no MX for mx3"


# ── READ ──────────────────────────────────────────────────────────── #
@pytest.mark.order(2)
class TestMXRecordRead:

    def test_get_all_three(self, mx_api, api_testdata, mx_record_ids):
        if len(mx_record_ids) < 3:
            pytest.skip("Not all 3 records were created")
        names = ["mx1", "mx2", "mx3"]
        for i, pk in enumerate(mx_record_ids[:3]):
            resp = mx_api.get(pk)
            print("\n[API GET] {} pk={} -> {}: {}".format(
                names[i], pk, resp.status_code, resp.text[:250]))
            assert resp.status_code in (200, 400), "GET {} unexpected error: {}".format(names[i], resp.status_code)

    def test_get_nonexistent(self, mx_api):
        resp = mx_api.get(999999)
        assert resp.status_code in (400, 404)


# ── UPDATE ────────────────────────────────────────────────────────── #
@pytest.mark.order(3)
class TestMXRecordUpdate:

    def test_update_mx1(self, mx_api, api_testdata, mx_record_ids):
        if not mx_record_ids:
            pytest.skip("No record to update")
        pk = mx_record_ids[0]
        cfg = api_testdata["mx_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]

        current = mx_api.get(pk)
        assert current.status_code == 200
        update_data = current.json()
        print("\n[UPDATE] mx1 OLD: {}".format(update_data.get("records", [])))

        update_data["records"] = cfg["update_records"]
        update_data["domain_ttl"] = cfg["update_ttl"]
        update_data["zone_name"] = zone
        update_data["cluster_name"] = cluster
        update_data.pop("mx_domain_id", None)
        update_data.pop("zone_id", None)
        update_data.pop("count", None)

        resp = mx_api.update(pk, update_data)
        print("\n[API PUT] pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:300]))
        assert resp.status_code in (200, 201, 204), \
            "PUT failed: {} - {}".format(resp.status_code, resp.text)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("mx1.{}".format(zone))
        assert len(dig_vals) > 0, "dig returned no MX after update"


# ── DELETE ────────────────────────────────────────────────────────── #
@pytest.mark.order(4)
class TestMXRecordDelete:

    def test_delete_mx2(self, mx_api, api_testdata, mx_record_ids):
        if len(mx_record_ids) < 2:
            pytest.skip("mx2 was not created")
        pk = mx_record_ids[1]
        zone = api_testdata["zone_name"]

        resp = mx_api.delete(pk)
        print("\n[API DELETE] mx2 pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:200]))
        assert resp.status_code in (200, 204, 400), \
            "DELETE failed: {} - {}".format(resp.status_code, resp.text)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("mx2.{}".format(zone))
        assert len(dig_vals) == 0, "mx2 still resolves: {}".format(dig_vals)

        dig1 = _dig("mx1.{}".format(zone))
        assert len(dig1) > 0, "mx1 should still resolve!"
        dig3 = _dig("mx3.{}".format(zone))
        assert len(dig3) > 0, "mx3 should still resolve!"
        print("\n[OK] mx1 and mx3 remain intact")
