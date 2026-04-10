"""
Basic API health check tests.
"""
from fastapi.testclient import TestClient


def test_health_endpoint(client):
    """Test /health returns ok status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_root(client):
    """Test /api returns version info."""
    response = client.get("/api")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
