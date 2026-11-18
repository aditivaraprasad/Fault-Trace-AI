"""
Simulation API Router.
Provides on-demand scenario simulation endpoints including:
- Preset 'f4_hero': Feeder F4 trip, 142 complaints, 48 km/h gusts, DT collapse, water pump outage.
- Preset 'random': Randomized feeder & section fault simulation.
Executes the full pipeline and persists results into the database.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
import backend.app.schemas as s
from backend.app.services.scenario_runner import ScenarioSimulationRunner

router = APIRouter(prefix="/simulate", tags=["Scenario Simulation"])


@router.post("/scenario")
def simulate_scenario(
    req: s.ScenarioSimulationRequest,
    db: Session = Depends(get_db),
):
    """
    Executes end-to-end incident scenario simulation:
    1. Creates Incident with ground-truth actual_fault_section.
    2. Ingests correlated telemetry events (breaker trips, DT voltage losses, customer complaints).
    3. Correlates events within 15-minute sliding window.
    4. Evaluates NetworkX distribution graph candidates.
    5. Scores and calibrates candidates with XGBoost ranker and Isotonic calibration.
    6. Computes Tree SHAP attributions, structured evidence, and engineering narratives.
    7. Evaluates downstream asset impact and severity.
    8. Generates advisory restoration switching plan with donor feeder headroom verification.
    9. Persists all entities into the database and returns the full result.
    """
    try:
        runner = ScenarioSimulationRunner(db=db)
        result = runner.run_scenario(
            scenario_type=req.scenario_type,
            feeder_code=req.feeder_code,
            complaint_count=req.complaint_count,
            wind_speed_kmh=req.wind_speed_kmh,
            noise_level=req.noise_level,
        )
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation error: {str(exc)}",
        )
