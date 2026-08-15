import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from subprocess import CompletedProcess

from modules.repository_sync import (
    SNAPSHOT_RELATIVE_PATH,
    build_feedback_snapshot,
    get_repository_status,
    write_feedback_snapshot,
)


class _FakeConnection:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, _query):
        return self

    def fetchall(self):
        return self.rows

    def close(self):
        return None


class RepositorySyncTests(unittest.TestCase):
    def test_feedback_snapshot_is_sanitized_and_stable(self):
        rows = [
            ("editorial-key", 12.3456, 42.9876, 30.642, 88, "v3", "approved", "contexto", '["hook", "completo"]', '{"_review_metadata": {"candidate_origin": "gemini_primary", "selection_source": "gemini", "confidence": 0.91}, "text": "não exportar"}', "2026-08-15 00:00:00"),
        ]
        with patch("modules.repository_sync.get_db", return_value=_FakeConnection(rows)):
            payload = build_feedback_snapshot()
        self.assertEqual(payload["format"], "furia-clips-editorial-feedback")
        self.assertEqual(payload["format_version"], 2)
        self.assertEqual(payload["record_count"], 1)
        record = payload["records"][0]
        self.assertEqual(record["editorial_key"], "editorial-key")
        self.assertEqual(record["action"], "approved")
        self.assertEqual(record["quality_tags"], ["hook", "completo"])
        self.assertEqual(record["review_metadata"], {"candidate_origin": "gemini_primary", "selection_source": "gemini", "confidence": 0.91})
        self.assertNotIn("transcript", record)
        self.assertNotIn("source_video", record)
        self.assertNotIn("api_key", json.dumps(payload))

    def test_repository_status_separates_feedback_snapshot_from_code_changes(self):
        def fake_git(_repo, *args, **kwargs):
            command = tuple(args)
            outputs = {
                ("branch", "--show-current"): "manus/rebuild-opus-parity\n",
                ("rev-parse", "HEAD"): "local123\n",
                ("rev-parse", "origin/manus/rebuild-opus-parity"): "local123\n",
                ("status", "--porcelain=v1"): " M data/editorial_feedback_snapshot.json\n",
            }
            return CompletedProcess(["git", *args], 0, outputs.get(command, ""), "")

        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            (repo / ".git").mkdir()
            with patch("modules.repository_sync._run_git", side_effect=fake_git):
                status = get_repository_status(str(repo), fetch=False)

        self.assertEqual(status["code_dirty_files"], [])
        self.assertTrue(status["feedback_snapshot_dirty"])
        self.assertFalse(status["update_available"])

    def test_snapshot_writer_does_not_write_outside_checkout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            (repo / ".git").mkdir()
            rows = []
            with patch("modules.repository_sync.get_db", return_value=_FakeConnection(rows)):
                result = write_feedback_snapshot(str(repo))
            target = repo / SNAPSHOT_RELATIVE_PATH
            self.assertEqual(Path(result["path"]), target)
            self.assertTrue(target.is_file())
            self.assertFalse((repo.parent / "editorial_feedback_snapshot.json").exists())
            saved = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(saved["records"], [])


if __name__ == "__main__":
    unittest.main()
