"""O ESTÚDIO — a interface que ele mandou, ligada no motor que já existia.

Ele mandou o `furiastudiofinal_1.zip` e disse: *"Você pode usar apenas essa a
partir de agora ok? não precisa por hora criar mais nada a não ser que seja
necessario, só adapte tudo o que ja funcionava aqui antes, console, blocos,
etc..."*

Cada teste aqui guarda um defeito de verdade — a maioria encontrada com a foto
da tela dele na mão, na resolução dele, que é 1366×768. Nenhum foi escrito por
antecipação: todos nasceram de alguma coisa que apareceu errada.
"""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
JS = RAIZ / "estudio" / "static" / "app.js"
CSS = RAIZ / "estudio" / "static" / "app.css"
HTML = RAIZ / "estudio" / "templates" / "estudio.html"
MOTOR = RAIZ / "app.py"


@pytest.fixture(scope="module")
def js():
    return JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def css():
    return CSS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def html():
    return HTML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def motor():
    return MOTOR.read_text(encoding="utf-8")


def sem_comentario(fonte):
    """O texto sem os comentários.

    Três vezes neste projeto um teste leu o próprio comentário que explicava
    por que a coisa proibida não estava lá, e passou a acusar o comentário. A
    saída certa nunca é enfraquecer o que o teste mede: é parar de medir a
    explicação.
    """
    sem_bloco = re.sub(r"/\*.*?\*/", "", fonte, flags=re.S)
    return "\n".join(
        linha for linha in sem_bloco.splitlines()
        if not linha.lstrip().startswith("//")
    )


def sem_docstring(fonte):
    """O Python sem as aspas triplas.

    Mesmo motivo do de cima: o `estudio/app.py` explica no próprio texto de
    abertura QUAL era o título pronto que saiu fora, e o teste passou a acusar
    a explicação. A frase proibida não pode estar no código; no relato de por
    que ela saiu, pode.
    """
    return re.sub(r'"""[\s\S]*?"""', "", fonte)


