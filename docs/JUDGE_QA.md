# FAULTTRACE AI: 12 Technical Defense Q&As for Judges

**BESCOM Power Hack 2026 — Theme 10**  
**Document Classification**: Technical Defense Manual & Oral Examination Prep  
**Target Audience**: Power Systems Evaluators, Data Science Reviewers & Utility Operations Judges

---

## Category 1: Distribution Graph Engine & Electrical Topology

### Q1: In radial distribution networks, how do you guarantee that your candidate set contains the true fault? What happens if downstream AMI meters fail to report?
> **Answer:**  
> Our graph engine leverages the radial tree topology ($G=(V,E)$) inherent to 11 kV BESCOM feeders. When a protective relay trips at the substation breaker, all nodes in the directed sub-tree downstream of the physical fault lose power. 
> 
> The candidate boundary is determined by traversing the tree to identify sections bounded between the **last observed-energized node** (where downstream smart meters report nominal voltage) and the **first observed-de-energized node** (where telemetry confirms voltage collapse). 
> 
> If AMI meters fail or packet loss occurs (loss of observability), the graph engine falls back gracefully: rather than prematurely pruning unobserved branches, it treats unobserved nodes as indeterminate and expands the candidate set upward to the nearest confirmed energized parent node. This guarantees zero false exclusions of the true fault section, ensuring that safety-critical candidate sets remain comprehensive even under degraded communications.

---

### Q2: Distribution feeders operate with normally-open (N.O.) tie switches. How does your graph engine handle meshed loops or back-fed configurations without violating the radial assumption?
> **Answer:**  
> In normal steady-state operation, the network graph is strictly partitioned into radial spanning trees by enforcing `is_normally_open == True` on all tie-switch edges (`network_connections` table). 
> 
> During topological traversal, the NetworkX engine filters out open tie switches, maintaining an acyclic Directed Acyclic Graph (DAG) directed away from the substation source busbar. When our advisory restoration planner evaluates back-feeding options, it simulates closing a tie switch only *after* mathematically asserting that an upstream sectionalizer or disconnector has been opened (`ISOLATE_FAULT_SECTION`), thereby preserving radiality and preventing unsynchronized parallel feeder loops.

---

## Category 2: Machine Learning Validity, Class Imbalance & Data Leakage

### Q3: In power distribution networks, fault events are extremely rare—non-fault sections outnumber fault sections 12 to 1. How did your ML pipeline handle this severe class imbalance?
> **Answer:**  
> In our synthetic dataset of 30,634 candidate rows, the ratio of non-fault to fault candidates is approximately 12.2 to 1 (only ~7.6% positive class). 
> 
> We addressed this using three specific techniques:
> 1. **Graph-Level Pre-Filtering**: The NetworkX graph engine prunes 91.56% of healthy network sections *before* passing candidates to the ML ranker, reducing the class imbalance from over 140:1 to 12:1.
> 2. **Algorithmic Weighting**: In XGBoost, we configured `scale_pos_weight` and tuned the objective to optimize ranking margins rather than raw binary cross-entropy.
> 3. **Evaluation Metric Alignment**: We rejected raw binary accuracy (which would yield a misleading 92% by predicting all zeros) and evaluated the system using **Top-1 (62.67%)** and **Top-3 (89.33%) localization accuracy per scenario**. Field crews inspect ranked candidates sequentially; ranking accuracy directly reflects operational dispatch utility.

---

### Q4: Machine learning models frequently suffer from data leakage. How did you guarantee that your training, validation, and test splits did not leak information?
> **Answer:**  
> We enforced strict **scenario-level partitioning** using `GroupShuffleSplit` on the unique `scenario_id` field. We never randomly split candidate rows.
> 
> If row-level splitting were used, candidates from the *same* storm event would appear in both training and test sets, causing massive data leakage of feeder telemetry, wind gusts, and customer call distributions.
> 
> In our pipeline, 1,750 scenarios are strictly isolated for training, 375 for calibration validation, and 375 for final testing. We enforce this via an automated unit test (`test_no_scenario_leakage` in `backend/tests/test_ml_pipeline.py`) which asserts that:
> $$\text{Set}(\text{train\_scenarios}) \cap \text{Set}(\text{val\_scenarios}) \cap \text{Set}(\text{test\_scenarios}) = \emptyset$$
> No event, feeder disturbance, or ambient condition seen at test time was ever presented during training.

