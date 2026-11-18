"""
Data Ingestion API Router.
Handles CSV uploads for breaker trips, voltage readings, customer complaints,
DT status updates, weather observations, and asset records.
Performs Pydantic validation (returns clear 422 on malformed input),
normalizes timestamps to UTC, resolves foreign identifiers, and persists records.
"""

import io
import csv
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
import backend.app.models as m
import backend.app.schemas as s
from backend.app.services.correlator import EventCorrelatorService

router = APIRouter(prefix="/ingest", tags=["Data Ingestion"])


def parse_utc_timestamp(val: str) -> datetime:
    """Normalizes string timestamp into UTC-aware datetime."""
    val = val.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception as exc:
        raise ValueError(f"Invalid timestamp format '{val}'. Must be ISO-8601 (e.g. 2026-11-18T14:30:00Z).") from exc


async def read_csv_lines(file: UploadFile) -> List[Dict[str, str]]:
    """Reads uploaded CSV file into list of row dicts."""
    contents = await file.read()
    try:
        decoded = contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = contents.decode("latin-1")

    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="CSV file contains no headers or is empty.",
        )
    return list(reader)


# 1. Breaker Trips & Outage Events
@router.post("/breaker-trips", response_model=s.IngestionSummaryResponse, status_code=status.HTTP_201_CREATED)
async def ingest_breaker_trips(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Ingests protective relay breaker trip and lockout events from CSV."""
    rows = await read_csv_lines(file)
    correlator = EventCorrelatorService(db=db)
    sec_map = {s.section_code: s.id for s in db.query(m.FeederSection).all()}

    ingested = 0
    errors = []

    for idx, row in enumerate(rows, start=2):
        sec_code = row.get("section_code", "").strip()
        sec_id = sec_map.get(sec_code)
        if not sec_id and "section_id" in row and row["section_id"].isdigit():
            sec_id = int(row["section_id"])

        if not sec_id:
            errors.append(f"Row {idx}: Unrecognized section_code '{sec_code}'.")
            continue

        raw_ts = row.get("event_timestamp", "").strip()
        try:
            ts = parse_utc_timestamp(raw_ts)
        except ValueError as e:
            errors.append(f"Row {idx}: {str(e)}")
            continue

        e_type = row.get("event_type", "BREAKER_TRIP").strip().upper()
        if e_type not in ["BREAKER_TRIP", "RECLOSER_LOCKOUT", "AMI_LAST_GASP", "CUSTOMER_CALL", "DMS_ALARM", "NORMAL_TELEMETRY"]:
            errors.append(f"Row {idx}: Invalid event_type '{e_type}'.")
            continue

        source = row.get("source", "SCADA").strip()

        event = m.OutageEvent(
            section_id=sec_id,
            event_timestamp=ts,
            event_type=e_type,
            source=source,
            raw_payload={"ingested_via": "csv", "source_file": file.filename},
        )
        db.add(event)
        db.flush()
        correlator.correlate_event(event)
        ingested += 1

    if errors:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"CSV validation failed on {len(errors)} row(s): " + "; ".join(errors[:5]),
        )

    db.commit()
    return s.IngestionSummaryResponse(
        dataset_type="breaker_trips",
        rows_received=len(rows),
        rows_ingested=ingested,
        message=f"Successfully ingested and correlated {ingested} breaker trip / outage event(s).",
    )


# 2. Voltage Readings
@router.post("/voltage-readings", response_model=s.IngestionSummaryResponse, status_code=status.HTTP_201_CREATED)
async def ingest_voltage_readings(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Ingests distribution transformer secondary voltage and load telemetry."""
    rows = await read_csv_lines(file)
    tx_map = {t.transformer_code: t.id for t in db.query(m.Transformer).all()}

    ingested = 0
    errors = []

    for idx, row in enumerate(rows, start=2):
        tx_code = row.get("transformer_code", "").strip()
        tx_id = tx_map.get(tx_code)
        if not tx_id and "transformer_id" in row and row["transformer_id"].isdigit():
            tx_id = int(row["transformer_id"])

        if not tx_id:
            errors.append(f"Row {idx}: Transformer '{tx_code}' not found.")
            continue

        try:
            ts = parse_utc_timestamp(row.get("timestamp", ""))
            v_val = float(row.get("voltage_v", 0.0))
            if v_val < 0.0 or v_val > 600.0:
                raise ValueError(f"Voltage {v_val}V out of physical range [0, 600]")
            i_val = float(row.get("current_a", 0.0))
            p_val = float(row.get("active_power_kw", 0.0))
            pf = float(row.get("power_factor", 0.95))
        except (ValueError, TypeError) as e:
            errors.append(f"Row {idx}: Validation error: {str(e)}")
            continue

        reading = m.VoltageReading(
            transformer_id=tx_id,
            timestamp=ts,
            voltage_v=v_val,
            current_a=i_val,
            active_power_kw=p_val,
            power_factor=pf,
            frequency_hz=float(row.get("frequency_hz", 50.0)),
        )
        db.add(reading)
        ingested += 1

    if errors:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"CSV validation failed on {len(errors)} row(s): " + "; ".join(errors[:5]),
        )

    db.commit()
    return s.IngestionSummaryResponse(
        dataset_type="voltage_readings",
        rows_received=len(rows),
        rows_ingested=ingested,
        message=f"Successfully ingested {ingested} transformer voltage reading(s).",
    )


