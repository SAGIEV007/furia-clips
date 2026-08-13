from modules.face_tracker import FaceTracker


def _positions(face_count=1, jump=0.02):
    return [
        {"time": time, "center_x": 0.35 + index * jump, "center_y": 0.5, "confidence": 0.88, "face_count": face_count}
        for index, time in enumerate((0.0, 2.0, 4.0, 6.0, 8.0))
    ]


def test_stable_single_speaker_is_confident():
    assessment = FaceTracker().assess_segment_tracking(_positions(), 0.0, 8.0)
    assert assessment["confident"] is True
    assert assessment["coverage"] >= 0.60
    assert assessment["multiple_face_samples"] == 0


def test_multiple_faces_force_original_fallback():
    assessment = FaceTracker().assess_segment_tracking(_positions(face_count=2), 0.0, 8.0)
    assert assessment["confident"] is False
    assert assessment["multiple_face_samples"] == 5


def test_short_coverage_forces_original_fallback():
    positions = _positions()[:2]
    assessment = FaceTracker().assess_segment_tracking(positions, 0.0, 30.0)
    assert assessment["confident"] is False
    assert "poucas" in assessment["reason"]
