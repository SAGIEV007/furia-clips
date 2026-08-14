import database


def test_performance_snapshot_persists_and_filters_by_observed_cohort(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "performance.sqlite"))
    database.init_db()

    first = {
        "content_key": "reel-main-1",
        "platform": "instagram",
        "format_id": "vertical_916",
        "account_key": "@renansantosmbl",
        "observation_window": "today",
        "region": "brasil",
        "published_at": "2026-08-14T10:00:00-03:00",
        "collected_at": "2026-08-14T12:00:00-03:00",
        "views": 2000,
        "likes": 100,
        "comments": 20,
        "shares": 10,
        "saves": 5,
        "engagement_actions": 135,
        "engagement_rate": 0.0675,
        "age_hours": 2,
        "view_velocity_per_hour": 1000,
        "ranking_position": 3,
        "xp": 10,
        "collection_state": "observed",
        "source": "manual_or_authorized_export",
    }
    second = {**first, "content_key": "reel-reserve-1", "account_key": "@renansantosreserva", "views": 900}
    database.save_performance_snapshot(first)
    database.save_performance_snapshot(second)

    snapshots = database.get_performance_snapshots(
        platform="instagram",
        format_id="vertical_916",
        observation_window="today",
        region="brasil",
    )
    summary = database.get_performance_summary(
        platform="instagram",
        observation_window="today",
        region="brasil",
    )

    assert len(snapshots) == 2
    assert {item["account_key"] for item in snapshots} == {"@renansantosmbl", "@renansantosreserva"}
    assert summary["contents"] == 2
    assert summary["views"] == 2900
