from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.api.endpoints import router as health_router
from backend.app.api.feeders import router as feeders_router
from backend.app.api.assets import router as assets_router
from backend.app.api.incidents import router as incidents_router
from backend.app.api.network import router as network_router
from backend.app.api.ml import router as ml_router
from backend.app.api.ingestion import router as ingestion_router
from backend.app.api.simulation import router as simulation_router
from backend.app.api.weather import router as weather_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.database.session import Base, engine
import backend.app.models  # Register all models for Base.metadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="BESCOM Power Hack 2026 (Theme 10) - Fault Localization & Advisory Restoration Engine",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers (/api/v1 prefix)
app.include_router(health_router, prefix="/api/v1")
app.include_router(feeders_router, prefix="/api/v1")
app.include_router(assets_router, prefix="/api/v1")
app.include_router(incidents_router, prefix="/api/v1")
app.include_router(network_router, prefix="/api/v1")
app.include_router(ml_router, prefix="/api/v1")
app.include_router(ingestion_router, prefix="/api/v1")
app.include_router(simulation_router, prefix="/api/v1")
app.include_router(weather_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")

# Root aliases for prompt specification (/network/topology, /localize/graph, /model/metrics, /incidents, /simulate/scenario, /dashboard/stats, /assets, /feeders, /health)
app.include_router(health_router)
app.include_router(network_router)
app.include_router(ml_router)
app.include_router(incidents_router)
app.include_router(ingestion_router)
app.include_router(simulation_router)
app.include_router(weather_router)
app.include_router(dashboard_router)
app.include_router(assets_router)
app.include_router(feeders_router)


@app.get("/")
def root():
    return {
        "message": "FAULTTRACE AI Distribution Grid Fault Localization Engine is active.",
        "docs_url": "/docs",
        "health_url": "/api/v1/health",
        "advisory_notice": "Restoration operations are advisory only. Manual engineer review required."
    }