# 3. Customer Complaints
@router.post("/complaints", response_model=s.IngestionSummaryResponse, status_code=status.HTTP_201_CREATED)
async def ingest_complaints(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Ingests customer outage complaints from CRM call logs."""
    rows = await read_csv_lines(file)
    correlator = EventCorrelatorService(db=db)
    cluster_map = {c.cluster_code: c.transformer.section_id for c in db.query(m.ConsumerCluster).join(m.Transformer).all() if c.transformer}
    sec_map = {s.section_code: s.id for s in db.query(m.FeederSection).all()}

    ingested = 0
    errors = []

    for idx, row in enumerate(rows, start=2):
        sec_id = None
        if "section_code" in row and row["section_code"] in sec_map:
            sec_id = sec_map[row["section_code"]]
        elif "cluster_code" in row and row["cluster_code"] in cluster_map:
            sec_id = cluster_map[row["cluster_code"]]
        elif "cluster_name" in row and row["cluster_name"] in cluster_map:
            sec_id = cluster_map[row["cluster_name"]]
        elif "section_id" in row and row["section_id"].isdigit():
            sec_id = int(row["section_id"])

        try:
            ts = parse_utc_timestamp(row.get("timestamp", ""))
        except ValueError as e:
            errors.append(f"Row {idx}: {str(e)}")
            continue

        c_type = row.get("complaint_type", "NO_POWER").strip()
        remarks = row.get("remarks", "")

        event = m.OutageEvent(
            section_id=sec_id,
            event_timestamp=ts,
            event_type="CUSTOMER_CALL",
            source="CRM",
            raw_payload={"complaint_type": c_type, "remarks": remarks, "phone": row.get("phone")},
        )
        db.add(event)
        db.flush()
        correlator.correlate_event(event)
        ingested += 1

    if errors:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"CSV validation failed on {len(errors)} row(s): " + "; ".join(errors[:5]),
        )

    db.commit()
    return s.IngestionSummaryResponse(
        dataset_type="complaints",
        rows_received=len(rows),
        rows_ingested=ingested,
        message=f"Successfully ingested and correlated {ingested} customer outage complaint(s).",
    )


# 4. DT Status Updates
@router.post("/dt-status", response_model=s.IngestionSummaryResponse, status_code=status.HTTP_201_CREATED)
async def ingest_dt_status(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Ingests distribution transformer load and status updates."""
    rows = await read_csv_lines(file)
    tx_cache = {t.transformer_code: t for t in db.query(m.Transformer).all()}

    ingested = 0
    errors = []

    for idx, row in enumerate(rows, start=2):
        tx_code = row.get("transformer_code", "").strip()
        tx = tx_cache.get(tx_code)
        if not tx:
            errors.append(f"Row {idx}: Transformer '{tx_code}' not found.")
            continue

        try:
            load_kva = float(row.get("current_load_kva", 0.0))
            load_pct = float(row.get("load_percentage", (load_kva / max(1.0, tx.rated_kva)) * 100.0))
            if load_kva < 0:
                raise ValueError("current_load_kva cannot be negative.")
        except ValueError as e:
            errors.append(f"Row {idx}: {str(e)}")
            continue

        tx.current_load_kva = load_kva
        tx.load_percentage = round(load_pct, 1)
        ingested += 1

    if errors:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"CSV validation failed on {len(errors)} row(s): " + "; ".join(errors[:5]),
        )

    db.commit()
    return s.IngestionSummaryResponse(
        dataset_type="dt_status",
        rows_received=len(rows),
        rows_ingested=ingested,
        message=f"Successfully updated status for {ingested} distribution transformer(s).",
    )


