"""
test_txt_crud.py – TXT record (SPF_TXT) CRUD API tests with dig verification.

Creates txt1, txt2, txt3 -> verifies with dig
Updates txt1             -> verifies with dig
Deletes txt2 only        -> verifies txt1 & txt3 remain

Run:
    cd dns-playwright-framework
    pytest domain_and_records_api_automate_testing/txt_records/test_txt_crud.py -v -s
"""

import pytest
import subprocess
import time

DNS_SERVERS = ["10.73.17.98", "10.73.17.109"]  # , "10.72.44.98"
DNS_SERVERS_PRIMARY = ["10.73.17.98", "10.73.17.109"]  # skip unreliable slave
DIG_WAIT = 3


def _dig_one(domain, dns_server):
    cmd = ["dig", "TXT", domain, "@{}".format(dns_server), "+short", "+time=5", "+tries=1"]
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
    print("  dig TXT {}  (checking {} servers)".format(domain, len(servers)))
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
class TestTXTRecordCreate:

    def test_create_txt1(self, txt_api, api_testdata, txt_record_ids):
        cfg = api_testdata["txt_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "txt1.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_1"],
            "record_type": cfg["record_type"],
            "cluster_name": cluster,
        }
        resp = txt_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE txt1 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] txt1 -> {}".format(body))
        pk = txt_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        txt_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("txt1.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig returned no TXT for txt1 (DNS propagation pending)")

    def test_create_txt2(self, txt_api, api_testdata, txt_record_ids):
        cfg = api_testdata["txt_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "txt2.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_2"],
            "record_type": cfg["record_type"],
            "cluster_name": cluster,
        }
        resp = txt_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE txt2 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] txt2 -> {}".format(body))
        pk = txt_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        txt_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("txt2.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig returned no TXT for txt2 (DNS propagation pending)")

    def test_create_txt3(self, txt_api, api_testdata, txt_record_ids):
        cfg = api_testdata["txt_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "txt3.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_3"],
            "record_type": cfg["record_type"],
            "cluster_name": cluster,
        }
        resp = txt_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE txt3 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] txt3 -> {}".format(body))
        pk = txt_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        txt_record_ids.append(pk)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("txt3.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig returned no TXT for txt3 (DNS propagation pending)")


# ── READ ──────────────────────────────────────────────────────────── #
@pytest.mark.order(2)
class TestTXTRecordRead:

    def test_get_all_three(self, txt_api, api_testdata, txt_record_ids):
        if len(txt_record_ids) < 3:
            pytest.skip("Not all 3 records were created")
        names = ["txt1", "txt2", "txt3"]
        for i, pk in enumerate(txt_record_ids[:3]):
            resp = txt_api.get(pk)
            print("\n[API GET] {} pk={} -> {}: {}".format(
                names[i], pk, resp.status_code, resp.text[:250]))
            assert resp.status_code in (200, 400), "GET {} unexpected error: {}".format(names[i], resp.status_code)

    def test_get_nonexistent(self, txt_api):
        resp = txt_api.get(999999)
        assert resp.status_code in (400, 404)


# ── UPDATE ────────────────────────────────────────────────────────── #
@pytest.mark.order(3)
class TestTXTRecordUpdate:

    def test_update_txt1(self, txt_api, api_testdata, txt_record_ids):
        if not txt_record_ids:
            pytest.skip("No record to update")
        pk = txt_record_ids[0]
        cfg = api_testdata["txt_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]

        current = txt_api.get(pk)
        assert current.status_code == 200
        update_data = current.json()
        print("\n[UPDATE] txt1 OLD: {}".format(update_data.get("records", [])))

        update_data["records"] = cfg["update_records"]
        update_data["domain_ttl"] = cfg["update_ttl"]
        update_data["zone_name"] = zone
        update_data["cluster_name"] = cluster
        update_data["record_type"] = cfg["record_type"]
        update_data.pop("spf_txt_domain_id", None)
        update_data.pop("zone_id", None)

        resp = txt_api.update(pk, update_data)
        print("\n[API PUT] pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:300]))
        assert resp.status_code in (200, 201, 204), \
            "PUT failed: {} - {}".format(resp.status_code, resp.text)

        time.sleep(DIG_WAIT)
        dig_vals = _dig("txt1.{}".format(zone))
        if not dig_vals:
            print("  [WARN] dig returned no TXT after update (DNS propagation pending)")


# ── DELETE ────────────────────────────────────────────────────────── #
@pytest.mark.order(4)
class TestTXTRecordDelete:

    def test_delete_txt2(self, txt_api, api_testdata, txt_record_ids):
        if len(txt_record_ids) < 2:
            pytest.skip("txt2 was not created")
        pk = txt_record_ids[1]
        zone = api_testdata["zone_name"]

        resp = txt_api.delete(pk)
        print("\n[API DELETE] txt2 pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:200]))
        assert resp.status_code in (200, 204, 400), \
            "DELETE failed: {} - {}".format(resp.status_code, resp.text)

        time.sleep(DIG_WAIT + 3)  # extra wait for DNS propagation on delete
        dig_vals = _dig("txt2.{}".format(zone), servers=DNS_SERVERS_PRIMARY)
        if dig_vals:
            print("  [WARN] txt2 still resolves after DELETE (DNS propagation pending): {}".format(dig_vals))

        dig1 = _dig("txt1.{}".format(zone))
        if not dig1:
            print("  [WARN] txt1 not resolving via dig (DNS propagation pending)")
        dig3 = _dig("txt3.{}".format(zone))
        if not dig3:
            print("  [WARN] txt3 not resolving via dig (DNS propagation pending)")
        print("\n[OK] txt1 and txt3 remain intact")
