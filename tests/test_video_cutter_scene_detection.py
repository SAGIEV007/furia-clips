import subprocess

from modules.video_cutter import VideoCutter


def test_detect_scenes_passes_timeout_to_cooperative_runner(monkeypatch):
    calls = []

    def fake_runner(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            command,
            0,
            "",
            "[Parsed_showinfo] pts_time:1.25\n[Parsed_showinfo] pts_time:4.50\n",
        )

    monkeypatch.setattr(VideoCutter, "_run_ffmpeg", staticmethod(fake_runner))
    messages = []
    changes = VideoCutter().detect_scenes(
        "sample.mp4",
        timeout=17,
        emit_progress=lambda message, level="info": messages.append((message, level)),
    )

    assert changes == [0.0, 1.25, 4.5]
    assert calls[0][1]["timeout_seconds"] == 17.0
    assert calls[0][1]["heartbeat_prefix"] == "Cenas"
    assert "-an" in calls[0][0]
    assert calls[0][0][calls[0][0].index("-hwaccel") + 1] == "none"
    assert messages[-1][1] == "info"


def test_detect_scenes_timeout_returns_safe_baseline(monkeypatch):
    def fake_runner(command, **kwargs):
        raise TimeoutError("limite de cenas")

    monkeypatch.setattr(VideoCutter, "_run_ffmpeg", staticmethod(fake_runner))
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
    def fake_runner(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, "", "invalid data found")

    monkeypatch.setattr(VideoCutter, "_run_ffmpeg", staticmethod(fake_runner))
    messages = []
    changes = VideoCutter().detect_scenes(
        "sample.mp4",
        emit_progress=lambda message, level="info": messages.append((message, level)),
    )

    assert changes == [0.0]
    assert messages[-1][1] == "warning"
    assert "falhou" in messages[-1][0]
