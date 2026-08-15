import importlib.util
import os
from pathlib import Path


SETUP_PATH = Path(__file__).resolve().parents[1] / "_setup.py"
_spec = importlib.util.spec_from_file_location("furia_setup", SETUP_PATH)
_setup = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_setup)


def test_setup_reads_and_saves_persistent_gemini_key(tmp_path, monkeypatch):
    env_path = tmp_path / "config" / "local.env"
    monkeypatch.setenv("FURIA_CLIPS_ENV_FILE", str(env_path))
    env_path.parent.mkdir(parents=True)
    env_path.write_text("GEMINI_API_KEY=persistent-test-key\n", encoding="utf-8")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    assert _setup.check_gemini_key() is True
    assert os.environ["GEMINI_API_KEY"] == "persistent-test-key"

    _setup._save_gemini_key_to_env("rotated-test-key")
    assert "GEMINI_API_KEY=rotated-test-key" in env_path.read_text(encoding="utf-8")
