import unittest

from modules.editorial_ranker import EditorialRanker


class EditorialRankerTests(unittest.TestCase):
    def setUp(self):
        self.ranker = EditorialRanker()

    def test_returns_explainable_factors_and_legacy_score(self):
        clip = {
            "start": 0,
            "end": 32,
            "duration": 32,
            "text": "Você sabia? A verdade é que esse dado muda tudo. O resultado foi confirmado.",
        }
        result = self.ranker.score_clip(clip, user_context="encontre dados confirmados")
        self.assertIn("editorial_potential_score", result)
        self.assertEqual(result["viral_score"], result["editorial_potential_score"])
        self.assertGreaterEqual(result["confidence"], 0)
        self.assertLessEqual(result["confidence"], 1)
        self.assertIn("hook", result["factors"])
        self.assertIn("context_match", result["factors"])
        self.assertIn("completeness", result["factors"])

    def test_context_match_changes_with_requested_topic(self):
        clip = {"start": 0, "end": 20, "duration": 20, "text": "O orçamento público teve dados oficiais."}
        matching = self.ranker.score_clip(clip, user_context="encontre orçamento público")
        unrelated = self.ranker.score_clip(clip, user_context="encontre futebol e gols")
        self.assertGreater(matching["factors"]["context_match"], unrelated["factors"]["context_match"])

    def test_duplicate_clip_is_removed_or_penalized(self):
        clips = [
            {"start": 0, "end": 30, "duration": 30, "text": "Você sabia? A verdade sobre o orçamento foi revelada."},
            {"start": 2, "end": 28, "duration": 26, "text": "Você sabia? A verdade sobre o orçamento foi revelada."},
            {"start": 60, "end": 90, "duration": 30, "text": "Outra explicação com dados diferentes e conclusão completa."},
        ]
        ranked = self.ranker.rank_clips(clips)
        self.assertLessEqual(len(ranked), 2)
        self.assertTrue(any("diversity" in clip["factors"] for clip in ranked))


if __name__ == "__main__":
    unittest.main()
