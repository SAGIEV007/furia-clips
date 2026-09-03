"""Os cortes existiam. A tela contava e não abria.

O editor descreveu três coisas numa frase só:

    "não sei sequer onde fica a pasta de cortes, no proprio programa não da
     para ver os cortes mesmo dizendo que tem mais de 70 e para piorar quando
     eu seleciono qualquer um dos cortes, pelo menos no video selecionado,
     mostra apenas o mesmo trecho do video"

São três sintomas de um problema só: a tela sabia contar os cortes e não tinha
como abrir nenhum deles.

  1. O card de cada live já dizia "72 clips" — o número vinha do banco. Mas o
     card era um bloco de texto sem clique, e nada na página chamava
     `/api/projects/<id>`. A rota existia no motor desde sempre, devolvendo os
     cortes; ninguém pedia. Pior: a lista de lives ficava escondida duas vezes,
     com `hidden` no HTML e dentro da etapa 04 ("Aprendizado"), que é o último
     lugar onde alguém procuraria os cortes de ontem.

  2. Não havia como assistir um corte. A moldura de prévia só sabia mostrar o
     vídeo-fonte a partir do zero, e nada levava o segundo do corte até ela —
     daí "mostra apenas o mesmo trecho". E a moldura mora na etapa 01, então
     mesmo carregada ela ficava com `display:none !important` enquanto ele
     estava na etapa 03 olhando os cortes.

  3. O botão que abre a pasta nasce com `display:none` e só aparece quando uma
     moagem termina. Fechando e abrindo o programa ele some de novo, com os
     cortes todos no disco.

Este arquivo mede os três, e mais um que apareceu no caminho: o estúdio de
texto de arte montava os cartões inteiros e os jogava fora.
"""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
JS = (RAIZ / "static" / "js" / "app.js").read_text(encoding="utf-8")
HTML = (RAIZ / "templates" / "index.html").read_text(encoding="utf-8")
MOTOR = (RAIZ / "app.py").read_text(encoding="utf-8")
LANCADOR = (RAIZ / "run.bat").read_text(encoding="utf-8", errors="replace")


def sem_comentario(fonte):
    """O texto sem os comentários — que aqui contam o defeito por extenso."""
    sem_bloco = re.sub(r"/\*.*?\*/", "", fonte, flags=re.S)
    return "\n".join(
        linha for linha in sem_bloco.splitlines()
        if not linha.lstrip().startswith("//")
    )


LIMPO = sem_comentario(JS)


# ── a porta da frente ───────────────────────────────────────────────────────


def test_a_porta_da_frente_e_a_tela_que_ele_consegue_usar():
    """A `/` serve a tela da 6.6, e a da 6.61 fica de pé sem link para ela.

    Ele foi claro sobre as duas: da 6.61 disse "é horrível e eu nunca consegui
    usar"; da 6.6, "eu consigo usar minimamente para fazer cortes". Contagem de
    teste não mede se ele consegue trabalhar.
    """
    assert '@app.route("/")\ndef index():' in MOTOR
    assert 'return render_template("index.html")' in MOTOR
    assert '@app.route("/mesa")' in MOTOR
    assert 'return render_template("mesa.html")' in MOTOR


def test_a_tela_da_frente_nao_carrega_os_scripts_da_outra():
    """Uma tela só. Misturar os dois conjuntos de script foi o que produziu as
    telas meio montadas de antes."""
    for arquivo in ("mesa.js", "atelie.js", "mapa.js", "painel.js", "talho.js", "mesa-app.js"):
        assert arquivo not in HTML, f"a tela da frente voltou a carregar {arquivo}"


def test_o_lancador_abre_a_tela_da_frente():
    """Uma aba só, e a da frente."""
    assert "3001/classico" not in LANCADOR
    assert "3001/estudio" not in LANCADOR
    assert LANCADOR.count('-Url "http://127.0.0.1:3001"') == 1


