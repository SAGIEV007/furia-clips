import numpy as np
import pytest

from modules.vad_segmenter import VADSegmenter


@pytest.fixture()
def segmenter():
    return VADSegmenter(threshold=0.5, min_silence_duration_ms=500, speech_pad_ms=200)


class TestVADSegmenter:
    def test_silence_returns_no_segments(self, segmenter):
        audio = np.zeros(16000, dtype=np.float32)
        result = segmenter.segment(audio, sampling_rate=16000)
        assert result == []

    def test_low_threshold_detects_energy(self, segmenter):
        # Com threshold baixo, energia aleatória é aceita como fala.
        seg = VADSegmenter(threshold=0.05, min_silence_duration_ms=200, speech_pad_ms=0)
        np.random.seed(0)
        audio = np.zeros(16000, dtype=np.float32)
        audio[4000:12000] = np.random.randn(8000).astype(np.float32) * 0.3
        result = seg.segment(audio, sampling_rate=16000)
        assert len(result) >= 1
        assert result[0]["end"] > result[0]["start"]

    def test_short_speech_filtered(self, segmenter):
        seg = VADSegmenter(threshold=0.05, min_silence_duration_ms=200,
                           speech_pad_ms=0, min_speech_duration_ms=1000)
        np.random.seed(0)
        audio = np.zeros(16000, dtype=np.float32)
        audio[4000:8000] = np.random.randn(4000).astype(np.float32) * 0.3
        result = seg.segment(audio, sampling_rate=16000)
        assert result == []

    def test_returns_seconds(self, segmenter):
        seg = VADSegmenter(threshold=0.05, min_silence_duration_ms=200, speech_pad_ms=0)
        np.random.seed(0)
        audio = np.zeros(32000, dtype=np.float32)
        audio[8000:24000] = np.random.randn(16000).astype(np.float32) * 0.3
        result = seg.segment(audio, sampling_rate=16000)
        assert len(result) == 1
        assert result[0]["start"] >= 0.4
        assert result[0]["start"] <= 0.9
        assert result[0]["end"] >= 1.3
        assert result[0]["end"] <= 1.8


class TestVADSegmenterFallback:
    def test_missing_backend_returns_empty(self, monkeypatch):
        import modules.vad_segmenter as vad_module
        monkeypatch.setitem(vad_module.__dict__, "get_vad_model", None)
        seg = VADSegmenter()
        # Remove cached model to force reload path
        seg._model = None
        result = seg.segment(__import__("numpy").zeros(16000, dtype="float32"), 16000)
        assert result == []
