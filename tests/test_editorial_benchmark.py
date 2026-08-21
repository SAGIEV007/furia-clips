import json

from modules.campaign_hub_memory import install_snapshot
from modules.editorial_benchmark import (
    assess_measurement,
    build_hard_negative_benchmark,
    compare_candidates,
    interval_iou,
    list_benchmarks,
    load_benchmark,
    map_interval_to_local,
    save_benchmark,
)
from modules.editorial_block_memory import get_block


BLOCK_ID = "block-b354"


def _payload():
    return {
        "version": "benchmark-test",
        "default_account": "@renansantosmbl",
        "accounts": {"@renansantosmbl": {"platform": "youtube", "hook_observations": []}},
        "records": {
            "sources": [{"id": "video-1", "youtube_id": "abc", "duration_s": 600}],
            "blocks": [{
                "id": BLOCK_ID,
                "video_id": "video-1",
                "title": "Kim mobiliza a campanha",
                "start_s": 6142.56,
                "end_s": 6692.0,
                "renan_speaking": False,
                "risk_flags": ["linguagem_ofensiva"],
            }],
            "highlights": [
                {"id": "h1", "block_id": BLOCK_ID, "start_s": 6289.36, "end_s": 6293.36, "text": "Nós somos um exército indestrutível.", "reason": "força coletiva"},
                {"id": "h2", "block_id": BLOCK_ID, "start_s": 6365.8, "end_s": 6370.96, "text": "Nós fundamos o nosso partido.", "reason": "origem do partido"},
                {"id": "h3", "block_id": BLOCK_ID, "start_s": 6631.04, "end_s": 6637.76, "text": "Se a gente não se empenhar.", "reason": "consequência dos 45 dias"},
            ],
        },
    }


def test_hard_negative_benchmark_keeps_unlabeled_items_descriptive_only():
    result = build_hard_negative_benchmark(
        [
            {
                "start": 10.0,
                "end": 22.0,
                "reason": "duplicate_overlap",
                "candidate_origin": "local_fallback",
                "score": 74,
                "confidence": 0.66,
                "text_preview": "A janela quase válida.",
                "winner": {"start": 8.0, "end": 24.0, "score": 82, "text_preview": "A janela vencedora."},
            },
            {"start": 40.0, "end": 48.0, "reason": "touching_sibling_lost_to_existing_candidate"},
            {"start": 90.0, "end": 80.0, "reason": "invalid"},
        ],
        source_name="live.mp4",
        source_duration=600,
        processing_identity="identity-1",
        transcript_digest="digest-1",
        decision_records=[
            {"id": "hard-negative-1", "decision": "rejected", "reason_code": "duplicata", "note": "A vencedora contém o mesmo pensamento."},
        ],
    )

    assert result["schema"] == "hard-negative-v1"
    assert result["source"]["name"] == "live.mp4"
    assert len(result["items"]) == 2
    assert result["items"][0]["human_decision"] == "rejected"
    assert result["items"][1]["human_decision"] == "unlabeled"
    assert result["metrics"]["decision_counts"]["rejected"] == 1
    assert result["metrics"]["decision_counts"]["unlabeled"] == 1
    assert result["metrics"]["human_decisions_complete"] is False
    assert result["metrics"]["measurement_status"] == "descriptive_only"
    assert any("sem decisão humana" in warning for warning in result["metrics"]["warnings"])


def test_hard_negative_benchmark_does_not_promote_unknown_decisions():
    result = build_hard_negative_benchmark(
        [{"id": "hn-1", "start": 0, "end": 10, "reason": "duplicate_similarity"}],
        decision_records={"hn-1": {"decision": "approved_by_model"}},
    )

    assert result["items"][0]["human_decision"] == "unlabeled"
    assert result["metrics"]["labeled_count"] == 0


def test_map_interval_uses_downloaded_block_timeline():
    mapped = map_interval_to_local(
        6289.36,
        6293.36,
        source_duration=549.45,
        reference_start=6142.56,
        reference_end=6692.0,
    )
    assert mapped["timeline_mapping"] == "downloaded_block_timeline"
    assert mapped["start"] == 146.8
    assert mapped["end"] == 150.8


