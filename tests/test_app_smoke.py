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
