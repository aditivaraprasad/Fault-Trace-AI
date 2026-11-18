"""
Probability Calibration classes for FAULTTRACE AI.
Provides unified interface for Isotonic Regression and Platt (Sigmoid) Scaling.
"""

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression


class ProbabilityCalibrator:
    """
    Validation-fitted post-hoc probability calibrator.
    Converts raw XGBoost scores into empirical probabilities.
    """

    def __init__(self, method: str = "isotonic"):
        self.method = method
        if method == "isotonic":
            self.model = IsotonicRegression(out_of_bounds="clip")
        else:
            self.model = LogisticRegression(random_state=42)

    def fit(self, raw_scores: np.ndarray, y_true: np.ndarray):
        if self.method == "isotonic":
            self.model.fit(raw_scores, y_true)
        else:
            self.model.fit(raw_scores.reshape(-1, 1), y_true)
        return self

    def predict_proba(self, raw_scores: np.ndarray) -> np.ndarray:
        if self.method == "isotonic":
            probs = self.model.predict(raw_scores)
            return np.clip(probs, 0.0, 1.0)
        else:
            return self.model.predict_proba(raw_scores.reshape(-1, 1))[:, 1]
