"""
Phase 5 Service and Endpoint Tests.
Verifies:
1. Candidate ranking order is strictly consistent with calibrated probabilities and model scores.
2. SHAP attributions, structured positive/negative evidence, and narratives exist for every candidate.
3. Restoration plan never routes power into or energizes a candidate fault section.
4. Endpoints: POST /incidents/{id}/localize, GET /incidents/{id}/explanation,
   GET /incidents/{id}/assets, GET /incidents/{id}/restoration.
"""

import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

import backend.app.models as m
from backend.app.database.seed import seed_database
from backend.app.database.session import SessionLocal, get_db
from backend.app.main import app
from backend.app.services.localization import FaultLocalizationService
from backend.app.services.asset_analysis import AssetAnalysisService
from backend.app.services.restoration import RestorationService, ADVISORY_DISCLAIMER
from backend.app.explainability.explainer import ShapExplainerService


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


def test_ranking_order_consistent_with_scores(seeded_db: Session):
    """
    Test 1: Verify ranking order is consistent with scores and calibrated probabilities.
    Asserts:
    - Ranks are ordered 1, 2, 3, ...
    - Calibrated probabilities are monotonically non-increasing (rank N >= rank N+1).
    - Candidate designation strictly adheres to 'topology-consistent candidate'.
    - Output probabilities are labeled correctly.
    """
    hero_incident = seeded_db.query(m.Incident).filter_by(scenario_id="SCENARIO_HERO_F4").first()
    assert hero_incident is not None

    service = FaultLocalizationService(db=seeded_db)
    result = service.localize_incident(hero_incident.id)

    assert "candidates" in result
    candidates = result["candidates"]
    assert len(candidates) >= 1

    prev_prob = 1.0
    for idx, cand in enumerate(candidates):
        expected_rank = idx + 1
        assert cand["rank"] == expected_rank, f"Candidate rank {cand['rank']} must match position {expected_rank}"
        
        cal_prob = cand["calibrated_probability"]
        assert 0.0 <= cal_prob <= 1.0, f"Calibrated probability {cal_prob} out of [0, 1] range"
        assert cal_prob <= prev_prob + 1e-5, f"Ranking inversion detected: {cal_prob} > {prev_prob}"
        prev_prob = cal_prob

        assert cand["candidate_designation"] == "topology-consistent candidate"
        assert "calibrated probability" in cand["probability_label"]
        assert "ECE =" in cand["probability_label"]


def test_shap_output_exists_for_every_candidate(seeded_db: Session):
    """
    Test 2: Verify SHAP explanations and structured evidence exist for EVERY candidate.
    Asserts:
    - shap_attributions dictionary contains all model features.
    - Top positive and top negative contributing features are extracted.
    - Readable engineering narrative is present.
    - For rank > 1 candidates, a comparative ranking reason explaining why it ranked below #1 is present.
    """
    hero_incident = seeded_db.query(m.Incident).filter_by(scenario_id="SCENARIO_HERO_F4").first()
    assert hero_incident is not None

    service = FaultLocalizationService(db=seeded_db)
    result = service.localize_incident(hero_incident.id)
    candidates = result["candidates"]

    # Also verify persisted predictions
    persisted_predictions = seeded_db.query(m.ModelPrediction).filter_by(incident_id=hero_incident.id).all()
    assert len(persisted_predictions) == len(candidates)

    for idx, cand in enumerate(candidates):
        # Explanations in result
        assert "narrative" in cand and len(cand["narrative"]) > 0
        assert "top_positive_features" in cand
        assert "top_negative_features" in cand
        assert isinstance(cand["top_positive_features"], list)
        assert isinstance(cand["top_negative_features"], list)

        # Comparative reason check
        if cand["rank"] > 1:
            assert cand["comparative_rank_reason"] is not None
            assert len(cand["comparative_rank_reason"]) > 0
            assert "Ranked lower than" in cand["comparative_rank_reason"]
        else:
            assert cand["comparative_rank_reason"] is None

        # Check persisted DB prediction record
        pred = seeded_db.query(m.ModelPrediction).filter_by(
            incident_id=hero_incident.id,
            candidate_id=seeded_db.query(m.FaultCandidate).filter_by(
                incident_id=hero_incident.id,
                rank=cand["rank"]
            ).first().id
        ).first()

        assert pred is not None
        assert pred.shap_values is not None
        assert len(pred.shap_values) >= 15
        assert "voltage_deviation" in pred.shap_values
        assert "complaint_density" in pred.shap_values


