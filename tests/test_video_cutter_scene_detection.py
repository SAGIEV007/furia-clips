import subprocess

from modules.video_cutter import VideoCutter


def test_detect_scenes_passes_timeout_and_returns_changes(monkeypatch):
    calls = []

    class Result:
        returncode = 0
        stderr = "[Parsed_showinfo] pts_time:1.25\n[Parsed_showinfo] pts_time:4.50\n"

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return Result()

    monkeypatch.setattr(subprocess, "run", fake_run)
    messages = []
    changes = VideoCutter().detect_scenes(
        "sample.mp4",
        timeout=17,
        emit_progress=lambda message, level="info": messages.append((message, level)),
    )

    assert changes == [0.0, 1.25, 4.5]
    assert calls[0][1]["timeout"] == 17.0
    assert "-an" in calls[0][0]
    assert calls[0][0][calls[0][0].index("-hwaccel") + 1] == "none"
    assert messages[-1][1] == "info"


def test_detect_scenes_timeout_returns_safe_baseline(monkeypatch):
    def fake_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", fake_run)
    messages = []
    changes = VideoCutter().detect_scenes(
        "sample.mp4",
        timeout=11,
        emit_progress=lambda message, level="info": messages.append((message, level)),
    )

    assert changes == [0.0]
    assert messages[-1][1] == "warning"
    assert "excedeu" in messages[-1][0]


def test_detect_scenes_nonzero_ffmpeg_returns_safe_baseline(monkeypatch):
    class Result:
        returncode = 1
        stderr = "invalid data found"

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Result())
    messages = []
    changes = VideoCutter().detect_scenes(
        "sample.mp4",
        emit_progress=lambda message, level="info": messages.append((message, level)),
    )

    assert changes == [0.0]
    assert messages[-1][1] == "warning"
    assert "falhou" in messages[-1][0]
