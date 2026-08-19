"""A tela do estúdio precisa mostrar os cartões, e ninguém estava verificando.

Na 6.7 eu removi o formato "fake tweet" da interface com um script que apagava
linhas do bloco até achar uma que terminasse em crase-ponto-e-vírgula. Essa linha
era a atribuição do `container.innerHTML`. Durante dois ciclos a função montou o
HTML inteiro e o jogou fora: a mensagem verde de sucesso aparecia, o servidor
devolvia as sugestões, e a tela ficava em branco.

O `node --check` passou nas duas vezes, porque o código continuava sintaticamente
válido — ele só não fazia nada. Nenhuma verificação que eu tinha era capaz de
pegar isso, e o editor teve de reportar duas vezes.

Este teste renderiza a função de verdade num navegador de verdade, com o payload
que o gerador produz, e pergunta a única coisa que importa: apareceu cartão na
tela? É pesado para um teste unitário e é o preço de ter quebrado a tela em
silêncio.
"""

import json
import os
import pathlib
import shutil
import subprocess
import textwrap

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_JS = os.path.join(RAIZ, "static", "js", "app.js")
CHROMIUM = "/opt/pw-browsers/chromium"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None or not os.path.exists(CHROMIUM),
    reason="node ou Chromium ausentes neste ambiente",
)


# Fixture pontuada de propósito: este teste é sobre a tela, não sobre a leitura
# da fonte. E uma fixture que repete a mesma expressão em linhas seguidas cai no
# dedutor de legenda progressiva do parser, que a colapsa antes de chegar aqui.
LEGENDA = """1
00:00:00,000 --> 00:00:04,000
As criptos são uma nova lógica de reserva de valor.

2
00:00:04,000 --> 00:00:09,000
O Brasil escolheu o caminho arcaico para tratar essa tecnologia.

3
00:00:09,000 --> 00:00:14,000
Quem escolhe o caminho arcaico paga com o próprio futuro.

4
00:00:14,000 --> 00:00:19,000
E esse caminho arcaico das criptos é uma escolha do Estado brasileiro.
"""


def _onde_esta_o_playwright() -> str:
    """A pasta que contém `node_modules/playwright`, ou vazio.

    Devolve a pasta-mãe, não o `node_modules`: o import ESM não olha NODE_PATH, e
    a única forma de o script achar o pacote é rodar de dentro do diretório que o
    contém.
    """
    candidatos = [
        os.path.join(RAIZ, "node_modules"),
        os.path.join(os.path.expanduser("~"), "node_modules"),
        *[
            os.path.join(base, "node_modules")
            for base in (os.environ.get("CLAUDE_SCRATCHPAD", ""), os.getcwd())
            if base
        ],
    ]
    for caminho in candidatos:
        if os.path.isdir(os.path.join(caminho, "playwright")):
            return os.path.dirname(caminho)
    return ""


def _funcao(fonte: str, nome: str) -> str:
    inicio = fonte.index(f"function {nome}(")
    fim = fonte.index("\nfunction ", inicio + 5)
    return fonte[inicio:fim]


