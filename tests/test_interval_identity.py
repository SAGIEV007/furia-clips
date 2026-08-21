import os

import database
from modules.source_interval import (
    normalize_processing_interval,
    processing_interval_identity,
    transcript_digest,
)


def test_interval_identity_ignores_temporary_path_and_changes_with_scope():
    interval = normalize_processing_interval("01:00", "05:00", 900)
    first = processing_interval_identity(
        "/tmp/furia-interval-a.mp4",
        interval,
        source_signature="abc123",
    )
    second = processing_interval_identity(
        "/another/tmp/furia-interval-b.mp4",
        interval,
        source_signature="abc123",
    )
    other = processing_interval_identity(
        "/another/tmp/furia-interval-b.mp4",
        normalize_processing_interval("05:00", "09:00", 900),
        source_signature="abc123",
    )

    assert first == second
    assert first != other
    assert first.startswith("interval-v1-")


def test_transcript_digest_changes_when_canonical_content_changes():
    base = {"language": "pt", "segments": [{"start": 0, "end": 2, "text": "A tese."}]}
    changed = {"language": "pt", "segments": [{"start": 0, "end": 2, "text": "A tese mudou."}]}

    assert transcript_digest(base) != transcript_digest(changed)
    assert transcript_digest(base) == transcript_digest(dict(base))


def test_database_persists_interval_identity_and_queries_only_same_scope(tmp_path):
    original_path = database.DB_PATH
    database.DB_PATH = os.path.join(tmp_path, "furia.sqlite3")
    try:
        database.init_db()
        interval_a = normalize_processing_interval("01:00", "05:00", 900)
        interval_b = normalize_processing_interval("05:00", "09:00", 900)
        identity_a = processing_interval_identity("live.mp4", interval_a, source_signature="same")
        identity_b = processing_interval_identity("live.mp4", interval_b, source_signature="same")
        project_a = database.create_project(
            "Faixa A",
            "C:/origem/live.mp4",
            source_signature="same",
            processing_identity=identity_a,
            processing_interval=interval_a,
        )
        project_b = database.create_project(
            "Faixa B",
            "D:/outra/live.mp4",
            source_signature="same",
            processing_identity=identity_b,
            processing_interval=interval_b,
        )
        database.save_clip(project_a, "exports/a.mp4", 10, 20, 10, 70, True, 0, "A")
        database.save_clip(project_b, "exports/b.mp4", 10, 20, 10, 70, True, 0, "B")

        same_scope = database.get_existing_clip_fingerprints(
            "D:/cache/live.mp4",
            processing_identity=identity_a,
        )
        other_scope = database.get_existing_clip_fingerprints(
            "D:/cache/live.mp4",
            processing_identity=identity_b,
        )

        assert len(same_scope) == 1
        assert same_scope[0]["processing_identity"] == identity_a
        assert len(other_scope) == 1
        assert other_scope[0]["processing_identity"] == identity_b
    finally:
        database.DB_PATH = original_path
