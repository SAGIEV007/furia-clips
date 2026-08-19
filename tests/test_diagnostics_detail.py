"""What the diagnostics file has to carry for a bad run to be diagnosable.

The file recorded the gates and the score and 400 characters of text. That was
enough to recognise a clip and not enough to judge it: the run of 18/08/2026
produced four clips of exactly 180.0 seconds and the only way to see it was to
notice that several durations matched. The sentences inside each clip, and how
its edges came to be where they are, now travel with the decision.
"""

from app import _clip_transcript


SEGMENTS = [
    {"start": 0.0, "end": 10.0, "text": "Antes do corte."},
    {"start": 10.0, "end": 20.0, "text": "Primeira frase dentro."},
    {"start": 20.0, "end": 30.0, "text": "Segunda frase dentro."},
    {"start": 30.0, "end": 40.0, "text": "Depois do corte."},
]


def test_only_the_lines_inside_the_clip_travel_with_it():
    lines = _clip_transcript(SEGMENTS, 10.0, 30.0)

    assert [line["texto"] for line in lines] == ["Primeira frase dentro.", "Segunda frase dentro."]


def test_a_line_straddling_the_edge_is_kept():
    """A clip that opens mid-sentence must show the sentence it cut into."""
    lines = _clip_transcript(SEGMENTS, 15.0, 25.0)

    assert len(lines) == 2


def test_each_line_carries_its_own_time():
    lines = _clip_transcript(SEGMENTS, 10.0, 30.0)

    assert lines[0]["t"] == 10.0 and lines[0]["fim"] == 20.0


def test_a_clip_with_no_transcript_is_not_an_error():
    assert _clip_transcript(None, 0.0, 10.0) == []
    assert _clip_transcript([{"start": "x", "end": None, "text": "ruído"}], 0.0, 10.0) == []