def test_iou_is_explainable():
    assert interval_iou((10, 20), (15, 25)) == 0.3333333333333333
    assert interval_iou((10, 20), None) == 0.0


def test_compare_persists_recall_and_classifications(tmp_path):
    memory = tmp_path / "profile.json"
    install_snapshot(_payload(), destination=memory)
    block = get_block(BLOCK_ID, str(memory))
    result = compare_candidates(
        block,
        [
            {"id": "candidate-covered", "start": 146.2, "end": 151.4, "review_flags": {"context_complete": True, "payoff_complete": True}},
            {"id": "candidate-duplicate", "start": 146.4, "end": 151.2},
            {"id": "candidate-miss", "start": 300, "end": 320},
        ],
        source_duration=549.45,
        source_name="b354.mp4",
    )
    assert result["metrics"]["reference_count"] == 3
    assert result["metrics"]["covered_count"] == 1
    assert result["metrics"]["coverage_recall"] == 0.3333
    assert result["metrics"]["duplicate_candidates"] == 1
    assert result["comparisons"][0]["classification"] == "furia_better"
    assert result["comparisons"][1]["classification"] == "campaign_hub_better"
    assert result["comparisons"][0]["timeline_mapping"] == "downloaded_block_timeline"

    assert result["measurement"]["reliable"] is True
    assert result["measurement"]["status"] == "reliable"
    assert result["metrics"]["measurement_reliable"] is True

    target = save_benchmark(result, tmp_path / "benchmarks")
    stored = load_benchmark(result["benchmark_id"], tmp_path / "benchmarks")
    assert target.exists()
    assert stored["metrics"] == result["metrics"]
    assert list_benchmarks(tmp_path / "benchmarks")[0]["benchmark_id"] == result["benchmark_id"]
    json.loads(target.read_text(encoding="utf-8"))


def test_missing_source_marks_measurement_unreliable(tmp_path):
    """A 0/3 caused by an unmapped timeline must not look like a 0/3 of selection."""
    memory = tmp_path / "profile.json"
    install_snapshot(_payload(), destination=memory)
    block = get_block(BLOCK_ID, str(memory))
    result = compare_candidates(
        block,
        [{"id": "candidate-local", "start": 146.2, "end": 151.4}],
        source_duration=None,
        source_name="",
    )
    # Without the local duration the highlights stay on absolute seconds.
    assert result["references"][0]["timeline_mapping"] == "source_timeline"
    assert result["references"][0]["local_start"] == 6289.36
    # The recall is still 0/3, but it is now explicitly not comparable.
    assert result["metrics"]["coverage_recall"] == 0.0
    assert result["measurement"]["reliable"] is False
    assert result["measurement"]["status"] == "unmapped_timeline"
    assert result["measurement"]["mapping_required"] is True
    assert result["measurement"]["mapping_applied"] is False
    assert result["measurement"]["warnings"]
    assert result["metrics"]["measurement_reliable"] is False
    assert result["source"]["mapping_applied"] is False


def test_full_length_source_stays_comparable_without_mapping():
    """Candidates cut from the whole live share the absolute timeline."""
    measurement = assess_measurement(
        source_duration=7241.0,
        reference_start=6142.56,
        reference_end=6692.0,
        timeline_mapping="source_timeline",
        reference_count=3,
        candidate_count=7,
    )
    assert measurement["reliable"] is True
    assert measurement["source_is_full_length"] is True
    assert measurement["warnings"] == []


def test_block_starting_at_zero_needs_no_mapping():
    measurement = assess_measurement(
        source_duration=None,
        reference_start=0.0,
        reference_end=549.44,
        timeline_mapping="source_timeline",
        reference_count=3,
        candidate_count=7,
    )
    assert measurement["reliable"] is True
    assert measurement["mapping_required"] is False


def test_empty_candidates_are_reported_as_such():
    measurement = assess_measurement(
        source_duration=549.449,
        reference_start=6142.56,
        reference_end=6692.0,
        timeline_mapping="downloaded_block_timeline",
        reference_count=3,
        candidate_count=0,
    )
    assert measurement["reliable"] is False
    assert measurement["status"] == "no_candidates"
