import os
import tempfile
import unittest
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
