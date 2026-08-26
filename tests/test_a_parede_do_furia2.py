"""A tela 3 do Furia 2: a parede de cortes.

O coração do programa. A mecânica é a do Cipher, inteira: os cortes ficam
cinzas no breu, o que está sob o mouse ganha cor, e a informação não mora
embaixo de cada quadro — mora numa legenda única no pé da tela que troca
conforme o mouse anda. Catorze quadros com quatro linhas embaixo de cada um
são cinquenta e seis linhas competindo; catorze quadros e uma linha só é uma
coisa para ler por vez.

Os testes daqui foram escritos contra uma rodada de verdade dele: o debate da
Band sobre o Renan Santos, 29 minutos e meio de fonte, 11 cortes entregues, 12
descartados por sobreposição e 32 recusados.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CSS = RAIZ / "furia2" / "static" / "css" / "furia2.css"
JS = RAIZ / "furia2" / "static" / "js" / "bancada.js"


def sem_comentario(texto):
    """O texto sem os comentários.

    Terceira vez nesta série que um teste reprova por ler a própria explicação
    escrita acima da regra: o comentário que conta por que `line-clamp` saiu
    contém `line-clamp`. A correção certa nunca é afrouxar a verificação.
    """
    saida, resto = [], texto
    while "/*" in resto:
        antes, _, depois = resto.partition("/*")
        saida.append(antes)
        _, _, resto = depois.partition("*/")
    saida.append(resto)
    return "".join(saida)


def carregar_furia2():
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    spec = importlib.util.spec_from_file_location("furia2_app_parede", RAIZ / "furia2" / "app.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def folha(cortes, diagnostico=None, fonte="entrevista.mp4", duracao=1772.1):
    """Uma folha de decisões no formato que o Furia 1 grava de verdade."""
    return {
        "gerado_em": "2026-08-25T08:42:32",
        "versao": "2.0",
        "job_id": "teste",
        "fonte": {"arquivo": fonte, "duracao_s": duracao},
        "selecao": {"origem": "gemini", "diagnostico": diagnostico or {}},
        "cortes_renderizados": cortes,
    }


def corte(n, inicio, fim, conferir=False, texto="uma fala qualquer"):
    return {
        "rank": n,
        "start_s": inicio,
        "end_s": fim,
        "duration_s": fim - inicio,
        "origem": "gemini_primary",
        "viral_score": 67,
        "review_required": conferir,
        "review_reasons": ["voz não confirmada pelo áudio; confira quem fala"] if conferir else [],
        "texto": texto,
        # Campos que a folha carrega e a parede NÃO deve repassar:
        "score_breakdown": {"peso": 1},
        "transcricao": [{"t": 0, "fala": "..."}],
        "fronteiras": {"inicio": "frase"},
        "bloco_chub": "b354",
    }


@pytest.fixture()
def montado(tmp_path, monkeypatch):
    """Um Furia 2 apontando para uma pasta de diagnósticos de mentira."""
    furia2 = carregar_furia2()
    pasta = tmp_path / "diagnostics"
    pasta.mkdir()
    monkeypatch.setattr(furia2, "DIAGNOSTICOS", pasta)
    monkeypatch.setattr(furia2, "WORKSPACE_DIR", str(tmp_path / "workspace"))
    (tmp_path / "workspace").mkdir()
    return furia2, pasta


def gravar(pasta, dados, nome="selecao-teste-20260825T084232.json"):
    (pasta / nome).write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")


# ── a folha vira parede ─────────────────────────────────────────────────────


def test_sem_rodada_a_parede_nao_quebra(montado):
    furia2, _ = montado
    corpo = furia2.app.test_client().get("/api/cortes/lista").get_json()
    assert corpo["ok"] is True
    assert corpo["tem_rodada"] is False
    assert corpo["cortes"] == []


def test_a_parede_le_a_rodada_mais_recente(montado):
    """Ele roda a mesma entrevista de novo depois de mexer nos ajustes. A
    parede tem de mostrar a decisão de agora, não a de duas horas atrás."""
    import os
    import time

    furia2, pasta = montado
    gravar(pasta, folha([corte(1, 10, 40)]), "selecao-velha-20260101T000000.json")
    gravar(pasta, folha([corte(1, 10, 40), corte(2, 90, 150)]), "selecao-nova-20260825T084232.json")
    agora = time.time()
    os.utime(pasta / "selecao-velha-20260101T000000.json", (agora - 9000, agora - 9000))
    os.utime(pasta / "selecao-nova-20260825T084232.json", (agora, agora))

    corpo = furia2.app.test_client().get("/api/cortes/lista").get_json()
    assert len(corpo["cortes"]) == 2


def test_a_folha_estragada_nao_derruba_a_bancada(montado):
    """Arquivo cortado pela metade porque a máquina desligou no meio da
    gravação. A bancada abre vazia; nunca com uma tela de erro."""
    furia2, pasta = montado
    (pasta / "selecao-quebrada-20260825T084232.json").write_text("{{{ não é json", encoding="utf-8")
    corpo = furia2.app.test_client().get("/api/cortes/lista").get_json()
    assert corpo["tem_rodada"] is False


def test_a_parede_recebe_sete_campos_e_nao_vinte_e_quatro(montado):
    """A folha guarda vinte e quatro campos por corte; a parede mostra sete.

    Os outros são do talho e do painel. Mandar tudo para a tela seria construir
    a tentação de encher a parede com número que não muda decisão nenhuma —
    que é a lei 4 do conceito, e é como o programa velho virou um painel.
    """
    furia2, pasta = montado
    gravar(pasta, folha([corte(1, 10, 40)]))
    c = furia2.app.test_client().get("/api/cortes/lista").get_json()["cortes"][0]
    assert set(c) == {"n", "inicio", "fim", "duracao", "conferir", "motivos", "fala", "origem"}
    for pesado in ("transcricao", "score_breakdown", "fronteiras", "bloco_chub"):
        assert pesado not in c


def test_o_resumo_conta_o_que_ficou_de_fora(montado):
    """A parede mostra o que saiu. Quem conta o que NÃO saiu é o resumo — e é
    a pergunta que ele mais faz: por que só onze?"""
    furia2, pasta = montado
    gravar(pasta, folha(
        [corte(n, n * 100, n * 100 + 60, conferir=True) for n in range(1, 12)],
        diagnostico={"fallback_discarded_overlap": 12, "hard_negative_count": 32},
    ))
    resumo = furia2.app.test_client().get("/api/cortes/lista").get_json()["resumo"]
    assert resumo == {
        "entregues": 11,
        "conferir": 11,
        "descartados_por_sobreposicao": 12,
        "recusados": 32,
    }


def test_a_parede_fica_de_pe_sem_o_video_da_fonte(montado):
    """A folha e o vídeo andam separados: a folha veio da máquina dele.
    A decisão é o que importa; a imagem é conforto."""
    furia2, pasta = montado
    gravar(pasta, folha([corte(1, 10, 40)], fonte="um video que nao existe.mp4"))
    corpo = furia2.app.test_client().get("/api/cortes/lista").get_json()
    assert corpo["tem_rodada"] is True
    assert corpo["fonte"]["achada"] is False
    assert len(corpo["cortes"]) == 1


# ── o quadro do corte ───────────────────────────────────────────────────────


def test_o_quadro_e_arrancado_depois_do_inicio_e_nao_no_inicio():
    """O primeiro quadro de um corte cai muitas vezes num piscar de olho ou
    numa troca de câmera, e um mural de gente de olho fechado não ajuda a
    reconhecer nada."""
    origem = (RAIZ / "furia2" / "app.py").read_text(encoding="utf-8")
    trecho = origem[origem.find("def api_cortes_quadro"):]
    assert "inicio + 2" in trecho, "o quadro voltou a ser arrancado no início exato"


@pytest.mark.parametrize("n", ["0", "99", "-1", "", "abc"])
def test_o_quadro_recusa_um_corte_que_nao_existe(montado, n):
    furia2, pasta = montado
    gravar(pasta, folha([corte(1, 10, 40)]))
    resposta = furia2.app.test_client().get("/api/cortes/quadro", query_string={"n": n})
    assert resposta.status_code == 404


# ── a decisão que a primeira foto derrubou ──────────────────────────────────


def test_o_vermelho_so_marca_o_quadro_quando_ele_separa():
    """A primeira versão marcava todo corte que pedia conferência.

    Na rodada de verdade, os ONZE pediam — e a parede saiu listrada de
    vermelho de ponta a ponta. Uma marca que está em tudo não aponta para
    nada, e queima a única cor que ele lê sem pensar. Quando é a rodada
    inteira, quem conta é a legenda do pé; quando são alguns, o traço mostra
    quais.
    """
    codigo = JS.read_text(encoding="utf-8")
    assert "const marcarUmAUm = resumo.conferir > 0 && resumo.conferir < cortesNaParede.length;" in codigo
    assert 'quadro.dataset.conferir = (corte.conferir && marcarUmAUm) ? "1" : "0";' in codigo


def test_o_aviso_e_um_traco_e_nao_uma_moldura():
    """Moldura vermelha em catorze quadros vira papel de parede mesmo quando
    só alguns estão marcados."""
    folha_css = CSS.read_text(encoding="utf-8")
    bloco = folha_css[folha_css.find('.f2-corte[data-conferir="1"] .f2-corte-tela::after'):]
    bloco = bloco[:bloco.find("}")]
    assert "height: 2px" in bloco and "bottom: 0" in bloco
    assert "border" not in bloco


# ── a legenda do pé ─────────────────────────────────────────────────────────


def test_a_legenda_e_uma_so_e_nao_uma_por_quadro():
    codigo = JS.read_text(encoding="utf-8")
    assert codigo.count('legenda.className = "f2-legenda"') == 1
    assert "mouseenter" in codigo and "mouseleave" in codigo, (
        "a legenda parou de seguir o mouse; sem isso ela é só um rodapé"
    )


def test_em_repouso_a_legenda_conta_a_rodada():
    """Sem mouse em cima, a linha do pé não pode ficar vazia: é o lugar onde
    ele lê de longe quantos saíram e quantos pedem o olho dele."""
    codigo = JS.read_text(encoding="utf-8")
    trecho = codigo[codigo.find("function emRepouso()"):]
    trecho = trecho[:trecho.find("\n        }")]
    assert "resumo.entregues" in trecho
    assert "resumo.conferir" in trecho
    assert "descartados_por_sobreposicao" in trecho


def test_o_motivo_chega_escrito_em_portugues(montado):
    """`review_reasons` vem em português da própria máquina. A parede repassa
    a frase inteira — não um código para ele decifrar depois."""
    furia2, pasta = montado
    gravar(pasta, folha([corte(1, 10, 40, conferir=True)]))
    c = furia2.app.test_client().get("/api/cortes/lista").get_json()["cortes"][0]
    assert c["conferir"] is True
    assert c["motivos"] and "confira quem fala" in c["motivos"][0]


# ── as duas vozes ───────────────────────────────────────────────────────────


def test_a_fala_e_serifada_e_a_maquina_e_monoespacada():
    """Mono é a máquina falando: rótulo, número, tempo, estado. Serifada é a
    PESSOA falando. É a lei da cor aplicada à letra."""
    folha_css = CSS.read_text(encoding="utf-8")
    for da_pessoa in (".f2-legenda-fala", ".f2-corte-fala"):
        bloco = folha_css[folha_css.find(da_pessoa + " {"):]
        bloco = bloco[:bloco.find("}")]
        assert "var(--f2-fala)" in bloco, f"{da_pessoa} deixou de ser a voz da pessoa"

    marca = folha_css[folha_css.find(".f2-legenda-marca {"):]
    marca = marca[:marca.find("}")]
    assert "tabular-nums" in marca, "os tempos voltaram a dançar quando o número vira"


def test_a_fala_some_por_desvanecimento_e_nao_por_corte():
    """A primeira versão contava linhas e a última ficava serrada, metade
    dentro e metade fora — porque o número de linhas que cabe muda com a
    largura da janela, e largura de janela não é um número fixo."""
    folha_css = sem_comentario(CSS.read_text(encoding="utf-8"))
    bloco = folha_css[folha_css.find(".f2-corte-fala {"):]
    bloco = bloco[:bloco.find("}")]
    assert "mask-image" in bloco
    assert "line-clamp" not in bloco


def test_o_numero_do_corte_atravessa_quadro_claro_e_escuro():
    """Ele fica POR CIMA da imagem. Sem a mistura por diferença, some no
    branco de um telão ou no preto de um corte de estúdio."""
    folha_css = CSS.read_text(encoding="utf-8")
    bloco = folha_css[folha_css.find(".f2-corte-n {"):]
    bloco = bloco[:bloco.find("}")]
    assert "mix-blend-mode: difference" in bloco


def test_a_parede_nao_se_mexe_sozinha():
    """No Cipher a composição é desalinhada e se reorganiza o tempo todo.
    É lindo num portfólio e sabotagem num programa de trabalho: ele precisa
    reencontrar o corte que viu dez segundos atrás."""
    folha_css = CSS.read_text(encoding="utf-8")
    bloco = folha_css[folha_css.find(".f2-mural-cortes {"):]
    bloco = bloco[:bloco.find("}")]
    assert "grid-template-columns: repeat(auto-fill" in bloco
    assert "animation" not in bloco
