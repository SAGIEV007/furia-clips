def test_progress_events_include_runtime_version(monkeypatch):
    import app as app_module

    events = []
    monkeypatch.setattr(app_module.socketio, "emit", lambda event, payload: events.append((event, payload)))
    app_module.emit_progress("teste de versão", "info")

    assert events
    event, payload = events[-1]
    assert event == "progress"
    assert payload["program_version"] == app_module.PROGRAM_VERSION
    assert payload["program_revision"] == app_module.PROGRAM_REVISION
    assert payload["job_id"] is None
    assert payload["message"].startswith("[Versão ")
    assert payload["time"]


def test_status_event_carries_runtime_identity(monkeypatch):
    import app as app_module

    events = []
    monkeypatch.setattr(app_module.socketio, "emit", lambda event, payload: events.append((event, payload)))
    app_module.emit_status("cut_complete", {"clips": []}, job_id="job-status-123")

    event, payload = events[-1]
    assert event == "status"
    assert payload["program_version"] == app_module.PROGRAM_VERSION
    assert payload["program_revision"] == app_module.PROGRAM_REVISION
    assert payload["data"]["program_version"] == app_module.PROGRAM_VERSION
    assert payload["data"]["program_revision"] == app_module.PROGRAM_REVISION


def test_job_update_carries_runtime_identity(monkeypatch):
    import app as app_module

    events = []
    monkeypatch.setattr(app_module.socketio, "emit", lambda event, payload: events.append((event, payload)))
    app_module._emit_job_update({"id": "job-update-123", "state": "running"})

    event, payload = events[-1]
    assert event == "job_update"
    assert payload["program_version"] == app_module.PROGRAM_VERSION
    assert payload["program_revision"] == app_module.PROGRAM_REVISION


def test_progress_event_carries_explicit_job_id(monkeypatch):
    import app as app_module

    events = []
    monkeypatch.setattr(app_module.socketio, "emit", lambda event, payload: events.append((event, payload)))
    app_module.emit_progress("progresso do job", "info", job_id="job-progress-123")

    event, payload = events[-1]
    assert event == "progress"
    assert payload["job_id"] == "job-progress-123"


def test_progress_event_infers_legacy_job_id_from_active_task(monkeypatch):
    import app as app_module

    events = []
    original = dict(app_module.current_task)
    monkeypatch.setattr(app_module.socketio, "emit", lambda event, payload: events.append((event, payload)))
    try:
        app_module.current_task.update({"active": True, "job_id": "legacy-progress-123"})
        app_module.emit_progress("progresso legado", "info")
    finally:
        app_module.current_task.clear()
        app_module.current_task.update(original)

    event, payload = events[-1]
    assert event == "progress"
    assert payload["job_id"] == "legacy-progress-123"


def test_settings_endpoint_exposes_runtime_identity():
    import app as app_module

    response = app_module.app.test_client().get("/api/settings")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["program_version"] == app_module.PROGRAM_VERSION
    assert payload["program_revision"] == app_module.PROGRAM_REVISION
