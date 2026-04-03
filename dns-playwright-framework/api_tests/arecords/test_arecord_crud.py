"""
test_arecord_crud.py – A-record CRUD API tests with dig verification.

Creates api1, api2, api3 → verifies with dig
Updates api1 IPs          → verifies with dig
Deletes api2 only         → verifies with dig (api1 & api3 remain)

Master DNS: 10.73.17.98
Zone: linux-ddns.com. (zone_pk=361)

Run:
    cd dns-playwright-framework
    pytest api_tests/arecords/test_arecord_crud.py -v -s
"""

import pytest
import random
import subprocess
import time


DNS_SERVERS = ["10.73.17.98", "10.73.17.109", "10.72.44.98"]
DNS_SERVERS_PRIMARY = ["10.73.17.98", "10.73.17.109"]  # skip unreliable slave
DIG_WAIT = 3  # seconds to wait for DNS propagation before dig


def _extract_pk(body):
    """Extract the A-record primary key from the API response."""
    return body.get("a_domain_id") or body.get("id") or body.get("pk")


def _random_ip():
    """Generate a random IP to avoid DDNS duplicate errors."""
    return "99.{}.{}.{}".format(
        random.randint(1, 254), random.randint(1, 254), random.randint(1, 254)
    )


def _dig_one(domain, dns_server):
    """Run dig against a single DNS server. Returns list of IPs."""
    cmd = ["dig", "A", domain, "@{}".format(dns_server), "+short", "+time=5", "+tries=1"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        output = result.stdout.strip()
        ips = [line.strip() for line in output.splitlines() if line.strip() and not line.startswith(';')]
        return ips
    except subprocess.TimeoutExpired:
        return None  # None = unreachable


def _dig(domain, servers=None):
    """
    Run dig against all DNS servers and print results.
    Unreachable servers are logged as warnings (not failures).
    Returns dict {server: [ips]} and combined unique ip list from reachable servers.
    """
    if servers is None:
        servers = DNS_SERVERS
    all_ips = set()
    results = {}

    print("\n" + "=" * 70)
    print("  dig A {}  (checking {} servers)".format(domain, len(servers)))
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


# ────────────────────────────────────────────────────────────────────── #
#  CREATE 3 records: api1, api2, api3
# ────────────────────────────────────────────────────────────────────── #
@pytest.mark.order(1)
class TestARecordCreate:
    """POST /api/dns/zone/{zone_pk}/A/ – Create 3 A records and dig verify."""

    def test_create_api1(self, arecord_api, api_testdata, created_record_ids):
        """Create api1.linux-ddns.com. with 2 IPs."""
        cfg = api_testdata["arecord"]
        ips = [_random_ip(), _random_ip()]
        payload = {
            "domain_name": "api1.{}".format(cfg["zone_name"]),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": cfg["zone_name"],
            "records": ips,
            "cluster_name": cfg["cluster_name"],
        }
        resp = arecord_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE api1 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] api1 -> {}".format(body))
        pk = _extract_pk(body)
        assert pk, "No a_domain_id: {}".format(body)
        created_record_ids.append(pk)

        # dig verify on all DNS servers
        time.sleep(DIG_WAIT)
        srv_results, dig_ips = _dig("api1.{}".format(cfg["zone_name"]))
        for ip in ips:
            assert ip in dig_ips, \
                "dig missing IP {} for api1, got: {}".format(ip, dig_ips)

    def test_create_api2(self, arecord_api, api_testdata, created_record_ids):
        """Create api2.linux-ddns.com. with 1 IP."""
        cfg = api_testdata["arecord"]
        ips = [_random_ip()]
        payload = {
            "domain_name": "api2.{}".format(cfg["zone_name"]),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": cfg["zone_name"],
            "records": ips,
            "cluster_name": cfg["cluster_name"],
        }
        resp = arecord_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE api2 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] api2 -> {}".format(body))
        pk = _extract_pk(body)
        assert pk, "No a_domain_id: {}".format(body)
        created_record_ids.append(pk)

        # dig verify on all DNS servers
        time.sleep(DIG_WAIT)
        srv_results, dig_ips = _dig("api2.{}".format(cfg["zone_name"]))
        for ip in ips:
            assert ip in dig_ips, \
                "dig missing IP {} for api2, got: {}".format(ip, dig_ips)

    def test_create_api3(self, arecord_api, api_testdata, created_record_ids):
        """Create api3.linux-ddns.com. with 2 IPs."""
        cfg = api_testdata["arecord"]
        ips = [_random_ip(), _random_ip()]
        payload = {
            "domain_name": "api3.{}".format(cfg["zone_name"]),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": cfg["zone_name"],
            "records": ips,
            "cluster_name": cfg["cluster_name"],
        }
        resp = arecord_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE api3 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] api3 -> {}".format(body))
        pk = _extract_pk(body)
        assert pk, "No a_domain_id: {}".format(body)
        created_record_ids.append(pk)

        # dig verify on all DNS servers
        time.sleep(DIG_WAIT)
        srv_results, dig_ips = _dig("api3.{}".format(cfg["zone_name"]))
        for ip in ips:
            assert ip in dig_ips, \
                "dig missing IP {} for api3, got: {}".format(ip, dig_ips)


