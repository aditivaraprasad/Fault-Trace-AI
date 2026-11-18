from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall service status (healthy/degraded)")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(..., description="Current UTC timestamp")
    database: Dict[str, Any] = Field(..., description="Database connectivity status and dialect")
    pipeline: Dict[str, Any] = Field(..., description="Pipeline parameters")
