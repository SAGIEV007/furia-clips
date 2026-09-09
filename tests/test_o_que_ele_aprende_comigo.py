"""O motor aprendendo com o julgamento do editor — e as travas que impedem o pior.

O PEDIDO QUE ORIGINOU ISTO
--------------------------
    "quando eu mandar links de lives recentes, essas lives não vão estar no
     chub, então precisam ter aprendido padrões de cortes anteriores"

Um sistema que aprende é um sistema que pode aprender errado, e errado com
confiança. Estes testes são as travas: eles não perguntam se o aprendizado
funciona, perguntam se ele **se recusa** a funcionar quando a evidência é
fraca. Um motor que muda de opinião com três vereditos não aprendeu o padrão
dele — decorou o último clipe que ele reprovou.
"""

import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


def _caderno(tmp_path, vereditos, sinais_por_corte):
    """Monta um caderno e o manifesto que o acompanha."""
    pasta = tmp_path / "vereditos"
    pasta.mkdir(parents=True, exist_ok=True)
    linhas = []
    cortes = []
    for numero, (veredito, etiqueta) in enumerate(vereditos, start=1):
        linhas.append(f"2026-09-05 22:00 | r1 | #{numero} | {veredito} | {etiqueta} | motivo")
        cortes.append({"numero": str(numero), "sinais": sinais_por_corte})
    (pasta / "r1.txt").write_text("\n".join(linhas), encoding="utf-8")
    (pasta / "r1.manifesto.json").write_text(
        json.dumps({"rodada": "r1", "cortes": cortes}), encoding="utf-8"
    )
    return tmp_path


# ── 1. a trava da evidência fraca ───────────────────────────────────────────


def test_poucos_vereditos_nao_mexem_em_nada(monkeypatch, tmp_path):
    """Três reprovações não são um padrão; são três reprovações.

    Sem esta trava o motor viraria uma gangorra: cada rodada de revisão
    empurraria os pesos para o defeito daquela rodada, e o editor veria o
    programa piorar justamente por estar "aprendendo".

    ISOLAMENTO ACHADO RODANDO NA MÁQUINA DELE
    -------------------------------------------
    `ajustes(data_dir)` só isola a metade do caderno; a metade da tela
    (`ler_do_programa`, dentro de `tudo_que_ele_julgou`) sempre lê
    `config.DB_PATH` de verdade, sem jeito de apontar para outro lugar por
    fora. Na nuvem esse banco estava vazio, e o teste passava por acidente.
    Aqui é o banco real dele, com 169 vereditos — e os três exatamente do
    tipo que este teste finge não existir.
    """
    monkeypatch.setattr("config.DB_PATH", str(tmp_path / "sem-vereditos-na-tela.sqlite3"))
    from modules.aprendizado import ajustes

    dados = _caderno(tmp_path, [("nao", "fim")] * 3, {"payoff_complete": True})
    assert ajustes(dados) == {}


def test_com_casos_suficientes_o_peso_se_move(tmp_path):
    """O caso da skill do caderno, que é o motivo de tudo isto existir:
    cortes marcados 'final cortado' em que o motor tinha dito 'fecho completo'."""
    from modules.aprendizado import ajustes

    dados = _caderno(tmp_path, [("nao", "fim")] * 10, {"payoff_complete": True})
    movidos = ajustes(dados)

    assert "termina_sem_fechar" in movidos, (
        "dez vezes o editor viu o defeito e o motor não; o desconto tem que subir"
    )
    assert movidos["termina_sem_fechar"] > 0


def test_o_motor_exagerando_faz_o_desconto_descer(monkeypatch, tmp_path):
    """A direção contrária, que é a que ninguém lembra de testar.

    Se o motor acusa um defeito e o editor aprova o corte assim mesmo, o
    desconto está caro demais — e um aprendizado que só sabe apertar acaba
    reprovando tudo.
    """
    monkeypatch.setattr("config.DB_PATH", str(tmp_path / "sem-vereditos-na-tela.sqlite3"))
    from modules.aprendizado import ajustes

    dados = _caderno(tmp_path, [("ok", "")] * 10, {"payoff_complete": False})
    movidos = ajustes(dados)

    assert movidos.get("termina_sem_fechar", 0) < 0


