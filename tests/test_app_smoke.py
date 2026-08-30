import os
import tempfile
import unittest
from unittest.mock import Mock, patch

import app as furia_app
import database


class AppSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()
        cls.client = furia_app.app.test_client()

    def test_project_reload_returns_persisted_context_recovery(self):
        project_id = database.create_project("Reload de contexto", "uploads/reload-contexto.mp4")
        clip_id = database.save_clip(
            project_id,
            "exports/reload-contexto.mp4",
            12.0,
            28.0,
            16.0,
            76,
            True,
            0,
            "A decisão foi anunciada porque havia uma regra.",
        )
        recovery = {
            "applied": True,
            "reason": "antecedente recuperado antes de início truncado",
            "added_start": 9.5,
            "original_start": 12.0,
            "gap_seconds": 0.6,
        }
        database.update_clip_editorial_score(
            clip_id,
            76,
            {"context_completeness": 74},
            0.8,
            review_flags={"context_recovery_applied": True},
            context_recovery=recovery,
        )

        response = self.client.get(f"/api/projects/{project_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["clips"][0]["context_recovery"], recovery)

    def test_review_provenance_normalizes_confirmed_manual_transcript(self):
        provenance = furia_app._review_provenance(
            {"source": "manual_confirmed", "coverage": {"status": "covered"}},
            {"context_complete": True},
            "local_dossier",
        )

        self.assertEqual(provenance["transcript_source"], "manual")
        self.assertEqual(provenance["transcript_coverage_status"], "covered")
        self.assertFalse(provenance["transcript_semantic_identity_verified"])
        self.assertIsNone(provenance["transcript_end_ratio"])

    def test_review_provenance_coerces_legacy_identity_flag(self):
        provenance = furia_app._review_provenance(
            {
                "source": "public_subtitle",
                "coverage": {"status": "covered", "semantic_identity_verified": "false"},
            },
            {},
            "local_dossier",
        )

        self.assertFalse(provenance["transcript_semantic_identity_verified"])


    def test_review_provenance_exposes_bounded_temporal_coverage(self):
        provenance = furia_app._review_provenance(
            {
                "source": "public_subtitle",
                "coverage": {
                    "status": "partial",
                    "semantic_identity_verified": True,
                    "end_ratio": 1.7,
                },
            },
            {},
            "local_dossier",
        )

        self.assertTrue(provenance["transcript_semantic_identity_verified"])
        self.assertEqual(provenance["transcript_end_ratio"], 1.0)

    def test_review_provenance_ignores_invalid_legacy_end_ratio(self):
        provenance = furia_app._review_provenance(
            {"source": "public_subtitle", "coverage": {"status": "partial", "end_ratio": "not-a-number"}},
            {},
            "local_dossier",
        )

        self.assertIsNone(provenance["transcript_end_ratio"])

    def test_transcription_quality_exposes_reviewable_temporal_identity(self):
        coverage = furia_app._transcription_coverage_report({"segments": [{"start": 10, "end": 20}]}, 100)

        quality = {
            "status": coverage["status"],
            "end_ratio": coverage["end_ratio"],
            "semantic_identity_verified": bool(coverage["semantic_identity_verified"]),
            "review_required": coverage["status"] != "covered",
        }

        self.assertEqual(quality["status"], "partial")
        self.assertEqual(quality["end_ratio"], 0.2)
        self.assertFalse(quality["semantic_identity_verified"])
        self.assertTrue(quality["review_required"])

    def test_empty_transcription_coverage_requires_review(self):
        coverage = furia_app._transcription_coverage_report({"segments": []}, 120)

        self.assertEqual(coverage["status"], "empty")
        self.assertEqual(coverage["segment_count"], 0)
        self.assertFalse(coverage["semantic_identity_verified"])

    def test_status_event_payload_can_bind_to_job_id(self):
        captured = []
        with patch.object(furia_app.socketio, "emit", side_effect=lambda *args, **kwargs: captured.append((args, kwargs))):
            furia_app.emit_status("cut_complete", {"clips": []}, job_id="job-smoke-123")

        self.assertEqual(captured[0][0][0], "status")
        payload = captured[0][0][1]
        self.assertEqual(payload["job_id"], "job-smoke-123")
        self.assertEqual(payload["data"]["job_id"], "job-smoke-123")

    def test_transcript_archive_folder_endpoint_is_read_only_and_root_scoped(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            archive_dir = os.path.join(tmp_dir, "clip_hash")
            os.makedirs(archive_dir, exist_ok=True)
            with patch.object(furia_app, "PERSISTENT_TRANSCRIPTS_DIR", tmp_dir), patch.object(furia_app, "open_local_path") as opener:
                response = self.client.post("/api/editorial/transcripts/open", json={"relative_dir": "clip_hash"})
                traversal = self.client.post("/api/editorial/transcripts/open", json={"relative_dir": "../"})

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.get_json()["success"])
            opener.assert_called_once_with(archive_dir)
            self.assertEqual(traversal.status_code, 404)

    def test_render_presets_endpoint(self):
        response = self.client.get("/api/render-presets")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(any(item["id"] == "shorts" for item in payload["presets"]))

    def test_jobs_endpoint_is_available(self):
        response = self.client.get("/api/jobs")
        self.assertEqual(response.status_code, 200)
        self.assertIn("jobs", response.get_json())

    def test_legacy_process_status_is_read_only_and_versioned(self):
        original = dict(furia_app.current_task)
        try:
            furia_app.current_task.update({
                "active": True,
                "operation": "source_import",
                "job_id": "legacy-status-123",
                "started_at": "2026-08-20T12:00:00",
            })
            response = self.client.get("/api/process/status")
        finally:
            furia_app.current_task.clear()
            furia_app.current_task.update(original)

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["active"])
        self.assertEqual(payload["operation"], "source_import")
        self.assertEqual(payload["job_id"], "legacy-status-123")
        self.assertIn("program_version", payload)
        self.assertIn("program_revision", payload)

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

    def test_multimodal_nonverbal_moment_ignores_non_finite_timestamps_and_no_event(self):
        clips = [{"start": 0, "end": 20, "text": "fala"}]
        result = furia_app._attach_multimodal_visual_observations(
            clips,
            {
                "source_identity_status": "validated",
                "source_identity_confidence": 0.9,
                "nonverbal_moments": [{
                    "start": "nan",
                    "end": "00:10",
                    "kind": "berrante",
                    "description": "não deve ser anexado",
                    "confidence": 0.9,
                }],
            },
        )

        self.assertNotIn("nonverbal_moment", result[0])
        self.assertNotIn("nonverbal_moment_confidence", result[0])

    def test_multimodal_visual_flags_accept_schema_aliases_safely(self):
        clips = [{"start": 0, "end": 20, "text": "fala"}]
        result = furia_app._attach_multimodal_visual_observations(
            clips,
            {
                "source_identity_status": "validated",
                "source_identity_confidence": 0.9,
                "visual_observations": [{
                    "start": 0,
                    "end": 20,
                    "visual_format": "text_panel",
                    "has_text_panel": "true",
                    "fake_tweet": "false",
                    "split_screen": "0",
                    "confidence": "0.9",
                }],
            },
        )
        self.assertTrue(result[0]["text_panel"])
        self.assertFalse(result[0]["fake_tweet"])
        self.assertFalse(result[0]["split_screen"])


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

    def test_selected_gemini_reports_ollama_as_explicit_fallback(self):
        responses = [
            Mock(status_code=503),
            Mock(status_code=200, json=lambda: {"models": [{"name": "llama3.2:3b"}]}),
        ]
        with patch.object(furia_app.requests, "get", side_effect=responses):
            status = furia_app._check_ai_status({
                "ai_backend": "gemini",
                "gemini_api_key": "configured",
                "ollama_url": "http://127.0.0.1:11434",
                "ollama_model": "llama3.2:3b",
            })
        self.assertEqual(status["backend"], "ollama")
        self.assertEqual(status["fallback_from"], "gemini")
        self.assertIn("fallback", status["mode_label"])

    def test_selected_gemini_without_key_exposes_local_state(self):
        with patch.object(furia_app.requests, "get", side_effect=RuntimeError("offline")):
            status = furia_app._check_ai_status({
                "ai_backend": "gemini",
                "gemini_api_key": "",
                "ollama_url": "http://127.0.0.1:11434",
                "ollama_model": "llama3.2:3b",
            })
        self.assertEqual(status["status"], "no_key")
        self.assertEqual(status["fallback_from"], "gemini")
        self.assertIn("Gemini sem chave", status["mode_label"])


