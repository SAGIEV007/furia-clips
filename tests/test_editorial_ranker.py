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

    def test_same_topic_in_different_windows_receives_diversity_penalty(self):
        clips = [
            {
                "source_id": "live-1", "start": 0, "end": 35, "duration": 35,
                "text": "A reforma tributária aumenta impostos e prejudica pequenas empresas. A proposta precisa ser revista.",
            },
            {
                "source_id": "live-1", "start": 180, "end": 216, "duration": 36,
                "text": "Pequenas empresas sofrem com os impostos da reforma tributária. Precisamos rever essa proposta.",
            },
            {
                "source_id": "live-1", "start": 420, "end": 456, "duration": 36,
                "text": "A segurança pública precisa de investigação eficiente e punição para criminosos violentos.",
            },
        ]
        ranked = self.ranker.rank_clips(clips)
        tax_clips = [
            clip for clip in ranked
            if "empresa" in clip.get("text", "").lower()
            and "imposto" in clip.get("text", "").lower()
        ]
        security_clips = [
            clip for clip in ranked
            if "segurança" in clip.get("text", "").lower()
        ]
        self.assertLessEqual(len(tax_clips), 2)
        self.assertTrue(any(clip.get("diversity_penalty", 0) > 0 for clip in tax_clips))
        self.assertEqual(len(security_clips), 1)

    def test_cliffhanger_is_labeled_and_scores_below_equivalent_conclusion(self):
        cliffhanger = self.ranker.score_clip({
            "start": 0, "end": 28, "duration": 28,
            "text": "A prova está nos logs e nos IPs. Acompanhe porque amanhã vou mostrar todos os detalhes.",
        })
        conclusion = self.ranker.score_clip({
            "start": 0, "end": 28, "duration": 28,
            "text": "A prova está nos logs e nos IPs. Por isso, fica claro que a acusação precisa ser verificada publicamente.",
        })
        self.assertEqual(cliffhanger["closure_type"], "cliffhanger")
        self.assertEqual(conclusion["closure_type"], "conclusion")
        self.assertLess(cliffhanger["factors"]["completeness"], conclusion["factors"]["completeness"])

    def test_argument_structure_rewards_premise_reason_and_conclusion(self):
        argument = self.ranker.score_clip({
            "start": 0, "end": 35, "duration": 35,
            "text": "Se a investigação não tem consequência, significa impunidade. Por isso, a lei precisa ser aplicada com transparência.",
        })
        isolated = self.ranker.score_clip({
            "start": 0, "end": 35, "duration": 35,
            "text": "A lei precisa ser aplicada.",
        })
        self.assertGreater(argument["factors"]["argument_structure"], isolated["factors"]["argument_structure"])
        self.assertIn("argument_structure", argument["factors"])

    def test_multimodal_visual_observation_is_explained(self):
        result = self.ranker.score_clip({
            "start": 0,
            "end": 42,
            "duration": 42,
            "text": "O post mostra a prova e a reação explica o contexto.",
            "visual_format": "fake_tweet",
            "fake_tweet": True,
            "visual_observation": "post social e reação no mesmo quadro",
            "visual_observation_confidence": 0.9,
        })
        self.assertEqual(result["visual_format"], "fake_tweet")
        self.assertEqual(result["visual_observation"], "post social e reação no mesmo quadro")
        self.assertEqual(result["visual_observation_confidence"], 0.9)
        self.assertTrue(result["review_flags"]["visual_observation_available"])
        self.assertTrue(result["preserve_composition"])

    def test_explicit_external_evidence_preserves_composition(self):
        result = self.ranker.score_clip({
            "start": 0,
            "end": 42,
            "duration": 42,
            "text": "O vídeo mostra a prova e depois eu explico o que aconteceu.",
            "visual_format": "evidencia_externa",
        })
        self.assertEqual(result["visual_format"], "evidencia_externa")
        self.assertTrue(result["preserve_composition"])
        self.assertEqual(result["reframe_policy"], "preservar_composicao")
        self.assertTrue(result["review_flags"]["preserve_composition"])

    def test_shorter_complete_clip_is_preferred_without_fixed_duration(self):
        text = (
            "Você sabia? Isso é absurdo! A prova está nos dados. "
            "Por isso, fica claro que a proposta precisa ser revista."
        )
        short = self.ranker.score_clip({"start": 0, "end": 35, "duration": 35, "text": text})
        long = self.ranker.score_clip({"start": 0, "end": 220, "duration": 220, "text": text})
        self.assertEqual(short["duration_preference"]["status"], "curto_preferencial")
        self.assertLess(short["duration_fit"], 101)
        self.assertLess(long["duration_fit"], short["duration_fit"])
        self.assertEqual(long["duration_preference"]["status"], "excecao_contextual")
        self.assertTrue(long["review_flags"]["duration_exception"])

    def test_duration_policy_is_explainable_in_review_flags(self):
        result = self.ranker.score_clip({
            "start": 0,
            "end": 240,
            "duration": 240,
            "text": "Uma análise que ainda não terminou e precisa de revisão",
        })
        self.assertEqual(result["review_flags"]["duration_preference"], "longo_para_revisao")
        self.assertFalse(result["review_flags"]["duration_exception"])


if __name__ == "__main__":
    unittest.main()


def test_context_quality_penalizes_abrupt_start_and_unresolved_question():
    ranker = EditorialRanker()
    abrupt = ranker.score_clip({
        "start": 0, "end": 30, "duration": 30,
        "text": "E por isso a proposta foi rejeitada no final",
        "starts_mid_sentence": True,
        "question_detected": False,
        "payoff_complete": False,
        "context_complete": False,
    })
    complete = ranker.score_clip({
        "start": 0, "end": 34, "duration": 34,
        "text": "Por que isso aconteceu? A resposta está nos registros oficiais. Por isso, a apuração deve continuar.",
        "question_detected": True,
        "question_answer_complete": True,
        "evidence_present": True,
        "payoff_complete": True,
        "context_complete": True,
        "qa_bridge": True,
    })
    assert abrupt["review_flags"]["starts_mid_sentence"] is True
    assert complete["review_flags"]["question_answer_complete"] is True
    assert complete["factors"]["context_quality"] > abrupt["factors"]["context_quality"]
    assert complete["editorial_potential_score"] > abrupt["editorial_potential_score"]


    def test_observed_high_impact_openers_score_as_hooks(self):
        observed = self.ranker.score_clip({
            "start": 0,
            "end": 30,
            "duration": 30,
            "text": "Presta muita atenção! Leia de novo: este é o Brasil que vamos receber.",
        })
        plain = self.ranker.score_clip({
            "start": 0,
            "end": 30,
            "duration": 30,
            "text": "Este é o Brasil que vamos receber, segundo os dados apresentados.",
        })
        self.assertGreater(observed["factors"]["hook"], plain["factors"]["hook"])
        self.assertGreaterEqual(observed["factors"]["hook"], 70)
