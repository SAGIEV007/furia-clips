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

    def test_audio_energy_uses_windows_inside_clip(self):
        result = self.ranker.score_clip(
            {
                "start": 10,
                "end": 14,
                "duration": 4,
                "text": "A fala termina com uma conclusão clara.",
            },
            energy_profile=[
                {"time": 0, "energy_normalized": 0.1},
                {"time": 10, "energy_normalized": 0.8},
                {"time": 11, "energy_normalized": 1.0},
                {"time": 12, "energy_normalized": 0.9},
                {"time": 20, "energy_normalized": 0.1},
            ],
        )
        self.assertGreater(result["factors"]["audio_energy"], 80)

    def test_visual_change_density_is_exposed_when_scene_data_exists(self):
        result = self.ranker.score_clip(
            {
                "start": 0,
                "end": 20,
                "duration": 20,
                "text": "A proposta é clara e muda a vida das pessoas.",
                "scene_changes": [3, 7, 11, 15, 18],
            }
        )
        self.assertGreater(result["factors"]["visual_change_density"], 50)

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
