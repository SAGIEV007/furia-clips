"""A tela 5 do Furia 2: o mapa da fonte.

A parede responde "quais cortes saíram". Este mapa existe para a outra
pergunta, a que nunca teve resposta: POR QUE aquele pedaço de quatro minutos
não deu corte nenhum.

A resposta mora nos recusados. Eles sempre estiveram na folha de decisões e
até agora só existiam como um número no fim do relatório — "32 recusados" —,
que não ajuda ninguém. Aqui cada um vira uma marca no tempo, com o motivo
escrito em português e contra QUEM ele perdeu.

Medido na rodada de verdade do debate da Band: 29:32 de fonte, 18:09 viraram
corte (61%), 4 vãos sem corte nenhum, e 8 dos 32 recusados morreram dentro
desses vãos.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CSS = RAIZ / "furia2" / "static" / "css" / "furia2.css"
JS = RAIZ / "furia2" / "static" / "js" / "bancada.js"


def carregar_furia2():
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    spec = importlib.util.spec_from_file_location("furia2_app_mapa", RAIZ / "furia2" / "app.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def corte(inicio, fim):
    return {"start_s": inicio, "end_s": fim, "duration_s": fim - inicio, "texto": "uma fala"}


def recusado(inicio, fim, motivo="duplicate_overlap", vencedor=None, distancia=None):
    return {
        "start": inicio, "end": fim,
        "reason": motivo,
        "text_preview": "um trecho recusado",
        "winner": {"start": vencedor} if vencedor is not None else None,
        "details": {"score_gap": distancia} if distancia is not None else None,
    }


@pytest.fixture()
def montado(tmp_path, monkeypatch):
    furia2 = carregar_furia2()
    diag = tmp_path / "diagnostics"
    diag.mkdir()
    (tmp_path / "workspace").mkdir()
    monkeypatch.setattr(furia2, "DIAGNOSTICOS", diag)
    monkeypatch.setattr(furia2, "WORKSPACE_DIR", str(tmp_path / "workspace"))
    monkeypatch.setattr(furia2, "AJUSTES", tmp_path / "ajustes.json")
    return furia2, diag


def gravar(diag, cortes, recusados=(), adiados=(), duracao=1200.0):
    folha = {
        "job_id": "abc",
        "fonte": {"arquivo": "debate.mp4", "duracao_s": duracao},
        "selecao": {"origem": "gemini", "diagnostico": {"hard_negatives": list(recusados)}},
        "cortes_renderizados": list(cortes),
        "candidatos_adiados": list(adiados),
    }
    (diag / "selecao-teste-20260825T084232.json").write_text(
        json.dumps(folha, ensure_ascii=False), encoding="utf-8")


def mapa(furia2):
    return furia2.app.test_client().get("/api/mapa").get_json()


# ── os vãos ─────────────────────────────────────────────────────────────────


def test_o_vao_e_o_pedaco_da_fonte_que_nao_virou_nada(montado):
    furia2, diag = montado
    gravar(diag, [corte(100, 200), corte(800, 900)], duracao=1200)
    vazios = mapa(furia2)["vazios"]
    assert [(v["inicio"], v["fim"]) for v in vazios] == [(0.0, 100.0), (200.0, 800.0), (900.0, 1200.0)]


def test_respirar_entre_dois_cortes_nao_e_vao(montado):
    """Abaixo de um minuto, o intervalo entre dois cortes é respiração normal
    da entrevista. Marcar cada um deles encheria o mapa de buracos falsos."""
    furia2, diag = montado
    gravar(diag, [corte(0, 300), corte(330, 1200)], duracao=1200)
    assert mapa(furia2)["vazios"] == []


def test_cortes_que_se_sobrepoem_nao_inventam_vao(montado):
    """Dois cortes que se encavalam cobrem um pedaço só. Contar cada um por si
    faria aparecer um buraco onde não existe buraco nenhum."""
    furia2, diag = montado
    gravar(diag, [corte(0, 700), corte(300, 1200)], duracao=1200)
    assert mapa(furia2)["vazios"] == []
    assert mapa(furia2)["aproveitado"] == 1200.0


def test_o_aproveitado_nao_conta_o_mesmo_segundo_duas_vezes(montado):
    """Sem unir, dois cortes encavalados dariam "110% da fonte aproveitada" —
    número impossível que faz desconfiar do programa inteiro."""
    furia2, diag = montado
    gravar(diag, [corte(0, 700), corte(300, 1000)], duracao=1200)
    assert mapa(furia2)["aproveitado"] == 1000.0


def test_o_vao_conta_o_que_morreu_dentro_dele(montado):
    """A diferença entre "aqui não tinha nada" e "aqui tinha três coisas e
    todas caíram" é a resposta inteira desta tela."""
    furia2, diag = montado
    gravar(diag, [corte(0, 100), corte(900, 1200)],
           recusados=[recusado(300, 340), recusado(400, 450)], duracao=1200)
    vao = mapa(furia2)["vazios"][0]
    assert vao["recusados"] == 2
    assert vao["adiados"] == 0


