"""O espelho do CHUB: amostra de verdade, e dúvida declarada como dúvida.

O Furia vinha aprendendo com 71 registros — daí 55 das suas 58 famílias com uma
observação só, e daí o Campaign Hub não mover o ranking nem um ponto. O espelho
traz os resumos de 29.596 posts.

Metade destes testes existe por causa de erro meu, pego medindo em vez de lendo
o código:

- O mapa guardava "Romeu Zema" e o trecho falado diz "Zema". Passava batido.
- "Flávio Bolsonaro" acusava também Jair, pelo sobrenome.
- "Renan Calheiros" acusava Renan Santos, pelo primeiro nome — virando um
  aliado numa presença fantasma e um adversário em dois.
"""

import json
from pathlib import Path

import pytest

from modules import espelho_chub as espelho

ARQUIVO = Path(__file__).resolve().parents[1] / "data" / "espelho_chub.json"


def test_o_espelho_vem_dentro_do_programa():
    """Ele tem que servir na primeira abertura, sem depender da rede.

    A máquina onde este código é escrito não alcança o servidor do CHUB. Se o
    espelho só existisse depois de uma sincronização bem-sucedida, o editor
    ficaria dependendo de um cliente que ninguém conseguiu testar.
    """
    assert ARQUIVO.is_file()
    assert espelho.descrever()["disponivel"] is True


def test_a_amostra_e_a_de_verdade_e_nao_a_de_71_registros():
    forte = espelho.gancho("tese-provocativa")
    assert forte is not None
    assert forte["n"] >= 400, f"n={forte['n']} — o espelho voltou a ser o arquivo antigo"


def test_o_gancho_que_mais_rende_continua_medindo_mais():
    """news-peg tem mediana 1,40 contra 0,98 da tese-provocativa.

    É o achado que justifica a etapa inteira, e ele se repete em três lugares
    independentes: Instagram 1,403 (n=47), TikTok 1,782 (n=36) e a conta
    reserva 2,186 (n=10). Sinal que aparece em três contas não é acaso.
    """
    for plataforma, conta in (("instagram", "@renansantosmbl"),
                              ("tiktok", "@renansantosmbl"),
                              ("instagram", "@renansantosreserva")):
        peg = espelho.gancho("news-peg", conta, plataforma)
        tese = espelho.gancho("tese-provocativa", conta, plataforma)
        assert peg and tese
        assert peg["mediana"] > tese["mediana"], f"{conta}/{plataforma}"


def test_as_duas_familias_que_o_furia_nao_detectava_estao_no_espelho():
    for familia in ("numero-choque", "contraste-regional"):
        assert familia in espelho.familias_conhecidas()


def test_o_piso_de_tres_observacoes_vale_para_tudo():
    """Ler o formato certo não é aceitar qualquer amostra."""
    assert espelho.MINIMO_DE_OBSERVACOES == 3
    for item in espelho.carregar().get("ganchos") or []:
        if item["n"] < 3:
            achado = espelho.gancho(item["familia"], item["conta"], item["plataforma"])
            assert achado is None


def test_os_temas_separam_o_que_rende_do_que_nao_rende():
    melhor = espelho.tema("corrupcao-e-escandalos")
    pior = espelho.tema("congresso-centrao")
    assert melhor and pior
    assert melhor["mediana"] > pior["mediana"] * 1.5


# ── o mapa de nomes ──────────────────────────────────────────────────────────

def test_um_adversario_claro_e_marcado_como_adversario():
    achado = espelho.papel("Flávio Bolsonaro")
    assert achado["lado"] == "adversario"
    assert achado["confianca"] >= 0.8
    assert achado["contra"] > achado["a_favor"] * 3


def test_um_empate_nao_vira_adversario():
    """Zema aparece 62 vezes contra e 60 a favor. Isso não é uma posição.

    Era um dos dois nomes que o editor deu como exemplo de adversário. O dado
    não confirma, e o espelho tem que dizer isso em vez de escolher um lado
    porque a pergunta foi feita.
    """
    achado = espelho.papel("Romeu Zema")
    assert achado["lado"] == "indefinido"
    assert achado["confianca"] < 0.7


