from types import SimpleNamespace

import pytest

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
