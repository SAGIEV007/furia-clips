"""A interface não pode referenciar o que não existe mais.

Ao remover três configurações mortas da barra lateral eu deixei para trás um
`addEventListener` apontando para um elemento que tinha acabado de sair do HTML.
No escopo do módulo isso lança um erro de referência nula e mata a execução do
script dali em diante: não é um controle que para de funcionar, é toda a
interface abaixo daquela linha.

Este teste é a varredura que pegou o meu erro, deixada no lugar.
"""

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
JS = (RAIZ / "static" / "js" / "app.js").read_text(encoding="utf-8")
HTML = (RAIZ / "templates" / "index.html").read_text(encoding="utf-8")
CSS = (RAIZ / "static" / "css" / "style.css").read_text(encoding="utf-8")

IDS_NO_HTML = set(re.findall(r'id="([^"]+)"', HTML))


def test_nenhum_acesso_desprotegido_a_elemento_inexistente():
    """`getElementById("x").algo` sem `?.` exige que o id exista no HTML."""
    ausentes = {
        achado.group(1)
        for achado in re.finditer(r'document\.getElementById\("([^"]+)"\)\.(?!\s)', JS)
        if achado.group(1) not in IDS_NO_HTML
    }

    assert not ausentes, f"o script acessa ids que não existem no HTML: {sorted(ausentes)}"


def test_as_configuracoes_mortas_sairam_dos_dois_lados():
    """Removidas por não chegarem a lugar nenhum no servidor.

    O cortador é sempre "intelligent"; a duração é decidida pela costura da
    conversa, não por um menu; e a correção com IA só existia como valor padrão.
    """
    for morta in ("settingCutMethod", "settingCutDuration", "settingAiCorrection"):
        assert morta not in HTML, f"{morta} continua no HTML"
        assert morta not in JS, f"{morta} continua no script"


def test_a_barra_de_execucao_existe_dos_dois_lados():
    for elemento in ("runBar", "runBarTitle", "runBarDetail", "runBarClock", "runBarCancel"):
        assert f'id="{elemento}"' in HTML
    assert "beginRun(" in JS and "endRun(" in JS


def test_o_cancelamento_aponta_para_uma_rota_que_existe():
    """Eu tinha chutado /api/cancel, que não existe."""
    rotas = (RAIZ / "app.py").read_text(encoding="utf-8")
    for chamada in re.findall(r'fetch\("(/api/[^"`]+)"', JS):
        if chamada.endswith("/cancel"):
            assert f'"{chamada}"' in rotas, f"{chamada} não existe no servidor"


def test_o_conflito_de_processamento_tem_mensagem_propria():
    """409 é a guarda funcionando, não uma falha inexplicável."""
    assert "response.status === 409" in JS
    assert "Já existe um processamento em andamento" in JS


# ── Navegação por etapa ────────────────────────────────────────────────────────

def test_toda_secao_pertence_a_uma_etapa():
    """Uma seção fora do mapa some da tela e não volta por nenhum caminho."""
    mapa = re.search(r"const STAGE_SECTIONS = \{(.*?)\n\};", JS, re.DOTALL)
    assert mapa, "o mapa de etapas sumiu"
    mapeadas = set(re.findall(r'"([A-Za-z0-9_]+)"', mapa.group(1)))

    for secao in re.findall(r'<section class="section[^"]*" id="([^"]+)"', HTML):
        # O console é o registro do que está acontecendo e fica alcançável de
        # qualquer etapa, por isso não entra no agrupamento.
        if secao == "consoleSection":
            continue
        assert secao in mapeadas, f"{secao} não pertence a nenhuma etapa"


def test_a_etapa_esconde_com_classe_e_nao_com_o_atributo():
    """Prévia e resultados carregam `display` embutido, que ganha de `[hidden]`."""
    assert "stage-off" in JS and "stage-off" in CSS
    assert "secao.hidden = !visivel" not in JS


def test_as_etapas_sao_alcancaveis_pelo_teclado():
    assert 'setAttribute("role", "button")' in JS
    assert 'setAttribute("tabindex", "0")' in JS


# ── Voz de referência ──────────────────────────────────────────────────────────

def test_a_voz_tem_como_ser_cadastrada_pela_interface():
    """As rotas existiam desde a 4.8 sem nenhum botão que chegasse nelas.

    O editor perguntou como cadastrar e a resposta honesta era "não dá" — o
    mesmo padrão de peça pronta e desligada que este projeto repete.
    """
    for elemento in ("voicePanel", "voiceStatus", "btnEnrollVoice", "voiceFileInput"):
        assert f'id="{elemento}"' in HTML, f"{elemento} não existe na interface"
    assert "/api/voz/cadastrar" in JS
    assert "/api/voz/status" in JS


def test_a_rota_de_voz_existe_no_servidor():
    servidor = (RAIZ / "app.py").read_text(encoding="utf-8")
    assert '"/api/voz/cadastrar"' in servidor
    assert '"/api/voz/status"' in servidor
