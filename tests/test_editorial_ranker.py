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

    def test_direct_audience_challenge_is_a_hook_but_generic_challenge_is_not(self):
        direct = self.ranker.score_clip({
            "start": 0,
            "end": 24,
            "duration": 24,
            "text": "Meu desafio para vocês é conferir os dados e cobrar uma resposta concreta.",
        })
        generic = self.ranker.score_clip({
            "start": 0,
            "end": 24,
            "duration": 24,
            "text": "O primeiro desafio da proposta é organizar os dados antes da decisão.",
        })

        assert direct["factors"]["hook"] > generic["factors"]["hook"]

    def test_quality_scorecard_separates_context_editorial_technical_and_confidence(self):
        result = self.ranker.score_clip({
            "start": 0,
            "end": 28,
            "duration": 28,
            "text": "Você sabia? A proposta tem dados oficiais e termina com uma solução clara.",
            "speaker_review_required": True,
        })
        scorecard = result["quality_scorecard"]
        self.assertEqual(set(("context", "editorial_strength", "technical", "confidence", "status", "gate_status")), set(scorecard))
        self.assertGreaterEqual(scorecard["context"], 0)
        self.assertLessEqual(scorecard["context"], 100)
        self.assertEqual(scorecard["status"], "review_required")
        self.assertEqual(scorecard["confidence"], result["confidence"] * 100)

    def test_context_recovery_survives_ranking_and_review_flags(self):
        recovery = {
            "applied": True,
            "reason": "antecedente recuperado antes de início truncado",
            "added_start": 0.0,
            "original_start": 5.0,
            "gap_seconds": 1.0,
        }
        result = self.ranker.score_clip({
            "start": 0.0,
            "end": 20.0,
            "duration": 20.0,
            "text": "A decisão foi anunciada. Isso aconteceu porque havia uma regra clara e verificável.",
            "context_recovery": recovery,
        })
        self.assertEqual(result["context_recovery"], recovery)
        self.assertTrue(result["review_flags"]["context_recovery_applied"])

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

    def test_similar_text_with_distinct_context_is_not_hard_dropped(self):
        first = {
            "source_id": "live-1",
            "start": 0,
            "end": 30,
            "duration": 30,
            "text": "A proposta é clara e precisa de resposta. A conclusão é inevitável.",
            "closure_type": "conclusion",
            "question_answer_complete": True,
            "payoff_complete": True,
            "chapter_primary_id": 1,
            "topic_signature": "politica:proposta-resposta",
        }
        second = {
            **first,
            "start": 180,
            "end": 210,
            "closure_type": "cliffhanger",
            "question_answer_complete": False,
            "payoff_complete": False,
            "chapter_primary_id": 2,
        }

        penalty = self.ranker._diversity_penalty(second, [first])
        reason = self.ranker._diversity_reason(second, [first])

        self.assertLess(penalty, 70)
        self.assertEqual(reason, "texto semelhante, mas contexto/payoff distinto")

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


def test_scorecard_status_matches_non_clean_technical_gate():
    ranker = EditorialRanker()
    result = ranker.score_clip({
        "start": 0,
        "end": 30,
        "duration": 30,
        "text": "A proposta precisa de uma resposta clara porque os dados oficiais mostram uma consequência concreta para o cidadão.",
        "context_complete": True,
        "payoff_complete": False,
    })

    assert result["technical_gate"]["status"] == "review"
    assert result["quality_scorecard"]["gate_status"] == "review"
    assert result["quality_scorecard"]["status"] == "review_required"


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


def test_ranker_does_not_treat_nonfinite_flags_as_true():
    from modules.editorial_ranker import _coerce_flag

    assert _coerce_flag(float("nan")) is False
    assert _coerce_flag(float("inf")) is False
    assert _coerce_flag(float("nan"), default=True) is True


def test_ranker_does_not_promote_textual_false_speaker_boundary():
    ranker = EditorialRanker()
    result = ranker.score_clip({
        "start": 0,
        "end": 20,
        "duration": 20,
        "speaker_turn_valid": True,
        "speaker_change_detected": "false",
        "speaker_boundary": "false",
        "text": "Uma explicação com contexto suficiente e termina com uma conclusão clara.",
    })

    assert result["factors"]["speaker_boundary"] == 50.0


