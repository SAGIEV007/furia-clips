"""Duas moagens rodando juntas, e a que ele mandou parar nunca parou.

Do relato dele, com o console colado:

    [Transcrição] Geração automática solicitada.
    [Gemini] Compactando cópia de análise...
    [Sistema] Solicitação de parada enviada; aguardando a etapa segura.
    [Contexto] Análise integral antes do corte solicitada.
    [Job f29121be] [Contexto] Transcrição canônica confirmada: 4390 segmentos;
        origem manual; cobertura covered.
    ... (onze minutos depois) ...
    Iniciando transcricao...
    Transcrevendo... 50 segmentos processados
    ...
    Transcricao completa: 3330 segmentos, 154413 caracteres (700s)
    Transcricao concluida!
    [Sistema] Solicitação de parada enviada; aguardando a etapa segura.

Ele pediu para parar a transcrição automática, e ela terminou os 700 segundos
inteiros mesmo assim — enquanto "Análise integral" já tinha achado e usado a
transcrição manual que ele tinha confirmado. E depois de "Transcricao
concluida!", pediu para parar de novo, e 17 minutos depois ainda não tinha
parado: "agora é 8:35 e ainda sequer parou mesmo eu tenho pedido".

Numa segunda tentativa, a barra "Processando" ficou na tela horas depois de o
console já dizer "Transcricao concluida!" — a foto mostrava "quase meio dia"
com a última linha do console em 09:08.

Achado, lendo o código: das quatro rotas que entregam trabalho ao JobManager
(`source_transcription`, `cut_shorts`, `editorial_context`, `process_complete`),
três conferem `current_task["active"]` antes de começar e recusam com 409 se
já tem algo rodando. `/api/editorial/context` — a "Análise integral" — não
conferia. Ela começava de qualquer jeito, por cima de qualquer tarefa legada
(como a transcrição, que roda numa thread crua, fora do JobManager) que ainda
estivesse de pé. Foi assim que as duas rodaram juntas.

E o botão de parar só cancelava o job cujo id a TELA lembrava. Com dois
trabalhos ao mesmo tempo, a tela podia estar de olho no errado — e o pedido de
parar acertava um job que já tinha terminado, enquanto a transcrição, sem
saber de nada, seguia rodando.

Este arquivo prova as duas coisas separadamente e depois juntas.
"""

import pytest


@pytest.fixture()
def tarefa_legada_limpa():
    """Guarda e devolve `current_task` como estava — o mesmo padrão dos
    outros testes de cancelamento deste repositório."""
    import app as motor

    anterior = dict(motor.current_task)
    yield motor
    motor.current_task.clear()
    motor.current_task.update(anterior)


class GerenteDeJobsFalso:
    """Um JobManager de mentira: grava o que pediram e finge um estado."""

    def __init__(self, jobs_de_pe=None):
        self.submissoes = []
        self.cancelamentos = []
        self._jobs_de_pe = list(jobs_de_pe or [])

    def submit(self, job_type, target, project_id=None):
        job = {"id": f"job-{len(self.submissoes)}", "state": "queued"}
        self.submissoes.append({"type": job_type, "target": target, "project_id": project_id})
        return job

    def list(self, limit=50):
        return list(self._jobs_de_pe)[:limit]

    def request_cancel(self, job_id):
        conhecido = next((j for j in self._jobs_de_pe if j["id"] == job_id), None)
        if conhecido is None:
            raise KeyError(job_id)
        conhecido["state"] = "cancel_requested"
        self.cancelamentos.append(job_id)
        return conhecido


# ── 1. a Análise integral esperava a fila, como as outras três já esperavam ─


def test_a_analise_integral_recusa_comecar_por_cima_de_uma_tarefa_legada(tarefa_legada_limpa, tmp_path):
    """A transcrição dele ainda estava rodando (fora do JobManager, numa
    thread crua) quando ele pediu a Análise integral. Ela tinha que esperar —
    não começar por cima."""
    motor = tarefa_legada_limpa
    fonte = tmp_path / "fonte.mp4"
    fonte.write_bytes(b"x")

    gerente = GerenteDeJobsFalso()
    motor.current_task.update({
        "active": True, "operation": "transcription", "job_id": None,
        "cancel": False, "started_at": "2026-01-01T08:00:00",
    })

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(motor, "job_manager", gerente)
        mp.setattr(motor, "_resolve_media_input", lambda _v: str(fonte))
        resposta = motor.app.test_client().post(
            "/api/editorial/context", json={"video_path": str(fonte)}
        )

    assert resposta.status_code == 409, (
        "a Análise integral começou por cima da transcrição em vez de esperar"
    )
    assert resposta.get_json().get("busy") is True
    assert gerente.submissoes == [], "um job novo foi criado mesmo com a fila ocupada"


def test_a_analise_integral_registra_a_tarefa_legada_antes_de_responder(tarefa_legada_limpa, tmp_path):
    """Livre para começar, ela tem que se anunciar do mesmo jeito que o corte
    e o processo completo já se anunciam — senão o PRÓXIMO pedido (o dela
    mesma, mais tarde) não saberia que ela está rodando."""
    motor = tarefa_legada_limpa
    fonte = tmp_path / "fonte.mp4"
    fonte.write_bytes(b"x")

    gerente = GerenteDeJobsFalso()
    motor.current_task.update({
        "active": False, "operation": "", "job_id": None,
        "cancel": False, "started_at": None,
    })

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(motor, "job_manager", gerente)
        mp.setattr(motor, "_resolve_media_input", lambda _v: str(fonte))
        resposta = motor.app.test_client().post(
            "/api/editorial/context", json={"video_path": str(fonte)}
        )

    assert resposta.status_code == 200
    assert len(gerente.submissoes) == 1
    assert gerente.submissoes[0]["type"] == "editorial_context"
    assert motor.current_task["active"] is True
    assert motor.current_task["operation"] == "editorial_context"
    assert motor.current_task["job_id"] == resposta.get_json()["job_id"]