# ── 1. os cortes que existiam e não apareciam ───────────────────────────────


def test_o_corte_guardado_ganha_os_nomes_que_a_tela_le():
    """O banco guarda `start_time`, `end_time` e `file_path`. A tela — a mesma
    que recebe os cortes ao vivo pelo socket — lê `start`, `end` e `path`.

    Enquanto os dois nomes não se encontravam, os cortes de uma rodada anterior
    existiam no banco e não tinham como chegar na tela.
    """
    import json

    import app as motor

    guardado = {
        "id": 7,
        "file_path": "workspace/exports/corte-07.mp4",
        "start_time": 60.0,
        "end_time": 102.5,
        "duration": 42.5,
        "viral_score": 84,
        "score_confidence": 0.72,
        "transcript": "o que ele diz aqui",
        "score_factors": json.dumps({"hook": 0.8, "_review_flags": {"x": 1}}),
        "suggested_titles": json.dumps(["Um título"]),
        "suggested_tags": json.dumps(["tag"]),
        "suggested_hashtags": json.dumps(["#a"]),
        "suggested_description": "uma descrição",
    }
    na_tela = motor._corte_guardado_para_a_tela(guardado, fonte="workspace/uploads/live.mp4")

    assert na_tela["start"] == 60.0
    assert na_tela["end"] == 102.5
    assert na_tela["duration"] == 42.5
    assert na_tela["path"] == "workspace/exports/corte-07.mp4"
    assert na_tela["clip_id"] == 7
    assert na_tela["text"] == "o que ele diz aqui"
    assert na_tela["source_video"].replace("\\", "/") == "workspace/uploads/live.mp4"
    assert na_tela["seo"]["titles"] == ["Um título"]


def test_os_fatores_internos_nao_vazam_para_a_tela():
    """`_review_flags` e `_review_metadata` são anotações do motor dentro do
    mesmo campo. A tela desenha uma barrinha para cada fator; um dicionário
    inteiro entre eles viraria uma barra sem sentido."""
    import json

    import app as motor

    na_tela = motor._corte_guardado_para_a_tela({
        "id": 1, "file_path": "x.mp4", "start_time": 0, "end_time": 1, "duration": 1,
        "score_factors": json.dumps({
            "hook": 0.8, "_review_flags": {"a": 1}, "_review_metadata": {"b": 2},
        }),
    })
    assert na_tela["factors"] == {"hook": 0.8}


def test_o_corte_sem_nada_guardado_nao_derruba_a_tela():
    """Rodadas antigas têm campos vazios ou texto que não é JSON. Uma exceção
    aqui deixaria a lista inteira de fora."""
    import app as motor

    na_tela = motor._corte_guardado_para_a_tela({
        "id": 2, "file_path": "", "start_time": None, "end_time": None,
        "duration": None, "score_factors": "não é json", "suggested_titles": "{",
    })
    assert na_tela["start"] == 0.0
    assert na_tela["factors"] == {}
    assert na_tela["seo"]["titles"] == []


def test_a_rota_do_projeto_devolve_os_cortes_no_formato_da_tela():
    assert "_corte_guardado_para_a_tela(c, fonte) for c in get_clips(project_id)" in MOTOR


def test_a_rota_do_projeto_diz_onde_os_cortes_estao():
    """Sem isto o botão da pasta continuaria sem saber para onde apontar depois
    de reabrir uma live guardada."""
    trecho = MOTOR[MOTOR.find("def api_get_project"):]
    trecho = trecho[:trecho.find("\n@app.route")]
    assert 'project["output_dir"]' in trecho
    assert 'get_setting("output_dir")' in trecho


def test_o_card_da_live_abre_os_cortes():
    """O card contava "72 clips" e não abria nada."""
    assert "data-abrir-projeto" in LIMPO
    assert "async function abrirOsCortesDoProjeto" in LIMPO
    corpo = LIMPO[LIMPO.find("async function abrirOsCortesDoProjeto"):]
    corpo = corpo[:corpo.find("\n}")]
    assert "/api/projects/${Number(projectId)}" in corpo
    assert "displayResults(cortes" in corpo, (
        "abriu a live e não mandou os cortes para a tela"
    )