def test_ranker_sanitizes_nonfinite_editorial_factors():
    ranker = EditorialRanker()
    result = ranker.score_clip({
        "start": 0,
        "end": 20,
        "duration": 20,
        "speaker_confidence": float("nan"),
        "chapter_coherence_score": float("inf"),
        "visual_change_density": float("nan"),
        "contextual_hook": {"hook_text": "abertura", "score": float("nan")},
        "hook_distance_seconds": float("inf"),
        "text": "Uma explicação com contexto suficiente e termina com uma conclusão clara.",
    })

    assert result["factors"]["speaker_boundary"] == 50.0
    assert result["factors"]["chapter_coherence"] == 50.0
    assert result["factors"]["visual_change_density"] == 50.0
    assert result["factors"]["contextual_hook_alignment"] == 50.0
    assert 0 <= result["editorial_potential_score"] <= 100


def test_ranker_sanitizes_malformed_feedback_numbers():
    ranker = EditorialRanker(feedback_calibration={
        "eligible": "true",
        "sample_size": "nan",
        "approved_count": "bad",
        "rejected_count": "inf",
        "duration_signal": {
            "usable": "true",
            "approved_mean_seconds": "nan",
            "rejected_mean_seconds": "bad",
            "gap_seconds": "inf",
        },
        "candidate_origin_deltas": {"nlp": "nan"},
        "factor_deltas": {"hook": "inf"},
    })
    result = ranker.score_clip({
        "start": 0,
        "end": 20,
        "duration": 20,
        "candidate_origin": "nlp",
        "confidence": "nan",
        "text": "Uma explicação com contexto suficiente e termina com uma conclusão clara.",
    })

    assert result["feedback_calibration"]["sample_size"] == 0
    assert result["feedback_calibration"]["approved_count"] == 0
    assert result["feedback_calibration"]["duration_signal"]["gap_seconds"] == 0.0
    assert result["feedback_calibration"]["candidate_origin_delta"] == 0.0
    assert result["feedback_calibration"]["candidate_origin_confidence"] == 0.75


def test_ranker_treats_malformed_intervals_as_non_overlapping():
    from modules.editorial_ranker import _interval_overlap

    assert _interval_overlap({"start": "nan", "end": 20}, {"start": 0, "end": 10}) == 0.0
    assert _interval_overlap({"start": 20, "end": 10}, {"start": 0, "end": 10}) == 0.0


def test_ranker_normalizes_legacy_flags_in_review_payload():
    ranker = EditorialRanker()
    result = ranker.score_clip({
        "start": 0,
        "end": 20,
        "duration": 20,
        "text": "Uma explicação curta com contexto e fechamento claro.",
        "context_complete": "false",
        "payoff_complete": "false",
        "question_detected": "false",
        "overlap_suspected": "false",
        "timing_ambiguous": "false",
        "speaker_turn_valid": "false",
        "framing": {"review_required": "false"},
        "editorial_chapter_available": "false",
        "chapter_crosses_boundary": "false",
        "context_recovery": {"applied": "false"},
    })

    assert result["context_complete"] is False
    assert result["payoff_complete"] is False
    assert result["question_detected"] is False
    assert result["review_flags"]["overlap_suspected"] is False
    assert result["review_flags"]["timing_ambiguous"] is False
    assert result["review_flags"]["speaker_turn_valid"] is False
    assert result["factors"]["speaker_boundary"] == 25.0
    assert result["framing_review_required"] is False
    assert result["review_flags"]["editorial_chapter_available"] is False
    assert result["review_flags"]["chapter_crosses_boundary"] is False
    assert result["review_flags"]["context_recovery_applied"] is False


def test_ranker_uses_finite_audio_and_confidence_fallbacks():
    ranker = EditorialRanker()
    result = ranker.score_clip(
        {
            "start": 0,
            "end": 12,
            "duration": 12,
            "audio_energy": "nan",
            "text": "A explicação tem contexto suficiente e termina com uma conclusão clara.",
        },
        energy_profile=[
            {"time": "bad", "energy_normalized": "nan"},
            {"time": 2, "energy_normalized": 0.8},
        ],
    )

    assert result["factors"]["audio_energy"] == 87.0
    assert 0.0 <= result["confidence"] <= 1.0


