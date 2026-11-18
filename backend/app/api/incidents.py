from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
import backend.app.models as m
import backend.app.schemas as s
from backend.app.services.localization import FaultLocalizationService
from backend.app.services.asset_analysis import AssetAnalysisService
from backend.app.services.restoration import RestorationService, ADVISORY_DISCLAIMER
from backend.app.explainability.explainer import ShapExplainerService

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("", response_model=List[s.IncidentResponse])
def list_incidents(
    feeder_id: Optional[int] = Query(None, description="Filter by feeder ID"),
    scenario_id: Optional[str] = Query(None, description="Filter by scenario ID"),
    status: Optional[str] = Query(None, description="Filter by status (INVESTIGATING, CONFIRMED, RESOLVED)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retrieve outage and fault incident history."""
    query = db.query(m.Incident)
    if feeder_id is not None:
        query = query.filter(m.Incident.feeder_id == feeder_id)
    if scenario_id is not None:
        query = query.filter(m.Incident.scenario_id == scenario_id)
    if status is not None:
        query = query.filter(m.Incident.status == status.upper())

    incidents = query.order_by(m.Incident.start_time.desc()).offset(skip).limit(limit).all()
    results = []
    for inc in incidents:
        results.append(
            s.IncidentResponse(
                id=inc.id,
                scenario_id=inc.scenario_id,
                feeder_id=inc.feeder_id,
                feeder_code=inc.feeder.feeder_code if inc.feeder else None,
                feeder_name=inc.feeder.name if inc.feeder else None,
                root_cause_section_id=inc.root_cause_section_id,
                start_time=inc.start_time,
                end_time=inc.end_time,
                status=inc.status,
                fault_type=inc.fault_type,
                estimated_customers_affected=inc.estimated_customers_affected,
                correlation_window_start=inc.correlation_window_start,
                correlation_window_end=inc.correlation_window_end,
                description=inc.description,
                created_at=inc.created_at,
                updated_at=inc.updated_at,
            )
        )
    return results


@router.get("/{incident_id}", response_model=s.IncidentDetailResponse)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    """
    Retrieve comprehensive incident details, including:
    - Topology-consistent fault candidates (with raw scores and calibrated probabilities)
    - Advisory restoration sequence with required safety disclaimers.
    """
    inc = db.query(m.Incident).filter(m.Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found."
        )

    # Format candidates
    candidates = []
    for cand in inc.candidates:
        candidates.append(
            s.FaultCandidateResponse(
                id=cand.id,
                incident_id=cand.incident_id,
                section_id=cand.section_id,
                section_code=cand.section.section_code if cand.section else None,
                rank=cand.rank,
                raw_score=cand.raw_score,
                calibrated_probability=cand.calibrated_probability,
                is_topology_consistent=cand.is_topology_consistent,
                candidate_designation=cand.candidate_designation,
                pruning_reason=cand.pruning_reason,
                created_at=cand.created_at,
            )
        )

    # Format restoration steps
    restoration_steps = [
        s.RestorationPriorityResponse.model_validate(step) for step in inc.restoration_steps
    ]

    return s.IncidentDetailResponse(
        id=inc.id,
        scenario_id=inc.scenario_id,
        feeder_id=inc.feeder_id,
        feeder_code=inc.feeder.feeder_code if inc.feeder else None,
        feeder_name=inc.feeder.name if inc.feeder else None,
        root_cause_section_id=inc.root_cause_section_id,
        start_time=inc.start_time,
        end_time=inc.end_time,
        status=inc.status,
        fault_type=inc.fault_type,
        estimated_customers_affected=inc.estimated_customers_affected,
        correlation_window_start=inc.correlation_window_start,
        correlation_window_end=inc.correlation_window_end,
        description=inc.description,
        created_at=inc.created_at,
        updated_at=inc.updated_at,
        candidates=candidates,
        restoration_steps=restoration_steps,
        safety_advisory_notice=m.DEFAULT_SAFETY_DISCLAIMER,
    )


@router.post("", response_model=s.IncidentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(inc_in: s.IncidentCreate, db: Session = Depends(get_db)):
    """Log a new grid incident."""
    feeder = db.query(m.Feeder).filter(m.Feeder.id == inc_in.feeder_id).first()
    if not feeder:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Feeder ID {inc_in.feeder_id} does not exist."
        )

    incident = m.Incident(**inc_in.model_dump())
    db.add(incident)
    db.commit()
    db.refresh(incident)

    return s.IncidentResponse(
        id=incident.id,
        scenario_id=incident.scenario_id,
        feeder_id=incident.feeder_id,
        feeder_code=feeder.feeder_code,
        feeder_name=feeder.name,
        root_cause_section_id=incident.root_cause_section_id,
        start_time=incident.start_time,
        end_time=incident.end_time,
        status=incident.status,
        fault_type=incident.fault_type,
        estimated_customers_affected=incident.estimated_customers_affected,
        correlation_window_start=incident.correlation_window_start,
        correlation_window_end=incident.correlation_window_end,
        description=incident.description,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
    )


@router.patch("/{incident_id}", response_model=s.IncidentResponse)
def update_incident(incident_id: int, inc_update: s.IncidentUpdate, db: Session = Depends(get_db)):
    """Update incident status, resolution timestamp, or root-cause section."""
    incident = db.query(m.Incident).filter(m.Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found."
        )

    update_data = inc_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(incident, field, value)

    db.commit()
    db.refresh(incident)

    return s.IncidentResponse(
        id=incident.id,
        scenario_id=incident.scenario_id,
        feeder_id=incident.feeder_id,
        feeder_code=incident.feeder.feeder_code if incident.feeder else None,
        feeder_name=incident.feeder.name if incident.feeder else None,
        root_cause_section_id=incident.root_cause_section_id,
        start_time=incident.start_time,
        end_time=incident.end_time,
        status=incident.status,
        fault_type=incident.fault_type,
        estimated_customers_affected=incident.estimated_customers_affected,
        correlation_window_start=incident.correlation_window_start,
        correlation_window_end=incident.correlation_window_end,
        description=incident.description,
        created_at=incident.created_at,
        updated_at=incident.updated_at,
    )


# --- Phase 5 Localization, SHAP Explainability & Advisory Restoration Endpoints ---

@router.post("/{incident_id}/localize")
def localize_incident(incident_id: int, db: Session = Depends(get_db)):
    """
    Executes the full Fault Localization Pipeline:
    1. Gathers correlated telemetry from incident events.
    2. Runs NetworkX distribution graph engine to identify topology-consistent candidates.
    3. Builds 27-dimensional feature vectors.
    4. Evaluates XGBoost ranker and applies Isotonic probability calibration.
    5. Computes Tree SHAP attributions and engineering narratives.
    6. Formulates strictly safe advisory restoration plan with donor headroom verification.
    7. Persists candidates, model predictions, and restoration steps to database.
    """
    service = FaultLocalizationService(db=db)
    result = service.localize_incident(incident_id=incident_id)
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"],
        )
    return result


@router.get("/{incident_id}/explanation")
def get_incident_explanation(incident_id: int, db: Session = Depends(get_db)):
    """
    Returns Tree SHAP feature attributions, structured positive/negative evidence,
    and comparative ranking reasons for all candidates associated with this incident.
    Output labels: 'model score' vs 'calibrated probability (synthetic validation, ECE = measured value)'.
    """
    incident = db.query(m.Incident).filter_by(id=incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found.",
        )

    predictions = db.query(m.ModelPrediction).filter_by(incident_id=incident_id).all()
    if not predictions or not incident.candidates:
        # Run localization service on the fly to produce explanations
        service = FaultLocalizationService(db=db)
        loc_res = service.localize_incident(incident_id)
        if "error" in loc_res:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=loc_res["error"])
        return {
            "incident_id": incident.id,
            "scenario_id": incident.scenario_id,
            "feeder_code": loc_res.get("feeder_code"),
            "candidates": loc_res.get("candidates", []),
            "safety_advisory_notice": loc_res.get("safety_advisory_notice", ADVISORY_DISCLAIMER),
        }

    explainer = ShapExplainerService()
    sorted_candidates = sorted(incident.candidates, key=lambda c: c.rank)
    pred_map = {p.candidate_id: p for p in predictions}

    top_snapshot = None
    top_cand_code = "Rank #1"
    if sorted_candidates and sorted_candidates[0].id in pred_map:
        top_snapshot = pred_map[sorted_candidates[0].id].feature_snapshot
        if sorted_candidates[0].section:
            top_cand_code = sorted_candidates[0].section.section_code

    candidate_explanations = []
    for cand in sorted_candidates:
        pred = pred_map.get(cand.id)
        snapshot = pred.feature_snapshot if (pred and pred.feature_snapshot) else {}
        shap_attrs = pred.shap_values if (pred and pred.shap_values) else {}

        feat_pairs = []
        for k, v in shap_attrs.items():
            feat_pairs.append({
                "feature": k,
                "value": round(float(snapshot.get(k, 0.0)), 4),
                "shap_contribution": round(float(v), 5),
                "impact": "INCREASES_FAULT_RISK" if v > 0 else "DECREASES_FAULT_RISK",
            })
        feat_pairs.sort(key=lambda x: abs(x["shap_contribution"]), reverse=True)
        top_pos = [f for f in feat_pairs if f["shap_contribution"] > 0][:4]
        top_neg = [f for f in feat_pairs if f["shap_contribution"] < 0][:4]

        narrative = explainer._generate_narrative(snapshot, top_pos, top_neg)
        comp_reason = None
        if cand.rank > 1 and top_snapshot:
            comp_reason = explainer._compare_with_top(snapshot, top_snapshot, top_cand_code=top_cand_code)

        candidate_explanations.append({
            "rank": cand.rank,
            "section_id": cand.section_id,
            "section_code": cand.section.section_code if cand.section else None,
            "feeder_code": cand.section.feeder.feeder_code if (cand.section and cand.section.feeder) else None,
            "model_score": cand.raw_score,
            "calibrated_probability": cand.calibrated_probability,
            "probability_label": f"calibrated probability (synthetic validation, ECE = {explainer.measured_ece})",
            "candidate_designation": cand.candidate_designation or "topology-consistent candidate",
            "narrative": narrative,
            "comparative_rank_reason": comp_reason,
            "top_positive_features": top_pos,
            "top_negative_features": top_neg,
            "shap_attributions": shap_attrs,
        })

    return {
        "incident_id": incident.id,
        "scenario_id": incident.scenario_id,
        "feeder_code": incident.feeder.feeder_code if incident.feeder else None,
        "candidates": candidate_explanations,
        "safety_advisory_notice": ADVISORY_DISCLAIMER,
    }


