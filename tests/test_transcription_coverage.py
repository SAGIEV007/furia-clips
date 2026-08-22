from app import _max_finite_transcript_timestamp, _transcription_coverage_report


def test_max_finite_transcript_timestamp_ignores_invalid_values():
    value = _max_finite_transcript_timestamp([
        {"start": 0, "end": 3},
        {"start": "nan", "end": "inf"},
        {"start": 4, "end": "malformed"},
    ])
    assert value == 3.0


def test_coverage_report_marks_full_transcript_as_covered():
    report = _transcription_coverage_report(
        {"segments": [{"start": 0, "end": 300}]},
        300,
    )
    assert report["status"] == "covered"
    assert report["end_ratio"] == 1.0


def test_coverage_report_marks_short_manual_excerpt_as_partial():
    report = _transcription_coverage_report(
        {"segments": [{"start": 0, "end": 40}]},
        120,
    )
    assert report["status"] == "partial"
    assert report["end_ratio"] == round(40 / 120, 3)


def test_coverage_report_preserves_raw_timestamp_mismatch_after_clamp():
    report = _transcription_coverage_report(
        {
            "segments": [{"start": 0, "end": 119.9}],
            "raw_last_timestamp": 5400,
        },
        120,
    )
    assert report["status"] == "mismatch_suspected"
    assert report["semantic_identity_verified"] is False


def test_coverage_report_does_not_claim_identity_without_duration():
    report = _transcription_coverage_report(
        {"segments": [{"start": 0, "end": 40}], "raw_last_timestamp": 40},
        None,
    )
    assert report["status"] == "covered"
    assert report["semantic_identity_verified"] is False
