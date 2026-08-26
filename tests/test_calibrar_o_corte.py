"""Arrastar a alça e salvar precisa mudar o corte — e não mudava.

O editor descreveu o defeito inteiro em uma frase: "tentei usar a ferramenta
para editar o inicio e fim do corte, ela visualmente funciona bem, e até ao
arrastar a barrinha detectou a legenda e tudo, porem quando eu confirmei que era
para calibrar o corte, o video se manteve o mesmo, não gerou logs e ainda por
cima quando clico para editar novamente, REAPARECE O SISTEMA DE BOTÕES E NUMEROS
ANTIGOS".

São dois defeitos, e nenhum dos dois aparece lendo o código com atenção — os dois
só aparecem no navegador, arrastando de verdade.

**Um.** As alças escrevem nos campos escondidos. `previewClipBoundary` lia
deles; `persistClipBoundary` não. Salvar montava o ajuste a partir de
`clip.latest_adjustment`, e quem arrastasse e salvasse direto — sem passar pelo
"Pré-visualizar" — caía no `||` e gravava `clip.start` e `clip.end`, os valores
ORIGINAIS. O servidor respondia 200, o histórico registrava o corte igual ao que
já era, e nada na tela dizia que a decisão tinha sido descartada. "O video se
manteve o mesmo, não gerou logs" é literalmente o que o código fazia.

**Dois.** Salvar chama `renderResultsGrid`, que reconstrói o cartão inteiro a
partir de HTML: campos de número novos, rótulos visíveis, e o talho anterior
fora do documento. O mapa de talhos continuava guardando aquele nó morto, então
reabrir o editor batia no atalho "já montado" e voltava cedo — deixando à vista
exatamente o par de campos em segundos absolutos que o talho existia para
substituir.

Este teste faz o percurso do editor: abre o ajuste, arrasta a alça de entrada,
salva, e confere as três coisas que ele não conseguia ver — o corpo que foi ao
servidor, a linha de registro, e o que aparece ao reabrir.

Um detalhe do próprio teste, que custou uma rodada: a primeira versão arrastava
para uma coordenada fora da janela e o `pointerdown` nunca chegou na alça. Sem
`scroll_into_view_if_needed` o teste acusa de defeito no código o que é defeito
na mira. Por isso as duas medições de posição estão explícitas abaixo.
"""

import glob
import json
import logging
import os
import threading
import time

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _chromium() -> str:
    """O caminho real do Chromium instalado, não o que o playwright supõe.

    `p.chromium.executable_path` aponta para a revisão que a versão do pacote
    espera; a imagem traz outra. Quem existe no disco é a única que importa.
    """
    for padrao in ("chromium-*/chrome-linux*/chrome", "chromium-*/chrome-linux*/headless_shell"):
        achados = sorted(glob.glob(os.path.join("/opt/pw-browsers", padrao)))
        if achados:
            return achados[-1]
    return ""


playwright_api = pytest.importorskip("playwright.sync_api", reason="playwright ausente")
pytestmark = pytest.mark.skipif(not _chromium(), reason="Chromium ausente neste ambiente")

PORTA = 5223
CORTE = {
    "clip_id": "corte-de-prova",
    "start": 300.0,
    "end": 345.0,
    "duration": 45.0,
    "viral_score": 71,
    "rank": 1,
    "text": "Trecho de prova para a calibragem.",
    "source": "nlp",
    "source_duration": 3600.0,
}

# A repórter pergunta até 303 e a resposta começa aí: é a borda que o editor
# quer alcançar arrastando, e o mesmo caso que ele descreveu nos cortes reais.
FALAS = [
    {"start": 298, "end": 303, "text": "O senhor aceita esse debate?"},
    {"start": 303, "end": 340, "text": "Aceito, e vou dizer por que."},
    {"start": 340, "end": 350, "text": "Segundo ponto:"},
]


@pytest.fixture(scope="module")
def servidor():
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    import app as aplicacao

    alvo = lambda: aplicacao.app.run(port=PORTA, threaded=True, use_reloader=False)  # noqa: E731
    threading.Thread(target=alvo, daemon=True).start()
    time.sleep(2.5)
    # A porta da frente agora é o estúdio; a interface que estes testes
    # medem mora em /classico e continua inteira lá.
    return f"http://127.0.0.1:{PORTA}/classico"


