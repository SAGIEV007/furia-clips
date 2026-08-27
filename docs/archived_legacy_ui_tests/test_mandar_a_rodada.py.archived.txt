"""O relatório existia; o caminho até ele, não.

O editor: "onde eu acho essas informações para te passar? no console mesmo?".

O diagnóstico da rodada sempre foi gravado, e o console sempre imprimiu o
caminho. Só que o caminho é `C:\\Users\\<ele>\\FuriaClipsData\\diagnostics` — um
lugar que só se alcança navegando no explorador de arquivos, que é exatamente o
tipo de coisa que ele não deveria precisar fazer. É a mesma forma do defeito do
registro técnico, que ele reportou três vezes antes de eu agir: mostrar não é o
mesmo que dar o caminho.

Dois caminhos agora, para dois usos diferentes:

* Abrir a pasta, quando o assunto for a seleção inteira e valer a pena arrastar
  o arquivo completo para a conversa.

* Copiar um RESUMO, que resolve a pergunta que eu faço com mais frequência: qual
  corte abriu ou fechou errado. Para isso não preciso de meio megabyte de JSON —
  preciso da primeira e da última frase de cada corte. Aquilo cabe numa mensagem,
  e ele marca os ruins direto no texto colado.

Medido com a rodada real da PENÉLOPE: 3,7 KB, 60 linhas, 11 cortes.
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
    for padrao in ("chromium-*/chrome-linux*/chrome", "chromium-*/chrome-linux*/headless_shell"):
        achados = sorted(glob.glob(os.path.join("/opt/pw-browsers", padrao)))
        if achados:
            return achados[-1]
    return ""


def test_a_rota_diz_onde_fica_mesmo_sem_conseguir_abrir():
    """Sem ambiente gráfico o comando falha — e dizer ONDE ainda resolve."""
    import app as aplicacao

    resposta = aplicacao.app.test_client().post("/api/open-diagnostics")
    corpo = resposta.get_json()
    assert "pasta" in corpo
    assert corpo["pasta"].endswith("diagnostics")
    assert os.path.isdir(corpo["pasta"]), "a pasta precisa existir para ser aberta"
    # Quantos relatórios há e qual é o mais novo: é o que ele precisa saber para
    # escolher o arquivo certo depois que a pasta abre.
    assert "arquivos" in corpo and "mais_recente" in corpo


def test_a_pasta_do_diagnostico_e_a_mesma_onde_o_relatorio_e_gravado():
    """Abrir a pasta errada seria pior que não ter botão."""
    codigo = open(os.path.join(RAIZ, "app.py"), encoding="utf-8").read()
    escrita = codigo[codigo.index("def _write_selection_diagnostics("):]
    escrita = escrita[:escrita.index("def _anunciar_descartes")]
    abertura = codigo[codigo.index("def api_open_diagnostics("):]
    abertura = abertura[:abertura.index("@app.route(\"/api/open_folder\"")]
    for trecho in ('FURIA_CLIPS_DATA_DIR', '"FuriaClipsData"', '"diagnostics"'):
        assert trecho in escrita and trecho in abertura, (
            f"a escrita e a abertura divergem em {trecho}: o botão abriria outro lugar"
        )


def test_os_botoes_existem_e_fazem_alguma_coisa():
    html = open(os.path.join(RAIZ, "templates", "index.html"), encoding="utf-8").read()
    js = open(os.path.join(RAIZ, "static", "js", "atelie.js"), encoding="utf-8").read()
    for botao in ("btnAbrirPastaDiagnostico", "btnCopiarResumoDaRodada"):
        assert f'id="{botao}"' in html, f"{botao} sumiu da tela"
        assert botao in js, f"{botao} existe mas não faz nada"


@pytest.mark.skipif(not _chromium(), reason="Chromium ausente neste ambiente")
def test_o_resumo_traz_a_borda_de_cada_corte_e_cabe_numa_mensagem():
    """O que ele vai colar aqui, montado com os cortes reais da PENÉLOPE."""
    playwright_api = pytest.importorskip("playwright.sync_api")
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    import app as aplicacao

    porta = 5251
    alvo = lambda: aplicacao.app.run(port=porta, threaded=True, use_reloader=False)  # noqa: E731
    threading.Thread(target=alvo, daemon=True).start()
    time.sleep(2.5)

    cortes = [
        {"clip_id": "c0", "start": 472.0, "end": 591.4, "duration": 119.4, "rank": 1,
         "viral_score": 67, "source_duration": 1772.1,
         "text": "O político hoje quer expor as suas mentiras. "
                 "Sempre houve outras maneiras de conhecer as propostas."},
        {"clip_id": "c1", "start": 256.6, "end": 399.6, "duration": 143.0, "rank": 2,
         "viral_score": 63, "source_duration": 1772.1,
         "text": "Está certo? O Lula tem que estar nos debates. "
                 "Em um futuro próximo não haverá mais debates."},
    ]
    descartados = [
        {"inicio": 1194.0, "fim": 1361.0, "duracao": 167.0, "inedito_s": 111.0,
         "dentro_do_vencedor": False, "trecho": "Uma fala inteira que morreu na borda."},
        {"inicio": 480.0, "fim": 520.0, "duracao": 40.0, "inedito_s": 0.0,
         "dentro_do_vencedor": True, "trecho": "Um pedaço da mesma resposta."},
    ]

    with playwright_api.sync_playwright() as p:
        navegador = p.chromium.launch(executable_path=_chromium())
        contexto = navegador.new_context(
            viewport={"width": 1366, "height": 768},
            permissions=["clipboard-read", "clipboard-write"],
        )
        pagina = contexto.new_page()
        erros = []
        pagina.on("pageerror", lambda e: erros.append(str(e)))
        pagina.goto(f"http://127.0.0.1:{porta}/", wait_until="load")
        time.sleep(1.2)
        pagina.evaluate(
            """([cortes, descartados]) => {
                state.clips = cortes;
                state.selectedVideoName = "PENELOPE NOVA X SESTARO.mp4";
                state.diagnostics = { descartados_por_sobreposicao: descartados };
                document.getElementById('btnGaveta').click();
            }""",
            [cortes, descartados],
        )
        time.sleep(0.4)
        pagina.click("#btnCopiarResumoDaRodada")
        time.sleep(0.6)
        aviso = pagina.evaluate("document.getElementById('gavetaAviso').textContent")
        texto = pagina.evaluate("navigator.clipboard.readText()")
        navegador.close()

    assert erros == [], f"erro de JavaScript ao montar o resumo: {erros}"
    assert "copiado" in aviso, aviso

    # Cabe numa mensagem: é a razão de o resumo existir em vez do JSON inteiro.
    assert len(texto) < 20000, f"o resumo saiu com {len(texto)} caracteres"

    # A fonte, legível — não o textContent cru do elemento, que trazia junto o
    # ícone e a dica escondida ("cloud_upload Nenhum vídeo carregado Importe…").
    assert "fonte: PENELOPE NOVA X SESTARO.mp4" in texto, texto[:200]
    assert "cloud_upload" not in texto

    # A borda de cada corte, que é a única coisa que decide se ela ficou certa.
    assert "abre:  O político hoje quer expor" in texto
    assert "fecha: Sempre houve outras maneiras de conhecer as propostas." in texto
    assert "abre:  Está certo?" in texto

    # E o que a peneira derrubou COM material próprio; o engolido não entra,
    # porque aquilo não é perda e só faria o texto crescer.
    assert "Descartados que traziam material próprio (1)" in texto
    assert "111s inéditos" in texto
    assert "Um pedaço da mesma resposta" not in texto


@pytest.mark.skipif(not _chromium(), reason="Chromium ausente neste ambiente")
def test_sem_corte_nenhum_o_resumo_avisa_em_vez_de_copiar_vazio():
    playwright_api = pytest.importorskip("playwright.sync_api")
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    import app as aplicacao

    porta = 5252
    alvo = lambda: aplicacao.app.run(port=porta, threaded=True, use_reloader=False)  # noqa: E731
    threading.Thread(target=alvo, daemon=True).start()
    time.sleep(2.5)

    with playwright_api.sync_playwright() as p:
        navegador = p.chromium.launch(executable_path=_chromium())
        pagina = navegador.new_page(viewport={"width": 1366, "height": 768})
        pagina.goto(f"http://127.0.0.1:{porta}/", wait_until="load")
        time.sleep(1.2)
        pagina.evaluate("() => { state.clips = []; document.getElementById('btnGaveta').click(); }")
        time.sleep(0.3)
        pagina.click("#btnCopiarResumoDaRodada")
        time.sleep(0.4)
        aviso = pagina.evaluate("document.getElementById('gavetaAviso').textContent")
        navegador.close()

    assert "nenhum corte" in aviso.lower(), aviso
