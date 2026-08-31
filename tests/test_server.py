import json

import pytest
from fastapi.testclient import TestClient

from dynasty_prospects import server
from dynasty_prospects.server import app

client = TestClient(app)


def test_healthz_reports_ok():
    response = client.get("/api/healthz")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_healthz_reports_missing_dashboard_data():
    """data/dashboard.json isn't committed (see data/README.md) -- confirm the
    server degrades gracefully rather than assuming it's always there."""
    path = server.DATA_DIR / "dashboard.json"
    assert not path.exists(), "this test assumes no dashboard.json is committed to the repo"
    response = client.get("/api/healthz")
    assert response.json()["dashboard_data"] is False


def test_index_serves_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "Dynasty Prospects" in response.text


@pytest.fixture
def fixture_dashboard_data():
    path = server.DATA_DIR / "dashboard.json"
    path.write_text(json.dumps({"generated_at": "now", "draft_class": 2027, "prospects": []}), encoding="utf-8")
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


def test_dashboard_data_is_served_from_data_mount(fixture_dashboard_data):
    response = client.get("/data/dashboard.json")
    assert response.status_code == 200
    assert "prospects" in response.json()


def test_cache_control_is_no_cache():
    response = client.get("/api/healthz")
    assert response.headers["cache-control"] == "no-cache"
