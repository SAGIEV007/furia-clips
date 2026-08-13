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
