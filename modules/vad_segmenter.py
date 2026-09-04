"""Segmentação opcional de fala via Silero VAD empacotado no faster-whisper.

Fallback silencioso quando o backend não está disponível; o módulo não
introduz dependências novas — reaproveita o ONNX já empacotado pelo
próprio faster-whisper.
"""

from typing import List, Optional


class VADSegmenter:
    """Segmentador de fala leve, CPU-friendly, sem GPU."""

    def __init__(
        self,
        threshold: float = 0.5,
        min_silence_duration_ms: int = 500,
        speech_pad_ms: int = 200,
        min_speech_duration_ms: int = 0,
    ):
        self.threshold = threshold
        self.min_silence_duration_ms = min_silence_duration_ms
        self.speech_pad_ms = speech_pad_ms
        self.min_speech_duration_ms = min_speech_duration_ms
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from faster_whisper.vad import get_vad_model
                self._model = get_vad_model()
            except Exception as exc:
                raise RuntimeError(
                    "Silero VAD empacotado no faster-whisper não está disponível."
                ) from exc

    def segment(
        self,
        audio: "np.ndarray",
        sampling_rate: int = 16000,
    ) -> List[dict]:
        """Retorna segmentos de fala [{start, end}, ...] em segundos."""
        self._load_model()
        from faster_whisper.vad import VadOptions, get_speech_timestamps
        opts = VadOptions(
            threshold=self.threshold,
            min_silence_duration_ms=self.min_silence_duration_ms,
            speech_pad_ms=self.speech_pad_ms,
            min_speech_duration_ms=self.min_speech_duration_ms,
        )
        raw = get_speech_timestamps(audio, vad_options=opts, sampling_rate=sampling_rate)
        segments = []
        for seg in raw:
            start = round(seg["start"] / sampling_rate, 3)
            end = round(seg["end"] / sampling_rate, 3)
            if end > start:
                segments.append({"start": start, "end": end})
        segments.sort(key=lambda x: x["start"])
        return segments
