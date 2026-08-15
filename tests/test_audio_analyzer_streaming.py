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
