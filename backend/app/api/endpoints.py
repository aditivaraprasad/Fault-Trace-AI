from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.database.session import get_db, engine
from backend.app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint reporting operational status,
    database connectivity, and pipeline configuration.
    """
    db_status = "connected"
    error_msg = None
    try:
        # Check database connectivity
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = "disconnected"
        error_msg = str(exc)

    overall_status = "healthy" if db_status == "connected" else "degraded"

    return HealthResponse(
        status=overall_status,
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc),
        database={
            "status": db_status,
            "dialect": engine.dialect.name,
            "url_scheme": settings.DATABASE_URL.split("://")[0],
            "error": error_msg
        },
        pipeline={
            "correlation_window_minutes": settings.CORRELATION_WINDOW_MINUTES,
            "calibration_method": settings.CALIBRATION_METHOD,
            "open_meteo_enabled": settings.OPEN_METEO_ENABLED,
            "candidate_pruning_policy": "topology-consistent candidates"
        }
    )