def test_ranker_uses_finite_duration_fallback_for_legacy_values():
    ranker = EditorialRanker()
    malformed = ranker.score_clip({
        "start": "0",
        "end": "30",
        "duration": "nan",
        "text": "A explicação tem contexto suficiente e termina com uma conclusão clara.",
    })

    assert malformed["duration_preference"]["status"] == "curto_preferencial"
    assert malformed["duration_fit"] == 100.0
    ranked = ranker.rank_clips([
        {"start": 0, "end": 30, "duration": "not-a-number", "text": "A explicação tem contexto suficiente e termina com uma conclusão clara."},
        {"start": 0, "end": 20, "duration": 20, "text": "A explicação tem contexto suficiente e termina com uma conclusão clara."},
    ])
    assert ranked
    assert all(ranked_item["duration_fit"] == 100.0 for ranked_item in ranked)


def test_context_quality_coerces_legacy_string_flags():
    ranker = EditorialRanker()
    text = "Uma explicação com contexto suficiente para comparação editorial."
    boolean_result = ranker._context_quality(
        {"context_complete": False, "payoff_complete": False, "question_detected": False},
        text,
        "open",
    )
    textual_result = ranker._context_quality(
        {"context_complete": "false", "payoff_complete": "false", "question_detected": "false"},
        text,
        "open",
    )

    assert textual_result == boolean_result


def test_observed_high_impact_openers_score_as_hooks():
    ranker = EditorialRanker()
    observed = ranker.score_clip({
        "start": 0,
        "end": 30,
        "duration": 30,
        "text": "Presta muita atenção! Leia de novo: este é o Brasil que vamos receber.",
    })
    plain = ranker.score_clip({
        "start": 0,
        "end": 30,
        "duration": 30,
        "text": "Este é o Brasil que vamos receber, segundo os dados apresentados.",
    })
    assert observed["factors"]["hook"] > plain["factors"]["hook"]
    assert observed["factors"]["hook"] >= 70


def test_contextually_distinct_coerces_legacy_string_flags():
    from modules.editorial_ranker import _contextually_distinct

    first = {
        "closure_type": "conclusion",
        "question_answer_complete": True,
        "payoff_complete": True,
        "qa_bridge": True,
        "chapter_primary_id": 1,
    }
    second = {
        "closure_type": "cliffhanger",
        "question_answer_complete": "false",
        "payoff_complete": "false",
        "qa_bridge": "false",
        "chapter_primary_id": 2,
    }

    assert _contextually_distinct(first, second) is True


def test_diversity_penalty_exposes_explainable_reason():
    ranker = EditorialRanker()
    clips = [
        {
            "source_id": "live-1",
            "start": 0,
            "end": 30,
            "duration": 30,
            "topic_signature": "seguranca_publica",
            "text": "A proposta muda a segurança pública e precisa de responsabilidade.",
        },
        {
            "source_id": "live-1",
            "start": 60,
            "end": 90,
            "duration": 30,
            "topic_signature": "seguranca_publica",
            "text": "A investigação precisa de método e a segurança pública depende de responsabilidade.",
        },
    ]
    ranked = ranker.rank_clips(clips)
    penalized = [clip for clip in ranked if clip.get("diversity_penalty", 0) > 0]
    assert penalized
    assert penalized[0]["diversity_reason"] in {
        "texto muito semelhante",
        "tema editorial semelhante",
        "intervalo temporal sobreposto",
    }


def test_context_quality_penalizes_unresolved_reference_opening():
    ranker = EditorialRanker()
    complete = ranker.score_clip({
        "start": 0, "end": 25, "duration": 25,
        "text": "A operação expôs dados sigilosos da família e precisa ser responsabilizada.",
        "context_complete": True,
        "payoff_complete": True,
    })
    unresolved = ranker.score_clip({
        "start": 0, "end": 25, "duration": 25,
        "text": "Isso expôs dados sigilosos da família e precisa ser responsabilizado.",
        "starts_with_context_reference": True,
        "context_complete": False,
        "payoff_complete": True,
    })
    assert complete["factors"]["context_quality"] > unresolved["factors"]["context_quality"]


