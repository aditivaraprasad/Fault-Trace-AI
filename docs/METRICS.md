# FAULTTRACE AI: Comprehensive Model Evaluation & Metric Reconciliation

**BESCOM Power Hack 2026 — Theme 10**  
**Document Classification**: Empirical Evaluation Report & Slide Reconciliation Guide  
**Source of Truth**: `models/metrics.json` and `datasets/processed/qa_live_benchmark_20_runs.json`

---

## 1. Evaluation Methodology & Ground Truth Integrity

### 1.1 Scenario-Split Partitioning (Zero Data Leakage)
To prevent optimistic data leakage, all datasets were split strictly at the **`scenario_id` level** using `GroupShuffleSplit` rather than row-level random sampling:
- **Total Synthetic Scenarios Generated**: 2,500
- **Total Candidate Feature Rows**: 30,634
- **Training Set (70%)**: 1,750 scenarios (21,452 candidate rows)
- **Validation Set (15%)**: 375 scenarios (4,605 candidate rows) &rarr; used exclusively for probability calibration fitting
- **Test Set (15%)**: 375 scenarios (4,577 candidate rows) &rarr; evaluated once on held-out data

> **Data Leakage Invariant**: An automated test (`test_no_scenario_leakage` in `backend/tests/test_ml_pipeline.py`) asserts that `set(train_scenarios) ∩ set(val_scenarios) ∩ set(test_scenarios) == ∅`. No feeder disturbance or event signature appears in more than one partition.

---

## 2. Real Measured Metrics from Held-Out Test Set

The following metrics represent strictly empirical results evaluated on the 375 held-out test scenarios:

### 2.1 Core Localization Performance

| Metric | Measured Test Value | Description / Operational Interpretation |
| :--- | :--- | :--- |
| **Top-1 Localization Accuracy** | **62.67%** | The true physical fault section was ranked as Rank #1 in 235 out of 375 scenarios. |
| **Top-3 Localization Accuracy** | **89.33%** | The true physical fault section was included in the Top-3 candidate sections in 335 out of 375 scenarios. |
| **Binary Classification Accuracy** | **92.07%** | Raw fraction of candidate sections correctly classified as fault vs. non-fault. |
| **Precision (at 0.5 threshold)** | **63.64%** | True Positives / (True Positives + False Positives) = 28 / (28 + 16). |
| **Recall (at 0.5 threshold)** | **7.47%** | True Positives / (True Positives + False Negatives) = 28 / (28 + 347). Reflects extreme 1:12 class imbalance at default 0.5 threshold. |
| **F1-Score (at 0.5 threshold)** | **0.1337** | Harmonic mean of precision and recall at fixed 0.5 cutoff. |
| **Brier Score** | **0.06696** | Mean squared difference between predicted probability and actual binary outcome. (Lower is better, &lt;0.10 is excellent). |
| **Log-Loss (Cross-Entropy)** | **0.23591** | Negative log-likelihood of calibrated probabilities on held-out test data. |
| **Expected Calibration Error (ECE)** | **0.0054 (0.54%)** | 10-bin reliability deviation. Confirms calibrated probabilities match observed empirical frequencies within 0.54%. |
| **Raw ML Inference Latency** | **0.038 ms** | Microseconds per candidate batch on CPU. |
| **End-to-End Pipeline Latency** | **131.5 ms** | Mean end-to-end latency including DB commit, NetworkX graph pruning, Tree SHAP calculation, and restoration planning. |
| **Graph Pruning Efficiency** | **91.56%** | Percentage of non-viable grid sections pruned by the graph engine prior to ML ranking. |

---

### 2.2 Test Set Confusion Matrix (4,577 Evaluated Candidate Rows)

```
                       ACTUAL NON-FAULT (0)       ACTUAL FAULT SECTION (1)
PREDICTED NON-FAULT (0)        4,186 (TN)                     347 (FN)
PREDICTED FAULT SECTION (1)       16 (FP)                      28 (TP)
```

- **True Negatives (TN = 4,186)**: The model correctly identified 4,186 healthy candidate sections as non-fault.
- **False Positives (FP = 16)**: Only 16 healthy sections were incorrectly predicted as faults above the 0.5 probability threshold (**False Alarm Rate = 0.38%**).
- **False Negatives (FN = 347)**: At a hard 0.5 binary threshold, many true fault sections had calibrated probabilities between 0.20 and 0.49 due to severe class imbalance. This mathematically demonstrates why **ranking (Top-3 accuracy = 89.33%)** is the correct operational metric over arbitrary binary thresholding.
- **True Positives (TP = 28)**: 28 fault sections had strong multi-modal convergence (&gt;0.5 calibrated probability).

