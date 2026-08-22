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

    def test_selector_coerces_legacy_boolean_flags(self):
        from modules.clip_selector import _coerce_flag

        assert _coerce_flag("false") is False
        assert _coerce_flag("true") is True
        assert _coerce_flag("0") is False
        assert _coerce_flag("1") is True

    def test_previous_fingerprint_keeps_nearby_contextually_distinct_candidate(self):
        self.selector._previous_clip_fingerprints = [{
            "start": 0.0,
            "end": 20.0,
            "duration": 20.0,
            "text": "A proposta precisa de uma resposta clara e responsável.",
            "closure_type": "cliffhanger",
            "question_answer_complete": "false",
            "payoff_complete": "false",
            "qa_bridge": "false",
            "chapter_primary_id": 1,
        }]
        candidate = {
            "start": 22.0,
            "end": 42.0,
            "duration": 20.0,
            "text": "A proposta precisa de uma resposta clara e responsável.",
            "closure_type": "conclusion",
            "question_answer_complete": True,
            "payoff_complete": True,
            "qa_bridge": True,
            "chapter_primary_id": 2,
        }

        assert self.selector._remove_previous_fingerprints([candidate]) == [candidate]

    def test_remove_overlaps_tolerates_malformed_ranking_numbers(self):
        clips = [
            {"start": 0.0, "end": 10.0, "duration": "indisponível", "viral_score": "n/a", "confidence": ""},
            {"start": 20.0, "end": 30.0, "duration": 10.0, "viral_score": 70, "confidence": 0.8},
        ]

        selected = self.selector._remove_overlaps(clips)

        assert len(selected) == 2
        assert {clip["start"] for clip in selected} == {0.0, 20.0}

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

    def test_sentence_blocks_ignore_non_finite_timing_confidence(self):
        segments = [
            {"start": 0.0, "end": 2.0, "text": "Uma afirmação clara.", "timing_confidence": "nan"},
            {"start": 2.1, "end": 4.0, "text": "Outra frase clara.", "timing_confidence": "inf"},
        ]

        sentences = self.selector._build_sentences(segments)
        blocks = self.selector._build_transcript_blocks(sentences)

        assert sentences
        assert blocks
        assert all(item["timing_confidence"] is None for item in sentences)
        assert all(item["timing_confidence"] == 1.0 for item in blocks)

    def test_payoff_extension_ignores_legacy_false_flags(self):
        first = {
            "start": 0.0,
            "end": 4.0,
            "duration": 4.0,
            "text": "Isso aconteceu porque.",
            "overlap_suspected": "false",
            "timing_ambiguous": "false",
            "topic_boundary": "false",
            "speaker_turn_valid": "true",
            "speaker_change_detected": "false",
        }
        second = {
            "start": 4.2,
            "end": 9.0,
            "duration": 4.8,
            "text": "A regra foi aplicada de forma objetiva.",
            "overlap_suspected": "false",
            "timing_ambiguous": "false",
            "topic_boundary": "false",
            "speaker_turn_valid": "true",
            "speaker_change_detected": "false",
        }

        blocks, end_index = self.selector._extend_for_payoff(
            [first],
            0,
            [(first, 80.0), (second, 70.0)],
            set(),
        )

        assert end_index == 1
        assert len(blocks) == 2

    def test_context_recovery_records_when_previous_block_is_prepended(self):
        scored_blocks = [
            ({"start": 0.0, "end": 4.0, "duration": 4.0, "text": "A decisão foi anunciada."}, 10.0),
            ({"start": 5.0, "end": 10.0, "duration": 5.0, "text": "Isso aconteceu porque havia uma regra clara."}, 90.0),
        ]

        clips = self.selector._build_clips_from_scored_blocks(scored_blocks, context_data={})

        assert clips
        recovery = clips[0]["context_recovery"]
        assert recovery["applied"] is True
        assert recovery["added_start"] == 0.0
        assert recovery["original_start"] == 5.0
        assert "antecedente recuperado" in recovery["reason"]

    def test_context_recovery_adds_question_before_clean_answer_opening(self):
        scored_blocks = [
            ({"start": 0.0, "end": 4.0, "duration": 4.0, "text": "Qual é a proposta?"}, 25.0),
            ({"start": 4.2, "end": 12.0, "duration": 7.8, "text": "A proposta reduz impostos e protege o cidadão."}, 95.0),
        ]

        clips = self.selector._build_clips_from_scored_blocks(scored_blocks, context_data={})

        assert clips
        assert clips[0]["start"] == 0.0
        assert "Qual é a proposta?" in clips[0]["text"]
        assert clips[0]["context_recovery"]["applied"] is True
        assert "pergunta e resposta" in clips[0]["context_recovery"]["reason"]

    def test_context_recovery_accepts_single_text_speaker_label(self):
        scored_blocks = [
            ({"start": 0.0, "end": 4.0, "duration": 4.0, "text": "Qual é a proposta?", "speaker": "Entrevistador", "speakers": "Entrevistador"}, 20.0),
            ({"start": 4.2, "end": 12.0, "duration": 7.8, "text": "A proposta protege o cidadão.", "speaker": "Renan", "speakers": "Renan"}, 95.0),
        ]

        clips = self.selector._build_clips_from_scored_blocks(scored_blocks, context_data={})

        assert clips
        assert clips[0]["start"] == 0.0
        assert "Qual é a proposta?" in clips[0]["text"]
        assert clips[0]["context_recovery"]["applied"] is True

    def test_context_recovery_skips_multi_speaker_question(self):
        scored_blocks = [
            ({"start": 0.0, "end": 4.0, "duration": 4.0, "text": "Qual é a proposta?", "speaker_change_detected": True, "speakers": ["Entrevistador", "Renan"]}, 20.0),
            ({"start": 4.2, "end": 12.0, "duration": 7.8, "text": "A proposta protege o cidadão."}, 95.0),
        ]

        clips = self.selector._build_clips_from_scored_blocks(scored_blocks, context_data={})

        assert clips
        assert clips[0]["start"] == 4.2
        assert "Qual é a proposta?" not in clips[0]["text"]

    def test_context_recovery_skips_ambiguous_answer(self):
        scored_blocks = [
            ({"start": 0.0, "end": 4.0, "duration": 4.0, "text": "Qual é a proposta?"}, 20.0),
            ({"start": 4.2, "end": 12.0, "duration": 7.8, "text": "A proposta protege o cidadão.", "speaker_turn_valid": False}, 95.0),
        ]

        clips = self.selector._build_clips_from_scored_blocks(scored_blocks, context_data={})

        assert clips
        assert clips[0]["start"] == 4.2
        assert "Qual é a proposta?" not in clips[0]["text"]

    def test_context_recovery_skips_unsafe_overlapping_question(self):
        scored_blocks = [
            ({"start": 0.0, "end": 5.0, "duration": 5.0, "text": "Qual é a proposta?", "overlap_suspected": True}, 20.0),
            ({"start": 4.6, "end": 12.0, "duration": 7.4, "text": "A proposta protege o cidadão."}, 95.0),
        ]

        clips = self.selector._build_clips_from_scored_blocks(scored_blocks, context_data={})

        assert clips
        assert clips[0]["start"] == 4.6
        assert "Qual é a proposta?" not in clips[0]["text"]

    def test_llm_parser_recovers_question_before_clean_answer_opening(self):
        all_blocks = [
            {"index": 0, "start": 0.0, "end": 4.0, "duration": 4.0, "text": "Qual é a proposta?"},
            {"index": 1, "start": 4.2, "end": 12.0, "duration": 7.8, "text": "A proposta reduz impostos e protege o cidadão."},
        ]
        response = '[{"blocks": [1], "title": "A proposta", "reason": "resposta", "hook": "B", "flow": "B", "value": "B", "energy": "B"}]'

        clips = self.selector._parse_llm_response(response, [], all_blocks, 0, source="gemini")

        assert clips
        assert clips[0]["start"] == 0.0
        assert "Qual é a proposta?" in clips[0]["text"]
        assert clips[0]["context_recovery"]["applied"] is True
        assert "pergunta e resposta" in clips[0]["context_recovery"]["reason"]

    def test_recovered_question_keeps_qa_candidate_until_its_completion(self):
        scored_blocks = [
            ({"start": 0.0, "end": 4.0, "duration": 4.0, "text": "Qual é a proposta?"}, 25.0),
            ({"start": 4.2, "end": 12.0, "duration": 7.8, "text": "A proposta reduz impostos e protege o cidadão."}, 95.0),
            ({"start": 12.2, "end": 18.0, "duration": 5.8, "text": "Isso gera economia e segurança."}, 70.0),
            ({"start": 18.2, "end": 25.0, "duration": 6.8, "text": "Esse é o resultado final para a população."}, 65.0),
        ]
        context = {"qa_candidates": [{"start": 0.0, "end": 25.0, "needs_question": True}]}
        selector = ClipSelector(target_duration=15, max_clips=5, min_duration=5, max_duration=30)

        clips = selector._build_clips_from_scored_blocks(scored_blocks, context_data={}, editorial_context=context)

        assert clips
        assert clips[0]["start"] == 0.0
        assert clips[0]["end"] == 25.0
        assert clips[0]["qa_bridge"] is True

    def test_nlp_builder_preserves_full_qa_bridge_before_natural_stop(self):
        scored_blocks = [
            ({"start": 0.0, "end": 8.0, "duration": 8.0, "text": "Qual é a proposta?"}, 95.0),
            ({"start": 8.2, "end": 17.0, "duration": 8.8, "text": "A proposta reduz impostos e protege o cidadão."}, 82.0),
            ({"start": 17.2, "end": 22.0, "duration": 4.8, "text": "Isso gera economia e segurança."}, 74.0),
            ({"start": 22.2, "end": 28.0, "duration": 5.8, "text": "Esse é o resultado final para a população."}, 68.0),
        ]
        context = {"qa_candidates": [{"start": 0.0, "end": 28.0, "needs_question": True}]}

        clips = self.selector._build_clips_from_scored_blocks(scored_blocks, context_data={}, editorial_context=context)

        self.assertTrue(clips)
        self.assertGreaterEqual(clips[0]["end"], 25.5)
        self.assertTrue(clips[0]["qa_bridge"])

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

    def test_nlp_builder_extends_open_payoff_to_adjacent_block(self):
        scored_blocks = [
            ({"start": 0.0, "end": 8.0, "duration": 8.0, "text": "A proposta resolve porque."}, 95.0),
            ({"start": 8.2, "end": 15.0, "duration": 6.8, "text": "reduz custos e protege o cidadão."}, 70.0),
        ]

        selector = ClipSelector(target_duration=8, max_clips=5, min_duration=5, max_duration=30)
        clips = selector._build_clips_from_scored_blocks(scored_blocks, context_data={})

        assert clips
        assert clips[0]["end"] == 15.0
        assert "reduz custos" in clips[0]["text"]
        assert clips[0]["payoff_complete"] is True

    def test_editorial_flags_distinguish_questions_from_discourse_connectors(self):
        assert self.selector._editorial_flags("Como combater o crime organizado de forma efetiva?")["question_detected"] is True
        assert self.selector._editorial_flags("O que fazer diante desse problema")["question_detected"] is True
        assert self.selector._editorial_flags("Como resultado, a proposta foi aprovada.")["question_detected"] is False
        assert self.selector._editorial_flags("Por fim, a medida protege o cidadão.")["question_detected"] is False

    def test_question_detector_distinguishes_explicit_question_labels(self):
        assert self.selector._looks_like_explicit_question("Pergunta: qual é o próximo ponto") is True
        assert self.selector._looks_like_explicit_question("A questão: como resolver isso") is True
        assert self.selector._looks_like_explicit_question("A questão central é o custo da medida") is False
        assert self.selector._looks_like_explicit_question("Será que essa proposta funciona") is True
        assert self.selector._looks_like_explicit_question("Você acha que isso resolve o problema") is True
        assert self.selector._looks_like_explicit_question("Como resultado, a proposta foi aprovada") is False
        assert self.selector._looks_like_explicit_question("Por fim, a medida protege o cidadão") is False

    def test_payoff_extension_stops_before_labeled_question(self):
        scored_blocks = [
            ({"start": 0.0, "end": 8.0, "duration": 8.0, "text": "A proposta resolve porque."}, 95.0),
            ({"start": 8.2, "end": 15.0, "duration": 6.8, "text": "Pergunta: qual é o próximo ponto?"}, 70.0),
        ]
        selector = ClipSelector(target_duration=8, max_clips=5, min_duration=5, max_duration=30)

        clips = selector._build_clips_from_scored_blocks(scored_blocks, context_data={})

        assert clips
        assert clips[0]["end"] == 8.0
        assert "Pergunta:" not in clips[0]["text"]

    def test_payoff_extension_does_not_cross_confirmed_speaker_change(self):
        scored_blocks = [
            ({"start": 0.0, "end": 8.0, "duration": 8.0, "text": "A proposta resolve porque.", "speaker": "Renan"}, 95.0),
            ({"start": 8.2, "end": 15.0, "duration": 6.8, "text": "Qual é o próximo ponto?", "speaker": "Entrevistador", "speaker_turn_valid": False}, 70.0),
        ]
        selector = ClipSelector(target_duration=8, max_clips=5, min_duration=5, max_duration=30)

        clips = selector._build_clips_from_scored_blocks(scored_blocks, context_data={})

        assert clips
        assert clips[0]["start"] == 0.0
        assert clips[0]["end"] == 8.0
        assert "Qual é o próximo ponto?" not in clips[0]["text"]

    def test_initial_builder_stops_before_ambiguous_block(self):
        scored_blocks = [
            ({"start": 0.0, "end": 4.0, "duration": 4.0, "text": "A proposta começa."}, 95.0),
            ({"start": 4.2, "end": 12.0, "duration": 7.8, "text": "Fala com áudio incerto.", "timing_ambiguous": True}, 70.0),
        ]
        selector = ClipSelector(target_duration=20, max_clips=5, min_duration=5, max_duration=30)

        clips = selector._build_clips_from_scored_blocks(scored_blocks, context_data={})

        assert clips
        assert clips[0]["start"] == 4.2
        assert clips[0]["end"] == 12.0
        assert "Qual é a proposta?" not in clips[0]["text"]

    def test_payoff_extension_stops_before_multi_speaker_block(self):
        scored_blocks = [
            ({"start": 0.0, "end": 8.0, "duration": 8.0, "text": "A proposta resolve porque."}, 95.0),
            ({"start": 8.2, "end": 15.0, "duration": 6.8, "text": "reduz custos e protege o cidadão.", "speaker_change_detected": True, "speakers": ["Renan", "Entrevistador"]}, 70.0),
        ]
        selector = ClipSelector(target_duration=8, max_clips=5, min_duration=5, max_duration=30)

        clips = selector._build_clips_from_scored_blocks(scored_blocks, context_data={})

        assert clips
        assert clips[0]["end"] == 8.0
        assert "reduz custos" not in clips[0]["text"]

    def test_payoff_extension_stops_before_a_new_question(self):
        scored_blocks = [
            ({"start": 0.0, "end": 8.0, "duration": 8.0, "text": "A proposta resolve porque."}, 95.0),
            ({"start": 8.2, "end": 15.0, "duration": 6.8, "text": "Qual é o próximo ponto do debate?"}, 70.0),
        ]
        selector = ClipSelector(target_duration=8, max_clips=5, min_duration=5, max_duration=30)

        clips = selector._build_clips_from_scored_blocks(scored_blocks, context_data={})

        assert clips
        assert clips[0]["end"] == 8.0
        assert "Qual é o próximo ponto" not in clips[0]["text"]

    def test_payoff_extension_stops_after_a_long_pause(self):
        scored_blocks = [
            ({"start": 0.0, "end": 8.0, "duration": 8.0, "text": "A proposta resolve porque."}, 95.0),
            ({"start": 20.0, "end": 27.0, "duration": 7.0, "text": "reduz custos e protege o cidadão."}, 70.0),
        ]
        selector = ClipSelector(target_duration=8, max_clips=5, min_duration=5, max_duration=30)

        clips = selector._build_clips_from_scored_blocks(scored_blocks, context_data={})

        assert clips
        assert clips[0]["end"] == 8.0
        assert "reduz custos" not in clips[0]["text"]

    def test_payoff_extension_keeps_explanatory_porque_continuation(self):
        scored_blocks = [
            ({"start": 0.0, "end": 8.0, "duration": 8.0, "text": "A proposta é necessária porque."}, 95.0),
            ({"start": 8.2, "end": 15.0, "duration": 6.8, "text": "porque protege o cidadão."}, 70.0),
        ]
        selector = ClipSelector(target_duration=8, max_clips=5, min_duration=5, max_duration=30)

        clips = selector._build_clips_from_scored_blocks(scored_blocks, context_data={})

        assert clips
        assert clips[0]["end"] == 15.0
        assert "porque protege" in clips[0]["text"]
        assert clips[0]["payoff_complete"] is True

    def test_response_reference_requires_adjacent_question_context(self):
        flags = self.selector._editorial_flags("A resposta é proteger o cidadão com transparência.")

        self.assertTrue(flags["starts_with_context_reference"])
        self.assertFalse(flags["context_complete"])

        recovered = self.selector._opening_context_signal(
            {"text": "A resposta é proteger o cidadão com transparência."},
            {"text": "Qual é a proposta para o problema?"},
        )
        self.assertTrue(recovered["weak"])
        self.assertIn("antecedente recuperado", recovered["reason"])


    def test_editorial_flags_do_not_treat_por_fim_as_question(self):
        flags = self.selector._editorial_flags("Por fim, essa medida protege o cidadão.")

        self.assertFalse(flags["question_detected"])
        self.assertTrue(flags["payoff_complete"])

    def test_payoff_extension_keeps_como_resultado_continuation(self):
        scored_blocks = [
            ({"start": 0.0, "end": 8.0, "duration": 8.0, "text": "A medida é necessária porque."}, 95.0),
            ({"start": 8.2, "end": 15.0, "duration": 6.8, "text": "Como resultado, a segurança melhora."}, 70.0),
        ]
        selector = ClipSelector(target_duration=8, max_clips=5, min_duration=5, max_duration=30)

        clips = selector._build_clips_from_scored_blocks(scored_blocks, context_data={})

        assert clips
        assert clips[0]["end"] == 15.0
        assert "Como resultado" in clips[0]["text"]

    def test_editorial_flags_expose_topic_boundary(self):
        flags = self.selector._editorial_flags(
            "A primeira pauta foi concluída com contexto suficiente.",
            {"topic_boundary": True},
        )

        self.assertTrue(flags["topic_boundary"])
        self.assertTrue(flags["needs_topic_review"])
        self.assertIn("mudança de tópico", flags["topic_review_reason"])
        self.assertFalse(flags["context_complete"])

    def test_payoff_gate_rejects_linguistically_open_ending(self):
        weak = self.selector._editorial_flags(
            "A proposta parecia resolver o problema, porque."
        )
        self.assertFalse(weak["payoff_complete"])
        self.assertTrue(weak["payoff_weak_ending"])
        self.assertFalse(weak["context_complete"])

    def test_payoff_gate_keeps_explicit_conclusion(self):
        complete = self.selector._editorial_flags(
            "A proposta resolve o problema porque reduz o custo e protege o cidadão."
        )
        self.assertTrue(complete["payoff_complete"])
        self.assertFalse(complete["payoff_weak_ending"])
        self.assertTrue(complete["context_complete"])

    def test_dossier_qa_bonus_requires_question_and_response_window(self):
        context = {"qa_candidates": [{"start": 20.0, "end": 58.0, "needs_question": True, "speaker_boundary": True}]}
        response_only = self.selector._dossier_context_score(
            {"start": 34.0, "end": 58.0}, context
        )
        complete_qa = self.selector._dossier_context_score(
            {"start": 19.0, "end": 58.0}, context
        )
        self.assertLess(response_only, complete_qa)
        self.assertEqual(response_only, -2.5)
        self.assertEqual(complete_qa, 3.0)

    def test_dossier_hook_bonus_requires_confirmed_payoff_for_full_weight(self):
        confirmed = self.selector._dossier_context_score(
            {"start": 10.0, "end": 30.0},
            {"hook_candidates": [{"start": 10.0, "end": 30.0, "score": 100, "payoff_confirmed": True}]},
        )
        lead_only = self.selector._dossier_context_score(
            {"start": 10.0, "end": 30.0},
            {"hook_candidates": [{"start": 10.0, "end": 30.0, "score": 100, "payoff_confirmed": False}]},
        )
        self.assertEqual(confirmed, 8.0)
        self.assertEqual(lead_only, 2.0)

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

    def test_selection_progress_uses_explicit_local_backend_label(self):
        transcription = {
            "segments": [
                {"start": 0.0, "end": 4.0, "text": "A proposta é reduzir impostos com responsabilidade."},
                {"start": 4.2, "end": 8.0, "text": "O plano precisa de metas e prazo claro."},
                {"start": 8.2, "end": 12.0, "text": "Essa é a consequência para o cidadão."},
            ]
        }
        messages = []
        with patch.object(self.selector, "_select_with_llm", return_value=None):
            self.selector.select_clips(
                transcription,
                settings={"ai_backend": "auto", "gemini_api_key": ""},
                emit_progress=lambda message, level="info": messages.append(message),
            )
        self.assertTrue(any("via NLP local" in message for message in messages))
        self.assertFalse(any("NLP basico" in message for message in messages))

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


    @patch("modules.clip_selector.requests.post")
    def test_gemini_quota_message_explains_local_fallback(self, post):
        post.return_value.status_code = 429
        post.return_value.json.return_value = {"error": {"message": "quota exhausted"}}
        messages = []
        sentences = self.selector._build_sentences([
            {"start": 0.0, "end": 12.0, "text": "Uma tese completa com consequência clara."},
        ])

        result = self.selector._select_with_gemini(
            sentences,
            energy_profile=[],
            user_context="",
            settings={"gemini_api_key": "chave-de-teste"},
            emit_progress=lambda message, level="info": messages.append((message, level)),
        )

        assert result == []
        assert any("atingiu a cota" in message for message, _level in messages)
        assert any("fallback local" in message for message, _level in messages)
        assert not any("Tentando proximo modelo" in message for message, _level in messages)

    def test_context_gate_rejects_unresolved_reference_at_opening(self):
        flags = self.selector._editorial_flags(
            "Isso destruiu a vida de muitas pessoas e revelou um problema grave de responsabilidade pública."
        )
        self.assertTrue(flags["starts_with_context_reference"])
        self.assertFalse(flags["context_complete"])

    def test_payoff_gate_rejects_connective_ending_without_conclusion(self):
        weak = self.selector._editorial_flags(
            "A proposta resolveria o problema e protegeria o cidadão, por isso."
        )
        self.assertTrue(weak["payoff_weak_ending"])
        self.assertFalse(weak["payoff_complete"])




