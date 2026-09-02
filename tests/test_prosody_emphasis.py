"""Teste para heurística de ênfase prosódica via word-timestamps (P5)."""

import pytest

from modules.clip_selector import ClipSelector


def _block(text, word_spans):
    start = 0.0
    end = max((ws.get("end", 0) or 0) for ws in word_spans) if word_spans else 1.0
    return {
        "index": 0,
        "start": start,
        "end": end,
        "duration": round(end - start, 1),
        "text": text,
        "sentences": [],
        "word_spans": word_spans,
        "speaker": "A",
    }


class TestProsodyEmphasis:
    def test_sem_word_spans_sem_bonus(self):
        cs = ClipSelector()
        block = _block("O candidato explica a proposta com clareza.", [])
        score = cs._nlp_score_block(block, "", None)
        # Sanidade: pontuação básica sem word_spans
        assert 0 <= score <= 100

    def test_palavras_longas_dao_bonus(self):
        cs = ClipSelector()
        # Palavras com duração acima de 1.5x a média devem gerar bonus
        word_spans = [
            {"start": 0.0, "end": 0.4},
            {"start": 0.4, "end": 0.8},
            {"start": 0.8, "end": 2.0},  # longa (1.5x mais que média ~0.73)
            {"start": 2.0, "end": 2.3},
            {"start": 2.3, "end": 2.7},
        ]
        block = _block("Inacreditável o que esse governo está fazendo.", word_spans)
        score_com = cs._nlp_score_block(block, "", None)

        word_spans_curtas = [
            {"start": 0.0, "end": 0.3},
            {"start": 0.3, "end": 0.6},
            {"start": 0.6, "end": 0.9},
            {"start": 0.9, "end": 1.2},
            {"start": 1.2, "end": 1.5},
        ]
        block_curtas = _block("O candidato explica a proposta com clareza.", word_spans_curtas)
        score_sem = cs._nlp_score_block(block_curtas, "", None)

        assert score_com > score_sem

    def test_bonus_eh_limitado(self):
        cs = ClipSelector()
        # Todas as palavras longas => density = 1.0 => bonus max = 8
        word_spans = [
            {"start": 0.0, "end": 2.0},
            {"start": 2.0, "end": 4.0},
            {"start": 4.0, "end": 6.0},
        ]
        block = _block("Inacreditável chocante surreal.", word_spans)
        score = cs._nlp_score_block(block, "", None)
        # Base mínima ~40 + max bonus 8 + outros componentes
        assert score >= 40
        assert score <= 100

    def test_word_spans_com_dados_invalidos_nao_quebra(self):
        cs = ClipSelector()
        # None, zero/negative durations e chaves faltando devem ser ignorados
        word_spans = [
            {"start": None, "end": None},
            {"start": 0.0, "end": 0.0},      # duração zero
            {"start": 1.0, "end": 0.5},       # duração negativa
            {"text": "palavra"},               # sem start/end
            {"start": 0.0, "end": 0.3},
            {"start": 0.3, "end": 1.5},       # palavra longa válida
        ]
        block = _block("Inacreditável o que esse governo está fazendo.", word_spans)
        score = cs._nlp_score_block(block, "", None)
        assert 0 <= score <= 100