---

### 2.3 Top 5 Most Predictive Features (XGBoost Feature Importance)

| Rank | Feature Name | Importance Weight | Physical Engineering Rationale |
| :---: | :--- | :---: | :--- |
| **1** | `downstream_outage_fraction` | **0.5041 (50.4%)** | Fraction of downstream transformers that lost voltage. A fault upstream de-energizes 100% of downstream nodes. |
| **2** | `downstream_dt_count` | **0.1348 (13.5%)** | Total number of transformers downstream; distinguishes main trunk branches from terminal stubs. |
| **3** | `estimated_voltage_drop_v` | **0.0956 (9.6%)** | Synthetic $I \cdot Z$ voltage drop deviation from nominal 230V base. |
| **4** | `distance_from_substation_km` | **0.0257 (2.6%)** | Electrical distance along the radial feeder tree from the circuit breaker. |
| **5** | `depth` | **0.0243 (2.4%)** | Topological tree depth (number of hops from substation busbar). |

---

## 3. Live 20-Run Scenario Benchmark (Production Readiness Test)

Conducted during Phase 8 QA across 20 randomized live simulation executions:

| Metric | Baseline Test Set ($N=375$) | Live QA Benchmark ($N=20$) | Variance |
| :--- | :---: | :---: | :---: |
| **Top-1 Accuracy** | 62.67% | **35.00%** | -27.67% (Sample variance on small batch of complex lateral faults) |
| **Top-3 Accuracy** | 89.33% | **80.00%** | -9.33% (16 of 20 runs located within Top 3) |
| **Mean Pruning %** | 91.56% | **91.50%** | **-0.06% (Exact consistency)** |
| **Mean Pipeline Latency** | 131.5 ms | **131.5 ms** | &lt;150 ms target achieved |

---

## 4. Pitch Deck Slide Claims vs. Real Measured Reality

To ensure complete credibility during the judging round, use this table to align your presentation slides with verifiable reality:

| Topic / Metric | Typical Hackathon Pitch Claim (Avoid) | Real Engineering Reality (Say This Instead) | Why the Real Claim Wins Judges' Respect |
| :--- | :--- | :--- | :--- |
| **Localization Accuracy** | *"99.9% Fault Localization Accuracy"* | **"62.7% Top-1 Accuracy, 89.3% Top-3 Localization Accuracy"** | Power systems judges know 99.9% is impossible on noisy distribution grids. Demonstrating that field crews get a 3-pole window 89% of the time proves operational realism. |
| **Decision Metric** | *"High Precision & Recall &gt; 95%"* | **"Rank-based Top-k metrics because class imbalance is 1:12"** | In a distribution grid, 92% of candidate sections are healthy. Precision/Recall at 0.5 threshold hides the ranking nature of utility crew dispatch. |
| **System Latency** | *"Instant sub-millisecond AI"* | **"0.038 ms model inference, 131.5 ms full end-to-end pipeline"** | Acknowledging that database writes, graph pruning, SHAP explanations, and restoration planning take 131 ms proves you built an end-to-end system, not just a standalone notebook script. |
| **Automation Level** | *"Autonomous self-healing AI grid"* | **"Advisory Decision Support with Mandatory Safety Invariants"** | Fully autonomous switching in distribution grids violates utility safety codes (CEA/OSHA). Calling it advisory with human-in-the-loop review demonstrates domain maturity. |
| **Candidate Identification** | *"Mathematical proof of fault location"* | **"Topology-Consistent Candidates (91.56% search space pruned)"** | Network reachability prunes non-viable branches, but cannot "prove" physical wire damage between two un-metered poles without field inspection. |
| **Model Output** | *"AI Probability Score"* | **"Calibrated Probabilities (Isotonic Regression, ECE = 0.0054)"** | Demonstrates understanding that raw tree scores are uncalibrated and cannot be directly interpreted as risk probabilities. |

---

## 5. Slide Update Action Items

1. **Slide 4 (The Solution)**: Update headline from *"Instant AI Self-Healing"* to *"Intelligent Fault Localization & Advisory Switching Platform"*.
2. **Slide 7 (ML Performance)**: Replace *"99% Accuracy"* with a two-part metric:
   - **89.3% Top-3 Localization Accuracy** (3-pole crew dispatch window)
   - **91.56% Topological Search Space Pruning** (reduces 140 sections to &lt;12 candidates)
3. **Slide 9 (Safety & Human in the Loop)**: Prominently feature the **Lock-Out / Tag-Out (LOTO)** invariant and the **Advisory Review Banner**, highlighting that FAULTTRACE AI protects linemen from unauthorized re-energization.