"""Gancho nos primeiros 30s e piso de fala na via LLM.

Contexto (01/09): a coletiva do Renan gerou um corte de 54s com 47s MUDOS no
começo — 12% de densidade de fala — e mesmo assim recebeu a MAIOR nota do lote
e foi entregue. Dois defeitos permitiram isso:

1. `speech_density` só era calculado na via NLP. Na via LLM (o caminho de
   produção) o campo nunca existia, então o piso de 60% do `quality_gate`
   silenciosamente nunca disparava.
2. Nada media a janela inicial. Medição no Chub (708 vídeos, 01/09) mostra que
   a retenção real vive nos primeiros ~30s em QUALQUER duração: 30,8s assistidos
   num clipe médio de 122s. Silêncio nessa janela custa a audiência inteira.
"""

import pytest

from modules.clip_selector import ClipSelector


@pytest.fixture
def selector():
    return ClipSelector()


def _blocos(intervalos):
    """Constrói blocos de fala a partir de pares (início, fim)."""
    return [
        {"start": ini, "end": fim, "text": f"fala de {ini:.0f}s a {fim:.0f}s",
         "duration": fim - ini}
        for ini, fim in intervalos
    ]


class TestDensidadeDeFala:
    def test_corte_mudo_da_coletiva_e_medido_corretamente(self, selector):
        """O corte real: 54s de duração, fala só a partir dos 47s."""
        blocos = _blocos([(47.0, 54.0)])
        densidade = selector._calculate_speech_density(blocos, 0.0, 54.0)
        assert densidade < 0.2, f"esperado ~0.13, veio {densidade}"

    def test_corte_cheio_de_fala_pontua_alto(self, selector):
        blocos = _blocos([(0.0, 60.0)])
        assert selector._calculate_speech_density(blocos, 0.0, 60.0) == 1.0

    def test_piso_de_60_por_cento_rejeita_o_corte_mudo(self, selector):
        clipe = {
            "duration": 54.0, "viral_score": 95, "has_hook": True,
            "context_complete": True, "payoff_complete": True,
            "speech_density": 0.13,
        }
        veredito, motivo = selector.quality_gate(clipe)
        assert veredito == "reject"
        assert motivo == "low_speech_density"

    def test_piso_preserva_os_cortes_bons_da_coletiva(self, selector):
        """Cortes 9 e 10 tinham 68% e 99% — não podem ser mortos junto."""
        for densidade in (0.68, 0.99, 1.0):
            clipe = {
                "duration": 120.0, "viral_score": 80, "has_hook": True,
                "context_complete": True, "payoff_complete": True,
                "speech_density": densidade,
            }
            veredito, _ = selector.quality_gate(clipe)
            assert veredito != "reject", f"densidade {densidade} não devia ser cortada"


class TestGanchoNosPrimeiros30s:
    def test_gancho_mede_so_a_janela_inicial_nao_o_clipe_todo(self, selector):
        """Clipe de 120s com os primeiros 30s mudos: densidade geral alta,
        gancho péssimo. É exatamente o caso que o total esconde."""
        blocos = _blocos([(30.0, 120.0)])

        geral = selector._calculate_speech_density(blocos, 0.0, 120.0)
        gancho = selector._calculate_speech_density(blocos, 0.0, 30.0)

        assert geral >= 0.7, "no total o clipe parece saudável"
        assert gancho == 0.0, "mas a janela que importa está vazia"

    def test_gancho_forte_quando_a_fala_comeca_na_hora(self, selector):
        blocos = _blocos([(0.0, 120.0)])
        assert selector._calculate_speech_density(blocos, 0.0, 30.0) == 1.0

    def test_pausa_curta_de_respiro_nao_condena_o_gancho(self, selector):
        """2s de pausa aos 10s é respiro normal de fala, não defeito."""
        blocos = _blocos([(0.0, 10.0), (12.0, 30.0)])
        gancho = selector._calculate_speech_density(blocos, 0.0, 30.0)
        assert gancho > 0.9


class TestPenalidadeDeGanchoNaNota:
    """A regra aplicada na via LLM: <0.5 perde 25 pontos, <0.7 perde 10."""

    @staticmethod
    def _aplicar(nota, gancho):
        if gancho < 0.5:
            nota -= 25
        elif gancho < 0.7:
            nota -= 10
        return max(0, min(100, nota))

    def test_corte_mudo_perde_a_lideranca_do_lote(self):
        """O caso real: nota 95 com gancho de 12% cai abaixo de um
        concorrente honesto de nota 78."""
        mudo = self._aplicar(95, 0.12)
        honesto = self._aplicar(78, 1.0)
        assert mudo < honesto, f"mudo={mudo} ainda ganha de honesto={honesto}"

    def test_gancho_limpo_nao_perde_ponto(self):
        assert self._aplicar(80, 1.0) == 80

    def test_penalidade_e_escalonada_nao_binaria(self):
        forte = self._aplicar(80, 0.95)
        morno = self._aplicar(80, 0.6)
        fraco = self._aplicar(80, 0.2)
        assert forte > morno > fraco

    def test_nota_nunca_sai_da_escala(self):
        assert self._aplicar(10, 0.0) == 0
        assert self._aplicar(100, 1.0) == 100
