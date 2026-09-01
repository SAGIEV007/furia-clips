"""Teste de ponta a ponta: a via de reserva precisa aprovar ALGUM corte.

Contexto (01/09): rodando o Fúria na entrevista da IstoÉ (32 min, material bom),
a via NLP entregou ZERO cortes de 15 candidatos. A suíte inteira estava verde —
os testes cobriam cada regra isoladamente, mas ninguém perguntava o essencial:
*este programa consegue entregar alguma coisa?*

Dois gargalos de escala empilhados causavam isso:
  1. `viral_score` só subtraía. Partia da média dos blocos (~45) e apenas
     descia, contra um piso de 50 no `quality_gate` — matematicamente incapaz
     de alcançar o próprio filtro.
  2. `hook_grade` exigia `start_score > 50` na mesma escala comprimida (base
     40), reprovando 13 de 15 candidatos com abertura densa em "weak_hook".

Este teste falha se a calibração voltar a ficar impossível de satisfazer.
"""

import pytest

from modules.clip_selector import ClipSelector


def _fala(inicio, fim, texto):
    return {"id": 0, "start": inicio, "end": fim, "text": texto, "words": []}


@pytest.fixture
def transcricao_boa():
    """Entrevista sintética: fala contínua, assunto fechado, prova concreta.

    Espelha o material real que foi injustamente reprovado — sem silêncio,
    contexto e desfecho completos, números e nomes citados.
    """
    falas = []
    t = 0.0
    blocos = [
        "As pessoas gostam de prefeitos populares.",
        "Só que elas não conseguem determinar pelo voto para onde vai o dinheiro dos partidos.",
        "O fundo partidário passou de dois bilhões de reais na última eleição.",
        "Esse dinheiro foi para show de Wesley Safadão e de Alok em campanha municipal.",
        "E esses municípios não melhoraram em nada depois disso.",
        "Quanto mais pobre o município, mais dependente ele fica dessa estrutura.",
        "O prefeito vira refém do repasse e o eleitor perde o poder de cobrar.",
        "A gente vê isso em cidade do interior inteira, ano após ano, sem exceção.",
        "Enquanto isso o partido cresce e a cidade continua exatamente igual.",
        "Por isso a nossa proposta começa cortando o fundo partidário pela metade.",
        "É o primeiro projeto que a gente apresenta se for eleito.",
    ]
    for texto in blocos:
        # ~7s por fala mantém o clipe acima do piso de 45s da calibração Chub.
        dur = max(7.0, len(texto) / 11.0)
        falas.append(_fala(t, t + dur, texto))
        t += dur
    return {"segments": falas, "text": " ".join(blocos)}


class TestViaDeReservaEntregaAlgo:
    def test_material_bom_produz_pelo_menos_um_candidato(self, transcricao_boa):
        cs = ClipSelector()
        clips = cs.select_clips(transcricao_boa)
        assert clips, "a via de reserva não gerou nenhum candidato"

    def test_material_bom_nao_pode_ter_zero_aprovados(self, transcricao_boa):
        """O bug real: 15 candidatos, 0 aprovados, suíte verde."""
        cs = ClipSelector()
        clips = cs.select_clips(transcricao_boa)
        aprovados = [c for c in clips if cs.quality_gate(c)[0] in ("accept", "review")]
        assert aprovados, (
            "nenhum corte aprovado em material limpo — a escala de nota "
            f"não alcança o próprio filtro. Notas geradas: "
            f"{sorted((c.get('viral_score', 0) for c in clips), reverse=True)}"
        )

    def test_a_nota_maxima_alcanca_o_piso_do_filtro(self, transcricao_boa):
        """Invariante de escala: se o teto fica abaixo do piso, nada passa."""
        cs = ClipSelector()
        clips = cs.select_clips(transcricao_boa)
        melhor = max(c.get("viral_score", 0) for c in clips)
        assert melhor >= 50, (
            f"teto da via NLP é {melhor}, abaixo do piso 50 do quality_gate — "
            "a calibração é impossível de satisfazer"
        )


class TestSinaisDeQualidadeSaoPremiados:
    def test_gancho_denso_vale_mesmo_sem_palavra_gatilho(self, transcricao_boa):
        """Fala direta e densa é bom gancho, mesmo sem 'você sabia' ou
        'presta atenção' — o dicionário não pode ser o único critério."""
        cs = ClipSelector()
        clips = cs.select_clips(transcricao_boa)
        assert any(c.get("has_hook") for c in clips), (
            "nenhum candidato reconhecido com gancho, apesar de abertura densa"
        )

    def test_via_nlp_publica_densidade_de_gancho(self, transcricao_boa):
        """hook_density existia só na via LLM; sem ele o piso de gancho
        nunca disparava neste caminho."""
        cs = ClipSelector()
        clips = cs.select_clips(transcricao_boa)
        assert clips
        for c in clips:
            assert "hook_density" in c, "via NLP não publica hook_density"
            assert "speech_density" in c, "via NLP não publica speech_density"

    def test_fala_continua_gera_densidade_alta(self, transcricao_boa):
        cs = ClipSelector()
        clips = cs.select_clips(transcricao_boa)
        melhor = max(clips, key=lambda c: c.get("viral_score", 0))
        assert melhor.get("speech_density", 0) > 0.9, (
            "transcrição sem pausas deveria render densidade alta"
        )
