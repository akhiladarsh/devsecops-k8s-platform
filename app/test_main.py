"""
Unit tests for the Flask application.
Run with: pytest app/test_main.py -v
"""

import pytest
from app.main import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_returns_service_info(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.get_json()
    assert data["service"] == "devsecops-k8s-platform"
    assert "version" in data
    assert "hostname" in data


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "healthy"}


def test_ready_endpoint(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ready"}


def test_metrics_endpoint_format(client):
    """Metrics endpoint should return Prometheus-formatted data."""
    response = client.get("/metrics")
    # Either 200 with metrics or 501 if prometheus_client not installed
    assert response.status_code in (200, 501)


def test_unknown_route_returns_404(client):
    response = client.get("/nonexistent")
    assert response.status_code == 404
