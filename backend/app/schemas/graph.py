from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field
from backend.app.models.incident import DEFAULT_SAFETY_DISCLAIMER


# --- Request Schemas ---
class GraphLocalizationRequest(BaseModel):
    feeder_code: Optional[str] = Field(None, description="Optional target feeder code, e.g. 'F4'")
    observed_energized_section_codes: List[str] = Field(
        default_factory=list,
        description="Section codes confirmed energized (e.g. ['F4-S01', 'F4-S05', 'F4-S10'])"
    )
    observed_deenergized_section_codes: List[str] = Field(
        default_factory=list,
        description="Section codes confirmed de-energized (e.g. ['F4-S12', 'F4-S14'])"
    )
    incident_id: Optional[int] = Field(None, description="Optional incident ID to associate or load events from")


# --- Topology Response Schemas ---
class TopologyNode(BaseModel):
    id: str
    type: str  # substation, section, transformer
    label: str
    latitude: float
    longitude: float
    metadata: Dict[str, Any] = {}


class TopologyEdge(BaseModel):
    from_node: str
    to_node: str
    edge_type: str  # trunk, branch, transformer_drop, tie_switch
    is_tie_switch: bool = False
    status: str = "CLOSED"
    length_km: Optional[float] = None
    resistance_ohm: Optional[float] = None
    reactance_ohm: Optional[float] = None


class NetworkTopologyResponse(BaseModel):
    substations: List[Dict[str, Any]]
    feeders: List[Dict[str, Any]]
    sections: List[Dict[str, Any]]
    transformers: List[Dict[str, Any]]
    critical_loads: List[Dict[str, Any]]
    tie_switches: List[Dict[str, Any]]
    is_radial: bool
    total_sections: int
    total_transformers: int
    total_tie_switches: int


# --- Candidate Localization Response Schemas ---
class CandidateElectricalMetrics(BaseModel):
    cumulative_resistance_ohm: float
    cumulative_reactance_ohm: float
    distance_from_substation_km: float
    downstream_load_kva: float
    estimated_voltage_drop_v: float
    voltage_drop_percentage: float


class TopologyCandidate(BaseModel):
    rank: int
    section_id: int
    section_code: str
    feeder_code: str
    candidate_designation: str = "topology-consistent candidate"
    raw_score: float
    is_topology_consistent: bool = True
    evidence: str
    electrical_metrics: CandidateElectricalMetrics
    downstream_transformers_count: int
    downstream_transformers: List[str]
    downstream_critical_loads: List[Dict[str, Any]]
    start_coords: Tuple[float, float]
    end_coords: Tuple[float, float]


class PrunedCandidate(BaseModel):
    section_id: int
    section_code: str
    pruning_rule: str
    reason: str


class GraphLocalizationResponse(BaseModel):
    total_network_sections: int
    pruned_sections_count: int
    retained_candidates_count: int
    pruning_percentage: float
    last_observed_energized_sections: List[str]
    first_observed_deenergized_sections: List[str]
    topology_consistent_candidates: List[TopologyCandidate]
    pruned_candidates: List[PrunedCandidate]
    safety_advisory_notice: str = DEFAULT_SAFETY_DISCLAIMER
