import os
import json
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any

router = APIRouter(tags=["ML & Metrics"])

METRICS_PATH = "models/metrics.json"
CALIB_PATH = "models/calibration_curve.json"


@router.get("/model/metrics")
def get_model_metrics():
    """
    Returns empirical evaluation metrics, calibration stats, and feature importance.
    Evaluated strictly on held-out test scenarios.
    """
    if not os.path.exists(METRICS_PATH):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model metrics not found. Train the model using 'python -m backend.app.ml_engine.train'."
        )

    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    calibration_data = {}
    if os.path.exists(CALIB_PATH):
        with open(CALIB_PATH, "r", encoding="utf-8") as f:
            calibration_data = json.load(f)

    bins = calibration_data.get("reliability_bins", [])
    samples = [
        {
            "mean_predicted_value": round(b["mean_confidence"], 3),
            "fraction_of_positives": round(b["empirical_accuracy"], 3),
            "sample_count": b["sample_count"],
        }
        for b in bins if b.get("sample_count", 0) > 0
    ]

    return {
        "status": "trained",
        "metrics": metrics,
        "test_metrics": metrics.get("test_metrics", {}),
        "calibration": {
            **calibration_data,
            "reliability_curve_samples": samples,
        },
        "terminology_compliance": {
            "uncalibrated_model_output": "raw_score",
            "calibrated_model_output": "calibrated_probability",
            "candidate_designation": "topology-consistent candidates",
            "split_method": "scenario_id grouping (zero row leakage)"
        }
    }
