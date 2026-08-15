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