def test_editorial_data_endpoint_exposes_only_safe_summary():
    client = furia_app.app.test_client()
    with patch.object(furia_app, "get_editorial_data_summary", return_value={
        "data_dir": "C:/Users/editor/FuriaClipsData",
        "database_exists": True,
        "integrity": "ok",
        "projects": 2,
        "clips": 6,
        "feedback_events": 4,
    }):
        response = client.get("/api/editorial/data")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["integrity"] == "ok"
    assert "gemini_api_key" not in payload

def test_editorial_backup_endpoint_returns_download_metadata():
    client = furia_app.app.test_client()
    with patch.object(furia_app, "create_editorial_backup", return_value={
        "path": "C:/Users/editor/FuriaClipsData/backups/furia-editorial-backup-test.zip",
        "filename": "furia-editorial-backup-test.zip",
        "size_bytes": 512,
        "summary": {"integrity": "ok"},
    }):
        response = client.post("/api/editorial/backup")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["filename"] == "furia-editorial-backup-test.zip"
    assert "path" not in payload

def test_gemini_key_is_saved_to_explicit_persistent_env():
    with tempfile.TemporaryDirectory() as tmp_dir:
        env_path = os.path.join(tmp_dir, "config", "local.env")
        with patch.dict(os.environ, {"FURIA_CLIPS_ENV_FILE": env_path}, clear=False):
            furia_app._save_key_to_env("GEMINI_API_KEY", "test-only-secret")
        with open(env_path, "r", encoding="utf-8") as handle:
            content = handle.read()
        assert "GEMINI_API_KEY=test-only-secret" in content
        assert os.path.join(furia_app.BASE_DIR, ".env") not in env_path


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