def test_nenhum_ajuste_passa_do_teto(tmp_path):
    """Mesmo com cem vereditos no mesmo sentido.

    Um peso sem teto deixa de ser desempate e vira a decisão inteira: um único
    sinal passaria a decidir sozinho o que é corte e o que não é.
    """
    from modules.aprendizado import TETO, ajustes

    dados = _caderno(tmp_path, [("nao", "fim")] * 100, {"payoff_complete": True})
    for valor in ajustes(dados).values():
        assert abs(valor) <= TETO


def test_veredito_sem_manifesto_nao_ensina_nada(monkeypatch, tmp_path):
    """Reclamação sem endereço não conserta parafuso.

    Sem o manifesto sabe-se que ele reprovou, não o que o motor tinha achado
    daquele corte — e é a diferença entre os dois que diz onde está o erro.
    """
    monkeypatch.setattr("config.DB_PATH", str(tmp_path / "sem-vereditos-na-tela.sqlite3"))
    from modules.aprendizado import ajustes

    pasta = tmp_path / "vereditos"
    pasta.mkdir(parents=True)
    (pasta / "r1.txt").write_text(
        "\n".join(f"2026-09-05 22:00 | r1 | #{n} | nao | fim | final cortado"
                  for n in range(1, 21)),
        encoding="utf-8",
    )
    assert ajustes(tmp_path) == {}


# ── 2. o último veredito vale, e o histórico fica ───────────────────────────


def test_ele_pode_mudar_de_ideia(tmp_path):
    """O caderno só acrescenta linha. A última vale; as anteriores ficam."""
    from modules.aprendizado import ler_vereditos

    pasta = tmp_path / "vereditos"
    pasta.mkdir(parents=True)
    (pasta / "r1.txt").write_text(
        "2026-09-05 22:00 | r1 | #3 | nao | fim | final cortado\n"
        "2026-09-05 22:30 | r1 | #3 | ok  |     | pensei melhor\n",
        encoding="utf-8",
    )
    lidos = ler_vereditos(tmp_path)
    assert len(lidos) == 1
    assert lidos[0]["veredito"] == "ok"


# ── 3. os cortes dele viram régua ───────────────────────────────────────────


def test_o_corte_dele_vira_gabarito(tmp_path):
    """A peça que resolve a live recente.

    O Acervo não tem o vídeo de ontem. Ele tem, porque cortou — e o começo e o
    fim que ele escolheu são a resposta certa para aquele vídeo.
    """
    from modules.aprendizado import gabarito_do_editor

    pasta = tmp_path / "cortes_do_editor"
    pasta.mkdir(parents=True)
    (pasta / "set.txt").write_text(
        "2026-09-05 14:02 | vid1 | 400.0 | 455.0 | segunda headline\n"
        "2026-09-05 14:09 | vid1 | 120.0 | 178.5 | primeira headline\n"
        "2026-09-05 14:11 | vid2 | 10.0  | 40.0  | de outro vídeo\n",
        encoding="utf-8",
    )
    blocos = gabarito_do_editor("vid1", tmp_path)

    assert len(blocos) == 2, "só os cortes daquele vídeo"
    assert blocos[0]["start"] == 120.0, "em ordem de tempo, não de digitação"
    assert blocos[0]["titulo"] == "primeira headline"
    assert all(b["fonte_do_gabarito"] == "editor" for b in blocos), (
        "a régua precisa saber de quem é a resposta certa; chamar de Acervo "
        "o julgamento do editor apagaria a única coisa que distingue os dois"
    )


def test_corte_invertido_e_ignorado(tmp_path):
    """Fim antes do começo é erro de digitação no WhatsApp, não gabarito."""
    from modules.aprendizado import ler_cortes_do_editor

    pasta = tmp_path / "cortes_do_editor"
    pasta.mkdir(parents=True)
    (pasta / "set.txt").write_text(
        "2026-09-05 14:02 | vid1 | 455.0 | 400.0 | invertido\n"
        "2026-09-05 14:03 | vid1 | isso  | nao   | nem número é\n"
        "2026-09-05 14:04 | vid1 | 100.0 | 160.0 | este presta\n",
        encoding="utf-8",
    )
    cortes = ler_cortes_do_editor(tmp_path)
    assert len(cortes) == 1
    assert cortes[0]["start"] == 100.0


