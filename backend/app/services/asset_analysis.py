"""
Affected Asset and Grid Impact Analysis Service.
Evaluates downstream distribution transformers, consumer counts, critical facilities,
outage severity classifications, and estimated repair durations.
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
import backend.app.models as m
from backend.app.graph_engine.engine import DistributionGraphEngine


class AssetAnalysisService:
    """Computes comprehensive impact assessment for an identified fault candidate section."""

    def __init__(self, db: Session):
        self.db = db
        self.graph_engine = DistributionGraphEngine(db=db)

    def analyze_impact(self, candidate_section_id: int) -> Dict[str, Any]:
        """
        Calculates all impacted assets, consumers, critical loads, severity, and duration
        resulting from an outage at candidate_section_id.
        """
        sec_meta = self.graph_engine.section_metadata.get(candidate_section_id)
        if not sec_meta:
            return {"error": f"Section ID {candidate_section_id} not found."}

        # 1. Impacted Sections (Candidate + all downstream sections)
        downstream_sec_ids = [candidate_section_id] + self.graph_engine.get_downstream_sections(candidate_section_id)
        impacted_sections = [
            {
                "section_id": s_id,
                "section_code": self.graph_engine.section_metadata[s_id]["section_code"],
                "length_km": self.graph_engine.section_metadata[s_id]["length_km"],
                "conductor_type": self.graph_engine.section_metadata[s_id]["conductor_type"],
            }
            for s_id in downstream_sec_ids
            if s_id in self.graph_engine.section_metadata
        ]

        # 2. Downstream Transformers & Load
        downstream_dts = self.graph_engine.get_downstream_transformers(candidate_section_id)
        total_interrupted_kva = sum(dt["current_load_kva"] for dt in downstream_dts)
        total_installed_kva = sum(dt["rated_kva"] for dt in downstream_dts)

        # 3. Estimated Consumers Affected
        tx_ids = [dt["id"] for dt in downstream_dts]
        clusters = self.db.query(m.ConsumerCluster).filter(m.ConsumerCluster.transformer_id.in_(tx_ids)).all()
        total_consumers = sum(c.consumer_count for c in clusters)
        total_smart_meters = sum(c.smart_meter_count for c in clusters)

        # 4. Critical Facilities Impacted
        critical_loads = self.graph_engine.get_downstream_critical_loads(candidate_section_id)
        has_tier1 = any(cl["priority_tier"] == 1 for cl in critical_loads)
        has_tier2 = any(cl["priority_tier"] == 2 for cl in critical_loads)

        # 5. Severity Level Calculation
        if has_tier1 or total_consumers >= 400 or total_interrupted_kva >= 750.0:
            severity = "CRITICAL"
            severity_description = "Life-critical or major public service facility de-energized, or high consumer population outage."
        elif has_tier2 or total_consumers >= 150 or total_interrupted_kva >= 350.0:
            severity = "HIGH"
            severity_description = "Essential infrastructure or substantial commercial demand interrupted."
        elif total_consumers >= 50:
            severity = "MEDIUM"
            severity_description = "Moderate localized feeder branch interruption."
        else:
            severity = "LOW"
            severity_description = "Minor lateral line interruption with minimal consumer impact."

        # 6. Estimated Restoration / Repair Duration (Minutes)
        # Overhead clearing vs underground cable vs stormy conditions
        is_cable = any("CABLE" in s["conductor_type"] for s in impacted_sections)
        base_repair_mins = 120 if is_cable else 60
        # If severe critical load, estimated dispatched crew response priority reduces wait time
        est_duration_mins = base_repair_mins + min(len(impacted_sections) * 10, 60)

        return {
            "candidate_section_id": candidate_section_id,
            "candidate_section_code": sec_meta["section_code"],
            "feeder_code": sec_meta["feeder_code"],
            "severity_level": severity,
            "severity_description": severity_description,
            "estimated_duration_minutes": est_duration_mins,
            "total_impacted_sections_count": len(impacted_sections),
            "impacted_sections": impacted_sections,
            "total_downstream_dts_count": len(downstream_dts),
            "downstream_transformers": downstream_dts,
            "total_interrupted_kva": round(total_interrupted_kva, 1),
            "total_installed_capacity_kva": round(total_installed_kva, 1),
            "estimated_consumers_affected": total_consumers,
            "smart_meters_offline": total_smart_meters,
            "critical_facilities_count": len(critical_loads),
            "critical_facilities": critical_loads,
        }
