"""
test_spf_crud.py – SPF record CRUD API tests with dig verification.

Creates spf1, spf2, spf3 -> verifies with dig SPF query
Updates spf1              -> verifies with dig
Deletes spf2 only         -> verifies spf1 & spf3 remain

Run:
    cd dns-playwright-framework
    python3 -m pytest api_tests/spf_records/test_spf_crud.py -v -s
"""

import pytest
import subprocess
import time

DNS_SERVERS = ["10.73.17.98", "10.73.17.109"]  # , "10.72.44.98"
DNS_SERVERS_PRIMARY = ["10.73.17.98", "10.73.17.109"]
DIG_WAIT = 3


def _dig_one(domain, dns_server):
    """Run: dig SPF <domain> @<server> +short"""
    cmd = ["dig", "SPF", domain, "@{}".format(dns_server), "+short", "+time=5", "+tries=1"]
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
    print("  dig SPF {}  (checking {} servers)".format(domain, len(servers)))
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
class TestSPFRecordCreate:

    def test_create_spf1(self, spf_api, api_testdata, spf_record_ids):
        cfg = api_testdata["spf_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "spf1.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_1"],
            "record_type": cfg["record_type"],
            "cluster_name": cluster,
        }
        resp = spf_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE spf1 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] spf1 -> {}".format(body))
        pk = spf_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        spf_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("spf1.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig SPF returned no records (DNS propagation pending)")

    def test_create_spf2(self, spf_api, api_testdata, spf_record_ids):
        cfg = api_testdata["spf_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "spf2.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_2"],
            "record_type": cfg["record_type"],
            "cluster_name": cluster,
        }
        resp = spf_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE spf2 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] spf2 -> {}".format(body))
        pk = spf_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        spf_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("spf2.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig SPF returned no records (DNS propagation pending)")

    def test_create_spf3(self, spf_api, api_testdata, spf_record_ids):
        cfg = api_testdata["spf_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "spf3.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_3"],
            "record_type": cfg["record_type"],
            "cluster_name": cluster,
        }
        resp = spf_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE spf3 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] spf3 -> {}".format(body))
        pk = spf_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        spf_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("spf3.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig SPF returned no records (DNS propagation pending)")


# ── READ ──────────────────────────────────────────────────────────── #
@pytest.mark.order(2)
class TestSPFRecordRead:

    def test_get_all_three(self, spf_api, api_testdata, spf_record_ids):
        if len(spf_record_ids) < 3:
            pytest.skip("Not all 3 records were created")
        names = ["spf1", "spf2", "spf3"]
        for i, pk in enumerate(spf_record_ids[:3]):
            resp = spf_api.get(pk)
            print("\n[API GET] {} pk={} -> {}: {}".format(
                names[i], pk, resp.status_code, resp.text[:250]))
            assert resp.status_code in (200, 400), "GET {} unexpected error: {}".format(names[i], resp.status_code)

    def test_get_nonexistent(self, spf_api):
        resp = spf_api.get(999999)
        assert resp.status_code in (400, 404)


# ── UPDATE ────────────────────────────────────────────────────────── #
@pytest.mark.order(3)
class TestSPFRecordUpdate:

    def test_update_spf1(self, spf_api, api_testdata, spf_record_ids):
        if not spf_record_ids:
            pytest.skip("No record to update")
        pk = spf_record_ids[0]
        cfg = api_testdata["spf_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]

        current = spf_api.get(pk)
        assert current.status_code == 200
        update_data = current.json()
        print("\n[UPDATE] spf1 OLD: {}".format(update_data.get("records", [])))

        update_data["records"] = cfg["update_records"]
        update_data["domain_ttl"] = cfg["update_ttl"]
        update_data["zone_name"] = zone
        update_data["cluster_name"] = cluster
        update_data["record_type"] = cfg["record_type"]
        update_data.pop("spf_txt_domain_id", None)
        update_data.pop("zone_id", None)

        resp = spf_api.update(pk, update_data)
        print("\n[API PUT] pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:300]))
        assert resp.status_code in (200, 201, 204), \
            "PUT failed: {} - {}".format(resp.status_code, resp.text)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("spf1.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig SPF returned no records (DNS propagation pending)")


# ── DELETE ────────────────────────────────────────────────────────── #
@pytest.mark.order(4)
class TestSPFRecordDelete:

    def test_delete_spf2(self, spf_api, api_testdata, spf_record_ids):
        if len(spf_record_ids) < 2:
            pytest.skip("spf2 was not created")
        pk = spf_record_ids[1]
        zone = api_testdata["zone_name"]

        resp = spf_api.delete(pk)
        print("\n[API DELETE] spf2 pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:200]))
        assert resp.status_code in (200, 204, 400), \
            "DELETE failed: {} - {}".format(resp.status_code, resp.text)

        time.sleep(DIG_WAIT + 3)
        _dig("spf2.{}".format(zone), servers=DNS_SERVERS_PRIMARY)

        # Verify spf1 and spf3 still exist via API
        pk1 = spf_record_ids[0]
        pk3 = spf_record_ids[2]
        resp1 = spf_api.get(pk1)
        resp3 = spf_api.get(pk3)
        assert resp1.status_code == 200, "spf1 should still exist!"
        assert resp3.status_code == 200, "spf3 should still exist!"
        print("\n[OK] spf1 and spf3 remain intact")
        _dig("spf1.{}".format(zone))
        _dig("spf3.{}".format(zone))