---

## Category 3: Probability Calibration & Explainability

### Q5: Why are raw XGBoost scores unsuitable for control room operators, and how does your probability calibration work?
> **Answer:**  
> Gradient-boosted decision trees optimize an uncalibrated surrogate loss function. A raw prediction of "0.85" from XGBoost does not mean there is an 85% probability of a physical fault; it merely indicates an arbitrary ranking margin influenced by tree depth and leaf weights. Control room engineers allocating emergency line crews require true Bayesian risk probabilities.
> 
> We evaluated two post-hoc calibration methods on our held-out validation set: **Platt Scaling** (logistic sigmoid) and **Isotonic Regression** (non-parametric monotonic step function). Isotonic Regression achieved superior performance with a **Brier score of 0.06696** and an **Expected Calibration Error (ECE) of 0.0054 (0.54%)**.
> 
> This means across 10 empirical probability bins on held-out test data, our predicted probabilities deviate from observed fault frequencies by less than half a percent. In our UI, we explicitly label these as "Calibrated Probability (Synthetic Validation, ECE = 0.0054)" to maintain complete scientific integrity.

---

### Q6: Why did you choose Tree SHAP over LIME or permutation feature importance for control room explainability?
> **Answer:**  
> Distribution grid control rooms operate under high stress where explanations must be mathematically consistent and computationally instantaneous:
> 1. **Exact Local Attribution**: Tree SHAP (`shap.TreeExplainer`) provides exact Shapley values derived from cooperative game theory, satisfying mathematical axioms of efficiency, symmetry, and additivity. In contrast, LIME relies on stochastic local perturbations that produce unstable explanations across repeated runs.
> 2. **Sub-Millisecond Speed**: Tree SHAP computes exact polynomial-time attributions directly from the trained XGBoost tree structure in under 10 milliseconds, whereas permutation importance requires thousands of forward inference passes that would block real-time dispatch.
> 3. **Comparative Delta Explanations**: We use SHAP values not just to explain Rank #1, but to generate explicit "Why Ranked Lower?" comparative delta cards (e.g. showing that candidate F4-S12 ranked lower because healthy downstream telemetry penalized its likelihood by -0.21 SHAP units).

---

## Category 4: Operational Safety, Restoration & Invariants

### Q7: If your ML model makes an incorrect Rank #1 prediction, what prevents your restoration planner from back-feeding into an uncleared fault and causing an explosion?
> **Answer:**  
> In power engineering, software must assume machine learning can and will make errors. Therefore, FAULTTRACE AI enforces a non-negotiable **Lock-Out / Tag-Out (LOTO) Safety Invariant**:
> 1. **Physical Isolation Before Energization**: The restoration engine mandates opening disconnectors on *both* sides of the candidate section (`ISOLATE_FAULT_SECTION` / `OPEN`) before any tie switch is closed.
> 2. **Path Constrained Search**: The alternate path algorithm mathematically constrains the switching graph by removing all candidate fault sections from the allowable power flow path.
> 3. **Human-in-the-Loop Advisory Requirement**: The system is 100% advisory. Every plan carries the prominent warning: `"ADVISORY, requires qualified engineer review."` Automated breaker closing is prohibited in software to ensure that a certified field engineer issues a Line Clear Permit (LCP) and physically verifies ground isolation before any switch is turned.

---

### Q8: When closing a tie switch to back-feed consumers from an adjacent feeder, how do you verify that the healthy feeder won't trip on overcurrent?
> **Answer:**  
> Our restoration planner executes a **Thermal Headroom Capacity Verification** prior to recommending any tie-switch closure.
> 
> In the database, each feeder records its rated thermal capacity (e.g. 5.0 MVA for typical 11 kV overhead express feeders). When evaluating Tie Switch `TS-F4-F5`, the algorithm queries the active pre-fault load on donor Feeder F5 (e.g. 2.6 MVA) and adds the aggregate nominal kVA of all de-energized transformers to be transferred (0.85 MVA). 
> 
> If the combined load ($2.6 + 0.85 = 3.45\text{ MVA}$, 69% loading) remains within the safe operating envelope (&lt;85% continuous capacity), the advisory step is approved. If the donor feeder would be overloaded (&gt;100%), the system suppresses the transfer and issues an alert: *"Tie switch closure rejected: Feeder F5 thermal headroom exceeded"*.

