# FAULTTRACE AI: 5-Minute Pitch & Control Room Demo Walkthrough

**BESCOM Power Hack 2026 — Theme 10**  
**Platform**: FAULTTRACE AI (Distribution Grid Fault Localization & Advisory Restoration)  
**Presenter**: Control Room Operations & AI Systems Lead  
**Target Duration**: Exactly 5 minutes (with 3 live backup scenarios)

---

## ⏱️ Master Timing Schedule

```
+---------------+-----------------------------------------------+-----------------------+
| Time          | Segment                                       | Page / Action         |
+---------------+-----------------------------------------------+-----------------------+
| 0:00 - 0:45   | 1. The Challenge & Control Room Overview      | Dashboard (/)         |
| 0:45 - 1:45   | 2. Storm Event Trigger & Event Correlation    | Simulation (/simulate)|
| 1:45 - 2:45   | 3. Topological Search Space Pruning           | Network Map (/map)    |
| 2:45 - 3:45   | 4. ML Ranking, Calibration & Tree SHAP        | Incident (/incidents) |
| 3:45 - 4:30   | 5. Advisory Restoration & Safety Invariants   | Restoration Tab       |
| 4:30 - 5:00   | 6. Empirical Model Evaluation & Conclusion    | Model Page (/model)   |
+---------------+-----------------------------------------------+-----------------------+
```

---

## 🎬 5-Minute Step-by-Step Demo Script

### Segment 1: The Challenge & Control Room Overview (0:00 - 0:45)
- **Starting Screen**: `http://localhost:5173/` (Dashboard)
- **UI State**: Clean dashboard showing active grid telemetry, healthy feeder statuses, and 0 active critical alarms.
- **Presenter Action**: Hover cursor across the KPI cards (Total Substations: 2, Active Feeders: 8, Transformers: 48, Critical Loads: 3).

> **Presenter Script:**  
> *"Good morning, respected judges. In an urban distribution network like BESCOM's Bengaluru grid, monsoon storms trigger cascading outages across hundreds of kilometers of 11 kV overhead feeders. When a tree falls across a conductor, control room engineers are hit with a storm of information: breaker trip alarms, delayed customer calls to the 1912 helpline, and missing smart meter pings. Today, locating that fault section often takes field patrol crews 2 to 4 hours on foot.*  
>  
> *Welcome to FAULTTRACE AI. On this dashboard, you are seeing a live control-room digital twin of 8 BESCOM distribution feeders. Our goal is simple: reduce that 2-hour search to under 200 milliseconds, localize the exact fault section, and generate an electrically safe, advisory restoration plan."*

---

### Segment 2: Storm Event Trigger & Ingestion (0:45 - 1:45)
- **Screen**: Navigate to `Simulation & Ingestion` via sidebar (`/simulate`).
- **Presenter Action**:
  1. Point out the live Open-Meteo weather widget in the top header (showing current temperature and wind gust telemetry).
  2. Scroll down to the **"Preset Scenarios"** panel.
  3. Click the orange button: **"Run Feeder F4 Hero Scenario"**.
- **Visual Cue**: A loading spinner appears for ~200ms. A success banner flashes: *"Incident INC-2026-F4-HERO generated! 142 complaints ingested, 4 downstream DT outages correlated, fault candidate ranked."*
- **Presenter Action**: Click the blue text link in the toast banner: **"View Incident INC-2026-F4-HERO &rarr;"**.

> **Presenter Script:**  
> *"Let's simulate a real-world pre-monsoon storm hitting North Bengaluru. I am triggering our Hero Scenario on Feeder F4.  
>  
> In one single click, three multi-modal streams flood our ingestion pipeline:  
> 1. A SCADA breaker trip alarm on Feeder F4 at Substation North-01.  
> 2. Zero-voltage AMI smart meter telemetry from 4 downstream distribution transformers.  
> 3. 142 urgent customer outage complaints logged across consumer clusters, accompanied by 48 km/h wind gusts.  
>  
> Notice our 15-minute rolling correlator: rather than treating these as 146 isolated alarms, FAULTTRACE AI automatically groups them into one unified operational incident. Let's inspect the network map."*

---

