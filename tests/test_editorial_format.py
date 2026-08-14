import unittest

from modules.daily_portfolio import build_daily_portfolio
from modules.editorial_format import classify_editorial_format


class EditorialFormatTests(unittest.TestCase):
    def test_declared_institutional_format_preserves_composition(self):
        result = classify_editorial_format({"visual_format": "institucional"})
        self.assertEqual(result["visual_format"], "institucional")
        self.assertTrue(result["preserve_composition"])
        self.assertEqual(result["reframe_policy"], "preservar_composicao")

    def test_split_screen_with_reaction_cues_routes_to_react(self):
        result = classify_editorial_format(
            {"has_split_screen": True},
            "Renan reage à notícia e responde ao que foi dito.",
        )
        self.assertEqual(result["visual_format"], "react")
        self.assertTrue(result["preserve_composition"])

    def test_split_screen_without_semantic_evidence_stays_explicit(self):
        result = classify_editorial_format({"split_screen": True}, "Uma fala com duas fontes.")
        self.assertEqual(result["visual_format"], "split_screen")
        self.assertTrue(result["preserve_composition"])

    def test_single_stable_face_allows_conservative_reframe(self):
        result = classify_editorial_format(
            {"face_count": 1, "speaker_confidence": 0.93, "is_selfie": True},
            "Eu vou explicar o que aconteceu.",
        )
        self.assertEqual(result["visual_format"], "selfie_proximo")
        self.assertFalse(result["preserve_composition"])
        self.assertEqual(result["reframe_policy"], "reframe_se_seguro")

    def test_unknown_format_does_not_claim_reframe_safety(self):
        result = classify_editorial_format({}, "Texto sem sinal visual estruturado.")
        self.assertEqual(result["visual_format"], "desconhecido")
        self.assertTrue(result["preserve_composition"])
        self.assertLess(result["visual_format_confidence"], 0.5)

    def test_portfolio_exposes_format_counts_without_changing_family_caps(self):
        candidates = [
            {
                "source_id": "live-a",
                "editorial_family": "politico",
                "visual_format": "talking_head",
                "editorial_potential_score": 90,
                "confidence": 0.9,
                "text": "A proposta é clara e termina com uma conclusão.",
                "factors": {"context_completeness": 90, "completeness": 90, "clarity": 90},
            },
            {
                "source_id": "live-b",
                "editorial_family": "react",
                "visual_format": "react",
                "editorial_potential_score": 88,
                "confidence": 0.85,
                "text": "A notícia mostra o problema e a reação explica a consequência.",
                "factors": {"context_completeness": 88, "completeness": 88, "clarity": 88},
            },
        ]
        result = build_daily_portfolio(candidates, target_min=1, max_clips=2, min_score=60)
        self.assertEqual(result["summary"]["selected_count"], 2)
        self.assertEqual(result["summary"]["format_counts"], {"talking_head": 1, "react": 1})
        self.assertEqual({clip["daily_portfolio_format"] for clip in result["clips"]}, {"talking_head", "react"})


if __name__ == "__main__":
    unittest.main()
