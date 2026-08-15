import math
import subprocess
import wave

from modules.audio_analyzer import AudioAnalyzer


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
