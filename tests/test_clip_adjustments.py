import pytest

from modules.clip_adjustments import adjust_clip_bounds


def test_adjust_clip_bounds_snaps_near_transcript_boundaries_without_mutating_clip():
    clip = {"start": 10, "end": 25, "duration": 15, "title": "Tese"}
    adjusted = adjust_clip_bounds(
        clip,
        start=10.8,
        end=24.2,
        transcript_segments=[
            {"start": 11.0, "end": 15.0},
            {"start": 18.0, "end": 24.0},
        ],
    )
    assert adjusted["start"] == 11.0
    assert adjusted["end"] == 24.0
    assert adjusted["duration"] == 13.0
    assert adjusted["boundary_adjustment"]["source"] == "transcript"
    assert clip["start"] == 10
    assert clip["end"] == 25


def test_adjust_clip_bounds_clamps_to_video_and_preserves_minimum_duration():
    adjusted = adjust_clip_bounds(
        {"start": 10, "end": 20},
        start=0,
        end=1,
        duration=30,
        min_duration=4,
    )
    assert adjusted["start"] == 0.0
    assert adjusted["end"] == 4.0
    assert adjusted["duration"] == 4.0


def test_adjust_clip_bounds_rejects_impossible_minimum_inside_short_source():
    with pytest.raises(ValueError, match="duração mínima"):
        adjust_clip_bounds(
            {"start": 0, "end": 1},
            start=0,
            end=0.5,
            duration=2,
            min_duration=3,
        )


def test_adjust_clip_bounds_does_not_snap_far_boundaries():
    adjusted = adjust_clip_bounds(
        {"start": 10, "end": 20},
        start=10.0,
        end=20.0,
        transcript_segments=[{"start": 14.0, "end": 16.0}],
        snap_tolerance=1.0,
    )
    assert adjusted["start"] == 10.0
    assert adjusted["end"] == 20.0
    assert adjusted["boundary_adjustment"]["source"] == "manual"


def test_adjust_clip_bounds_rejects_non_finite_bounds_and_duration():
    for kwargs in ({"start": "nan"}, {"end": "inf"}, {"duration": "nan"}):
        with pytest.raises(ValueError):
            adjust_clip_bounds(
                {"start": 10, "end": 30, "duration": 20},
                **kwargs,
            )


def test_adjust_clip_bounds_rejects_invalid_interval():
    with pytest.raises(ValueError):
        adjust_clip_bounds({"start": 10, "end": 20}, start=20, end=10)
