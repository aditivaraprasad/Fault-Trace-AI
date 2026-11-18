import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "FAULTTRACE AI" in data["message"]
    assert "advisory_notice" in data


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()

    # Core health checks
    assert data["status"] in ["healthy", "degraded"]
    assert data["app_name"] == "FAULTTRACE AI"
    assert "version" in data
    assert "timestamp" in data

    # Database connectivity check
    assert "database" in data
    assert data["database"]["status"] == "connected"
    assert data["database"]["dialect"] in ["sqlite", "postgresql"]

    # Pipeline configuration check
    assert "pipeline" in data
    assert data["pipeline"]["correlation_window_minutes"] == 15
    assert data["pipeline"]["candidate_pruning_policy"] == "topology-consistent candidates"
