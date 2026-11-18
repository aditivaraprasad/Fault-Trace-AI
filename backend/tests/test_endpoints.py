from datetime import datetime, timezone
import pytest
import backend.app.models as m


def test_feeder_endpoints(client, db_session):
    # Setup prerequisite substation
    sub = m.Substation(
        name="Indiranagar 66kV Substation",
        code="IND-SS-01",
        latitude=12.9784,
        longitude=77.6408,
    )
    db_session.add(sub)
    db_session.commit()

    # 1. Test POST /api/v1/feeders
    post_payload = {
        "substation_id": sub.id,
        "feeder_code": "IND-F01",
        "name": "100ft Road Feeder",
        "voltage_kv": 11.0,
        "rated_current_a": 400.0,
        "nominal_capacity_mva": 8.0,
        "status": "ACTIVE",
        "total_length_km": 4.5,
    }
    res = client.post("/api/v1/feeders", json=post_payload)
    assert res.status_code == 201
    created = res.json()
    assert created["feeder_code"] == "IND-F01"
    feeder_id = created["id"]

    # 2. Test duplicate feeder code returns 409
    res_dup = client.post("/api/v1/feeders", json=post_payload)
    assert res_dup.status_code == 409

    # 3. Test GET /api/v1/feeders
    res_list = client.get("/api/v1/feeders")
    assert res_list.status_code == 200
    feeders = res_list.json()
    assert len(feeders) >= 1
    assert any(f["feeder_code"] == "IND-F01" for f in feeders)

    # 4. Test GET /api/v1/feeders/{id}
    res_get = client.get(f"/api/v1/feeders/{feeder_id}")
    assert res_get.status_code == 200
    detail = res_get.json()
    assert detail["name"] == "100ft Road Feeder"
    assert detail["substation_name"] == "Indiranagar 66kV Substation"
    assert detail["section_count"] == 0

    # 5. Test PATCH /api/v1/feeders/{id}
    res_patch = client.patch(f"/api/v1/feeders/{feeder_id}", json={"status": "MAINTENANCE"})
    assert res_patch.status_code == 200
    assert res_patch.json()["status"] == "MAINTENANCE"

    # 6. Test GET non-existent feeder returns 404
    res_404 = client.get("/api/v1/feeders/99999")
    assert res_404.status_code == 404


def test_asset_endpoints(client, db_session):
    # 1. Test POST /api/v1/assets
    asset_payload = {
        "asset_type": "TRANSFORMER",
        "asset_identifier": "DTC-IND-501",
        "health_index": 72.5,
        "condition_rating": "FAIR",
        "notes": "Moderate dissolved gas readings during routine test.",
    }
    res = client.post("/api/v1/assets", json=asset_payload)
    assert res.status_code == 201
    created = res.json()
    assert created["asset_identifier"] == "DTC-IND-501"
    asset_id = created["id"]

    # 2. Test GET /api/v1/assets
    res_list = client.get("/api/v1/assets?asset_type=TRANSFORMER")
    assert res_list.status_code == 200
    assets = res_list.json()
    assert len(assets) >= 1
    assert assets[0]["asset_identifier"] == "DTC-IND-501"

    # 3. Test GET /api/v1/assets/{id}
    res_get = client.get(f"/api/v1/assets/{asset_id}")
    assert res_get.status_code == 200
    assert res_get.json()["health_index"] == 72.5

    # 4. Test PATCH /api/v1/assets/{id}
    res_patch = client.patch(f"/api/v1/assets/{asset_id}", json={"health_index": 85.0, "condition_rating": "GOOD"})
    assert res_patch.status_code == 200
    assert res_patch.json()["health_index"] == 85.0
    assert res_patch.json()["condition_rating"] == "GOOD"

    # 5. Test 404 for missing asset
    res_404 = client.get("/api/v1/assets/99999")
    assert res_404.status_code == 404


def test_incident_endpoints(client, db_session):
    # Setup substation and feeder
    sub = m.Substation(name="SS-KOR", code="KOR-SS", latitude=12.93, longitude=77.62)
    db_session.add(sub)
    db_session.flush()

    feeder = m.Feeder(substation_id=sub.id, feeder_code="KOR-F01", name="Koramangala 80ft Feeder")
    db_session.add(feeder)
    db_session.flush()

    sec = m.FeederSection(feeder_id=feeder.id, section_code="KOR-SEC01", start_latitude=12.93, start_longitude=77.62, end_latitude=12.94, end_longitude=77.63)
    db_session.add(sec)
    db_session.flush()

    # 1. Test POST /api/v1/incidents
    inc_payload = {
        "scenario_id": "SCENARIO_KOR_01",
        "feeder_id": feeder.id,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "status": "INVESTIGATING",
        "fault_type": "LINE_TO_GROUND",
        "estimated_customers_affected": 240,
        "description": "Transient ground fault detected.",
    }
    res = client.post("/api/v1/incidents", json=inc_payload)
    assert res.status_code == 201
    incident = res.json()
    assert incident["scenario_id"] == "SCENARIO_KOR_01"
    incident_id = incident["id"]

    # Seed a candidate and restoration step directly to test detail endpoint response
    cand = m.FaultCandidate(
        incident_id=incident_id,
        section_id=sec.id,
        rank=1,
        raw_score=2.91,
        calibrated_probability=0.82,
        is_topology_consistent=True,
        candidate_designation="topology-consistent candidate",
        pruning_reason="Graph reachability downstream of breaker trip",
    )
    step = m.RestorationPriority(
        incident_id=incident_id,
        step_number=1,
        action_type="ISOLATE_SECTION",
        switch_code="AB-KOR-01",
        target_section_id=sec.id,
        advisory_notes="Manual isolation step.",
    )
    db_session.add_all([cand, step])
    db_session.commit()

    # 2. Test GET /api/v1/incidents (list)
    res_list = client.get("/api/v1/incidents?scenario_id=SCENARIO_KOR_01")
    assert res_list.status_code == 200
    incidents = res_list.json()
    assert len(incidents) == 1
    assert incidents[0]["feeder_code"] == "KOR-F01"

    # 3. Test GET /api/v1/incidents/{id} (detail)
    res_detail = client.get(f"/api/v1/incidents/{incident_id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert len(detail["candidates"]) == 1
    assert detail["candidates"][0]["raw_score"] == 2.91
    assert detail["candidates"][0]["calibrated_probability"] == 0.82
    assert detail["candidates"][0]["candidate_designation"] == "topology-consistent candidate"
    assert len(detail["restoration_steps"]) == 1
    assert "ENGINEER REVIEW REQUIRED" in detail["restoration_steps"][0]["safety_disclaimer"]
    assert "ENGINEER REVIEW REQUIRED" in detail["safety_advisory_notice"]

    # 4. Test PATCH /api/v1/incidents/{id}
    res_patch = client.patch(f"/api/v1/incidents/{incident_id}", json={"status": "RESOLVED"})
    assert res_patch.status_code == 200
    assert res_patch.json()["status"] == "RESOLVED"

    # 5. Test 404 for missing incident
    res_404 = client.get("/api/v1/incidents/99999")
    assert res_404.status_code == 404
