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
    assert payload["message"].startswith("[Versão ")
    assert payload["time"]


def test_program_version_matches_repository_file():
    import app as app_module
    from pathlib import Path

    version_path = Path(app_module.BASE_DIR) / "VERSION"
    assert version_path.read_text(encoding="utf-8").strip() == app_module.PROGRAM_VERSION
    assert app_module.PROGRAM_VERSION == "1.7"


def test_connected_event_exposes_runtime_identity(monkeypatch):
    import app as app_module

    events = []
    monkeypatch.setattr(app_module, "emit", lambda event, payload: events.append((event, payload)))
    app_module.handle_connect()
    connected = next(payload for event, payload in events if event == "connected")
    assert connected["program_version"] == app_module.PROGRAM_VERSION
    assert connected["program_revision"] == app_module.PROGRAM_REVISION
    assert "Versão 1.7" in connected["message"]


def test_settings_endpoint_exposes_runtime_identity():
    import app as app_module

    response = app_module.app.test_client().get("/api/settings")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["program_version"] == app_module.PROGRAM_VERSION
    assert payload["program_revision"] == app_module.PROGRAM_REVISION