def test_a_live_sem_corte_nao_vira_botao():
    """Um card que promete abrir e abre uma lista vazia é pior que um card que
    não promete nada."""
    trecho = LIMPO[LIMPO.find("function renderProjectLibrary"):]
    trecho = trecho[:trecho.find("\n}")]
    assert "const abrivel = clips > 0;" in trecho
    assert "abrivel ? `role=" in trecho or 'abrivel ? `role="button"' in trecho


def test_a_lista_de_lives_esta_na_etapa_em_que_ele_comeca():
    """Ela estava na etapa 04 ("Aprendizado"), que é o último lugar onde alguém
    procuraria os cortes de ontem. Reabrir uma live é escolher uma fonte."""
    assert 'id="doneLivesSection"' in HTML
    assert '"doneLivesSection"' in LIMPO
    linha = next(l for l in LIMPO.splitlines() if l.strip().startswith("source: ["))
    assert "doneLivesSection" in linha


def test_a_lista_de_lives_nao_nasce_escondida():
    """`hidden` no HTML, além da etapa errada: escondida duas vezes."""
    bloco = HTML[HTML.find('id="doneLivesSection"'):]
    bloco = bloco[:bloco.find("</section>")]
    assert "hidden" not in bloco
    assert 'id="projectLibraryList"' in bloco


# ── 2. cada corte mostrando o próprio trecho ────────────────────────────────


def test_cada_corte_tem_como_ser_assistido():
    assert 'onclick="verOTrecho(${originalIndex})"' in LIMPO
    assert "function verOTrecho(" in LIMPO


@pytest.fixture()
def ver_o_trecho():
    corpo = LIMPO[LIMPO.find("function verOTrecho("):]
    return corpo[:corpo.find("\n}")]


def test_o_trecho_toca_o_arquivo_do_proprio_corte(ver_o_trecho):
    """Quando o corte já foi renderizado, o arquivo dele É o corte — não uma
    aproximação dele."""
    assert "const arquivoDoCorte = String(corte.path" in ver_o_trecho
    assert "arquivoDoCorte\n        ? mediaUrlForPath(arquivoDoCorte)" in ver_o_trecho


def test_sem_arquivo_a_fonte_abre_no_segundo_do_corte(ver_o_trecho):
    """O segundo vai no próprio endereço (`#t=`), que o navegador lê antes de
    qualquer script rodar — em vez de abrir no zero e pular depois."""
    assert "#t=${inicio.toFixed(2)}" in ver_o_trecho
    assert "fim > inicio" in ver_o_trecho, "o fim do corte sumiu do endereço"


def test_o_trecho_para_onde_o_corte_acaba():
    """Sem isto a fonte seguiria tocando pela live adentro, e o que ele veria
    não seria mais o corte."""
    assert "function pararNoFimDoTrecho(" in LIMPO
    corpo = LIMPO[LIMPO.find("function pararNoFimDoTrecho("):]
    corpo = corpo[:corpo.find("\n}\n")]
    assert 'addEventListener("timeupdate"' in corpo
    assert "video.pause()" in corpo
    assert "pararNoFimDoTrecho();" in LIMPO, "ninguém liga a trava ao abrir a tela"


def test_ver_a_fonte_inteira_nao_para_no_meio():
    """A trava é do corte. Assistindo a fonte, ela tem de sair do caminho."""
    corpo = LIMPO[LIMPO.find("function showVideoPreview("):]
    corpo = corpo[:corpo.find("\n}")]
    assert "state.trechoNoPlayer = null" in corpo


