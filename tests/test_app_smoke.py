import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as furia_app
import database


class AppSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()
        cls.client = furia_app.app.test_client()

    def test_render_presets_endpoint(self):
        response = self.client.get("/api/render-presets")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(any(item["id"] == "shorts" for item in payload["presets"]))

    def test_jobs_endpoint_is_available(self):
        response = self.client.get("/api/jobs")
        self.assertEqual(response.status_code, 200)
        self.assertIn("jobs", response.get_json())

    def test_settings_do_not_return_api_key(self):
        database.set_setting("gemini_api_key", "secret-for-test")
        response = self.client.get("/api/settings")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["gemini_api_key"], "")
        self.assertTrue(payload["gemini_api_key_configured"])

    def test_file_traversal_is_blocked(self):
        response = self.client.get("/api/files?path=../")
        self.assertEqual(response.status_code, 403)

    def test_source_destination_expands_environment_and_reuses_folder(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.dict(os.environ, {"FURIA_TEST_DOWNLOAD_DIR": tmp_dir}):
                resolved = furia_app._resolve_source_destination("$FURIA_TEST_DOWNLOAD_DIR")
            self.assertEqual(resolved, os.path.abspath(tmp_dir))

    def test_source_destination_rejects_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "video.mp4")
            with open(file_path, "w", encoding="utf-8") as handle:
                handle.write("placeholder")
            with self.assertRaises(OSError):
                furia_app._resolve_source_destination(file_path)

    def test_source_destination_ignores_ui_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            resolved = furia_app._resolve_source_destination(
                "A pasta será escolhida ao importar",
                {"source_download_dir": tmp_dir},
            )
            self.assertEqual(resolved, os.path.abspath(tmp_dir))

    def test_source_destination_ignores_persisted_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            resolved = furia_app._resolve_source_destination(
                "",
                {"source_download_dir": "A pasta será escolhida ao importar"},
            )
            self.assertTrue(os.path.isdir(resolved))
            self.assertNotIn("A pasta será escolhida ao importar", resolved)

    def test_multimodal_visual_observation_attaches_by_overlap(self):
        clips = [{"start": 20, "end": 55, "text": "fala"}]
        result = furia_app._attach_multimodal_visual_observations(
            clips,
            {
                "source_identity_status": "validated",
                "source_identity_confidence": 0.9,
                "visual_observations": [
                    {
                        "start": "00:15",
                        "end": "00:45",
                        "visual_format": "fake_tweet",
                        "fake_tweet": True,
                        "composition_note": "post social e reação no mesmo quadro",
                        "confidence": 0.9,
                    }
                ]
            },
        )
        self.assertEqual(result[0]["visual_format"], "fake_tweet")
        self.assertTrue(result[0]["fake_tweet"])
        self.assertEqual(result[0]["visual_observation_confidence"], 0.9)

    def test_batch_rank_returns_quality_gated_portfolio(self):
        response = self.client.post(
            "/api/batch/rank",
            json={
                "candidates": [
                    {
                        "source_id": "live-a",
                        "start": 0,
                        "end": 40,
                        "duration": 40,
                        "text": "A proposta econômica termina com uma solução clara.",
                        "editorial_potential_score": 80,
                        "factors": {"context_completeness": 80, "completeness": 85, "clarity": 80},
                    },
                    {
                        "source_id": "live-b",
                        "start": 10,
                        "end": 50,
                        "duration": 40,
                        "text": "Uma reação engraçada fecha com uma piada.",
                        "editorial_potential_score": 80,
                        "factors": {"context_completeness": 80, "completeness": 85, "clarity": 80},
                    },
                ],
                "options": {"target_min": 1, "max_clips": 2, "min_score": 55},
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["summary"]["selected_count"], 2)
        self.assertIn("rejections", payload["summary"])

    def test_batch_rank_rejects_non_list_candidates(self):
        response = self.client.post("/api/batch/rank", json={"candidates": {}})
        self.assertEqual(response.status_code, 400)

    def test_clip_adjustment_endpoint_is_non_destructive(self):
        response = self.client.post(
            "/api/clips/adjust",
            json={
                "clip": {"start": 10, "end": 25, "duration": 15},
                "start": 10.8,
                "end": 24.2,
                "transcript_segments": [
                    {"start": 11.0, "end": 15.0},
                    {"start": 18.0, "end": 24.0},
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertFalse(payload["mutated"])
        self.assertEqual(payload["clip"]["start"], 11.0)
        self.assertEqual(payload["clip"]["end"], 24.0)

    def test_clip_adjustment_endpoint_rejects_invalid_clip(self):
        response = self.client.post("/api/clips/adjust", json={"clip": []})
        self.assertEqual(response.status_code, 400)

    def test_auto_ai_status_falls_back_to_local_nlp(self):
        with patch.object(furia_app.requests, "get", side_effect=RuntimeError("offline")):
            status = furia_app._check_ai_status({
                "ai_backend": "auto",
                "gemini_api_key": "",
                "ollama_url": "http://127.0.0.1:11434",
                "ollama_model": "llama3.2:3b",
            })
        self.assertEqual(status["mode"], "nlp")
        self.assertEqual(status["backend"], "auto")
        self.assertIn("NLP local", status["mode_label"])

    def test_gemini_status_keeps_key_out_of_query_string(self):
        calls = []

        class Response:
            status_code = 200

        def fake_get(url, **kwargs):
            calls.append((url, kwargs))
            return Response()

        with patch.object(furia_app.requests, "get", side_effect=fake_get):
            status = furia_app._check_ai_status({
                "ai_backend": "gemini",
                "gemini_api_key": "secret-for-test",
                "ollama_url": "http://127.0.0.1:11434",
            })

        self.assertEqual(status["mode"], "gemini")
        self.assertEqual(len(calls), 1)
        self.assertNotIn("secret-for-test", calls[0][0])
        self.assertEqual(calls[0][1]["headers"]["x-goog-api-key"], "secret-for-test")


if __name__ == "__main__":
    unittest.main()


    def test_editorial_data_endpoint_exposes_only_safe_summary(self):
        with patch.object(furia_app, "get_editorial_data_summary", return_value={
            "data_dir": "C:/Users/editor/FuriaClipsData",
            "database_exists": True,
            "integrity": "ok",
            "projects": 2,
            "clips": 6,
            "feedback_events": 4,
        }):
            response = self.client.get("/api/editorial/data")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["integrity"], "ok")
        self.assertNotIn("gemini_api_key", payload)

    def test_editorial_backup_endpoint_returns_download_metadata(self):
        with patch.object(furia_app, "create_editorial_backup", return_value={
            "path": "C:/Users/editor/FuriaClipsData/backups/furia-editorial-backup-test.zip",
            "filename": "furia-editorial-backup-test.zip",
            "size_bytes": 512,
            "summary": {"integrity": "ok"},
        }):
            response = self.client.post("/api/editorial/backup")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["filename"], "furia-editorial-backup-test.zip")
        self.assertNotIn("path", payload)

    def test_gemini_key_is_saved_to_explicit_persistent_env(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_path = os.path.join(tmp_dir, "config", "local.env")
            with patch.dict(os.environ, {"FURIA_CLIPS_ENV_FILE": env_path}, clear=False):
                furia_app._save_key_to_env("GEMINI_API_KEY", "test-only-secret")
            with open(env_path, "r", encoding="utf-8") as handle:
                content = handle.read()
            self.assertIn("GEMINI_API_KEY=test-only-secret", content)
            self.assertNotIn(os.path.join(furia_app.BASE_DIR, ".env"), env_path)


def test_multimodal_visual_observation_rejects_mismatched_source():
    clips = [{"start": 20, "end": 55, "text": "fala"}]
    result = furia_app._attach_multimodal_visual_observations(
        clips,
        {
            "source_identity_status": "mismatch",
            "visual_observations": [{
                "start": "00:15", "end": "00:45", "visual_format": "fake_tweet", "confidence": 0.99,
            }],
        },
    )
    assert "visual_format" not in result[0]
    assert result[0]["multimodal_identity_status"] == "mismatch"
    assert result[0]["visual_observation_review_required"] is True
    assert "incompatível" in result[0]["visual_observation_review_reason"]


def test_multimodal_visual_observation_is_capped_without_identity_validation():
    clips = [{"start": 20, "end": 55, "text": "fala"}]
    result = furia_app._attach_multimodal_visual_observations(
        clips,
        {
            "source_identity_status": "unverified",
            "source_identity_confidence": 0.2,
            "visual_observations": [{
                "start": "00:15", "end": "00:45", "visual_format": "entrevista", "confidence": 0.99,
            }],
        },
    )
    assert result[0]["visual_observation_confidence"] == 0.35
    assert result[0]["visual_observation_review_required"] is True


def test_coerce_bool_handles_json_and_form_style_values():
    assert furia_app._coerce_bool(True) is True
    assert furia_app._coerce_bool(False) is False
    assert furia_app._coerce_bool("false") is False
    assert furia_app._coerce_bool("0") is False
    assert furia_app._coerce_bool("off") is False
    assert furia_app._coerce_bool("true") is True
    assert furia_app._coerce_bool(None, default=True) is True


def test_campaign_hub_memory_status_endpoint_is_safe():
    response = furia_app.app.test_client().get("/api/campaign-hub/memory/status")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["source"] == "campaign_hub_local_memory"
    assert payload["read_only_runtime"] is True
    assert "token" not in str(payload).lower()


def test_campaign_hub_memory_import_endpoint_installs_authorized_json(tmp_path):
    import io
    import json

    payload = {
        "version": "http-test",
        "default_account": "@renansantosmbl",
        "accounts": {
            "@renansantosmbl": {
                "platform": "instagram",
                "hook_observations": [
                    {"hook": "news-peg", "ratio": 1.0},
                    {"hook": "news-peg", "ratio": 1.1},
                    {"hook": "news-peg", "ratio": 1.2},
                ],
            }
        },
        "records": {"blocks": [{"id": "http-block", "start_s": 0, "end_s": 10}]},
        "metadata": {"privacy_contract": {"raw_media_included": False}},
    }
    destination = tmp_path / "profile.json"
    with patch.object(furia_app, "get_all_settings", return_value={"campaign_hub_snapshot_path": str(destination)}):
        response = furia_app.app.test_client().post(
            "/api/campaign-hub/memory/import",
            data={"snapshot": (io.BytesIO(json.dumps(payload).encode("utf-8")), "export.json")},
            content_type="multipart/form-data",
        )
    assert response.status_code == 200
    result = response.get_json()
    assert result["success"] is True
    assert result["record_counts"]["blocks"] == 1
    assert destination.is_file()


def test_editorial_block_interval_export_validates_and_returns_download_path(tmp_path):
    from modules import video_cutter

    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")

    def fake_cut(_self, _video, _start, _end, output_path, **_kwargs):
        with open(output_path, "wb") as handle:
            handle.write(b"rendered")
        return output_path

    with patch.object(furia_app, "_resolve_media_input", return_value=str(source)), \
         patch.object(furia_app, "_probe_video_duration_seconds", return_value=120.0), \
         patch.object(video_cutter.VideoCutter, "cut_clip", new=fake_cut):
        response = furia_app.app.test_client().post(
            "/api/editorial/blocks/export",
            json={"video_path": "workspace/uploads/source.mp4", "block_id": "b1", "start": 10, "end": 30},
        )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["source_mode"] == "local_interval"
    assert payload["duration"] == 20
    assert payload["download_url"].startswith("/workspace/")


def test_editorial_block_interval_export_rejects_source_overflow(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    with patch.object(furia_app, "_resolve_media_input", return_value=str(source)), \
         patch.object(furia_app, "_probe_video_duration_seconds", return_value=10.0):
        response = furia_app.app.test_client().post(
            "/api/editorial/blocks/export",
            json={"video_path": "source.mp4", "start": 10, "end": 40},
        )
    assert response.status_code == 400
    assert "apenas" in response.get_json()["error"]


def test_editorial_block_interval_export_maps_downloaded_block_timeline(tmp_path):
    from modules import video_cutter

    source = tmp_path / "downloaded-block.mp4"
    source.write_bytes(b"source")

    def fake_cut(_self, _video, start, end, output_path, **_kwargs):
        assert start == 0.0
        assert abs(end - 549.44) < 1e-6
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as handle:
            handle.write(b"rendered")
        return output_path

    with patch.object(furia_app, "_resolve_media_input", return_value=str(source)), \
         patch.object(furia_app, "_probe_video_duration_seconds", return_value=553.527), \
         patch.object(video_cutter.VideoCutter, "cut_clip", new=fake_cut):
        response = furia_app.app.test_client().post(
            "/api/editorial/blocks/export",
            json={"video_path": "downloaded-block.mp4", "block_id": "b354", "start": 6142.56, "end": 6692.0},
        )

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["timeline_mapping"] == "downloaded_block_timeline"
    assert payload["requested_start"] == 6142.56
    assert payload["start"] == 0.0


def _benchmark_memory_payload():
    return {
        "version": "api-benchmark-test",
        "default_account": "@renansantosmbl",
        "accounts": {"@renansantosmbl": {"platform": "youtube", "hook_observations": []}},
        "records": {
            "sources": [{"id": "video-api", "title": "Evento API"}],
            "blocks": [{
                "id": "block-api",
                "video_id": "video-api",
                "title": "Bloco API",
                "start_s": 100,
                "end_s": 200,
                "renan_speaking": False,
            }],
            "highlights": [{
                "id": "highlight-api",
                "block_id": "block-api",
                "start_s": 120,
                "end_s": 125,
                "text": "Destaque API",
                "reason": "teste",
            }],
        },
    }


def test_highlight_export_maps_downloaded_block_timeline(tmp_path):
    from modules.campaign_hub_memory import install_snapshot

    memory_path = tmp_path / "profile.json"
    install_snapshot(_benchmark_memory_payload(), destination=memory_path)
    source_path = tmp_path / "source.mp4"
    source_path.write_bytes(b"fake-media")
    rendered_path = tmp_path / "rendered.mp4"
    with patch.object(furia_app, "get_all_settings", return_value={"campaign_hub_snapshot_path": str(memory_path)}), \
         patch.object(furia_app, "_resolve_media_input", return_value=str(source_path)), \
         patch.object(furia_app, "_probe_video_duration_seconds", return_value=100.0), \
         patch("modules.video_cutter.VideoCutter.cut_clip", return_value=str(rendered_path)):
        response = furia_app.app.test_client().post(
            "/api/editorial/blocks/highlights/export",
            json={"video_path": str(source_path), "block_id": "block-api", "highlight_id": "highlight-api"},
        )
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["timeline_mapping"] == "downloaded_block_timeline"
    assert payload["start"] == 20.0
    assert payload["end"] == 25.0


def test_benchmark_api_persists_and_lists_local_comparison(tmp_path):
    from modules.campaign_hub_memory import install_snapshot
    import modules.editorial_benchmark as benchmark

    memory_path = tmp_path / "profile.json"
    install_snapshot(_benchmark_memory_payload(), destination=memory_path)
    source_path = tmp_path / "source.mp4"
    source_path.write_bytes(b"fake-media")
    with patch.object(furia_app, "get_all_settings", return_value={"campaign_hub_snapshot_path": str(memory_path)}), \
         patch.object(furia_app, "_resolve_media_input", return_value=str(source_path)), \
         patch.object(furia_app, "_probe_video_duration_seconds", return_value=100.0), \
         patch.object(benchmark, "DEFAULT_BENCHMARK_DIR", tmp_path / "benchmarks"):
        client = furia_app.app.test_client()
        response = client.post(
            "/api/editorial/benchmark",
            json={
                "block_id": "block-api",
                "video_path": str(source_path),
                "candidates": [{"id": "candidate-api", "start": 20, "end": 25, "review_flags": {"context_complete": True, "payoff_complete": True}}],
                "benchmark_version": "api-test",
            },
        )
        payload = response.get_json()
        listing = client.get("/api/editorial/benchmark")
    assert response.status_code == 200
    assert payload["success"] is True
    assert payload["metrics"]["coverage_recall"] == 1.0
    assert listing.status_code == 200
    assert listing.get_json()["benchmarks"][0]["benchmark_id"].endswith("api-test")


def test_hard_negative_decision_api_appends_history(tmp_path):
    import modules.editorial_benchmark as benchmark

    payload = benchmark.build_hard_negative_benchmark(
        [{"id": "hn-api", "start": 10, "end": 20, "reason": "duplicate_overlap"}],
        processing_identity="api-identity",
        transcript_digest="api-digest",
    )
    benchmark.save_benchmark(payload, tmp_path / "benchmarks")
    with patch.object(benchmark, "DEFAULT_BENCHMARK_DIR", tmp_path / "benchmarks"):
        client = furia_app.app.test_client()
        response = client.post(
            "/api/editorial/benchmark/hard-negatives-api/decisions",
            json={
                "annotator_id": "editor-api",
                "decisions": {"hn-api": {"decision": "rejected", "reason_code": "sem_payoff"}},
            },
        )
        detail = client.get("/api/editorial/benchmark/hard-negatives-api")
    assert response.status_code == 404

    benchmark_id = payload["benchmark_id"]
    with patch.object(benchmark, "DEFAULT_BENCHMARK_DIR", tmp_path / "benchmarks"):
        client = furia_app.app.test_client()
        response = client.post(
            f"/api/editorial/benchmark/{benchmark_id}/decisions",
            json={
                "annotator_id": "editor-api",
                "decisions": {"hn-api": {"decision": "rejected", "reason_code": "sem_payoff"}},
            },
        )
        detail = client.get(f"/api/editorial/benchmark/{benchmark_id}")
    assert response.status_code == 200
    assert response.get_json()["decision_status"] == "complete"
    stored = detail.get_json()["benchmark"]["items"][0]
    assert stored["human_decision"] == "rejected"
    assert stored["decision_history"][0]["annotator_id"] == "editor-api"


def test_cut_endpoint_rejects_invalid_processing_interval_before_queueing():
    with tempfile.TemporaryDirectory() as tmp_dir:
        source = Path(tmp_dir) / "live.mp4"
        source.write_bytes(b"placeholder")
        with patch.object(furia_app, "_resolve_media_input", return_value=str(source)), \
             patch.object(furia_app, "_probe_video_duration_seconds", return_value=7200.0):
            response = furia_app.app.test_client().post(
                "/api/process/cut",
                json={"video_path": str(source), "processing_start": "01:00", "processing_end": "00:30"},
            )
    assert response.status_code == 400
    assert "maior que o início" in response.get_json()["error"]


def test_complete_endpoint_rejects_interval_outside_source_before_queueing():
    with tempfile.TemporaryDirectory() as tmp_dir:
        source = Path(tmp_dir) / "live.mp4"
        source.write_bytes(b"placeholder")
        with patch.object(furia_app, "_resolve_media_input", return_value=str(source)), \
             patch.object(furia_app, "_probe_video_duration_seconds", return_value=600.0):
            response = furia_app.app.test_client().post(
                "/api/process/complete",
                json={"video_path": str(source), "processing_start": "00:00", "processing_end": "20:00"},
            )
    assert response.status_code == 400
    assert "ultrapassa a duração" in response.get_json()["error"]


def test_job_event_and_diagnostic_routes_return_safe_payloads():
    from modules.job_manager import JobManager

    with tempfile.TemporaryDirectory() as tmp_dir:
        manager = JobManager(os.path.join(tmp_dir, "jobs.sqlite3"), max_workers=1)
        try:
            created = manager.create("api-observability")
            manager.record_event(
                created["id"],
                event_name="api.test",
                stage="testing",
                message="Evento de smoke test",
                details={"source": "pytest"},
            )
            with patch.object(furia_app, "job_manager", manager):
                client = furia_app.app.test_client()
                events_response = client.get(f"/api/jobs/{created['id']}/events")
                diagnostic_response = client.get(f"/api/jobs/{created['id']}/diagnostic")
                missing_response = client.get("/api/jobs/does-not-exist/events")
            assert events_response.status_code == 200
            assert events_response.get_json()["count"] >= 2
            assert diagnostic_response.status_code == 200
            diagnostic = diagnostic_response.get_json()
            assert diagnostic["job"]["id"] == created["id"]
            assert diagnostic["schema_version"] == "job-diagnostic-v1"
            assert missing_response.status_code == 404
        finally:
            manager.shutdown()
