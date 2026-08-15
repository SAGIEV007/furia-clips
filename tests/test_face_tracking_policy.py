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


def test_tasks_api_without_model_reports_safe_fallback(monkeypatch):
    import sys
    from types import SimpleNamespace

    fake_mp = SimpleNamespace(
        tasks=SimpleNamespace(
            BaseOptions=object,
            vision=SimpleNamespace(FaceDetector=object()),
        )
    )
    monkeypatch.setitem(sys.modules, "mediapipe", fake_mp)

    tracker = FaceTracker()
    tracker._get_model_path = lambda: None

    assert tracker._ensure_detector() is False
    assert "modelo facial" in tracker._unavailable_reason


def test_tasks_api_uses_detector_factory_when_model_exists(monkeypatch):
    import sys
    from types import SimpleNamespace

    class FakeBaseOptions:
        def __init__(self, model_asset_path):
            self.model_asset_path = model_asset_path

    class FakeDetectorOptions:
        def __init__(self, base_options, min_detection_confidence):
            self.base_options = base_options
            self.min_detection_confidence = min_detection_confidence

    class FakeDetectorFactory:
        @staticmethod
        def create_from_options(options):
            return {"options": options}

    fake_mp = SimpleNamespace(
        tasks=SimpleNamespace(
            BaseOptions=FakeBaseOptions,
            vision=SimpleNamespace(
                FaceDetector=FakeDetectorFactory,
                FaceDetectorOptions=FakeDetectorOptions,
            ),
        )
    )
    monkeypatch.setitem(sys.modules, "mediapipe", fake_mp)

    tracker = FaceTracker()
    tracker._get_model_path = lambda: "/tmp/fake-face-model.tflite"

    assert tracker._ensure_detector() is True
    assert tracker.detector["options"].base_options.model_asset_path.endswith("fake-face-model.tflite")
    assert tracker._unavailable_reason is None


def test_model_path_resolves_models_directory(monkeypatch, tmp_path):
    import modules.face_tracker as face_tracker_module

    module_root = tmp_path / "project" / "modules"
    module_root.mkdir(parents=True)
    model_dir = tmp_path / "project" / "models"
    model_dir.mkdir()
    model_file = model_dir / "blaze_face_short_range.tflite"
    model_file.write_bytes(b"model")
    monkeypatch.setattr(face_tracker_module, "__file__", str(module_root / "face_tracker.py"))

    assert FaceTracker()._get_model_path() == str(model_file)


def test_tracker_close_is_idempotent():
    tracker = FaceTracker()
    tracker.close()
    tracker.close()
    assert tracker.detector is None
