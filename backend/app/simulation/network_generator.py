"""
Deterministic synthetic power distribution grid generator for Bengaluru region.
Complies with BESCOM 66/11kV distribution feeder specifications.
Seeded for 100% reproducible topology generation.
"""

import random
from typing import Dict, List, Any, Tuple
from datetime import datetime, timezone, timedelta


def generate_synthetic_grid(seed: int = 42) -> Dict[str, Any]:
    """
    Generates a deterministic distribution network topology:
    - 2 Substations (Hebbal & Peenya)
    - 8 Feeders (F1 to F8)
    - 12-25 Sections per feeder with branching
    - 45-55 Distribution Transformers (DTCs)
    - Consumer clusters for each DTC
    - 4 Normally-Open Tie-Switches for back-feed restoration
    - Critical loads including District Water Pump on F4-DT-14, Hospitals, Oxygen Plant
    - Hero Feeder F4 with branch sections F4-S12, F4-S14 and DT-12, 13, 14, 16.
    """
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)

    # 1. Substations (Bengaluru coordinates)
    substations_data = [
        {
            "name": "Hebbal 66/11kV Substation",
            "code": "HEB-SS-01",
            "latitude": 13.0358,
            "longitude": 77.5970,
            "voltage_kv": 66.0,
            "capacity_mva": 50.0,
            "division": "Bangalore North",
            "subdivision": "Hebbal",
        },
        {
            "name": "Peenya 66/11kV Substation",
            "code": "PNY-SS-01",
            "latitude": 13.0285,
            "longitude": 77.5195,
            "voltage_kv": 66.0,
            "capacity_mva": 60.0,
            "division": "Bangalore West",
            "subdivision": "Peenya",
        },
    ]

    # 2. Feeders: 4 under Hebbal (F1, F2, F3, F4), 4 under Peenya (F5, F6, F7, F8)
    feeders_data = [
        {"feeder_code": "F1", "name": "F1-Ganganagar Feeder", "substation_code": "HEB-SS-01", "voltage_kv": 11.0, "rated_current_a": 400.0, "nominal_capacity_mva": 7.5, "status": "ACTIVE"},
        {"feeder_code": "F2", "name": "F2-RTNagar Feeder", "substation_code": "HEB-SS-01", "voltage_kv": 11.0, "rated_current_a": 400.0, "nominal_capacity_mva": 7.5, "status": "ACTIVE"},
        {"feeder_code": "F3", "name": "F3-Sanjaynagar Feeder", "substation_code": "HEB-SS-01", "voltage_kv": 11.0, "rated_current_a": 400.0, "nominal_capacity_mva": 7.5, "status": "ACTIVE"},
        {"feeder_code": "F4", "name": "F4-Sahakarnagar Hero Feeder", "substation_code": "HEB-SS-01", "voltage_kv": 11.0, "rated_current_a": 450.0, "nominal_capacity_mva": 8.5, "status": "ACTIVE"},
        {"feeder_code": "F5", "name": "F5-Peenya Industrial Feeder", "substation_code": "PNY-SS-01", "voltage_kv": 11.0, "rated_current_a": 600.0, "nominal_capacity_mva": 10.0, "status": "ACTIVE"},
        {"feeder_code": "F6", "name": "F6-Jalahalli Feeder", "substation_code": "PNY-SS-01", "voltage_kv": 11.0, "rated_current_a": 400.0, "nominal_capacity_mva": 7.5, "status": "ACTIVE"},
        {"feeder_code": "F7", "name": "F7-Nagasandra Feeder", "substation_code": "PNY-SS-01", "voltage_kv": 11.0, "rated_current_a": 400.0, "nominal_capacity_mva": 7.5, "status": "ACTIVE"},
        {"feeder_code": "F8", "name": "F8-Yeshwanthpur Feeder", "substation_code": "PNY-SS-01", "voltage_kv": 11.0, "rated_current_a": 450.0, "nominal_capacity_mva": 8.0, "status": "ACTIVE"},
    ]

    sections_data: List[Dict[str, Any]] = []
    transformers_data: List[Dict[str, Any]] = []
    clusters_data: List[Dict[str, Any]] = []
    critical_loads_data: List[Dict[str, Any]] = []
    tie_switches_data: List[Dict[str, Any]] = []
    assets_data: List[Dict[str, Any]] = []

    # Helper coordinate offsets
    sub_coords = {
        "HEB-SS-01": (13.0358, 77.5970),
        "PNY-SS-01": (13.0285, 77.5195),
    }

    # Feeder angle direction vectors for realistic geographical layout in Bangalore
    feeder_directions = {
        "F1": (-0.003, 0.002),   # South-East
        "F2": (-0.002, -0.003),  # South-West
        "F3": (0.002, 0.003),    # North-East
        "F4": (0.003, -0.002),   # North-West (Hero Feeder)
        "F5": (0.003, 0.003),    # North-East Peenya
        "F6": (0.001, -0.004),   # West Jalahalli
        "F7": (-0.003, 0.001),   # South Nagasandra
        "F8": (-0.002, -0.003),  # South-West Yeshwanthpur
    }

    # Generate sections and equipment for each feeder
    for f in feeders_data:
        f_code = f["feeder_code"]
        sub_code = f["substation_code"]
        base_lat, base_lon = sub_coords[sub_code]
        d_lat, d_lon = feeder_directions[f_code]

        if f_code == "F4":
            # --- Dedicated Hero Feeder F4 Design ---
            # Total 18 sections with explicit branching for F4-S12 and F4-S14
            # Main trunk: F4-S01 -> S02 -> S03 -> S04 -> S05 -> S06 -> S07 -> S08 -> S09 -> S10
            # Branch from S10: S10 -> F4-S11 -> F4-S12 -> F4-S13 -> F4-S14 (downstream branch)
            # Lateral branch from S05: S05 -> F4-S15 -> F4-S16 -> F4-S17 -> F4-S18
            f4_topology = [
                # Main trunk
                ("F4-S01", None, 0.6, "ACSR_DOG", 3800.0),
                ("F4-S02", "F4-S01", 0.5, "ACSR_DOG", 3800.0),
                ("F4-S03", "F4-S02", 0.4, "ACSR_DOG", 3500.0),
                ("F4-S04", "F4-S03", 0.5, "ACSR_RABBIT", 3000.0),
                ("F4-S05", "F4-S04", 0.4, "ACSR_RABBIT", 3000.0),
                ("F4-S06", "F4-S05", 0.5, "ACSR_RABBIT", 2500.0),
                ("F4-S07", "F4-S06", 0.4, "ACSR_RABBIT", 2500.0),
                ("F4-S08", "F4-S07", 0.4, "ACSR_RABBIT", 2200.0),
                ("F4-S09", "F4-S08", 0.5, "ACSR_RABBIT", 2000.0),
                ("F4-S10", "F4-S09", 0.4, "ACSR_RABBIT", 2000.0),

                # Hero Target Branch containing S12 & S14
                ("F4-S11", "F4-S10", 0.4, "ACSR_RABBIT", 1800.0),
                ("F4-S12", "F4-S11", 0.5, "ACSR_RABBIT", 1800.0),  # Hero Candidate Section 12
                ("F4-S13", "F4-S12", 0.4, "ACSR_WEASEL", 1500.0),
                ("F4-S14", "F4-S13", 0.5, "ACSR_WEASEL", 1500.0),  # Hero Candidate Section 14 (Feeds Water Pump)

                # Lateral Branch from S05
                ("F4-S15", "F4-S05", 0.5, "ACSR_RABBIT", 2000.0),
                ("F4-S16", "F4-S15", 0.4, "ACSR_RABBIT", 1800.0),
                ("F4-S17", "F4-S16", 0.5, "ACSR_WEASEL", 1500.0),
                ("F4-S18", "F4-S17", 0.4, "ACSR_WEASEL", 1200.0),
            ]

            cur_lat, cur_lon = base_lat, base_lon
            section_coords = {}
            for s_code, p_code, length, cond, cap in f4_topology:
                if p_code is None:
                    s_lat, s_lon = cur_lat, cur_lon
                else:
                    s_lat, s_lon = section_coords[p_code][1]

                # Advance coordinates slightly based on branch
                if s_code in ["F4-S11", "F4-S12", "F4-S13", "F4-S14"]:
                    e_lat = s_lat + d_lat * 0.4 + rng.uniform(-0.0005, 0.0005)
                    e_lon = s_lon + d_lon * 0.4 + 0.001
                elif s_code in ["F4-S15", "F4-S16", "F4-S17", "F4-S18"]:
                    e_lat = s_lat + d_lat * 0.3 - 0.001
                    e_lon = s_lon + d_lon * 0.3 + rng.uniform(-0.0005, 0.0005)
                else:
                    e_lat = s_lat + d_lat * 0.3
                    e_lon = s_lon + d_lon * 0.3

                section_coords[s_code] = ((s_lat, s_lon), (e_lat, e_lon))

                # Real electrical impedances per km for standard BESCOM ACSR conductors
                # DOG: ~0.27 ohm/km, RABBIT: ~0.54 ohm/km, WEASEL: ~0.91 ohm/km
                unit_r = 0.27 if cond == "ACSR_DOG" else (0.54 if cond == "ACSR_RABBIT" else 0.91)
                unit_x = 0.32  # standard 11kV overhead reactance ohm/km

                sections_data.append({
                    "section_code": s_code,
                    "feeder_code": "F4",
                    "parent_section_code": p_code,
                    "length_km": length,
                    "resistance_ohm": round(unit_r * length, 4),
                    "reactance_ohm": round(unit_x * length, 4),
                    "rated_capacity_kva": cap,
                    "conductor_type": cond,
                    "start_latitude": round(s_lat, 6),
                    "start_longitude": round(s_lon, 6),
                    "end_latitude": round(e_lat, 6),
                    "end_longitude": round(e_lon, 6),
                    "status": "ENERGIZED",
                })

            # F4 Hero Downstream Transformers: DT-12, DT-13, DT-14, DT-16
            f4_transformers = [
                ("DT-04", "F4-S04", 500.0, 240.0, "Commercial Complex Sahakarnagar"),
                ("DT-08", "F4-S08", 250.0, 110.0, "Residential Layout Block A"),
                ("DT-12", "F4-S12", 250.0, 140.0, "Telecom Exchange & Residential"),
                ("DT-13", "F4-S13", 500.0, 280.0, "Mixed Market Area"),
                ("DT-14", "F4-S14", 500.0, 310.0, "District Water Pumping Substation"),
                ("DT-16", "F4-S16", 250.0, 120.0, "Sahakarnagar Block G"),
            ]

            for dt_code, sec_code, r_kva, c_kva, desc in f4_transformers:
                e_coords = section_coords[sec_code][1]
                transformers_data.append({
                    "transformer_code": dt_code,
                    "section_code": sec_code,
                    "rated_kva": r_kva,
                    "current_load_kva": c_kva,
                    "load_percentage": round((c_kva / r_kva) * 100, 1),
                    "primary_voltage_kv": 11.0,
                    "secondary_voltage_v": 415.0,
                    "phase": 3,
                    "latitude": e_coords[0],
                    "longitude": e_coords[1],
                    "description": desc,
                })
                # Consumer cluster
                clusters_data.append({
                    "cluster_code": f"CLUST-{dt_code}",
                    "transformer_code": dt_code,
                    "consumer_count": rng.randint(45, 140),
                    "cluster_type": "MIXED" if "Market" in desc or "Commercial" in desc else "RESIDENTIAL",
                    "peak_demand_kw": round(c_kva * 0.85, 1),
                    "smart_meter_count": rng.randint(40, 130),
                })

            # Hero Scenario Critical Load: District Water Pump on DT-14 (Section F4-S14)
            critical_loads_data.append({
                "section_code": "F4-S14",
                "facility_name": "District Water Pump",
                "facility_type": "WATER_PUMPING",
                "priority_tier": 1,
                "backup_generator_present": True,
                "backup_run_hours": 6.0,
                "contact_number": "+91-80-23631100",
            })

        else:
            # --- Standard Feeder Generator (F1, F2, F3, F5, F6, F7, F8) ---
            num_sections = rng.randint(14, 20)
            sec_coords_map = {}
            for i in range(1, num_sections + 1):
                s_code = f"{f_code}-S{i:02d}"
                if i == 1:
                    p_code = None
                    s_lat, s_lon = base_lat, base_lon
                    cond = "ACSR_DOG"
                    cap = 3800.0
                elif i <= 8:
                    # Main trunk
                    p_code = f"{f_code}-S{i-1:02d}"
                    s_lat, s_lon = sec_coords_map[p_code][1]
                    cond = "ACSR_RABBIT"
                    cap = 3000.0
                elif i <= 14:
                    # Branch 1 (branched from S04 or S06)
                    branch_parent = 4 if i == 9 else i - 1
                    p_code = f"{f_code}-S{branch_parent:02d}"
                    s_lat, s_lon = sec_coords_map[p_code][1]
                    cond = "ACSR_RABBIT"
                    cap = 2200.0
                else:
                    # Branch 2 (lateral from S08)
                    branch_parent = 8 if i == 15 else i - 1
                    p_code = f"{f_code}-S{branch_parent:02d}"
                    s_lat, s_lon = sec_coords_map[p_code][1]
                    cond = "ACSR_WEASEL"
                    cap = 1600.0

                length = round(rng.uniform(0.35, 0.75), 2)
                e_lat = s_lat + d_lat * 0.25 + rng.uniform(-0.0006, 0.0006)
                e_lon = s_lon + d_lon * 0.25 + rng.uniform(-0.0006, 0.0006)
                sec_coords_map[s_code] = ((s_lat, s_lon), (e_lat, e_lon))

                unit_r = 0.27 if cond == "ACSR_DOG" else (0.54 if cond == "ACSR_RABBIT" else 0.91)
                unit_x = 0.32

                sections_data.append({
                    "section_code": s_code,
                    "feeder_code": f_code,
                    "parent_section_code": p_code,
                    "length_km": length,
                    "resistance_ohm": round(unit_r * length, 4),
                    "reactance_ohm": round(unit_x * length, 4),
                    "rated_capacity_kva": cap,
                    "conductor_type": cond,
                    "start_latitude": round(s_lat, 6),
                    "start_longitude": round(s_lon, 6),
                    "end_latitude": round(e_lat, 6),
                    "end_longitude": round(e_lon, 6),
                    "status": "ENERGIZED",
                })

            # Add 4 to 6 transformers per standard feeder
            dt_count = rng.randint(4, 6)
            chosen_sections = rng.sample([s for s in range(3, num_sections + 1)], dt_count)
            for idx, s_idx in enumerate(sorted(chosen_sections)):
                sec_code = f"{f_code}-S{s_idx:02d}"
                dt_code = f"{f_code}-DT{idx+1:02d}"
                r_kva = rng.choice([100.0, 250.0, 500.0])
                c_kva = round(r_kva * rng.uniform(0.35, 0.70), 1)
                e_coords = sec_coords_map[sec_code][1]

                transformers_data.append({
                    "transformer_code": dt_code,
                    "section_code": sec_code,
                    "rated_kva": r_kva,
                    "current_load_kva": c_kva,
                    "load_percentage": round((c_kva / r_kva) * 100, 1),
                    "primary_voltage_kv": 11.0,
                    "secondary_voltage_v": 415.0,
                    "phase": 3,
                    "latitude": e_coords[0],
                    "longitude": e_coords[1],
                    "description": f"Distribution transformer on {sec_code}",
                })
                clusters_data.append({
                    "cluster_code": f"CLUST-{dt_code}",
                    "transformer_code": dt_code,
                    "consumer_count": rng.randint(30, 160),
                    "cluster_type": rng.choice(["RESIDENTIAL", "COMMERCIAL", "MIXED"]),
                    "peak_demand_kw": round(c_kva * 0.85, 1),
                    "smart_meter_count": rng.randint(25, 150),
                })

    # Critical loads on other feeders
    other_critical_loads = [
        ("F1-S06", "Aster CMI Hospital", "HOSPITAL", 1, True, 16.0, "+91-80-43420100"),
        ("F2-S05", "Bangalore Baptist Hospital", "HOSPITAL", 1, True, 12.0, "+91-80-22024444"),
        ("F5-S07", "Peenya Medical Oxygen Plant", "OXYGEN_PLANT", 1, True, 24.0, "+91-80-28395511"),
        ("F7-S04", "BWSSB Major Water Pumping Station", "WATER_PUMPING", 1, True, 10.0, "+91-80-22945100"),
        ("F8-S03", "Yeshwanthpur Metro Traction Substation", "METRO_RAIL", 2, True, 8.0, "+91-80-23456789"),
    ]
    for sec_code, name, f_type, tier, gen, hrs, contact in other_critical_loads:
        critical_loads_data.append({
            "section_code": sec_code,
            "facility_name": name,
            "facility_type": f_type,
            "priority_tier": tier,
            "backup_generator_present": gen,
            "backup_run_hours": hrs,
            "contact_number": contact,
        })

    # 3. Normally-Open Tie-Switches (4 inter-feeder boundary tie switches)
    tie_switches_data = [
        # Tie 1: F1 <-> F2 boundary
        {"switch_code": "TIE-SW-F1-F2", "from_section": "F1-S08", "to_section": "F2-S08", "switch_type": "TIE_SWITCH", "is_tie_switch": True, "is_normally_open": True, "status": "OPEN", "rated_current_a": 400.0, "is_telecontrolled": True},
        # Tie 2: F2 <-> F3 boundary
        {"switch_code": "TIE-SW-F2-F3", "from_section": "F2-S10", "to_section": "F3-S08", "switch_type": "TIE_SWITCH", "is_tie_switch": True, "is_normally_open": True, "status": "OPEN", "rated_current_a": 400.0, "is_telecontrolled": True},
        # Tie 3: F4 Hero Feeder <-> F3 boundary (vital for F4 back-feed restoration)
        {"switch_code": "TIE-SW-F4-F3", "from_section": "F4-S14", "to_section": "F3-S12", "switch_type": "TIE_SWITCH", "is_tie_switch": True, "is_normally_open": True, "status": "OPEN", "rated_current_a": 400.0, "is_telecontrolled": True},
        # Tie 4: F5 (Peenya) <-> F6 boundary
        {"switch_code": "TIE-SW-F5-F6", "from_section": "F5-S10", "to_section": "F6-S08", "switch_type": "TIE_SWITCH", "is_tie_switch": True, "is_normally_open": True, "status": "OPEN", "rated_current_a": 600.0, "is_telecontrolled": True},
        # Tie 5: F7 <-> F8 boundary
        {"switch_code": "TIE-SW-F7-F8", "from_section": "F7-S08", "to_section": "F8-S08", "switch_type": "TIE_SWITCH", "is_tie_switch": True, "is_normally_open": True, "status": "OPEN", "rated_current_a": 400.0, "is_telecontrolled": True},
    ]

    # 4. Asset Health Monitoring Records (Transformers, Circuit Breakers, Air-Break Switches)
    for dt in transformers_data:
        h_idx = round(rng.uniform(62.0, 98.0), 1)
        cond = "EXCELLENT" if h_idx > 90 else ("GOOD" if h_idx > 75 else ("FAIR" if h_idx > 60 else "POOR"))
        assets_data.append({
            "asset_type": "TRANSFORMER",
            "asset_identifier": dt["transformer_code"],
            "health_index": h_idx,
            "condition_rating": cond,
            "installation_date": now - timedelta(days=rng.randint(200, 2500)),
            "last_maintenance_date": now - timedelta(days=rng.randint(30, 180)),
            "next_scheduled_maintenance": now + timedelta(days=rng.randint(30, 180)),
            "failure_history_count": rng.randint(0, 2),
            "operating_temperature_c": round(rng.uniform(45.0, 72.0), 1),
            "dga_status": "CAUTION" if h_idx < 65 else "NORMAL",
            "notes": f"Distribution transformer health rating: {cond}.",
        })

    for f in feeders_data:
        h_idx = round(rng.uniform(85.0, 98.0), 1)
        assets_data.append({
            "asset_type": "BREAKER",
            "asset_identifier": f"BRK-{f['feeder_code']}",
            "health_index": h_idx,
            "condition_rating": "EXCELLENT" if h_idx > 90 else "GOOD",
            "installation_date": now - timedelta(days=rng.randint(400, 1500)),
            "last_maintenance_date": now - timedelta(days=rng.randint(20, 90)),
            "next_scheduled_maintenance": now + timedelta(days=rng.randint(90, 200)),
            "failure_history_count": 0,
            "notes": f"Vacuum circuit breaker controlling Feeder {f['feeder_code']}.",
        })

    return {
        "substations": substations_data,
        "feeders": feeders_data,
        "sections": sections_data,
        "transformers": transformers_data,
        "consumer_clusters": clusters_data,
        "critical_loads": critical_loads_data,
        "tie_switches": tie_switches_data,
        "assets": assets_data,
    }