def test_context_review_flags_expose_reference_and_weak_payoff():
    ranker = EditorialRanker()
    result = ranker.score_clip({
        "start": 0, "end": 20, "duration": 20,
        "text": "Isso acontece porque a proposta ainda precisa de análise.",
        "starts_with_context_reference": True,
        "payoff_weak_ending": True,
    })
    assert result["review_flags"]["starts_with_context_reference"] is True
    assert result["review_flags"]["payoff_weak_ending"] is True


def test_visual_evidence_hook_is_reviewable_and_bounded_in_ranker():
    ranker = EditorialRanker()
    base = {
        "start": 0, "end": 24, "duration": 24,
        "text": "Olha esse gráfico da pesquisa: a proposta muda o debate e termina com uma resposta completa.",
        "context_complete": True,
        "payoff_complete": True,
        "evidence_present": True,
    }
    complete = ranker.score_clip(base)
    visual = ranker.score_clip({
        **base,
        "contextual_hook": {
            "family": "tese-provocativa",
            "hook_text": "Olha esse gráfico da pesquisa",
            "visual_evidence_required": True,
        },
    })
    assert visual["viral_score"] < complete["viral_score"]
    assert visual["viral_score"] >= complete["viral_score"] - 8
    assert visual["technical_gate"]["visual_evidence_required"] is True
    assert "evidência visual citada; confirmar no vídeo" in visual["technical_gate"]["reasons"]
    assert visual["review_flags"]["visual_evidence_review_required"] is True


def test_framing_review_caps_score_confidence_and_explains_gate():
    ranker = EditorialRanker()
    base = {
        "start": 0, "end": 24, "duration": 24,
        "text": "A proposta concreta muda o debate e termina com uma resposta completa.",
        "context_complete": True,
        "payoff_complete": True,
        "evidence_present": True,
    }
    complete = ranker.score_clip(base)
    review = ranker.score_clip({
        **base,
        "framing": {
            "mode": "",
            "review_required": True,
            "reason": "metadata de enquadramento ausente ou legada; confirme a composição visual",
        },
    })
    assert review["viral_score"] < complete["viral_score"]
    assert review["viral_score"] <= 78
    assert review["confidence"] <= 0.72
    assert any("enquadramento exige confirmação visual" in reason for reason in review["technical_gate"]["reasons"])
    assert review["review_flags"]["framing_review_required"] is True


def test_partial_transcription_caps_score_confidence_and_explains_gate():
    ranker = EditorialRanker()
    base = {
        "start": 0, "end": 24, "duration": 24,
        "text": "A proposta concreta muda o debate e termina com uma resposta completa.",
        "context_complete": True,
        "payoff_complete": True,
        "evidence_present": True,
    }
    complete = ranker.score_clip(base)
    partial = ranker.score_clip({
        **base,
        "transcription_review_required": True,
        "transcription_coverage_status": "partial",
    })
    assert partial["viral_score"] < complete["viral_score"]
    assert partial["confidence"] <= 0.74
    assert "cobertura parcial da transcrição" in partial["technical_gate"]["reasons"]
    assert partial["review_flags"]["transcription_review_required"] is True


def test_technical_gate_coerces_legacy_string_flags_safely():
    ranker = EditorialRanker()
    result = ranker.score_clip({
        "start": 0,
        "end": 30,
        "duration": 30,
        "text": "A explicação apresenta contexto, evidência e uma conclusão clara.",
        "context_complete": "true",
        "payoff_complete": "true",
        "evidence_present": "true",
        "topic_boundary": "false",
        "topic_change_detected": "false",
        "overlap_suspected": "false",
        "timing_ambiguous": "false",
        "speaker_turn_valid": "true",
        "review_flags": {
            "topic_review_required": "false",
            "speaker_review_required": "false",
        },
    })

    assert result["topic_review_required"] is False
    assert result["review_flags"]["topic_review_required"] is False
    assert result["technical_gate"]["status"] == "clean"
    assert "mudança de tópico" not in result["technical_gate"]["reasons"]


