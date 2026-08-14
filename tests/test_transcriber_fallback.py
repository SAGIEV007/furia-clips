from modules.transcriber import Transcriber


def test_openai_whisper_fallback_disables_fp16_on_cpu():
    captured = {}

    class FakeWhisperModel:
        def transcribe(self, audio_path, **kwargs):
            captured["audio_path"] = audio_path
            captured.update(kwargs)
            return {"segments": [], "text": "", "language": "pt"}

    transcriber = Transcriber()
    transcriber.device = "cpu"
    transcriber.model = FakeWhisperModel()

    result = transcriber._transcribe_openai_whisper("video.mp4")

    assert captured["audio_path"] == "video.mp4"
    assert captured["fp16"] is False
    assert result["segments"] == []


def test_openai_whisper_fallback_keeps_fp16_on_cuda():
    captured = {}

    class FakeWhisperModel:
        def transcribe(self, audio_path, **kwargs):
            captured.update(kwargs)
            return {"segments": [], "text": "", "language": "pt"}

    transcriber = Transcriber()
    transcriber.device = "cuda"
    transcriber.model = FakeWhisperModel()

    transcriber._transcribe_openai_whisper("video.mp4")

    assert captured["fp16"] is True


def test_faster_whisper_downgrades_when_cuda_float16_is_unavailable(monkeypatch):
    import sys
    from types import SimpleNamespace

    attempts = []

    class FakeWhisperModel:
        def __init__(self, model_name, device="cpu", compute_type="int8", **kwargs):
            attempts.append((device, compute_type))
            if device == "cuda":
                raise RuntimeError("float16 backend unavailable")

    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=FakeWhisperModel))
    transcriber = Transcriber(device="cuda")
    monkeypatch.setattr(transcriber, "_detect_device", lambda: "cuda")
    events = []

    transcriber.load_model(lambda message, level="info": events.append((message, level)))

    assert transcriber.device == "cpu"
    assert transcriber.compute_type in {"int8", "int8_float32", "float32"}
    assert any(device == "cuda" and compute == "float16" for device, compute in attempts)
    assert any(device == "cpu" for device, _ in attempts)
    assert any("configuração segura" in message for message, _ in events)