def test_multimodal_nonverbal_moment_attaches_as_reviewable_evidence():
    clips = [{"start": 40, "end": 70, "text": "fala sobre a experiência"}]
    result = furia_app._attach_multimodal_visual_observations(
        clips,
        {
            "source_identity_status": "validated",
            "source_identity_confidence": 0.9,
            "nonverbal_moments": [{
                "start": "00:44",
                "end": "00:50",
                "kind": "berrante",
                "description": "Renan toca o berrante ao ar livre.",
                "editorial_value": "momento visual e sonoro complementar",
                "confidence": 0.9,
                "requires_visual_review": True,
            }],
        },
    )

    assert result[0]["nonverbal_moment_kind"] == "berrante"
    assert "toca o berrante" in result[0]["nonverbal_moment"]
    assert result[0]["nonverbal_moment_confidence"] == 0.9
    assert result[0]["nonverbal_moment_review_required"] is True


def test_multimodal_nonverbal_attaches_only_the_best_overlapping_moment():
    clips = [{"start": 20, "end": 40, "text": "fala"}]
    result = furia_app._attach_multimodal_visual_observations(
        clips,
        {
            "source_identity_status": "validated",
            "source_identity_confidence": 0.9,
            "nonverbal_moments": [
                {"start": 18, "end": 22, "kind": "risada", "description": "risada curta", "confidence": 0.95},
                {"start": 20, "end": 32, "kind": "cavalgada", "description": "cavalgada com interação com o ambiente", "confidence": 0.8},
            ],
        },
    )

    assert result[0]["nonverbal_moment_kind"] == "cavalgada"
    assert "cavalgada" in result[0]["nonverbal_moment"]


def test_multimodal_nonverbal_mismatch_is_discarded():
    clips = [{"start": 0, "end": 20, "text": "fala"}]
    result = furia_app._attach_multimodal_visual_observations(
        clips,
        {
            "source_identity_status": "mismatch",
            "source_identity_confidence": 0.99,
            "nonverbal_moments": [{
                "start": 0,
                "end": 20,
                "kind": "berrante",
                "description": "fonte incompatível",
                "confidence": 0.99,
            }],
        },
    )

    assert "nonverbal_moment" not in result[0]


