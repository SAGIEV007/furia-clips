from modules.quality_metrics import boundary_errors, evaluate_temporal_quality, interval_iou


def test_interval_iou_accepts_garimpo_style_timestamps():
    assert interval_iou({"startS": 10, "endS": 30}, {"start": 20, "end": 40}) == 0.333333


def test_boundary_errors_are_absolute_and_explainable():
    assert boundary_errors({"start": 12, "end": 39}, {"start": 10, "end": 40}) == {
        "start_error_seconds": 2.0,
        "end_error_seconds": 1.0,
    }


def test_evaluate_temporal_quality_reports_iou_recall_precision_and_boundary_hits():
    result = evaluate_temporal_quality(
        [{"start": 10, "end": 40}, {"start": 80, "end": 100}],
        [{"start": 12, "end": 39}, {"start": 80, "end": 100}],
        iou_thresholds=(0.5, 0.7),
        boundary_tolerances=(2, 5),
    )

    assert result["basis"] == "supplied_editorial_references"
    assert result["iou"]["0.5"]["precision"] == 1.0
    assert result["iou"]["0.5"]["recall"] == 1.0
    assert result["iou"]["0.7"]["matched_count"] == 2
    assert result["boundary"]["hit_rate_2_0s"] == 1.0
    assert result["boundary"]["mean_iou"] > 0.9


def test_evaluate_temporal_quality_does_not_fabricate_score_without_references():
    result = evaluate_temporal_quality([{"start": 0, "end": 10}], [])

    assert result["basis"] == "no_reference"
    assert result["iou"] == {}
    assert result["reference_count"] == 0


def test_duplicate_rate_flags_redundant_predictions_without_rejecting_them():
    result = evaluate_temporal_quality(
        [{"start": 0, "end": 20}, {"start": 1, "end": 19}, {"start": 40, "end": 60}],
        [{"start": 0, "end": 20}],
    )

    assert result["duplicate_rate"] == round(2 / 3, 6)
    assert result["prediction_count"] == 3