def test_o_vao_sem_nada_dentro_diz_isso(montado):
    furia2, diag = montado
    gravar(diag, [corte(0, 100), corte(900, 1200)], duracao=1200)
    assert mapa(furia2)["vazios"][0]["recusados"] == 0
    assert "a máquina não propôs nada neste trecho" in JS.read_text(encoding="utf-8")


# ── os recusados ────────────────────────────────────────────────────────────


def test_o_motivo_chega_em_portugues(montado):
    """As etiquetas da máquina são em inglês. Ele não lê inglês e não tem por
    que ler: quem escreve a etiqueta é o programa."""
    furia2, diag = montado
    gravar(diag, [corte(0, 100)], recusados=[
        recusado(300, 340, "duplicate_overlap"),
        recusado(400, 450, "touching_sibling_lost_to_better_candidate"),
        recusado(500, 550, "already_exported_fingerprint"),
    ])
    motivos = [r["motivo"] for r in mapa(furia2)["recusados"]]
    assert motivos == [
        "repetia material de um corte já escolhido",
        "encostava em outro trecho e perdeu",
        "já tinha sido exportado numa rodada anterior",
    ]


def test_um_motivo_desconhecido_nao_vira_etiqueta_crua(montado):
    """Se o motor ganhar um motivo novo amanhã, o mapa não pode mostrar
    `motivo_novo_qualquer` na tela de um editor de vídeo."""
    furia2, diag = montado
    gravar(diag, [corte(0, 100)], recusados=[recusado(300, 340, "motivo_novo_qualquer")])
    assert mapa(furia2)["recusados"][0]["motivo"] == "motivo novo qualquer"


def test_o_recusado_diz_contra_qual_CORTE_perdeu(montado):
    """A folha guarda o vencedor pelo segundo em que ele começa — número que
    não quer dizer nada para ele. Saber que perdeu para o CORTE 02 resolve,
    porque aí ele abre o corte 02 e julga."""
    furia2, diag = montado
    gravar(diag, [corte(0, 100), corte(500, 600)],
           recusados=[recusado(300, 340, vencedor=500.0, distancia=23.0)])
    r = mapa(furia2)["recusados"][0]
    assert r["perdeu_para"] == 2
    assert r["por_quanto"] == 23.0


def test_perder_para_um_trecho_que_tambem_nao_saiu_e_dito_como_tal(montado):
    """Apontar para um corte que não existe seria pior do que não apontar."""
    furia2, diag = montado
    gravar(diag, [corte(0, 100)], recusados=[recusado(300, 340, vencedor=777.0)])
    assert mapa(furia2)["recusados"][0]["perdeu_para"] is None


def test_o_vencedor_e_casado_com_a_borda_que_a_maquina_propos(montado):
    """A disputa aconteceu ANTES de qualquer ajuste. Casar com a borda de agora
    faria a resposta mudar sozinha quando ele arrastasse uma alça no talho."""
    furia2, diag = montado
    gravar(diag, [corte(0, 100), corte(500, 600)],
           recusados=[recusado(300, 340, vencedor=500.0, distancia=9.0)])
    cliente = furia2.app.test_client()
    cliente.post("/api/talho/guardar", json={"n": 2, "inicio": 540.0, "fim": 600.0})
    assert mapa(furia2)["recusados"][0]["perdeu_para"] == 2


def test_so_acende_o_recusado_que_explica_um_buraco(montado):
    """Um recusado no meio de um trecho que já deu corte é rotina. Um recusado
    dentro de um buraco de três minutos é a explicação do buraco — e é para
    isso que este mapa existe."""
    furia2, diag = montado
    gravar(diag, [corte(0, 400), corte(900, 1200)],
           recusados=[recusado(100, 150), recusado(600, 650)], duracao=1200)
    r = mapa(furia2)["recusados"]
    assert r[0]["num_vao"] is False, "recusado dentro de um corte entregue não é evidência"
    assert r[1]["num_vao"] is True, "recusado dentro do buraco é a evidência"

    folha_css = CSS.read_text(encoding="utf-8")
    assert '.f2-recusado[data-vao="0"]' in folha_css
    assert '.f2-recusado[data-vao="1"]' in folha_css


