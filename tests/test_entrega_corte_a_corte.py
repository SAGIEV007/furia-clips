"""Os cortes saem enquanto a fonte ainda está sendo cortada.

O pedido do editor, nas palavras dele:

    "se eu coloco um video para ir cortando e ele tem 2 horas e vai gerar 30
    cortes, que os cortes ja vai saindo para eu analisar antes do video todo ser
    concluido"

Cortar já era um por um — `batch_cut` renderiza em laço, valida e guarda. O que
faltava era CONTAR. A lista inteira só saía no `cut_complete`, no fim, então
numa fonte de duas horas ele esperava a trigésima renderização para ver a
primeira, que costuma estar pronta em menos de um minuto.

── o que quase saiu errado ──────────────────────────────────────────────────

Entregar cedo é fácil; entregar cedo um cartão ÚTIL não é. Dois cuidados, e os
dois estão testados abaixo porque os dois quebrariam calados:

1. O registro no banco tem de vir junto, não depois. Sem `clip_id` o cartão
   nasce sem poder ser ajustado nem aprovado — a ferramenta de entrada e saída
   responde "este resultado ainda não possui um registro persistente". Um cartão
   pela metade é pior que um cartão tarde.

2. O cartão entregue tem de ser o MESMO que a lista final traz. Montar em dois
   lugares garantiria que divergissem na primeira alteração, e o editor veria um
   cartão durante o processo e outro no fim, sem entender por quê. A montagem
   ficou numa função só.

E um terceiro, que é sobre não estragar o que já funciona: um aviso que falha
não pode derrubar o corte. O arquivo já está no disco — se ninguém estiver
ouvindo, a lista final tem de sair igual.
"""

import pytest

from modules.video_cutter import VideoCutter


class _ValidacaoOk:
    valid = True
    errors: list = []

    @staticmethod
    def as_dict():
        return {"valid": True}


@pytest.fixture
def cortador(monkeypatch, tmp_path):
    """Um cortador que não chama ffmpeg: aqui o assunto é a ENTREGA."""
    cortador = VideoCutter({})

    def cortar_falso(video_path, inicio, fim, saida, *args, **kwargs):
        destino = tmp_path / "saida.mp4"
        destino.write_bytes(b"fake")
        return str(saida)

    monkeypatch.setattr(cortador, "cut_clip", cortar_falso)
    monkeypatch.setattr(cortador, "cut_clip_with_face_tracking", cortar_falso)
    monkeypatch.setattr("modules.video_cutter.validate_media", lambda *a, **k: _ValidacaoOk())
    return cortador


TRECHOS = [
    {"start": 10.0, "end": 70.0, "duration": 60.0, "text": "Primeiro trecho.", "title": "um"},
    {"start": 100.0, "end": 170.0, "duration": 70.0, "text": "Segundo trecho.", "title": "dois"},
    {"start": 200.0, "end": 250.0, "duration": 50.0, "text": "Terceiro trecho.", "title": "tres"},
]


def _cortar(cortador, tmp_path, **extra):
    return cortador.batch_cut(
        "fonte.mp4", TRECHOS, "projeto",
        output_dir=str(tmp_path), original_aspect_indices={0, 1, 2},
        **extra,
    )


def test_cada_corte_avisa_assim_que_fica_pronto(cortador, tmp_path):
    avisos = []
    resultados = _cortar(
        cortador, tmp_path,
        on_clip_ready=lambda corte, i, total: avisos.append((i, total, corte["start"])),
    )
    assert len(resultados) == 3
    assert avisos == [(0, 3, 10.0), (1, 3, 100.0), (2, 3, 200.0)], (
        "os avisos não saíram um por um, na ordem em que os cortes ficaram prontos"
    )


def test_o_aviso_chega_antes_de_o_ultimo_corte_existir(cortador, tmp_path):
    """A promessa inteira em uma asserção: o primeiro não espera o último."""
    momentos = []
    original = cortador.cut_clip

    def registrando(*args, **kwargs):
        momentos.append("renderizou")
        return original(*args, **kwargs)

    cortador.cut_clip = registrando
    _cortar(
        cortador, tmp_path,
        on_clip_ready=lambda corte, i, total: momentos.append(f"entregou {i}"),
    )
    assert momentos.index("entregou 0") < momentos.index("entregou 2"), "ordem trocada"
    assert momentos.index("entregou 0") < len(momentos) - 1, (
        "a primeira entrega só aconteceu no fim de tudo"
    )
    # Entre a entrega do primeiro e a do último ainda houve renderização: prova
    # de que ele não esperou a fonte inteira terminar.
    entre = momentos[momentos.index("entregou 0") + 1:momentos.index("entregou 2")]
    assert "renderizou" in entre


def test_o_corte_entregue_e_o_mesmo_que_a_lista_final(cortador, tmp_path):
    """Dois cartões diferentes para o mesmo corte é pior que nenhum aviso."""
    entregues = []
    resultados = _cortar(
        cortador, tmp_path,
        on_clip_ready=lambda corte, i, total: entregues.append(corte),
    )
    for entregue, final in zip(entregues, resultados):
        assert entregue == final


def test_um_aviso_que_falha_nao_derruba_o_corte(cortador, tmp_path):
    """O arquivo já está no disco; ninguém ouvindo não pode custar o trabalho."""
    def explodir(corte, i, total):
        raise RuntimeError("a tela caiu")

    resultados = _cortar(cortador, tmp_path, on_clip_ready=explodir)
    assert len(resultados) == 3, "uma falha no aviso levou os cortes junto"


