import unittest
from unittest.mock import patch

import requests

from modules.ai_backend import AIBackend


class AIBackendTests(unittest.TestCase):
    def test_auto_prefers_gemini_when_key_is_configured(self):
        backend = AIBackend("AUTO", {"gemini_api_key": "configured"})
        with patch.object(backend, "_generate_gemini", return_value="resposta Gemini") as gemini:
            with patch.object(backend, "_generate_ollama", return_value="resposta Ollama") as ollama:
                result = backend.generate("prompt")

        self.assertEqual(result, "resposta Gemini")
        gemini.assert_called_once_with("prompt", "", None)
        ollama.assert_not_called()

    def test_auto_uses_ollama_when_gemini_returns_no_text(self):
        backend = AIBackend("auto", {"gemini_api_key": "configured"})
        with patch.object(backend, "_generate_gemini", return_value="") as gemini:
            with patch.object(backend, "_generate_ollama", return_value="resposta Ollama") as ollama:
                result = backend.generate("prompt", "system")

        self.assertEqual(result, "resposta Ollama")
        gemini.assert_called_once_with("prompt", "system", None)
        ollama.assert_called_once_with("prompt", "system", None)

    def test_auto_without_key_skips_gemini_and_uses_ollama(self):
        backend = AIBackend("auto", {"gemini_api_key": ""})
        with patch.object(backend, "_generate_gemini") as gemini:
            with patch.object(backend, "_generate_ollama", return_value="resposta Ollama") as ollama:
                result = backend.generate("prompt")

        self.assertEqual(result, "resposta Ollama")
        gemini.assert_not_called()
        ollama.assert_called_once_with("prompt", "", None)

    def test_auto_exposes_local_provider_after_all_providers_are_empty(self):
        backend = AIBackend("auto", {"gemini_api_key": "configured"})
        with patch.object(backend, "_generate_gemini", return_value=""):
            with patch.object(backend, "_generate_ollama", return_value=""):
                result = backend.generate("prompt")

        self.assertEqual(result, "")
        self.assertEqual(backend.last_provider, "local")

    def test_provider_errors_are_retained_for_diagnostics(self):
        backend = AIBackend("ollama", {"ollama_url": "http://127.0.0.1:9"})
        with patch(
            "modules.ai_backend.requests.post",
            side_effect=requests.exceptions.ConnectionError("offline"),
        ):
            result = backend.generate("prompt")

        self.assertEqual(result, "")
        self.assertEqual(backend.last_provider, "local")
        self.assertIn("Ollama indisponível", backend.last_error)


if __name__ == "__main__":
    unittest.main()
