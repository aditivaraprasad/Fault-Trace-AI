from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
import backend.app.models as m
from backend.app.schemas.graph import (
    NetworkTopologyResponse,
    GraphLocalizationRequest,
    GraphLocalizationResponse,
)
from backend.app.graph_engine.engine import DistributionGraphEngine

router = APIRouter(tags=["Network & Graph Engine"])


@router.get("/network/topology", response_model=NetworkTopologyResponse)
def get_network_topology(
    feeder_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Returns the comprehensive distribution network topology from the shared database.
    Used for GIS map visualizers and graph connectivity validation.
    """
    engine = DistributionGraphEngine(db=db, feeder_id=feeder_id)

    # 1. Substations
    subs = db.query(m.Substation).all()
    substations_data = [
        {
            "id": s.id,
            "name": s.name,
            "code": s.code,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "voltage_kv": s.voltage_kv,
            "capacity_mva": s.capacity_mva,
            "division": s.division,
        }
        for s in subs
    ]

    # 2. Feeders (always return all feeders for UI navigation and filtering)
    all_feeders = db.query(m.Feeder).all()
    feeders_data = [
        {
            "id": f.id,
            "substation_id": f.substation_id,
            "feeder_code": f.feeder_code,
            "name": f.name,
            "voltage_kv": f.voltage_kv,
            "status": f.status,
            "total_length_km": f.total_length_km,
        }
        for f in all_feeders
    ]

    # 3. Sections
    sec_q = db.query(m.FeederSection)
    if feeder_id:
        sec_q = sec_q.filter(m.FeederSection.feeder_id == feeder_id)
    sections = sec_q.all()
    sections_data = [
        {
            "id": s.id,
            "feeder_id": s.feeder_id,
            "parent_section_id": s.parent_section_id,
            "section_code": s.section_code,
            "length_km": s.length_km,
            "resistance_ohm": s.resistance_ohm,
            "reactance_ohm": s.reactance_ohm,
            "rated_capacity_kva": s.rated_capacity_kva,
            "conductor_type": s.conductor_type,
            "status": s.status,
            "start_latitude": s.start_latitude,
            "start_longitude": s.start_longitude,
            "end_latitude": s.end_latitude,
            "end_longitude": s.end_longitude,
            "coordinates": [[s.start_latitude, s.start_longitude], [s.end_latitude, s.end_longitude]],
        }
        for s in sections
    ]

    # 4. Transformers
    tx_q = db.query(m.Transformer)
    if feeder_id:
        tx_q = tx_q.join(m.FeederSection).filter(m.FeederSection.feeder_id == feeder_id)
    transformers = tx_q.all()
    transformers_data = [
        {
            "id": t.id,
            "section_id": t.section_id,
            "transformer_code": t.transformer_code,
            "rated_kva": t.rated_kva,
            "current_load_kva": t.current_load_kva,
            "load_percentage": t.load_percentage,
            "latitude": t.latitude,
            "longitude": t.longitude,
        }
        for t in transformers
    ]

    # 5. Critical Loads
    cl_q = db.query(m.CriticalLoad)
    if feeder_id:
        cl_q = cl_q.join(m.FeederSection).filter(m.FeederSection.feeder_id == feeder_id)
    critical_loads = cl_q.all()
    critical_loads_data = [
        {
            "id": c.id,
            "section_id": c.section_id,
            "facility_name": c.facility_name,
            "facility_type": c.facility_type,
            "priority_tier": c.priority_tier,
            "backup_generator_present": c.backup_generator_present,
            "backup_run_hours": c.backup_run_hours,
        }
        for c in critical_loads
    ]

    # 6. Tie Switches
    ties = db.query(m.NetworkConnection).all()
    tie_switches_data = [
        {
            "id": t.id,
            "from_section_id": t.from_section_id,
            "to_section_id": t.to_section_id,
            "switch_code": t.switch_code,
            "switch_type": t.switch_type,
            "is_tie_switch": t.is_tie_switch,
            "is_normally_open": t.is_normally_open,
            "current_status": t.current_status,
            "rated_current_a": t.rated_current_a,
        }
        for t in ties
    ]

    return NetworkTopologyResponse(
        substations=substations_data,
        feeders=feeders_data,
        sections=sections_data,
        transformers=transformers_data,
        critical_loads=critical_loads_data,
        tie_switches=tie_switches_data,
        is_radial=engine.is_radial(),
        total_sections=len(sections_data),
        total_transformers=len(transformers_data),
        total_tie_switches=len(tie_switches_data),
    )


@router.post("/localize/graph", response_model=GraphLocalizationResponse)
def localize_fault_graph(
    req: GraphLocalizationRequest,
    db: Session = Depends(get_db)
):
    """
    Graph Engine fault localization & candidate pruning.
    Traces the radial tree between the last observed-energized and first observed-de-energized boundaries.
    Eliminates inconsistent candidate sections and returns topology-consistent candidates with evidence.
    """
    # 1. Lookup section IDs from section codes if provided
    energized_ids: set[int] = set()
    deenergized_ids: set[int] = set()

    if req.observed_energized_section_codes:
        rows = db.query(m.FeederSection.id).filter(m.FeederSection.section_code.in_(req.observed_energized_section_codes)).all()
        energized_ids.update(r[0] for r in rows)

    if req.observed_deenergized_section_codes:
        rows = db.query(m.FeederSection.id).filter(m.FeederSection.section_code.in_(req.observed_deenergized_section_codes)).all()
        deenergized_ids.update(r[0] for r in rows)

    # If an incident ID was supplied without explicit section sets, look up from incident and downstream events
    if req.incident_id and not (energized_ids or deenergized_ids):
        inc = db.query(m.Incident).filter_by(id=req.incident_id).first()
        if not inc:
            raise HTTPException(status_code=404, detail=f"Incident ID {req.incident_id} not found.")

        # Default hero scenario behavior if hero incident
        if inc.root_cause_section_id:
            # Root cause section and its immediate children are de-energized
            engine_temp = DistributionGraphEngine(db=db, feeder_id=inc.feeder_id)
            deenergized_ids.add(inc.root_cause_section_id)
            deenergized_ids.update(engine_temp.get_downstream_sections(inc.root_cause_section_id))
            # Upstream ancestors of root cause are energized
            ancestors = engine_temp.get_upstream_sections(inc.root_cause_section_id)
            if ancestors:
                energized_ids.update(ancestors[1:])  # e.g., root to parent

    # 2. Run graph engine
    feeder_id_filter = None
    if req.feeder_code:
        f_obj = db.query(m.Feeder).filter_by(feeder_code=req.feeder_code).first()
        if f_obj:
            feeder_id_filter = f_obj.id

    graph_engine = DistributionGraphEngine(db=db, feeder_id=feeder_id_filter)
    result = graph_engine.prune_candidates(
        observed_energized_section_ids=energized_ids,
        observed_deenergized_section_ids=deenergized_ids,
    )

    return GraphLocalizationResponse(
        total_network_sections=result["total_network_sections"],
        pruned_sections_count=result["pruned_sections_count"],
        retained_candidates_count=result["retained_candidates_count"],
        pruning_percentage=result["pruning_percentage"],
        last_observed_energized_sections=result["last_observed_energized_sections"],
        first_observed_deenergized_sections=result["first_observed_deenergized_sections"],
        topology_consistent_candidates=result["topology_consistent_candidates"],
        pruned_candidates=result["pruned_candidates"],
        safety_advisory_notice=m.DEFAULT_SAFETY_DISCLAIMER,
    )
