"""Regression tests for substantive answer and reporter-heavy gates."""
from __future__ import annotations

import pytest

from modules.quality_gate import (
    _has_substantive_answer,
    _is_reporter_heavy,
    apply_quality_gate,
)


def test_has_substantive_answer_recognizes_new_markers():
    markers = [
        "Candidato, qual a sua visão? Vou ter que analisar com cuidado.",
        "Candidato, onde buscar recursos? Eu pergunto porque é fundamental.",
        "Candidato, como o senhor conduz? Como presidente, eu vou priorizar.",
        "Candidato, como o senhor vê? Como o senhor mesmo disse, é urgente.",
        "Candidato, onde o senhor estava? Onde o senhor estiver, eu vou cobrar.",
    ]
    for text in markers:
        assert _has_substantive_answer(text), f"marker not detected in: {text}"


def test_has_substantive_answer_rejects_question_only():
    assert not _has_substantive_answer("Candidato, qual é a sua proposta?")
    assert not _has_substantive_answer("Candidato, como o senhor vê?")


def test_is_reporter_heavy_flags_new_reporter_markers():
    text = "Candidato, como o senhor vê a questão? Candidato, onde o senhor busca apoio?"
    assert _is_reporter_heavy(text) is True


def test_gate_rejects_reporter_question_without_substantive_answer():
    clip = {
        "start": 0.0,
        "end": 10.0,
        "viral_score": 80,
        "text": "Candidato, qual é a sua proposta para o país?",
        "starts_mid_sentence": False,
        "starts_with_context_reference": False,
        "opening_dependent": False,
        "ending_fragmented": False,
        "question_detected": True,
        "qa_bridge": False,
        "qa_bridge_local": False,
        "context_complete": True,
        "payoff_complete": True,
        "overlap_suspected": False,
        "contains_broadcast_break": False,
    }
    accepted, rejected = apply_quality_gate([clip])
    assert accepted == []
    assert any("abre_com_pergunta_do_reporter" in r for r in rejected[0]["rejection_reasons"])


def test_gate_accepts_qa_with_substantive_answer_after_question():
    clip = {
        "start": 0.0,
        "end": 15.0,
        "viral_score": 80,
        "text": (
            "Candidato, qual é a sua proposta? "
            "Vou ter que ampliar o atendimento e melhorar a gestão."
        ),
        "starts_mid_sentence": False,
        "starts_with_context_reference": False,
        "opening_dependent": False,
        "ending_fragmented": False,
        "question_detected": True,
        "qa_bridge": True,
        "qa_bridge_local": False,
        "context_complete": True,
        "payoff_complete": True,
        "overlap_suspected": False,
        "contains_broadcast_break": False,
    }
    accepted, rejected = apply_quality_gate([clip])
    assert accepted == [clip]
    assert rejected == []


def test_gate_rejects_reporter_heavy_opening():
    clip = {
        "start": 0.0,
        "end": 15.0,
        "viral_score": 80,
        "text": (
            "Candidato, como o senhor vê a questão? "
            "Candidato, onde o senhor busca apoio? "
            "Eu acho que devemos conversar mais."
        ),
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
    accepted, rejected = apply_quality_gate([clip])
    assert accepted == []
    assert any("abertura_pergunta_sem_resposta_substancial" in r for r in rejected[0]["rejection_reasons"])