# ── 4. o motor de verdade lê o que foi aprendido ────────────────────────────


def test_o_ranqueador_usa_o_ajuste_do_editor(monkeypatch):
    """Não basta calcular o número: ele tem que chegar na nota.

    Este teste existe porque o mesmo defeito já aconteceu neste projeto — os
    pesos do CHUB estavam no disco há semanas e nenhum arquivo os lia.
    """
    from modules.editorial_ranker import EditorialRanker

    monkeypatch.setattr(EditorialRanker, "_PESOS_DO_ESPELHO", {}, raising=False)
    monkeypatch.setattr(EditorialRanker, "_APRENDIDO", {}, raising=False)
    padrao = EditorialRanker._peso("termina_sem_fechar", 12)

    monkeypatch.setattr(EditorialRanker, "_APRENDIDO", {"termina_sem_fechar": 25.0})
    aprendido = EditorialRanker._peso("termina_sem_fechar", 12)

    assert aprendido > padrao, "o julgamento dele não chegou até a nota"


def test_sem_caderno_nada_muda(monkeypatch):
    """O caderno vazio é o estado normal no primeiro dia.

    Uma máquina que só funciona depois de treinada não serve para ele: ele
    precisa cortar hoje, com o caderno vazio, e melhorar depois.
    """
    from modules.editorial_ranker import EditorialRanker

    monkeypatch.setattr(EditorialRanker, "_PESOS_DO_ESPELHO", {}, raising=False)
    monkeypatch.setattr(EditorialRanker, "_APRENDIDO", {}, raising=False)

    assert EditorialRanker._peso("termina_sem_fechar", 12) == 12
    assert EditorialRanker._peso("abre_sem_afirmar", 45) == 45


@pytest.mark.parametrize("peso,padrao", [
    ("abre_sem_afirmar", 45),
    ("comeca_no_meio_da_frase", 14),
    ("termina_sem_fechar", 12),
    ("repeticao", 22),
    ("contexto_incompleto", 8),
])
def test_todo_defeito_que_ele_etiqueta_tem_um_peso_ajustavel(peso, padrao, monkeypatch):
    """Cada etiqueta do WhatsApp precisa ter para onde ir.

    Uma etiqueta sem peso correspondente é feedback que ele dá e o programa
    joga fora — e ele não teria como saber que jogou.
    """
    from modules.editorial_ranker import EditorialRanker

    monkeypatch.setattr(EditorialRanker, "_PESOS_DO_ESPELHO", {}, raising=False)
    monkeypatch.setattr(EditorialRanker, "_APRENDIDO", {peso: 20.0}, raising=False)

    assert EditorialRanker._peso(peso, padrao) > padrao


def test_toda_etiqueta_do_caderno_chega_num_peso():
    """A ponte entre o WhatsApp e o motor não pode ter buraco."""
    from modules.aprendizado import O_QUE_CADA_ETIQUETA_CORRIGE

    caderno = RAIZ / "docs" / "hermes" / "skills" / "caderno-de-vereditos.md"
    texto = caderno.read_text(encoding="utf-8")
    for etiqueta in ("fim", "abertura", "locutor", "contexto", "repetido"):
        assert f"`{etiqueta}`" in texto, f"a skill não ensina a etiqueta {etiqueta}"
        assert etiqueta in O_QUE_CADA_ETIQUETA_CORRIGE, (
            f"ele pode etiquetar '{etiqueta}' e o motor não sabe o que fazer com isso"
        )


# ── 5. trabalhando sozinho, sem o Hermes ────────────────────────────────────


