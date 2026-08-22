from types import SimpleNamespace

import pytest
from unittest.mock import patch

from modules.cancellation import OperationCancelled
from modules.job_manager import JobCancelled
from modules.transcriber import Transcriber


def test_faster_whisper_checks_cancel_between_segments():
    transcriber = Transcriber()
    transcriber.model = SimpleNamespace(
        transcribe=lambda *args, **kwargs: (
            iter([
                SimpleNamespace(start=0.0, end=1.0, text="primeiro", words=[]),
                SimpleNamespace(start=1.0, end=2.0, text="segundo", words=[]),
            ]),
            SimpleNamespace(),
        )
    )
    calls = []

    def cancel_after_first():
        calls.append(True)
        if len(calls) >= 2:
            raise OperationCancelled("parado")

    with pytest.raises(OperationCancelled, match="parado"):
        transcriber._transcribe_faster_whisper("video.mp4", cancel_check=cancel_after_first)
    assert len(calls) == 2


def test_silence_remover_terminates_ffmpeg_when_cancelled(monkeypatch):
    import modules.silence_remover as silence_module

    class FakeProcess:
        def __init__(self):
            self.terminated = False
            self.killed = False
            self.returncode = None
            self.stdout = None
            self.stderr = None

        def poll(self):
            return None

        def communicate(self):
            return "", ""

        def terminate(self):
            self.terminated = True
            self.returncode = -15

        def wait(self, timeout=None):
            return self.returncode

        def kill(self):
            self.killed = True
            self.returncode = -9

    process = FakeProcess()
    monkeypatch.setattr(silence_module.subprocess, "Popen", lambda *args, **kwargs: process)

    def cancel():
        raise OperationCancelled("parado no silêncio")

    with pytest.raises(OperationCancelled, match="parado no silêncio"):
        silence_module.SilenceRemover()._run_command(["ffmpeg", "-i", "video.mp4"], cancel_check=cancel)

    assert process.terminated is True
    assert process.killed is False


def test_silence_remover_reads_ffprobe_duration_json(monkeypatch):
    import modules.silence_remover as silence_module

    remover = silence_module.SilenceRemover()
    monkeypatch.setattr(
        remover,
        "_run_command",
        lambda _cmd, cancel_check=None: (0, '{"format": {"duration": "12.5"}}', ""),
    )
    assert remover._get_duration("video.mp4") == 12.5


def test_silence_route_passes_cancel_check_and_restores_legacy_state(monkeypatch, tmp_path):
    import app as app_module
    import modules.silence_remover as silence_module

    source = tmp_path / "silence-source.mp4"
    source.write_bytes(b"fake")
    original = dict(app_module.current_task)
    captured = {}

    class FakeRemover:
        def __init__(self, **kwargs):
            captured["settings"] = kwargs

        def remove_silence(self, video_path, emit_progress=None, cancel_check=None):
            captured["video_path"] = video_path
            captured["cancel_check"] = cancel_check
            assert callable(cancel_check)
            cancel_check()
            return {"output_path": "processed.mp4"}

    class ImmediateThread:
        def __init__(self, target, daemon=True):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(silence_module, "SilenceRemover", FakeRemover)
    monkeypatch.setattr(app_module.threading, "Thread", ImmediateThread)
    monkeypatch.setattr(app_module, "_resolve_media_input", lambda _value: str(source))
    try:
        app_module.current_task.update({
            "active": False,
            "cancel": False,
            "operation": "",
            "job_id": None,
            "started_at": None,
        })
        response = app_module.app.test_client().post(
            "/api/process/silence",
            json={"video_path": str(source)},
        )
        assert response.status_code == 200
        assert response.get_json()["job_id"].startswith("legacy-")
        assert response.get_json()["state"] == "running"
        assert captured["video_path"] == str(source)
        assert app_module.current_task["active"] is False
        assert app_module.current_task["operation"] == ""
    finally:
        app_module.current_task.clear()
        app_module.current_task.update(original)