@router.get("/{incident_id}/assets")
def get_incident_assets(
    incident_id: int,
    section_id: Optional[int] = Query(None, description="Optional target section ID. Defaults to top candidate."),
    db: Session = Depends(get_db),
):
    """
    Evaluates affected grid assets downstream of the candidate fault section:
    downstream distribution transformers, customer counts, critical facilities,
    outage severity tier, and estimated repair duration.
    """
    incident = db.query(m.Incident).filter_by(id=incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found.",
        )

    target_sec_id = section_id
    if target_sec_id is None:
        if incident.candidates:
            top_cand = sorted(incident.candidates, key=lambda c: c.rank)[0]
            target_sec_id = top_cand.section_id
        else:
            target_sec_id = incident.root_cause_section_id

    if target_sec_id is None:
        service = FaultLocalizationService(db=db)
        loc_res = service.localize_incident(incident_id)
        if "error" in loc_res or not loc_res.get("candidates"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to determine target section for asset analysis.",
            )
        target_sec_id = loc_res["candidates"][0]["section_id"]

    asset_service = AssetAnalysisService(db=db)
    impact = asset_service.analyze_impact(target_sec_id)
    if "error" in impact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=impact["error"])
    return impact


@router.get("/{incident_id}/restoration")
def get_incident_restoration(
    incident_id: int,
    section_id: Optional[int] = Query(None, description="Optional candidate section ID to isolate. Defaults to top candidate."),
    db: Session = Depends(get_db),
):
    """
    Generates an advisory restoration plan with transparent multi-criteria prioritization,
    candidate tie switch discovery, donor feeder capacity check, and strictly safe isolation steps.
    All plans require qualified engineer authorization.
    """
    incident = db.query(m.Incident).filter_by(id=incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found.",
        )

    target_sec_id = section_id
    if target_sec_id is None:
        if incident.candidates:
            top_cand = sorted(incident.candidates, key=lambda c: c.rank)[0]
            target_sec_id = top_cand.section_id
        else:
            target_sec_id = incident.root_cause_section_id

    if target_sec_id is None:
        service = FaultLocalizationService(db=db)
        loc_res = service.localize_incident(incident_id)
        if "error" in loc_res or not loc_res.get("candidates"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to determine candidate section for restoration planning.",
            )
        target_sec_id = loc_res["candidates"][0]["section_id"]

    restoration_service = RestorationService(db=db)
    plan = restoration_service.plan_restoration(target_sec_id)
    if "error" in plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=plan["error"])
    return plan