def test_multimodal_nonverbal_unverified_confidence_is_capped_and_requires_review():
    clips = [{"start": 0, "end": 20, "text": "fala"}]
    result = furia_app._attach_multimodal_visual_observations(
        clips,
        {
            "source_identity_status": " unverified ",
            "source_identity_confidence": 0.2,
            "nonverbal_moments": [{
                "start": 0,
                "end": 20,
                "kind": "risada",
                "description": "risada observada",
                "confidence": 0.99,
            }],
        },
    )

    assert result[0]["nonverbal_moment_confidence"] == 0.35
    assert result[0]["nonverbal_moment_review_required"] is True


def test_multimodal_nonverbal_moment_ignores_non_finite_confidence():
    clips = [{"start": 0, "end": 20, "text": "fala"}]
    result = furia_app._attach_multimodal_visual_observations(
        clips,
        {
            "source_identity_status": "validated",
            "source_identity_confidence": 0.9,
            "nonverbal_moments": [{
                "start": 0,
                "end": 20,
                "kind": "risada",
                "description": "risada audível",
                "confidence": "nan",
            }],
        },
    )

    assert result[0]["nonverbal_moment_confidence"] == 0.0
    assert result[0]["nonverbal_moment_review_required"] is True


if __name__ == "__main__":
    unittest.main()



def test_campaign_hub_status_endpoint_exposes_read_only_snapshot_influence(tmp_path):
    snapshot_path = tmp_path / "profile.json"
    snapshot_path.write_text(
        '{"accounts":{"@renansantosmbl":{"hook_observations":['
        '{"hook":"news-peg","ratio":1.0},'
        '{"hook":"news-peg","ratio":1.1},'
        '{"hook":"news-peg","ratio":1.2}]}}}',
        encoding="utf-8",
    )
    client = furia_app.app.test_client()
    with patch.object(furia_app, "get_all_settings", return_value={"campaign_hub_snapshot_path": str(snapshot_path)}):
        response = client.get("/api/campaign-hub/status")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ready"
    assert payload["available"] is True
    assert payload["influences_ranking"] is True
    assert payload["read_only"] is True
    assert "não cria cortes" in payload["influence_scope"]



def test_campaign_hub_status_endpoint_reports_rich_acervo_counts(tmp_path):
    snapshot_path = tmp_path / "rich-profile.json"
    snapshot_path.write_text(
        '{"accounts":{"@renansantosmbl":{"acervo_blocks":[{"id":"b","startS":1,"endS":4,"video":{"youtubeId":"AbCdEfGhI12"}}],"acervo_pauta":[{"id":"p","startS":5,"endS":9,"video":{"youtubeId":"AbCdEfGhI12"}}]}}}',
        encoding="utf-8",
    )
    client = furia_app.app.test_client()
    with patch.object(furia_app, "get_all_settings", return_value={"campaign_hub_snapshot_path": str(snapshot_path)}):
        response = client.get("/api/campaign-hub/status")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["available"] is True
    assert payload["rich_context_available"] is True
    assert payload["total_acervo_blocks"] == 1
    assert payload["total_pauta_candidates"] == 1
    assert payload["read_only"] is True


