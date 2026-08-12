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


if __name__ == "__main__":
    unittest.main()
