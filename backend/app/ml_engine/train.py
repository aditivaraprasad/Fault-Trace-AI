"""
Training and Evaluation Pipeline for FAULTTRACE AI.
- Enforces Scenario-ID based train/val/test split (Zero row-level leakage).
- Trains XGBoost candidate ranker with class imbalance weighting.
- Calibrates probabilities on the validation partition (Platt Scaling vs Isotonic Regression).
- Evaluates Top-1 & Top-3 Localization Accuracy, Confusion Matrix, ECE, and Inference Latency on TEST split only.
- Saves all model artifacts, metrics, and reliability curves.
"""

import os
import json
import time
from typing import Dict, List, Tuple, Any
import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    brier_score_loss,
    log_loss,
)

from backend.app.ml_engine.calibrator import ProbabilityCalibrator
from backend.app.simulation.scenario_simulator import generate_and_save_scenarios

FEATURE_COLS = [
    "voltage_deviation",
    "min_voltage",
    "downstream_outage_count",
    "downstream_outage_fraction",
    "complaint_count",
    "complaint_density",
    "wind_speed_kmh",
    "precipitation_mm",
    "ambient_temp_c",
    "lightning_count",
    "hour_of_day",
    "is_peak_hour",
    "asset_health_index",
    "historical_failures",
    "operating_temperature_c",
    "section_length_km",
    "resistance_ohm",
    "reactance_ohm",
    "rated_capacity_kva",
    "distance_from_substation_km",
    "cumulative_resistance_ohm",
    "estimated_voltage_drop_v",
    "downstream_dt_count",
    "downstream_load_kva",
    "has_critical_load",
    "depth",
    "branch_factor",
]