def test_adjust_render_endpoint_renders_and_persists_derived_file(monkeypatch, tmp_path):
    import modules.video_cutter as video_module

    db_path = tmp_path / "adjust-render.sqlite"
    source_path = tmp_path / "source.mp4"
    rendered_path = tmp_path / "adjusted.mp4"
    source_path.write_bytes(b"source")
    rendered_path.write_bytes(b"rendered")

    with patch.object(database, "DB_PATH", str(db_path)):
        database.init_db()
        project_id = database.create_project("Projeto de ajuste", str(source_path))
        clip_id = database.save_clip(
            project_id,
            "exports/original.mp4",
            10.0,
            52.0,
            42.0,
            viral_score=80,
            transcript="A tese completa do trecho.",
        )
        fake_render = {
            "index": 0,
            "path": str(rendered_path),
            "start": 12.0,
            "end": 49.0,
            "duration": 37.0,
            "render_start": 12.0,
            "render_end": 49.0,
            "render_duration": 37.0,
            "render_boundary_policy": "word_timestamps_preserved",
            "validation": {"valid": True},
            "preset": "9:16",
        }
        monkeypatch.setattr(furia_app, "_resolve_media_input", lambda _value: str(source_path))
        monkeypatch.setattr(video_module.VideoCutter, "get_video_info", lambda _self, _path: {"format": {"duration": "60.0"}})
        monkeypatch.setattr(video_module.VideoCutter, "batch_cut", lambda *_args, **_kwargs: [fake_render])

        class ImmediateContext:
            job_id = "adjust-test-job"

            def update(self, **_kwargs):
                return {}

            def check_cancel(self):
                return None

        def immediate_submit(_job_type, target, project_id=None):
            target(ImmediateContext())
            return {"id": "adjust-test-job", "state": "completed", "stage": "completed", "type": _job_type, "project_id": project_id}

        monkeypatch.setattr(furia_app.job_manager, "submit", immediate_submit)
        monkeypatch.setattr(furia_app.socketio, "emit", lambda *_args, **_kwargs: None)
        response = furia_app.app.test_client().post(

            f"/api/clips/{clip_id}/adjust/render",
            json={
                "adjustment": {"start": 12.0, "end": 49.0},
                "source_duration": None,
                "render_preset": "shorts",
                "transcript_segments": [],
            },
        )

        assert response.status_code == 202
        payload = response.get_json()
        assert payload["success"] is True
        assert payload["job_id"] == "adjust-test-job"
        assert payload["operation"] == "adjust_clip_render"
        assert payload["render_status"] == "queued"
        persisted_adjustment = database.get_clip_feedback(clip_id)[0]["adjustments"]
        assert persisted_adjustment["render_status"] == "rendered"
        assert persisted_adjustment["render_path"] == str(rendered_path)

        persisted_clip = database.get_clip(clip_id)
        assert persisted_clip["file_path"] == str(rendered_path)
        assert persisted_clip["start_time"] == 10.0
        assert persisted_clip["end_time"] == 52.0


def test_project_reload_normalizes_persisted_clip_for_review_player(monkeypatch, tmp_path):
    db_path = tmp_path / "project-reload.sqlite"
    with patch.object(database, "DB_PATH", str(db_path)):
        database.init_db()
        project_id = database.create_project("Projeto recarregado", "uploads/source.mp4")
        clip_id = database.save_clip(
            project_id,
            "exports/original.mp4",
            10.0,
            52.0,
            42.0,
            transcript="A fala completa.",
        )
        database.update_clip_rendered_file(clip_id, "exports/ajustado.mp4")
        database.save_clip_adjustment(
            clip_id,
            {"start": 7.0, "end": 55.0, "duration": 48.0, "render_status": "rendered", "render_path": "exports/ajustado.mp4"},
        )
        monkeypatch.setattr(furia_app, "_resolve_media_input", lambda _value: None)
        response = furia_app.app.test_client().get(f"/api/projects/{project_id}")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["source_duration"] is None
    assert payload["source_duration_available"] is False
    clip = payload["clips"][0]
    assert clip["clip_id"] == clip_id
    assert clip["path"] == "exports/ajustado.mp4"
    assert clip["start"] == 7.0
    assert clip["end"] == 55.0
    assert clip["duration"] == 48.0
    assert clip["active_bounds"] == {"start": 7.0, "end": 55.0, "duration": 48.0}
    assert clip["active_start"] == 7.0
    assert clip["active_end"] == 55.0
    assert clip["active_duration"] == 48.0
    assert clip["active_render_status"] == "rendered"
    assert clip["latest_adjustment"]["render_path"] == "exports/ajustado.mp4"
    assert clip["original_bounds"] == {"start": 10.0, "end": 52.0, "duration": 42.0}


