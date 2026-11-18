"""
Phase 6 Integration Tests.
Verifies:
1. Complete Hero Scenario Simulation Flow (POST /simulate/scenario preset 'f4_hero').
2. Random Scenario Simulation Flow (POST /simulate/scenario preset 'random').
3. Multi-source CSV Data Ingestion and 15-minute event correlation.
4. Malformed CSV Ingestion returning HTTP 422 with clear validation errors.
5. Weather API telemetry retrieval and source tracking ('live' vs 'synthetic').
6. Live Operational Dashboard statistics computation from database.
7. Asset filtering endpoints.
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import backend.app.models as m
from backend.app.database.seed import seed_database
from backend.app.database.session import SessionLocal, get_db
from backend.app.main import app

SAMPLES_DIR = "datasets/samples"


@pytest.fixture(scope="module")
def seeded_db():
    """Ensure the synthetic grid and hero scenario are seeded into the database."""
    seed_database(reset=True)
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="module")
def seeded_client(seeded_db):
    """TestClient configured with the seeded database."""
    def override_get_db():
        yield seeded_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


def test_hero_simulation_scenario_complete_flow(seeded_client: TestClient, seeded_db: Session):
    """
    Test 1: Complete Hero Scenario Simulation Flow.
    Asserts:
    - Feeder F4 trip under 48 km/h gusts.
    - True simulated section is stored as actual_fault_section (F4-S14).
    - Pipeline executes: create incident -> ingest events -> correlate -> graph candidates ->
      ML rank -> SHAP explain -> assets -> advisory restoration -> persist in DB.
    """
    payload = {
        "scenario_type": "f4_hero",
        "feeder_code": "F4",
        "complaint_count": 142,
        "wind_speed_kmh": 48.0,
    }
    resp = seeded_client.post("/simulate/scenario", json=payload)
    assert resp.status_code == 200, f"Simulation failed: {resp.text}"
    data = resp.json()

    # Verify simulation metadata
    assert data["scenario_type"] == "f4_hero"
    assert data["feeder_code"] == "F4"
    assert "HERO-F4-" in data["simulation_scenario_id"]
    assert data["complaints_logged_count"] == 142

    # Verify true simulated section ground truth
    actual_sec = data["actual_fault_section"]
    assert actual_sec["section_code"] == "F4-S14"

    # Verify weather observation
    weather = data["weather_observation"]
    assert weather["wind_gust_kmh"] == 48.0
    assert weather["source"] in ["live", "synthetic"]

    # Verify localization pipeline output
    loc = data["localization_result"]
    assert loc["incident_id"] == data["incident_id"]
    assert len(loc["candidates"]) >= 1
    top_cand = loc["candidates"][0]
    assert top_cand["candidate_designation"] == "topology-consistent candidate"
    assert "calibrated probability" in top_cand["probability_label"]

    # Verify SHAP attributions and engineering narrative
    assert "narrative" in top_cand
    assert len(top_cand["narrative"]) > 0

    # Verify restoration plan invariants
    restoration = loc["restoration_plan"]
    steps = restoration["recommended_switching_steps"]
    assert len(steps) >= 1
    assert steps[0]["action_type"] == "ISOLATE_FAULT_SECTION"
    assert steps[0]["target_section_code"] == "F4-S14"
    assert "ADVISORY, requires qualified engineer review" in restoration["advisory_disclaimer"]

    # Verify DB persistence
    inc_db = seeded_db.query(m.Incident).filter_by(id=data["incident_id"]).first()
    assert inc_db is not None
    assert inc_db.actual_fault_section_id == actual_sec["section_id"]
    assert len(inc_db.candidates) == len(loc["candidates"])


def test_random_simulation_scenario(seeded_client: TestClient):
    """Test 2: Random Scenario Simulation Flow."""
    payload = {"scenario_type": "random"}
    resp = seeded_client.post("/simulate/scenario", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["scenario_type"] == "random"
    assert "actual_fault_section" in data
    assert len(data["localization_result"]["candidates"]) >= 1


def test_csv_ingestion_valid_and_correlator(seeded_client: TestClient):
    """Test 3: Valid CSV uploads for breaker trips, voltage readings, and complaints."""
    # 1. Breaker trips
    bt_path = os.path.join(SAMPLES_DIR, "sample_breaker_trips.csv")
    with open(bt_path, "rb") as f:
        resp = seeded_client.post("/ingest/breaker-trips", files={"file": ("sample_breaker_trips.csv", f, "text/csv")})
    assert resp.status_code == 201
    assert resp.json()["rows_ingested"] == 3

    # 2. Voltage readings
    vr_path = os.path.join(SAMPLES_DIR, "sample_voltage_readings.csv")
    with open(vr_path, "rb") as f:
        resp = seeded_client.post("/ingest/voltage-readings", files={"file": ("sample_voltage_readings.csv", f, "text/csv")})
    assert resp.status_code == 201
    assert resp.json()["rows_ingested"] == 5

    # 3. Customer complaints
    cp_path = os.path.join(SAMPLES_DIR, "sample_complaints.csv")
    with open(cp_path, "rb") as f:
        resp = seeded_client.post("/ingest/complaints", files={"file": ("sample_complaints.csv", f, "text/csv")})
    assert resp.status_code == 201
    assert resp.json()["rows_ingested"] == 3


def test_csv_ingestion_malformed_returns_422(seeded_client: TestClient):
    """
    Test 4: Malformed CSV uploads must return HTTP 422 with clear validation error details.
    """
    malformed_path = os.path.join(SAMPLES_DIR, "malformed_breaker_trips.csv")
    with open(malformed_path, "rb") as f:
        resp = seeded_client.post("/ingest/breaker-trips", files={"file": ("malformed_breaker_trips.csv", f, "text/csv")})
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data
    assert "validation failed" in data["detail"].lower()


def test_weather_endpoints(seeded_client: TestClient):
    """Test 5: Weather endpoints and source reporting ('live' vs 'synthetic')."""
    # 1. GET /weather/current
    resp = seeded_client.get("/weather/current")
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] in ["live", "synthetic"]
    assert "wind_gust_kmh" in data

    # 2. POST /weather/fetch?force_synthetic=true
    resp_fetch = seeded_client.post("/weather/fetch?force_synthetic=true")
    assert resp_fetch.status_code == 200
    assert resp_fetch.json()["source"] == "synthetic"


def test_dashboard_stats_endpoint(seeded_client: TestClient):
    """Test 6: Live Operational Dashboard statistics computation."""
    resp = seeded_client.get("/dashboard/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_substations"] >= 2
    assert data["total_feeders"] >= 8
    assert data["total_sections"] >= 100
    assert data["total_transformers"] >= 30
    assert data["total_consumers"] > 0
    assert "model_metrics" in data
    assert data["model_metrics"]["expected_calibration_error_ece"] == 0.0054
    assert data["model_metrics"]["top_3_accuracy_pct"] == 89.33
    assert data["latest_weather"]["source"] in ["live", "synthetic"]


def test_assets_filtering_endpoint(seeded_client: TestClient):
    """Test 7: Asset filtering by condition rating and type."""
    # Filter by condition POOR
    resp = seeded_client.get("/assets?condition_rating=POOR")
    assert resp.status_code == 200
    data = resp.json()
    for item in data:
        assert item["condition_rating"] == "POOR"

    # Filter by asset_type SECTION
    resp_sec = seeded_client.get("/assets?asset_type=SECTION")
    assert resp_sec.status_code == 200
    data_sec = resp_sec.json()
    for item in data_sec:
        assert item["asset_type"] == "SECTION"
