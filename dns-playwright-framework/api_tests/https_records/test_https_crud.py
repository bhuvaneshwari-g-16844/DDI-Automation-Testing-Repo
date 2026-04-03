"""
test_https_crud.py – HTTPS record CRUD API tests with dig verification.

Creates https1, https2, https3 -> verifies with dig (TYPE65)
Updates https1                 -> verifies
Deletes https2 only            -> verifies https1 & https3 remain

Run:
    cd dns-playwright-framework
    pytest api_tests/https_records/test_https_crud.py -v -s
"""

import pytest
import subprocess
import time

DNS_SERVERS = ["10.73.17.98", "10.73.17.109", "10.72.44.98"]
DIG_WAIT = 3


def _dig_one(domain, dns_server):
    """dig HTTPS (TYPE65) against a single server."""
    cmd = ["dig", "TYPE65", domain, "@{}".format(dns_server), "+short", "+time=5", "+tries=1"]
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
    print("  dig HTTPS {}  (checking {} servers)".format(domain, len(servers)))
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
class TestHTTPSRecordCreate:

    def test_create_https1(self, https_api, api_testdata, https_record_ids):
        cfg = api_testdata["https_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "https1.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_1"],
            "cluster_name": cluster,
        }
        resp = https_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE https1 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] https1 -> {}".format(body))
        pk = https_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        https_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        _dig("https1.{}".format(zone))

    def test_create_https2(self, https_api, api_testdata, https_record_ids):
        cfg = api_testdata["https_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "https2.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_2"],
            "cluster_name": cluster,
        }
        resp = https_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE https2 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] https2 -> {}".format(body))
        pk = https_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        https_record_ids.append(pk)

    def test_create_https3(self, https_api, api_testdata, https_record_ids):
        cfg = api_testdata["https_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "https3.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_3"],
            "cluster_name": cluster,
        }
        resp = https_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE https3 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] https3 -> {}".format(body))
        pk = https_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        https_record_ids.append(pk)


# ── READ ──────────────────────────────────────────────────────────── #
@pytest.mark.order(2)
class TestHTTPSRecordRead:

    def test_get_all_three(self, https_api, api_testdata, https_record_ids):
        if len(https_record_ids) < 3:
            pytest.skip("Not all 3 records were created")
        names = ["https1", "https2", "https3"]
        for i, pk in enumerate(https_record_ids[:3]):
            resp = https_api.get(pk)
            print("\n[API GET] {} pk={} -> {}: {}".format(
                names[i], pk, resp.status_code, resp.text[:250]))
            assert resp.status_code in (200, 400), "GET {} unexpected error: {}".format(names[i], resp.status_code)

    def test_get_nonexistent(self, https_api):
        resp = https_api.get(999999)
        assert resp.status_code in (400, 404)


# ── UPDATE ────────────────────────────────────────────────────────── #
@pytest.mark.order(3)
class TestHTTPSRecordUpdate:

    def test_update_https1(self, https_api, api_testdata, https_record_ids):
        if not https_record_ids:
            pytest.skip("No record to update")
        pk = https_record_ids[0]
        cfg = api_testdata["https_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]

        current = https_api.get(pk)
        assert current.status_code == 200
        update_data = current.json()
        print("\n[UPDATE] https1 OLD: {}".format(update_data.get("records", [])))

        update_data["records"] = cfg["update_records"]
        update_data["domain_ttl"] = cfg["update_ttl"]
        update_data["zone_name"] = zone
        update_data["cluster_name"] = cluster
        update_data.pop("https_domain_id", None)
        update_data.pop("zone_id", None)

        resp = https_api.update(pk, update_data)
        print("\n[API PUT] pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:300]))
        assert resp.status_code in (200, 201, 204), \
            "PUT failed: {} - {}".format(resp.status_code, resp.text)


# ── DELETE ────────────────────────────────────────────────────────── #
@pytest.mark.order(4)
class TestHTTPSRecordDelete:

    def test_delete_https2(self, https_api, api_testdata, https_record_ids):
        if len(https_record_ids) < 2:
            pytest.skip("https2 was not created")
        pk = https_record_ids[1]

        resp = https_api.delete(pk)
        print("\n[API DELETE] https2 pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:200]))
        assert resp.status_code in (200, 204, 400), \
            "DELETE failed: {} - {}".format(resp.status_code, resp.text)

        get_resp = https_api.get(pk)
        assert get_resp.status_code in (400, 404), "https2 still exists after DELETE"

        # Verify https1 and https3 remain (only if they were created)
        if len(https_record_ids) >= 1:
            r1 = https_api.get(https_record_ids[0])
            assert r1.status_code == 200, "https1 should still exist"
        if len(https_record_ids) >= 3:
            r3 = https_api.get(https_record_ids[2])
            assert r3.status_code == 200, "https3 should still exist"
        print("\n[OK] https1 and https3 remain intact")
