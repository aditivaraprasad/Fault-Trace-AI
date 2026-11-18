"""
Weather Observation Service for FAULTTRACE AI.
Fetches live weather from Open-Meteo public API (no key required)
or falls back gracefully to synthetic Bangalore meteorological data.
Explicitly records the 'source' attribute ('live' vs 'synthetic').
"""

import os
import urllib.request
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

import backend.app.models as m
from backend.app.core.config import settings

# Default Bengaluru Substation Coordinates (Hebbal / Bangalore North)
DEFAULT_LAT = 13.0358
DEFAULT_LON = 77.5970


class WeatherService:
    """Manages weather telemetry retrieval and persistence."""

    def __init__(self, db: Session):
        self.db = db

    def get_or_fetch_observation(
        self,
        substation_id: Optional[int] = None,
        force_synthetic: bool = False,
        lat: float = DEFAULT_LAT,
        lon: float = DEFAULT_LON,
    ) -> m.WeatherObservation:
        """
        Retrieves current weather observation.
        Attempts Open-Meteo public API first; falls back to synthetic on failure or if forced.
        """
        obs_data = None
        source = "synthetic"

        if not force_synthetic:
            try:
                # Open-Meteo public no-key endpoint
                url = (
                    f"https://api.open-meteo.com/v1/forecast?"
                    f"latitude={lat:.4f}&longitude={lon:.4f}&"
                    f"current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_gusts_10m"
                )
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "FaultTraceAI/1.0 (BESCOM Power Hack 2026)"}
                )
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    if resp.status == 200:
                        raw = json.loads(resp.read().decode("utf-8"))
                        curr = raw.get("current", {})
                        obs_data = {
                            "temperature_c": float(curr.get("temperature_2m", 27.2)),
                            "relative_humidity_pct": float(curr.get("relative_humidity_2m", 68.0)),
                            "precipitation_mm": float(curr.get("precipitation", 0.0)),
                            "wind_speed_kmh": float(curr.get("wind_speed_10m", 14.5)),
                            "wind_gust_kmh": float(curr.get("wind_gusts_10m", 22.0)),
                            "lightning_count": 0,
                            "source": "live",
                        }
                        source = "live"
            except Exception:
                # Fallback silently to synthetic observation
                obs_data = None

        if obs_data is None:
            # Deterministic/realistic synthetic Bengaluru baseline
            obs_data = {
                "temperature_c": 28.5,
                "relative_humidity_pct": 72.0,
                "precipitation_mm": 6.5,
                "wind_speed_kmh": 24.0,
                "wind_gust_kmh": 48.0,  # Gusts characteristic of stormy Bengaluru monsoon/pre-monsoon
                "lightning_count": 2,
                "source": "synthetic",
            }

        # Find substation if not provided
        if substation_id is None:
            sub = self.db.query(m.Substation).first()
            if sub:
                substation_id = sub.id

        observation = m.WeatherObservation(
            substation_id=substation_id,
            region_name="Bangalore North",
            timestamp=datetime.now(timezone.utc),
            source=obs_data["source"],
            temperature_c=obs_data["temperature_c"],
            relative_humidity_pct=obs_data["relative_humidity_pct"],
            precipitation_mm=obs_data["precipitation_mm"],
            wind_speed_kmh=obs_data["wind_speed_kmh"],
            wind_gust_kmh=obs_data["wind_gust_kmh"],
            lightning_count=obs_data["lightning_count"],
        )
        self.db.add(observation)
        self.db.commit()
        self.db.refresh(observation)
        return observation

    def get_latest_observation(self) -> Optional[m.WeatherObservation]:
        """Returns the most recent weather observation recorded in the database."""
        obs = self.db.query(m.WeatherObservation).order_by(m.WeatherObservation.timestamp.desc()).first()
        if not obs:
            return self.get_or_fetch_observation(force_synthetic=True)
        return obs
