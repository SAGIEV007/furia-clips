import subprocess

import pytest

from modules.cancellation import OperationCancelled
from modules.video_cutter import VideoCutter


class _FakeProcess:
    def __init__(self):
        self.returncode = None
        self.stderr = self
        self.killed = False
        self.waited = False

    def poll(self):
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None):
        self.waited = True
        return self.returncode

    def read(self):
        return ""


def test_ffmpeg_runner_kills_child_when_job_is_cancelled(monkeypatch):
    process = _FakeProcess()
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)

    with pytest.raises(OperationCancelled):
        VideoCutter._run_ffmpeg(["ffmpeg", "-version"], cancel_check=lambda: (_ for _ in ()).throw(OperationCancelled("cancelado")))

    assert process.killed is True
    assert process.waited is True
