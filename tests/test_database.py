import os
import tempfile
import unittest

import database


class DatabaseMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_path = database.DB_PATH
        database.DB_PATH = os.path.join(self.tempdir.name, "furia.sqlite3")
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.original_path
        self.tempdir.cleanup()

    def test_new_schema_persists_score_and_feedback(self):
        project_id = database.create_project("Teste", "uploads/test.mp4")
        clip_id = database.save_clip(project_id, "exports/test.mp4", 0, 10, 10, 60, True, 70, "Texto")
        database.update_clip_editorial_score(
            clip_id, 78, {"hook": 80, "flow": 75}, 0.82, "v1-explainable"
        )
        database.save_clip_feedback(clip_id, "approved", {"start": 0.2}, "bom")

        clip = database.get_clips(project_id)[0]
        self.assertEqual(clip["viral_score"], 78)
        self.assertEqual(clip["review_status"], "approved")
        self.assertEqual(database.get_clip_feedback(clip_id)[0]["action"], "approved")

    def test_review_flags_survive_database_round_trip(self):
        project_id = database.create_project("Persistência de alertas", "uploads/alertas.mp4")
        clip_id = database.save_clip(project_id, "exports/alerta.mp4", 0, 20, 20, 82, True, 0, "Alegação nominal.")
        database.update_clip_editorial_score(
            clip_id,
            82,
            {"hook": 80, "context_completeness": 72},
            0.78,
            review_flags={"needs_fact_review": True, "needs_legal_review": True},
        )
        clip = database.get_clips(project_id)[0]
        self.assertTrue(clip["review_flags"]["needs_fact_review"])
        self.assertTrue(clip["review_flags"]["needs_legal_review"])


