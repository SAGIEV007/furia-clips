from modules.performance_metrics import cohort_observed_score, compare_snapshots, normalize_snapshot


def test_normalize_snapshot_computes_observed_metrics_without_guessing_retention():
    snapshot = normalize_snapshot(
        {
            "content_key": "renan-0813",
            "platform": "instagram",
            "format_id": "square_alfinetei",
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
