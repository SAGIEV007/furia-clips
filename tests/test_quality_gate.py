"""Tests for modules/quality_gate.apply_quality_gate."""
from __future__ import annotations

import pytest

from modules.quality_gate import apply_quality_gate


def _clip(start: float, end: float, **overrides) -> dict:
    base = {
        "start": start,
        "end": end,
        "viral_score": 80,
        "text": "Renan fala sobre o tema com clareza.",
        "starts_mid_sentence": False,
        "starts_with_context_reference": False,
        "opening_dependent": False,
        "ending_fragmented": False,
        "question_detected": False,
        "qa_bridge": False,
        "qa_bridge_local": False,
        "context_complete": True,
        "payoff_complete": True,
        "overlap_suspected": False,
        "contains_broadcast_break": False,
    }
    base.update(overrides)
    return base


def test_empty_input_returns_empty():
    assert apply_quality_gate([]) == ([], [])


def test_rejects_short_duration():
    clips = [_clip(0, 3, viral_score=90)]
    accepted, rejected = apply_quality_gate(clips)
    assert accepted == []
    assert any("duracao_abaixo" in r for r in rejected[0]["rejection_reasons"])


def test_rejects_low_viral_score():
    clips = [_clip(0, 10, viral_score=20)]
    accepted, rejected = apply_quality_gate(clips)
    assert accepted == []
    assert any("viral_score" in r for r in rejected[0]["rejection_reasons"])


def test_rejects_starts_mid_sentence():
    clips = [_clip(0, 10, starts_mid_sentence=True)]
    accepted, rejected = apply_quality_gate(clips)
    assert any("abre_no_meio_da_frase" in r for r in rejected[0]["rejection_reasons"])


def test_rejects_context_reference():
    clips = [_clip(0, 10, starts_with_context_reference=True)]
    accepted, rejected = apply_quality_gate(clips)
    assert any("abre_com_referencia" in r for r in rejected[0]["rejection_reasons"])


def test_rejects_opening_dependent():
    clips = [_clip(0, 10, opening_dependent=True)]
    accepted, rejected = apply_quality_gate(clips)
    assert any("abertura_dependente" in r for r in rejected[0]["rejection_reasons"])


def test_rejects_ending_fragmented():
    clips = [_clip(0, 10, ending_fragmented=True)]
    accepted, rejected = apply_quality_gate(clips)
    assert any("fim_fragmentado" in r for r in rejected[0]["rejection_reasons"])


def test_rejects_unanswered_question():
    clips = [_clip(0, 10, question_detected=True)]
    accepted, rejected = apply_quality_gate(clips)
    assert any("pergunta_sem_resposta" in r for r in rejected[0]["rejection_reasons"])


def test_rejects_incomplete_context():
    clips = [_clip(0, 10, context_complete=False)]
    accepted, rejected = apply_quality_gate(clips)
    assert any("contexto_incompleto" in r for r in rejected[0]["rejection_reasons"])


def test_rejects_incomplete_payoff():
    clips = [_clip(0, 10, payoff_complete=False)]
    accepted, rejected = apply_quality_gate(clips)
    assert any("payoff_incompleto" in r for r in rejected[0]["rejection_reasons"])


def test_rejects_broadcast_break():
    clips = [_clip(0, 10, contains_broadcast_break=True)]
    accepted, rejected = apply_quality_gate(clips)
    assert any("atravessa_intervalo" in r for r in rejected[0]["rejection_reasons"])


def test_accepts_clean_clip():
    clips = [_clip(10, 20, viral_score=80)]
    accepted, rejected = apply_quality_gate(clips)
    assert accepted == clips
    assert rejected == []


def test_duplicate_lower_score_rejected():
    high = _clip(10, 20, viral_score=90, text="Renan explica o projeto com dados concretos.")
    low = _clip(12, 22, viral_score=40, text="Renan explica o projeto com dados concretos.")
    accepted, rejected = apply_quality_gate([high, low])
    assert high in accepted
    assert any(c["text"] == low["text"] and c["viral_score"] == low["viral_score"] for c in rejected)
    assert any("duplicata_de_score" in r for c in rejected for r in c["rejection_reasons"])


def test_duplicate_higher_score_rejected_when_processed_first():
    low = _clip(10, 20, viral_score=40, text="Renan explica o projeto com dados concretos.")
    high = _clip(12, 22, viral_score=90, text="Renan explica o projeto com dados concretos.")
    accepted, rejected = apply_quality_gate([low, high])
    assert high in accepted
    assert any(c["text"] == low["text"] and c["viral_score"] == low["viral_score"] for c in rejected)
    assert any("duplicata_de_score" in r for c in rejected for r in c["rejection_reasons"])


def test_overlap_without_text_similarity_accepted():
    a = _clip(0, 20, viral_score=80, text="Renan fala sobre economia com propriedade.")
    b = _clip(15, 35, viral_score=70, text="Renan fala sobre politica com propriedade.")
    accepted, rejected = apply_quality_gate([a, b])
    assert len(accepted) == 2


def test_full_overlap_only_highest_survives():
    clips = [
        _clip(0, 10, viral_score=50, text="Renan explica o projeto A com dados concretos."),
        _clip(0, 10, viral_score=90, text="Renan explica o projeto B com dados concretos."),
        _clip(0, 10, viral_score=70, text="Renan explica o projeto C com dados concretos."),
    ]
    accepted, rejected = apply_quality_gate(clips)
    assert len(accepted) == 1
    assert accepted[0]["viral_score"] == 90
    assert len(rejected) == 2


def test_accumulates_multiple_reasons():
    clips = [_clip(0, 3, viral_score=20, starts_mid_sentence=True, context_complete=False)]
    accepted, rejected = apply_quality_gate(clips)
    reasons = rejected[0]["rejection_reasons"]
    assert any("duracao_abaixo" in r for r in reasons)
    assert any("viral_score" in r for r in reasons)
    assert any("abre_no_meio_da_frase" in r for r in reasons)
    assert any("contexto_incompleto" in r for r in reasons)
