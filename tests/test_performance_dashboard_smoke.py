import json
from app import app as furia_app


def test_dashboard_smoke_returns_200():
    client = furia_app.test_client()
    response = client.get("/api/performance/dashboard")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert payload.get("success") is True
    assert "dashboard" in payload
