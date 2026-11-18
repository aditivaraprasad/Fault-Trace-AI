"""
Synthetic Scenario Simulator for FAULTTRACE AI.
Generates multi-feeder fault scenarios with realistic telemetry, noisy voltage readings,
stochastic customer complaints, weather correlations, asset conditions, and partial observations.
Extracts candidate feature vectors for XGBoost training and evaluation.
"""

import random
import math
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from backend.app.database.session import SessionLocal
import backend.app.models as m
from backend.app.graph_engine.engine import DistributionGraphEngine


class GridScenarioSimulator:
    """
    Simulates stochastic distribution fault scenarios on the synthetic Bengaluru grid.
    All data is synthetic. Never hardcodes predictions.
    """

    def __init__(self, db: Session, seed: int = 42):
        self.db = db
        self.rng = random.Random(seed)
        self.np_rng = np.random.RandomState(seed)
        self.graph_engine = DistributionGraphEngine(db=db)
        self.all_sections = list(self.graph_engine.section_metadata.values())
        self.all_feeders = {s["feeder_id"] for s in self.all_sections}

        # Cache asset records by identifier
        asset_rows = self.db.query(m.AssetRecord).all()
        self.asset_cache = {a.asset_identifier: a for a in asset_rows}

    def generate_single_scenario(self, scenario_id: str) -> Dict[str, Any]:
        """
        Generates a single fault event scenario with realistic telemetry and physical noise.
        """
        # 1. Environmental factors (Time of day & Weather)
        hour = self.rng.randint(0, 23)
        is_peak_hour = (9 <= hour <= 12) or (18 <= hour <= 22)

        # Weather: dry calm vs stormy monsoon conditions
        is_stormy = self.rng.random() < 0.35
        if is_stormy:
            wind_speed = round(self.rng.uniform(30.0, 75.0), 1)  # high winds cause tree branches to hit lines
            precipitation = round(self.rng.uniform(10.0, 45.0), 1)
            lightning_count = self.rng.randint(2, 20)
            ambient_temp = round(self.rng.uniform(21.0, 26.0), 1)
        else:
            wind_speed = round(self.rng.uniform(4.0, 25.0), 1)
            precipitation = round(self.rng.uniform(0.0, 2.0), 1)
            lightning_count = 0
            ambient_temp = round(self.rng.uniform(24.0, 35.0), 1)

        # 2. Pick target feeder and true fault section
        # Probability of fault weighted by weather, asset condition, and section length
        section_weights = []
        for s in self.all_sections:
            sec_len = s["length_km"]
            asset = self.asset_cache.get(s["section_code"])
            health = asset.health_index if asset else 85.0
            fail_count = asset.failure_history_count if asset else 0

            # Weight formula based on physical vulnerability
            w = sec_len * (1.0 + (100.0 - health) / 40.0) * (1.0 + fail_count * 0.5)
            if is_stormy and s["conductor_type"] in ["ACSR_WEASEL", "ACSR_RABBIT"]:
                w *= 2.2  # lighter overhead lines more susceptible to wind sway
            section_weights.append(w)

        total_w = sum(section_weights)
        norm_weights = [w / total_w for w in section_weights]
        true_fault_sec = self.np_rng.choice(self.all_sections, p=norm_weights)
        true_fault_id = true_fault_sec["id"]
        target_feeder_id = true_fault_sec["feeder_id"]
        feeder_code = true_fault_sec["feeder_code"]

        # 3. Graph reachability: downstream de-energization vs upstream energized
        downstream_sec_ids = set(self.graph_engine.get_downstream_sections(true_fault_id))
        downstream_sec_ids.add(true_fault_id)
        upstream_sec_ids = set(self.graph_engine.get_upstream_sections(true_fault_id))

        # 4. Generate Telemetry for all Distribution Transformers (DTs)
        dt_telemetry = {}
        for tx_id, tx_meta in self.graph_engine.transformer_metadata.items():
            tx_sec_id = tx_meta["section_id"]
            tx_code = tx_meta["transformer_code"]

            if tx_sec_id in downstream_sec_ids:
                # Downstream of fault: OUTAGE!
                # Most read 0V, but some meters have slight residual induction or delayed reporting
                v_reading = round(max(0.0, self.rng.gauss(3.0, 2.5)), 1)
                is_outage = True
                # AMI last gasp packet delivery: 88% chance received, 12% lost
                ami_reported = self.rng.random() < 0.88
            elif tx_sec_id in upstream_sec_ids:
                # Upstream on same feeder: energized, with slight transient dip during fault
                v_reading = round(self.rng.gauss(226.0, 3.5), 1)
                is_outage = False
                ami_reported = False
            else:
                # Other feeders: normal healthy grid operation with small noise
                v_reading = round(self.rng.gauss(231.0, 2.5), 1)
                is_outage = False
                # 0.5% chance of spurious brownout report on unrelated feeder
                ami_reported = self.rng.random() < 0.005

            dt_telemetry[tx_code] = {
                "transformer_id": tx_id,
                "section_id": tx_sec_id,
                "voltage_v": v_reading,
                "is_outage": is_outage,
                "ami_reported": ami_reported,
            }

        # 5. Generate Customer Complaints per Consumer Cluster
        cluster_complaints = {}
        for tx_id, tx_meta in self.graph_engine.transformer_metadata.items():
            tx_code = tx_meta["transformer_code"]
            tx_sec_id = tx_meta["section_id"]
            is_affected = tx_sec_id in downstream_sec_ids

            # Base complaint reporting probability
            if is_affected:
                # High complaint propensity during waking/peak hours
                propensity = 0.45 if is_peak_hour else 0.18
                # Number of complaints follows binomial/Poisson around consumer count * propensity
                c_count = self.rng.randint(2, max(3, int(tx_meta["rated_kva"] * propensity * 0.4)))
            else:
                # Background noise / false complaints on unaffected sections!
                # E.g. internal tripping in a house, faulty inverter, or billing grievance
                c_count = 1 if self.rng.random() < 0.06 else 0

            cluster_complaints[tx_code] = c_count

        # 6. Simulate Partial Sensor Observations for Graph Engine
        # Breaker on target feeder trips:
        # We observe the root section or early trunk energized before trip, or breaker lockout
        # Partial telemetry observations:
        observed_energized = set()
        for u_id in upstream_sec_ids:
            if self.rng.random() < 0.65:  # 65% chance of upstream telemetry available
                observed_energized.add(u_id)

        observed_deenergized = set()
        for d_id in downstream_sec_ids:
            # If any DT on section d_id reported outage or AMI last gasp
            sec_dts = [t for t in self.graph_engine.transformer_metadata.values() if t["section_id"] == d_id]
            if any(dt_telemetry[t["transformer_code"]]["is_outage"] and dt_telemetry[t["transformer_code"]]["ami_reported"] for t in sec_dts):
                observed_deenergized.add(d_id)
            elif self.rng.random() < 0.40:
                observed_deenergized.add(d_id)

        # Fallback: ensure at least one de-energized observation exists on the faulted branch
        if not observed_deenergized:
            observed_deenergized.add(true_fault_id)

        # 7. Execute Graph Engine Pruning to get candidate sections
        pruning_result = self.graph_engine.prune_candidates(
            observed_energized_section_ids=observed_energized,
            observed_deenergized_section_ids=observed_deenergized,
        )

        candidates = pruning_result["topology_consistent_candidates"]

        # Ensure true fault section is present in candidates if it wasn't pruned
        # (If true fault section was pruned due to extreme noisy observation, record it honestly)
        candidate_section_ids = {c["section_id"] for c in candidates}

        # 8. Build Feature Rows for every candidate section
        candidate_rows = []
        for cand in candidates:
            c_id = cand["section_id"]
            sec_meta = self.graph_engine.section_metadata[c_id]
            s_code = sec_meta["section_code"]
            f_code = sec_meta["feeder_code"]

            # Downstream DTs for this candidate
            downstream_dts = self.graph_engine.get_downstream_transformers(c_id)
            downstream_dt_codes = [d["transformer_code"] for d in downstream_dts]

            # Aggregate voltage telemetry on downstream DTs
            if downstream_dt_codes:
                voltages = [dt_telemetry[d]["voltage_v"] for d in downstream_dt_codes]
                mean_voltage = float(np.mean(voltages))
                min_voltage = float(np.min(voltages))
                voltage_deviation = max(0.0, 230.0 - mean_voltage)
                outage_count = sum(1 for d in downstream_dt_codes if dt_telemetry[d]["is_outage"])
                outage_fraction = outage_count / len(downstream_dt_codes)
                complaints_sum = sum(cluster_complaints.get(d, 0) for d in downstream_dt_codes)
                total_downstream_kva = sum(d["current_load_kva"] for d in downstream_dts)
            else:
                voltage_deviation = 0.0
                min_voltage = 230.0
                outage_count = 0
                outage_fraction = 0.0
                complaints_sum = 0
                total_downstream_kva = 0.0

            # Asset condition
            asset = self.asset_cache.get(s_code)
            health_index = asset.health_index if asset else 85.0
            fail_count = asset.failure_history_count if asset else 0
            operating_temp = asset.operating_temperature_c if (asset and asset.operating_temperature_c) else 50.0

            # Electrical metrics from graph engine
            elec = cand["electrical_metrics"]

            # Topology features
            upstream_path = self.graph_engine.get_upstream_sections(c_id)
            depth = len(upstream_path)
            branch_factor = len(list(self.graph_engine.graph.successors(f"section:{c_id}")))

            is_true = 1 if c_id == true_fault_id else 0

            candidate_rows.append({
                "scenario_id": scenario_id,
                "section_id": c_id,
                "section_code": s_code,
                "feeder_code": f_code,
                # Observational & Telemetry Features
                "voltage_deviation": round(voltage_deviation, 2),
                "min_voltage": round(min_voltage, 2),
                "downstream_outage_count": outage_count,
                "downstream_outage_fraction": round(outage_fraction, 3),
                "complaint_count": complaints_sum,
                "complaint_density": round(complaints_sum / max(1.0, len(downstream_dt_codes)), 3),
                # Environmental & Weather Features
                "wind_speed_kmh": wind_speed,
                "precipitation_mm": precipitation,
                "ambient_temp_c": ambient_temp,
                "lightning_count": lightning_count,
                "hour_of_day": hour,
                "is_peak_hour": 1 if is_peak_hour else 0,
                # Asset Condition Features
                "asset_health_index": health_index,
                "historical_failures": fail_count,
                "operating_temperature_c": operating_temp,
                # Topological & Electrical Line Features
                "section_length_km": sec_meta["length_km"],
                "resistance_ohm": sec_meta["resistance_ohm"],
                "reactance_ohm": sec_meta["reactance_ohm"],
                "rated_capacity_kva": sec_meta["rated_capacity_kva"],
                "distance_from_substation_km": elec["distance_from_substation_km"],
                "cumulative_resistance_ohm": elec["cumulative_resistance_ohm"],
                "estimated_voltage_drop_v": elec["estimated_voltage_drop_v"],
                "downstream_dt_count": len(downstream_dts),
                "downstream_load_kva": elec["downstream_load_kva"],
                "has_critical_load": 1 if cand["downstream_critical_loads"] else 0,
                "depth": depth,
                "branch_factor": branch_factor,
                # Target ground truth label
                "is_true_fault": is_true,
            })

        return {
            "scenario_id": scenario_id,
            "feeder_code": feeder_code,
            "true_fault_section_code": true_fault_sec["section_code"],
            "candidates_count": len(candidate_rows),
            "rows": candidate_rows,
        }

    def generate_dataset(self, num_scenarios: int = 2500) -> pd.DataFrame:
        """
        Generates thousands of synthetic scenarios and returns a consolidated DataFrame.
        """
        all_rows = []
        for i in range(1, num_scenarios + 1):
            sc_id = f"SCENARIO_{i:05d}"
            sc_data = self.generate_single_scenario(sc_id)
            all_rows.extend(sc_data["rows"])

        df = pd.DataFrame(all_rows)
        return df


def generate_and_save_scenarios(num_scenarios: int = 2500, output_path: str = "datasets/processed/candidate_features.csv"):
    """CLI / programmatic generator for synthetic training dataset."""
    db = SessionLocal()
    try:
        simulator = GridScenarioSimulator(db=db, seed=2026)
        print(f"Simulating {num_scenarios} realistic grid fault scenarios across 8 feeders...")
        df = simulator.generate_dataset(num_scenarios=num_scenarios)
        print(f"Generated {len(df)} candidate feature rows across {num_scenarios} scenarios.")
        print(f"Class distribution: {df['is_true_fault'].value_counts().to_dict()}")
        df.to_csv(output_path, index=False)
        print(f"Dataset saved to {output_path}")
        return df
    finally:
        db.close()


if __name__ == "__main__":
    generate_and_save_scenarios(num_scenarios=2500)
