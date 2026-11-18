"""
Inference wrapper for the FAULTTRACE AI XGBoost Model & Calibrator.
Strict terminology compliance:
- Raw model output is a "score".
- Calibrated model output is a "probability".
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
import joblib
import numpy as np
import pandas as pd


class FaultTraceRanker:
    """Production inference wrapper for candidate ranking and probability calibration."""

    def __init__(self, models_dir: str = "models"):
        self.models_dir = models_dir
        self.model = None
        self.calibrator = None
        self.feature_names = []
        self._load_artifacts()

    def _load_artifacts(self):
        xgb_path = os.path.join(self.models_dir, "xgboost_ranker.joblib")
        calib_path = os.path.join(self.models_dir, "calibrator.joblib")
        feat_path = os.path.join(self.models_dir, "feature_names.json")

        if os.path.exists(xgb_path) and os.path.exists(calib_path) and os.path.exists(feat_path):
            self.model = joblib.load(xgb_path)
            self.calibrator = joblib.load(calib_path)
            with open(feat_path, "r", encoding="utf-8") as f:
                self.feature_names = json.load(f)
        else:
            self.model = None
            self.calibrator = None
            self.feature_names = []

    def is_loaded(self) -> bool:
        return self.model is not None and self.calibrator is not None

    def score_candidates(self, features_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Computes raw scores and calibrated probabilities for a candidate batch.
        Raw output = 'raw_score'. Calibrated output = 'calibrated_probability'.
        """
        if not self.is_loaded():
            raise RuntimeError("Model or calibrator artifacts not loaded. Run train pipeline first.")

        # Ensure all expected feature columns exist
        missing = set(self.feature_names) - set(features_df.columns)
        if missing:
            raise ValueError(f"Missing required feature columns: {missing}")

        X = features_df[self.feature_names]

        # Raw scores from the base XGBoost estimator (uncalibrated probability margin)
        raw_scores = self.model.predict_proba(X)[:, 1]

        # Calibrated probabilities from the validation-fitted calibrator
        calibrated_probs = self.calibrator.predict_proba(raw_scores)

        results = []
        for i in range(len(features_df)):
            results.append({
                "raw_score": round(float(raw_scores[i]), 4),
                "calibrated_probability": round(float(calibrated_probs[i]), 4),
            })
        return results


# Global singleton instance
fault_ranker = FaultTraceRanker()
