"""O trabalho que ficou de pé depois que o programa morreu.

O editor baixou uma versão nova, abriu, e o console dele mostrou isto:

    18:28:57  Aguardando execução
    18:28:57  Criando projeto
    18:28:57  ━━━ ETAPA 1/6: Removendo Silencio ━━━
    18:35:29  Encontrados 3 periodos de silencio (58.1s total)
    18:35:29  Processando 4 segmentos de fala...
    16:28:57  — daqui para baixo é ao vivo —
    16:29:15  Pedido de parada enviado. O motor para no próximo passo.
    16:30:40  Pedido de parada enviado. O motor para no próximo passo.
    16:30:41  Pedido de parada enviado. O motor para no próximo passo.
    16:30:42  Pedido de parada enviado. O motor para no próximo passo.

E resumiu: *"não faz sentido para mim baixar uma nova versão e constar o
trabalho antigo em andamento; para mim o vídeo sequer deveria estar lá"*.

Três defeitos numa tela só, e os três meus:

  1. o trabalho era de três horas antes, de OUTRA versão do programa (o rótulo
     "Removendo Silencio" nem existe mais), e apareceu como se estivesse
     rodando;
  2. a história veio em UTC e o ao vivo em hora local — três horas para trás no
     meio da lista;
  3. o botão de parar prometeu cinco vezes uma coisa que não tinha como fazer,
     porque não havia worker nenhum para parar.
"""

import re
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
JS = (RAIZ / "estudio" / "static" / "app.js").read_text(encoding="utf-8")


def sem_comentario(fonte):
    """O texto sem os comentários — que aqui contam o defeito por extenso."""
    sem_bloco = re.sub(r"/\*.*?\*/", "", fonte, flags=re.S)
    return "\n".join(
        linha for linha in sem_bloco.splitlines()
        if not linha.lstrip().startswith("//")
    )


@pytest.fixture()
def banco():
    with tempfile.TemporaryDirectory() as pasta:
        yield str(Path(pasta) / "jobs.sqlite3")


# ── 1. o fantasma ───────────────────────────────────────────────────────────


def test_abrir_o_programa_enterra_o_trabalho_do_uso_anterior(banco):
    """Os trabalhos rodam num executor em memória, dentro deste processo.
    Nenhum sobrevive a fechar e abrir o programa — então toda linha que ainda
    diga "rodando" na abertura é de um processo que já morreu.

    Antes havia uma janela de doze horas de inatividade antes de enterrar. Ela
    protegia contra uma coisa que não pode acontecer, e cobrava isto: o
    trabalho de três horas antes reaparecendo como "em andamento" numa versão
    recém-baixada.
    """
    from modules.job_manager import JobManager

    velho = JobManager(banco, max_workers=1)
    try:
        trabalho = velho.create("moagem")
        velho.update(trabalho["id"], state="running", stage="silence", progress=15)
    finally:
        velho.shutdown()

    # O programa novo abrindo, com o mesmo banco de dados na mesma pasta.
    novo = JobManager(banco, max_workers=1)
    try:
        enterrados = novo.reconcile_stale()
        assert len(enterrados) == 1, "o trabalho do uso anterior continuou de pé"
        estado = novo.get(trabalho["id"])
        assert estado["state"] == "failed"
        assert estado["error"] == "stale_job_recovered"
        assert "uso anterior" in estado["message"], (
            "a mensagem tem de dizer o que aconteceu, em português dele"
        )
    finally:
        novo.shutdown()


def test_enterra_mesmo_o_trabalho_de_um_minuto_atras(banco):
    """A idade não importa: o que importa é que o processo dono morreu.

    Um minuto ou doze horas dá no mesmo — o executor é em memória. Este teste
    existe porque a versão anterior olhava para o relógio em vez de olhar para
    o fato.
    """
    from modules.job_manager import JobManager

    gerente = JobManager(banco, max_workers=1)
    try:
        trabalho = gerente.create("moagem")
        gerente.update(trabalho["id"], state="running", progress=3)
        conexao = sqlite3.connect(banco)
        conexao.execute(
            "UPDATE jobs SET updated_at = ? WHERE id = ?",
            (datetime.fromtimestamp(time.time() - 60, timezone.utc).isoformat(), trabalho["id"]),
        )
        conexao.commit()
        conexao.close()

        assert len(gerente.reconcile_stale()) == 1
        assert gerente.get(trabalho["id"])["state"] == "failed"
    finally:
        gerente.shutdown()