def test_o_veredito_dado_na_tela_ensina_igual(tmp_path, monkeypatch):
    """A fonte principal quando ele trabalha sem agente nenhum.

    Ele já aperta Aprovar/Rejeitar e escolhe o motivo na lista da tela, e o
    programa já guarda isso junto com os sinais do motor. O "manifesto" que o
    Hermes precisa escrever à mão, aqui existe de graça: `score_factors` está
    na mesma linha do corte.
    """
    import sqlite3

    banco = tmp_path / "b.sqlite3"
    conn = sqlite3.connect(banco)
    conn.executescript(
        "CREATE TABLE projects (id INTEGER PRIMARY KEY, source_signature TEXT);"
        "INSERT INTO projects VALUES (1, 'v');"
        "CREATE TABLE clips (id INTEGER PRIMARY KEY, project_id INTEGER DEFAULT 1,"
        " start_time REAL, end_time REAL, score_factors TEXT);"
        "CREATE TABLE clip_feedback (id INTEGER PRIMARY KEY, clip_id INTEGER,"
        " action TEXT, reason_code TEXT);"
    )
    for numero in range(1, 11):
        conn.execute("INSERT INTO clips (id, project_id, start_time, end_time,"
                     " score_factors) VALUES (?,1,?,?,?)",
                     (numero, numero * 100.0, numero * 100.0 + 60,
                      json.dumps({"payoff_complete": True})))
        conn.execute("INSERT INTO clip_feedback (clip_id, action, reason_code) VALUES (?,?,?)",
                     (numero, "rejected", "no_payoff"))
    conn.commit()
    conn.close()

    monkeypatch.setattr("config.DB_PATH", str(banco))
    from modules.aprendizado import ajustes, ler_do_programa

    vereditos, sinais = ler_do_programa()
    assert len(vereditos) == 10
    assert vereditos[0]["etiqueta"] == "fim", (
        "'Não conclui o raciocínio' na tela é a mesma coisa que 'fim' no WhatsApp"
    )
    assert sinais[("programa", "1")]["sinais"]["payoff_complete"] is True

    movidos = ajustes(tmp_path)
    assert movidos.get("termina_sem_fechar", 0) > 0


def test_os_sinais_vem_do_formato_que_o_motor_grava_de_verdade(tmp_path, monkeypatch):
    """O aprendizado lia a gaveta errada, e noventa vereditos não moveram nada.

    O teste acima monta `score_factors` como `{"payoff_complete": True}` — plano.
    **O motor não grava assim.** Ele guarda duas coisas diferentes no mesmo
    lugar: as NOTAS do ranqueamento na raiz (hook, flow, value, clarity...) e as
    MARCAS do corte dentro de `_review_flags`. E este arquivo só olhava a raiz.

    Medido no banco do editor em 08/09, com 90 vereditos dados por ele na tela:

        manifestos lidos ....... 90
        casos contados .......... 0    <- nenhum sinal batia
        ajustes no motor ....... {}

    Ele apertou Aprovar e Rejeitar noventa vezes e o motor não mudou uma
    vírgula, sem nenhum erro aparecer na tela. Depois do conserto, o mesmo banco
    dá +20% em 'começa no meio da frase', +20% em 'termina sem fechar' e +16,7%
    em 'contexto incompleto' — que são exatamente as três etiquetas que ele mais
    usou (starts_late 14, no_payoff 13, missing_context 10).

    Este teste usa o formato REAL. O de cima usa um simplificado, e foi por isso
    que ele passou o tempo todo enquanto a coisa não funcionava.
    """
    import sqlite3

    banco = tmp_path / "b.sqlite3"
    conn = sqlite3.connect(banco)
    conn.executescript(
        "CREATE TABLE projects (id INTEGER PRIMARY KEY, source_signature TEXT);"
        "INSERT INTO projects VALUES (1, 'v');"
        "CREATE TABLE clips (id INTEGER PRIMARY KEY, project_id INTEGER DEFAULT 1,"
        " start_time REAL, end_time REAL, score_factors TEXT);"
        "CREATE TABLE clip_feedback (id INTEGER PRIMARY KEY, clip_id INTEGER,"
        " action TEXT, reason_code TEXT);"
    )
    # O formato de verdade: notas na raiz, marcas em `_review_flags`.
    como_o_motor_grava = {
        "hook": 72, "flow": 65, "value": 80, "clarity": 70,
        "_review_flags": {
            "payoff_complete": True,
            "starts_mid_sentence": False,
            "context_complete": True,
            "overlap_suspected": False,
        },
        "_review_metadata": {"selection_source": "gemini"},
    }
    for numero in range(1, 11):
        conn.execute("INSERT INTO clips (id, project_id, start_time, end_time,"
                     " score_factors) VALUES (?,1,?,?,?)",
                     (numero, numero * 100.0, numero * 100.0 + 60,
                      json.dumps(como_o_motor_grava)))
        conn.execute("INSERT INTO clip_feedback (clip_id, action, reason_code) VALUES (?,?,?)",
                     (numero, "rejected", "no_payoff"))
    conn.commit()
    conn.close()

    monkeypatch.setattr("config.DB_PATH", str(banco))
    from modules.aprendizado import ajustes, ler_do_programa

    _, sinais = ler_do_programa()
    assert sinais[("programa", "1")]["sinais"]["payoff_complete"] is True, (
        "a marca está dentro de _review_flags; sem entrar lá, nada é contado"
    )
    assert sinais[("programa", "1")]["sinais"]["hook"] == 72, (
        "as notas da raiz continuam valendo — as duas gavetas contam"
    )

    movidos = ajustes(tmp_path)
    assert movidos.get("termina_sem_fechar", 0) > 0, (
        "dez rejeições por 'não conclui' têm que mover o peso do fecho"
    )


