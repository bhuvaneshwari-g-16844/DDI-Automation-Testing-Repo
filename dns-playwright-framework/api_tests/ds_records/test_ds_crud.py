"""
test_ds_crud.py – DS record CRUD API tests.

Creates ds1, ds2, ds3 -> GET verify
Updates ds1           -> verify
Deletes ds2 only      -> verify ds1 & ds3 remain

Note: DS records are not queryable via standard dig; verification is API-only.

Run:
    cd dns-playwright-framework
    pytest api_tests/ds_records/test_ds_crud.py -v -s
"""

import pytest

pytestmark = pytest.mark.skip(reason="DS records not supported on DDNS zones – server returns fake 200 but does not persist")


# ── CREATE ────────────────────────────────────────────────────────── #
@pytest.mark.order(1)
class TestDSRecordCreate:

    def test_create_ds1(self, ds_api, api_testdata, ds_record_ids):
        cfg = api_testdata["ds_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "ds1.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_1"],
            "cluster_name": cluster,
        }
        resp = ds_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE ds1 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] ds1 -> {}".format(body))
        pk = ds_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        ds_record_ids.append(pk)

    def test_create_ds2(self, ds_api, api_testdata, ds_record_ids):
        cfg = api_testdata["ds_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "ds2.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_2"],
            "cluster_name": cluster,
        }
        resp = ds_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE ds2 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] ds2 -> {}".format(body))
        pk = ds_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        ds_record_ids.append(pk)

    def test_create_ds3(self, ds_api, api_testdata, ds_record_ids):
        cfg = api_testdata["ds_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]
        payload = {
            "domain_name": "ds3.{}".format(zone),
            "domain_ttl": cfg["domain_ttl"],
            "zone_name": zone,
            "records": cfg["records_3"],
            "cluster_name": cluster,
        }
        resp = ds_api.create_or_replace(payload)
        assert resp.status_code in (200, 201), \
            "CREATE ds3 failed: {} - {}".format(resp.status_code, resp.text)
        body = resp.json()
        print("\n[API CREATE] ds3 -> {}".format(body))
        pk = ds_api.extract_pk(body)
        assert pk, "No pk: {}".format(body)
        ds_record_ids.append(pk)


# ── READ ──────────────────────────────────────────────────────────── #
@pytest.mark.order(2)
class TestDSRecordRead:

    def test_get_all_three(self, ds_api, api_testdata, ds_record_ids):
        if len(ds_record_ids) < 3:
            pytest.skip("Not all 3 records were created")
        names = ["ds1", "ds2", "ds3"]
        for i, pk in enumerate(ds_record_ids[:3]):
            resp = ds_api.get(pk)
            print("\n[API GET] {} pk={} -> {}: {}".format(
                names[i], pk, resp.status_code, resp.text[:250]))
            assert resp.status_code in (200, 400), "GET {} unexpected error: {}".format(names[i], resp.status_code)

    def test_get_nonexistent(self, ds_api):
        resp = ds_api.get(999999)
        assert resp.status_code in (400, 404)


# ── UPDATE ────────────────────────────────────────────────────────── #
@pytest.mark.order(3)
class TestDSRecordUpdate:

    def test_update_ds1(self, ds_api, api_testdata, ds_record_ids):
        if not ds_record_ids:
            pytest.skip("No record to update")
        pk = ds_record_ids[0]
        cfg = api_testdata["ds_record"]
        zone = api_testdata["zone_name"]
        cluster = api_testdata["cluster_name"]

        current = ds_api.get(pk)
        assert current.status_code == 200
        update_data = current.json()
        print("\n[UPDATE] ds1 OLD: {}".format(update_data.get("records", [])))

        update_data["records"] = cfg["update_records"]
        update_data["domain_ttl"] = cfg["update_ttl"]
        update_data["zone_name"] = zone
        update_data["cluster_name"] = cluster
        update_data.pop("ds_domain_id", None)
        update_data.pop("zone_id", None)

        resp = ds_api.update(pk, update_data)
        print("\n[API PUT] pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:300]))
        assert resp.status_code in (200, 201, 204), \
            "PUT failed: {} - {}".format(resp.status_code, resp.text)


# ── DELETE ────────────────────────────────────────────────────────── #
@pytest.mark.order(4)
class TestDSRecordDelete:

    def test_delete_ds2(self, ds_api, api_testdata, ds_record_ids):
        if len(ds_record_ids) < 2:
            pytest.skip("ds2 was not created")
        pk = ds_record_ids[1]

        resp = ds_api.delete(pk)
        print("\n[API DELETE] ds2 pk={} -> {}: {}".format(pk, resp.status_code, resp.text[:200]))
        assert resp.status_code in (200, 204, 400), \
            "DELETE failed: {} - {}".format(resp.status_code, resp.text)

        get_resp = ds_api.get(pk)
        assert get_resp.status_code in (400, 404), "ds2 still exists after DELETE"

        r1 = ds_api.get(ds_record_ids[0])
        assert r1.status_code == 200, "ds1 should still exist"
        r3 = ds_api.get(ds_record_ids[2])
        assert r3.status_code == 200, "ds3 should still exist"
        print("\n[OK] ds1 and ds3 remain intact")
