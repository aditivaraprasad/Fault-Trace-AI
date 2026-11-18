"""
Rolling 15-Minute Event Correlation Service.
Groups telemetry events, breaker trips, customer calls, and AMI logs around
protective relay operations into unified Incidents.
Handles duplicates and late-arriving telemetry packets.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

import backend.app.models as m

CORRELATION_WINDOW_MINUTES = 15


class EventCorrelatorService:
    """Orchestrates temporal and topological event correlation."""

    def __init__(self, db: Session):
        self.db = db

    def correlate_event(self, event: m.OutageEvent) -> m.Incident:
        """
        Correlates an incoming event into an existing incident or spawns a new one.
        Handles duplicates and late arrivals.
        """
        t = event.event_timestamp
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)

        # 1. Deduplication Check: reject if exact duplicate event exists within 5 seconds
        dup = (
            self.db.query(m.OutageEvent)
            .filter(
                m.OutageEvent.id != event.id,
                m.OutageEvent.event_type == event.event_type,
                m.OutageEvent.source == event.source,
                m.OutageEvent.section_id == event.section_id,
                m.OutageEvent.event_timestamp >= t - timedelta(seconds=5),
                m.OutageEvent.event_timestamp <= t + timedelta(seconds=5),
            )
            .first()
        )
        if dup and dup.incident_id:
            event.incident_id = dup.incident_id
            return dup.incident

        # 2. Determine Feeder ID from Section ID
        feeder_id = None
        if event.section_id:
            sec = self.db.query(m.FeederSection).filter_by(id=event.section_id).first()
            if sec:
                feeder_id = sec.feeder_id

        if not feeder_id:
            # Fallback to first active feeder
            first_feeder = self.db.query(m.Feeder).first()
            feeder_id = first_feeder.id if first_feeder else 1

        # 3. Search for open correlation window matching this feeder (Late Arrivals Handling)
        existing_incident = (
            self.db.query(m.Incident)
            .filter(
                m.Incident.feeder_id == feeder_id,
                m.Incident.correlation_window_start <= t,
                m.Incident.correlation_window_end >= t,
                m.Incident.status.in_(["INVESTIGATING", "CONFIRMED"]),
            )
            .order_by(m.Incident.start_time.desc())
            .first()
        )

        if existing_incident:
            # Late arrival attached to open incident
            event.incident_id = existing_incident.id
            if event.event_type in ["CUSTOMER_CALL", "AMI_LAST_GASP"]:
                existing_incident.estimated_customers_affected += 1
            existing_incident.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            return existing_incident

        # 4. If Breaker Trip or Recloser Lockout, spawn new Incident
        win_start = t - timedelta(minutes=5)
        win_end = t + timedelta(minutes=CORRELATION_WINDOW_MINUTES)

        scenario_code = f"INC-{t.strftime('%Y%m%d%H%M%S')}-F{feeder_id}"
        new_incident = m.Incident(
            scenario_id=scenario_code,
            feeder_id=feeder_id,
            root_cause_section_id=event.section_id,
            actual_fault_section_id=event.section_id,
            start_time=t,
            status="INVESTIGATING",
            fault_type="LINE_TO_GROUND",
            estimated_customers_affected=1 if event.event_type in ["CUSTOMER_CALL", "AMI_LAST_GASP"] else 0,
            correlation_window_start=win_start,
            correlation_window_end=win_end,
            description=f"Correlated incident triggered by {event.event_type} from {event.source} on Feeder {feeder_id}.",
        )
        self.db.add(new_incident)
        self.db.flush()

        event.incident_id = new_incident.id
        self.db.commit()
        self.db.refresh(new_incident)
        return new_incident

    def correlate_batch(self, events: List[m.OutageEvent]) -> List[m.Incident]:
        """Correlates a batch of events in chronological order."""
        # Sort chronologically
        events.sort(key=lambda e: e.event_timestamp)
        incidents = []
        for ev in events:
            inc = self.correlate_event(ev)
            if inc not in incidents:
                incidents.append(inc)
        return incidents
