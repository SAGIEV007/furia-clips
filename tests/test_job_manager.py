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

    def test_cancelled_queued_job_never_starts_target(self):
        started = []
        created = self.manager.create("queued-cancel")
        requested = self.manager.request_cancel(created["id"])
        self.assertEqual(requested["state"], "cancelled")
        self.assertEqual(requested["error"], "cancelled_before_start")

        def worker(_ctx):
            started.append(True)
            return {}

        self.manager._run(created["id"], worker)
        final = self.manager.get(created["id"])
        self.assertEqual(started, [])
        self.assertEqual(final["state"], "cancelled")
        self.assertEqual(final["stage"], "cancelled")
        self.assertEqual(final["error"], "cancelled_before_start")

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

    def test_new_manager_recovers_recent_running_job_as_orphan(self):
        created = self.manager.create("recent-orphan")
        self.manager.update(created["id"], state="running", stage="rendering", progress=15)
        recovered = JobManager(self.db_path, max_workers=1)
        try:
            final = recovered.get(created["id"])
            self.assertEqual(final["state"], "failed")
            self.assertEqual(final["stage"], "stale_recovered")
            self.assertEqual(final["error"], "stale_job_recovered")
        finally:
            recovered.shutdown()

    def test_new_manager_recovers_inactive_running_job(self):
        created = self.manager.create("orphaned-on-startup")
        self.manager.update(created["id"], state="running", stage="rendering", progress=15)
        old_timestamp = datetime.fromtimestamp(time.time() - 3600, timezone.utc).isoformat()
        connection = sqlite3.connect(self.db_path)
        connection.execute("UPDATE jobs SET updated_at = ? WHERE id = ?", (old_timestamp, created["id"]))
        connection.commit()
        connection.close()

        recovered = JobManager(self.db_path, max_workers=1)
        try:
            final = recovered.get(created["id"])
            self.assertEqual(final["state"], "failed")
            self.assertEqual(final["stage"], "stale_recovered")
            self.assertEqual(final["error"], "stale_job_recovered")
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
        self.assertEqual(len(recovered), 1)
        final = self.manager.get(created["id"])
        self.assertEqual(final["state"], "failed")
        self.assertEqual(final["stage"], "stale_recovered")
        self.assertEqual(final["error"], "stale_job_recovered")

    def test_operation_cancelled_is_persisted_as_cancelled_state(self):
        from modules.cancellation import OperationCancelled

        def worker(_ctx):
            raise OperationCancelled("parado no worker")

        created = self.manager.submit("cancelled-operation", worker)
        deadline = time.time() + 3
        final = None
        while time.time() < deadline:
            final = self.manager.get(created["id"])
            if final and final["state"] in {"completed", "failed", "cancelled"}:
                break
            time.sleep(0.02)

        self.assertIsNotNone(final)
        self.assertEqual(final["state"], "cancelled")
        self.assertEqual(final["stage"], "cancelled")
        self.assertIn("parado no worker", final["error"])

    def test_job_events_are_persisted_and_diagnostic_is_correlated(self):
        created = self.manager.create("diagnostic")
        self.manager.update(
            created["id"],
            state="running",
            stage="transcription",
            progress=35,
            message="Transcrevendo",
            event_name="transcription.started",
            details={"engine": "whisper", "secret": "não deveria ser segredo"},
        )
        self.manager.update(
            created["id"],
            state="failed",
            stage="failed",
            message="Job falhou",
            error="erro de teste",
        )

        events = self.manager.events(created["id"])
        diagnostic = self.manager.diagnostic(created["id"])
        self.assertGreaterEqual(len(events), 3)
        self.assertEqual([event["sequence"] for event in events], list(range(1, len(events) + 1)))
        self.assertTrue(all(event["job_id"] == created["id"] for event in events))
        self.assertEqual(events[1]["event_name"], "transcription.started")
        self.assertEqual(events[-1]["details"]["error"], "erro de teste")
        self.assertEqual(diagnostic["job"]["state"], "failed")
        self.assertEqual(diagnostic["breadcrumbs"][-1]["event_id"], events[-1]["event_id"])

    def test_job_context_note_persists_without_changing_job_state(self):
        created = self.manager.create("breadcrumb")
        context = self.manager  # replaced below with the public context class
        from modules.job_manager import JobContext
        context = JobContext(self.manager, created["id"])
        before = self.manager.get(created["id"])
        note = context.note(
            "Legenda manual recebida",
            stage="transcription",
            event_name="transcription.manual_received",
            details={"segment_count": 42},
        )
        after = self.manager.get(created["id"])
        self.assertEqual(note["event_name"], "transcription.manual_received")
        self.assertEqual(note["details"]["segment_count"], 42)
        self.assertEqual(after["state"], before["state"])
        self.assertEqual(after["progress"], before["progress"])

    def test_event_details_are_bounded(self):
        created = self.manager.create("bounded")
        event = self.manager.record_event(
            created["id"],
            event_name="bounded.details",
            details={"long": "x" * 5000, "items": list(range(100))},
        )
        self.assertLessEqual(len(event["details"]["long"]), 500)
        self.assertLessEqual(len(event["details"]["items"]), 20)

    def test_legacy_jobs_can_receive_event_history_after_migration(self):
        created = self.manager.create("legacy")
        self.manager.shutdown()
        migrated = JobManager(self.db_path, max_workers=1)
        try:
            event = migrated.record_event(created["id"], event_name="migration.checked", message="Banco legado preservado")
            self.assertEqual(migrated.events(created["id"])[-1]["event_id"], event["event_id"])
            self.assertEqual(migrated.diagnostic(created["id"])["job"]["type"], "legacy")
        finally:
            migrated.shutdown()
            self.manager = JobManager(self.db_path, max_workers=1)

    def test_event_retention_keeps_only_the_latest_events(self):
        self.manager.shutdown()
        self.manager = JobManager(self.db_path, max_workers=1, event_retention_limit=3)
        created = self.manager.create("retention")
        for index in range(5):
            self.manager.record_event(created["id"], event_name=f"retention.{index}", message=f"evento {index}")
        events = self.manager.events(created["id"])
        self.assertEqual(len(events), 3)
        self.assertEqual([event["event_name"] for event in events], ["retention.2", "retention.3", "retention.4"])

    def test_unknown_job_has_no_events_and_cannot_record(self):
        self.assertIsNone(self.manager.events("does-not-exist"))
        with self.assertRaises(KeyError):
            self.manager.record_event("does-not-exist", event_name="invalid")


if __name__ == "__main__":
    unittest.main()