def test_project_payload_exposes_real_source_duration_on_each_clip(monkeypatch, tmp_path):
    db_path = tmp_path / "project-source-duration.sqlite"
    source_path = tmp_path / "source.mp4"
    source_path.write_bytes(b"source")
    with patch.object(database, "DB_PATH", str(db_path)):
        database.init_db()
        project_id = database.create_project("Projeto com duração", str(source_path))
        database.save_clip(project_id, "exports/clip.mp4", 2.0, 9.0, 7.0, transcript="Trecho")
        monkeypatch.setattr(furia_app, "_resolve_media_input", lambda _value: str(source_path))
        monkeypatch.setattr(furia_app, "_probe_video_duration_seconds", lambda _path: 123.5)
        response = furia_app.app.test_client().get(f"/api/projects/{project_id}")

    payload = response.get_json()
    assert response.status_code == 200
    assert payload["source_duration"] == 123.5
    assert payload["source_duration_available"] is True
    assert payload["clips"][0]["source_duration"] == 123.5
    assert payload["clips"][0]["original_bounds"] == {"start": 2.0, "end": 9.0, "duration": 7.0}


def test_adjust_render_claim_is_per_clip_and_releases_cleanly():

    furia_app.active_adjust_render_ids.clear()

    assert furia_app._claim_adjust_render(17) is True
    assert furia_app._claim_adjust_render(17) is False
    assert furia_app._claim_adjust_render(18) is True

    furia_app._release_adjust_render(17)
    furia_app._release_adjust_render(18)
    assert furia_app._claim_adjust_render(17) is True
    furia_app._release_adjust_render(17)


def test_adjust_render_claim_releases_when_cutter_constructor_fails(monkeypatch, tmp_path):
    import modules.video_cutter as video_module

    db_path = tmp_path / "adjust-render-constructor.sqlite"
    source_path = tmp_path / "source.mp4"
    source_path.write_bytes(b"source")
    with patch.object(database, "DB_PATH", str(db_path)):
        database.init_db()
        project_id = database.create_project("Projeto com falha", str(source_path))
        clip_id = database.save_clip(project_id, "exports/original.mp4", 10.0, 52.0, 42.0)

        class BrokenCutter:
            def __init__(self, *_args, **_kwargs):
                raise RuntimeError("falha de inicialização simulada")

        monkeypatch.setattr(furia_app, "_resolve_media_input", lambda _value: str(source_path))
        monkeypatch.setattr(video_module, "VideoCutter", BrokenCutter)

        class ImmediateContext:
            job_id = "adjust-constructor-failure"

            def update(self, **_kwargs):
                return {}

            def check_cancel(self):
                return None

        def immediate_submit(_job_type, target, project_id=None):
            target(ImmediateContext())
            return {"id": "adjust-constructor-failure", "state": "completed", "stage": "completed", "type": _job_type, "project_id": project_id}

        monkeypatch.setattr(furia_app.job_manager, "submit", immediate_submit)
        furia_app.active_adjust_render_ids.clear()
        response = furia_app.app.test_client().post(
            f"/api/clips/{clip_id}/adjust/render",
            json={"adjustment": {"start": 12.0, "end": 49.0}, "source_duration": 60.0},
        )

    assert response.status_code == 500
    assert furia_app.active_adjust_render_ids == set()



def test_adjustment_framing_inference_defaults_to_safe_original_composition():
    import json

    assert furia_app._infer_adjustment_preserve_original_aspect({
        "score_factors": json.dumps({
            "_review_metadata": {"framing": {"mode": "reframe_9_16"}},
        }),
    }) is True
    assert furia_app._infer_adjustment_preserve_original_aspect({
        "framing": {"mode": "face_tracking", "tracking_applied": True},
    }) is True
    assert furia_app._infer_adjustment_preserve_original_aspect({
        "framing": {"mode": "original_16_9"},
    }) is True
    assert furia_app._infer_adjustment_preserve_original_aspect({
        "framing": {"mode": "unknown", "tracking_applied": False},
    }) is False