def test_o_protagonista_nao_e_confundido_com_adversario():
    achado = espelho.papel("Renan Santos")
    assert achado["lado"] == "aliado"
    assert achado["confianca"] >= 0.95


def test_o_apelido_falado_encontra_a_pessoa():
    """O espelho guarda "Romeu Zema"; ninguém fala assim."""
    assert espelho.papeis_no_texto("o Zema desconversou")[0]["nome"] == "Romeu Zema"


def test_o_sobrenome_nao_contamina_quem_o_carrega():
    """"Flávio Bolsonaro" não pode acusar Jair junto."""
    achados = espelho.papeis_no_texto("O Flávio Bolsonaro não soube responder.")
    assert [item["nome"] for item in achados] == ["Flávio Bolsonaro"]


def test_o_primeiro_nome_nao_contamina_um_homonimo():
    """"Renan Calheiros" não pode acusar Renan Santos junto."""
    achados = espelho.papeis_no_texto("O Renan Calheiros preside o Senado.")
    assert [item["nome"] for item in achados] == ["Renan Calheiros"]


def test_um_sobrenome_sozinho_ainda_resolve_para_o_mais_citado():
    """O controle do teste acima: sem o nome completo, o mapa não pode calar."""
    achados = espelho.papeis_no_texto("O Bolsonaro falou ontem.")
    assert [item["nome"] for item in achados] == ["Jair Bolsonaro"]


def test_texto_sem_politico_nao_inventa_ninguem():
    assert espelho.papeis_no_texto("Bata a manteiga com o açúcar até clarear.") == []
    assert espelho.papeis_no_texto("") == []


def test_o_espelho_da_pasta_de_dados_tem_precedencia(tmp_path):
    """É assim que o chub.bat atualiza sem trocar a versão do programa."""
    destino = tmp_path / "chub"
    destino.mkdir()
    (destino / "espelho.json").write_text(json.dumps({
        "schema": "espelho-chub-v1",
        "gerado_em": "2030-01-01T00:00:00+00:00",
        "fonte": {"posts_com_desempenho": 99999},
        "ganchos": [{"conta": "@renansantosmbl", "plataforma": "instagram",
                     "familia": "news-peg", "n": 900, "mediana": 2.0, "p90": 4.0}],
        "temas": [], "papeis": [], "formatos": [],
    }), encoding="utf-8")

    espelho.recarregar()
    try:
        assert espelho.gancho("news-peg", data_dir=tmp_path)["n"] == 900
        assert espelho.descrever(tmp_path)["origem"] == "pasta de dados"
    finally:
        espelho.recarregar()


def test_um_espelho_corrompido_cai_para_o_do_pacote(tmp_path):
    """O arquivo vem de fora e é editável à mão; não pode derrubar o corte."""
    destino = tmp_path / "chub"
    destino.mkdir()
    (destino / "espelho.json").write_text("{isto não é json", encoding="utf-8")

    espelho.recarregar()
    try:
        assert espelho.descrever(tmp_path)["disponivel"] is True
        assert espelho.gancho("tese-provocativa", data_dir=tmp_path)["n"] >= 400
    finally:
        espelho.recarregar()


def test_o_espelho_nao_carrega_credencial_nenhuma():
    """Ele é publicado junto com o programa, num repositório público."""
    bruto = ARQUIVO.read_text(encoding="utf-8")
    for marca in ("wk_", "AIza", "sk-ant-", "chub-api", "http://", "https://"):
        assert marca not in bruto, f"o espelho carrega '{marca}'"


def test_o_espelho_cabe_no_programa():
    """Precisa viajar junto com o repositório sem pesar."""
    assert ARQUIVO.stat().st_size < 250 * 1024
