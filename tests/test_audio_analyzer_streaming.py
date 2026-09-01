import math
import subprocess
import wave

from modules.audio_analyzer import AudioAnalyzer


def test_find_high_energy_moments_coerces_legacy_values():
    profile = [
        {"time": "0", "energy_normalized": "0.8"},
        {"time": 1, "energy_normalized": "0.9"},
        {"time": "2", "energy_normalized": "nan"},
        {"time": 3, "energy_normalized": "0.1"},
        {"time": "invalid", "energy_normalized": 1.0},
    ]

    moments = AudioAnalyzer().find_high_energy_moments(profile, threshold=0.6, min_duration=1.0)

    assert moments
    assert moments[0]["start"] == 0.0
    assert moments[0]["end"] == 3.0
    assert all(
        value == value and value != float("inf")
        for moment in moments
        for value in moment.values()
        if isinstance(value, float)
    )


def test_analyze_energy_streams_pcm_and_normalizes(tmp_path):
    source = tmp_path / "tone.wav"
    sample_rate = 16000
    frames = bytearray()
    for index in range(sample_rate * 2):
        value = int(12000 * math.sin(2 * math.pi * 440 * index / sample_rate))
        frames.extend(value.to_bytes(2, byteorder="little", signed=True))
    with wave.open(str(source), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(bytes(frames))

    events = []
    profile = AudioAnalyzer().analyze_energy(str(source), emit_progress=events.append)

    assert len(profile) == 2
    assert profile[0]["energy_rms"] > 0
    assert max(item["energy_normalized"] for item in profile) == 1.0
    assert any("streaming" in message for message in events)
    assert events[-1].startswith("Analise de energia completa")


def test_analyze_energy_kills_ffmpeg_when_cancelled(monkeypatch):
    import modules.audio_analyzer as audio_module
    from modules.cancellation import OperationCancelled

    class FakeStream:
        def __init__(self):
            self.reads = [b"\x00" * 32000]

        def read(self, _size):
            return self.reads.pop(0) if self.reads else b""

        def decode(self, *args, **kwargs):
            return ""

    class FakeProcess:
        def __init__(self):
            self.stdout = FakeStream()
            self.stderr = FakeStream()
            self.killed = False
            self.waited = False

        def poll(self):
            return -9 if self.killed else None

        def kill(self):
            self.killed = True

        def wait(self):
            self.waited = True
            return -9 if self.killed else 0

    process = FakeProcess()
    monkeypatch.setattr(audio_module.subprocess, "Popen", lambda *args, **kwargs: process)
    checks = iter([False, True])

    try:
        AudioAnalyzer().analyze_energy("video.mp4", cancel_check=lambda: next(checks))
    except OperationCancelled:
        pass
    else:
        raise AssertionError("o cancelamento deveria interromper o streaming")

    assert process.killed is True
    assert process.waited is True



def test_analyze_energy_exposes_bounded_acoustic_cues(tmp_path):
    source = tmp_path / "tone-cues.wav"
    sample_rate = 16000
    frames = bytearray()
    for index in range(sample_rate * 2):
        amplitude = 12000 if index < sample_rate else 22000
        value = int(amplitude * math.sin(2 * math.pi * 440 * index / sample_rate))
        frames.extend(value.to_bytes(2, byteorder="little", signed=True))
    with wave.open(str(source), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(bytes(frames))

    profile = AudioAnalyzer().analyze_energy(str(source), window_seconds=1.0)

    assert len(profile) == 2
    for item in profile:
        assert 0.0 <= item["zero_crossing_rate"] <= 1.0
        assert 0.0 <= item["onset_strength"] <= 1.0
        assert 0.0 <= item["possible_reaction_signal"] <= 1.0
        assert item["audio_review_required"] is True


def test_summarize_window_is_review_only_and_ignores_invalid_values():
    summary = AudioAnalyzer().summarize_window([
        {"time": 10, "energy_normalized": 0.8, "onset_strength": 0.4, "zero_crossing_rate": 0.1, "possible_reaction_signal": 0.5},
        {"time": 12, "energy_normalized": 0.9, "onset_strength": 0.6, "zero_crossing_rate": 0.2, "possible_reaction_signal": 0.7},
        {"time": "nan", "energy_normalized": 1.0},
    ], 9, 13)

    assert summary["available"] is True
    assert summary["review_required"] is True
    assert summary["peak_energy"] == 0.9
    assert summary["possible_reaction_peak"] == 0.7
    assert summary["confidence"] <= 0.5


def test_detect_silence_finds_intervals(tmp_path):
    source = tmp_path / "tone_silence.wav"
    sample_rate = 16000
    frames = bytearray()
    # 0.5s silence, 0.5s tone, 1.0s silence, 0.5s tone, 0.5s silence
    segments = [
        (0, 0.5, 0),
        (0.5, 1.0, 12000),
        (1.0, 2.0, 0),
        (2.0, 2.5, 12000),
        (2.5, 3.0, 0),
    ]
    for start, end, amplitude in segments:
        for index in range(int(start * sample_rate), int(end * sample_rate)):
            value = int(amplitude * math.sin(2 * math.pi * 440 * index / sample_rate))
            frames.extend(value.to_bytes(2, byteorder="little", signed=True))
    with wave.open(str(source), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(bytes(frames))

    intervals = AudioAnalyzer().detect_silence(str(source), noise_tolerance_db=-40, min_duration=0.3)

    assert len(intervals) >= 2
    assert all("start" in i and "end" in i and "duration" in i for i in intervals)
