from datetime import datetime, timezone, timedelta
import pytest
import backend.app.models as m


def test_substation_feeder_relationship(db_session):
    sub = m.Substation(
        name="Peenya 220/66kV Substation",
        code="PNY-SS-01",
        latitude=13.0285,
        longitude=77.5195,
        voltage_kv=220.0,
        capacity_mva=100.0,
        division="Bangalore West",
        subdivision="Peenya",
    )
    db_session.add(sub)
    db_session.commit()

    feeder = m.Feeder(
        substation_id=sub.id,
        feeder_code="PNY-F01",
        name="Peenya Industrial Feeder",
        voltage_kv=11.0,
        rated_current_a=600.0,
        nominal_capacity_mva=10.0,
        status="ACTIVE",
    )
    db_session.add(feeder)
    db_session.commit()

    # Query back and verify relationship
    queried_sub = db_session.query(m.Substation).filter_by(code="PNY-SS-01").first()
    assert queried_sub is not None
    assert len(queried_sub.feeders) == 1
    assert queried_sub.feeders[0].feeder_code == "PNY-F01"
    assert queried_sub.feeders[0].substation.name == "Peenya 220/66kV Substation"


def test_feeder_section_tree_hierarchy(db_session):
    sub = m.Substation(
        name="Whitefield Substation",
        code="WFD-SS-01",
        latitude=12.9698,
        longitude=77.7499,
        voltage_kv=66.0,
    )
    db_session.add(sub)
    db_session.flush()

    feeder = m.Feeder(
        substation_id=sub.id,
        feeder_code="WFD-F01",
        name="ITPL Feeder",
    )
    db_session.add(feeder)
    db_session.flush()

    # Root section
    root_sec = m.FeederSection(
        feeder_id=feeder.id,
        parent_section_id=None,
        section_code="WFD-SEC-ROOT",
        start_latitude=12.9698,
        start_longitude=77.7499,
        end_latitude=12.9720,
        end_longitude=77.7510,
    )
    db_session.add(root_sec)
    db_session.flush()

    # Child section
    child_sec = m.FeederSection(
        feeder_id=feeder.id,
        parent_section_id=root_sec.id,
        section_code="WFD-SEC-BRANCH1",
        start_latitude=12.9720,
        start_longitude=77.7510,
        end_latitude=12.9750,
        end_longitude=77.7530,
    )
    db_session.add(child_sec)
    db_session.commit()

    # Verify hierarchy
    assert child_sec.parent_section.section_code == "WFD-SEC-ROOT"
    assert len(root_sec.child_sections) == 1
    assert root_sec.child_sections[0].section_code == "WFD-SEC-BRANCH1"


def test_network_connection_tie_switch(db_session):
    sub = m.Substation(name="SS-A", code="SSA", latitude=13.0, longitude=77.0)
    db_session.add(sub)
    db_session.flush()

    f1 = m.Feeder(substation_id=sub.id, feeder_code="F1", name="Feeder 1")
    f2 = m.Feeder(substation_id=sub.id, feeder_code="F2", name="Feeder 2")
    db_session.add_all([f1, f2])
    db_session.flush()

    s1 = m.FeederSection(feeder_id=f1.id, section_code="S1", start_latitude=13.0, start_longitude=77.0, end_latitude=13.01, end_longitude=77.01)
    s2 = m.FeederSection(feeder_id=f2.id, section_code="S2", start_latitude=13.02, start_longitude=77.02, end_latitude=13.03, end_longitude=77.03)
    db_session.add_all([s1, s2])
    db_session.flush()

    tie = m.NetworkConnection(
        from_section_id=s1.id,
        to_section_id=s2.id,
        switch_code="TIE-01",
        switch_type="TIE_SWITCH",
        is_tie_switch=True,
        is_normally_open=True,
        current_status="OPEN",
        rated_current_a=400.0,
    )
    db_session.add(tie)
    db_session.commit()

    assert tie.is_tie_switch is True
    assert tie.is_normally_open is True
    assert tie.current_status == "OPEN"
    assert tie.from_section.section_code == "S1"
    assert tie.to_section.section_code == "S2"


def test_incident_candidates_and_restoration_disclaimer(db_session):
    sub = m.Substation(name="SS-B", code="SSB", latitude=13.0, longitude=77.0)
    db_session.add(sub)
    db_session.flush()

    feeder = m.Feeder(substation_id=sub.id, feeder_code="FB", name="Feeder B")
    db_session.add(feeder)
    db_session.flush()

    sec = m.FeederSection(feeder_id=feeder.id, section_code="SB1", start_latitude=13.0, start_longitude=77.0, end_latitude=13.01, end_longitude=77.01)
    db_session.add(sec)
    db_session.flush()

    now = datetime.now(timezone.utc)
    incident = m.Incident(
        scenario_id="SCENARIO_TEST_99",
        feeder_id=feeder.id,
        start_time=now,
        fault_type="LINE_TO_GROUND",
    )
    db_session.add(incident)
    db_session.flush()

    candidate = m.FaultCandidate(
        incident_id=incident.id,
        section_id=sec.id,
        rank=1,
        raw_score=3.14,
        calibrated_probability=0.88,
        is_topology_consistent=True,
        candidate_designation="topology-consistent candidate",
    )
    db_session.add(candidate)

    step = m.RestorationPriority(
        incident_id=incident.id,
        step_number=1,
        action_type="ISOLATE_SECTION",
        switch_code="SW-01",
        target_section_id=sec.id,
        advisory_notes="Advisory isolation recommendation.",
    )
    db_session.add(step)
    db_session.commit()

    # Rule checks
    assert candidate.raw_score == 3.14
    assert candidate.calibrated_probability == 0.88
    assert candidate.candidate_designation == "topology-consistent candidate"
    assert "ENGINEER REVIEW REQUIRED" in step.safety_disclaimer
    assert step.requires_engineer_approval is True