def test_ele_muda_de_ideia_na_tela_tambem(tmp_path, monkeypatch):
    """Apertar Rejeitar e depois Aprovar: vale o último, como no caderno."""
    import sqlite3

    banco = tmp_path / "b.sqlite3"
    conn = sqlite3.connect(banco)
    conn.executescript(
        "CREATE TABLE projects (id INTEGER PRIMARY KEY, source_signature TEXT);"
        "INSERT INTO projects VALUES (1, 'v');"
        "CREATE TABLE clips (id INTEGER PRIMARY KEY, project_id INTEGER DEFAULT 1,"
        " start_time REAL, end_time REAL, score_factors TEXT);"
        "CREATE TABLE clip_feedback (id INTEGER PRIMARY KEY, clip_id INTEGER,"
        " action TEXT, reason_code TEXT);"
    )
    conn.execute("INSERT INTO clips (id, project_id, start_time, end_time,"
                 " score_factors) VALUES (1,1,10.0,70.0,'{}')")
    conn.execute("INSERT INTO clip_feedback (clip_id, action, reason_code) VALUES (1,'rejected','no_payoff')")
    conn.execute("INSERT INTO clip_feedback (clip_id, action, reason_code) VALUES (1,'approved','')")
    conn.commit()
    conn.close()

    monkeypatch.setattr("config.DB_PATH", str(banco))
    from modules.aprendizado import ler_do_programa

    vereditos, _ = ler_do_programa()
    assert len(vereditos) == 1
    assert vereditos[0]["veredito"] == "ok"


def test_sem_banco_nada_quebra(tmp_path, monkeypatch):
    """Primeira execução numa máquina nova: não há banco, e isso é normal."""
    monkeypatch.setattr("config.DB_PATH", str(tmp_path / "nao_existe.sqlite3"))
    from modules.aprendizado import ler_do_programa

    assert ler_do_programa() == ([], {})


def test_todo_motivo_da_tela_chega_num_peso():
    """A lista de motivos da tela não pode ter opção que o motor ignora.

    Ele escolhe um motivo achando que está ensinando alguma coisa. Se aquele
    motivo não leva a peso nenhum, o programa jogou fora o trabalho dele — e ele
    não teria como saber.
    """
    from modules.aprendizado import O_MENU_DA_TELA, O_QUE_CADA_ETIQUETA_CORRIGE

    tela = (RAIZ / "static" / "js" / "app.js").read_text(encoding="utf-8")
    for codigo, etiqueta in O_MENU_DA_TELA.items():
        assert f'"{codigo}"' in tela, f"o motivo {codigo} sumiu da lista da tela"
        assert etiqueta in O_QUE_CADA_ETIQUETA_CORRIGE, (
            f"'{codigo}' está na tela e não chega em peso nenhum"
        )