def split_by_scenario_id(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Partitions the dataset strictly by scenario_id.
    Ensures zero cross-scenario data leakage between train, validation, and test splits.
    """
    unique_scenarios = df["scenario_id"].unique()
    rng = np.random.RandomState(seed)
    shuffled_scenarios = rng.permutation(unique_scenarios)

    n_total = len(shuffled_scenarios)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)

    train_scenarios = set(shuffled_scenarios[:n_train])
    val_scenarios = set(shuffled_scenarios[n_train : n_train + n_val])
    test_scenarios = set(shuffled_scenarios[n_train + n_val :])

    # Assert mutual exclusivity across all splits
    assert train_scenarios.isdisjoint(val_scenarios), "Leakage detected: Train and Val overlap!"
    assert train_scenarios.isdisjoint(test_scenarios), "Leakage detected: Train and Test overlap!"
    assert val_scenarios.isdisjoint(test_scenarios), "Leakage detected: Val and Test overlap!"

    df_train = df[df["scenario_id"].isin(train_scenarios)].copy()
    df_val = df[df["scenario_id"].isin(val_scenarios)].copy()
    df_test = df[df["scenario_id"].isin(test_scenarios)].copy()

    return df_train, df_val, df_test


def compute_expected_calibration_error(
    y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10
) -> Tuple[float, List[Dict[str, float]]]:
    """
    Computes empirical Expected Calibration Error (ECE) and reliability curve bins.
    """
    bin_limits = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    reliability_bins = []

    for i in range(n_bins):
        low, high = bin_limits[i], bin_limits[i + 1]
        # Include upper boundary on the final bin
        mask = (y_prob >= low) & (y_prob <= high) if i == n_bins - 1 else (y_prob >= low) & (y_prob < high)
        bin_count = np.sum(mask)

        if bin_count > 0:
            bin_acc = float(np.mean(y_true[mask]))
            bin_conf = float(np.mean(y_prob[mask]))
            weight = bin_count / len(y_true)
            ece += weight * abs(bin_acc - bin_conf)

            reliability_bins.append({
                "bin_index": i + 1,
                "bin_range": f"{low:.1f}-{high:.1f}",
                "mean_confidence": round(bin_conf, 4),
                "empirical_accuracy": round(bin_acc, 4),
                "sample_count": int(bin_count),
            })
        else:
            reliability_bins.append({
                "bin_index": i + 1,
                "bin_range": f"{low:.1f}-{high:.1f}",
                "mean_confidence": round((low + high) / 2.0, 4),
                "empirical_accuracy": 0.0,
                "sample_count": 0,
            })

    return round(float(ece), 4), reliability_bins


def compute_scenario_localization_accuracy(
    df_test: pd.DataFrame, scores: np.ndarray
) -> Dict[str, float]:
    """
    Computes Top-1 and Top-3 Fault Localization Accuracy per scenario.
    """
    df_eval = df_test[["scenario_id", "section_code", "is_true_fault"]].copy()
    df_eval["score"] = scores

    top1_correct = 0
    top3_correct = 0
    total_scenarios = 0

    for _, group in df_eval.groupby("scenario_id"):
        total_scenarios += 1
        sorted_group = group.sort_values(by="score", ascending=False)
        ranked_labels = sorted_group["is_true_fault"].values

        # Check if the true fault (label == 1) is ranked at position 0 (Top-1)
        if len(ranked_labels) > 0 and ranked_labels[0] == 1:
            top1_correct += 1

        # Check if true fault is in top 3 positions
        if any(ranked_labels[:3] == 1):
            top3_correct += 1

    top1_acc = round((top1_correct / total_scenarios) * 100.0, 2) if total_scenarios > 0 else 0.0
    top3_acc = round((top3_correct / total_scenarios) * 100.0, 2) if total_scenarios > 0 else 0.0

    return {
        "test_scenarios_count": total_scenarios,
        "top_1_accuracy_pct": top1_acc,
        "top_3_accuracy_pct": top3_acc,
    }


def train_and_evaluate(
    data_path: str = "datasets/processed/candidate_features.csv",
    models_dir: str = "models",
    n_scenarios_if_missing: int = 2500,
) -> Dict[str, Any]:
    """
    End-to-end training, calibration, and test-set evaluation pipeline.
    """
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(os.path.dirname(data_path), exist_ok=True)

    # 1. Load or generate dataset
    if not os.path.exists(data_path):
        print(f"Dataset not found at {data_path}. Generating {n_scenarios_if_missing} synthetic scenarios...")
        df = generate_and_save_scenarios(num_scenarios=n_scenarios_if_missing, output_path=data_path)
    else:
        print(f"Loading existing dataset from {data_path}...")
        df = pd.read_csv(data_path)

    print(f"Dataset loaded: {len(df)} total candidate rows across {df['scenario_id'].nunique()} scenarios.")

    # 2. Split train / validation / test by scenario_id
    df_train, df_val, df_test = split_by_scenario_id(df, train_ratio=0.70, val_ratio=0.15, seed=42)
    print(f"Partitioned splits (by Scenario ID): Train={df_train['scenario_id'].nunique()} scenarios ({len(df_train)} rows), "
          f"Val={df_val['scenario_id'].nunique()} scenarios ({len(df_val)} rows), "
          f"Test={df_test['scenario_id'].nunique()} scenarios ({len(df_test)} rows)")

    X_train = df_train[FEATURE_COLS]
    y_train = df_train["is_true_fault"].values
    X_val = df_val[FEATURE_COLS]
    y_val = df_val["is_true_fault"].values
    X_test = df_test[FEATURE_COLS]
    y_test = df_test["is_true_fault"].values

    # 3. Handle class imbalance
    num_neg = np.sum(y_train == 0)
    num_pos = np.sum(y_train == 1)
    scale_pos_weight = float(num_neg / max(1, num_pos))
    print(f"Class imbalance on Train: {num_pos} positives, {num_neg} negatives (scale_pos_weight={scale_pos_weight:.2f})")

    # 4. Train XGBoost Ranker
    print("Training XGBoost Candidate Ranker...")
    xgb_base = XGBClassifier(
        n_estimators=150,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        eval_metric="logloss",
        early_stopping_rounds=15,
        tree_method="hist",
    )

    xgb_base.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    # 5. Calibration Comparison on Validation Split (Isotonic vs Platt)
    print("Fitting probability calibrators on Validation partition...")
    raw_val_scores = xgb_base.predict_proba(X_val)[:, 1]

    # Isotonic
    iso_calibrator = ProbabilityCalibrator(method="isotonic")
    iso_calibrator.fit(raw_val_scores, y_val)
    iso_val_probs = iso_calibrator.predict_proba(raw_val_scores)
    iso_val_brier = brier_score_loss(y_val, iso_val_probs)
    iso_val_loss = log_loss(y_val, iso_val_probs)

    # Platt (Sigmoid)
    platt_calibrator = ProbabilityCalibrator(method="sigmoid")
    platt_calibrator.fit(raw_val_scores, y_val)
    platt_val_probs = platt_calibrator.predict_proba(raw_val_scores)
    platt_val_brier = brier_score_loss(y_val, platt_val_probs)
    platt_val_loss = log_loss(y_val, platt_val_probs)

    print(f"Validation Brier Loss: Isotonic={iso_val_brier:.5f}, Platt={platt_val_brier:.5f}")
    print(f"Validation Log Loss: Isotonic={iso_val_loss:.5f}, Platt={platt_val_loss:.5f}")

    if iso_val_brier <= platt_val_brier:
        best_calibrator = iso_calibrator
        chosen_calib_name = "isotonic"
    else:
        best_calibrator = platt_calibrator
        chosen_calib_name = "platt_sigmoid"
    print(f"Selected best calibration strategy: {chosen_calib_name.upper()}")

    # 6. Evaluate strictly on TEST split
    print("\nEvaluating model on TEST split only (unseen scenarios)...")
    # Measure inference latency over test scenarios
    start_time = time.perf_counter()
    raw_test_scores = xgb_base.predict_proba(X_test)[:, 1]
    calibrated_test_probs = best_calibrator.predict_proba(raw_test_scores)
    total_latency_ms = (time.perf_counter() - start_time) * 1000.0
    mean_latency_per_scenario_ms = total_latency_ms / max(1, df_test["scenario_id"].nunique())

    # Threshold-based predictions at 0.5 calibrated probability
    test_preds = (calibrated_test_probs >= 0.5).astype(int)

    # Standard metrics
    test_acc = accuracy_score(y_test, test_preds)
    test_prec = precision_score(y_test, test_preds, zero_division=0)
    test_rec = recall_score(y_test, test_preds, zero_division=0)
    test_f1 = f1_score(y_test, test_preds, zero_division=0)
    test_cm = confusion_matrix(y_test, test_preds).tolist()
    test_brier = brier_score_loss(y_test, calibrated_test_probs)
    test_logloss = log_loss(y_test, calibrated_test_probs)

    # Scenario-level Top-1 & Top-3 Localization Accuracy
    scenario_acc = compute_scenario_localization_accuracy(df_test, calibrated_test_probs)

    # Expected Calibration Error (ECE) and curve on Test split
    ece, reliability_curve = compute_expected_calibration_error(y_test, calibrated_test_probs, n_bins=10)

    # Feature Importance ranking
    feature_importances = dict(zip(FEATURE_COLS, [round(float(v), 5) for v in xgb_base.feature_importances_]))
    sorted_features = sorted(feature_importances.items(), key=lambda x: x[1], reverse=True)

    metrics_report = {
        "evaluation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model_architecture": "XGBoost Classifier + Calibration",
        "calibration_method": chosen_calib_name,
        "features_count": len(FEATURE_COLS),
        "dataset_summary": {
            "total_scenarios": int(df["scenario_id"].nunique()),
            "total_candidate_rows": int(len(df)),
            "train_scenarios": int(df_train["scenario_id"].nunique()),
            "val_scenarios": int(df_val["scenario_id"].nunique()),
            "test_scenarios": int(df_test["scenario_id"].nunique()),
            "test_candidates_count": int(len(df_test)),
        },
        "test_metrics": {
            "top_1_localization_accuracy_pct": scenario_acc["top_1_accuracy_pct"],
            "top_3_localization_accuracy_pct": scenario_acc["top_3_accuracy_pct"],
            "binary_accuracy": round(float(test_acc), 4),
            "precision": round(float(test_prec), 4),
            "recall": round(float(test_rec), 4),
            "f1_score": round(float(test_f1), 4),
            "confusion_matrix": {
                "true_negative": test_cm[0][0],
                "false_positive": test_cm[0][1],
                "false_negative": test_cm[1][0],
                "true_positive": test_cm[1][1],
            },
            "brier_score": round(float(test_brier), 5),
            "log_loss": round(float(test_logloss), 5),
            "expected_calibration_error_ece": ece,
            "mean_inference_latency_per_scenario_ms": round(float(mean_latency_per_scenario_ms), 3),
        },
        "top_5_predictive_features": sorted_features[:5],
    }

    # 7. Save model artifacts
    xgb_path = os.path.join(models_dir, "xgboost_ranker.joblib")
    calib_path = os.path.join(models_dir, "calibrator.joblib")
    features_path = os.path.join(models_dir, "feature_names.json")
    metrics_path = os.path.join(models_dir, "metrics.json")
    curve_path = os.path.join(models_dir, "calibration_curve.json")

    joblib.dump(xgb_base, xgb_path)
    joblib.dump(best_calibrator, calib_path)
    with open(features_path, "w", encoding="utf-8") as f:
        json.dump(FEATURE_COLS, f, indent=2)
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_report, f, indent=2)
    with open(curve_path, "w", encoding="utf-8") as f:
        json.dump({
            "calibration_method": chosen_calib_name,
            "expected_calibration_error": ece,
            "reliability_bins": reliability_curve,
        }, f, indent=2)

    print("\n=== MEASURED TEST EVALUATION RESULTS ===")
    print(f"  Top-1 Localization Accuracy: {scenario_acc['top_1_accuracy_pct']}%")
    print(f"  Top-3 Localization Accuracy: {scenario_acc['top_3_accuracy_pct']}%")
    print(f"  Precision: {test_prec:.4f} | Recall: {test_rec:.4f} | F1-Score: {test_f1:.4f}")
    print(f"  Brier Score: {test_brier:.5f} | Log Loss: {test_logloss:.5f}")
    print(f"  Expected Calibration Error (ECE): {ece}")
    print(f"  Inference Latency: {mean_latency_per_scenario_ms:.3f} ms / scenario")
    print(f"\nArtifacts saved to {models_dir}/")

    return metrics_report


if __name__ == "__main__":
    train_and_evaluate()