def test_nlp_builder_propagates_speaker_review_from_editorial_qa_dossier():
    selector = ClipSelector(target_duration=20, max_clips=5, min_duration=5, max_duration=30)
    scored_blocks = [
        ({"start": 0.0, "end": 8.0, "duration": 8.0, "text": "Qual é a proposta?"}, 95.0),
        ({"start": 8.2, "end": 17.0, "duration": 8.8, "text": "A proposta reduz impostos e protege o cidadão."}, 82.0),
    ]
    context = {
        "qa_candidates": [{
            "start": 0.0,
            "end": 17.0,
            "needs_question": True,
            "needs_speaker_review": True,
        }],
    }

    clips = selector._build_clips_from_scored_blocks(
        scored_blocks,
        context_data={},
        editorial_context=context,
    )

    assert clips
    assert clips[0]["needs_speaker_review"] is True
    assert "diarização" in clips[0]["speaker_review_reason"]


def test_word_timestamps_refine_edges_with_bounded_padding():
    selector = ClipSelector(target_duration=8, max_clips=5, min_duration=5, max_duration=30)
    start, end, metadata = selector._refine_clip_boundaries([
        {
            "start": 0.0,
            "end": 12.0,
            "word_spans": [
                {"start": 1.1, "end": 2.0},
                {"start": 8.6, "end": 10.0},
            ],
        }
    ])
    assert start == 0.8
    assert end == 11.2
    assert metadata["applied"] is True
    assert metadata["trim_before"] == 0.8
    assert metadata["trim_after"] == 0.8


