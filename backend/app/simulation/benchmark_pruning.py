"""
Empirical Benchmark: Measures real pruning percentage across 100 random fault scenarios.
Reports measured empirical metrics only (zero fabricated values).
"""

import random
import numpy as np
from sqlalchemy.orm import Session
from backend.app.database.session import SessionLocal
import backend.app.models as m
from backend.app.graph_engine.engine import DistributionGraphEngine


def run_pruning_benchmark(num_scenarios: int = 100, seed: int = 2026) -> dict:
    """
    Executes 100 randomized fault scenarios across all feeders in the network.
    Measures the exact percentage of search space pruned by the NetworkX graph engine.
    """
    rng = random.Random(seed)
    db = SessionLocal()

    try:
        engine = DistributionGraphEngine(db=db)
        all_sections = list(engine.section_metadata.values())
        feeders = list({s["feeder_id"] for s in all_sections})

        pruning_percentages = []
        candidates_counts = []
        pruned_counts = []

        print(f"Executing {num_scenarios} randomized fault scenarios for graph pruning evaluation...")

        for scenario_idx in range(1, num_scenarios + 1):
            # Pick a target feeder
            target_feeder = rng.choice(feeders)
            feeder_sections = [s for s in all_sections if s["feeder_id"] == target_feeder]

            # Pick a random faulted root section on the feeder
            # Choose from sections with depth >= 2 so there is an upstream and downstream
            potential_faults = [s for s in feeder_sections if s["parent_section_id"] is not None]
            fault_sec = rng.choice(potential_faults)
            fault_id = fault_sec["id"]

            # Downstream sections from fault are de-energized
            downstream_ids = set(engine.get_downstream_sections(fault_id))
            downstream_ids.add(fault_id)

            # Upstream sections are energized
            upstream_ids = set(engine.get_upstream_sections(fault_id))

            # Simulate partial observation:
            # Substation root and nearest ancestors report telemetry (energized)
            observed_energized = set(rng.sample(list(upstream_ids), max(1, len(upstream_ids) // 2)))
            # A subset of leaf downstream nodes report de-energization (AMI / alarm)
            observed_deenergized = set(rng.sample(list(downstream_ids), max(1, len(downstream_ids) // 2)))

            # Run graph engine candidate pruning
            result = engine.prune_candidates(
                observed_energized_section_ids=observed_energized,
                observed_deenergized_section_ids=observed_deenergized,
            )

            pruning_percentages.append(result["pruning_percentage"])
            candidates_counts.append(result["retained_candidates_count"])
            pruned_counts.append(result["pruned_sections_count"])

        pruning_arr = np.array(pruning_percentages)
        cand_arr = np.array(candidates_counts)

        summary = {
            "num_scenarios_evaluated": num_scenarios,
            "total_network_sections": len(all_sections),
            "mean_pruning_percentage": round(float(np.mean(pruning_arr)), 2),
            "median_pruning_percentage": round(float(np.median(pruning_arr)), 2),
            "std_pruning_percentage": round(float(np.std(pruning_arr)), 2),
            "min_pruning_percentage": round(float(np.min(pruning_arr)), 2),
            "max_pruning_percentage": round(float(np.max(pruning_arr)), 2),
            "mean_candidates_retained": round(float(np.mean(cand_arr)), 2),
            "min_candidates_retained": int(np.min(cand_arr)),
            "max_candidates_retained": int(np.max(cand_arr)),
        }

        print("\n=== MEASURED BENCHMARK RESULTS (100 SCENARIOS) ===")
        for k, v in summary.items():
            print(f"  {k}: {v}")

        return summary

    finally:
        db.close()


if __name__ == "__main__":
    run_pruning_benchmark(100)
