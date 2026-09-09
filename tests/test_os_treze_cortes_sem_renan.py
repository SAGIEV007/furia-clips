"""Vinte e quatro cortes, vinte e quatro vereditos, um relógio.

O QUE O EDITOR RECEBEU
----------------------
Uma entrevista de 1h46 em que Renan é chamado aos 32:46. O Furia devolveu 24
cortes. O editor julgou um por um e reprovou treze com a mesma frase, em
variações: "jornalistas conversando", "apenas o documento", "o Renan nem estava
no sofá ainda".

Cruzando os vereditos com os carimbos de tempo do arquivo de seleção que ele
exportou, os treze reprovados são exatamente os treze que começam antes de
32:46. E os cinco que ele elogiou — 7, 12, 13, 1, 20 — estão todos depois.
Vinte e quatro concordâncias em vinte e quatro.

O diagnóstico da mesma rodada explica: `processing_interval` = "fonte inteira",
`source_boundary` = "not_detected", `identity_available` = 0. A máquina não
sabia que a entrevista começava aos 32:46, e não tinha como saber — a validação
multimodal que diria quem está na tela nunca completou.

TRÊS DEFEITOS, TRÊS CONSERTOS
-----------------------------
1. A tela não tinha onde pedir um intervalo, embora o motor sempre soubesse
   recebê-lo e a outra tela já o enviasse. O editor recortava o vídeo à mão
   antes de carregar, justamente para contornar isso.

2. As fronteiras paravam no meio da frase, e o portão que deveria pegar isso
   dizia que estava tudo bem — porque julgava um texto montado dos segmentos
   inteiros, não o trecho realmente renderizado.

3. Cortes irmãos eram entregues em dobro. O editor pediu "o corte perfeito
   seria o 1+18 juntos"; a regra que existia para isso estava desligada por um
   sinal.
"""

import re
from pathlib import Path

import pytest

from modules.clip_selector import ClipSelector

RAIZ = Path(__file__).resolve().parents[1]
TELA = (RAIZ / "static" / "js" / "app.js").read_text(encoding="utf-8")
MESA = (RAIZ / "static" / "js" / "mesa-app.js").read_text(encoding="utf-8")
PAGINA = (RAIZ / "templates" / "index.html").read_text(encoding="utf-8")


def _seletor():
    """Um seletor sem construtor, para exercitar os passes de fronteira."""
    seletor = object.__new__(ClipSelector)
    seletor._candidate_diagnostics = {}
    return seletor


# ── 1. o intervalo que a tela nunca pediu ───────────────────────────────────


def test_a_tela_pede_o_trecho_da_fonte():
    """Os treze cortes sem Renan saem daqui.

    O motor aceita `processing_start`/`processing_end` desde sempre
    (`_requested_processing_interval`, em app.py) e a Mesa já enviava. Esta
    tela, que é a que o editor usa, não tinha os campos.
    """
    assert 'id="processingStartInput"' in PAGINA
    assert 'id="processingEndInput"' in PAGINA


@pytest.mark.parametrize("tela", [TELA, MESA], ids=["app.js", "mesa-app.js"])
def test_as_duas_telas_enviam_o_intervalo(tela):
    """Elas divergiram antes — no prazo de espera — e o editor estava na que
    ficou para trás. Divergir de novo aqui custa a tarde dele."""
    assert "processing_start:" in tela
    assert "processing_end:" in tela


def test_intervalo_invalido_nao_vira_moagem():
    """Fim antes do início tem que parar na tela, não no motor."""
    corpo = TELA[TELA.find("function readProcessingInterval"):]
    corpo = corpo[:corpo.find("\nfunction updateProcessingIntervalHint")]
    assert "não pode ser negativo" in corpo
    assert "precisa ser maior que o início" in corpo


def test_campos_vazios_continuam_significando_fonte_inteira():
    """Quem não quer restringir não pode ser obrigado a preencher nada."""
    corpo = TELA[TELA.find("function readProcessingInterval"):]
    corpo = corpo[:corpo.find("\nfunction updateProcessingIntervalHint")]
    assert 'if (!start && !end) return { valid: true, start: null, end: null' in corpo


# ── 2. terminar a frase, não a palavra ──────────────────────────────────────


def test_o_fim_da_frase_vem_da_pontuacao():
    """A legenda vem em blocos de dois segundos que não respeitam frase.
    "Eu tava conversando com o Vini antes de" é um bloco inteiro; quem sabe que
    um raciocínio fechou é o ponto final dentro do texto."""
    segmentos = [
        {"start": 0.0, "end": 2.0, "texto_errado": "x", "text": "É a turma do Lula no STF."},
        {"start": 2.0, "end": 4.0, "text": "Eu tava conversando com o Vini antes de"},
        {"start": 4.0, "end": 6.0, "text": "entrar no ar. Pode falar."},
    ]
    inicios, fins = ClipSelector._sentence_marks(segmentos)
    assert 2.0 in fins, "não viu o ponto final do primeiro bloco"
    assert 4.0 not in fins, "tratou um bloco aberto como fim de frase"
    assert 6.0 in fins
    # O bloco 2→4 vem depois de um ponto final, então ABRE frase; o 4→6
    # continua a dele e não abre.
    assert 2.0 in inicios
    assert 4.0 not in inicios