def test_word_timestamp_refinement_keeps_interval_without_safe_spans():
    selector = ClipSelector(target_duration=8, max_clips=5, min_duration=5, max_duration=30)
    start, end, metadata = selector._refine_clip_boundaries([
        {"start": 0.0, "end": 8.0, "word_spans": [{"start": "nan", "end": 4.0}]}
    ])
    assert (start, end) == (0.0, 8.0)
    assert metadata["applied"] is False
    assert metadata["reason"] == "sem_timestamps_de_palavras"


def test_sentence_builder_preserves_numeric_word_spans_only():
    selector = ClipSelector()
    sentences = selector._build_sentences([
        {
            "start": 0.0,
            "end": 4.0,
            "text": "Uma fala clara.",
            "words": [
                {"word": "Uma", "start": 0.4, "end": 0.8},
                {"word": "fala", "start": 1.0, "end": 1.6},
                {"word": "clara", "start": 2.0, "end": 2.5},
                {"word": "ruim", "start": "nan", "end": 3.0},
            ],
        }
    ])
    assert sentences[0]["word_spans"] == [
        {"start": 0.4, "end": 0.8},
        {"start": 1.0, "end": 1.6},
        {"start": 2.0, "end": 2.5},
    ]


def test_scene_boundary_adjustment_only_expands_clip_edges():
    selector = ClipSelector(target_duration=8, max_clips=5, min_duration=5, max_duration=30)
    clips = selector._adjust_to_scene_boundaries(
        [{"start": 10.5, "end": 19.5, "duration": 9.0}],
        [0.0, 9.0, 12.0, 20.5, 30.0],
    )

    assert clips[0]["start"] == 9.0
    assert clips[0]["end"] == 20.5
    assert clips[0]["duration"] == 11.5
    assert clips[0]["scene_boundary_adjustment"]["direction"] == "outward_only"


