import json

from modules.ab_exporter import build_run_export, export_run_candidates, load_run_export


def test_build_run_export_has_required_metadata_and_bounded_candidate_shape():
    payload = build_run_export(
        run_id="live A prioritize / 01",
        source_id="liveA",
        favorability_mode="prioritize",
        ai_backend="nlp",
        seeds_enabled=True,
        candidates=[{
            "clip_id": "c1",
            "start": 120.5,
            "end": 158.0,
            "score": 81,
            "favorability": {"available": True, "signal": 74},
            "editorial_family": "politico",
            "counterpunch": {"available": True, "answer_complete": True, "signal": 69},
            "context_seed_only": True,
            "review_required": True,
            "technical_gate": {"context_gate": True, "payoff_gate": True, "timing_gate": True},
            "transcript": "texto que não deve ser exportado",
            "source_path": "/private/video.mp4",
        }],
    )
    assert payload["run_id"] == "live_A_prioritize_01"
    assert payload["favorability_mode"] == "prioritize"
    assert payload["seeds_enabled"] is True
    assert payload["candidates_n"] == 1
    candidate = payload["candidates"][0]
    assert candidate["clip_id"] == "c1"
    assert candidate["favorability_score"] == 74
    assert candidate["coice_signal"] is True
    assert candidate["from_acervo_seed"] is True
    assert "texto que não deve ser exportado" not in str(payload)
    assert "/private/video" not in str(payload)


def test_export_run_candidates_writes_json_and_csv_under_requested_directory(tmp_path):
    result = export_run_candidates(
        run_id="run_liveA_off_001",
        source_id="liveA",
        favorability_mode="off",
        ai_backend="gemini",
        seeds_enabled=False,
        candidates=[],
        output_dir=tmp_path,
        generated_at="2026-08-22T15:00:00Z",
    )
    assert result["candidates_n"] == 0
    assert (tmp_path / "run_liveA_off_001.json").is_file()
    assert (tmp_path / "run_liveA_off_001.csv").is_file()
    payload = load_run_export("run_liveA_off_001", output_dir=tmp_path)
    assert payload["generated_at"] == "2026-08-22T15:00:00Z"
    assert json.loads((tmp_path / "run_liveA_off_001.json").read_text(encoding="utf-8"))["raw_transcript_included"] is False



def test_learning_endpoint_accepts_inline_items_and_reports_contract(monkeypatch, tmp_path):
    import app as app_module
    import modules.learning_importer as importer

    monkeypatch.setattr(importer, "DEFAULT_LEARNING_DIR", tmp_path / "learning")
    response = app_module.app.test_client().post(
        "/api/editorial/learning/import",
        json={"items": [
            {"clip_id": "inline-1", "label": "approved", "duration_sec": 38, "format_id": "vertical_916"},
            {"clip_id": "inline-2", "label": "rejected", "duration_sec": 12, "format_id": "unknown", "rejection_reason": "mid_sentence"},
        ]},
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["accepted"] == 2
    assert payload["rejected_rows"] == 0
    assert payload["sample_size_approved"] == 1
    assert payload["sample_size_rejected"] == 1
    assert payload["store_path_hint"] == "FuriaClipsData/learning"
    assert "inline-1" not in str(payload["prior"])


def test_learning_get_returns_aggregate_only_contract(monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "_get_approved_clip_prior", lambda: {
        "available": True,
        "eligible": True,
        "approved_count": 4,
        "rejected_count": 4,
        "headline_learning_thresholds": {"min_topic_format_count": 2, "min_overall_format_count": 4},
        "overall_by_format": {"vertical_916": 4},
        "raw_text": "must not be returned",
    })
    response = app_module.app.test_client().get("/api/editorial/learning")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["sample_size_approved"] == 4
    assert payload["raw_rows_exposed"] is False
    assert "must not be returned" not in str(payload)


def test_run_export_endpoint_and_get_support_json_and_csv(monkeypatch, tmp_path):
    import app as app_module
    import modules.ab_exporter as exporter

    monkeypatch.setattr(exporter, "DEFAULT_AB_RUN_DIR", tmp_path)
    response = app_module.app.test_client().post(
        "/api/editorial/runs/export",
        json={
            "run_id": "api-run-001",
            "source_id": "liveA",
            "favorability_mode": "require",
            "ai_backend": "nlp",
            "seeds_enabled": True,
            "candidates": [{"clip_id": "c1", "start": 0, "end": 30, "score": 80}],
        },
    )
    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    json_response = app_module.app.test_client().get("/api/editorial/runs/api-run-001/export?format=json")
    assert json_response.status_code == 200
    assert json_response.get_json()["favorability_mode"] == "require"
    csv_response = app_module.app.test_client().get("/api/editorial/runs/api-run-001/export?format=csv")
    assert csv_response.status_code == 200
    assert "clip_id" in csv_response.get_data(as_text=True)



def test_batch_rank_attaches_run_metadata_and_exports_candidates(monkeypatch, tmp_path):
    import app as app_module
    import modules.ab_exporter as exporter
    from modules.viral_ranker import ViralRanker

    monkeypatch.setattr(exporter, "DEFAULT_AB_RUN_DIR", tmp_path)
    monkeypatch.setattr(app_module, "get_feedback_calibration", lambda: {})
    monkeypatch.setattr(app_module, "get_all_settings", lambda: {"ai_backend": "nlp"})
    monkeypatch.setattr(
        ViralRanker,
        "rank_daily_portfolio",
        lambda self, candidates, **kwargs: {
            "clips": [{"clip_id": "ranked-1", "start": 0, "end": 30, "score": 80, "favorability_score": 70}],
            "summary": {"selected_count": 1},
        },
    )
    response = app_module.app.test_client().post(
        "/api/batch/rank",
        json={"source_id": "liveA", "candidates": [{"clip_id": "input-1"}], "options": {"run_id": "rank-api-001", "favorability_mode": "prioritize", "seeds_enabled": True}},
    )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["run_id"] == "rank-api-001"
    assert payload["favorability_mode"] == "prioritize"
    assert payload["seeds_enabled"] is True
    assert payload["summary"]["run_id"] == "rank-api-001"
    assert (tmp_path / "rank-api-001.json").is_file()