def test_o_corte_passa_a_terminar_onde_a_frase_termina():
    """O caso medido: o portão lia "...no STF." e aprovava, enquanto o áudio ia
    1,2 s adiante e parava em "Eu tava conver—"."""
    segmentos = [
        {"start": 0.0, "end": 2.0, "text": "É a turma do Lula no STF."},
        {"start": 2.0, "end": 4.0, "text": "Eu tava conversando com o Vini antes de"},
    ]
    cortes = [{"start": 0.0, "end": 2.78}]
    _seletor()._snap_to_sentence_ends(cortes, segmentos)
    assert cortes[0]["end"] == pytest.approx(2.0), (
        "o corte continua parando no meio da frase seguinte"
    )
    assert cortes[0]["sentence_snapped"] is True


def test_um_limite_longe_demais_nao_e_puxado():
    """Encaixe é ajuste de borda. Puxar oito segundos é escolher outro corte."""
    segmentos = [{"start": 0.0, "end": 2.0, "text": "Fecha aqui."}]
    cortes = [{"start": 0.0, "end": 30.0}]
    _seletor()._snap_to_sentence_ends(cortes, segmentos)
    assert cortes[0]["end"] == 30.0


def test_o_encaixe_nunca_apaga_o_corte():
    """Puxar o fim para trás do início devolveria duração negativa."""
    segmentos = [
        {"start": 0.0, "end": 1.0, "text": "Um."},
        {"start": 1.0, "end": 2.0, "text": "Dois."},
    ]
    cortes = [{"start": 1.4, "end": 2.2}]
    _seletor()._snap_to_sentence_ends(cortes, segmentos)
    assert float(cortes[0]["end"]) - float(cortes[0]["start"]) >= 1.0


def test_sem_pontuacao_o_passe_nao_faz_nada():
    """Legenda automática sem pontuação é normal e não pode virar erro."""
    segmentos = [{"start": 0.0, "end": 2.0, "text": "sem pontuacao nenhuma aqui"}]
    cortes = [{"start": 0.0, "end": 1.9}]
    seletor = _seletor()
    seletor._snap_to_sentence_ends(cortes, segmentos)
    assert cortes[0]["end"] == 1.9
    assert seletor._candidate_diagnostics["sentence_snap_available"] is False


def test_segmento_torto_nao_derruba_a_moagem():
    """Fim antes do início, campo faltando, texto nulo — nada disso é exceção."""
    segmentos = [
        {"start": 5.0, "end": 1.0, "text": "invertido."},
        {"start": "x", "end": 2.0, "text": "ruim."},
        {"start": 0.0, "end": 2.0, "text": None},
        {"start": 2.0, "end": 4.0, "text": "Boa."},
    ]
    inicios, fins = ClipSelector._sentence_marks(segmentos)
    assert 4.0 in fins


# ── 3. os irmãos que eram entregues em dobro ────────────────────────────────


def test_uma_lasca_de_sobreposicao_e_encostar():
    """O editor: "o corte perfeito seria o 1+18 juntos".

    Naquela rodada o corte 1 terminava em 2200,4 e o 18 começava em 2199,9 —
    quarenta centésimos de sobreposição. A regra exigia folga >= 0 e não via
    nenhum dos sete pares colados; via um só, o único com folga positiva.
    """
    def enxerga(gap):
        return -ClipSelector.TOUCHING_OVERLAP_S <= gap <= ClipSelector.TOUCHING_GAP_S

    for gap in (-0.40, -0.24, -0.84, -1.00, -1.26, -1.96, 0.0, 0.76, 2.5):
        assert enxerga(gap), f"folga de {gap}s deixou de ser encostar"


def test_sobreposicao_grande_continua_sendo_outro_problema():
    """Engolir sobreposição de verdade aqui escondia qual candidato perdeu
    para qual. A lasca é ruído de arredondamento; dezoito segundos não são."""
    assert not (-ClipSelector.TOUCHING_OVERLAP_S <= -17.91 <= ClipSelector.TOUCHING_GAP_S)
    assert not (-ClipSelector.TOUCHING_OVERLAP_S <= -5.0 <= ClipSelector.TOUCHING_GAP_S)


def test_a_regra_ainda_exige_que_ninguem_pergunte_no_meio():
    """A proteção que impede o passe de apagar respostas distintas continua de
    pé: se o entrevistador toma a palavra na junta, são duas respostas."""
    import inspect

    origem = inspect.getsource(ClipSelector._drop_touching_siblings)
    assert "pergunta_entre" in origem
    assert "TOUCHING_OVERLAP_S" in origem


def test_o_limite_da_lasca_e_declarado_e_pequeno():
    assert 0 < ClipSelector.TOUCHING_OVERLAP_S <= 3.0
