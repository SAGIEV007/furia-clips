"""Abertura cerimonial não é conteúdo.

Contexto (01/09): a coletiva entregou como MAIOR nota do lote um corte que era
abertura protocolar. Depois, na entrevista da IstoÉ, entrou na lista de
aprovados um corte abrindo com "Seja muito bem-vinda, seja muito bem-vindo você
que acompanha o canal…".

Por que os filtros anteriores não pegam: a densidade de fala é ALTA nesses
trechos — o apresentador fala sem parar. Silêncio não é o problema; o problema é
que a locução não entrega conteúdo nenhum. Nenhum medidor acústico distingue
saudação de argumento.

A detecção é textual e só vale no INÍCIO do trecho: "bem-vindo" citado no meio
de um raciocínio é conteúdo legítimo e não pode punir o corte.
"""

import pytest

from modules.clip_selector import ClipSelector


@pytest.fixture
def selector():
    return ClipSelector()


class TestDeteccaoDeAberturaCerimonial:
    def test_saudacao_real_da_istoe_e_detectada(self, selector):
        texto = (
            "Seja muito bem-vinda, seja muito bem-vindo você que acompanha o "
            "canal da IstoÉ no YouTube. Eu sou o seu apresentador e hoje "
            "recebemos o pré-candidato à presidência."
        )
        assert selector._editorial_flags(texto)["ceremonial_opening"] is True

    def test_pedido_de_inscricao_e_cerimonial(self, selector):
        texto = "Inscreva-se no canal e ative o sininho para não perder nenhum vídeo."
        assert selector._editorial_flags(texto)["ceremonial_opening"] is True

    def test_agradecimento_protocolar_de_coletiva(self, selector):
        texto = (
            "Agradeço a presença de todos os jornalistas aqui hoje. "
            "Vamos começar o programa."
        )
        assert selector._editorial_flags(texto)["ceremonial_opening"] is True

    def test_conteudo_real_nao_e_marcado(self, selector):
        texto = (
            "Essas pessoas estão se desengajando, porque a causa do bolsonarismo "
            "meio que morreu e ninguém apresentou outra."
        )
        assert selector._editorial_flags(texto)["ceremonial_opening"] is False

    def test_bem_vindo_no_meio_do_argumento_nao_pune(self, selector):
        """O caso que separa detecção boa de detecção burra: a palavra aparece,
        mas como parte do raciocínio, não como saudação de abertura."""
        texto = (
            "O fundo partidário passou de dois bilhões de reais. E aí o partido "
            "diz que você é bem-vindo a participar, mas não te dá voz nenhuma. "
            "Isso é uma farsa completa."
        )
        assert selector._editorial_flags(texto)["ceremonial_opening"] is False

    def test_pergunta_de_entrevistador_nao_e_cerimonial(self, selector):
        """Pergunta direta abre corte legítimo — não confundir com protocolo."""
        texto = (
            "Renan, eu vou começar te perguntando: por que o senhor quer se "
            "eleger presidente em 2026?"
        )
        assert selector._editorial_flags(texto)["ceremonial_opening"] is False


class TestPenalidadeDerrubaOProtocolar:
    """A regra aplicada nas duas vias: -18 pontos."""

    @staticmethod
    def _aplicar(nota, cerimonial):
        if cerimonial:
            nota -= 18
        return max(0, min(100, nota))

    def test_protocolar_perde_para_conteudo_de_nota_menor(self):
        """Caso real da IstoÉ: o protocolar tinha 53 e entrou entre os
        aprovados; um corte de conteúdo com 51 ficava atrás dele."""
        protocolar = self._aplicar(53, True)
        conteudo = self._aplicar(51, False)
        assert protocolar < conteudo

    def test_conteudo_nao_perde_ponto(self):
        assert self._aplicar(59, False) == 59

    def test_nota_nunca_sai_da_escala(self):
        assert self._aplicar(10, True) == 0


class TestFlagChegaAoClipe:
    def test_flag_e_publicado_no_dicionario_de_flags(self, selector):
        flags = selector._editorial_flags("Seja bem-vindo ao programa de hoje.")
        assert "ceremonial_opening" in flags, (
            "o sinal precisa estar nos flags para as duas vias consultarem"
        )
