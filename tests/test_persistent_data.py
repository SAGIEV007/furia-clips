import json
import os
import sqlite3


def _create_legacy_database(path):
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE projects (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        connection.execute("INSERT INTO projects (name) VALUES ('Decisões editoriais antigas')")
        connection.commit()
    finally:
        connection.close()


def test_legacy_database_is_migrated_to_external_persistent_directory(monkeypatch, tmp_path):
    import config

    legacy_dir = tmp_path / "checkout" / "data"
    legacy_dir.mkdir(parents=True)
    legacy_db = legacy_dir / "furia_clips.db"
    _create_legacy_database(str(legacy_db))

    persistent_root = tmp_path / "FuriaClipsData"
    database_dir = persistent_root / "database"
    backup_dir = persistent_root / "backups"
    target_db = database_dir / "editorial_learning.sqlite3"

    monkeypatch.setattr(config, "LEGACY_DB_PATH", str(legacy_db))
    monkeypatch.setattr(config, "PERSISTENT_DATA_DIR", str(persistent_root))
    monkeypatch.setattr(config, "PERSISTENT_DATABASE_DIR", str(database_dir))
    monkeypatch.setattr(config, "PERSISTENT_PROJECTS_DIR", str(persistent_root / "projects"))
    monkeypatch.setattr(config, "PERSISTENT_TRANSCRIPTS_DIR", str(persistent_root / "transcripts"))
    monkeypatch.setattr(config, "PERSISTENT_ANALYSES_DIR", str(persistent_root / "analyses"))
    monkeypatch.setattr(config, "PERSISTENT_DECISIONS_DIR", str(persistent_root / "clip_decisions"))
    monkeypatch.setattr(config, "PERSISTENT_EXPORTS_DIR", str(persistent_root / "exports"))
    monkeypatch.setattr(config, "PERSISTENT_BACKUPS_DIR", str(backup_dir))
    monkeypatch.setattr(config, "PERSISTENT_MEDIA_INDEX_DIR", str(persistent_root / "media_index"))
    monkeypatch.setattr(config, "PERSISTENT_SCHEMA_PATH", str(persistent_root / "schema_version.json"))
    monkeypatch.setattr(config, "DB_PATH", str(target_db))

    config._ensure_persistent_data_layout()

    assert legacy_db.exists(), "A cópia antiga nunca deve ser removida pela migração."
    assert target_db.exists()
    assert list(backup_dir.glob("legacy-furia-clips-*.sqlite3"))
    with sqlite3.connect(target_db) as connection:
        assert connection.execute("SELECT name FROM projects").fetchone()[0] == "Decisões editoriais antigas"
    with open(persistent_root / "schema_version.json", encoding="utf-8") as handle:
        metadata = json.load(handle)
    assert metadata["migrated_from"] == str(legacy_db)


def test_persistent_status_never_exposes_secret_settings(monkeypatch, tmp_path):
    import config

    persistent_root = tmp_path / "FuriaClipsData"
    db_path = persistent_root / "database" / "editorial_learning.sqlite3"
    monkeypatch.setattr(config, "PERSISTENT_DATA_DIR", str(persistent_root))
    monkeypatch.setattr(config, "PERSISTENT_BACKUPS_DIR", str(persistent_root / "backups"))
    monkeypatch.setattr(config, "DB_PATH", str(db_path))
    monkeypatch.setattr(config, "LEGACY_DB_PATH", str(tmp_path / "legacy.sqlite3"))

    status = config.get_persistent_data_status()
    assert status["data_dir"] == str(persistent_root)
    assert "gemini" not in json.dumps(status).lower()


def _configure_persistent_module(monkeypatch, tmp_path):
    import config
    import modules.persistent_data as persistent_data

    root = tmp_path / "FuriaClipsData"
    database_dir = root / "database"
    backup_dir = root / "backups"
    transcripts_dir = root / "transcripts"
    db_path = database_dir / "editorial_learning.sqlite3"
    schema_path = root / "schema_version.json"
    for module in (config, persistent_data):
        monkeypatch.setattr(module, "DB_PATH", str(db_path))
        monkeypatch.setattr(module, "PERSISTENT_BACKUPS_DIR", str(backup_dir))
        monkeypatch.setattr(module, "PERSISTENT_TRANSCRIPTS_DIR", str(transcripts_dir))
    monkeypatch.setattr(config, "PERSISTENT_DATA_DIR", str(root))
    monkeypatch.setattr(config, "PERSISTENT_DATABASE_DIR", str(database_dir))
    monkeypatch.setattr(config, "PERSISTENT_SCHEMA_PATH", str(schema_path))
    return root, db_path, backup_dir


def _create_editorial_schema(path, project_name="Projeto atual"):
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE projects (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
            CREATE TABLE clips (id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL);
            CREATE TABLE transcriptions (id INTEGER PRIMARY KEY, project_id INTEGER NOT NULL);
            CREATE TABLE clip_feedback (id INTEGER PRIMARY KEY, clip_id INTEGER NOT NULL, action TEXT NOT NULL);
            """
        )
        connection.execute("INSERT INTO projects (name) VALUES (?)", (project_name,))
        connection.execute("INSERT INTO clips (project_id) VALUES (1)")
        connection.execute("INSERT INTO clip_feedback (clip_id, action) VALUES (1, 'approved')")
        connection.commit()
    finally:
        connection.close()


def test_portable_backup_and_restore_preserve_editorial_decisions(monkeypatch, tmp_path):
    import modules.persistent_data as persistent_data

    _root, db_path, backup_dir = _configure_persistent_module(monkeypatch, tmp_path)
    db_path.parent.mkdir(parents=True)
    transcript_dir = _root / "transcripts" / "live_hash"
    transcript_dir.mkdir(parents=True)
    (transcript_dir / "transcript.txt").write_text("00:00:00.000 contexto completo\n", encoding="utf-8")
    (transcript_dir / "transcript.json").write_text('{"segments": []}', encoding="utf-8")
    (transcript_dir / "metadata.json").write_text('{"source": "public_subtitle"}', encoding="utf-8")
    _create_editorial_schema(str(db_path), "Versão preservada")

    backup = persistent_data.create_editorial_backup()
    assert os.path.isfile(backup["path"])
    assert backup["summary"]["feedback_events"] == 1
    assert backup["summary"]["archived_transcripts"] == 1
    import zipfile
    with zipfile.ZipFile(backup["path"]) as archive:
        assert "transcripts/live_hash/transcript.txt" in archive.namelist()
        assert "transcripts/live_hash/transcript.json" in archive.namelist()
        assert "transcripts/live_hash/metadata.json" in archive.namelist()

    with sqlite3.connect(db_path) as connection:
        connection.execute("UPDATE projects SET name = 'Versão descartável'")
        connection.commit()

    restored = persistent_data.restore_editorial_backup(backup["path"])
    assert restored["restored"] is True
    assert restored["pre_restore_backup"] is not None
    assert list(backup_dir.glob("furia-editorial-backup-*.zip"))
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT name FROM projects").fetchone()[0] == "Versão preservada"
    assert (transcript_dir / "transcript.txt").read_text(encoding="utf-8").startswith("00:00:00.000")


def test_restore_rejects_non_editorial_zip(monkeypatch, tmp_path):
    import modules.persistent_data as persistent_data

    _root, _db_path, backup_dir = _configure_persistent_module(monkeypatch, tmp_path)
    backup_dir.mkdir(parents=True)
    invalid = backup_dir / "invalido.zip"
    import zipfile
    with zipfile.ZipFile(invalid, "w") as archive:
        archive.writestr("manifest.json", "{}")
    import pytest
    with pytest.raises(persistent_data.PersistentDataError):
        persistent_data.restore_editorial_backup(str(invalid))


def test_manual_editorial_zip_without_manifest_is_imported_safely(monkeypatch, tmp_path):
    import modules.persistent_data as persistent_data
    import zipfile

    root, db_path, backup_dir = _configure_persistent_module(monkeypatch, tmp_path)
    db_path.parent.mkdir(parents=True)
    source_db = tmp_path / "manual-source.sqlite3"
    _create_editorial_schema(str(source_db), "Importação manual")
    transcript_dir = root / "manual-transcripts"
    transcript_dir.mkdir(parents=True)
    archive_path = backup_dir / "manual-export.zip"
    backup_dir.mkdir(parents=True)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(source_db, "database/editorial_learning.sqlite3")
        archive.writestr("transcripts/manual/transcript.txt", "00:00:00.000 decisão preservada\n")
        archive.writestr("transcripts/manual/metadata.json", '{"source":"manual"}')

    restored = persistent_data.restore_editorial_backup(str(archive_path))

    assert restored["restored"] is True
    assert restored["backup_kind"] == "manual_import"
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT name FROM projects").fetchone()[0] == "Importação manual"
    assert (root / "transcripts" / "manual" / "transcript.txt").exists()
