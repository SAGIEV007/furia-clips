"""O corpus de estilo do editor estava no repositório e ninguém lia.

`data/estilo/headlines_publicadas.json` foi transcrito das capturas que o editor
mandou: dezenove chamadas superiores que ele **publicou de verdade**, sete padrões
de forma com os verbos que ele usa, nove palavras que ele subiu para caixa alta, e
seis regras lidas do próprio corpus. Nenhuma linha disso chegava ao gerador.

Enquanto isso o `headline_copy.HOOKS` tinha treze ganchos inventados por mim.
Cruzando as duas listas, **só "BOMBA!" coincidia**. É exatamente a queixa dele
sobre as três headlines que rejeitou:

    "não tem uma coisa para chamar a atenção como eu fiz no meu"

A correção é usar o vocabulário dele em vez do meu. Mas nem tudo no corpus
transfere, e o próprio corpus avisa:

    Copiar um molde daqui sobre um corte que não o sustenta produz manchete falsa,
    que é pior do que manchete fraca.

Há duas espécies de chamada ali. Uma é **reação pura** — "VIRALIZOU!", "NA LATA!",
"CHOCADA!", "MEU DEUS!" — que só diz o que sentir e serve a qualquer corte da
mesma postura. A outra **carrega conteúdo** — "FIM DO XANDÃO?", "NEM FLÁVIO, NEM
LULA:", "DE MILÍCIA A COMANDO VERMELHO" — e reusar isso num corte que não fala de
Moraes é afirmar um fato que o corte não tem. Só a primeira espécie entra.
"""

import json
import pathlib

import pytest

from modules.estilo_publicado import (
    carregar_estilo,
    ganchos_observados,
    ganchos_que_transferem,
)

CORPUS = pathlib.Path("data/estilo/headlines_publicadas.json")


@pytest.fixture(scope="module")
def estilo():
    if not CORPUS.exists():
        pytest.skip("corpus de estilo ausente")
    return carregar_estilo()


# ── o corpus chega ao gerador ──────────────────────────────────────────────

def test_o_corpus_e_de_fato_lido(estilo):
    assert estilo["ganchos"], "as chamadas superiores não foram lidas"
    assert estilo["padroes"], "os padrões de forma não foram lidos"
    assert estilo["enfase"], "as palavras de ênfase não foram lidas"


def test_os_ganchos_do_gerador_vem_do_feed_do_editor():
    """O teste que descreve o defeito: treze ganchos meus, um em comum com ele."""
    from modules.headline_copy import HOOKS

    do_gerador = {gancho for lista in HOOKS.values() for gancho in lista}
    do_feed = set(ganchos_observados())
    assert do_feed, "o feed não trouxe gancho nenhum"
    vindos_do_feed = do_gerador & do_feed
    assert len(vindos_do_feed) >= 6, (
        f"só {len(vindos_do_feed)} dos {len(do_gerador)} ganchos do gerador saem do "
        f"feed do editor; o resto continua inventado: {sorted(do_gerador - do_feed)}"
    )


# ── o que transfere e o que não transfere ──────────────────────────────────

@pytest.mark.parametrize("gancho", [
    "NA LATA!", "CHOCADA!", "BOMBA!", "MEU DEUS!", "SEM FILTRO!", "INUSITADO!",
])
def test_reacao_pura_transfere(gancho):
    assert gancho in ganchos_que_transferem(), (
        f"{gancho!r} é reação pura e serve a qualquer corte da mesma postura"
    )


