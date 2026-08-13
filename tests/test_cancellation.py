from types import SimpleNamespace

import pytest

from modules.cancellation import OperationCancelled
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