def test_performance_dashboard_endpoint_uses_summarize_snapshots(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "perf.sqlite"))
    database.init_db()

    database.save_performance_snapshot({
        "content_key": "smoke-dashboard-1",
        "platform": "instagram",
        "format_id": "vertical_916",
        "account_key": "@renansantosmbl",
        "observation_window": "today",
        "region": "brasil",
        "published_at": "2026-08-14T10:00:00-03:00",
        "collected_at": "2026-08-14T12:00:00-03:00",
        "views": 5000,
        "likes": 400,
        "comments": 50,
        "shares": 25,
        "saves": 25,
        "ranking_position": 1,
        "xp": 100,
        "collection_state": "observed",
        "source": "manual_or_authorized_export",
    })
    client = furia_app.app.test_client()
    response = client.get("/api/performance/dashboard?platform=instagram&observation_window=today")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert "dashboard" in payload
    assert payload["dashboard"]["count"] == 1
    assert payload["dashboard"]["total_views"] == 5000
    assert payload["dashboard"]["top_platform"] == "instagram"
    assert payload["dashboard"]["top_format"] == "vertical_916"


class YouTubeApiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()
        cls.client = furia_app.app.test_client()

    def test_youtube_probe_rejects_invalid_url(self):
        response = self.client.post("/api/youtube/probe", json={"url": "not-a-youtube-url"})
        assert response.status_code == 400
        payload = response.get_json()
        assert payload["success"] is False

    def test_youtube_metadata_rejects_invalid_url(self):
        response = self.client.post("/api/youtube/metadata", json={"url": "not-a-youtube-url"})
        assert response.status_code == 400
        payload = response.get_json()
        assert payload["success"] is False

    def test_youtube_probe_accepts_valid_url(self):
        response = self.client.post(
            "/api/youtube/probe",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        source = payload["source"]
        assert source["platform"] == "youtube"
        assert source["source_video_id"] == "dQw4w9WgXcQ"
        assert "source_title" in source
    def test_youtube_probe_accepts_shorts_url(self):
        response = self.client.post(
            "/api/youtube/probe",
            json={"url": "https://www.youtube.com/shorts/dQw4w9WgXcQ"},
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        source = payload["source"]
        assert source["platform"] == "youtube"
        assert source["source_video_id"] == "dQw4w9WgXcQ"

    def test_youtube_probe_accepts_live_url(self):
        response = self.client.post(
            "/api/youtube/probe",
            json={"url": "https://www.youtube.com/live/dQw4w9WgXcQ"},
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        source = payload["source"]
        assert source["platform"] == "youtube"
        assert source["source_video_id"] == "dQw4w9WgXcQ"
    def test_youtube_metadata_accepts_valid_url(self):
        fake_metadata = {
            "video_id": "dQw4w9WgXcQ",
            "title": "Never Gonna Give You Up",
            "duration": 212.0,
            "uploader": "Rick Astley",
            "is_live": False,
        }
        with patch("app.fetch_youtube_metadata", return_value=fake_metadata) as mock_md:
            response = self.client.post(
                "/api/youtube/metadata",
                json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            )
            assert response.status_code == 200
            payload = response.get_json()
            assert payload["success"] is True
            assert payload["metadata"]["title"] == "Never Gonna Give You Up"
            mock_md.assert_called_once()
    def test_youtube_download_rejects_invalid_url(self):
        response = self.client.post(
            "/api/youtube/download",
            json={"url": "not-a-youtube-url", "destination": "/tmp"},
        )
        assert response.status_code == 400
        payload = response.get_json()
        assert payload["success"] is False

    def test_youtube_download_accepts_valid_url(self):
        fake_result = {"path": "/tmp/fake.mp4", "source_id": "dQw4w9WgXcQ"}
        with patch("app.download_youtube_video", return_value=fake_result) as mock_dl:
            response = self.client.post(
                "/api/youtube/download",
                json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "destination": "/tmp"},
            )
            assert response.status_code == 200
            payload = response.get_json()
            assert payload["success"] is True
            assert payload["result"]["path"] == "/tmp/fake.mp4"
            mock_dl.assert_called_once()



    def test_health_endpoint_returns_ok(self):
        response = self.client.get("/health")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["status"] == "ok"
        assert "version" in payload
        assert "db" in payload
        assert "exists" in payload["db"]
        assert "whisper" in payload
        assert "engine" in payload["whisper"]