def test_legacy_cancel_endpoint_accepts_matching_legacy_job_id():
    import app as app_module

    original = dict(app_module.current_task)
    try:
        app_module.current_task.update({
            "active": True,
            "cancel": False,
            "operation": "transcription",
            "job_id": "legacy-transcription-123",
            "started_at": "now",
        })
        response = app_module.app.test_client().post(
            "/api/process/cancel",
            json={"job_id": "legacy-transcription-123"},
        )
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["success"] is True
        assert payload["state"] == "cancel_requested"
        assert payload["job_id"] == "legacy-transcription-123"
        assert app_module.current_task["cancel"] is True
    finally:
        app_module.current_task.clear()
        app_module.current_task.update(original)


def test_legacy_cancel_endpoint_does_not_cancel_new_operation_for_stale_job_id(monkeypatch):
    import app as app_module

    calls = []
    original = dict(app_module.current_task)

    class FakeJobManager:
        def request_cancel(self, job_id):
            calls.append(job_id)
            raise KeyError(job_id)

    monkeypatch.setattr(app_module, "job_manager", FakeJobManager())
    try:
        app_module.current_task.update({
            "active": True,
            "cancel": False,
            "operation": "transcription",
            "job_id": "legacy-transcription-new",
            "started_at": "now",
        })
        response = app_module.app.test_client().post(
            "/api/process/cancel",
            json={"job_id": "legacy-transcription-old"},
        )
        assert response.status_code == 404
        assert app_module.current_task["cancel"] is False
        assert calls == ["legacy-transcription-old"]
    finally:
        app_module.current_task.clear()
        app_module.current_task.update(original)


def test_cancel_endpoint_routes_persistent_job_to_job_manager(monkeypatch):
    import app as app_module

    calls = []
    original = dict(app_module.current_task)

    class FakeJobManager:
        def request_cancel(self, job_id):
            calls.append(job_id)
            return {"success": True, "state": "cancel_requested", "job_id": job_id}

    monkeypatch.setattr(app_module, "job_manager", FakeJobManager())
    try:
        app_module.current_task.update({
            "active": True,
            "cancel": False,
            "operation": "cut",
            "job_id": "job-cut-123",
            "started_at": "now",
        })
        response = app_module.app.test_client().post(
            "/api/process/cancel",
            json={"job_id": "job-cut-123"},
        )
        assert response.status_code == 200
        assert response.get_json()["state"] == "cancel_requested"
        assert calls == ["job-cut-123"]
        assert app_module.current_task["cancel"] is False
    finally:
        app_module.current_task.clear()
        app_module.current_task.update(original)


def test_legacy_cancel_endpoint_sets_shared_signal():
    import app as app_module

    original = dict(app_module.current_task)
    try:
        app_module.current_task.update({"active": True, "cancel": False, "operation": "transcription"})
        client = app_module.app.test_client()
        response = client.post("/api/process/cancel", json={})
        assert response.status_code == 200
        assert response.get_json()["success"] is True
        assert app_module.current_task["cancel"] is True
    finally:
        app_module.current_task.clear()
        app_module.current_task.update(original)


def test_cut_route_creates_persistent_job_before_returning(monkeypatch, tmp_path):
    import app as app_module

    source = tmp_path / "fonte.mp4"
    source.write_bytes(b"")
    original = dict(app_module.current_task)
    submissions = []

    class CapturingJobManager:
        def submit(self, job_type, target, project_id=None):
            submissions.append({"type": job_type, "target": target, "project_id": project_id})
            return {"id": "job-cut-123", "state": "queued"}

    monkeypatch.setattr(app_module, "job_manager", CapturingJobManager())
    monkeypatch.setattr(app_module, "_resolve_media_input", lambda _value: str(source))
    try:
        app_module.current_task.update({
            "active": False,
            "cancel": True,
            "operation": "",
            "job_id": None,
            "started_at": None,
        })
        response = app_module.app.test_client().post(
            "/api/process/cut",
            json={"video_path": str(source)},
        )

        payload = response.get_json()
        assert response.status_code == 200
        assert payload["success"] is True
        assert payload["job_id"] == "job-cut-123"
        assert len(submissions) == 1
        assert submissions[0]["type"] == "cut_shorts"
        assert callable(submissions[0]["target"])
        assert app_module.current_task["active"] is True
        assert app_module.current_task["operation"] == "cut"
        assert app_module.current_task["job_id"] == "job-cut-123"
        assert app_module.current_task["cancel"] is False
        assert app_module.current_task["started_at"]
    finally:
        app_module.current_task.clear()
        app_module.current_task.update(original)