def carregar_estudio():
    import importlib.util
    import sys
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    spec = importlib.util.spec_from_file_location("estudio_app", RAIZ / "estudio" / "app.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture(scope="module")
def estudio():
    return carregar_estudio()


# ── a porta da frente ───────────────────────────────────────────────────────


def test_o_estudio_e_a_porta_da_frente(motor):
    """Ele pediu para usar só esta. Então é esta que abre em `/`."""
    assert 'from estudio.app import estudio as _frente_estudio' in motor
    assert 'app.register_blueprint(_frente_estudio)' in motor
    assert '@app.route("/classico")' in motor, (
        "a interface antiga voltou para a porta da frente"
    )


def test_o_lancador_abre_uma_aba_so():
    """Duas abas era para comparar a bancada com a antiga. Ele já comparou e
    escolheu: agora abre o estúdio e mais nada."""
    bat = (RAIZ / "run.bat").read_text(encoding="utf-8", errors="replace")
    aberturas = bat.count("open_browser_windows.ps1")
    assert aberturas == 1, f"o lançador abre {aberturas} abas"
    assert "3001/2" not in bat and "3001/classico" not in bat


def test_nenhuma_tela_leva_ele_de_volta_para_a_interface_antiga(js, html):
    """O defeito que ele gritou: *"quando fui em ajustes e ajustes completos
    simplesmente abriu o furia antigo, PORQUE????"*

    Um botão que devolve para o lugar de onde ele pediu para sair é o programa
    admitindo que não dá conta — e me deixa confortável em deixar buraco na
    tela nova. A interface antiga continua servida em `/classico` para não se
    perder nada, e ninguém é levado até lá.
    """
    for arquivo, texto in (("app.js", js), ("estudio.html", html)):
        limpo = sem_comentario(texto)
        assert "/classico" not in limpo, f"{arquivo} voltou a levar para a interface antiga"


def test_o_estudio_tem_a_propria_tela_de_ajustes(js):
    """A saída para "faltou ajuste aqui" é construir o ajuste aqui."""
    limpo = sem_comentario(js)
    assert "carregarOsAjustes" in limpo and "guardarOsAjustes" in limpo
    for campo in ("gemini_api_key", "whisper_model", "cut_duration", "output_dir", "channel_context"):
        assert f'"{campo}"' in limpo, f"sumiu o ajuste {campo} da tela"


def test_a_pasta_de_saida_se_escolhe_por_janela_e_nao_se_digita(js):
    """Ele não digita caminho. Se precisa de pasta, tem botão que abre a janela
    do Windows."""
    limpo = sem_comentario(js)
    assert '"/api/dialog/choose"' in limpo
    assert '"escolher-pasta"' in limpo
    assert '"folder"' in limpo, "o modo do diálogo tem de ser um que a rota aceita"


# ── o motor de brinquedo foi embora ─────────────────────────────────────────


FRASES_DE_ENFEITE = [
    "A frase que muda o rumo da conversa",
    "O trecho mais claro da fonte",
    "Uma resposta pronta para virar corte",
    "A ideia com mais energia editorial",
    "O momento que pede formato vertical",
    "Um argumento que se sustenta sozinho",
    "A virada que merece contexto",
    "O melhor recorte desta fonte",
]


def test_os_titulos_prontos_do_zip_nao_existem_em_lugar_nenhum(js, estudio):
    """O motor que veio no zip dava a cada corte um título tirado de uma lista
    de oito frases prontas, e uma nota calculada da duração e da posição na
    fila. Onze cortes ficavam com cara de irmãos e a nota não media nada.

    Isso não é seleção fraca: é enfeite com cara de seleção, que é a coisa mais
    cara que pode existir num programa de corte, porque parece que funcionou.
    """
    origem_py = sem_docstring((RAIZ / "estudio" / "app.py").read_text(encoding="utf-8"))
    codigo_js = sem_comentario(js)
    for frase in FRASES_DE_ENFEITE:
        assert frase not in codigo_js, f"voltou o título pronto: {frase!r}"
        assert frase not in origem_py, f"voltou o título pronto: {frase!r}"
    assert not hasattr(estudio, "create_candidates"), "voltou o seletor de brinquedo"


def test_o_titulo_do_corte_vem_do_material(estudio):
    """Primeiro o que o motor sugeriu; se não sugeriu, a primeira frase da
    própria fala. Nunca um texto inventado pelo programa."""
    do_motor = estudio._titulo({"suggested_titles": '["O que ele disse sobre a CLT"]'})
    assert do_motor == "O que ele disse sobre a CLT"

    da_fala = estudio._titulo({
        "transcript": "A CLT do jeito que está trava o emprego. E ninguém diz isso.",
    })
    assert da_fala == "A CLT do jeito que está trava o emprego."

    sem_nada = estudio._titulo({})
    assert "corte" in sem_nada.lower() and "melhor" not in sem_nada.lower()


def test_a_nota_da_maquina_e_apresentada_como_palpite(js):
    """NORTE §15: um número que a ferramenta gera sobre o que a ferramenta fez
    não mede nada. A nota pode aparecer — ela ordena a lista — mas não pode
    aparecer com cara de resultado."""
    limpo = sem_comentario(js)
    assert "palpite da máquina, não uma promessa" in limpo
    for promessa in ("viral", "vai bombar", "previsão de alcance", "chance de viralizar"):
        assert promessa.lower() not in limpo.lower(), f"a tela promete {promessa!r}"


def test_o_motivo_do_corte_e_frase_de_oficio_e_nao_nome_de_codigo(estudio):
    """"hook 78" não diz nada para quem vai decidir se corta."""
    motivos = estudio._motivos({"hook": 81.0, "duration_fit": 74.0, "clarity": 70.0, "flow": 40.0})
    assert motivos == ["abre com gancho", "duração publicável", "ideia clara"]
    assert "flow" not in " ".join(motivos), "fator fraco virou motivo"
    assert all(not m.isascii() or " " in m for m in motivos), "sobrou nome de código"


def test_so_tres_motivos(estudio):
    """Uma lista de vinte razões é uma lista que ninguém lê."""
    fortes = {nome: 90.0 for nome in estudio.MOTIVOS}
    assert len(estudio._motivos(fortes)) == 3


def test_o_motivo_ignora_o_que_nao_e_numero(estudio):
    """O motor põe `_review_flags` e booleanos dentro do mesmo dicionário."""
    assert estudio._motivos({"_review_flags": {"x": 1}, "has_hook": True, "hook": 88.0}) == ["abre com gancho"]


# ── as bordas que ele moveu ─────────────────────────────────────────────────


def test_a_borda_que_vale_na_tela_e_a_que_ele_arrastou(estudio):
    """O ajuste fica guardado à parte do corte já renderizado, de propósito: o
    arquivo em disco continua o antigo até um render novo. Mas na TELA quem
    manda é a decisão dele — senão ele arrasta a alça, salva, e a tela devolve
    o número velho, que é o programa dizendo que não ouviu."""
    corte = estudio._corte_para_a_tela({
        "id": 7, "start_time": 300.0, "end_time": 345.0,
        "latest_adjustment": {"start": 312.5, "end": 340.0},
        "review_status": "needs_review", "viral_score": 71,
    })
    assert corte["start"] == 312.5
    assert corte["end"] == 340.0
    assert corte["duration"] == 27.5, "a duração ficou do corte velho"
    assert corte["ajustado"] is True


def test_a_duracao_e_calculada_e_nao_copiada(estudio):
    """Já aconteceu antes, na bancada: a tela mostrava a borda nova com a
    duração antiga porque a duração vinha de um campo guardado."""
    corte = estudio._corte_para_a_tela({"id": 1, "start_time": 10.0, "end_time": 55.0, "duration": 999})
    assert corte["duration"] == 45.0


def test_a_alca_da_onda_arrasta_escutando_a_janela(js):
    """A primeira versão prendia o ponteiro na alça e escutava o movimento
    nela. No teste de navegador o `pointerdown` chegava e nenhum `pointermove`
    chegava depois: a alça tem catorze pixels, o cursor sai de cima dela no
    primeiro pixel de movimento, e sem a prisão do ponteiro os eventos vão para
    quem estiver embaixo. A alça não saía do lugar."""
    limpo = sem_comentario(js)
    assert 'window.addEventListener("pointermove", moverAAlca)' in limpo
    # A prisão de ponteiro continua certa para ARRASTAR JANELA pela barra de
    # título, que é larga e fica embaixo do cursor o tempo todo. O que não pode
    # voltar é na alça da onda, que tem catorze pixels.
    alcas = limpo[limpo.find("function ligarAsAlcas"):]
    alcas = alcas[:alcas.find("\n  }")]
    assert "setPointerCapture" not in alcas, "voltou a prisão de ponteiro que não pegava"


def test_soltar_a_alca_nao_redesenha_a_tela_por_baixo(js):
    """O arrasto passou a funcionar e sumia no mesmo gesto: terminar o arrasto
    dispara um clique na onda, e a onda tinha `data-corte`, que abria a revisão
    de novo e devolvia as bordas guardadas. Parecia que o programa ignorou."""
    limpo = sem_comentario(js)
    assert '$$(".clip-card[data-corte]"' in limpo, (
        "voltou a valer para qualquer coisa com data-corte, inclusive a onda"
    )
    assert "arrastou" in limpo, "sumiu a guarda contra o clique que vem depois do arrasto"


def test_os_dois_lugares_que_mostram_a_borda_andam_juntos(js):
    """Dois números da mesma coisa discordando na tela é o jeito mais rápido de
    ele parar de acreditar nos dois."""
    limpo = sem_comentario(js)
    assert "bordasDoCorte" in limpo
    trecho = limpo[limpo.find("function posicionarAsAlcas"):]
    trecho = trecho[:trecho.find("\n  }")]
    assert "bordasDoCorte" in trecho, "o painel do lado parou de acompanhar o arrasto"


# ── o console ───────────────────────────────────────────────────────────────


def test_o_console_ouve_o_canal_do_motor(js):
    """Ele pediu pelo nome. É a única peça que responde "o que está acontecendo
    agora" sem ele abrir uma pasta."""
    limpo = sem_comentario(js)
    assert 'canal.on("progress"' in limpo
    assert 'canal.on("status"' in limpo
    assert "escreverNoConsole" in limpo


def test_o_console_tem_memoria(js):
    """Um canal ao vivo só mostra o que passou enquanto a página estava aberta.
    Na prática: ele recarrega a tela no meio de meia hora de trabalho e o
    console fica em branco — o pior momento possível para a tela parecer vazia.
    """
    limpo = sem_comentario(js)
    assert "recuperarOTrabalho" in limpo
    assert '"/api/jobs"' in limpo
    assert "/events?limit=" in limpo


def test_o_console_deixa_copiar(js):
    """Ele precisou mandar o log três vezes e as três vezes teve de copiar da
    janela preta do .bat. Sem um botão, a única forma de contar um erro é
    digitar de novo olhando para a tela."""
    limpo = sem_comentario(js)
    assert "btnConsoleCopy" in limpo and "clipboard" in limpo


def test_o_console_nao_nasce_aberto(html, css):
    """Na primeira foto desta versão ele nasceu aberto tapando o canto da tela.
    O `hidden` do HTML perdia para o `display: flex` da classe."""
    assert 'id="consoleShell" hidden' in html
    assert ".console-shell[hidden] { display: none; }" in css


def test_o_trabalho_pode_ser_parado_de_dentro_do_console(js, html):
    """Meia hora de trabalho errado é meia hora. O botão de parar mora ao lado
    das linhas que mostram que está errado."""
    assert 'id="btnCancelWork"' in html
    limpo = sem_comentario(js)
    assert '"/api/process/cancel"' in limpo


def test_moer_registra_o_trabalho_no_motor(motor):
    """Defeito de verdade, encontrado quando o console ficou sem histórico:
    `/api/process/complete` era a única rota que não se registrava como tarefa
    ativa, e a própria função já contava com isso — o `finally` desligava um
    sinalizador que ninguém tinha ligado.

    Três consequências: nenhuma linha do processo completo virava histórico
    (justamente o processo que demora meia hora), a trava de "já tem coisa
    rodando" nunca fechava aqui, e o `finally` desligava o sinalizador de outra
    operação que estivesse rodando. A rota de corte já fazia certo.
    """
    trecho = motor[motor.find("def api_process_complete"):]
    trecho = trecho[:trecho.find('@app.route("/api/process/cancel"')]
    assert '_set_legacy_task("process_complete", active=True)' in trecho
    assert 'current_task["job_id"] = job["id"]' in trecho
    assert "with processing_lock:" in trecho, "a checagem ficou fora da trava"


# ── os blocos ───────────────────────────────────────────────────────────────


def test_os_blocos_vem_da_rota_do_motor(js):
    """Ele pediu de volta pelo nome."""
    limpo = sem_comentario(js)
    assert '"/api/editorial/blocks"' in limpo
    assert "carregarOsBlocos" in limpo


def test_o_bloco_nao_ganha_titulo_inventado(js):
    """O motor deixa `title` vazio de propósito: "No title: nobody wrote one.
    The position is a fact, a title is not." Preencher isso na tela seria uma
    mentira pequena que compõe."""
    limpo = sem_comentario(js)
    trecho = limpo[limpo.find("lista.innerHTML = blocos.map"):]
    trecho = trecho[:trecho.find("}).join")]
    assert "b.title" not in trecho, "a tela voltou a procurar um título que ninguém escreveu"
    assert "b.label" in trecho and "b.summary" in trecho


def test_a_tela_diz_se_o_bloco_passou_por_gente(js):
    """Bloco do acervo passou por revisão humana; bloco da leitura do Furia é
    palpite da máquina. A diferença é grande demais para ficar implícita."""
    limpo = sem_comentario(js)
    assert "REVISADO" in limpo and "LEITURA DO FURIA" in limpo
    assert "dados.reviewed" in limpo


def test_quando_nao_ha_bloco_quem_fala_e_o_motor(js):
    """A mensagem da rota diz o que FAZER — "a transcrição não rende trechos
    longos o bastante", "importe os blocos do Acervo deste vídeo". Trocar isso
    por um texto genérico meu seria jogar fora a única frase da tela que
    resolve o problema dele."""
    limpo = sem_comentario(js)
    trecho = limpo[limpo.find("if (!blocos.length)"):]
    trecho = trecho[:trecho.find("return;")]
    assert "dados.message" in trecho


# ── o painel ────────────────────────────────────────────────────────────────


def test_o_painel_le_o_espelho_e_nao_o_proprio_programa(js):
    """Tudo no painel é medição de FORA: desempenho de post publicado. Um
    número que a ferramenta gera sobre o que a ferramenta fez não mede nada, e
    é por isso que a nota do corte não entra aqui."""
    limpo = sem_comentario(js)
    assert "/api/painel?conta=" in limpo
    assert "Nada aqui saiu deste programa" in limpo
    trecho = limpo[limpo.find("function desenharOPainel"):]
    trecho = trecho[:trecho.find("\n  }")]
    assert "score" not in trecho.lower(), "a nota da máquina entrou no painel do que já rendeu"


def test_a_barra_do_painel_desenha_a_distancia_ate_um(js):
    """1,00× é o desempenho típico da própria conta. O que interessa é quanto
    um gancho se afasta disso; o valor bruto não diz se foi bom."""
    limpo = sem_comentario(js)
    trecho = limpo[limpo.find("function barra("):]
    trecho = trecho[:trecho.find("\n  }")]
    assert "valor - 1" in trecho
    assert "Math.min(50" in trecho, (
        "a barra do tema mais forte passava por cima da coluna do número e o "
        "valor sumia da tela"
    )


def test_a_barra_do_painel_e_fina_e_de_ponta_reta(css):
    """Barra grossa vira bloco de cor e a ponta arredondada esconde onde ela
    termina — e a ponta é o valor."""
    trecho = css[css.find(".barra {"):]
    trecho = trecho[:trecho.find("}")]
    assert "height: 10px" in trecho
    assert "border-radius" not in trecho


def test_o_nome_do_gancho_e_do_tema_aparecem(js):
    """Na primeira foto todas as linhas do painel mostravam só um traço: o
    espelho chama gancho de `familia` e tema de `slug`, e a tela procurava
    `gancho` e `tema`."""
    limpo = sem_comentario(js)
    assert "item.familia" in limpo and "item.slug" in limpo


# ── a tela dele tem 1366 por 768 ────────────────────────────────────────────


def test_a_mesa_inteira_cabe_na_tela_dele(css):
    """Na primeira foto a faixa de números caía debaixo da doca e dois dos
    quatro números ficavam tapados. O desenho supunha uma tela mais alta."""
    assert "@media (min-width: 781px) and (max-height: 840px)" in css
    trecho = css[css.find("@media (min-width: 781px) and (max-height: 840px)"):]
    trecho = trecho[:trecho.find("\n}")]
    assert ".desk-stage { min-height: 516px" in trecho


def test_a_revisao_cabe_na_tela_dele(css):
    """A onda é o controle do corte e ficava abaixo da dobra: ele teria de
    rolar a tela para alcançar justamente a coisa que mais usa."""
    assert '#screen-project[data-aba="review"] .review-frame' in css
    trecho = css[css.find('#screen-project[data-aba="review"] .review-frame'):]
    trecho = trecho[:trecho.find("}")]
    assert "vh" in trecho, "a altura do quadro voltou a ser fixa"


def test_o_nome_da_fonte_nao_come_meia_tela(css, js):
    """Nome de arquivo do YouTube tem sessenta caracteres. A 100px isso virava
    três linhas de manchete antes de aparecer qualquer coisa útil."""
    # A última que começa a linha: a folha tem a regra original do zip lá em
    # cima, a correção mais embaixo (que é a que o navegador aplica) e ainda
    # uma terceira só para a aba de revisão, que é outra coisa e não vale aqui.
    trecho = css[css.rfind("\n.project-heading h1 {"):]
    trecho = trecho[:trecho.find("}")]
    assert "line-clamp: 2" in trecho
    assert "clamp(28px" in trecho
    assert "semExtensao" in sem_comentario(js), "o .mp4 voltou para o título"


def test_o_empilhamento_solto_vale_so_no_palco_do_entender(css):
    """Sem o `.editor-grid >` a regra pegava toda janela com a classe, e as
    telas novas — ajustes, painel, blocos — nasciam com as janelas soltas uma
    por cima da outra."""
    assert ".editor-grid > .editor-window { position: absolute; }" in css
    assert "\n.editor-window { position: absolute; }" not in css


def test_a_janela_nasce_na_camada_que_o_desenho_escolheu(js):
    """`.wm-ready` punha um z-index só para todas, e aí quem ficava na frente
    passava a ser quem vem depois no HTML: foi assim que o quadro de sinal subiu
    por cima do título da mesa."""
    limpo = sem_comentario(js)
    trecho = limpo[limpo.find("function registrarJanela"):]
    trecho = trecho[:trecho.find("const barra =")]
    assert "getComputedStyle(elemento).zIndex" in trecho


def test_a_bandeja_so_mostra_janela_guardada(js):
    """Uma fileira de botões para janelas que já estão abertas não faz nada e
    ocupa uma faixa da tela o tempo todo — e na tela dele essa faixa cobria a
    linha de números da mesa."""
    limpo = sem_comentario(js)
    trecho = limpo[limpo.find("function esconder("):]
    trecho = trecho[:trecho.find("\n  }")]
    assert "bandeja().appendChild(item.aba)" in trecho
    assert "item.aba.remove()" in trecho


def test_a_pagina_nao_pede_favicon_que_nao_existe(html):
    """Sem o ícone escrito no próprio HTML o navegador pede um /favicon.ico que
    não existe e anota um erro a cada abertura. Erro falso é caro: é o tipo de
    linha que faz procurar defeito onde não tem."""
    assert 'rel="icon"' in html
    assert "data:image/svg+xml" in html


# ── nada sai desta máquina ──────────────────────────────────────────────────


def test_a_tela_nao_busca_nada_na_internet(html, js, css):
    """A máquina dele trabalha desligada. Um endereço de fora é uma tela que um
    dia não carrega e ele não vai saber por quê."""
    # O `xmlns` de um SVG parece endereço e não é: é o NOME do padrão, e o
    # navegador nunca vai buscá-lo. Marcar isso como "busca coisa de fora"
    # seria o teste reprovando justamente o ícone que existe para o navegador
    # PARAR de pedir um arquivo que não existe.
    def busca_de_fora(linha):
        sem_ns = re.sub(r"xmlns(:\w+)?=['\"][^'\"]*['\"]", "", linha)
        for fora in ("http://", "https://", "//cdn", "fonts.googleapis"):
            if fora in sem_ns and "127.0.0.1" not in sem_ns and "localhost" not in sem_ns:
                return True
        return False

    for nome, texto in (("estudio.html", html), ("app.js", js), ("app.css", css)):
        achados = [linha for linha in sem_comentario(texto).splitlines() if busca_de_fora(linha)]
        assert not achados, f"{nome} busca coisa de fora: {achados[:2]}"


def test_o_arquivo_do_corte_passa_pela_regra_do_motor(estudio):
    """Os cortes e as miniaturas não moram na pasta de trabalho — saem em
    `~/FuriaClipsData/exports`. A primeira versão montava um `/workspace/...`
    e todo cartão de corte aparecia sem foto.

    Quem já sabe servir arquivo de fora com a regra certa é a rota do motor:
    ela confere se o caminho está debaixo de uma pasta permitida. Uma regra só
    no programa inteiro, em vez de duas que um dia divergem.
    """
    assert not hasattr(estudio, "_relativo"), "voltou o atalho que só olhava a pasta de trabalho"
    assert estudio._arquivo("") == ""
    assert estudio._arquivo("/nao/existe/corte.mp4") == "", (
        "arquivo que não existe virou endereço na tela"
    )
    origem = (RAIZ / "estudio" / "app.py").read_text(encoding="utf-8")
    assert "/api/output_file?path=" in origem


def test_a_lista_de_fontes_nao_mistura_corte_pronto(estudio, tmp_path, monkeypatch):
    """Fonte é ENTRADA. Quando uma lista dessas leu o disco de verdade pela
    primeira vez ela devolveu 114 cortes exportados misturados com 5 fontes."""
    (tmp_path / "uploads").mkdir()
    (tmp_path / "exports").mkdir()
    (tmp_path / "processed").mkdir()
    (tmp_path / "uploads" / "entrevista.mp4").write_bytes(b"x")
    (tmp_path / "exports" / "corte-01.mp4").write_bytes(b"x")
    (tmp_path / "processed" / "corte-02.mp4").write_bytes(b"x")
    (tmp_path / "solta.mp4").write_bytes(b"x")

    monkeypatch.setattr(estudio, "WORKSPACE_DIR", str(tmp_path))
    chaves = {f["chave"] for f in estudio._fontes_no_disco()}

    assert "uploads/entrevista.mp4" in chaves
    assert "solta.mp4" in chaves
    assert not any("exports" in c or "processed" in c for c in chaves), (
        f"corte já pronto voltou para a lista de fontes: {sorted(chaves)}"
    )


def test_a_lista_de_fontes_nao_repete(estudio, tmp_path, monkeypatch):
    """A raiz e as pastas de entrada são varridas em sequência."""
    (tmp_path / "uploads").mkdir()
    (tmp_path / "uploads" / "a.mp4").write_bytes(b"x")
    (tmp_path / "b.mp4").write_bytes(b"x")
    monkeypatch.setattr(estudio, "WORKSPACE_DIR", str(tmp_path))
    chaves = [f["chave"] for f in estudio._fontes_no_disco()]
    assert len(chaves) == len(set(chaves)), f"vídeo repetido: {chaves}"


def test_a_fonte_de_fora_e_importada_e_nao_so_apontada(js):
    """Era isto que fazia "moer" falhar: o motor só aceita vídeo de dentro da
    pasta de trabalho — regra dele, e uma regra certa, porque senão qualquer
    página aberta no navegador poderia mandar o programa ler um arquivo
    qualquer do computador. Escolher na janela do Windows dá o caminho, não a
    permissão."""
    limpo = sem_comentario(js)
    assert '"/api/fonte/escolher"' in limpo
    assert "escolherNoWindows" in limpo


def test_o_erro_de_rede_vira_frase_e_nao_silencio(js):
    """"Failed to fetch" não é uma frase que resolve a tarde dele."""
    limpo = sem_comentario(js)
    trecho = limpo[limpo.find("async function pedir("):]
    trecho = trecho[:trecho.find("\n  }")]
    assert "O programa parou de responder" in trecho