def _renderizar(tmp_path, payload: dict) -> dict:
    """Roda a função de render da interface num Chromium e conta o que apareceu."""
    fonte = open(APP_JS, encoding="utf-8").read()
    trechos = "\n".join(
        _funcao(fonte, nome)
        for nome in ("artworkHeadlineHtml", "renderArtworkHeadline",
                     "renderHeadlineStudioResults", "formatTimecode")
    )
    pagina = tmp_path / "estudio.html"
    pagina.write_text(
        "<!doctype html><meta charset='utf-8'><div id='alvo'></div><script>\n"
        "function escapeHtml(v){return String(v==null?'':v).replace(/[&<>\"']/g,"
        "c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'}[c]));}\n"
        "const state={};\n"
        "const artworkFormatLabels={vertical_916:'9:16',square_alfinetei:'1:1'};\n"
        "function artworkCopyButton(){return '<button class=\"artwork-copy-button\"></button>';}\n"
        "function artworkFeedbackButton(){return '<button class=\"artwork-feedback-button\"></button>';}\n"
        "function copyToClipboard(){}\nfunction saveArtworkFeedback(){}\n"
        f"{trechos}\n"
        f"const payload={json.dumps(payload, ensure_ascii=False)};\n"
        "renderHeadlineStudioResults(payload,{container:document.getElementById('alvo')});\n"
        "</script>",
        encoding="utf-8",
    )
    base = _onde_esta_o_playwright()
    if not base:
        pytest.skip("playwright não encontrado nesta máquina")
    script = pathlib.Path(base) / "_furia_render_test.mjs"
    script.write_text(textwrap.dedent(f"""
        import {{ chromium }} from 'playwright';
        const b = await chromium.launch({{ executablePath: '{CHROMIUM}' }});
        const p = await b.newPage();
        const erros = [];
        p.on('pageerror', e => erros.push(String(e)));
        await p.goto('file://{pagina}');
        const contagem = await p.evaluate(() => ({{
            cartoes: document.querySelectorAll('.artwork-suggestion-card').length,
            headlines: document.querySelectorAll('.artwork-headline').length,
            ganchos: document.querySelectorAll('.artwork-eyebrow').length,
            destaques: document.querySelectorAll('.artwork-mark').length,
            html: document.getElementById('alvo').innerHTML.length,
        }}));
        console.log(JSON.stringify({{ ...contagem, erros }}));
        await b.close();
    """).strip(), encoding="utf-8")

    try:
        resultado = subprocess.run(
            [shutil.which("node"), str(script)],
            cwd=base, capture_output=True, text=True, timeout=180,
        )
    finally:
        script.unlink(missing_ok=True)
    if resultado.returncode != 0:
        pytest.skip(f"playwright indisponível: {resultado.stderr[-200:]}")
    return json.loads(resultado.stdout.strip().splitlines()[-1])


def test_a_tela_mostra_os_cartoes_que_o_gerador_produziu(tmp_path):
    from modules.headline_studio import FORMAT_SQUARE, generate_artwork_copy

    payload = generate_artwork_copy(
        LEGENDA,
        mini_context="Fala do presidenciável Renan Santos sobre as criptos",
        preferred_format=FORMAT_SQUARE,
        ai_backend=None,
    )
    esperado = len(payload["formats"][FORMAT_SQUARE]["suggestions"])
    assert esperado, "o gerador precisa devolver sugestões para o teste valer"

    tela = _renderizar(tmp_path, payload)
    assert not tela["erros"], f"a página quebrou: {tela['erros']}"
    assert tela["html"] > 0, (
        "o container ficou vazio: a função montou o HTML e não o atribuiu, que é "
        "exatamente o defeito que deixou a tela em branco por dois ciclos"
    )
    assert tela["cartoes"] == esperado, (
        f"o gerador devolveu {esperado} sugestões e a tela mostrou {tela['cartoes']}"
    )
    assert tela["ganchos"] == esperado, "toda headline aparece com gancho na tela"


def test_o_trecho_destacado_e_pintado_dentro_da_frase(tmp_path):
    """O destaque é parte da leitura, não uma anotação embaixo dela."""
    from modules.headline_studio import FORMAT_SQUARE, generate_artwork_copy

    payload = generate_artwork_copy(
        LEGENDA,
        mini_context="Fala do presidenciável Renan Santos sobre as criptos",
        preferred_format=FORMAT_SQUARE,
        ai_backend=None,
    )
    com_destaque = sum(1 for item in payload["formats"][FORMAT_SQUARE]["suggestions"] if item["emphasis"])
    if not com_destaque:
        pytest.skip("esta fonte não rendeu trecho em destaque")

    tela = _renderizar(tmp_path, payload)
    assert tela["destaques"] == com_destaque


def test_a_tela_diz_o_motivo_quando_nada_foi_gerado(tmp_path):
    """Silêncio é defeito: o motivo já vem do servidor e tem de chegar à tela."""
    from modules.headline_studio import FORMAT_VERTICAL, generate_artwork_copy

    payload = generate_artwork_copy(
        "Boa noite. Obrigado. Prazer todo meu. Muito obrigado mesmo, viu.",
        preferred_format=FORMAT_VERTICAL,
        ai_backend=None,
    )
    assert not payload["formats"][FORMAT_VERTICAL]["suggestions"]

    tela = _renderizar(tmp_path, payload)
    assert not tela["erros"]
    assert tela["cartoes"] == 0
    assert tela["html"] > 0, "sem cartão a tela ainda precisa explicar o que faltou"