def test_a_analise_integral_libera_a_tarefa_legada_mesmo_falhando(tarefa_legada_limpa, tmp_path):
    """Um erro no meio da análise não pode deixar a trava fechada para
    sempre — senão nada mais roda até reiniciar o programa."""
    motor = tarefa_legada_limpa
    fonte = tmp_path / "fonte.mp4"
    fonte.write_bytes(b"x")

    gerente = GerenteDeJobsFalso()
    motor.current_task.update({
        "active": False, "operation": "", "job_id": None,
        "cancel": False, "started_at": None,
    })

    class ContextoFalso:
        job_id = "job-0"

        def update(self, **_kw):
            return None

        def check_cancel(self):
            return None

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(motor, "job_manager", gerente)
        mp.setattr(motor, "_resolve_media_input", lambda _v: str(fonte))
        mp.setattr(motor, "_probe_video_duration_seconds", lambda _p: 30.0)
        mp.setattr(motor, "_manual_transcript_was_supplied", lambda _d: False)
        mp.setattr(motor, "_transcription_from_request", lambda _d, duration=None: None)
        mp.setattr(motor, "_run_gemini_video_analysis", lambda *a, **k: None)
        mp.setattr(motor, "_transcription_from_gemini_result", lambda *a, **k: None)

        resposta = motor.app.test_client().post(
            "/api/editorial/context", json={"video_path": str(fonte)}
        )
        assert resposta.status_code == 200
        alvo = gerente.submissoes[0]["target"]

        with pytest.raises(ValueError):
            alvo(ContextoFalso())

    assert motor.current_task["active"] is False, (
        "a tarefa legada continuou marcada como ativa depois do erro"
    )
    assert motor.current_task["job_id"] is None


# ── 2. parar tinha que parar o que está rodando, não o que a tela lembra ────


def test_parar_cancela_a_tarefa_legada_mesmo_quando_a_tela_aponta_outro_job(tarefa_legada_limpa):
    """O cenário exato do relato: a transcrição (tarefa legada) segue viva, e
    a tela manda parar um `job_id` que já terminou. Antes, o pedido acertava
    só aquele job e a transcrição nunca soube que devia parar."""
    motor = tarefa_legada_limpa
    gerente = GerenteDeJobsFalso(jobs_de_pe=[
        {"id": "job-ja-acabou", "state": "completed"},
    ])
    motor.current_task.update({
        "active": True, "operation": "transcription", "job_id": None,
        "cancel": False, "started_at": "2026-01-01T08:00:00",
    })

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(motor, "job_manager", gerente)
        resposta = motor.app.test_client().post(
            "/api/process/cancel", json={"job_id": "job-ja-acabou"}
        )

    assert resposta.status_code == 200
    assert motor.current_task["cancel"] is True, (
        "pedir para parar um job já terminado não pode deixar a transcrição viva sem aviso"
    )


def test_parar_cancela_um_job_que_a_tela_nem_sabia_que_existia(tarefa_legada_limpa):
    """"Análise integral" rodando sem a tela ter registrado o id (o defeito
    consertado acima) não pode ficar imune ao botão de parar."""
    motor = tarefa_legada_limpa
    gerente = GerenteDeJobsFalso(jobs_de_pe=[
        {"id": "job-escondido", "state": "running"},
    ])
    motor.current_task.update({
        "active": False, "operation": "", "job_id": None,
        "cancel": False, "started_at": None,
    })

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(motor, "job_manager", gerente)
        resposta = motor.app.test_client().post("/api/process/cancel", json={})

    assert resposta.status_code == 200
    assert "job-escondido" in gerente.cancelamentos, (
        "um job rodando de verdade ficou de fora só por a tela não conhecer o id"
    )


def test_parar_sem_nada_rodando_nao_inventa_trabalho(tarefa_legada_limpa):
    """Nada ativo, nada para cancelar — e isso não é erro."""
    motor = tarefa_legada_limpa
    gerente = GerenteDeJobsFalso()
    motor.current_task.update({
        "active": False, "operation": "", "job_id": None,
        "cancel": False, "started_at": None,
    })

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(motor, "job_manager", gerente)
        resposta = motor.app.test_client().post("/api/process/cancel", json={})

    assert resposta.status_code == 200
    assert resposta.get_json()["success"] is True
    assert gerente.cancelamentos == []


# ── 3. a barra "processando" tinha que saber quando não há mais nada vivo ───


def test_a_lista_de_jobs_expoe_se_a_tarefa_legada_esta_viva(tarefa_legada_limpa):
    """A tela só sabia de trabalho pelo JobManager. A transcrição — fora dele
    — podia terminar sem que nenhum evento avisasse, e a barra "Processando"
    ficava de pé horas depois. `legacy_task` é a janela que faltava."""
    motor = tarefa_legada_limpa

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(motor, "job_manager", GerenteDeJobsFalso())

        motor.current_task.update({"active": True, "operation": "transcription"})
        ativo = motor.app.test_client().get("/api/jobs").get_json()
        assert ativo["legacy_task"] == {"active": True, "operation": "transcription"}

        motor.current_task.update({"active": False, "operation": ""})
        parado = motor.app.test_client().get("/api/jobs").get_json()
        assert parado["legacy_task"] == {"active": False, "operation": ""}
