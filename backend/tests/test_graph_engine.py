import pytest
from sqlalchemy.orm import Session
import backend.app.models as m
from backend.app.graph_engine.engine import DistributionGraphEngine
from backend.app.database.seed import seed_database
from backend.app.database.session import SessionLocal


@pytest.fixture(scope="module")
def seeded_db():
    """Ensure the synthetic grid is seeded into the database for graph tests."""
    seed_database(reset=True)
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="module")
def seeded_client(seeded_db):
    """Client configured with the seeded database."""
    from backend.app.database.session import get_db
    from backend.app.main import app
    from fastapi.testclient import TestClient

    def override_get_db():
        yield seeded_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


def test_radial_property(seeded_db: Session):
    """Verifies that the distribution grid operates as a radial forest with open tie switches."""
    engine = DistributionGraphEngine(db=seeded_db)
    assert engine.is_radial() is True, "Operational distribution grid must be strictly radial without closed loop cycles."


def test_traversal_correctness(seeded_db: Session):
    """Verifies upstream and downstream traversal on Feeder F4."""
    engine = DistributionGraphEngine(db=seeded_db, feeder_id=4)

    # Locate section F4-S14
    s14 = seeded_db.query(m.FeederSection).filter_by(section_code="F4-S14").first()
    assert s14 is not None

    # Upstream path must lead back through branch: S13 -> S12 -> S11 -> S10 -> ... -> S01
    upstream_ids = engine.get_upstream_sections(s14.id)
    upstream_codes = [engine.section_metadata[uid]["section_code"] for uid in upstream_ids]

    assert "F4-S13" in upstream_codes
    assert "F4-S12" in upstream_codes
    assert "F4-S11" in upstream_codes
    assert "F4-S10" in upstream_codes
    assert "F4-S01" in upstream_codes

    # Downstream from S10 must reach branch sections S11, S12, S13, S14
    s10 = seeded_db.query(m.FeederSection).filter_by(section_code="F4-S10").first()
    assert s10 is not None
    downstream_from_s10 = engine.get_downstream_sections(s10.id)
    downstream_s10_codes = [engine.section_metadata[did]["section_code"] for did in downstream_from_s10]

    assert "F4-S11" in downstream_s10_codes
    assert "F4-S12" in downstream_s10_codes
    assert "F4-S13" in downstream_s10_codes
    assert "F4-S14" in downstream_s10_codes


def test_hero_scenario_f4_candidate_pruning(seeded_db: Session):
    """
    Hero Scenario: Outage on Feeder F4 downstream branch with sections F4-S12 and F4-S14.
    Downstream transformers: DT-12, 13, 14.
    Critical Load: District Water Pump on DT-14.
    """
    engine = DistributionGraphEngine(db=seeded_db)

    # Telemetry observations:
    # Main trunk and lateral branch are observed healthy/energized
    energized_codes = [
        "F4-S01", "F4-S02", "F4-S03", "F4-S04", "F4-S05",
        "F4-S06", "F4-S07", "F4-S08", "F4-S09", "F4-S10",
        "F4-S15", "F4-S16", "F4-S17", "F4-S18"
    ]
    # Faulted branch end observed de-energized
    deenergized_codes = ["F4-S13", "F4-S14"]

    energized_ids = {s.id for s in seeded_db.query(m.FeederSection).filter(m.FeederSection.section_code.in_(energized_codes)).all()}
    deenergized_ids = {s.id for s in seeded_db.query(m.FeederSection).filter(m.FeederSection.section_code.in_(deenergized_codes)).all()}

    res = engine.prune_candidates(
        observed_energized_section_ids=energized_ids,
        observed_deenergized_section_ids=deenergized_ids,
    )

    candidate_codes = [c["section_code"] for c in res["topology_consistent_candidates"]]

    # F4-S12 and F4-S14 must be among the topology-consistent candidates
    assert "F4-S12" in candidate_codes
    assert "F4-S14" in candidate_codes

    # Main trunk sections (S01-S10) and lateral branch (S15-S18) must be pruned
    assert "F4-S01" not in candidate_codes
    assert "F4-S05" not in candidate_codes
    assert "F4-S15" not in candidate_codes

    # Verify downstream District Water Pump critical load detection
    water_pump_detected = False
    for cand in res["topology_consistent_candidates"]:
        for cl in cand["downstream_critical_loads"]:
            if cl["facility_name"] == "District Water Pump":
                water_pump_detected = True
                assert cl["priority_tier"] == 1
                assert cl["facility_type"] == "WATER_PUMPING"
    assert water_pump_detected is True, "District Water Pump must be identified downstream of candidate branch."

    # Verify real measured pruning percentage across the entire network
    assert res["pruning_percentage"] > 90.0, f"Expected >90% network pruning, got {res['pruning_percentage']}%"