### Segment 3: Topological Pruning on the GIS Map (1:45 - 2:45)
- **Screen**: Navigate to `Network Map` (`/map`).
- **Presenter Action**:
  1. Filter the feeder dropdown to **"F4 - Peenya Industrial / Residential"**.
  2. Point to the glowing red polyline branch and orange transformer icons.
  3. Click on the fault boundary section `F4-S14`.
- **Visual Cue**: The modal popup opens showing:
  - Section Code: `F4-S14`
  - Status: `DE-ENERGIZED (Candidate Fault Section)`
  - Downstream DTs: `DT-12, DT-13, DT-14, DT-16`
  - Critical Load: `District Water Pumping Station (DT-14)`
  - Upstream Status: `F4-S01 through F4-S12 (ENERGIZED / NORMAL)`

> **Presenter Script:**  
> *"This is the power of our NetworkX graph engine. Before running any machine learning, we apply deterministic electrical topology pruning. Feeder F4 has 18 sections, and the entire grid has 140 sections.  
>  
> Look at the blue sections upstream: because transformers on sections F4-S01 through F4-S12 reported healthy 230V telemetry, our graph engine mathematically proves the fault cannot be upstream of section S12. In less than 15 milliseconds, the graph engine prunes 91.43% of the search space, isolating just 12 topology-consistent candidate sections.  
>  
> We never feed raw, un-pruned networks into an AI black box. Physics and graph topology always lead first."*

---

### Segment 4: ML Ranking, Calibration & Tree SHAP Attribution (2:45 - 3:45)
- **Screen**: Navigate to `Incidents` (`/incidents`) and click into the active `INC-2026-F4-HERO`.
- **Presenter Action**:
  1. Scroll to the **"Ranked Candidate Sections"** table.
  2. Highlight the two column headers: **"Model Score"** vs. **"Calibrated Probability"**.
  3. Click on **Rank #1: F4-S14**.
  4. Scroll to the **"Tree SHAP Feature Attribution"** horizontal bar chart.
- **Visual Cue**:
  - `F4-S14`: Model Score `0.8421` | Calibrated Probability `0.7814`
  - SHAP Bar Chart highlights positive bars in red: `voltage_deviation (+0.312)`, `complaint_density (+0.245)`, `downstream_dt_outage_frac (+0.188)`, `wind_gust_kmh (+0.089)`.
  - "Why Ranked Lower?" card for `F4-S12`: shows negative delta due to healthy upstream voltage.

> **Presenter Script:**  
> *"Now the pruned candidates reach our XGBoost ranking model. Notice an essential engineering distinction that sets FAULTTRACE AI apart: we show both the raw Model Score (0.842) and the Calibrated Probability (0.781). A raw machine learning score is not a probability! We use Isotonic Regression fitted on held-out validation scenarios, achieving an Expected Calibration Error of just 0.0054. When our screen says 78%, an operator can trust that 78 out of 100 times, the physical conductor damage is right here.  
>  
> But control room operators will never trust a black box. Look at the Tree SHAP explanation: our AI explicitly reveals that voltage deviation (+0.31) and localized customer complaint surge (+0.25) under 48 km/h wind gusts are the decisive features driving F4-S14 to Rank #1. For lower-ranked sections, it explicitly shows why they were demoted due to contradictory healthy voltage reports."*

---

### Segment 5: Critical Asset Impact & Advisory Restoration (3:45 - 4:30)
- **Screen**: Scroll down to the **"Restoration Plan"** tab on the Incident page (or `/restoration`).
- **Presenter Action**:
  1. Gesture to the bright yellow striped banner: **"ADVISORY, REQUIRES QUALIFIED ENGINEER REVIEW"**.
  2. Walk through the 3 sequential switching steps:
     - Step 1: `ISOLATE_FAULT_SECTION` (Lock-Out / Tag-Out `F4-S14`)
     - Step 2: `OPEN_UPSTREAM_DISCONNECTOR` (Isolate `F4-S13` to `F4-S14`)
     - Step 3: `CLOSE_TIE_SWITCH` (Close `TS-F4-F5` to back-feed healthy lateral from Feeder F5).
  3. Point to the **Headroom Capacity Check**: Feeder F5 capacity = 5.0 MVA, current load = 2.6 MVA, transfer load = 0.85 MVA, post-switch loading = 69% (**SAFE**).

