import json

from modules.campaign_hub_memory import install_snapshot
from modules.editorial_benchmark import (
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

    target = save_benchmark(result, tmp_path / "benchmarks")
    stored = load_benchmark(result["benchmark_id"], tmp_path / "benchmarks")
    assert target.exists()
    assert stored["metrics"] == result["metrics"]
    assert list_benchmarks(tmp_path / "benchmarks")[0]["benchmark_id"] == result["benchmark_id"]
    json.loads(target.read_text(encoding="utf-8"))