def test_aprovar_marcando_o_defeito_nao_afrouxa_o_desconto(tmp_path, monkeypatch):
    """A resposta dele em 08/09, quando perguntei o que aquilo queria dizer.

        eu: "quando você aprova marcando um defeito, quer dizer 'tem o defeito
             mas serve' ou 'o motor errou'?"
        ele: **"tem o defeito, mas dá para usar"**

    Ele concorda com o diagnóstico e publica assim mesmo. A regra antiga contava
    isso como alarme falso — e alarme falso AFROUXA o desconto. Ou seja: ele
    confirmava que o defeito existe e o motor passava a se importar menos com
    ele, que é o oposto exato do que ele quis dizer.

    No banco dele são oito casos: aprovou marcando `starts_late` três vezes,
    `no_payoff` uma, `too_long` quatro. Hoje o número não muda, porque o motor
    não tinha acusado nenhum deles — este teste existe para o dia em que tiver.
    """
    import sqlite3

    banco = tmp_path / "b.sqlite3"
    conn = sqlite3.connect(banco)
    conn.executescript(
        "CREATE TABLE projects (id INTEGER PRIMARY KEY, source_signature TEXT);"
        "INSERT INTO projects VALUES (1, 'v');"
        "CREATE TABLE clips (id INTEGER PRIMARY KEY, project_id INTEGER DEFAULT 1,"
        " start_time REAL, end_time REAL, score_factors TEXT);"
        "CREATE TABLE clip_feedback (id INTEGER PRIMARY KEY, clip_id INTEGER,"
        " action TEXT, reason_code TEXT);"
    )
    # O motor ACUSOU o defeito (payoff_complete falso) e ele aprovou assim
    # mesmo, marcando o mesmo defeito: "tem, mas dá para usar".
    motor_acusou = json.dumps({"_review_flags": {"payoff_complete": False}})
    for numero in range(1, 11):
        conn.execute("INSERT INTO clips (id, project_id, start_time, end_time,"
                     " score_factors) VALUES (?,1,?,?,?)",
                     (numero, numero * 100.0, numero * 100.0 + 60, motor_acusou))
        conn.execute("INSERT INTO clip_feedback (clip_id, action, reason_code)"
                     " VALUES (?,?,?)", (numero, "approved", "no_payoff"))
    conn.commit()
    conn.close()

    monkeypatch.setattr("config.DB_PATH", str(banco))
    from modules.aprendizado import _acertos_e_erros, ler_do_programa

    contas = _acertos_e_erros(*ler_do_programa())
    self_conta = contas["termina_sem_fechar"]
    assert self_conta["alarme_falso"] == 0, (
        "ele confirmou o defeito ao marcá-lo; isso não é o motor exagerando"
    )


def test_aprovar_SEM_apontar_o_defeito_continua_sendo_alarme_falso(tmp_path, monkeypatch):
    """O caso legítimo: o motor viu problema onde ele não viu.

    Sem esta metade, o desconto só saberia subir, e um sinal mal calibrado para
    cima nunca mais desceria.
    """
    import sqlite3

    banco = tmp_path / "b.sqlite3"
    conn = sqlite3.connect(banco)
    conn.executescript(
        "CREATE TABLE projects (id INTEGER PRIMARY KEY, source_signature TEXT);"
        "INSERT INTO projects VALUES (1, 'v');"
        "CREATE TABLE clips (id INTEGER PRIMARY KEY, project_id INTEGER DEFAULT 1,"
        " start_time REAL, end_time REAL, score_factors TEXT);"
        "CREATE TABLE clip_feedback (id INTEGER PRIMARY KEY, clip_id INTEGER,"
        " action TEXT, reason_code TEXT);"
    )
    motor_acusou = json.dumps({"_review_flags": {"payoff_complete": False}})
    for numero in range(1, 11):
        conn.execute("INSERT INTO clips (id, project_id, start_time, end_time,"
                     " score_factors) VALUES (?,1,?,?,?)",
                     (numero, numero * 100.0, numero * 100.0 + 60, motor_acusou))
        conn.execute("INSERT INTO clip_feedback (clip_id, action, reason_code)"
                     " VALUES (?,?,?)", (numero, "approved", "excellent_context"))
    conn.commit()
    conn.close()

    monkeypatch.setattr("config.DB_PATH", str(banco))
    from modules.aprendizado import _acertos_e_erros, ajustes, ler_do_programa

    contas = _acertos_e_erros(*ler_do_programa())
    assert contas["termina_sem_fechar"]["alarme_falso"] == 10
    assert ajustes(tmp_path).get("termina_sem_fechar", 0) < 0, "o desconto tem que descer"