def test_sem_ouvinte_tudo_continua_igual(cortador, tmp_path):
    """Quem não passa `on_clip_ready` recebe exatamente o que recebia antes."""
    assert len(_cortar(cortador, tmp_path)) == 3


def test_a_tela_sabe_receber_um_corte_avulso():
    """O outro lado do fio: o app.js precisa tratar `clip_ready`."""
    import pathlib

    js = (pathlib.Path(__file__).resolve().parents[1] / "static" / "js" / "app.js").read_text(
        encoding="utf-8"
    )
    assert 'case "clip_ready"' in js, "o servidor avisa e ninguém escuta"
    trecho = js[js.index('case "clip_ready"'):js.index('case "cut_complete"')]
    assert "state.clips" in trecho
    assert "renderResultsGrid" in trecho, "o corte chega e a grade não redesenha"
    assert "clip_id" in trecho, (
        "sem conferir clip_id o mesmo corte pode entrar duas vezes na lista"
    )


def test_o_servidor_monta_o_corte_num_lugar_so():
    """A garantia estrutural por trás do teste de igualdade acima."""
    import pathlib

    codigo = (pathlib.Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert codigo.count("def montar_corte(") == 1, (
        "a montagem do cartão foi duplicada; os dois caminhos vão divergir"
    )
    assert "on_clip_ready=entregar_corte" in codigo
    # A persistência precisa acontecer ANTES da entrega, senão o cartão chega
    # sem clip_id e não dá para ajustar nem aprovar.
    entrega = codigo[codigo.index("def entregar_corte("):]
    entrega = entrega[:entrega.index("emit_status(\"clip_ready\"")]
    assert "persistir_corte(res, i)" in entrega


# ── e a prova de que o cartão aparece de verdade ───────────────────────────

import glob
import logging
import os
import threading
import time


def _chromium() -> str:
    for padrao in ("chromium-*/chrome-linux*/chrome", "chromium-*/chrome-linux*/headless_shell"):
        achados = sorted(glob.glob(os.path.join("/opt/pw-browsers", padrao)))
        if achados:
            return achados[-1]
    return ""


PORTA = 5243
FONTE_S = 1772.1


def _corte_para_a_tela(i, de, ate):
    return {
        "clip_id": f"cid-{i}", "start": de, "end": ate, "duration": ate - de,
        "viral_score": 70 + i, "rank": i + 1, "text": f"Trecho {i + 1} da fonte.",
        "source": "gemini", "source_duration": FONTE_S, "filename": f"corte_{i + 1}.mp4",
        "breakdown": {}, "factors": {}, "review_flags": {},
        "seo": {"titles": [], "tags": [], "hashtags": []},
    }


@pytest.mark.skipif(not _chromium(), reason="Chromium ausente neste ambiente")
def test_o_cartao_aparece_a_cada_corte_entregue():
    """O que ele vai ver: a tela enchendo enquanto a fonte ainda é cortada.

    Os asserts de código acima provam o mecanismo; este prova o efeito. Sem ele
    o servidor poderia estar avisando perfeitamente para uma tela que não
    redesenha — que é exatamente o tipo de falha calada desta base.
    """
    playwright_api = pytest.importorskip("playwright.sync_api")
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    import app as aplicacao

    alvo = lambda: aplicacao.app.run(port=PORTA, threaded=True, use_reloader=False)  # noqa: E731
    threading.Thread(target=alvo, daemon=True).start()
    time.sleep(2.5)

    with playwright_api.sync_playwright() as p:
        navegador = p.chromium.launch(executable_path=_chromium())
        pagina = navegador.new_page(viewport={"width": 1366, "height": 768})
        erros = []
        pagina.on("pageerror", lambda e: erros.append(str(e)))
        pagina.goto(f"http://127.0.0.1:{PORTA}/", wait_until="load")
        time.sleep(1.2)
        pagina.evaluate("() => { state.clips = []; state.sourceDuration = %s; }" % FONTE_S)

        contagens = []
        for i, (de, ate) in enumerate([(87.7, 174.6), (256.6, 399.6), (472.0, 591.4)]):
            pagina.evaluate(
                "(carga) => handleStatusUpdate(carga)",
                {"status": "clip_ready", "data": {
                    "clip": _corte_para_a_tela(i, de, ate), "index": i,
                    "delivered": i + 1, "expected": 3,
                    "output_folder": "/saida", "selection_source": "gemini"}},
            )
            time.sleep(0.4)
            contagens.append(
                pagina.evaluate("document.querySelectorAll('#resultsGrid .result-card').length")
            )

        ambiente = pagina.evaluate("document.querySelector('.rail-tab.is-active')?.dataset.ambiente")
        resumo = pagina.evaluate("document.querySelector('.mapa-resumo')?.textContent") or ""
        registro = pagina.evaluate(
            "[...document.querySelectorAll('.console-line')].map(n => n.textContent)"
            ".filter(t => t.includes('[Entrega]'))"
        )
        navegador.close()

    assert erros == [], f"erro de JavaScript ao receber um corte: {erros}"
    assert contagens == [1, 2, 3], (
        f"os cartões não foram aparecendo um a um: {contagens}"
    )
    assert ambiente == "auditoria", (
        "o primeiro corte pronto não levou o editor para onde ele pode revisá-lo"
    )
    # O mapa da fonte enche junto: ele vê a cobertura crescer enquanto espera.
    assert "3 cortes" in resumo, resumo
    assert len(registro) == 3, f"o registro não contou as entregas: {registro}"
    assert "Corte 1 de 3" in registro[0], registro[0]