@pytest.mark.parametrize("gancho", [
    # Nomeiam gente ou episódio: só eram verdadeiras no corte de onde saíram.
    "FIM DO XANDÃO?",
    "NEM FLÁVIO, NEM LULA:",
    "DE MILÍCIA A COMANDO VERMELHO",
    "ALERTA DE TESTOSTERONA!",
    # Afirmam algo sobre o próprio corte. "VIRALIZOU!" num corte que o Furia
    # acabou de gerar é simplesmente falso — ele não viralizou, nem foi
    # publicado. "RESPOSTA HONESTA!" afirma que há resposta e que ela é honesta,
    # duas coisas que a ferramenta não tem como saber. Eram verdadeiras quando o
    # editor as escolheu à mão olhando o post; não transferem para uma máquina
    # que escolhe antes.
    "VIRALIZOU!",
    "EM ALTA!",
    "RESPOSTA HONESTA! KKKK",
])
def test_gancho_que_carrega_conteudo_nao_transfere(gancho):
    """Reusar isso num corte que não sustenta é afirmar o que ele não diz.

    É o aviso do próprio corpus: molde copiado sobre corte que não o sustenta
    produz manchete falsa, que é pior que manchete fraca.
    """
    assert gancho not in ganchos_que_transferem(), (
        f"{gancho!r} carrega conteúdo e viraria afirmação falsa noutro corte"
    )


def test_nenhum_gancho_passa_do_tamanho_que_o_editor_usa(estilo):
    """`palavras_max: 4`, lido do corpus e não escolhido por mim."""
    limite = estilo["ganchos_palavras_max"]
    assert limite >= 1
    for gancho in ganchos_que_transferem():
        assert len(gancho.split()) <= limite, f"{gancho!r} passa de {limite} palavras"


def test_todo_gancho_que_transfere_saiu_do_feed(estilo):
    observados = set(ganchos_observados())
    for gancho in ganchos_que_transferem():
        assert gancho in observados, f"{gancho!r} não está no feed; voltou a ser invenção"


# ── a headline continua descrevendo o corte ────────────────────────────────

def test_o_gancho_do_feed_nao_afrouxa_o_portao_de_invencao():
    """Usar o vocabulário dele não é licença para dizer o que o corte não diz."""
    from modules.headline_studio import FORMAT_SQUARE, generate_artwork_copy

    legenda = """1
00:00:00,000 --> 00:00:06,000
O STF virou um problema para a democracia brasileira.

2
00:00:06,000 --> 00:00:12,000
Ministros que ninguém elegeu decidem o que pode ser dito.
"""
    resultado = generate_artwork_copy(
        legenda, mini_context="Renan Santos sobre o STF",
        preferred_format=FORMAT_SQUARE, ai_backend=None,
    )
    sugestoes = resultado["formats"][FORMAT_SQUARE]["suggestions"]
    assert sugestoes
    fonte = legenda.lower()
    for item in sugestoes:
        assert item["eyebrow"].strip(), "headline sem gancho"
        corpo = item["headline"].lower()
        for palavra in ("bolsonaro", "lula", "moraes", "xandão"):
            assert palavra not in corpo, (
                f"a headline citou {palavra!r}, que não está no corte: {item['headline']!r}"
            )
        assert "stf" in corpo or "supremo" in corpo or fonte, corpo


def test_o_corpus_corrompido_nao_derruba_a_geracao(tmp_path, monkeypatch):
    """Um arquivo de estilo quebrado degrada para o padrão, não para exceção."""
    quebrado = tmp_path / "estilo.json"
    quebrado.write_text("{ isto não é json", encoding="utf-8")
    monkeypatch.setattr("modules.estilo_publicado._CAMINHO", quebrado)
    monkeypatch.setattr("modules.estilo_publicado._CACHE", None)
    estilo = carregar_estilo()
    assert estilo["ganchos"] == []
    assert ganchos_que_transferem(), "sem corpus o gerador ficou sem gancho nenhum"


def test_o_corpus_e_json_valido_e_tem_o_que_promete():
    if not CORPUS.exists():
        pytest.skip("corpus ausente")
    dados = json.loads(CORPUS.read_text(encoding="utf-8"))
    assert dados["chamadas_superiores"]["observadas"]
    assert dados["chamadas_superiores"]["palavras_max"] >= 1
    assert dados["padroes"] and dados["regras_lidas_do_corpus"]
