import os
import tempfile

import database as _database_module
import modules.clip_selector as _clip_selector_module


def _fast_llm_fallback(*args, **kwargs):
    return []


# Avoid network timeouts when Ollama is not running.
# Tests that need real LLM behavior should patch this explicitly.
_clip_selector_module.ClipSelector._select_with_llm = _fast_llm_fallback


# SAFETY NET (added 2026-08-31): before this, any test that called
# database.init_db()/create_project() without explicitly patching
# database.DB_PATH wrote directly into the user's REAL production
# database (~/FuriaClipsData/database/editorial_learning.sqlite3).
# This silently accumulated 1442+ junk projects ("Teste", "Reload de
# contexto") in production over time. Redirecting DB_PATH here, at
# conftest import time (before any test module/class runs), makes the
# whole test session safe by default regardless of whether individual
# tests remember to isolate their own DB path. Tests that explicitly
# patch/monkeypatch DB_PATH to their own tmp_path continue to work
# unchanged — they just revert to this safe default afterwards instead
# of to the real production path.
_TEST_DB_DIR = tempfile.mkdtemp(prefix="furia-pytest-db-")
_database_module.DB_PATH = os.path.join(_TEST_DB_DIR, "furia-test.sqlite3")
_database_module.init_db()