> **Presenter Script:**  
> *"Locating the fault is only half the battle. Downstream of section F4-S14 sits Transformer DT-14, powering the District Water Pumping Station—a lifeline utility for 1,240 households.  
>  
> Notice this prominent safety banner: FAULTTRACE AI is strictly advisory. In distribution systems, autonomous breaker closure can kill linemen. We enforce a zero-violation safety invariant: the candidate fault section F4-S14 is strictly locked out and tagged out. Power is NEVER routed into the fault.  
>  
> Instead, our graph engine searches for alternate paths and identifies Tie Switch TS-F4-F5. It verifies that healthy Feeder F5 has 2.4 MVA of spare headroom, and instructs the operator to back-feed the water pumping station in under 10 minutes. The critical pump is saved while line crews repair the damaged branch."*

---

### Segment 6: Model Metrics Transparency & Conclusion (4:30 - 5:00)
- **Screen**: Navigate to `Model Evaluation` (`/model`).
- **Presenter Action**:
  1. Highlight the Confusion Matrix: `True Negatives: 4186, False Positives: 16, False Negatives: 347, True Positives: 28`.
  2. Point to the Top-1 Accuracy (`62.67%`) and Top-3 Localization Accuracy (`89.33%`).
  3. Conclude facing the judges.

> **Presenter Script:**  
> *"Finally, we believe in radical transparency. We do not claim 99.9% accuracy on a marketing slide. On our held-out test split of 375 realistic scenarios with severe class imbalance, our Top-1 accuracy is 62.7%, and our Top-3 accuracy is 89.33% with an inference latency of 38 microseconds. For field utility crews, isolating the fault to a 3-pole window turns a 4-hour patrol into a 15-minute targeted fix.  
>  
> FAULTTRACE AI combines deterministic graph theory, calibrated gradient boosting, and safety-locked advisory restoration to make BESCOM's grid faster, safer, and resilient. Thank you, and we welcome your questions!"*

---

## 🛡️ 3 Live Backup Scenarios (Ready on Demand)

If a judge asks: *"Can your system handle other feeders, different fault types, or randomized storm events?"*, execute one of these backup workflows:

### Backup Scenario 1: Feeder F1 Heavy Industrial Trunk Trip
- **Context**: Main overhead trunk fault on Feeder F1 (`F1-S03`), affecting heavy commercial loads.
- **How to Trigger**:
  1. Go to `/simulate`.
  2. Select **"Random Scenario Simulation"**.
  3. Set Feeder: `F1`, Complaints: `85`, Wind: `35 km/h`. Click **"Simulate Scenario"**.
- **Key Talking Points**:
  - Trunk faults cause widespread downstream de-energization across 10+ transformers.
  - Graph engine isolates the fault to the first 3 sections near the substation breaker.
  - Tie Switch `TS-F1-F2` is evaluated; system warns if Feeder F2 is near peak capacity (&gt;85% loading) before advisory transfer.

### Backup Scenario 2: Feeder F5 Hospital Feeder Fault
- **Context**: Conductor break on Feeder F5 near `DT-22`, which directly feeds **City General Hospital**.
- **How to Trigger**:
  1. In Swagger UI (`http://localhost:8000/docs`) or via Simulation page, post custom scenario:
     ```json
     {
       "scenario_type": "random",
       "feeder_code": "F5",
       "complaint_count": 110,
       "wind_speed_kmh": 42.0
     }
     ```
- **Key Talking Points**:
  - The Critical Load badge triggers priority restoration ranking.
  - The system highlights the hospital's downstream status in red.
  - Restoration scheduler prioritizes backup tie-switch `TS-F4-F5` or `TS-F5-F6` within Step 1 to restore medical oxygen and ICU power supplies within minutes.

### Backup Scenario 3: Real CSV Ingestion & Malformed Data Handling
- **Context**: Judge asks: *"What happens when actual field SCADA telemetry or invalid CSV files are ingested?"*
- **How to Trigger**:
  1. Go to `/simulate` &rarr; **"Operational Data Ingestion"**.
  2. Select dataset type: **"Breaker Trips"** or **"Voltage Readings"**.
  3. Upload `datasets/synthetic/sample_voltage_readings.csv`.
  4. Instant feedback: 6 readings validated and stored in UTC.
  5. Next, upload an invalid file (e.g. empty file or corrupt headers) &rarr; show immediate HTTP 422 validation response in UI with clean error explanation without crashing.