def test_random_fault_case_1_feeder_f1(seeded_db: Session):
    """Random fault case 1: Outage on Feeder F1 (Hospital branch)."""
    engine = DistributionGraphEngine(db=seeded_db)

    # Trunk S01-S03 energized; S06-S08 de-energized
    e_codes = ["F1-S01", "F1-S02", "F1-S03"]
    d_codes = ["F1-S06", "F1-S07", "F1-S08"]

    e_ids = {s.id for s in seeded_db.query(m.FeederSection).filter(m.FeederSection.section_code.in_(e_codes)).all()}
    d_ids = {s.id for s in seeded_db.query(m.FeederSection).filter(m.FeederSection.section_code.in_(d_codes)).all()}

    res = engine.prune_candidates(e_ids, d_ids)
    candidate_codes = [c["section_code"] for c in res["topology_consistent_candidates"]]

    assert "F1-S01" not in candidate_codes
    assert res["pruning_percentage"] > 85.0


def test_random_fault_case_2_feeder_f5_oxygen_plant(seeded_db: Session):
    """Random fault case 2: Outage on Feeder F5 (Peenya Oxygen Plant)."""
    engine = DistributionGraphEngine(db=seeded_db)

    e_codes = ["F5-S01", "F5-S02", "F5-S03", "F5-S04"]
    d_codes = ["F5-S07", "F5-S08"]

    e_ids = {s.id for s in seeded_db.query(m.FeederSection).filter(m.FeederSection.section_code.in_(e_codes)).all()}
    d_ids = {s.id for s in seeded_db.query(m.FeederSection).filter(m.FeederSection.section_code.in_(d_codes)).all()}

    res = engine.prune_candidates(e_ids, d_ids)
    candidate_codes = [c["section_code"] for c in res["topology_consistent_candidates"]]

    assert "F5-S01" not in candidate_codes
    assert res["pruning_percentage"] > 85.0


def test_random_fault_case_3_feeder_f7_water_pumping(seeded_db: Session):
    """Random fault case 3: Outage on Feeder F7 (BWSSB Pumping)."""
    engine = DistributionGraphEngine(db=seeded_db)

    e_codes = ["F7-S01", "F7-S02"]
    d_codes = ["F7-S04", "F7-S05", "F7-S06"]

    e_ids = {s.id for s in seeded_db.query(m.FeederSection).filter(m.FeederSection.section_code.in_(e_codes)).all()}
    d_ids = {s.id for s in seeded_db.query(m.FeederSection).filter(m.FeederSection.section_code.in_(d_codes)).all()}

    res = engine.prune_candidates(e_ids, d_ids)
    candidate_codes = [c["section_code"] for c in res["topology_consistent_candidates"]]

    assert "F7-S01" not in candidate_codes
    assert res["pruning_percentage"] > 85.0


def test_network_topology_endpoint(seeded_client):
    """Verifies GET /network/topology endpoint returns full shared DB graph."""
    res = seeded_client.get("/network/topology")
    assert res.status_code == 200
    data = res.json()

    assert len(data["substations"]) == 2
    assert len(data["feeders"]) == 8
    assert data["total_sections"] >= 120
    assert data["total_transformers"] >= 35
    assert data["total_tie_switches"] >= 4
    assert data["is_radial"] is True


def test_localize_graph_endpoint(seeded_client):
    """Verifies POST /localize/graph endpoint returns topology-consistent candidates."""
    # 1. Feeder-scoped localization
    payload_feeder = {
        "feeder_code": "F4",
        "observed_energized_section_codes": ["F4-S01", "F4-S05", "F4-S10"],
        "observed_deenergized_section_codes": ["F4-S13", "F4-S14"]
    }
    res = seeded_client.post("/localize/graph", json=payload_feeder)
    assert res.status_code == 200
    data = res.json()

    assert data["pruning_percentage"] >= 50.0
    assert len(data["topology_consistent_candidates"]) > 0
    top_cand = data["topology_consistent_candidates"][0]
    assert top_cand["candidate_designation"] == "topology-consistent candidate"
    assert "evidence" in top_cand
    assert "electrical_metrics" in top_cand
    assert "ENGINEER REVIEW REQUIRED" in data["safety_advisory_notice"]

    # 2. Network-wide localization (without feeder filter)
    payload_network = {
        "observed_energized_section_codes": ["F4-S01", "F4-S05", "F4-S10"],
        "observed_deenergized_section_codes": ["F4-S13", "F4-S14"]
    }
    res_net = seeded_client.post("/localize/graph", json=payload_network)
    assert res_net.status_code == 200
    data_net = res_net.json()
    assert data_net["pruning_percentage"] > 90.0
    assert data_net["total_network_sections"] == 140