# ── 5. as bordas que ele move na tela viram gabarito ────────────────────────


def _banco_com_ajuste(tmp_path, ajuste, nota="", assinatura="live-do-ceara"):
    import sqlite3

    banco = tmp_path / "b.sqlite3"
    conn = sqlite3.connect(banco)
    conn.executescript(
        "CREATE TABLE projects (id INTEGER PRIMARY KEY, source_signature TEXT, source_video TEXT);"
        "CREATE TABLE clips (id INTEGER PRIMARY KEY, project_id INTEGER,"
        " start_time REAL, end_time REAL, score_factors TEXT);"
        "CREATE TABLE clip_feedback (id INTEGER PRIMARY KEY, clip_id INTEGER, action TEXT,"
        " adjustments TEXT, note TEXT, created_at TEXT, reason_code TEXT);"
    )
    conn.execute("INSERT INTO projects VALUES (1,?,?)", (assinatura, "C:/v/live.mp4"))
    conn.execute("INSERT INTO clips VALUES (1,1,100.0,200.0,'{}')")
    conn.execute(
        "INSERT INTO clip_feedback (clip_id,action,adjustments,note,created_at,reason_code)"
        " VALUES (1,'adjusted',?,?,?,'')",
        (json.dumps(ajuste), nota, "2026-09-08 13:00:00"))
    conn.commit()
    conn.close()
    return banco


def test_a_borda_que_ele_move_vira_gabarito(tmp_path, monkeypatch):
    """A escolha dele em 08/09, quando perguntei como preferia corrigir.

    "arrastar as bordas do corte na tela" — e ele estava certo: o programa já
    grava começo e fim corrigidos, e ninguém lia. No banco dele há cinco linhas
    `adjusted`, todas com start igual a original_start.

    Uma etiqueta diz que existe defeito. **Uma borda movida diz onde estava o
    certo** — e numa live que o Acervo não catalogou é a única resposta certa
    que existe no mundo.
    """
    banco = _banco_com_ajuste(tmp_path, {
        "start": 100.0, "end": 184.0,
        "original_start": 100.0, "original_end": 200.0,
    }, nota="acabava no meio da pergunta do repórter")
    monkeypatch.setattr("config.DB_PATH", str(banco))
    from modules.aprendizado import cortes_ajustados_no_programa, gabarito_do_editor

    movidos = cortes_ajustados_no_programa()
    assert len(movidos) == 1
    assert movidos[0]["end"] == 184.0
    assert movidos[0]["movido_no_fim_s"] == -16.0, "encurtou dezesseis segundos"

    blocos = gabarito_do_editor("live-do-ceara", tmp_path)
    assert len(blocos) == 1
    assert blocos[0]["end"] == 184.0
    assert blocos[0]["fonte_do_gabarito"] == "editor"


def test_salvar_sem_mexer_nao_e_gabarito(tmp_path, monkeypatch):
    """As cinco linhas do banco dele são exatamente este caso.

    Contar isso como correção seria o programa se elogiando com o próprio
    palpite — o que a regra do NORTE §15 proíbe.
    """
    banco = _banco_com_ajuste(tmp_path, {
        "start": 100.0, "end": 200.0,
        "original_start": 100.0, "original_end": 200.0,
    })
    monkeypatch.setattr("config.DB_PATH", str(banco))
    from modules.aprendizado import cortes_ajustados_no_programa

    assert cortes_ajustados_no_programa() == []


def test_borda_invertida_ou_ilegivel_e_ignorada(tmp_path, monkeypatch):
    banco = _banco_com_ajuste(tmp_path, {
        "start": 200.0, "end": 100.0,
        "original_start": 100.0, "original_end": 200.0,
    })
    monkeypatch.setattr("config.DB_PATH", str(banco))
    from modules.aprendizado import cortes_ajustados_no_programa

    assert cortes_ajustados_no_programa() == []


def test_sem_banco_nenhum_nada_quebra(tmp_path, monkeypatch):
    monkeypatch.setattr("config.DB_PATH", str(tmp_path / "nao-existe.sqlite3"))
    from modules.aprendizado import cortes_ajustados_no_programa, gabarito_do_editor

    assert cortes_ajustados_no_programa() == []
    assert gabarito_do_editor("qualquer", tmp_path) == []