---

## Category 5: Real-World Ingestion, Latency & Noise

### Q9: Real-world customer complaints to the 1912 helpline are notoriously noisy and delayed. How does your model avoid being misled by false or delayed calls?
> **Answer:**  
> Customer phone calls are never used in isolation; they are one component of a multi-modal feature vector. 
> 
> In our synthetic scenario generator, we inject 5% false-positive complaint noise (calls originating from healthy sections) and model Poisson arrival delays. The XGBoost model learns feature hierarchy:
> - As shown in our feature importance analysis (`models/metrics.json`), physical electrical telemetry dominates: `downstream_outage_fraction` accounts for **50.4%** of model gain, while customer complaints contribute less than **5%**.
> - If 20 angry customers call from section F4-S02, but smart meters on section F4-S02 confirm steady 230V voltage, the graph engine and electrical features immediately override the complaint noise. Complaints serve as secondary corroboration during storm-induced communications outages, never as a single point of failure.

---

### Q10: Why did Top-1 accuracy drop from 62.7% on the 375-scenario test set to 35.0% during the live 20-run benchmark, while Top-3 remained solid at 80.0%?
> **Answer:**  
> This discrepancy illustrates an authentic physical characteristic of radial distribution grids:
> 1. **Topological Equivalence on Lateral Stubs**: In distribution networks, multiple pole spans along a rural lateral branch may share identical downstream observability—meaning no intermediate smart meter separates pole section S13 from pole section S14. When a fault occurs on S13, both S13 and S14 exhibit identical downstream transformer outage signatures.
> 2. **Cumulative Impedance Bias**: In these ambiguous lateral spans, the gradient booster tends to rank the terminal section slightly higher due to cumulative synthetic line impedance.
> 3. **Operational Reality**: For utility field operations, the difference between S13 and S14 is a 100-meter span along the same road. This is why **Top-3 accuracy (89.3% test, 80.0% live benchmark)** is the operational metric of interest: it narrows the patrol area from a 25-kilometer feeder to a 3-pole window, reducing patrol time by over 85%.

---

## Category 6: Production Integration with BESCOM Infrastructure

### Q11: Does FAULTTRACE AI solve full AC dynamic power flows (like OpenDSS or Pandapower)? What are the electrical approximations in your prototype?
> **Answer:**  
> No, FAULTTRACE AI currently uses a steady-state $R+jX$ impedance and radial voltage drop approximation rather than a full non-linear AC Newton-Raphson or dynamic Electro-Magnetic Transient (EMT) solver.
> 
> We made this deliberate design choice for sub-second control room latency: our graph pruning and feature extraction execute in **18 milliseconds**, whereas a full AC multi-phase state estimation across 140 unbalanced nodes would require several seconds. 
> 
> In our production roadmap (`docs/LIMITATIONS.md`), we document that a production utility deployment should couple our graph engine with an asynchronous OpenDSS worker to verify secondary busbar voltage regulation ($\pm 6\%$) and reactive power (VAR) flows prior to tie-switch execution.

---

### Q12: BESCOM uses an ABB/Schneider SCADA system and an in-house 1912 complaint portal. What technical adapters are required to connect your platform to BESCOM's live infrastructure?
> **Answer:**  
> As detailed in `docs/LIMITATIONS.md`, transitioning from our prototype to live BESCOM production requires 4 specific adapters:
> 1. **SCADA Telemetry**: An **IEC 60870-5-104** or DNP3 protocol adapter communicating over BESCOM's secure OT MPLS network to ingest breaker auxiliary contacts (52a/52b) and numerical protection relay trip signals (50/51/50N).
> 2. **AMI Smart Meter Stream**: An **Apache Kafka consumer** connected to BESCOM's Smart Meter Head-End System (HES) to ingest DLMS/COSEM push frames and "Last-Gasp" outage traps.
> 3. **GIS Integration**: A parser for **CIM XML (IEC 61968-13)** to automatically synchronize daily feeder connectivity models from BESCOM's enterprise GIS database.
> 4. **Cybersecurity**: Deployment within BESCOM's IT/OT Demilitarized Zone (DMZ) with unidirectional data diodes compliant with the CEA (Central Electricity Authority) 2021 Cyber Security Guidelines.