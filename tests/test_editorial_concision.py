import pytest

from modules.clip_selector import ClipSelector


def block(index, start, end, text, score):
    return (
        {
            "index": index,
            "start": start,
            "end": end,
            "duration": end - start,
            "text": text,
            "speaker_turn_valid": True,
            "timing_confidence": 1.0,
        },
        score,
    )


def test_complete_short_idea_stops_before_next_editorial_block():
    selector = ClipSelector(target_duration=45, min_duration=6, max_duration=60)
    scored = [
        block(
            0,
            0,
            12,
            "A proposta reduz impostos, protege o cidadão e estabelece metas claras para o próximo ano.",
            92,
        ),
        block(
            1,
            12,
            24,
            "O segundo ponto é uma discussão diferente sobre segurança pública e orçamento.",
            55,
        ),
    ]

    clips = selector._build_clips_from_scored_blocks(scored)

    assert clips
    assert clips[0]["end"] == 12
    assert "O segundo ponto" not in clips[0]["text"]
    assert clips[0]["context_complete"] is True
    assert clips[0]["payoff_complete"] is True


def test_opening_context_can_recover_more_than_one_adjacent_block():
    selector = ClipSelector(target_duration=30, min_duration=6, max_duration=45)
    scored = [
        block(0, 0, 8, "O relatório oficial confirmou a alteração do contrato público.", 45),
        block(1, 8, 16, "E isso afetou diretamente o orçamento previsto.", 50),
        block(2, 16, 24, "Isso mostra por que a medida precisa ser revista imediatamente.", 95),
    ]

    clips = selector._build_clips_from_scored_blocks(scored)

    assert clips
    assert clips[0]["start"] == 0
    assert clips[0]["text"].startswith("O relatório oficial")
    assert clips[0]["starts_mid_sentence"] is False
    assert clips[0]["starts_with_context_reference"] is False
    assert clips[0]["context_complete"] is True


def test_qa_candidate_adds_question_to_response_without_unrelated_tail():
    selector = ClipSelector(target_duration=30, min_duration=6, max_duration=45)
    scored = [
        block(0, 0, 5, "Qual é a proposta para reduzir impostos?", 52),
        block(
            1,
            5,
            17,
            "A proposta reduz a carga para as famílias, protege o cidadão e define metas claras.",
            95,
        ),
        block(2, 17, 29, "Agora o debate muda para segurança pública e orçamento municipal.", 40),
    ]
    editorial_context = {
        "qa_candidates": [
            {"start": 0, "end": 17, "needs_question": True, "speaker_boundary": True}
        ]
    }

    clips = selector._build_clips_from_scored_blocks(
        scored,
        editorial_context=editorial_context,
    )

    assert clips
    assert clips[0]["start"] == 0
    assert "Qual é a proposta" in clips[0]["text"]
    assert "Agora o debate muda" not in clips[0]["text"]
    assert clips[0]["qa_bridge"] is True
    assert clips[0]["question_answer_complete"] is True


def test_cyclist_case_keeps_setup_before_prendeu_matou_payoff():
    selector = ClipSelector(target_duration=30, min_duration=6, max_duration=45)
    scored = [
        block(0, 0, 8, "O ciclista Vitor Medrado foi morto durante um assalto no Parque do Povo.", 58),
        block(1, 8, 16, "Ele entregou o celular e mesmo assim foi baleado por um criminoso.", 62),
        block(2, 16, 24, "Foi ali que eu lancei o bordão: prendeu, matou.", 98),
        block(3, 24, 34, "Agora vamos mudar de assunto e falar sobre a próxima pauta eleitoral.", 35),
    ]

    clips = selector._build_clips_from_scored_blocks(scored)

    assert clips
    assert clips[0]["start"] == 0
    assert clips[0]["end"] == 24
    assert "Vitor Medrado" in clips[0]["text"]
    assert "prendeu, matou" in clips[0]["text"]
    assert "próxima pauta eleitoral" not in clips[0]["text"]
    assert clips[0]["context_complete"] is True
    assert clips[0]["payoff_complete"] is True
