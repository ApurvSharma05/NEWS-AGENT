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


# ── POST /digest/run: auth, lock, CORS ────────────────────────────────────────

import api.main as api_main


class _FakeAgent:
    def run_daily_digest(self):
        return {"status": "success"}


class _BoomAgent:
    def run_daily_digest(self):
        raise RuntimeError("boom")


@pytest.fixture
def fake_agent(monkeypatch):
    monkeypatch.setattr(api_main, "NewsAgent", _FakeAgent)


def test_digest_run_open_when_no_api_key_configured(client, fake_agent, monkeypatch):
    monkeypatch.setattr(api_main, "DIGEST_API_KEY", "")
    response = client.post("/digest/run?async_mode=false")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_digest_run_requires_api_key_when_configured(client, fake_agent, monkeypatch):
    monkeypatch.setattr(api_main, "DIGEST_API_KEY", "s3cret")
    assert client.post("/digest/run?async_mode=false").status_code == 401
    assert client.post("/digest/run?async_mode=false", headers={"X-API-Key": "nope"}).status_code == 401
    ok = client.post("/digest/run?async_mode=false", headers={"X-API-Key": "s3cret"})
    assert ok.status_code == 200


def test_digest_run_rejects_concurrent_run_with_409(client, fake_agent, monkeypatch):
    monkeypatch.setattr(api_main, "DIGEST_API_KEY", "")
    assert api_main._digest_lock.acquire(blocking=False)
    try:
        response = client.post("/digest/run?async_mode=false")
        assert response.status_code == 409
    finally:
        api_main._digest_lock.release()
    # Once the running job is done, a new run is accepted again.
    assert client.post("/digest/run?async_mode=false").status_code == 200


def test_digest_lock_released_after_failure(client, monkeypatch):
    monkeypatch.setattr(api_main, "DIGEST_API_KEY", "")
    monkeypatch.setattr(api_main, "NewsAgent", _BoomAgent)
    assert client.post("/digest/run?async_mode=false").status_code == 500
    assert not api_main._digest_lock.locked()


def test_digest_lock_released_after_background_run(client, fake_agent, monkeypatch):
    monkeypatch.setattr(api_main, "DIGEST_API_KEY", "")
    response = client.post("/digest/run")  # async_mode defaults to True
    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    # TestClient runs background tasks before returning, which releases the lock.
    assert not api_main._digest_lock.locked()


def test_cors_only_allows_configured_origins(client):
    allowed = api_main.CORS_ALLOW_ORIGINS[0]
    ok = client.get("/health", headers={"Origin": allowed})
    assert ok.headers.get("access-control-allow-origin") == allowed

    evil = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in evil.headers
