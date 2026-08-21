import os
import tempfile
import unittest

from modules.media_validation import validate_media
from modules.video_cutter import VideoCutter


FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_av.mp4")


@unittest.skipUnless(os.path.exists(FIXTURE), "fixture de mídia ainda não foi gerada")
class VideoCutterTests(unittest.TestCase):
    def test_cut_clip_renders_vertical_with_audio(self):
        with tempfile.TemporaryDirectory() as tempdir:
            output = os.path.join(tempdir, "vertical.mp4")
            cutter = VideoCutter(preset="shorts")
            result = cutter.cut_clip(FIXTURE, 0, 1.5, output, vertical=True)
            self.assertEqual(result, output)
            validation = validate_media(
                output,
                expected_width=1080,
                expected_height=1920,
                expected_duration=1.5,
                duration_tolerance=0.5,
                require_audio=True,
            )
            self.assertTrue(validation.valid, validation.as_dict())

    def test_debate_layout_preserves_full_frame_inside_vertical_canvas(self):
        with tempfile.TemporaryDirectory() as tempdir:
            output = os.path.join(tempdir, "debate.mp4")
            cutter = VideoCutter(preset="shorts")
            result = cutter.cut_clip(
                FIXTURE, 0, 1.0, output, vertical=True, video_layout="debate"
            )
            self.assertEqual(result, output)
            validation = validate_media(
                output,
                expected_width=1080,
                expected_height=1920,
                expected_duration=1.0,
                duration_tolerance=0.5,
                require_audio=True,
            )
            self.assertTrue(validation.valid, validation.as_dict())

    def test_batch_layout_plan_can_force_original_composition(self):
        with tempfile.TemporaryDirectory() as tempdir:
            cutter = VideoCutter(preset="shorts")
            results = cutter.batch_cut(
                FIXTURE,
                [{"start": 0.0, "end": 1.0, "duration": 1.0, "title": "split"}],
                "layout_plan",
                use_face_tracking=True,
                face_positions_map={0: [
                    {"time": 0.0, "center_x": 0.70, "confidence": 0.92},
                    {"time": 0.5, "center_x": 0.71, "confidence": 0.91},
                    {"time": 1.0, "center_x": 0.70, "confidence": 0.90},
                ]},
                output_dir=tempdir,
                layout_plans={0: {
                    "layout_family": "split_screen",
                    "reframe_allowed": False,
                    "reason": "preservar os dois interlocutores",
                }},
            )

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["framing_mode"], "original_16_9")
            self.assertEqual(results[0]["framing_reason"], "preservar os dois interlocutores")
            self.assertEqual(
                results[0]["layout_plan"]["reason"],
                "preservar os dois interlocutores",
            )
            self.assertEqual(results[0]["preset"], "original_16:9")


if __name__ == "__main__":
    unittest.main()


def test_batch_cut_preserves_source_index_after_earlier_render_rejection(monkeypatch, tmp_path):
    from types import SimpleNamespace
    import modules.video_cutter as module

    def fake_cut(self, video_path, start, end, output_path, **kwargs):
        open(output_path, "wb").close()
        return output_path

    def fake_validate(path, **kwargs):
        rejected = "Primeiro" in os.path.basename(path)
        return SimpleNamespace(
            valid=not rejected,
            errors=["falha sintética"] if rejected else [],
            warnings=[],
            as_dict=lambda: {"valid": not rejected},
        )

    monkeypatch.setattr(module.VideoCutter, "cut_clip", fake_cut)
    monkeypatch.setattr(module, "validate_media", fake_validate)

    results = module.VideoCutter(preset="shorts").batch_cut(
        "fonte.mp4",
        [
            {"start": 0.0, "end": 10.0, "duration": 10.0, "title": "Primeiro", "text": "Primeiro texto"},
            {"start": 20.0, "end": 32.0, "duration": 12.0, "title": "Segundo", "text": "Segundo texto"},
        ],
        "indice-preservado",
        output_dir=str(tmp_path),
    )

    assert len(results) == 1
    assert results[0]["index"] == 1
    assert results[0]["text"] == "Segundo texto"
    assert results[0]["title"] == "Segundo"


def test_detect_scenes_handles_empty_stderr(monkeypatch):
    from types import SimpleNamespace
    import modules.video_cutter as module

    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stderr=None, returncode=0),
    )
    assert VideoCutter().detect_scenes("video.mp4") == [0.0]


