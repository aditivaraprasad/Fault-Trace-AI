from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Index, Text, Enum
)
from sqlalchemy.orm import relationship
from backend.app.database.session import Base


class Substation(Base):
    __tablename__ = "substations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    voltage_kv = Column(Float, nullable=False, default=66.0)  # e.g., 66kV or 220kV
    capacity_mva = Column(Float, nullable=False, default=50.0)
    division = Column(String(100), nullable=False, default="Bangalore North")
    subdivision = Column(String(100), nullable=False, default="Hebbal")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    feeders = relationship("Feeder", back_populates="substation", cascade="all, delete-orphan")


class Feeder(Base):
    __tablename__ = "feeders"

    id = Column(Integer, primary_key=True, index=True)
    substation_id = Column(Integer, ForeignKey("substations.id", ondelete="CASCADE"), nullable=False, index=True)
    feeder_code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    voltage_kv = Column(Float, nullable=False, default=11.0)  # 11kV distribution
    rated_current_a = Column(Float, nullable=False, default=400.0)
    nominal_capacity_mva = Column(Float, nullable=False, default=7.5)
    status = Column(String(20), nullable=False, default="ACTIVE")  # ACTIVE, TRIPPED, MAINTENANCE, DE-ENERGIZED
    total_length_km = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    substation = relationship("Substation", back_populates="feeders")
    sections = relationship("FeederSection", back_populates="feeder", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="feeder")


