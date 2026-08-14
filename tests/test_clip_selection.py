import unittest
from unittest.mock import patch

from modules.clip_selector import ClipSelector


class ClipSelectionTests(unittest.TestCase):
    def setUp(self):
        self.selector = ClipSelector(
            target_duration=20,
            max_clips=5,
            min_duration=5,
            max_duration=30,
        )

    def test_build_sentences_preserves_wording_and_splits_on_pause(self):
        segments = [
            {"start": 0.0, "end": 2.0, "text": "A primeira ideia."},
            {"start": 3.2, "end": 5.0, "text": "A segunda ideia."},
        ]
        sentences = self.selector._build_sentences(segments)
        self.assertEqual(len(sentences), 2)
        self.assertEqual(sentences[0]["text"], "A primeira ideia.")
        self.assertEqual(sentences[1]["start"], 3.2)

    def test_remove_overlaps_keeps_non_duplicate_candidates(self):
        clips = [
            {"start": 0.0, "end": 10.0, "duration": 10.0, "viral_score": 90},
            {"start": 2.0, "end": 9.0, "duration": 7.0, "viral_score": 80},
            {"start": 20.0, "end": 30.0, "duration": 10.0, "viral_score": 70},
        ]
        selected = self.selector._remove_overlaps(clips)
        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0]["viral_score"], 90)
        self.assertEqual(selected[1]["start"], 20.0)

    def test_nlp_selection_respects_max_duration(self):
        segments = [
            {"start": i * 4.0, "end": i * 4.0 + 3.5, "text": "Uma frase completa."}
            for i in range(12)
        ]
        sentences = self.selector._build_sentences(segments)
        clips = self.selector._select_with_nlp(sentences, [], "", None)
        self.assertTrue(clips)
        self.assertTrue(all(clip["duration"] <= 30 for clip in clips))

    def test_default_duration_policy_is_short_first_with_soft_ceiling(self):
        selector = ClipSelector()
        self.assertEqual(selector.min_duration, 8)
        self.assertEqual(selector.preferred_max_duration, 180.0)
        self.assertGreater(selector.max_duration, selector.preferred_max_duration)
        self.assertGreater(selector._duration_score(25), selector._duration_score(210))

    def test_gemini_prompt_does_not_impose_fixed_duration_range(self):
        selector = ClipSelector()
        prompt = selector._get_gemini_system_prompt()
        self.assertIn("menor trecho", prompt)
        self.assertIn("180 segundos como teto preferencial", prompt)
        self.assertNotIn("30 a 180 segundos", prompt)

    def test_ollama_prompt_does_not_impose_fixed_duration_range(self):
        selector = ClipSelector()
        prompt = selector._get_system_prompt()
        self.assertIn("menor trecho autossuficiente", prompt)
        self.assertIn("180 segundos", prompt)
        self.assertNotIn("30 a 180 segundos por clip", prompt)

    def test_auto_backend_uses_nlp_without_gemini_key(self):
        transcription = {
            "segments": [
                {"start": 0.0, "end": 4.0, "text": "A proposta é reduzir impostos com responsabilidade."},
                {"start": 4.2, "end": 8.0, "text": "O plano precisa de metas e prazo claro."},
                {"start": 8.2, "end": 12.0, "text": "Essa é a consequência para o cidadão."},
            ]
        }
        with patch.object(self.selector, "_select_with_llm", return_value=None):
            clips = self.selector.select_clips(
                transcription,
                settings={"ai_backend": "auto", "gemini_api_key": ""},
            )
        self.assertTrue(clips)
        self.assertEqual(self.selector.get_selection_source(), "nlp")

    @patch("modules.clip_selector.requests.post")
    def test_gemini_selector_uses_configured_model(self, post):
        post.return_value.status_code = 403
        sentences = self.selector._build_sentences([
            {"start": 0.0, "end": 4.0, "text": "A proposta exige uma resposta concreta."},
        ])

        self.selector._select_with_gemini(
            sentences,
            energy_profile=[],
            user_context="",
            settings={
                "gemini_api_key": "chave-de-teste",
                "gemini_model": "gemini-2.5-flash-lite",
            },
            emit_progress=None,
        )

        self.assertIn(
            "/models/gemini-2.5-flash-lite:generateContent",
            post.call_args.args[0],
        )


if __name__ == "__main__":
    unittest.main()
