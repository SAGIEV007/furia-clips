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
    dashboard = payload["dashboard"] or {}
    assert "count" in dashboard
    assert "total_views" in dashboard
    assert "avg_engagement_rate" in dashboard
    assert "avg_velocity" in dashboard
    assert "top_format" in dashboard
    assert "top_platform" in dashboard
    snapshots = payload.get("snapshots") or []
    assert isinstance(snapshots, list)
    if snapshots:
        for snap in snapshots:
            assert "platform" in snap
            assert "format_id" in snap


def test_performance_summary_smoke_returns_200():
    client = furia_app.test_client()
    response = client.get("/api/performance/summary")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert payload.get("success") is True
    assert "summary" in payload
    summary = payload["summary"] or {}
    assert "contents" in summary
    assert "snapshots" in summary
    assert "views" in summary
    assert "latest" in summary
