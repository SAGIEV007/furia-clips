"""Whether the voice in a stretch is the one we enrolled, or somebody else.

This is the piece the editor has been asking for from the start, phrased three
different ways: "corta antes porque não é o Renan falando", "aparece Locutor:
Renan Santos 0% e ele fala em todos", "esse corte vira um corte CONTRA ele". All
three are the same missing fact — the program has no idea who is speaking.

Nothing in the Campaign Hub answers it. The Hub knows who the people are and
what they mean to this material; it has never heard them. The answer has to be
computed from the audio, on the machine that holds the audio.

The method is deliberately old and deliberately relative. Frames are reduced to
cepstral coefficients, the enrolled voice is modelled as a diagonal Gaussian
over them, and a stretch is scored not by its absolute likelihood but against
the rest of the same source. That ratio is what makes it survive a new room, a
new microphone and a new compression: everything that changed changed for both
sides of the comparison.

An absolute score would have to be calibrated per recording and would quietly
rot the first time the editor loaded a video from another studio.

Three answers are possible and the third is the important one. ``True`` and
``False`` are claims. ``None`` means the audio did not settle it, and the
editorial rule stands: a clip may not attribute speech to somebody on a guess.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import numpy as np


SAMPLE_RATE = 16000
_FRAME_S = 0.025
_HOP_S = 0.010
_N_FFT = 512
_N_MELS = 26
_N_CEPS = 13
# Frames quieter than this share of the median are silence or room tone, and
# scoring them says more about the room than about the speaker.
_VOICE_FLOOR = 0.35
# Below this many voiced frames a stretch is too short to judge: a second and a
# half of speech is roughly where the estimate stops moving.
_MIN_FRAMES = 150
# The decision is taken on the effect size, not on the raw log-ratio. The raw
# number is enormous and its scale depends on the recording — measured on the
# synthetic pair, +20 for the enrolled voice against -1744 for the other — so a
# fixed threshold on it would mean nothing on the next source. Dividing by the
# spread across frames gives a figure that travels.
#
# The band between the two is wide on purpose, and the asymmetry is real: the
# background model contains the enrolled speaker as well, so their own voice
# scores modestly positive while a stranger scores heavily negative.
_SAYS_YES = 1.0
_SAYS_NO = -1.0


def storage_dir() -> Path:
    """Where enrolled voices live. Never inside the repository."""
    base = Path(os.environ.get("FURIA_CLIPS_DATA_DIR") or (Path.home() / "FuriaClipsData"))
    return base / "voz"


def read_pcm(media_path: str | Path, start_s: float = 0.0, end_s: float | None = None) -> np.ndarray:
    """Mono 16 kHz samples, the same way the energy analysis already reads them."""
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error"]
    if start_s:
        command += ["-ss", f"{float(start_s):.3f}"]
    command += ["-i", str(media_path)]
    if end_s is not None:
        command += ["-t", f"{max(0.0, float(end_s) - float(start_s)):.3f}"]
    command += ["-vn", "-f", "s16le", "-acodec", "pcm_s16le",
                "-ar", str(SAMPLE_RATE), "-ac", "1", "pipe:1"]
    result = subprocess.run(command, capture_output=True, check=True)
    return np.frombuffer(result.stdout, dtype="<i2").astype(np.float32) / 32768.0


def _mel_filterbank() -> np.ndarray:
    def to_mel(hz):
        return 2595.0 * np.log10(1.0 + hz / 700.0)

    def to_hz(mel):
        return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)

    edges = to_hz(np.linspace(to_mel(300.0), to_mel(SAMPLE_RATE / 2 - 100), _N_MELS + 2))
    bins = np.floor((_N_FFT + 1) * edges / SAMPLE_RATE).astype(int)
    bank = np.zeros((_N_MELS, _N_FFT // 2 + 1), dtype=np.float32)
    for index in range(_N_MELS):
        left, centre, right = bins[index], bins[index + 1], bins[index + 2]
        if centre == left:
            centre = left + 1
        if right == centre:
            right = centre + 1
        if right >= bank.shape[1]:
            break
        bank[index, left:centre] = (np.arange(left, centre) - left) / (centre - left)
        bank[index, centre:right] = (right - np.arange(centre, right)) / (right - centre)
    return bank


_BANK: np.ndarray | None = None


def features(samples: np.ndarray) -> np.ndarray:
    """Cepstral coefficients for the voiced frames of this audio.

    Deliberately not mean-normalised. Subtracting each coefficient's mean is the
    textbook way to cancel the microphone and the room, and applied to a single
    stretch it also cancels the speaker: the mean vector becomes zero by
    construction, and with it every trace of who was talking. Measured, that left
    the comparison running on variance alone and the two synthetic voices barely
    separated.

    The channel is cancelled a level up instead, where the stretch is scored
    against the rest of the same recording — same room, same microphone, both
    sides of the ratio.
    """
    global _BANK
    if _BANK is None:
        _BANK = _mel_filterbank()
    if samples.size < int(_FRAME_S * SAMPLE_RATE) * 2:
        return np.zeros((0, _N_CEPS - 1), dtype=np.float32)

    emphasised = np.append(samples[0], samples[1:] - 0.97 * samples[:-1])
    frame_len, hop = int(_FRAME_S * SAMPLE_RATE), int(_HOP_S * SAMPLE_RATE)
    count = 1 + (len(emphasised) - frame_len) // hop
    if count < 1:
        return np.zeros((0, _N_CEPS - 1), dtype=np.float32)
    indices = np.arange(frame_len)[None, :] + hop * np.arange(count)[:, None]
    frames = emphasised[indices] * np.hamming(frame_len)

    power = (np.abs(np.fft.rfft(frames, _N_FFT)) ** 2) / _N_FFT
    energy = power.sum(axis=1)
    voiced = energy > max(np.median(energy) * _VOICE_FLOOR, 1e-8)
    if voiced.sum() < 2:
        return np.zeros((0, _N_CEPS - 1), dtype=np.float32)

    mel = np.log(power[voiced] @ _BANK.T + 1e-10)
    # DCT-II, orthonormal enough for this purpose; c0 is loudness, not identity.
    basis = np.cos(np.pi / _N_MELS * (np.arange(_N_MELS) + 0.5)[None, :] * np.arange(_N_CEPS)[:, None])
    return (mel @ basis.T)[:, 1:].astype(np.float32)


class VoicePrint:
    """A diagonal Gaussian over one speaker's cepstra."""

    def __init__(self, mean: np.ndarray, variance: np.ndarray, frames: int, label: str = ""):
        self.mean = np.asarray(mean, dtype=np.float32)
        # A floor on the variance: a coefficient that barely moved during
        # enrolment would otherwise dominate every later score.
        self.variance = np.maximum(np.asarray(variance, dtype=np.float32), 1e-3)
        self.frames = int(frames)
        self.label = label

    def log_likelihood(self, cepstra: np.ndarray) -> np.ndarray:
        deviation = cepstra - self.mean
        return -0.5 * (
            np.log(2 * np.pi * self.variance).sum() + (deviation ** 2 / self.variance).sum(axis=1)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "furia-voz-v1",
            "label": self.label,
            "frames": self.frames,
            "mean": [round(float(value), 6) for value in self.mean],
            "variance": [round(float(value), 6) for value in self.variance],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "VoicePrint":
        return cls(
            np.asarray(payload.get("mean") or [], dtype=np.float32),
            np.asarray(payload.get("variance") or [], dtype=np.float32),
            int(payload.get("frames") or 0),
            str(payload.get("label") or ""),
        )


def enroll_from_features(cepstra: np.ndarray, label: str) -> VoicePrint:
    if cepstra.shape[0] < _MIN_FRAMES:
        raise ValueError(
            f"A amostra tem só {cepstra.shape[0]} quadros de fala; são necessários pelo menos "
            f"{_MIN_FRAMES} (cerca de 1,5 s de voz limpa, sem música e sem outra pessoa falando)."
        )
    return VoicePrint(cepstra.mean(axis=0), cepstra.var(axis=0), cepstra.shape[0], label)


def enroll(media_path: str | Path, label: str = "renan", start_s: float = 0.0,
           end_s: float | None = None) -> dict[str, Any]:
    """Learn a voice from a clean sample and file it under the editor's data."""
    print_ = enroll_from_features(features(read_pcm(media_path, start_s, end_s)), label)
    target = storage_dir()
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{label}.json"
    path.write_text(json.dumps(print_.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"label": label, "frames": print_.frames, "arquivo": str(path)}


def load(label: str = "renan") -> VoicePrint | None:
    try:
        return VoicePrint.from_dict(json.loads((storage_dir() / f"{label}.json").read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError):
        return None


def identify(cepstra: np.ndarray, voice: VoicePrint, background: VoicePrint) -> dict[str, Any]:
    """Is this the enrolled speaker, judged against the rest of this recording.

    The comparison is what carries the method. An absolute likelihood would need
    calibrating for every new room; a ratio against the same recording cancels
    the room out, because the room is in both terms.
    """
    if cepstra.shape[0] < _MIN_FRAMES:
        return {
            "e_o_locutor": None,
            "razao": 0.0,
            "quadros": int(cepstra.shape[0]),
            "motivo": "fala insuficiente para decidir",
        }
    per_frame = voice.log_likelihood(cepstra) - background.log_likelihood(cepstra)
    ratio = float(per_frame.mean())
    strength = ratio / (float(per_frame.std()) + 1e-9)
    if strength >= _SAYS_YES:
        verdict: bool | None = True
    elif strength <= _SAYS_NO:
        verdict = False
    else:
        verdict = None
    return {
        "e_o_locutor": verdict,
        "forca": round(strength, 3),
        "razao": round(ratio, 3),
        "quadros": int(cepstra.shape[0]),
        "motivo": "" if verdict is not None else "áudio não decide; tratar como locutor não confirmado",
    }


def background_from_source(media_path: str | Path, duration_s: float, samples: int = 12) -> VoicePrint | None:
    """A model of everything this recording contains, the enrolled voice included.

    Sampled across the whole source rather than taken from one stretch, so a long
    monologue in the middle does not become the definition of "everyone else".
    """
    if duration_s <= 0:
        return None
    window = min(20.0, max(5.0, duration_s / (samples * 2)))
    collected = []
    for index in range(samples):
        start = duration_s * (index + 0.5) / samples - window / 2
        try:
            block = features(read_pcm(media_path, max(0.0, start), max(0.0, start) + window))
        except (subprocess.CalledProcessError, OSError, ValueError):
            continue
        if block.shape[0]:
            collected.append(block)
    if not collected:
        return None
    stacked = np.vstack(collected)
    return VoicePrint(stacked.mean(axis=0), stacked.var(axis=0), stacked.shape[0], "fundo")
