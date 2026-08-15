import os
import sqlite3
import tempfile
import time
import unittest
from datetime import datetime, timezone

from modules.job_manager import JobManager


class JobManagerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "jobs.sqlite3")
        self.manager = JobManager(self.db_path, max_workers=1)

    def tearDown(self):
        self.manager.shutdown()
        self.tempdir.cleanup()

    def test_job_completes_and_persists_progress(self):
        def worker(ctx):
            ctx.update(stage="analysis", progress=50, message="Analisando")
            return {"artifacts": ["exports/clip.mp4"]}

        created = self.manager.submit("test", worker)
        deadline = time.time() + 3
        final = None
        while time.time() < deadline:
            final = self.manager.get(created["id"])
            if final and final["state"] in {"completed", "failed", "cancelled"}:
                break
            time.sleep(0.02)

        self.assertIsNotNone(final)
        self.assertEqual(final["state"], "completed")
        self.assertEqual(final["progress"], 100)
        self.assertEqual(final["artifacts"], ["exports/clip.mp4"])

    def test_cancel_request_is_visible_to_worker(self):
        started = []

        def worker(ctx):
            started.append(True)
            for _ in range(100):
                ctx.check_cancel()
                time.sleep(0.01)
            return {}

        created = self.manager.submit("long", worker)
        deadline = time.time() + 3
        while not started and time.time() < deadline:
            time.sleep(0.01)
        self.manager.request_cancel(created["id"])

        deadline = time.time() + 3
        final = None
        while time.time() < deadline:
            final = self.manager.get(created["id"])
            if final and final["state"] in {"completed", "failed", "cancelled"}:
                break
            time.sleep(0.02)

        self.assertIsNotNone(final)
        self.assertEqual(final["state"], "cancelled")

    def test_jobs_are_recoverable_from_a_new_manager_instance(self):
        created = self.manager.create("recovery")
        recovered = JobManager(self.db_path, max_workers=1)
        try:
            self.assertEqual(recovered.get(created["id"])["state"], "queued")
            self.assertEqual(len(recovered.list()), 1)
        finally:
            recovered.shutdown()

    def test_reconcile_stale_running_job_marks_it_failed(self):
        created = self.manager.create("orphaned")
        self.manager.update(created["id"], state="running", stage="analysis", progress=40)
        old_timestamp = datetime.fromtimestamp(time.time() - 3600, timezone.utc).isoformat()
        connection = sqlite3.connect(self.db_path)
        connection.execute(
            "UPDATE jobs SET updated_at = ? WHERE id = ?",
            (old_timestamp, created["id"]),
        )
        connection.commit()
        connection.close()

        recovered = self.manager.reconcile_stale(max_age_seconds=60)
        assert len(recovered) == 1
        final = self.manager.get(created["id"])
        self.assertEqual(final["state"], "failed")
        self.assertEqual(final["stage"], "stale_recovered")
        self.assertEqual(final["error"], "stale_job_recovered")


if __name__ == "__main__":
    unittest.main()