def test_restoration_plan_never_routes_power_into_fault_candidate(seeded_db: Session):
    """
    Test 3: Safety Invariant Verification.
    Asserts:
    - Candidate fault section is strictly ISOLATED before any downstream restore actions.
    - No switching instruction ever suggests energizing or routing power INTO the fault candidate section.
    - Advisory disclaimer is unconditionally attached to every plan.
    - Zero auto-execution: requires_engineer_approval is True.
    - Alternate tie switch back-feed verifies donor feeder headroom capacity.
    """
    # Test on Hero Section F4-S14 (where District Water Pump is downstream)
    s14 = seeded_db.query(m.FeederSection).filter_by(section_code="F4-S14").first()
    assert s14 is not None

    restoration_service = RestorationService(db=seeded_db)
    plan = restoration_service.plan_restoration(candidate_section_id=s14.id)

    assert "recommended_switching_steps" in plan
    steps = plan["recommended_switching_steps"]
    assert len(steps) >= 1

    # Invariant 1: Step 1 must physically ISOLATE the candidate fault section
    step1 = steps[0]
    assert step1["step_number"] == 1
    assert step1["action_type"] == "ISOLATE_FAULT_SECTION"
    assert step1["operation"] == "OPEN"
    assert step1["target_section_code"] == s14.section_code

    # Invariant 2: Candidate section is NEVER energized in any subsequent step
    for step in steps[1:]:
        assert step["operation"] != "CLOSE" or step["target_section_code"] != s14.section_code, (
            f"Safety violation: Step {step['step_number']} attempts to close switch onto candidate fault section {s14.section_code}!"
        )

    # Invariant 3: Advisory disclaimers and human authorization required
    assert "ADVISORY, requires qualified engineer review" in plan["advisory_disclaimer"]
    assert plan["requires_engineer_approval"] is True
    assert plan["approval_status"] == "PENDING_REVIEW"

    # Invariant 4: Check alternate path capacity verification
    if plan["alternate_paths_evaluated"]:
        for alt in plan["alternate_paths_evaluated"]:
            assert "donor_available_headroom_kva" in alt
            assert "load_to_transfer_kva" in alt
            assert "capacity_check_passed" in alt
            if alt["capacity_check_passed"]:
                assert alt["load_to_transfer_kva"] <= alt["donor_available_headroom_kva"]


def test_phase5_endpoints(seeded_client: TestClient, seeded_db: Session):
    """
    Test 4: Verify REST endpoints:
    - POST /incidents/{id}/localize
    - GET /incidents/{id}/explanation
    - GET /incidents/{id}/assets
    - GET /incidents/{id}/restoration
    """
    hero_incident = seeded_db.query(m.Incident).filter_by(scenario_id="SCENARIO_HERO_F4").first()
    assert hero_incident is not None
    inc_id = hero_incident.id

    # 1. POST /incidents/{id}/localize
    loc_resp = seeded_client.post(f"/incidents/{inc_id}/localize")
    assert loc_resp.status_code == 200
    loc_data = loc_resp.json()
    assert loc_data["incident_id"] == inc_id
    assert len(loc_data["candidates"]) >= 1
    assert "restoration_plan" in loc_data
    assert "ADVISORY" in loc_data["safety_advisory_notice"]

    # 2. GET /incidents/{id}/explanation
    exp_resp = seeded_client.get(f"/incidents/{inc_id}/explanation")
    assert exp_resp.status_code == 200
    exp_data = exp_resp.json()
    assert exp_data["incident_id"] == inc_id
    assert len(exp_data["candidates"]) >= 1
    top_cand = exp_data["candidates"][0]
    assert "narrative" in top_cand
    assert "shap_attributions" in top_cand
    assert "probability_label" in top_cand
    assert "calibrated probability" in top_cand["probability_label"]

    # 3. GET /incidents/{id}/assets
    asset_resp = seeded_client.get(f"/incidents/{inc_id}/assets")
    assert asset_resp.status_code == 200
    asset_data = asset_resp.json()
    assert "candidate_section_code" in asset_data
    assert "severity_level" in asset_data
    assert "estimated_duration_minutes" in asset_data
    assert "downstream_transformers" in asset_data
    assert "estimated_consumers_affected" in asset_data

    # 4. GET /incidents/{id}/restoration
    rest_resp = seeded_client.get(f"/incidents/{inc_id}/restoration")
    assert rest_resp.status_code == 200
    rest_data = rest_resp.json()
    assert "restoration_priority_score" in rest_data
    assert "score_breakdown" in rest_data
    assert "recommended_switching_steps" in rest_data
    assert rest_data["recommended_switching_steps"][0]["action_type"] == "ISOLATE_FAULT_SECTION"
    assert "ADVISORY" in rest_data["advisory_disclaimer"]

    # 5. Verify /api/v1 prefix aliases also work
    loc_v1 = seeded_client.post(f"/api/v1/incidents/{inc_id}/localize")
    assert loc_v1.status_code == 200
    exp_v1 = seeded_client.get(f"/api/v1/incidents/{inc_id}/explanation")
    assert exp_v1.status_code == 200
