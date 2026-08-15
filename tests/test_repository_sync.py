import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from subprocess import CompletedProcess

from modules.repository_sync import (
    SNAPSHOT_RELATIVE_PATH,
    SYNC_FORMAT,
    build_feedback_snapshot,
    get_repository_status,
    write_feedback_snapshot,
    _feedback_snapshot_metadata,
    restore_feedback_snapshot,
    RepositorySyncError,
)


class _FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.queries = []

    def execute(self, query):
        self.queries.append(query)
        return self

    def fetchall(self):
        return self.rows

    def close(self):
        return None


class RepositorySyncTests(unittest.TestCase):
    def test_feedback_snapshot_is_sanitized_and_stable(self):
        rows = [
            ("editorial-key", 12.3456, 42.9876, 30.642, 88, "v3", "approved", "contexto", '["hook", "completo"]', '{"_review_metadata": {"candidate_origin": "gemini_primary", "selection_source": "gemini", "confidence": 0.91}, "text": "não exportar"}', "2026-08-15 00:00:00", "physical-signature"),
        ]
        connection = _FakeConnection(rows)
        with patch("modules.repository_sync.get_db", return_value=connection):
            payload = build_feedback_snapshot()
        self.assertEqual(payload["format"], "furia-clips-editorial-feedback")
        self.assertEqual(payload["format_version"], 2)
        self.assertEqual(payload["record_count"], 1)
        record = payload["records"][0]
        self.assertEqual(record["editorial_key"], "editorial-key")
        self.assertEqual(record["action"], "approved")
        self.assertEqual(record["quality_tags"], ["hook", "completo"])
        self.assertEqual(record["source_signature"], "physical-signature")
        self.assertEqual(record["review_metadata"], {"candidate_origin": "gemini_primary", "selection_source": "gemini", "confidence": 0.91})
        self.assertNotIn("transcript", record)
        self.assertNotIn("source_video", record)
        self.assertNotIn("api_key", json.dumps(payload))
        self.assertIn("ROW_NUMBER() OVER", connection.queries[0])
        self.assertIn("PARTITION BY f.clip_id", connection.queries[0])
        self.assertIn("f.action IN ('approved', 'rejected', 'needs_review')", connection.queries[0])
        self.assertIn("WHERE feedback_rank = 1", connection.queries[0])
        self.assertIn("ORDER BY editorial_key ASC, start_time ASC", connection.queries[0])

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

    def test_feedback_snapshot_metadata_is_portable_and_non_sensitive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            target = repo / SNAPSHOT_RELATIVE_PATH
            target.parent.mkdir(parents=True)
            target.write_text(
                json.dumps(
                    {
                        "format": SYNC_FORMAT,
                        "format_version": 2,
                        "generated_at": "2026-08-15T05:00:00+00:00",
                        "records": [{"action": "approved"}, {"action": "rejected"}],
                        "record_count": 2,
                    }
                ),
                encoding="utf-8",
            )
            metadata = _feedback_snapshot_metadata(repo)
        self.assertTrue(metadata["feedback_snapshot_present"])
        self.assertTrue(metadata["feedback_snapshot_valid"])
        self.assertTrue(metadata["feedback_snapshot_consistent"])
        self.assertEqual(metadata["feedback_snapshot_records"], 2)
        self.assertEqual(metadata["feedback_snapshot_version"], 2)
        self.assertEqual(metadata["feedback_snapshot_generated_at"], "2026-08-15T05:00:00+00:00")

    def test_restore_feedback_snapshot_validates_and_replays_final_decisions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            (repo / ".git").mkdir()
            target = repo / SNAPSHOT_RELATIVE_PATH
            target.parent.mkdir(parents=True)
            record = {
                "editorial_key": "portable-key",
                "action": "approved",
                "reason_code": "contexto_completo",
                "quality_tags": ["hook"],
                "created_at": "2026-08-15T05:00:00+00:00",
            }
            target.write_text(
                json.dumps(
                    {
                        "format": SYNC_FORMAT,
                        "format_version": 2,
                        "record_count": 1,
                        "records": [record],
                    }
                ),
                encoding="utf-8",
            )
            with patch(
                "modules.repository_sync.restore_local_feedback_snapshot",
                return_value={"records_seen": 1, "imported": 1, "already_current": 0},
            ) as replay:
                result = restore_feedback_snapshot(str(repo))

        replay.assert_called_once_with([record])
        self.assertTrue(result["success"])
        self.assertEqual(result["imported"], 1)
        self.assertEqual(result["feedback_snapshot_version"], 2)

    def test_restore_feedback_snapshot_rejects_inconsistent_count(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            (repo / ".git").mkdir()
            target = repo / SNAPSHOT_RELATIVE_PATH
            target.parent.mkdir(parents=True)
            target.write_text(
                json.dumps(
                    {
                        "format": SYNC_FORMAT,
                        "format_version": 2,
                        "record_count": 2,
                        "records": [{"editorial_key": "one", "action": "approved"}],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(RepositorySyncError):
                restore_feedback_snapshot(str(repo))

    def test_invalid_feedback_snapshot_is_present_but_not_valid(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            target = repo / SNAPSHOT_RELATIVE_PATH
            target.parent.mkdir(parents=True)
            target.write_text("not-json", encoding="utf-8")
            metadata = _feedback_snapshot_metadata(repo)
        self.assertTrue(metadata["feedback_snapshot_present"])
        self.assertFalse(metadata["feedback_snapshot_valid"])
        self.assertFalse(metadata["feedback_snapshot_consistent"])
        self.assertEqual(metadata["feedback_snapshot_records"], 0)

    def test_feedback_snapshot_with_wrong_count_is_not_valid(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            target = repo / SNAPSHOT_RELATIVE_PATH
            target.parent.mkdir(parents=True)
            target.write_text(
                json.dumps(
                    {
                        "format": SYNC_FORMAT,
                        "format_version": 2,
                        "record_count": 7,
                        "records": [{"action": "approved"}],
                    }
                ),
                encoding="utf-8",
            )
            metadata = _feedback_snapshot_metadata(repo)
        self.assertTrue(metadata["feedback_snapshot_present"])
        self.assertFalse(metadata["feedback_snapshot_valid"])
        self.assertFalse(metadata["feedback_snapshot_consistent"])
        self.assertEqual(metadata["feedback_snapshot_records"], 1)


if __name__ == "__main__":
    unittest.main()
