"""
Unit tests for FastAPI endpoints in api/main.py.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "EPC Competitor Intelligence Agent"
    assert data["version"] == "2.0.0"
    assert "docs_url" in data


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True
    assert "timestamp" in data


def test_stats_endpoint(client):
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_articles" in data
    assert "total_tracked_companies" in data
    assert len(data["tracked_companies"]) > 0


def test_articles_endpoint(client):
    response = client.get("/articles?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "articles" in data
    assert isinstance(data["articles"], list)
    if data["articles"]:
        item = data["articles"][0]
        assert "title" in item
        assert "link" in item
        assert "importance" in item
        assert "companies" in item