class FeederSection(Base):
    __tablename__ = "feeder_sections"

    id = Column(Integer, primary_key=True, index=True)
    feeder_id = Column(Integer, ForeignKey("feeders.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_section_id = Column(Integer, ForeignKey("feeder_sections.id", ondelete="SET NULL"), nullable=True, index=True)
    section_code = Column(String(50), nullable=False, unique=True, index=True)
    length_km = Column(Float, nullable=False, default=0.5)
    resistance_ohm = Column(Float, nullable=False, default=0.15)
    reactance_ohm = Column(Float, nullable=False, default=0.12)
    rated_capacity_kva = Column(Float, nullable=False, default=2000.0)
    conductor_type = Column(String(50), nullable=False, default="ACSR_RABBIT")
    start_latitude = Column(Float, nullable=False)
    start_longitude = Column(Float, nullable=False)
    end_latitude = Column(Float, nullable=False)
    end_longitude = Column(Float, nullable=False)
    status = Column(String(20), nullable=False, default="ENERGIZED")  # ENERGIZED, ISOLATED, FAULTED
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Hierarchical tree relationships
    feeder = relationship("Feeder", back_populates="sections")
    parent_section = relationship("FeederSection", remote_side=[id], backref="child_sections")
    transformers = relationship("Transformer", back_populates="section", cascade="all, delete-orphan")
    critical_loads = relationship("CriticalLoad", back_populates="section")

    __table_args__ = (
        Index("idx_section_feeder_parent", "feeder_id", "parent_section_id"),
    )


class Transformer(Base):
    __tablename__ = "transformers"

    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("feeder_sections.id", ondelete="CASCADE"), nullable=False, index=True)
    transformer_code = Column(String(50), nullable=False, unique=True, index=True)
    rated_kva = Column(Float, nullable=False, default=250.0)  # e.g., 100, 250, 500 kVA DTC
    current_load_kva = Column(Float, nullable=False, default=120.0)
    load_percentage = Column(Float, nullable=False, default=48.0)
    primary_voltage_kv = Column(Float, nullable=False, default=11.0)
    secondary_voltage_v = Column(Float, nullable=False, default=415.0)
    phase = Column(Integer, nullable=False, default=3)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    section = relationship("FeederSection", back_populates="transformers")
    consumer_clusters = relationship("ConsumerCluster", back_populates="transformer", cascade="all, delete-orphan")
    voltage_readings = relationship("VoltageReading", back_populates="transformer")


class ConsumerCluster(Base):
    __tablename__ = "consumer_clusters"

    id = Column(Integer, primary_key=True, index=True)
    transformer_id = Column(Integer, ForeignKey("transformers.id", ondelete="CASCADE"), nullable=False, index=True)
    cluster_code = Column(String(50), nullable=False, unique=True, index=True)
    consumer_count = Column(Integer, nullable=False, default=50)
    cluster_type = Column(String(30), nullable=False, default="RESIDENTIAL")  # RESIDENTIAL, COMMERCIAL, INDUSTRIAL, MIXED
    peak_demand_kw = Column(Float, nullable=False, default=150.0)
    smart_meter_count = Column(Integer, nullable=False, default=45)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    transformer = relationship("Transformer", back_populates="consumer_clusters")


class NetworkConnection(Base):
    __tablename__ = "network_connections"

    id = Column(Integer, primary_key=True, index=True)
    from_section_id = Column(Integer, ForeignKey("feeder_sections.id", ondelete="CASCADE"), nullable=False, index=True)
    to_section_id = Column(Integer, ForeignKey("feeder_sections.id", ondelete="CASCADE"), nullable=False, index=True)
    switch_code = Column(String(50), nullable=False, unique=True, index=True)
    switch_type = Column(String(30), nullable=False, default="AIR_BREAK_SWITCH")  # CIRCUIT_BREAKER, AUTO_RECLOSER, LOAD_BREAK_SWITCH, AIR_BREAK_SWITCH, TIE_SWITCH
    is_tie_switch = Column(Boolean, nullable=False, default=False, index=True)
    is_normally_open = Column(Boolean, nullable=False, default=False)
    current_status = Column(String(10), nullable=False, default="CLOSED")  # OPEN, CLOSED
    rated_current_a = Column(Float, nullable=False, default=400.0)
    is_telecontrolled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    from_section = relationship("FeederSection", foreign_keys=[from_section_id])
    to_section = relationship("FeederSection", foreign_keys=[to_section_id])

    __table_args__ = (
        Index("idx_net_conn_from_to", "from_section_id", "to_section_id"),
    )


class CriticalLoad(Base):
    __tablename__ = "critical_loads"

    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("feeder_sections.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_name = Column(String(120), nullable=False, index=True)
    facility_type = Column(String(50), nullable=False)  # HOSPITAL, WATER_PUMPING, METRO_RAIL, DEFENSE, GOVERNMENT, DATA_CENTER
    priority_tier = Column(Integer, nullable=False, default=1)  # 1 = highest / life-critical, 2 = essential infrastructure, 3 = high commercial
    backup_generator_present = Column(Boolean, nullable=False, default=True)
    backup_run_hours = Column(Float, nullable=False, default=8.0)
    contact_number = Column(String(30), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    section = relationship("FeederSection", back_populates="critical_loads")


class AssetRecord(Base):
    __tablename__ = "asset_records"

    id = Column(Integer, primary_key=True, index=True)
    asset_type = Column(String(30), nullable=False, index=True)  # TRANSFORMER, BREAKER, SECTION, RECLOSER, CABLE
    asset_identifier = Column(String(50), nullable=False, index=True)  # Reference to code or asset ID
    health_index = Column(Float, nullable=False, default=85.0)  # 0 to 100
    condition_rating = Column(String(20), nullable=False, default="GOOD")  # EXCELLENT, GOOD, FAIR, POOR, CRITICAL
    installation_date = Column(DateTime(timezone=True), nullable=True)
    last_maintenance_date = Column(DateTime(timezone=True), nullable=True)
    next_scheduled_maintenance = Column(DateTime(timezone=True), nullable=True)
    failure_history_count = Column(Integer, nullable=False, default=0)
    operating_temperature_c = Column(Float, nullable=True)
    dga_status = Column(String(30), nullable=True, default="NORMAL")  # Dissolved Gas Analysis for transformers: NORMAL, CAUTION, WARNING
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_asset_type_ident", "asset_type", "asset_identifier"),
    )
