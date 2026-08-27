"""What the diagnostics file has to carry for a bad run to be diagnosable.

The file recorded the gates and the score and 400 characters of text. That was
enough to recognise a clip and not enough to judge it: the run of 18/08/2026
produced four clips of exactly 180.0 seconds and the only way to see it was to
notice that several durations matched. The sentences inside each clip, and how
its edges came to be where they are, now travel with the decision.
"""

import json

import modules.editorial_benchmark as editorial_benchmark
from app import _candidate_rejection_summary, _clip_transcript, _write_selection_diagnostics


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


def test_zero_result_summary_uses_selector_diagnostics():
    count, summary = _candidate_rejection_summary(
        [],
        {
            "primary_count": 5,
            "final_count": 0,
            "reason": "short_source",
            "hard_negatives": [
                {"reason": "duplicate_same_closing"},
                {"reason": "already_exported_fingerprint"},
            ],
        },
    )

    assert count == 5
    assert "duplicate_same_closing (1)" in summary
    assert "already_exported_fingerprint (1)" in summary
    assert "short_source (1)" in summary
    assert "não registrados" not in summary


def test_selection_diagnostics_materialize_hard_negative_benchmark(tmp_path, monkeypatch):
    data_dir = tmp_path / "furia-data"
    benchmark_dir = tmp_path / "benchmarks"
    monkeypatch.setenv("FURIA_CLIPS_DATA_DIR", str(data_dir))
    monkeypatch.setattr(editorial_benchmark, "DEFAULT_BENCHMARK_DIR", benchmark_dir)
    diagnostics = {
        "processing_identity": "identity-test",
        "transcript_digest": "digest-test",
        "hard_negatives": [{
            "start": 10,
            "end": 20,
            "reason": "duplicate_overlap",
            "text_preview": "Uma janela quase válida.",
            "winner": {"start": 8, "end": 22, "score": 80, "text_preview": "A janela completa."},
        }],
    }

    _write_selection_diagnostics(
        job_id="job-test",
        video_path=str(tmp_path / "live.mp4"),
        duration_s=120,
        selection_source="nlp",
        diagnostics=diagnostics,
        clips=[],
        deferred=[],
        segments=SEGMENTS,
    )

    reports = list((data_dir / "diagnostics").glob("selecao-*.json"))
    benchmarks = list(benchmark_dir.glob("*.json"))
    assert len(reports) == 1
    assert len(benchmarks) == 1
    report = json.loads(reports[0].read_text(encoding="utf-8"))
    benchmark = json.loads(benchmarks[0].read_text(encoding="utf-8"))
    assert report["hard_negative_benchmark"]["schema"] == "hard-negative-v1"
    assert benchmark["metrics"]["item_count"] == 1
    assert benchmark["metrics"]["measurement_status"] == "descriptive_only"