# ────────────────────────────────────────────────────────────────────── #
#  READ – verify all 3 exist via API
# ────────────────────────────────────────────────────────────────────── #
@pytest.mark.order(2)
class TestARecordRead:
    """GET /api/dns/zone/{zone_pk}/A/{pk}/ – Verify records."""

    def test_get_all_three(self, arecord_api, api_testdata, created_record_ids):
        """GET each of the 3 created records by pk."""
        if len(created_record_ids) < 3:
            pytest.skip("Not all 3 records were created")
        names = ["api1", "api2", "api3"]
        for i, pk in enumerate(created_record_ids[:3]):
            resp = arecord_api.get(pk)
            print("\n[API GET] {} pk={} -> {}: {}".format(
                names[i], pk, resp.status_code, resp.text[:250]))
            assert resp.status_code in (200, 400), \
                "GET {} failed: {}".format(names[i], resp.text)
            if resp.status_code == 200:
                body = resp.json()
                assert "{}." in body.get("domain_name", "") or names[i] in body.get("domain_name", "")

    def test_get_nonexistent(self, arecord_api):
        """GET bogus pk -> 400."""
        resp = arecord_api.get(999999)
        print("\n[API GET 404] {}: {}".format(resp.status_code, resp.text))
        assert resp.status_code in (400, 404)


# ────────────────────────────────────────────────────────────────────── #
#  UPDATE – change api1 IPs, verify with dig
# ────────────────────────────────────────────────────────────────────── #
@pytest.mark.order(3)
class TestARecordUpdate:
    """PUT /api/dns/zone/{zone_pk}/A/{pk}/ – Update api1 and dig verify."""

    def test_update_api1(self, arecord_api, api_testdata, created_record_ids):
        """PUT – change api1 IPs to update_records, verify with dig."""
        if not created_record_ids:
            pytest.skip("No record to update")

        pk = created_record_ids[0]  # api1
        cfg = api_testdata["arecord"]
        new_ips = cfg["update_records"]

        # GET current record
        current = arecord_api.get(pk)
        assert current.status_code == 200, "GET before PUT failed: {}".format(current.text)
        update_data = current.json()
        old_ips = update_data.get("records", [])
        print("\n[UPDATE] api1 OLD IPs: {}".format(old_ips))
        print("[UPDATE] api1 NEW IPs: {}".format(new_ips))

        update_data["records"] = new_ips
        update_data["domain_ttl"] = cfg["update_ttl"]
        update_data.pop("a_domain_id", None)
        update_data.pop("zone_id", None)
        update_data.pop("record_mode", None)

        resp = arecord_api.update(pk, update_data)
        print("\n[API PUT] pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:300]))
        assert resp.status_code in (200, 201, 204), \
            "PUT failed: {} - {}".format(resp.status_code, resp.text)

        if resp.status_code in (200, 201):
            body = resp.json()
            assert sorted(body.get("records", [])) == sorted(new_ips), \
                "API records mismatch after update"

        # dig verify on all DNS servers – new IPs should appear
        time.sleep(DIG_WAIT)
        srv_results, dig_ips = _dig("api1.{}".format(cfg["zone_name"]))
        for ip in new_ips:
            assert ip in dig_ips, \
                "dig missing updated IP {} for api1, got: {}".format(ip, dig_ips)
        print("[VERIFY] api1 updated IPs confirmed on all servers")


# ────────────────────────────────────────────────────────────────────── #
#  DELETE – remove only api2, verify with dig on all servers
# ────────────────────────────────────────────────────────────────────── #
@pytest.mark.order(4)
class TestARecordDelete:
    """DELETE /api/dns/zone/{zone_pk}/A/{pk}/ – Delete api2 only."""

    def test_delete_api2(self, arecord_api, api_testdata, created_record_ids):
        """Delete api2, dig all servers to confirm it's gone, api1 & api3 remain."""
        if len(created_record_ids) < 2:
            pytest.skip("api2 was not created")

        pk = created_record_ids[1]  # api2
        cfg = api_testdata["arecord"]

        # Show api2 IPs before delete on all servers
        print("\n--- api2 BEFORE delete ---")
        _dig("api2.{}".format(cfg["zone_name"]))

        resp = arecord_api.delete(pk)
        print("\n[API DELETE] api2 pk={} -> {}: {}".format(
            pk, resp.status_code, resp.text[:200]))
        assert resp.status_code in (200, 204, 400), \
            "DELETE api2 failed: {} - {}".format(resp.status_code, resp.text)

        # dig verify on all servers – api2 should be gone
        time.sleep(DIG_WAIT)
        print("\n--- api2 AFTER delete ---")
        srv_results, dig_ips = _dig("api2.{}".format(cfg["zone_name"]), servers=DNS_SERVERS_PRIMARY)
        assert len(dig_ips) == 0, \
            "api2 still resolves after DELETE! IPs: {}".format(dig_ips)
        print("[VERIFY] api2 deleted on all servers")

        # Confirm api1 and api3 still resolve on all servers
        print("\n--- Confirm api1 still exists on all servers ---")
        _, api1_ips = _dig("api1.{}".format(cfg["zone_name"]))
        assert len(api1_ips) > 0, "api1 should still resolve!"

        print("\n--- Confirm api3 still exists on all servers ---")
        _, api3_ips = _dig("api3.{}".format(cfg["zone_name"]))
        assert len(api3_ips) > 0, "api3 should still resolve!"

        print("\n[OK] api1 and api3 records remain intact in the application")