def test_speaker_review_required_caps_score_and_exposes_reason():
    ranker = EditorialRanker()
    result = ranker.score_clip({
        "start": 0,
        "end": 36,
        "duration": 36,
        "text": "Qual é a proposta? A resposta está nos dados e precisa ser conferida.",
        "question_detected": True,
        "context_complete": True,
        "payoff_complete": True,
        "needs_speaker_review": True,
    })

    assert result["speaker_review_required"] is True
    assert result["confidence"] <= 0.70
    assert result["editorial_potential_score"] <= 78
    assert result["review_flags"]["speaker_review_required"] is True
    assert "locutor" in result["speaker_review_reason"]
    assert result["technical_gate"]["status"] == "review_required"


def test_topic_boundary_requires_review_and_caps_score():
    ranker = EditorialRanker()
    result = ranker.score_clip({
        "start": 0,
        "end": 36,
        "duration": 36,
        "text": "A proposta tem contexto, uma explicação concreta e um fechamento claro.",
        "context_complete": True,
        "payoff_complete": True,
        "evidence_present": True,
        "topic_boundary": True,
    })

    assert result["topic_review_required"] is True
    assert result["editorial_potential_score"] <= 72
    assert result["review_flags"]["topic_review_required"] is True
    assert "mudança de tópico" in result["topic_review_reason"]
    assert result["technical_gate"]["status"] == "review_required"
    assert any("mudança de tópico" in reason for reason in result["technical_gate"]["reasons"])
    assert "mudança de tópico" in result["reason"]


def test_topic_change_alias_uses_same_review_contract():
    ranker = EditorialRanker()
    result = ranker.score_clip({
        "start": 0,
        "end": 30,
        "duration": 30,
        "text": "A explicação tem começo, desenvolvimento, evidência e conclusão.",
        "context_complete": True,
        "payoff_complete": True,
        "topic_change_detected": True,
    })

    assert result["topic_review_required"] is True
    assert result["topic_boundary"] is False
    assert result["topic_change_detected"] is True
    assert result["review_flags"]["topic_review_required"] is True
    assert result["review_flags"]["topic_change_detected"] is True
    assert result["technical_gate"]["status"] == "review_required"


def test_nested_topic_flags_use_same_review_contract():
    ranker = EditorialRanker()
    result = ranker.score_clip({
        "start": 0,
        "end": 30,
        "duration": 30,
        "text": "A explicação apresenta a pauta e fecha com uma consequência concreta.",
        "context_complete": True,
        "payoff_complete": True,
        "review_flags": {"topic_boundary": True},
    })

    assert result["topic_review_required"] is True
    assert result["review_flags"]["topic_review_required"] is True
    assert result["technical_gate"]["topic_review_required"] is True


def test_feedback_cannot_override_speaker_review_score_cap():
    ranker = EditorialRanker(
        feedback_calibration={
            "eligible": True,
            "factor_deltas": {},
            "candidate_origin_deltas": {"gemini_primary": 100},
        }
    )
    result = ranker.score_clip({
        "start": 0,
        "end": 36,
        "duration": 36,
        "text": "Qual é a proposta? A resposta está nos dados e precisa ser conferida.",
        "question_detected": True,
        "context_complete": True,
        "payoff_complete": True,
        "needs_speaker_review": True,
        "candidate_origin": "gemini_primary",
        "confidence": 0.9,
    })

    assert result["feedback_calibration"]["adjustment"] > 0
    assert result["editorial_potential_score"] <= 78


def test_qa_boundary_review_requires_speaker_review_only_for_questions():
    ranker = EditorialRanker()
    question = ranker.score_clip({
        "start": 0,
        "end": 24,
        "duration": 24,
        "text": "A proposta tem uma consequência clara e verificável.",
        "question_detected": True,
        "qa_boundary_review_required": True,
    })
    statement = ranker.score_clip({
        "start": 0,
        "end": 24,
        "duration": 24,
        "text": "A proposta tem uma consequência clara e verificável.",
        "question_detected": False,
        "qa_boundary_review_required": True,
    })

    assert question["speaker_review_required"] is True
    assert statement["speaker_review_required"] is False
