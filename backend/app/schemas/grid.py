from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


# --- Substation Schemas ---
class SubstationBase(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50)
    latitude: float
    longitude: float
    voltage_kv: float = 66.0
    capacity_mva: float = 50.0
    division: str = "Bangalore North"
    subdivision: str = "Hebbal"


class SubstationCreate(SubstationBase):
    pass


class SubstationResponse(SubstationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Feeder Section Schemas ---
class FeederSectionBase(BaseModel):
    section_code: str = Field(..., max_length=50)
    feeder_id: int
    parent_section_id: Optional[int] = None
    length_km: float = 0.5
    resistance_ohm: float = 0.15
    reactance_ohm: float = 0.12
    rated_capacity_kva: float = 2000.0
    conductor_type: str = "ACSR_RABBIT"
    start_latitude: float
    start_longitude: float
    end_latitude: float
    end_longitude: float
    status: str = "ENERGIZED"


class FeederSectionCreate(FeederSectionBase):
    pass


class FeederSectionResponse(FeederSectionBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Feeder Schemas ---
class FeederBase(BaseModel):
    substation_id: int
    feeder_code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    voltage_kv: float = 11.0
    rated_current_a: float = 400.0
    nominal_capacity_mva: float = 7.5
    status: str = "ACTIVE"
    total_length_km: float = 0.0


class FeederCreate(FeederBase):
    pass


class FeederUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    rated_current_a: Optional[float] = None
    nominal_capacity_mva: Optional[float] = None
    total_length_km: Optional[float] = None


class FeederResponse(FeederBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeederDetailResponse(FeederResponse):
    substation_name: Optional[str] = None
    section_count: int = 0
    sections: List[FeederSectionResponse] = []

    model_config = ConfigDict(from_attributes=True)


# --- Transformer Schemas ---
class TransformerBase(BaseModel):
    section_id: int
    transformer_code: str
    rated_kva: float = 250.0
    current_load_kva: float = 120.0
    load_percentage: float = 48.0
    primary_voltage_kv: float = 11.0
    secondary_voltage_v: float = 415.0
    phase: int = 3
    latitude: float
    longitude: float


class TransformerCreate(TransformerBase):
    pass


class TransformerResponse(TransformerBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Asset Record Schemas ---
class AssetRecordBase(BaseModel):
    asset_type: str = Field(..., max_length=30)
    asset_identifier: str = Field(..., max_length=50)
    health_index: float = Field(..., ge=0.0, le=100.0)
    condition_rating: str = "GOOD"
    installation_date: Optional[datetime] = None
    last_maintenance_date: Optional[datetime] = None
    next_scheduled_maintenance: Optional[datetime] = None
    failure_history_count: int = 0
    operating_temperature_c: Optional[float] = None
    dga_status: Optional[str] = "NORMAL"
    notes: Optional[str] = None


class AssetRecordCreate(AssetRecordBase):
    pass


class AssetRecordUpdate(BaseModel):
    health_index: Optional[float] = Field(None, ge=0.0, le=100.0)
    condition_rating: Optional[str] = None
    last_maintenance_date: Optional[datetime] = None
    next_scheduled_maintenance: Optional[datetime] = None
    failure_history_count: Optional[int] = None
    operating_temperature_c: Optional[float] = None
    dga_status: Optional[str] = None
    notes: Optional[str] = None


class AssetRecordResponse(AssetRecordBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
