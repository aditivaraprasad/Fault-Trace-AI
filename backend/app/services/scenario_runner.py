"""
Scenario Simulation and Live Ingestion Runner for FAULTTRACE AI.
Implements:
- Preset 'f4_hero': Feeder F4 trip, 142 customer complaints, 48 km/h gusts, downstream DT collapse,
  true simulated fault in F4-S14 (District Water Pump on DT-14 downstream).
- Preset 'random': Randomized feeder & section fault simulation.
Flow:
Create Incident -> Ingest Events -> Correlate (15-min) -> Graph Candidates ->
ML Rank -> Explain (SHAP) -> Assets Analysis -> Advisory Restoration ->
Persist in DB -> Return Complete Result.
"""

import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

import backend.app.models as m
from backend.app.services.correlator import EventCorrelatorService
from backend.app.services.weather import WeatherService
from backend.app.services.localization import FaultLocalizationService
from backend.app.graph_engine.engine import DistributionGraphEngine


class ScenarioSimulationRunner:
    """Orchestrates end-to-end incident scenario simulation and pipeline execution."""

    def __init__(self, db: Session):
        self.db = db
        self.correlator = EventCorrelatorService(db=db)
        self.weather_service = WeatherService(db=db)
        self.localization_service = FaultLocalizationService(db=db)
        self.graph_engine = DistributionGraphEngine(db=db)

    def run_scenario(
        self,
        scenario_type: str = "f4_hero",
        feeder_code: Optional[str] = "F4",
        complaint_count: Optional[int] = None,
        wind_speed_kmh: Optional[float] = None,
        noise_level: float = 0.05,
    ) -> Dict[str, Any]:
        """Executes complete scenario flow and returns comprehensive diagnosis and restoration result."""
        now = datetime.now(timezone.utc)

        # 1. Resolve Target Feeder & Actual Fault Section
        if scenario_type.lower() == "f4_hero":
            feeder = self.db.query(m.Feeder).filter_by(feeder_code="F4").first()
            if not feeder:
                feeder = self.db.query(m.Feeder).first()
            actual_sec = self.db.query(m.FeederSection).filter_by(section_code="F4-S14").first()
            if not actual_sec:
                actual_sec = self.db.query(m.FeederSection).filter_by(feeder_id=feeder.id).first()
            n_complaints = complaint_count if complaint_count is not None else 142
            gust_speed = wind_speed_kmh if wind_speed_kmh is not None else 48.0
            precip = 14.5
            scenario_id_code = f"HERO-F4-{now.strftime('%Y%m%d%H%M%S')}"
            desc = (
                f"Hero Simulation: Feeder F4 high-impedance ground fault on section {actual_sec.section_code} "
                f"under heavy monsoon gusts ({gust_speed} km/h). Downstream District Water Pump interrupted."
            )
        else:
            # Random scenario
            if feeder_code:
                feeder = self.db.query(m.Feeder).filter_by(feeder_code=feeder_code).first()
            else:
                feeders = self.db.query(m.Feeder).all()
                feeder = random.choice(feeders) if feeders else None

            if not feeder:
                raise ValueError("No feeder found for simulation.")

            sections = self.db.query(m.FeederSection).filter_by(feeder_id=feeder.id).all()
            actual_sec = random.choice(sections) if sections else None
            if not actual_sec:
                raise ValueError(f"No sections available on Feeder {feeder.feeder_code}.")

            n_complaints = complaint_count if complaint_count is not None else random.randint(45, 120)
            gust_speed = wind_speed_kmh if wind_speed_kmh is not None else random.uniform(25.0, 55.0)
            precip = random.uniform(2.0, 20.0)
            scenario_id_code = f"SIM-{feeder.feeder_code}-{actual_sec.section_code}-{now.strftime('%Y%m%d%H%M%S')}"
            desc = f"Simulated fault on Feeder {feeder.feeder_code} Section {actual_sec.section_code}."

        # 2. Weather Ingestion / Observation
        sub_id = feeder.substation_id
        weather_obs = m.WeatherObservation(
            substation_id=sub_id,
            region_name="Bangalore North",
            timestamp=now,
            source="synthetic",
            temperature_c=26.4,
            relative_humidity_pct=82.0,
            precipitation_mm=round(precip, 1),
            wind_speed_kmh=round(gust_speed * 0.6, 1),
            wind_gust_kmh=round(gust_speed, 1),
            lightning_count=3 if gust_speed > 40 else 0,
        )
        self.db.add(weather_obs)
        self.db.flush()

        # 3. Create Incident with Ground-Truth Actual Fault Section
        win_start = now - timedelta(minutes=5)
        win_end = now + timedelta(minutes=15)

        incident = m.Incident(
            scenario_id=scenario_id_code,
            feeder_id=feeder.id,
            root_cause_section_id=actual_sec.id,
            actual_fault_section_id=actual_sec.id,
            start_time=now,
            status="INVESTIGATING",
            fault_type="LINE_TO_GROUND",
            estimated_customers_affected=n_complaints * 3,
            correlation_window_start=win_start,
            correlation_window_end=win_end,
            description=desc,
        )
        self.db.add(incident)
        self.db.flush()

        # 4. Ingest Correlated Events into Outage Events
        # Upstream healthy trunk telemetry (observed energized)
        upstream_sec_ids = self.graph_engine.get_upstream_sections(actual_sec.id)
        for u_sec_id in upstream_sec_ids:
            healthy_ev = m.OutageEvent(
                incident_id=incident.id,
                section_id=u_sec_id,
                event_timestamp=now - timedelta(seconds=5),
                event_type="NORMAL_TELEMETRY",
                source="SCADA",
                raw_payload={"status": "ENERGIZED", "voltage_kv": 11.0},
            )
            self.db.add(healthy_ev)

        # Primary protective relay trip on faulted section
        primary_trip = m.OutageEvent(
            incident_id=incident.id,
            section_id=actual_sec.id,
            event_timestamp=now,
            event_type="BREAKER_TRIP",
            source="SCADA",
            raw_payload={"phase": "RYB", "current_ka": 3.8, "target_feeder": feeder.feeder_code},
        )
        self.db.add(primary_trip)

        # Downstream section telemetry collapse
        downstream_sec_ids = self.graph_engine.get_downstream_sections(actual_sec.id)
        for d_sec_id in downstream_sec_ids:
            trip_ev = m.OutageEvent(
                incident_id=incident.id,
                section_id=d_sec_id,
                event_timestamp=now + timedelta(seconds=random.randint(1, 4)),
                event_type="RECLOSER_LOCKOUT",
                source="RTU",
                raw_payload={"status": "DE_ENERGIZED"},
            )
            self.db.add(trip_ev)

        # Ingest Voltage collapses on downstream transformers
        downstream_dts = self.graph_engine.get_downstream_transformers(actual_sec.id)
        for dt_dict in downstream_dts:
            reading = m.VoltageReading(
                transformer_id=dt_dict["id"],
                timestamp=now + timedelta(seconds=2),
                voltage_v=0.0,
                current_a=0.0,
                active_power_kw=0.0,
                power_factor=0.0,
                frequency_hz=50.0,
            )
            self.db.add(reading)

            ami_gasp = m.OutageEvent(
                incident_id=incident.id,
                section_id=dt_dict["section_id"],
                event_timestamp=now + timedelta(seconds=random.randint(2, 6)),
                event_type="AMI_LAST_GASP",
                source="AMI",
                raw_payload={"transformer_code": dt_dict["transformer_code"], "voltage_drop": 230.0},
            )
            self.db.add(ami_gasp)

        # Ingest representative Customer Complaints
        complaint_samples = min(n_complaints, 10)
        for c_idx in range(complaint_samples):
            comp_ev = m.OutageEvent(
                incident_id=incident.id,
                section_id=actual_sec.id,
                event_timestamp=now + timedelta(minutes=random.uniform(0.5, 4.0)),
                event_type="CUSTOMER_CALL",
                source="CRM",
                raw_payload={"complaint_id": f"CRM-{now.strftime('%H%M%S')}-{c_idx+1}", "type": "NO_POWER"},
            )
            self.db.add(comp_ev)

        self.db.commit()

        # 5. Execute Full Localization Pipeline (Graph -> ML -> SHAP -> Restoration)
        pipeline_output = self.localization_service.localize_incident(incident.id)

        # 6. Format Return Result
        return {
            "simulation_scenario_id": scenario_id_code,
            "scenario_type": scenario_type,
            "incident_id": incident.id,
            "feeder_code": feeder.feeder_code,
            "feeder_name": feeder.name,
            "actual_fault_section": {
                "section_id": actual_sec.id,
                "section_code": actual_sec.section_code,
                "length_km": actual_sec.length_km,
                "conductor_type": actual_sec.conductor_type,
            },
            "weather_observation": {
                "source": weather_obs.source,
                "temperature_c": weather_obs.temperature_c,
                "precipitation_mm": weather_obs.precipitation_mm,
                "wind_gust_kmh": weather_obs.wind_gust_kmh,
            },
            "events_simulated_count": 1 + len(downstream_sec_ids) + len(downstream_dts) + complaint_samples,
            "complaints_logged_count": n_complaints,
            "localization_result": pipeline_output,
        }
