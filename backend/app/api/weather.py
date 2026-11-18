"""
Weather Observation API Router.
Retrieves current and historical weather telemetry.
Surfaces the 'source' attribute ('live' from Open-Meteo or 'synthetic' fallback).
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
import backend.app.schemas as s
from backend.app.services.weather import WeatherService

router = APIRouter(prefix="/weather", tags=["Weather"])


@router.get("/current", response_model=s.WeatherObservationResponse)
def get_current_weather(db: Session = Depends(get_db)):
    """Retrieves the latest weather observation, reporting source ('live' or 'synthetic')."""
    service = WeatherService(db=db)
    obs = service.get_latest_observation()
    return s.WeatherObservationResponse.model_validate(obs)


@router.post("/fetch", response_model=s.WeatherObservationResponse)
def fetch_weather(
    force_synthetic: bool = Query(False, description="Force synthetic fallback instead of Open-Meteo"),
    db: Session = Depends(get_db),
):
    """Triggers an on-demand weather fetch from Open-Meteo public API with synthetic fallback."""
    service = WeatherService(db=db)
    obs = service.get_or_fetch_observation(force_synthetic=force_synthetic)
    return s.WeatherObservationResponse.model_validate(obs)
