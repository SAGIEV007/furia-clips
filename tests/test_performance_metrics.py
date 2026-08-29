from modules.performance_metrics import cohort_observed_score, compare_snapshots, normalize_snapshot


def test_normalize_snapshot_computes_observed_metrics_without_guessing_retention():
    snapshot = normalize_snapshot(
        {
            "content_key": "renan-0813",
            "platform": "instagram",
            "format_id": "square_alfinetei",
            "account_key": "@renansantosmbl",
            "observation_window": "week",
            "region": "brasil",
            "published_at": "2026-08-13T10:00:00-03:00",
            "collected_at": "2026-08-14T10:00:00-03:00",
            "views": 10000,
            "likes": 800,
            "comments": 100,
            "shares": 50,
            "saves": 50,
            "ranking_position": 8,
            "xp": 10000,
        }
    )
    assert snapshot["engagement_actions"] == 1000
    assert snapshot["engagement_rate"] == 0.1
    assert snapshot["age_hours"] == 24.0
    assert snapshot["view_velocity_per_hour"] == 416.667
    assert snapshot["account_key"] == "@renansantosmbl"
    assert snapshot["observation_window"] == "week"
    assert snapshot["region"] == "brasil"
    assert "retention" not in snapshot


def test_compare_snapshots_reports_delta_and_interval():
    previous = {"views": 1000, "collected_at": "2026-08-14T10:00:00+00:00"}
    current = {"views": 1500, "collected_at": "2026-08-14T12:00:00+00:00"}
    result = compare_snapshots(previous, current)
    assert result["views_delta"] == 500
    assert result["views_growth_rate"] == 0.5
    assert result["collection_interval_hours"] == 2.0


def test_cohort_score_is_relative_and_explains_components():
    cohort = [
        {"views": 100, "engagement_rate": 0.01, "view_velocity_per_hour": 10},
        {"views": 500, "engagement_rate": 0.05, "view_velocity_per_hour": 50},
        {"views": 1000, "engagement_rate": 0.10, "view_velocity_per_hour": 100},
    ]
    result = cohort_observed_score(cohort[2], cohort)
    assert result["basis"] == "supplied_cohort"
    assert result["score"] == 100.0
    assert result["components"]["engagement_percentile"] == 100.0


from modules.performance_metrics import summarize_snapshots


def test_summarize_snapshots_empty_list():
    result = summarize_snapshots([])
    assert result["count"] == 0
    assert result["total_views"] == 0
    assert result["avg_engagement_rate"] == 0.0
    assert result["avg_velocity"] == 0.0
    assert result["top_format"] == "unknown"
    assert result["top_platform"] == "other"


def test_summarize_snapshots_aggregates_views_and_averages():
    snapshots = [
        {
            "content_key": "a",
            "platform": "instagram",
            "format_id": "vertical_916",
            "views": 1000,
            "engagement_rate": 0.05,
            "view_velocity_per_hour": 50.0,
        },
        {
            "content_key": "b",
            "platform": "youtube",
            "format_id": "square_alfinetei",
            "views": 2000,
            "engagement_rate": 0.10,
            "view_velocity_per_hour": 100.0,
        },
        {
            "content_key": "c",
            "platform": "instagram",
            "format_id": "vertical_916",
            "views": 3000,
            "engagement_rate": None,
            "view_velocity_per_hour": 75.0,
        },
    ]
    result = summarize_snapshots(snapshots)
    assert result["count"] == 3
    assert result["total_views"] == 6000
    assert result["avg_engagement_rate"] == 0.075
    assert result["avg_velocity"] == 75.0
    assert result["top_format"] == "vertical_916"
    assert result["top_platform"] == "instagram"


def test_summarize_snapshots_handles_missing_optional_metrics():
    snapshots = [
        {
            "content_key": "x",
            "platform": "tiktok",
            "format_id": "fake_tweet",
            "views": 500,
        }
    ]
    result = summarize_snapshots(snapshots)
    assert result["count"] == 1
    assert result["total_views"] == 500
    assert result["avg_engagement_rate"] == 0.0
    assert result["avg_velocity"] == 0.0
    assert result["top_format"] == "fake_tweet"
    assert result["top_platform"] == "tiktok"