def test_batch_cut_preserves_original_when_reframe_requires_review(monkeypatch, tmp_path):
    from types import SimpleNamespace
    import modules.video_cutter as module

    def fake_cut(self, video_path, start, end, output_path, **kwargs):
        open(output_path, "wb").close()
        return output_path

    monkeypatch.setattr(module.VideoCutter, "cut_clip", fake_cut)
    monkeypatch.setattr(module, "validate_media", lambda *args, **kwargs: SimpleNamespace(
        valid=True,
        errors=[],
        warnings=[],
        as_dict=lambda: {"valid": True},
    ))

    results = module.VideoCutter(preset="shorts").batch_cut(
        "fonte.mp4",
        [{"start": 0.0, "end": 10.0, "duration": 10.0, "title": "Ambíguo"}],
        "framing-review",
        use_face_tracking=True,
        face_positions_map={0: [{"time": 0.0, "center_x": 0.7, "confidence": 0.9}]},
        output_dir=str(tmp_path),
        layout_plans={0: {
            "layout_family": "single_face",
            "reframe_allowed": True,
            "review_required": True,
            "confidence": 0.70,
            "reason": "confiança abaixo do limite; confirmar enquadramento",
        }},
    )

    assert len(results) == 1
    assert results[0]["framing_mode"] == "original_16_9"
    assert results[0]["preset"] == "original_16:9"
    assert results[0]["layout_plan"]["review_required"] is True


def test_invalid_render_is_removed_before_it_can_be_returned(tmp_path):
    from modules.video_cutter import VideoCutter

    invalid = tmp_path / "invalid.mp4"
    invalid.write_bytes(b"not a media file")
    events = []

    result = VideoCutter()._validate_rendered_output(
        str(invalid),
        1.0,
        emit_progress=lambda message, level="info": events.append((message, level)),
    )

    assert result is False
    assert not invalid.exists()
    assert any("Renderização rejeitada" in message for message, _ in events)


def test_direct_render_validation_checks_selected_preset_dimensions(monkeypatch, tmp_path):
    import modules.video_cutter as module
    from types import SimpleNamespace

    output = tmp_path / "wrong-size.mp4"
    output.write_bytes(b"placeholder")
    captured = {}

    def fake_validate(path, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(valid=True, errors=[], warnings=[])

    monkeypatch.setattr(module, "validate_media", fake_validate)
    assert module.VideoCutter(preset="square")._validate_rendered_output(
        str(output),
        12.0,
        preset=module.get_preset("square"),
    ) is True
    assert captured["expected_width"] == 1080
    assert captured["expected_height"] == 1080
    assert captured["require_audio"] is True
    assert captured["require_video"] is True


def test_face_tracking_uses_selected_preset_aspect_ratio(monkeypatch, tmp_path):
    from types import SimpleNamespace
    import modules.video_cutter as module

    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        output_path = command[-1]
        open(output_path, "wb").close()
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module, "validate_media", lambda *args, **kwargs: SimpleNamespace(
        valid=True,
        errors=[],
        warnings=[],
    ))

    for preset_name, expected_filter in (
        ("square", "crop=1080:1080"),
        ("landscape", "crop=1920:1080"),
    ):
        output = tmp_path / f"{preset_name}.mp4"
        cutter = module.VideoCutter(preset=preset_name)
        cutter.get_video_info = lambda _path: {
            "streams": [{"codec_type": "video", "width": 1920, "height": 1080}]
        }
        result = cutter.cut_clip_with_face_tracking(
            "source.mp4",
            0.0,
            2.0,
            str(output),
            face_positions=[{"center_x": 0.8, "center_y": 0.5, "confidence": 0.9}],
        )
        assert result == str(output)
        vf_index = commands[-1].index("-vf")
        assert commands[-1][vf_index + 1].startswith(expected_filter)
        assert f"scale={cutter.preset['width']}:{cutter.preset['height']}" in commands[-1][vf_index + 1]


def test_batch_cut_clamps_padding_to_source_duration(monkeypatch, tmp_path):
    from types import SimpleNamespace
    import modules.video_cutter as module

    calls = []

    def fake_cut(self, video_path, start, end, output_path, **kwargs):
        calls.append((start, end))
        open(output_path, "wb").close()
        return output_path

    monkeypatch.setattr(module.VideoCutter, "cut_clip", fake_cut)
    monkeypatch.setattr(module, "validate_media", lambda *args, **kwargs: SimpleNamespace(
        valid=True,
        errors=[],
        warnings=[],
        as_dict=lambda: {"valid": True},
    ))

    results = module.VideoCutter(preset="shorts").batch_cut(
        "fonte.mp4",
        [{"start": 8.8, "end": 10.0, "duration": 1.2, "title": "final"}],
        "padding-limitado",
        output_dir=str(tmp_path),
        source_duration=10.0,
    )

    assert len(results) == 1
    assert calls == [(8.5, 10.0)]


def test_batch_cut_skips_interval_that_collapses_at_source_end(monkeypatch, tmp_path):
    import modules.video_cutter as module

    events = []
    results = module.VideoCutter(preset="shorts").batch_cut(
        "fonte.mp4",
        [{"start": 10.0, "end": 10.0, "duration": 0.0, "title": "invalido"}],
        "padding-invalido",
        output_dir=str(tmp_path),
        source_duration=10.0,
        emit_progress=lambda message, level="info": events.append((message, level)),
    )

    assert results == []
    assert any("limites inválidos" in message for message, _level in events)
