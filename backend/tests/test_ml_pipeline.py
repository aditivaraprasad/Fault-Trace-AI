import os
import json
import pytest
import pandas as pd
import numpy as np

from backend.app.ml_engine.calibrator import ProbabilityCalibrator
from backend.app.ml_engine.train import (
    FEATURE_COLS,
    split_by_scenario_id,
    compute_expected_calibration_error,
    train_and_evaluate,
)
from backend.app.ml_engine.model import FaultTraceRanker


def test_no_scenario_leakage():
    """
    CRITICAL AUDIT TEST:
    Asserts that scenario-based splitting produces strictly disjoint partitions.
    No scenario ID may appear in multiple splits.
    """
    # Create synthetic mock scenario data
    mock_scenarios = [f"SCENARIO_{i:04d}" for i in range(1, 101)]
    records = []
    for s_id in mock_scenarios:
        for c_idx in range(5):  # 5 candidates per scenario
            records.append({
                "scenario_id": s_id,
                "section_code": f"SEC_{c_idx}",
                "is_true_fault": 1 if c_idx == 0 else 0,
            })
    df_mock = pd.DataFrame(records)

    df_train, df_val, df_test = split_by_scenario_id(df_mock, train_ratio=0.7, val_ratio=0.15, seed=42)

    train_ids = set(df_train["scenario_id"].unique())
    val_ids = set(df_val["scenario_id"].unique())
    test_ids = set(df_test["scenario_id"].unique())

    # Verify non-empty
    assert len(train_ids) == 70
    assert len(val_ids) == 15
    assert len(test_ids) == 15

    # STRICT ASSERTIONS: Mutual exclusivity
    assert len(train_ids.intersection(val_ids)) == 0, "Data leakage between Train and Val!"
    assert len(train_ids.intersection(test_ids)) == 0, "Data leakage between Train and Test!"
    assert len(val_ids.intersection(test_ids)) == 0, "Data leakage between Val and Test!"

    # Total conservation
    assert len(train_ids) + len(val_ids) + len(test_ids) == 100


def test_ece_computation():
    """Verifies that ECE returns valid empirical calibration error in [0, 1]."""
    y_true = np.array([1, 0, 1, 0, 1, 0, 0, 0, 1, 1])
    y_prob = np.array([0.9, 0.1, 0.8, 0.2, 0.7, 0.3, 0.15, 0.25, 0.85, 0.95])

    ece, curve = compute_expected_calibration_error(y_true, y_prob, n_bins=5)
    assert 0.0 <= ece <= 1.0
    assert len(curve) == 5
    assert "mean_confidence" in curve[0]
    assert "empirical_accuracy" in curve[0]


def test_model_training_and_artifacts():
    """Verifies model training, artifact creation, and evaluation files."""
    # Run training pipeline with existing or minimal scenario set
    metrics = train_and_evaluate(
        data_path="datasets/processed/candidate_features.csv",
        models_dir="models",
        n_scenarios_if_missing=500,
    )

    # Check that artifact files exist
    assert os.path.exists("models/xgboost_ranker.joblib")
    assert os.path.exists("models/calibrator.joblib")
    assert os.path.exists("models/feature_names.json")
    assert os.path.exists("models/metrics.json")
    assert os.path.exists("models/calibration_curve.json")

    # Check metrics content
    assert "test_metrics" in metrics
    tm = metrics["test_metrics"]
    assert "top_1_localization_accuracy_pct" in tm
    assert "top_3_localization_accuracy_pct" in tm
    assert "brier_score" in tm
    assert "expected_calibration_error_ece" in tm
    assert tm["top_1_localization_accuracy_pct"] >= 0.0
    assert tm["top_3_localization_accuracy_pct"] >= tm["top_1_localization_accuracy_pct"]


def test_model_loads_and_predicts():
    """Verifies that the inference wrapper correctly loads artifacts and outputs scores & probabilities."""
    ranker = FaultTraceRanker(models_dir="models")
    assert ranker.is_loaded() is True
    assert len(ranker.feature_names) == 27

    # Create a synthetic test row matching feature names
    sample_data = {feat: [0.5] for feat in ranker.feature_names}
    df_sample = pd.DataFrame(sample_data)

    results = ranker.score_candidates(df_sample)
    assert len(results) == 1
    assert "raw_score" in results[0]
    assert "calibrated_probability" in results[0]

    # Verify probability bounds
    prob = results[0]["calibrated_probability"]
    assert 0.0 <= prob <= 1.0


def test_metrics_endpoint(client):
    """Verifies GET /model/metrics returns live test metrics from models/metrics.json."""
    res = client.get("/model/metrics")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "trained"
    assert "metrics" in data
    assert "test_metrics" in data["metrics"]
    assert "terminology_compliance" in data
    assert data["terminology_compliance"]["uncalibrated_model_output"] == "raw_score"
    assert data["terminology_compliance"]["calibrated_model_output"] == "calibrated_probability"