def test_scene_boundary_adjustment_never_shrinks_spoken_interval():
    selector = ClipSelector(target_duration=8, max_clips=5, min_duration=5, max_duration=30)
    clips = selector._adjust_to_scene_boundaries(
        [{"start": 10.0, "end": 20.0, "duration": 10.0}],
        [0.0, 10.8, 19.2, 30.0],
    )

    assert clips[0]["start"] == 10.0
    assert clips[0]["end"] == 20.0
    assert clips[0]["scene_boundary_adjustment"]["applied"] is False


def test_scene_boundary_adjustment_ignores_invalid_timestamps():
    selector = ClipSelector(target_duration=8, max_clips=5, min_duration=5, max_duration=30)
    clips = selector._adjust_to_scene_boundaries(
        [{"start": 10.0, "end": 20.0, "duration": 10.0}],
        ["nan", None, "inf", -1, 0.0],
    )

    assert clips == [{"start": 10.0, "end": 20.0, "duration": 10.0}]


if __name__ == "__main__":
    unittest.main()



def test_previous_fingerprint_keeps_overlapping_contextually_distinct_candidate():
    selector = ClipSelector(target_duration=20, max_clips=5, min_duration=5, max_duration=30)
    selector._previous_clip_fingerprints = [{
        "start": 0.0,
        "end": 30.0,
        "duration": 30.0,
        "text": "A proposta precisa de uma resposta clara e responsável.",
        "closure_type": "cliffhanger",
        "question_answer_complete": False,
        "payoff_complete": False,
        "qa_bridge": False,
        "chapter_primary_id": 1,
    }]
    candidate = {
        "start": 15.0,
        "end": 35.0,
        "duration": 20.0,
        "text": "A proposta precisa de uma resposta clara e responsável.",
        "closure_type": "conclusion",
        "question_answer_complete": True,
        "payoff_complete": True,
        "qa_bridge": True,
        "chapter_primary_id": 2,
    }

    assert selector._remove_previous_fingerprints([candidate]) == [candidate]


