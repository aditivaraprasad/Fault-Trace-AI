"""
Database Seeding Script for FAULTTRACE AI.
Populates the realistic synthetic Bengaluru distribution network into SQLite/PostgreSQL.
Ensures the DB, Graph Engine, and Frontend Map share the identical source of truth.
"""

from datetime import datetime, timezone, timedelta
from backend.app.database.session import SessionLocal, engine, Base
import backend.app.models as m
from backend.app.simulation.network_generator import generate_synthetic_grid


def seed_database(reset: bool = True):
    """Loads the deterministic synthetic network into the database."""
    print("Initializing database tables...")
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("Generating synthetic Bengaluru distribution network data (seed=42)...")
        grid = generate_synthetic_grid(seed=42)

        # 1. Substations
        substation_map = {}
        for s_data in grid["substations"]:
            sub = m.Substation(**s_data)
            db.add(sub)
            db.flush()
            substation_map[sub.code] = sub.id

        # 2. Feeders
        feeder_map = {}
        for f_data in grid["feeders"]:
            sub_id = substation_map[f_data["substation_code"]]
            feeder = m.Feeder(
                substation_id=sub_id,
                feeder_code=f_data["feeder_code"],
                name=f_data["name"],
                voltage_kv=f_data["voltage_kv"],
                rated_current_a=f_data["rated_current_a"],
                nominal_capacity_mva=f_data["nominal_capacity_mva"],
                status=f_data["status"],
            )
            db.add(feeder)
            db.flush()
            feeder_map[feeder.feeder_code] = feeder.id

        # 3. Sections: topological order insertion (parents first)
        section_map = {}
        pending_sections = list(grid["sections"])
        inserted_count = 0

        # Loop until all sections are inserted respecting parent_section_id
        while pending_sections:
            progress = False
            remaining = []
            for sec_data in pending_sections:
                p_code = sec_data["parent_section_code"]
                if p_code is None or p_code in section_map:
                    parent_id = section_map[p_code] if p_code else None
                    sec = m.FeederSection(
                        feeder_id=feeder_map[sec_data["feeder_code"]],
                        parent_section_id=parent_id,
                        section_code=sec_data["section_code"],
                        length_km=sec_data["length_km"],
                        resistance_ohm=sec_data["resistance_ohm"],
                        reactance_ohm=sec_data["reactance_ohm"],
                        rated_capacity_kva=sec_data["rated_capacity_kva"],
                        conductor_type=sec_data["conductor_type"],
                        start_latitude=sec_data["start_latitude"],
                        start_longitude=sec_data["start_longitude"],
                        end_latitude=sec_data["end_latitude"],
                        end_longitude=sec_data["end_longitude"],
                        status=sec_data["status"],
                    )
                    db.add(sec)
                    db.flush()
                    section_map[sec.section_code] = sec.id
                    progress = True
                    inserted_count += 1
                else:
                    remaining.append(sec_data)
            if not progress and remaining:
                raise RuntimeError(f"Cyclic or unresolved parent reference in sections: {[s['section_code'] for s in remaining]}")
            pending_sections = remaining

        # Update total feeder lengths
        for f_code, f_id in feeder_map.items():
            tot_len = sum(s["length_km"] for s in grid["sections"] if s["feeder_code"] == f_code)
            feeder_obj = db.query(m.Feeder).filter_by(id=f_id).first()
            if feeder_obj:
                feeder_obj.total_length_km = round(tot_len, 2)
        db.flush()

        # 4. Transformers
        tx_map = {}
        for tx_data in grid["transformers"]:
            sec_id = section_map[tx_data["section_code"]]
            tx = m.Transformer(
                section_id=sec_id,
                transformer_code=tx_data["transformer_code"],
                rated_kva=tx_data["rated_kva"],
                current_load_kva=tx_data["current_load_kva"],
                load_percentage=tx_data["load_percentage"],
                primary_voltage_kv=tx_data["primary_voltage_kv"],
                secondary_voltage_v=tx_data["secondary_voltage_v"],
                phase=tx_data["phase"],
                latitude=tx_data["latitude"],
                longitude=tx_data["longitude"],
            )
            db.add(tx)
            db.flush()
            tx_map[tx.transformer_code] = tx.id

        # 5. Consumer Clusters
        for c_data in grid["consumer_clusters"]:
            tx_id = tx_map[c_data["transformer_code"]]
            clust = m.ConsumerCluster(
                transformer_id=tx_id,
                cluster_code=c_data["cluster_code"],
                consumer_count=c_data["consumer_count"],
                cluster_type=c_data["cluster_type"],
                peak_demand_kw=c_data["peak_demand_kw"],
                smart_meter_count=c_data["smart_meter_count"],
            )
            db.add(clust)

        # 6. Critical Loads
        for cl_data in grid["critical_loads"]:
            sec_id = section_map[cl_data["section_code"]]
            cl = m.CriticalLoad(
                section_id=sec_id,
                facility_name=cl_data["facility_name"],
                facility_type=cl_data["facility_type"],
                priority_tier=cl_data["priority_tier"],
                backup_generator_present=cl_data["backup_generator_present"],
                backup_run_hours=cl_data["backup_run_hours"],
                contact_number=cl_data["contact_number"],
            )
            db.add(cl)

        # 7. Tie-Switches (Normally Open)
        for tie_data in grid["tie_switches"]:
            from_id = section_map[tie_data["from_section"]]
            to_id = section_map[tie_data["to_section"]]
            conn = m.NetworkConnection(
                from_section_id=from_id,
                to_section_id=to_id,
                switch_code=tie_data["switch_code"],
                switch_type=tie_data["switch_type"],
                is_tie_switch=tie_data["is_tie_switch"],
                is_normally_open=tie_data["is_normally_open"],
                current_status=tie_data["status"],
                rated_current_a=tie_data["rated_current_a"],
                is_telecontrolled=tie_data["is_telecontrolled"],
            )
            db.add(conn)

        # 8. Assets
        for a_data in grid["assets"]:
            asset = m.AssetRecord(**a_data)
            db.add(asset)

        # 9. Seed the Hero Scenario on Feeder F4
        now = datetime.now(timezone.utc)
        f4_id = feeder_map["F4"]
        f4_s14_id = section_map["F4-S14"]
        f4_s12_id = section_map["F4-S12"]

        hero_incident = m.Incident(
            scenario_id="SCENARIO_HERO_F4",
            feeder_id=f4_id,
            root_cause_section_id=f4_s14_id,
            start_time=now - timedelta(minutes=14),
            status="INVESTIGATING",
            fault_type="LINE_TO_GROUND",
            estimated_customers_affected=380,
            correlation_window_start=now - timedelta(minutes=20),
            correlation_window_end=now - timedelta(minutes=5),
            description="Hero Scenario: Transient tree contact fault on branch F4-S14 serving District Water Pump.",
        )
        db.add(hero_incident)
        db.flush()

        # Hero topology-consistent candidates
        cand1 = m.FaultCandidate(
            incident_id=hero_incident.id,
            section_id=f4_s14_id,
            rank=1,
            raw_score=3.42,
            calibrated_probability=0.78,
            is_topology_consistent=True,
            candidate_designation="topology-consistent candidate",
            pruning_reason="Downstream boundary of zero-voltage telemetry from DT-14 (Water Pump)",
        )
        cand2 = m.FaultCandidate(
            incident_id=hero_incident.id,
            section_id=f4_s12_id,
            rank=2,
            raw_score=1.35,
            calibrated_probability=0.22,
            is_topology_consistent=True,
            candidate_designation="topology-consistent candidate",
            pruning_reason="Adjacent upstream branch section with partial voltage sag on DT-12",
        )
        db.add_all([cand1, cand2])
        db.flush()

        # Hero advisory restoration steps
        rest1 = m.RestorationPriority(
            incident_id=hero_incident.id,
            step_number=1,
            action_type="ISOLATE_SECTION",
            switch_code="AB-SW-F4-13",
            target_section_id=f4_s14_id,
            priority_score=10.0,
            critical_load_served=False,
            estimated_restored_kva=0.0,
            advisory_notes="Advisory: Open switch AB-SW-F4-13 to physically isolate faulted branch F4-S14.",
            safety_disclaimer=m.DEFAULT_SAFETY_DISCLAIMER,
            requires_engineer_approval=True,
            approval_status="PENDING_REVIEW",
        )
        rest2 = m.RestorationPriority(
            incident_id=hero_incident.id,
            step_number=2,
            action_type="CLOSE_TIE_SWITCH",
            switch_code="TIE-SW-F4-F3",
            target_section_id=f4_s14_id,
            priority_score=9.5,
            critical_load_served=True,
            estimated_restored_kva=310.0,
            advisory_notes="Advisory: Close tie switch TIE-SW-F4-F3 to restore power to District Water Pump via Sanjaynagar Feeder (F3).",
            safety_disclaimer=m.DEFAULT_SAFETY_DISCLAIMER,
            requires_engineer_approval=True,
            approval_status="PENDING_REVIEW",
        )
        db.add_all([rest1, rest2])

        db.commit()
        print(f"Database seeded successfully with {len(substation_map)} substations, {len(feeder_map)} feeders, {len(section_map)} sections, {len(tx_map)} transformers, and hero scenario.")
    except Exception as exc:
        db.rollback()
        print(f"Error seeding synthetic database: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database(reset=True)