def test_o_mesmo_trecho_julgado_duas_vezes_conta_uma(tmp_path, monkeypatch):
    """O defeito que a primeira importação dele deixou no banco.

    Agrupar por `clip_id` parece certo e não é. Um trecho ganha linha de corte
    nova toda vez que a fonte é moída de novo, e ganha outra quando o veredito
    vem importado de outro computador — três linhas para o mesmo julgamento
    sobre o mesmo pedaço de vídeo.

    Medido no banco dele em 08/09, depois da primeira importação:

        177 vereditos finais · 14 trechos julgados duas vezes
        contando por trecho: 159

    Nenhum é repetição exata (a hora difere), então a peneira da importação não
    os pega. E como a inflação é toda no mesmo sentido, as porcentagens quase
    não se mexem — que é o que torna o erro invisível.
    """
    import sqlite3

    banco = tmp_path / "b.sqlite3"
    conn = sqlite3.connect(banco)
    conn.executescript(
        "CREATE TABLE projects (id INTEGER PRIMARY KEY, source_signature TEXT);"
        "INSERT INTO projects VALUES (1, 'video-a');"
        "INSERT INTO projects VALUES (2, 'video-a');"   # o mesmo vídeo, importado
        "CREATE TABLE clips (id INTEGER PRIMARY KEY, project_id INTEGER,"
        " start_time REAL, end_time REAL, score_factors TEXT);"
        "CREATE TABLE clip_feedback (id INTEGER PRIMARY KEY, clip_id INTEGER,"
        " action TEXT, reason_code TEXT);"
    )
    sinais = json.dumps({"_review_flags": {"payoff_complete": True}})
    # O MESMO trecho (100–160) em duas linhas de corte: uma daqui, uma importada.
    conn.execute("INSERT INTO clips VALUES (1,1,100.0,160.0,?)", (sinais,))
    conn.execute("INSERT INTO clips VALUES (2,2,100.0,160.0,?)", (sinais,))
    conn.execute("INSERT INTO clip_feedback (clip_id,action,reason_code)"
                 " VALUES (1,'rejected','no_payoff')")
    conn.execute("INSERT INTO clip_feedback (clip_id,action,reason_code)"
                 " VALUES (2,'rejected','no_payoff')")
    conn.commit()
    conn.close()

    monkeypatch.setattr("config.DB_PATH", str(banco))
    from modules.aprendizado import ler_do_programa

    vereditos, _ = ler_do_programa()
    assert len(vereditos) == 1, (
        "o mesmo trecho julgado duas vezes é um julgamento, não dois"
    )


def test_trechos_diferentes_do_mesmo_video_continuam_contando_separado(tmp_path, monkeypatch):
    """A metade que impede o conserto de virar outro defeito."""
    import sqlite3

    banco = tmp_path / "b.sqlite3"
    conn = sqlite3.connect(banco)
    conn.executescript(
        "CREATE TABLE projects (id INTEGER PRIMARY KEY, source_signature TEXT);"
        "INSERT INTO projects VALUES (1, 'video-a');"
        "CREATE TABLE clips (id INTEGER PRIMARY KEY, project_id INTEGER,"
        " start_time REAL, end_time REAL, score_factors TEXT);"
        "CREATE TABLE clip_feedback (id INTEGER PRIMARY KEY, clip_id INTEGER,"
        " action TEXT, reason_code TEXT);"
    )
    sinais = json.dumps({"_review_flags": {"payoff_complete": True}})
    for numero, inicio in enumerate([100.0, 300.0, 500.0], start=1):
        conn.execute("INSERT INTO clips VALUES (?,1,?,?,?)",
                     (numero, inicio, inicio + 60, sinais))
        conn.execute("INSERT INTO clip_feedback (clip_id,action,reason_code)"
                     " VALUES (?,'rejected','no_payoff')", (numero,))
    conn.commit()
    conn.close()

    monkeypatch.setattr("config.DB_PATH", str(banco))
    from modules.aprendizado import ler_do_programa

    assert len(ler_do_programa()[0]) == 3