if __name__ == "__main__":
    unittest.main()


    def test_reprocessing_same_editorial_window_reuses_clip_and_feedback(self):
        project_id = database.create_project("Live", "uploads/live-original.mp4")
        first_id = database.save_clip(
            project_id, "exports/clip-v1.mp4", 15.0, 55.0, 40.0, 72, True, 0, "Tese completa."
        )
        database.save_clip_feedback(first_id, "approved", note="Manter a conclusão")
        second_id = database.save_clip(
            project_id, "exports/clip-v2.mp4", 15.0, 55.0, 40.0, 79, True, 0, "  Tese   completa. "
        )

        self.assertEqual(first_id, second_id)
        clips = database.get_clips(project_id)
        self.assertEqual(len(clips), 1)
        self.assertEqual(clips[0]["viral_score"], 79)
        self.assertTrue(clips[0]["editorial_key"])
        self.assertEqual(database.get_clip_feedback(second_id)[0]["action"], "approved")


    def test_daily_progress_counts_only_approved_clips_toward_editorial_goal(self):
        project_id = database.create_project("Meta diária", "uploads/meta.mp4")
        approved = database.save_clip(project_id, "exports/aprovado.mp4", 0, 20, 20, 75, True, 0, "Aprovado")
        pending = database.save_clip(project_id, "exports/pendente.mp4", 30, 50, 20, 70, True, 0, "Pendente")
        review = database.save_clip(project_id, "exports/revisar.mp4", 60, 80, 20, 68, False, 0, "Revisar")
        database.save_clip_feedback(approved, "approved")
        database.save_clip_feedback(review, "needs_review")

        progress = database.get_daily_editorial_progress(target_min=2, target_max=3)
        self.assertEqual(progress["approved"], 1)
        self.assertEqual(progress["pending"], 1)
        self.assertEqual(progress["needs_review"], 1)
        self.assertEqual(progress["review_queue"], 2)
        self.assertEqual(progress["remaining_to_minimum"], 1)
        self.assertFalse(progress["target_reached"])
        self.assertNotEqual(approved, pending)


    def test_restore_feedback_snapshot_by_editorial_key_is_idempotent(self):
        project_id = database.create_project("Restauração", "uploads/restauracao.mp4")
        clip_id = database.save_clip(
            project_id, "exports/restauracao.mp4", 5, 25, 20, 70, True, 0, "Contexto completo."
        )
        clip = database.get_clip(clip_id)
        record = {
            "editorial_key": clip["editorial_key"],
            "action": "approved",
            "reason_code": "contexto_completo",
            "quality_tags": ["hook", "completo"],
            "created_at": "2026-08-15T00:00:00+00:00",
        }

        first = database.restore_feedback_snapshot([record])
        second = database.restore_feedback_snapshot([record])

        self.assertEqual(first["imported"], 1)
        self.assertEqual(second["already_current"], 1)
        self.assertEqual(database.get_clip(clip_id)["review_status"], "approved")
        self.assertEqual(database.get_clip_feedback(clip_id)[0]["reason_code"], "contexto_completo")

    def test_restore_feedback_snapshot_does_not_overwrite_newer_local_decision(self):
        project_id = database.create_project("Restauração recente", "uploads/recente.mp4")
        clip_id = database.save_clip(project_id, "exports/recente.mp4", 0, 12, 12, 60, False, 0, "Decisão local.")
        clip = database.get_clip(clip_id)
        database.save_clip_feedback(clip_id, "rejected", reason_code="sem_contexto")
        old_record = {
            "editorial_key": clip["editorial_key"],
            "action": "approved",
            "reason_code": "contexto_completo",
            "quality_tags": [],
            "created_at": "2000-01-01T00:00:00+00:00",
        }

        result = database.restore_feedback_snapshot([old_record])

        self.assertEqual(result["skipped_older"], 1)
        self.assertEqual(database.get_clip(clip_id)["review_status"], "rejected")

    def test_project_library_exposes_clip_and_review_totals(self):
        project_id = database.create_project("Biblioteca", "uploads/biblioteca.mp4")
        approved = database.save_clip(project_id, "exports/a.mp4", 0, 15, 15, 70, True, 0, "A")
        database.save_clip(project_id, "exports/b.mp4", 20, 35, 15, 65, False, 0, "B")
        database.save_clip_feedback(approved, "approved")

        project = next(item for item in database.get_all_projects() if item["id"] == project_id)
        self.assertEqual(project["clip_count"], 2)
        self.assertEqual(project["approved_count"], 1)
        self.assertEqual(project["review_count"], 1)


    def test_source_signature_separates_same_basename_from_different_files(self):
        first_path = os.path.join(self.tempdir.name, "notebook-a", "entrevista.mp4")
        second_path = os.path.join(self.tempdir.name, "notebook-b", "entrevista.mp4")
        os.makedirs(os.path.dirname(first_path), exist_ok=True)
        os.makedirs(os.path.dirname(second_path), exist_ok=True)
        with open(first_path, "wb") as handle:
            handle.write(b"fonte-a" * 2048)
        with open(second_path, "wb") as handle:
            handle.write(b"fonte-b" * 2048)

        first_project = database.create_project("Fonte A", first_path)
        database.save_clip(first_project, "exports/a.mp4", 10, 25, 15, 70, True, 0, "Trecho da fonte A")
        second_project = database.create_project("Fonte B", second_path)
        database.save_clip(second_project, "exports/b.mp4", 10, 25, 15, 70, True, 0, "Trecho da fonte B")

        second_fingerprints = database.get_existing_clip_fingerprints(second_path)

        assert database.get_project(first_project)["source_signature"]
        assert database.get_project(second_project)["source_signature"]
        assert len(second_fingerprints) == 1
        assert second_fingerprints[0]["text"] == "Trecho da fonte B"


    def test_restore_feedback_snapshot_falls_back_to_source_signature_and_window(self):
        source_path = os.path.join(self.tempdir.name, "downloads", "entrevista.mp4")
        os.makedirs(os.path.dirname(source_path), exist_ok=True)
        with open(source_path, "wb") as handle:
            handle.write(b"same-physical-source" * 2048)

        project_id = database.create_project("Entrevista", source_path)
        clip_id = database.save_clip(project_id, "exports/clip.mp4", 12.0, 42.0, 30.0, 78, True, 0, "Contexto completo")
        signature = database.get_project(project_id)["source_signature"]

        result = database.restore_feedback_snapshot([{
            "editorial_key": "path-dependent-key-from-another-notebook",
            "source_signature": signature,
            "start_seconds": 12.0,
            "end_seconds": 42.0,
            "action": "approved",
            "reason_code": "contexto_completo",
            "quality_tags": ["hook"],
            "created_at": "2026-08-15T00:00:00+00:00",
        }])

        assert result["imported"] == 1
        assert database.get_clip(clip_id)["review_status"] == "approved"