# 5. Weather Observations
@router.post("/weather", response_model=s.IngestionSummaryResponse, status_code=status.HTTP_201_CREATED)
async def ingest_weather(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Ingests regional meteorological weather observations from CSV."""
    rows = await read_csv_lines(file)
    ingested = 0
    errors = []

    for idx, row in enumerate(rows, start=2):
        try:
            ts = parse_utc_timestamp(row.get("timestamp", ""))
            temp = float(row.get("temperature_c", 26.5))
            hum = float(row.get("relative_humidity_pct", 65.0))
            precip = float(row.get("precipitation_mm", 0.0))
            wind = float(row.get("wind_speed_kmh", 12.0))
            gust = float(row.get("wind_gust_kmh", 18.0))
            lightning = int(row.get("lightning_count", 0))
            src = row.get("source", "synthetic").strip().lower()
            if src not in ["live", "synthetic"]:
                src = "synthetic"
        except ValueError as e:
            errors.append(f"Row {idx}: Validation error: {str(e)}")
            continue

        obs = m.WeatherObservation(
            region_name=row.get("region_name", "Bangalore North").strip(),
            timestamp=ts,
            source=src,
            temperature_c=temp,
            relative_humidity_pct=hum,
            precipitation_mm=precip,
            wind_speed_kmh=wind,
            wind_gust_kmh=gust,
            lightning_count=lightning,
        )
        db.add(obs)
        ingested += 1

    if errors:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"CSV validation failed on {len(errors)} row(s): " + "; ".join(errors[:5]),
        )

    db.commit()
    return s.IngestionSummaryResponse(
        dataset_type="weather",
        rows_received=len(rows),
        rows_ingested=ingested,
        message=f"Successfully ingested {ingested} weather observation(s).",
    )


# 6. Asset Records
@router.post("/asset-records", response_model=s.IngestionSummaryResponse, status_code=status.HTTP_201_CREATED)
async def ingest_asset_records(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Ingests asset health, condition, and maintenance records."""
    rows = await read_csv_lines(file)
    existing_assets = {a.asset_identifier: a for a in db.query(m.AssetRecord).all()}

    ingested = 0
    errors = []

    for idx, row in enumerate(rows, start=2):
        ident = row.get("asset_identifier", "").strip()
        if not ident:
            errors.append(f"Row {idx}: asset_identifier is required.")
            continue

        try:
            h_idx = float(row.get("health_index", 85.0))
            if h_idx < 0.0 or h_idx > 100.0:
                raise ValueError("health_index must be between 0 and 100")
            fail_cnt = int(row.get("failure_history_count", 0))
            temp = float(row.get("operating_temperature_c", 50.0)) if row.get("operating_temperature_c") else None
        except ValueError as e:
            errors.append(f"Row {idx}: Validation error: {str(e)}")
            continue

        a_type = row.get("asset_type", "SECTION").strip()
        cond = row.get("condition_rating", "GOOD").strip()

        if ident in existing_assets:
            asset = existing_assets[ident]
            asset.health_index = h_idx
            asset.condition_rating = cond
            asset.failure_history_count = fail_cnt
            if temp is not None:
                asset.operating_temperature_c = temp
        else:
            asset = m.AssetRecord(
                asset_type=a_type,
                asset_identifier=ident,
                health_index=h_idx,
                condition_rating=cond,
                failure_history_count=fail_cnt,
                operating_temperature_c=temp,
            )
            db.add(asset)

        ingested += 1

    if errors:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"CSV validation failed on {len(errors)} row(s): " + "; ".join(errors[:5]),
        )

    db.commit()
    return s.IngestionSummaryResponse(
        dataset_type="asset_records",
        rows_received=len(rows),
        rows_ingested=ingested,
        message=f"Successfully ingested and updated {ingested} asset record(s).",
    )
