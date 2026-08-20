from scripts.score_chub_recall import load_highlights, score, score_benchmark


def test_score_counts_each_highlight_once_at_threshold():
    highlights = [(10.0, 20.0), (40.0, 50.0)]
    candidates = [(9.0, 21.0)]

    assert score(candidates, highlights, 0.10) == {
        "hits": 1,
        "total": 2,
        "recall": 0.5,
    }


def test_load_highlights_accepts_mcp_content_envelope(tmp_path):
    path = tmp_path / "blocks.json"
    path.write_text(
        '{"content": [{"text": "{\\"items\\": [{\\"highlights\\": [{\\"startS\\": 2, \\"endS\\": 5}]}]}"}]}',
        encoding="utf-8",
    )

    assert load_highlights(path) == [(2.0, 5.0)]


def test_score_benchmark_uses_the_passed_result():
    benchmark = {
        "conditions": [{
            "label": "fresh",
            "all_intervals": [[0, 10]],
            "all_guided_intervals": [[0, 10]],
        }]
    }

    result = score_benchmark(benchmark, [(1.0, 9.0)])

    assert result["conditions"][0]["label"] == "fresh"
    assert result["conditions"][0]["all_iou_recall_0_10"]["hits"] == 1
