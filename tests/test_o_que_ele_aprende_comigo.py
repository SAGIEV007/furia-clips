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


def test_poucos_vereditos_nao_mexem_em_nada(tmp_path):
    """Três reprovações não são um padrão; são três reprovações.

    Sem esta trava o motor viraria uma gangorra: cada rodada de revisão
    empurraria os pesos para o defeito daquela rodada, e o editor veria o
    programa piorar justamente por estar "aprendendo".
    """
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


def test_o_motor_exagerando_faz_o_desconto_descer(tmp_path):
    """A direção contrária, que é a que ninguém lembra de testar.

    Se o motor acusa um defeito e o editor aprova o corte assim mesmo, o
    desconto está caro demais — e um aprendizado que só sabe apertar acaba
    reprovando tudo.
    """
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


def test_veredito_sem_manifesto_nao_ensina_nada(tmp_path):
    """Reclamação sem endereço não conserta parafuso.

    Sem o manifesto sabe-se que ele reprovou, não o que o motor tinha achado
    daquele corte — e é a diferença entre os dois que diz onde está o erro.
    """
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