@pytest.fixture(scope="module")
def percurso(servidor):
    """Roda o percurso inteiro uma vez e devolve o que foi observado."""
    enviados: list[dict] = []
    erros: list[str] = []
    visto: dict = {}

    with playwright_api.sync_playwright() as p:
        navegador = p.chromium.launch(executable_path=_chromium())
        pagina = navegador.new_page(viewport={"width": 1600, "height": 1000})
        pagina.on("pageerror", lambda e: erros.append(str(e)))

        def gravar_ajuste(rota):
            corpo = rota.request.post_data_json
            enviados.append(corpo)
            rota.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {"adjustment": corpo["adjustment"], "review_status": "needs_review"}
                ),
            )

        pagina.route("**/api/clips/*/adjust", gravar_ajuste)
        # A onda vem do servidor a partir de um arquivo de vídeo que este teste
        # não tem; o desenho não é o que está sendo verificado aqui.
        pagina.route(
            "**/api/waveform*",
            lambda r: r.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"picos": [0.2, 0.9, 0.4, 0.7] * 60, "de": 295.0, "ate": 350.0}),
            ),
        )

        pagina.goto(servidor, wait_until="load")
        time.sleep(1)
        pagina.evaluate(
            """([corte, falas]) => {
                state.clips = [corte];
                state.manualTranscript = { segments: falas };
                document.querySelector('.rail-tab[data-ambiente="auditoria"]')?.click();
                renderResultsGrid();
            }""",
            [CORTE, FALAS],
        )
        time.sleep(0.5)

        pagina.click(".btn-boundary-toggle")
        time.sleep(1)
        visto["talho_ao_abrir"] = pagina.evaluate(
            "!!document.querySelector('#boundary-editor-0 .talho canvas')"
        )
        visto["tipo_do_campo"] = pagina.evaluate(
            'document.querySelector(\'[data-boundary-start="0"]\').type'
        )

        # Mirar antes de arrastar: fora da janela o pointerdown não chega.
        pagina.locator("#boundary-editor-0 .talho-tela").scroll_into_view_if_needed()
        time.sleep(0.4)
        tela = pagina.locator("#boundary-editor-0 .talho-tela").bounding_box()
        alca = pagina.locator('#boundary-editor-0 [data-alca="inicio"]').bounding_box()
        assert 0 <= alca["y"] < 1000, "a alça ficou fora da janela; o teste erraria a mira"

        visto["entrada_antes"] = pagina.evaluate(
            'document.querySelector(\'[data-boundary-start="0"]\').value'
        )
        meio = alca["y"] + alca["height"] / 2
        pagina.mouse.move(alca["x"] + alca["width"] / 2, meio)
        pagina.mouse.down()
        pagina.mouse.move(tela["x"] + tela["width"] * 0.25, meio, steps=12)
        pagina.mouse.up()
        time.sleep(0.4)
        visto["entrada_depois"] = pagina.evaluate(
            'document.querySelector(\'[data-boundary-start="0"]\').value'
        )

        pagina.click("#boundary-editor-0 .btn-success")
        time.sleep(1.5)
        visto["registro"] = pagina.evaluate(
            "[...document.querySelectorAll('.console-line')].map(n => n.textContent)"
            ".filter(t => t.includes('[Ajuste]'))"
        )

        # Reabrir depois do re-render: é aqui que os campos antigos voltavam.
        if pagina.evaluate("!document.getElementById('boundary-editor-0').hidden"):
            pagina.click(".btn-boundary-toggle")
            time.sleep(0.3)
        pagina.click(".btn-boundary-toggle")
        time.sleep(1)
        visto["talho_ao_reabrir"] = pagina.evaluate(
            "!!document.querySelector('#boundary-editor-0 .talho canvas')"
        )
        visto["rotulo_antigo_visivel"] = pagina.evaluate(
            '!document.querySelector(\'[data-boundary-start="0"]\')'
            '.closest(\'label\').hasAttribute(\'hidden\')'
        )
        navegador.close()

    visto["enviados"] = enviados
    visto["erros"] = erros
    return visto


def test_a_tela_nao_quebra(percurso):
    assert percurso["erros"] == [], f"erro de JavaScript no percurso: {percurso['erros']}"


def test_o_talho_substitui_os_campos_em_segundos(percurso):
    assert percurso["talho_ao_abrir"], "abriu o ajuste e não veio onda nenhuma"
    assert percurso["tipo_do_campo"] == "hidden", (
        "os campos em segundos absolutos continuam sendo o controle"
    )


def test_arrastar_move_a_entrada(percurso):
    antes = float(percurso["entrada_antes"])
    depois = float(percurso["entrada_depois"])
    assert antes == pytest.approx(300.0, abs=0.05)
    assert depois > antes + 1, f"a alça não moveu nada: {antes} → {depois}"


def test_salvar_grava_o_que_foi_arrastado(percurso):
    """O defeito exato: salvar mandava o corte original de volta."""
    assert len(percurso["enviados"]) == 1, "salvar não chegou ao servidor"
    ajuste = percurso["enviados"][0]["adjustment"]
    arrastado = float(percurso["entrada_depois"])
    assert ajuste["start"] == pytest.approx(arrastado, abs=0.05), (
        f"salvou {ajuste['start']} com a alça em {arrastado} — "
        "voltou a mandar o corte original"
    )
    assert ajuste["start"] > CORTE["start"] + 1
    assert ajuste["duration"] == pytest.approx(ajuste["end"] - ajuste["start"], abs=0.05)


def test_salvar_deixa_rastro_no_registro(percurso):
    """"não gerou logs": uma decisão que some sem registro não é auditável."""
    linhas = percurso["registro"]
    assert linhas, "salvar não escreveu nada no registro"
    assert "300.0s" in linhas[0] and "Corte 1" in linhas[0], linhas[0]


def test_reabrir_devolve_a_onda_e_nao_os_numeros(percurso):
    """"REAPARECE O SISTEMA DE BOTÕES E NUMEROS ANTIGOS"."""
    assert percurso["talho_ao_reabrir"], (
        "reabriu e o talho não voltou — o mapa guardou um nó fora do documento"
    )
    assert not percurso["rotulo_antigo_visivel"], (
        "os campos de número em segundos absolutos voltaram à tela"
    )