def test_o_trabalho_ja_terminado_nao_e_mexido(banco):
    """Enterrar é só para quem ficou de pé. O que já acabou fica como está."""
    from modules.job_manager import JobManager

    gerente = JobManager(banco, max_workers=1)
    try:
        pronto = gerente.create("moagem")
        gerente.update(pronto["id"], state="completed", progress=100)
        assert gerente.reconcile_stale() == []
        assert gerente.get(pronto["id"])["state"] == "completed"
    finally:
        gerente.shutdown()


def test_o_programa_enterra_os_fantasmas_ao_subir():
    """De nada adianta a função existir se ninguém a chama na abertura."""
    motor = (RAIZ / "app.py").read_text(encoding="utf-8")
    assert "job_manager.reconcile_stale()" in motor, (
        "o programa parou de enterrar os trabalhos do uso anterior ao abrir"
    )


def test_o_estudio_so_adota_trabalho_vivo():
    """A tela só assume um trabalho como seu se ele estiver mesmo de pé."""
    limpo = sem_comentario(JS)
    trecho = limpo[limpo.find("async function recuperarOTrabalho"):]
    trecho = trecho[:trecho.find("\n  }")]
    assert '["running", "queued"]' in trecho, (
        "a tela voltou a adotar trabalho em qualquer estado"
    )


# ── 2. o relógio ────────────────────────────────────────────────────────────


def test_a_hora_do_console_e_a_do_relogio_dele():
    """O motor grava em UTC. Recortar os caracteres da string dava a hora de
    Greenwich, enquanto as linhas ao vivo usavam a hora da máquina — e o
    console pulava três horas para trás no meio da lista.

    Duas horas diferentes na mesma tela é pior que nenhuma: ele não sabe mais
    qual das duas é a de agora.
    """
    limpo = sem_comentario(JS)
    assert "function horaLocal(" in limpo
    assert "horaLocal(evento.created_at)" in limpo, (
        "a história do console voltou a mostrar a hora de Greenwich"
    )
    corpo = limpo[limpo.find("function horaLocal("):]
    corpo = corpo[:corpo.find("\n  }")]
    assert "toTimeString" in corpo, "a conversão para a hora local sumiu"


# ── 3. a promessa repetida ──────────────────────────────────────────────────


def test_parar_confere_antes_de_prometer():
    """Cinco vezes "o motor para no próximo passo" e nada parou, porque não
    havia o que parar. Prometer a mesma coisa cinco vezes é pior do que não
    fazer nada."""
    limpo = sem_comentario(JS)
    trecho = limpo[limpo.find("async function pararOTrabalho"):]
    trecho = trecho[:trecho.find("\n  }\n")]
    assert '/api/jobs/${estado.trabalho}' in trecho, (
        "o botão de parar voltou a prometer sem conferir se tem o que parar"
    )
    assert "uso anterior" in trecho, (
        "sumiu o recado que explica que não havia nada rodando"
    )
    assert "terminarDeMoer(false)" in trecho, (
        "a tela continua dizendo que está moendo depois de descobrir que não está"
    )


def test_parar_nao_repete_a_mesma_promessa():
    """Depois de pedir a parada, o botão sai da tela. Apertar de novo não
    adianta, e repetir a frase faz parecer que o programa não ouviu."""
    limpo = sem_comentario(JS)
    trecho = limpo[limpo.find("async function pararOTrabalho"):]
    trecho = trecho[:trecho.find("\n  }\n")]
    assert "parar.hidden = true" in trecho
