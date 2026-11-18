"""
Pydantic schemas for Telemetry, Ingestion, Simulation, Weather, and Dashboard.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


# --- Outage Event Schemas ---
class OutageEventBase(BaseModel):
    section_id: Optional[int] = None
    event_timestamp: datetime
    event_type: str = Field(..., max_length=50, description="BREAKER_TRIP, RECLOSER_LOCKOUT, AMI_LAST_GASP, CUSTOMER_CALL, DMS_ALARM")
    source: str = Field(..., max_length=30, description="SCADA, RTU, AMI, CRM, DMS")
    raw_payload: Optional[Dict[str, Any]] = None


class OutageEventCreate(OutageEventBase):
    incident_id: Optional[int] = None


class OutageEventResponse(OutageEventBase):
    id: int
    incident_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Voltage Reading Schemas ---
class VoltageReadingBase(BaseModel):
    transformer_id: int
    timestamp: datetime
    voltage_v: float = Field(..., ge=0.0, le=500.0, description="Measured secondary phase voltage (Volts)")
    current_a: float = Field(..., ge=0.0, description="Current (Amperes)")
    active_power_kw: float = Field(..., ge=0.0, description="Active power (kW)")
    reactive_power_kvar: float = 0.0
    power_factor: float = Field(0.95, ge=-1.0, le=1.0)
    frequency_hz: float = Field(50.0, ge=40.0, le=60.0)


class VoltageReadingCreate(VoltageReadingBase):
    pass


class VoltageReadingResponse(VoltageReadingBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Weather Observation Schemas ---
class WeatherObservationBase(BaseModel):
    substation_id: Optional[int] = None
    region_name: str = "Bangalore North"
    timestamp: datetime
    source: str = Field("synthetic", description="'live' (Open-Meteo) or 'synthetic'")
    temperature_c: float = 26.5
    relative_humidity_pct: float = Field(65.0, ge=0.0, le=100.0)
    precipitation_mm: float = Field(0.0, ge=0.0)
    wind_speed_kmh: float = Field(12.0, ge=0.0)
    wind_gust_kmh: float = Field(18.0, ge=0.0)
    lightning_count: int = Field(0, ge=0)


class WeatherObservationCreate(WeatherObservationBase):
    pass


class WeatherObservationResponse(WeatherObservationBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Customer Complaint Schemas ---
class ComplaintCreate(BaseModel):
    cluster_id: Optional[int] = None
    transformer_id: Optional[int] = None
    section_id: Optional[int] = None
    timestamp: datetime
    complaint_type: str = "NO_POWER"
    caller_phone: Optional[str] = None
    remarks: Optional[str] = None


# --- CSV Ingestion Summary Response ---
class IngestionSummaryResponse(BaseModel):
    dataset_type: str
    rows_received: int
    rows_ingested: int
    rows_skipped: int = 0
    errors: List[str] = []
    message: str


# --- Scenario Simulation Schemas ---
class ScenarioSimulationRequest(BaseModel):
    scenario_type: str = Field("f4_hero", description="'f4_hero' or 'random'")
    feeder_code: Optional[str] = Field("F4", description="Feeder code if random or custom")
    complaint_count: Optional[int] = Field(None, description="Override complaint count")
    wind_speed_kmh: Optional[float] = Field(None, description="Override wind gust speed")
    noise_level: float = Field(0.05, ge=0.0, le=0.5, description="Telemetry noise ratio")


# --- Dashboard Stats Schemas ---
class DashboardStatsResponse(BaseModel):
    total_substations: int
    total_feeders: int
    total_sections: int
    total_transformers: int
    total_consumers: int
    active_incidents_count: int
    investigating_incidents_count: int
    resolved_incidents_count: int
    total_customers_affected: int
    critical_facilities_interrupted: int
    model_metrics: Dict[str, Any]
    latest_weather: WeatherObservationResponse
    outages_timeline: List[Dict[str, Any]] = []
    fault_categories: List[Dict[str, Any]] = []