def test_previous_fingerprint_still_discards_exact_duplicate():
    selector = ClipSelector(target_duration=20, max_clips=5, min_duration=5, max_duration=30)
    selector._previous_clip_fingerprints = [{
        "start": 10.0,
        "end": 30.0,
        "duration": 20.0,
        "text": "A resposta foi clara e responsável.",
    }]
    candidate = {
        "start": 10.0,
        "end": 30.0,
        "duration": 20.0,
        "text": "A resposta foi clara e responsável.",
    }

    assert selector._remove_previous_fingerprints([candidate]) == []
    assert selector._candidate_diagnostics["previous_discarded_count"] == 1



def test_scene_boundary_adjustment_preserves_interval_when_expansion_exceeds_max_duration():
    selector = ClipSelector(target_duration=8, max_clips=5, min_duration=5, max_duration=10)
    clips = selector._adjust_to_scene_boundaries(
        [{"start": 10.5, "end": 19.5, "duration": 9.0}],
        [0.0, 8.0, 10.0, 12.0, 20.5, 30.0],
    )

    assert clips[0]["start"] == 10.5
    assert clips[0]["end"] == 19.5
    assert clips[0]["duration"] == 9.0
    assert clips[0]["scene_boundary_adjustment"]["applied"] is False


def test_prompt_block_exposes_speaker_turns_and_confidence_to_editorial_models():
    selector = ClipSelector()
    block = selector._make_editorial_block(
        0,
        0.0,
        8.0,
        "Você pode explicar? A resposta começa agora.",
        [
            {"start": 0.0, "end": 3.0, "text": "Você pode explicar?", "speaker": "Entrevistador", "speakers": ["Entrevistador"], "speaker_confidence": 0.91},
            {"start": 3.0, "end": 8.0, "text": "A resposta começa agora.", "speaker": "Renan", "speakers": ["Renan"], "speaker_confidence": 0.83},
        ],
    )

    rendered = selector._format_prompt_block(block)

    assert "LOCUTOR/CONFIANÇA:" in rendered
    assert "Entrevistador" in rendered and "91%" in rendered
    assert "Renan" in rendered and "83%" in rendered


def test_prompt_block_warns_models_not_to_assume_unknown_speaker():
    selector = ClipSelector()
    rendered = selector._format_prompt_block({
        "index": 1,
        "start": 10.0,
        "end": 13.0,
        "duration": 3.0,
        "text": "Uma fala sem diarização.",
        "sentences": [{"start": 10.0, "end": 13.0, "text": "Uma fala sem diarização."}],
    })

    assert "locutor não identificado" in rendered
    assert "não assuma" in rendered
