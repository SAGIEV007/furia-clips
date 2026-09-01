import pytest
from modules.clip_selector import ClipSelector


def _block(start, end, text="texto"):
    return {
        "text": text,
        "start": float(start),
        "end": float(end),
        "duration": float(end) - float(start),
        "speaker": "",
        "speakers": [],
        "speaker_change_detected": False,
        "speaker_confidence": 0.9,
        "overlap_suspected": False,
        "timing_ambiguous": False,
        "timing_confidence": 0.9,
        "word_spans": [],
        "segment_ids": [],
    }


def _transcription(blocks):
    return {"segments": blocks}


def _settings():
    return {"ai_backend": "nlp", "editorial_context": {}}


def _energy(start, value):
    return {"start": float(start), "energy": float(value)}


def test_energy_window_keeps_best_candidate_within_30s():
    selector = ClipSelector()
    blocks = [_block(0, 50), _block(10, 60), _block(100, 150), _block(200, 250)]
    transcription = _transcription(blocks)
    settings = _settings()
    energy = [_energy(0, 10), _energy(10, 100), _energy(100, 30), _energy(200, 20)]

    clips = selector.select_clips(
        transcription, energy_profile=energy, user_context="", settings=settings
    )
    starts = sorted([float(c["start"]) for c in clips])
    assert starts == [0, 100, 200]


def test_energy_window_ignored_when_no_profile():
    selector = ClipSelector()
    blocks = [_block(0, 50), _block(10, 60), _block(100, 150)]
    transcription = _transcription(blocks)
    settings = _settings()

    clips = selector.select_clips(
        transcription, energy_profile=None, user_context="", settings=settings
    )
    starts = sorted([float(c["start"]) for c in clips])
    assert starts == [0, 10, 100]
