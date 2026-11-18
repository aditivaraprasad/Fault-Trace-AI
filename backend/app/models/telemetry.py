from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Index, Text, JSON
)
from sqlalchemy.orm import relationship
from backend.app.database.session import Base


class OutageEvent(Base):
    __tablename__ = "outage_events"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True)
    section_id = Column(Integer, ForeignKey("feeder_sections.id", ondelete="SET NULL"), nullable=True, index=True)
    event_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # BREAKER_TRIP, RECLOSER_LOCKOUT, AMI_LAST_GASP, CUSTOMER_CALL, DMS_ALARM
    source = Column(String(30), nullable=False)  # SCADA, RTU, AMI, CRM, DMS
    raw_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    incident = relationship("Incident", back_populates="outage_events")
    section = relationship("FeederSection")

    __table_args__ = (
        Index("idx_outage_time_type", "event_timestamp", "event_type"),
    )


class VoltageReading(Base):
    __tablename__ = "voltage_readings"

    id = Column(Integer, primary_key=True, index=True)
    transformer_id = Column(Integer, ForeignKey("transformers.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    voltage_v = Column(Float, nullable=False)  # e.g., 230V or line 415V
    current_a = Column(Float, nullable=False)
    active_power_kw = Column(Float, nullable=False)
    reactive_power_kvar = Column(Float, nullable=False, default=0.0)
    power_factor = Column(Float, nullable=False, default=0.95)
    frequency_hz = Column(Float, nullable=False, default=50.0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    transformer = relationship("Transformer", back_populates="voltage_readings")

    __table_args__ = (
        Index("idx_voltage_tx_time", "transformer_id", "timestamp"),
    )


class WeatherObservation(Base):
    __tablename__ = "weather_observations"

    id = Column(Integer, primary_key=True, index=True)
    substation_id = Column(Integer, ForeignKey("substations.id", ondelete="SET NULL"), nullable=True, index=True)
    region_name = Column(String(100), nullable=False, default="Bangalore North", index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    source = Column(String(30), nullable=False, default="synthetic")  # "live" (Open-Meteo) or "synthetic"
    temperature_c = Column(Float, nullable=False, default=26.5)
    relative_humidity_pct = Column(Float, nullable=False, default=65.0)
    precipitation_mm = Column(Float, nullable=False, default=0.0)
    wind_speed_kmh = Column(Float, nullable=False, default=12.0)
    wind_gust_kmh = Column(Float, nullable=False, default=18.0)
    lightning_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_weather_time_substation", "timestamp", "substation_id"),
    )
