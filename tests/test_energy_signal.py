"""The audio measurement reaching the decision it was measured for.

The energy profile was computed for every source — 4.418 windows on the
73-minute press conference of 18/08/2026 — passed into the Gemini and Ollama
selectors, and read by neither. Only the keyword fallback ever looked at it, so
the measurement only mattered on the path taken when everything else had already
failed.

Where the voice rises is the signal the editor keeps asking for by another name:
the "coice", the moment somebody is cornered. It now travels into the prompt.
"""

from modules.clip_selector import ClipSelector


def _blocks():
    return [
        {"index": 0, "start": 0.0, "end": 10.0, "duration": 10, "text": "Abertura calma."},
        {"index": 1, "start": 10.0, "end": 20.0, "duration": 10, "text": "Ele levanta a voz aqui."},
        {"index": 2, "start": 20.0, "end": 30.0, "duration": 10, "text": "E volta ao tom normal."},
    ]


# Median 1.0; the middle block peaks well above it and the first sits below.
PROFILE = [0.4] * 10 + [1.0] * 5 + [2.4] * 5 + [1.0] * 10


def test_a_raised_voice_is_marked():
    marked = ClipSelector._mark_energy(_blocks(), PROFILE)

    assert marked[1]["energy_mark"] == "voz elevada"


def test_a_quiet_stretch_is_marked_too():
    marked = ClipSelector._mark_energy(_blocks(), PROFILE)

    assert marked[0]["energy_mark"] == "voz baixa"


def test_an_ordinary_stretch_gets_no_mark():
    """Marking everything would be the same as marking nothing."""
    marked = ClipSelector._mark_energy(_blocks(), PROFILE)

    assert "energy_mark" not in marked[2]


def test_the_mark_reaches_the_prompt():
    selector = ClipSelector(target_duration=45, max_clips=10, min_duration=20, max_duration=600)
    marked = ClipSelector._mark_energy(_blocks(), PROFILE)

    prompt = selector._build_gemini_prompt(marked, "", None)

    assert "[voz elevada]" in prompt


def test_no_audio_is_not_an_error():
    assert "energy_mark" not in ClipSelector._mark_energy(_blocks(), None)[1]
    assert "energy_mark" not in ClipSelector._mark_energy(_blocks(), [])[1]


def test_the_comparison_is_relative_to_the_source():
    """A studio and a street have different floors; an absolute level travels badly."""
    loud_room = [value * 50 for value in PROFILE]

    assert ClipSelector._mark_energy(_blocks(), loud_room)[1]["energy_mark"] == "voz elevada"
