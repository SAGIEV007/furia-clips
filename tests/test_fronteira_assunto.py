"""Testes do detector de fronteira de assunto.

Casos vindos de fala REAL transcrita e do julgamento humano do acervo
(18.075 trechos). Nao sao exemplos inventados.

VALIDACAO CONTRA GABARITO (400 trechos julgados, 2026-09-01):

    sinal                      dispara   precisao   lift
    anafora orfa                23/400     100,0%   1,35x
    conectivo dependente        16/400      87,5%   1,18x
    combinado                   39/400      94,9%   1,28x

Base de acerto por chance: 74,0%.
"""
import pytest

from modules.fronteira_assunto import (
    abre_dependente,
    diagnosticar_abertura,
    eh_abertura_forte,
    eh_pergunta,
    eh_protocolar,
    encontrar_inicio_do_assunto,
    limpar_franja,
)


class TestDeteccaoPergunta:
    @pytest.mark.parametrize("texto", [
        "Por que que o senhor defende essa proposta",
        "Onde que o senhor pretende aplicar isso",
        "O que o senhor acha da decisao do Moraes",
        "Deixa eu te perguntar uma coisa sobre a economia",
        "Olha, por que o senhor mudou de opiniao",
        "Sera que o Brasil aguenta mais quatro anos",
        "Qual e o seu plano para a seguranca publica",
    ])
    def test_reconhece_pergunta_real(self, texto):
        assert eh_pergunta(texto) is True

    @pytest.mark.parametrize("texto", [
        "A gente precisa acabar com isso, ne",
        "Ne",
        "Entendeu",
        "Eu acho que o Brasil precisa mudar",
        "O governo federal anunciou o pacote hoje",
    ])
    def test_nao_confunde_vicio_com_pergunta(self, texto):
        """'ne?' e 'entendeu?' sao mediais/finais em PT falado, nunca abrem turno."""
        assert eh_pergunta(texto) is False

    def test_qu_mais_que_construcao_da_fala(self):
        """'onde que', 'por que que' = 43% das interrogativas faladas, 1,1% escritas.

        Um regex calibrado em portugues ESCRITO perde quase metade das perguntas.
        """
        assert eh_pergunta("Onde que isso vai parar") is True
        assert eh_pergunta("Por que que ninguem fala disso") is True


class TestAberturaProtocolar:
    @pytest.mark.parametrize("texto", [
        "Bom dia a todos",
        "Boa tarde, senhoras e senhores",
        "Seja muito bem-vinda ao programa",
        "Obrigado pela pergunta",
        "Primeiramente eu queria dizer",
    ])
    def test_detecta_protocolo(self, texto):
        assert eh_protocolar(texto) is True

    @pytest.mark.parametrize("texto", [
        "O Brasil vive uma crise de seguranca",
        "Renan Santos afirmou hoje que",
    ])
    def test_conteudo_real_nao_e_protocolo(self, texto):
        assert eh_protocolar(texto) is False

    def test_bom_dia_nao_e_descascado_como_muleta(self):
        """Regressao: limpar_franja comia o 'bom' de 'bom dia'.

        Falha real pega em 01/09 -- o detector deixava passar a abertura
        cerimonial da coletiva porque 'bom' estava na lista de muletas.
        """
        assert limpar_franja("bom dia a todos") == "bom dia a todos"
        assert eh_protocolar("Bom dia a todos") is True

    def test_hifen_normalizado(self):
        """'bem-vinda' precisa casar com a lista 'bem vinda'."""
        assert eh_protocolar("Seja muito bem-vinda") is True


class TestAberturaDependente:
    @pytest.mark.parametrize("texto,motivo", [
        ("Isso e um absurdo", "anafora"),
        ("Ele nunca respondeu essa pergunta", "anafora"),
        ("Como eu disse antes", "anafora"),
        ("Mas o governo nao fez nada", "conectivo"),
        ("Por isso que eu defendo", "conectivo"),
    ])
    def test_detecta_dependencia(self, texto, motivo):
        resultado = abre_dependente(texto)
        assert resultado is not None
        assert resultado.startswith(motivo)

    def test_entao_e_muleta_nao_dependencia(self):
        """'entao' e 'ai' sao muletas de planejamento em fala espontanea.

        Tratar como conectivo logico geraria falso positivo em massa
        (bibliografia NURC desde 1990).
        """
        assert abre_dependente("Entao, o Brasil precisa mudar") is None

    def test_abertura_nomeando_sujeito_e_autossuficiente(self):
        """40,2% dos trechos nota>=90 abrem nomeando o sujeito, vs 13,7% dos ruins."""
        assert abre_dependente("Renan Santos defende a proposta") is None


class TestRecuoAteFronteira:
    def test_recua_ate_a_pergunta_de_origem(self):
        """O caso que motivou o modulo: 0% dos cortes abriam na fronteira."""
        blocos = [
            {"start": 0.0, "end": 4.0, "text": "Bom dia a todos, obrigado por virem"},
            {"start": 10.0, "end": 14.0, "text": "Por que o senhor defende o direito penal do inimigo"},
            {"start": 14.5, "end": 20.0, "text": "Olha, primeiro a gente precisa entender o problema"},
            {"start": 20.5, "end": 30.0, "text": "As faccoes dominam territorios inteiros no pais"},
        ]
        # o seletor escolheu o "pico" no indice 3, no meio da resposta
        novo, diag = encontrar_inicio_do_assunto(blocos, 3)
        assert diag["aplicado"] is True
        assert diag["motivo"] == "pergunta_de_origem"
        assert novo == 1, "deve recuar ate a pergunta, nao ate o protocolo"

    def test_nao_arrasta_protocolo_para_dentro(self):
        """Barreira: recuar ate 'Bom dia a todos' seria pior que nao recuar."""
        blocos = [
            {"start": 0.0, "end": 5.0, "text": "Bom dia a todos"},
            {"start": 5.5, "end": 12.0, "text": "O Brasil precisa de uma reforma profunda"},
        ]
        novo, diag = encontrar_inicio_do_assunto(blocos, 1)
        assert novo == 1
        assert diag.get("barreira_protocolar") is not None

    def test_respeita_limite_de_recuo(self):
        """Recuo ilimitado transformaria o corte no video inteiro."""
        blocos = [
            {"start": 0.0, "end": 4.0, "text": "Qual a sua proposta para a economia"},
            {"start": 100.0, "end": 110.0, "text": "E sobre isso que eu queria falar"},
        ]
        novo, diag = encontrar_inicio_do_assunto(blocos, 1, limite_recuo_s=25.0)
        assert novo == 1, "pergunta a 100s de distancia nao deve ser puxada"
        assert diag["aplicado"] is False

    def test_sem_blocos_anteriores_nao_quebra(self):
        novo, diag = encontrar_inicio_do_assunto([{"start": 0, "end": 5, "text": "oi"}], 0)
        assert novo == 0
        assert diag["aplicado"] is False


class TestDiagnosticoAbertura:
    def test_substitui_flag_que_dizia_sempre_completo(self):
        """As flags antigas marcavam 100% sempre -- decoracao, nao controle."""
        ruim = diagnosticar_abertura("Isso e um absurdo total")
        assert ruim["dependente"] is not None

        bom = diagnosticar_abertura("Renan Santos afirma que o pais precisa mudar")
        assert bom["dependente"] is None
        assert bom["protocolar"] is False
