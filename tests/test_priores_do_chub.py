"""Os dois priores do Campaign Hub: um estava desligado, o outro mentia.

O editor perguntou, com todas as letras, se o CHUB serve para alguma coisa
quando o Renan não aparece — se o tema é do MBL mas ele não fala, e se sobra
algum proveito num vídeo que não tem nada a ver com o MBL. Para responder isso
era preciso medir, e a medição achou dois defeitos.

**O prior de hook nunca disparou uma vez.** O código pedia à conta a chave
``hook_observations``; todo snapshot publicado, incluindo o que vem dentro do
programa, escreve ``hook_priors``. A chave não existia, a lista voltava vazia, e
``available`` era False em cada corte já pontuado — inclusive num texto que cai
exatamente na família mais forte da conta.

**O prior de padrão dava o bônus máximo ao que não reconhecia.** A família de
descarte era ``conversation_social``, que por acaso tem a maior mediana de views
da tabela inteira — um milhão, vinda de um único post. Medido em dez textos,
seis caíam ali, entre eles uma receita de bolo e um comentário de futebol, os
dois pontuando acima de um trecho sobre desestatização.

É o mesmo erro do portão de locutor, invertido: lá "não sei" virava "não";
aqui "não sei" virava "ótimo".
"""

import json
from pathlib import Path

import pytest

from modules.campaign_hub import build_performance_prior
from modules.instagram_editorial_priors import build_editorial_pattern_prior

PACOTE = Path(__file__).resolve().parents[1] / "data" / "editorial_priors.json"

TESE = "Eu vou dizer uma coisa: o PT mentiu por trinta anos e ninguém teve coragem."
BOLO = "Você bate a manteiga com o açúcar até ficar bem clarinho, e junta os ovos."
FUTEBOL = "O São Paulo jogou mal, o goleiro falhou nos dois gols do primeiro tempo."


@pytest.fixture(scope="module")
def snapshot():
    return json.loads(PACOTE.read_text(encoding="utf-8"))


def test_o_snapshot_publicado_usa_hook_priors_e_nao_hook_observations(snapshot):
    """A causa, antes de qualquer conserto: o formato do arquivo é este."""
    conta = snapshot["accounts"]["@renansantosmbl"]
    assert "hook_priors" in conta
    assert "hook_observations" not in conta, (
        "se o formato mudou, o adaptador pode ser simplificado — mas confira antes"
    )


def test_o_prior_de_hook_finalmente_dispara_na_familia_forte_da_conta(snapshot):
    """`tese-provocativa` tem seis observações no arquivo. Elas têm que chegar."""
    prior = build_performance_prior(TESE, account="@renansantosmbl", snapshot=snapshot)

    assert prior["hook_family"] == "tese-provocativa"
    assert prior["sample_count"] == 6, "as observações agrupadas não estão sendo lidas"
    assert prior["available"] is True, "o prior continua desligado"
    assert prior["confidence"] > 0


def test_o_piso_de_tres_observacoes_continua_valendo(snapshot):
    """Ler o formato certo não é o mesmo que aceitar qualquer amostra.

    `curiosity-gap` tem duas observações. Duas não viram regra, e não podem
    passar a virar só porque o adaptador começou a enxergar o arquivo.
    """
    prior = build_performance_prior(
        "Olha só, veja o que é isso. Será que você sabia?",
        account="@renansantosmbl", snapshot=snapshot,
    )
    assert prior["hook_family"] == "curiosity-gap"
    assert prior["sample_count"] == 2
    assert prior["available"] is False
    assert prior["observed_signal"] == 50.0


def test_o_sinal_fica_dentro_do_teto_combinado(snapshot):
    """Histórico de desempenho não pode atropelar contexto e fecho."""
    for texto in (TESE, BOLO, FUTEBOL):
        prior = build_performance_prior(texto, account="@renansantosmbl", snapshot=snapshot)
        assert 42.0 <= prior["observed_signal"] <= 58.0


def test_um_snapshot_torto_nao_derruba_o_corte():
    """O arquivo vem de fora; nenhum formato estranho pode virar exceção."""
    for conta in (
        {"hook_priors": "isto não é uma lista"},
        {"hook_priors": [{"hook": "tese-provocativa"}]},
        {"hook_priors": [{"hook": "", "observations": 9, "mean_ratio": 2.0}]},
        {"hook_priors": [{"hook": "x", "observations": -3, "mean_ratio": "abc"}]},
        {},
    ):
        prior = build_performance_prior(
            TESE, account="@renansantosmbl",
            snapshot={"accounts": {"@renansantosmbl": conta}},
        )
        assert prior["available"] is False
        assert prior["observed_signal"] == 50.0


def test_o_que_nao_e_reconhecido_recebe_neutro_e_nao_o_bonus_maximo():
    """Uma receita de bolo não pode pontuar como o post de um milhão de views."""
    for texto in (BOLO, FUTEBOL):
        prior = build_editorial_pattern_prior(texto, {})
        assert prior["family"] == "desconhecida"
        assert prior["available"] is False
        assert prior["signal"] == 50.0


def test_as_familias_que_o_classificador_realmente_reconhece_continuam_valendo():
    """O controle: neutralizar o descarte não pode apagar o que funcionava."""
    reconhecidas = {
        "No palco do evento, o debate esquentou de vez.": "event_mobilization",
        "O gráfico mostra que a arrecadação subiu 12% em três anos.": "graph_evidence",
        "Qual é a sua opinião sobre a reforma administrativa?": "political_question_answer",
    }
    for texto, esperada in reconhecidas.items():
        prior = build_editorial_pattern_prior(texto, {})
        assert prior["family"] == esperada
        assert prior["available"] is True


def test_uma_familia_declarada_pelo_corte_continua_mandando():
    """Quando o seletor já sabe a família, o classificador não opina."""
    prior = build_editorial_pattern_prior(BOLO, {"editorial_family": "event_mobilization"})
    assert prior["family"] == "event_mobilization"
    assert prior["available"] is True