def test_a_moldura_sai_da_escuridao_para_mostrar_o_corte(ver_o_trecho):
    """A moldura mora na etapa 01. Ele olha os cortes na etapa 03, então ela
    está com `stage-off` — que é `display:none !important` e ganha de qualquer
    `display:block`. Sem esta linha o vídeo carrega, toca, e ninguém vê."""
    assert 'section.classList.remove("stage-off")' in ver_o_trecho
    assert ".stage-off { display: none !important; }" in (
        RAIZ / "static" / "css" / "style.css"
    ).read_text(encoding="utf-8"), "a regra mudou; a linha acima pode ter virado enfeite"


def test_o_corte_de_uma_live_guardada_sabe_qual_e_a_fonte(ver_o_trecho):
    """Reabrindo uma live, não há vídeo selecionado à mão. Sem a fonte que veio
    junto com o projeto, os cortes sem arquivo renderizado não teriam o que
    mostrar."""
    assert "function fonteDesteCorte(" in LIMPO
    fonte = LIMPO[LIMPO.find("function fonteDesteCorte("):]
    fonte = fonte[:fonte.find("\n}")]
    assert "corte.source_video" in fonte
    assert "state.fonteDoProjetoAberto" in fonte


# ── 3. a pasta ──────────────────────────────────────────────────────────────


def test_a_pasta_dos_cortes_esta_na_barra_de_cima():
    """O outro botão vive dentro dos resultados e nasce escondido: só aparece
    depois que uma moagem termina. Fechando e abrindo o programa ele some, com
    os cortes todos no disco."""
    cabecalho = HTML[HTML.find('<div class="main-header-actions">'):]
    cabecalho = cabecalho[:cabecalho.find("</header>")]
    assert 'id="btnCutsFolder"' in cabecalho
    botao = cabecalho[cabecalho.find('id="btnCutsFolder"'):]
    botao = botao[:botao.find("</button>")]
    assert "display:none" not in botao, "o botão da pasta voltou a nascer escondido"


def test_o_botao_da_pasta_faz_alguma_coisa():
    assert 'getElementById("btnCutsFolder")' in LIMPO
    assert "openOutputFolder(state.outputFolder" in LIMPO


def test_sem_caminho_o_botao_pergunta_ao_motor_em_vez_de_recusar():
    """"Pasta não informada" era o que ele ouvia justamente quando não sabia
    onde a pasta ficava — que é quando mais precisava do botão. O motor, sem
    caminho pedido, abre a pasta para onde os cortes realmente vão."""
    corpo = LIMPO[LIMPO.find("async function openOutputFolder("):]
    corpo = corpo[:corpo.find("\n}")]
    assert "Pasta não informada" not in corpo
    assert "folderPath ? { path: folderPath } : {}" in corpo


def test_a_pasta_padrao_continua_permitida_no_motor():
    """O conserto do 403 tem de continuar de pé: escolher uma pasta de saída
    nos ajustes não pode tirar a pasta padrão da lista de permitidos."""
    corpo = MOTOR[MOTOR.find("def api_open_folder"):]
    corpo = corpo[:corpo.find("\n@app.route")]
    assert "[destino_dos_cortes, EXPORT_DIR]" in corpo


# ── o que apareceu no caminho ───────────────────────────────────────────────


def test_o_estudio_de_texto_atribui_o_que_montou():
    """A função montava os cartões inteiros e os jogava fora: mensagem verde de
    sucesso, servidor devolvendo as sugestões, e a tela em branco. Era o mesmo
    defeito que já tinha custado dois ciclos na 6.7 — e a versão 6.6 nunca
    recebeu o conserto."""
    corpo = LIMPO[LIMPO.find("function renderHeadlineStudioResults("):]
    corpo = corpo[:corpo.find("\n}")]
    assert "container.innerHTML = " in corpo
    assert corpo.find("container.innerHTML = ") < corpo.find('container.style.display = "block"')
    assert corpo.find("const formatCards") < corpo.find("container.innerHTML = "), (
        "atribuiu antes de montar os cartões"
    )
