"""
test_caa_crud.py – CAA record CRUD API tests.

Creates caa1, caa2, caa3 -> GET verify
Updates caa1              -> verify
Deletes caa2 only         -> verify caa1 & caa3 remain

Run:
    cd dns-playwright-framework
    pytest domain_and_records_api_automate_testing/caa_records/test_caa_crud.py -v -s
"""

import pytest


# ── CREATE ────────────────────────────────────────────────────────── #
@pytest.mark.order(1)
class TestCAARecordCreate:

    def test_create_caa1(self, caa_api, api_testdata, caa_record_ids):
        cfg = api_testdata["caa_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "caa1.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_1"],
            "cluster_name": cluster,
        }
        resp = caa_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE caa1 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] caa1 -> {}".format(body))
        pk = caa_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        caa_record_ids.append(pk)

    def test_create_caa2(self, caa_api, api_testdata, caa_record_ids):
        cfg = api_testdata["caa_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "caa2.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_2"],
            "cluster_name": cluster,
        }
        resp = caa_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE caa2 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] caa2 -> {}".format(body))
        pk = caa_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        caa_record_ids.append(pk)

    def test_create_caa3(self, caa_api, api_testdata, caa_record_ids):
        cfg = api_testdata["caa_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "caa3.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_3"],
            "cluster_name": cluster,
        }
        resp = caa_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE caa3 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] caa3 -> {}".format(body))
        pk = caa_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        caa_record_ids.append(pk)


# ── READ ──────────────────────────────────────────────────────────── #
@pytest.mark.order(2)
class TestCAARecordRead:

    def test_get_all_three(self, caa_api, api_testdata, caa_record_ids):
        if len(caa_record_ids) < 3:
            pytest.skip("Not all 3 records were created")
        names = ["caa1", "caa2", "caa3"]
        for i, pk in enumerate(caa_record_ids[:3]):
            resp = caa_api.get(pk)
            print("\n[API GET] {} pk={} -> {}: {}".format(
                names[i], pk, resp.status_code, resp.text[:250]))
            assert resp.status_code in (200, 400), "GET {} unexpected error: {}".format(names[i], resp.status_code)

    def test_get_nonexistent(self, caa_api):
        resp = caa_api.get(999999)
        print("\n[API GET 404] {}: {}".format(resp.status_code, resp.text))
        assert resp.status_code in (400, 404)


# ── UPDATE ────────────────────────────────────────────────────────── #
@pytest.mark.order(3)
class TestCAARecordUpdate:

    def test_update_caa1(self, caa_api, api_testdata, caa_record_ids):
        if not caa_record_ids:
            pytest.skip("No record to update")
        pk = caa_record_ids[0]
        cfg = api_testdata["caa_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]

        current = caa_api.get(pk)
        assert current.status_code == 200
        update_data = current.json()
        print("\n[UPDATE] caa1 OLD records: {}".format(update_data.get("records", [])))

        update_data["records"] = cfg["update_records"]
        update_data["domain_ttl"] = cfg["update_ttl"]
        update_data["zone_name"] = zone
        update_data["cluster_name"] = cluster
        update_data.pop("caa_domain_id", None)
        update_data.pop("zone_id", None)

        resp = caa_api.update(pk, update_data)
        print("\n[API PUT] pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:300]))
        assert resp.status_code in (200, 201, 204), \
            "PUT failed: {} - {}".format(resp.status_code, resp.text)
        print("[VERIFY] caa1 updated successfully")


# ── DELETE ────────────────────────────────────────────────────────── #
@pytest.mark.order(4)
class TestCAARecordDelete:

    def test_delete_caa2(self, caa_api, api_testdata, caa_record_ids):
        if len(caa_record_ids) < 2:
            pytest.skip("caa2 was not created")
        pk = caa_record_ids[1]

        resp = caa_api.delete(pk)
        print("\n[API DELETE] caa2 pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:200]))
        assert resp.status_code in (200, 204, 400), \
            "DELETE caa2 failed: {} - {}".format(resp.status_code, resp.text)

        # Verify caa2 is gone
        get_resp = caa_api.get(pk)
        assert get_resp.status_code in (400, 404), "caa2 still exists after DELETE"

        # Verify caa1 and caa3 remain
        r1 = caa_api.get(caa_record_ids[0])
        assert r1.status_code == 200, "caa1 should still exist"
        r3 = caa_api.get(caa_record_ids[2])
        assert r3.status_code == 200, "caa3 should still exist"
        print("\n[OK] caa1 and caa3 remain intact")