def test_o_recusado_sem_tempo_valido_e_ignorado(montado):
    """Faixa de duração zero ou invertida existe em folha velha, e desenhar uma
    marca de largura negativa quebra a régua inteira."""
    furia2, diag = montado
    gravar(diag, [corte(0, 100)], recusados=[recusado(300, 300), recusado(500, 400)])
    assert mapa(furia2)["recusados"] == []


def test_numero_guardado_como_texto_nao_derruba_a_faixa(montado):
    """A folha guarda número às vezes como texto. Melhor tolerar do que deixar
    uma faixa inteira sumir do mapa por causa de uma aspa."""
    furia2, diag = montado
    gravar(diag, [corte(0, 100)], recusados=[recusado("300.5", "340.25")])
    r = mapa(furia2)["recusados"][0]
    assert r["inicio"] == 300.5 and r["fim"] == 340.25


# ── o adiado não é o recusado ───────────────────────────────────────────────


def test_o_adiado_e_uma_coisa_diferente_do_recusado(montado):
    """O adiado passou, mas pede o olho dele. Misturar os dois numa marca só
    apagaria a diferença entre "não vai sair" e "só falta você olhar"."""
    furia2, diag = montado
    gravar(diag, [corte(0, 100)], adiados=[{
        "start_s": 300, "end_s": 400,
        "motivo_adiamento": "contexto autossuficiente não confirmado",
        "texto": "um trecho adiado",
    }])
    d = mapa(furia2)
    assert d["recusados"] == []
    assert d["adiados"][0]["motivo"] == "contexto autossuficiente não confirmado"
    assert '.f2-recusado[data-tipo="adiado"]' in CSS.read_text(encoding="utf-8")


# ── a onda do mapa ──────────────────────────────────────────────────────────


def test_a_onda_da_fonte_inteira_e_lida_em_pedacos():
    """Ler meia hora de áudio de uma vez custa cento e treze megabytes; uma
    entrevista de duas horas, quase meio giga. E o mapa é uma janela que ele
    abre e fecha o dia todo."""
    origem = (RAIZ / "furia2" / "app.py").read_text(encoding="utf-8")
    trecho = origem[origem.find("def api_mapa_onda"):origem.find("def api_mapa(")]
    assert "PEDACO" in trecho
    assert "while inicio < duracao" in trecho


def test_a_onda_do_mapa_e_guardada_em_disco():
    """Oito segundos na primeira vez, doze milésimos depois. Sem guardar, cada
    abertura da janela custaria os oito segundos de novo."""
    origem = (RAIZ / "furia2" / "app.py").read_text(encoding="utf-8")
    trecho = origem[origem.find("def api_mapa_onda"):origem.find("def api_mapa(")]
    assert "guardado.exists()" in trecho
    assert "guardado.write_text" in trecho


def test_uma_onda_guardada_estragada_e_refeita_e_nao_quebra_a_tela():
    origem = (RAIZ / "furia2" / "app.py").read_text(encoding="utf-8")
    trecho = origem[origem.find("def api_mapa_onda"):origem.find("def api_mapa(")]
    assert "except (OSError, ValueError)" in trecho


def test_o_desenho_nao_refaz_a_conta_de_dentro_por_fatia():
    """Onze cortes contra novecentas fatias são nove mil comparações a cada
    redesenho — e a janela redesenha a cada arrasto."""
    codigo = JS.read_text(encoding="utf-8")
    trecho = codigo[codigo.find("function montarOMapa"):]
    assert "Uint8Array" in trecho


def test_a_regua_muda_o_passo_com_a_duracao():
    """Numa entrevista de meia hora, marcar de minuto em minuto dá trinta
    números grudados e ilegíveis."""
    codigo = JS.read_text(encoding="utf-8")
    assert "dur > 1500 ? 300 : dur > 600 ? 120 : 60" in codigo


def test_clicar_no_mapa_leva_ao_talho():
    """É o caminho curto: ele vê o buraco, entende que o corte vizinho comeu o
    trecho, e abre o vizinho para mexer na borda sem passar pela parede."""
    codigo = JS.read_text(encoding="utf-8")
    trecho = codigo[codigo.find("function montarOMapa"):]
    assert "MONTADO.talho()" in trecho


def test_o_mapa_usa_a_mesma_legenda_da_parede():
    """Duas telas com o mesmo gesto e o mesmo lugar de resposta. Inventar um
    segundo jeito de mostrar detalhe seria pedir para ele aprender duas vezes."""
    codigo = JS.read_text(encoding="utf-8")
    trecho = codigo[codigo.find("function montarOMapa"):]
    assert 'class="f2-legenda"' in trecho
    assert ".f2-mapa .f2-legenda" in CSS.read_text(encoding="utf-8")
