"""O X da prévia não fechava nada, e ninguém tinha como perceber.

O editor: "ao clicar na prévia do video para fechar não fecha, ainda esta
totalmente amador".

O botão existia, tinha ícone de fechar, tinha `title="Recolher preview"` e um
`addEventListener` registrado. E não fazia nada — escondia
`videoPreviewSection`, um elemento que deixou de existir quando a prévia virou
o dock lateral. `getElementById` devolvia `null`, a guarda `if (previewSection)`
engolia o caso, e o clique terminava em silêncio. Sem erro no console, sem
aviso, sem sintoma nenhum além do vídeo continuar lá.

É a mesma família de defeito do "salvar ajuste" e do "player sumiu": um caminho
que falha calado porque a guarda que devia proteger de um erro acabou
protegendo do conserto. Nenhuma leitura de código pega isso — só clicar.

Fechar tem de desfazer as três coisas que abrir faz, e a terceira é a que
importa mais: prévia fechada que continua tocando som atrás da tela é pior do
que prévia aberta.
"""

import glob
import logging
import os
import threading
import time

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _chromium() -> str:
    for padrao in ("chromium-*/chrome-linux*/chrome", "chromium-*/chrome-linux*/headless_shell"):
        achados = sorted(glob.glob(os.path.join("/opt/pw-browsers", padrao)))
        if achados:
            return achados[-1]
    return ""


playwright_api = pytest.importorskip("playwright.sync_api", reason="playwright ausente")
pytestmark = pytest.mark.skipif(not _chromium(), reason="Chromium ausente neste ambiente")

PORTA = 5237

ABRIR = """() => {
    const dock = document.getElementById('playerDock');
    dock.classList.add('is-open');
    document.querySelector('.main-content').classList.add('dock-open');
    const v = document.getElementById('videoPreview');
    v.__tocando = true;
    v.pause = function () { this.__tocando = false; };
    return true;
}"""

ESTADO = """() => ({
    aberto: document.getElementById('playerDock').classList.contains('is-open'),
    palcoEncolhido: document.querySelector('.main-content').classList.contains('dock-open'),
    tocando: document.getElementById('videoPreview').__tocando === true,
})"""


@pytest.fixture(scope="module")
def pagina():
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    import app as aplicacao

    alvo = lambda: aplicacao.app.run(port=PORTA, threaded=True, use_reloader=False)  # noqa: E731
    threading.Thread(target=alvo, daemon=True).start()
    time.sleep(2.5)

    with playwright_api.sync_playwright() as p:
        navegador = p.chromium.launch(executable_path=_chromium())
        aba = navegador.new_page(viewport={"width": 1366, "height": 768})
        erros = []
        aba.on("pageerror", lambda e: erros.append(str(e)))
        aba.goto(f"http://127.0.0.1:{PORTA}/", wait_until="load")
        time.sleep(1.2)
        aba.erros = erros
        yield aba
        navegador.close()


def test_o_botao_fecha(pagina):
    pagina.evaluate(ABRIR)
    assert pagina.evaluate(ESTADO)["aberto"], "a montagem do teste não abriu a prévia"

    pagina.click("#btnClosePreview")
    time.sleep(0.4)
    depois = pagina.evaluate(ESTADO)
    assert not depois["aberto"], "clicou no X e a prévia continuou aberta"


def test_fechar_devolve_a_largura_ao_palco(pagina):
    """Abrir a prévia empurra o palco; fechar sem devolver deixa a tela torta."""
    pagina.evaluate(ABRIR)
    pagina.click("#btnClosePreview")
    time.sleep(0.4)
    assert not pagina.evaluate(ESTADO)["palcoEncolhido"], (
        "o conteúdo continuou espremido depois de fechar a prévia"
    )


def test_fechar_para_o_video(pagina):
    """Som tocando atrás de uma janela fechada é pior que a janela aberta."""
    pagina.evaluate(ABRIR)
    assert pagina.evaluate(ESTADO)["tocando"]
    pagina.click("#btnClosePreview")
    time.sleep(0.4)
    assert not pagina.evaluate(ESTADO)["tocando"], (
        "a prévia sumiu da tela mas o vídeo continuou tocando"
    )


def test_esc_tambem_fecha(pagina):
    pagina.evaluate(ABRIR)
    pagina.keyboard.press("Escape")
    time.sleep(0.4)
    assert not pagina.evaluate(ESTADO)["aberto"], "Esc não fechou a prévia"


def test_esc_nao_fecha_enquanto_ele_digita(pagina):
    """Esc dentro de um campo é 'cancela o que eu estava escrevendo'."""
    # Um campo escondido não aceita foco, e o foco fica no botão do teste
    # anterior — aí o teste passaria sem medir guarda nenhuma. O ambiente
    # Cortar tem o campo de refinamento visível.
    pagina.evaluate("document.querySelector('.rail-tab[data-ambiente=\"cortar\"]').click()")
    time.sleep(0.4)
    pagina.evaluate(ABRIR)
    focou = pagina.evaluate(
        """() => {
            const campo = document.querySelector('.ambiente.is-active textarea');
            if (!campo) return "";
            campo.focus();
            return document.activeElement?.tagName || "";
        }"""
    )
    assert focou in ("TEXTAREA", "INPUT"), (
        f"o teste não conseguiu pôr o foco num campo ({focou!r}); sem foco ele "
        "não estaria medindo a guarda, e passaria por acidente"
    )
    pagina.keyboard.press("Escape")
    time.sleep(0.3)
    assert pagina.evaluate(ESTADO)["aberto"], (
        "Esc num campo de texto fechou a prévia junto"
    )
    pagina.click("#btnClosePreview")


def test_a_tela_nao_quebra(pagina):
    assert pagina.erros == [], f"erro de JavaScript: {pagina.erros}"