def test_editorial_context_worker_propagates_job_cancellation_during_local_audit(monkeypatch, tmp_path):
    import app as app_module

    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake-video")
    submitted = {}

    class CapturingJobManager:
        def submit(self, job_type, target, project_id=None):
            submitted["type"] = job_type
            submitted["target"] = target
            return {"id": "job-context-cancel", "state": "queued"}

    class Context:
        job_id = "job-context-cancel"

        def update(self, **kwargs):
            return kwargs

        def check_cancel(self):
            return None

    monkeypatch.setattr(app_module, "job_manager", CapturingJobManager())
    monkeypatch.setattr(app_module, "_resolve_media_input", lambda _value: str(source))
    monkeypatch.setattr(app_module, "_probe_video_duration_seconds", lambda _path: 30.0)
    monkeypatch.setattr(
        app_module,
        "_transcription_from_request",
        lambda _data, duration=None: {
            "segments": [{"start": 0.0, "end": 3.0, "text": "A proposta termina."}],
            "full_text": "A proposta termina.",
            "language": "pt",
            "source": "manual",
        },
    )
    monkeypatch.setattr(app_module, "_enrich_editorial_context", lambda *args, **kwargs: {"focus": "generic_political"})
    monkeypatch.setattr(
        app_module,
        "_enrich_editorial_context_locally",
        lambda *args, **kwargs: (_ for _ in ()).throw(JobCancelled("parado durante auditoria")),
    )

    response = app_module.app.test_client().post(
        "/api/editorial/context",
        json={"video_path": str(source), "analyze_video": False},
    )
    assert response.status_code == 200
    assert submitted["type"] == "editorial_context"

    with pytest.raises(JobCancelled, match="parado durante auditoria"):
        submitted["target"](Context())


def test_adjust_render_worker_propagates_cancellation_before_ffmpeg(monkeypatch, tmp_path):
    import app as app_module
    import database

    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake-video")
    db_path = tmp_path / "adjust-cancel.sqlite"
    submitted = {}

    class CapturingJobManager:
        def submit(self, job_type, target, project_id=None):
            submitted.update(type=job_type, target=target, project_id=project_id)
            return {"id": "job-adjust-cancel", "state": "queued"}

    class Context:
        job_id = "job-adjust-cancel"

        def update(self, **_kwargs):
            return {}

        def check_cancel(self):
            raise JobCancelled("parado antes do FFmpeg")

    with patch.object(database, "DB_PATH", str(db_path)):
        database.init_db()
        project_id = database.create_project("Projeto de cancelamento", str(source))
        clip_id = database.save_clip(project_id, "exports/original.mp4", 10.0, 52.0, 42.0)
        monkeypatch.setattr(app_module, "job_manager", CapturingJobManager())
        monkeypatch.setattr(app_module, "_resolve_media_input", lambda _value: str(source))
        app_module.active_adjust_render_ids.clear()
        response = app_module.app.test_client().post(
            f"/api/clips/{clip_id}/adjust/render",
            json={"adjustment": {"start": 12.0, "end": 49.0}, "source_duration": 60.0},
        )

    assert response.status_code == 202
    assert submitted["type"] == "adjust_clip_render"
    with pytest.raises(JobCancelled, match="parado antes do FFmpeg"):
        submitted["target"](Context())
    assert app_module.active_adjust_render_ids == set()
