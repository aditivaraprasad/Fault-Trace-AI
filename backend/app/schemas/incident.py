from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from backend.app.models.incident import DEFAULT_SAFETY_DISCLAIMER


# --- Fault Candidate Schemas ---
class FaultCandidateBase(BaseModel):
    section_id: int
    rank: int = 1
    raw_score: float = Field(..., description="Raw model output score from XGBoost")
    calibrated_probability: float = Field(..., ge=0.0, le=1.0, description="Empirically calibrated probability")
    is_topology_consistent: bool = True
    candidate_designation: str = "topology-consistent candidate"
    pruning_reason: Optional[str] = None


class FaultCandidateCreate(FaultCandidateBase):
    incident_id: int


class FaultCandidateResponse(FaultCandidateBase):
    id: int
    incident_id: int
    section_code: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Restoration Priority Schemas ---
class RestorationPriorityBase(BaseModel):
    step_number: int = 1
    action_type: str = Field(..., description="ISOLATE_SECTION, CLOSE_TIE_SWITCH, SHED_LOAD, ENERGIZE_BACKFEED")
    switch_code: str
    target_section_id: Optional[int] = None
    priority_score: float = 1.0
    critical_load_served: bool = False
    estimated_restored_kva: float = 0.0
    advisory_notes: Optional[str] = None
    safety_disclaimer: str = DEFAULT_SAFETY_DISCLAIMER
    requires_engineer_approval: bool = True
    approval_status: str = "PENDING_REVIEW"


class RestorationPriorityCreate(RestorationPriorityBase):
    incident_id: int


class RestorationPriorityResponse(RestorationPriorityBase):
    id: int
    incident_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Incident Schemas ---
class IncidentBase(BaseModel):
    scenario_id: str = Field(..., max_length=50, description="Scenario ID partition key")
    feeder_id: int
    root_cause_section_id: Optional[int] = None
    actual_fault_section_id: Optional[int] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "INVESTIGATING"
    fault_type: str = "LINE_TO_GROUND"
    estimated_customers_affected: int = 0
    correlation_window_start: Optional[datetime] = None
    correlation_window_end: Optional[datetime] = None
    description: Optional[str] = None


class IncidentCreate(IncidentBase):
    pass


class IncidentUpdate(BaseModel):
    status: Optional[str] = None
    end_time: Optional[datetime] = None
    root_cause_section_id: Optional[int] = None
    actual_fault_section_id: Optional[int] = None
    estimated_customers_affected: Optional[int] = None
    description: Optional[str] = None


class IncidentResponse(IncidentBase):
    id: int
    feeder_code: Optional[str] = None
    feeder_name: Optional[str] = None
    actual_fault_section_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentDetailResponse(IncidentResponse):
    candidates: List[FaultCandidateResponse] = []
    restoration_steps: List[RestorationPriorityResponse] = []
    safety_advisory_notice: str = DEFAULT_SAFETY_DISCLAIMER

    model_config = ConfigDict(from_attributes=True)
