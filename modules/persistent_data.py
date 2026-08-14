"""Backup and restore helpers for user-owned Furia Clips editorial data."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from config import DB_PATH, PERSISTENT_BACKUPS_DIR, PERSISTENT_SCHEMA_PATH, get_persistent_data_status

BACKUP_FORMAT_VERSION = 1
MAX_RESTORE_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB of uncompressed SQLite data.
REQUIRED_TABLES = {"settings", "projects", "clips", "transcriptions", "clip_feedback"}


class PersistentDataError(RuntimeError):
    pass


def _timestamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _sqlite_snapshot(source_path: str, destination_path: str):
    source = sqlite3.connect(source_path)
    destination = sqlite3.connect(destination_path)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()


def _validate_sqlite_database(path: str):
    try:
        # O caminho normal funciona em Windows e Linux; a existência já foi
        # validada pelo chamador, portanto não há risco de criar um banco vazio.
        connection = sqlite3.connect(str(Path(path).resolve()))
    except sqlite3.Error as exc:
        raise PersistentDataError("O arquivo de dados não é um banco SQLite legível.") from exc
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise PersistentDataError("O banco restaurado falhou na verificação de integridade.")
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        missing = REQUIRED_TABLES - tables
        if missing:
            raise PersistentDataError(
                "O backup não contém as tabelas editoriais esperadas: " + ", ".join(sorted(missing))
            )
    finally:
        connection.close()


def get_editorial_data_summary():
    """Return a non-sensitive, UI-ready summary of persistent editorial storage."""
    status = get_persistent_data_status()
    summary = {**status, "integrity": "missing", "projects": 0, "clips": 0, "feedback_events": 0}
    if not os.path.isfile(DB_PATH):
        return summary
    try:
        _validate_sqlite_database(DB_PATH)
        connection = sqlite3.connect(DB_PATH)
        try:
            summary.update({
                "integrity": "ok",
                "projects": connection.execute("SELECT COUNT(*) FROM projects").fetchone()[0],
                "clips": connection.execute("SELECT COUNT(*) FROM clips").fetchone()[0],
                "feedback_events": connection.execute("SELECT COUNT(*) FROM clip_feedback").fetchone()[0],
            })
        finally:
            connection.close()
    except (PersistentDataError, sqlite3.Error):
        summary["integrity"] = "needs_attention"
    return summary


def create_editorial_backup():
    """Create a portable ZIP with a consistent SQLite snapshot and manifest."""
    if not os.path.isfile(DB_PATH):
        raise PersistentDataError("Ainda não existe uma base editorial para fazer backup.")
    _validate_sqlite_database(DB_PATH)
    os.makedirs(PERSISTENT_BACKUPS_DIR, exist_ok=True)
    archive_path = os.path.join(PERSISTENT_BACKUPS_DIR, f"furia-editorial-backup-{_timestamp()}.zip")

    with tempfile.TemporaryDirectory(prefix="furia-backup-") as temp_dir:
        snapshot_path = os.path.join(temp_dir, "editorial_learning.sqlite3")
        _sqlite_snapshot(DB_PATH, snapshot_path)
        manifest = {
            "format": "furia-clips-editorial-backup",
            "format_version": BACKUP_FORMAT_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "database_file": "database/editorial_learning.sqlite3",
            "summary": get_editorial_data_summary(),
        }
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(snapshot_path, arcname=manifest["database_file"])
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            if os.path.isfile(PERSISTENT_SCHEMA_PATH):
                archive.write(PERSISTENT_SCHEMA_PATH, arcname="schema_version.json")

    return {
        "path": archive_path,
        "filename": os.path.basename(archive_path),
        "size_bytes": os.path.getsize(archive_path),
        "summary": get_editorial_data_summary(),
    }


def _safe_member(archive: zipfile.ZipFile, member_name: str):
    try:
        info = archive.getinfo(member_name)
    except KeyError as exc:
        raise PersistentDataError("O arquivo selecionado não é um backup editorial do Furia Clips.") from exc
    if info.is_dir() or info.file_size <= 0 or info.file_size > MAX_RESTORE_BYTES:
        raise PersistentDataError("O banco dentro do backup tem tamanho inválido.")
    if ".." in Path(member_name).parts or Path(member_name).is_absolute():
        raise PersistentDataError("O backup contém um caminho de arquivo inválido.")
    return info


def restore_editorial_backup(archive_path: str):
    """Validate a backup and atomically replace the persistent database.

    The current database is backed up first. Callers must ensure no processing is
    running before invoking this function.
    """
    if not archive_path or not os.path.isfile(archive_path):
        raise PersistentDataError("Arquivo de backup não encontrado.")
    if not zipfile.is_zipfile(archive_path):
        raise PersistentDataError("Selecione um arquivo ZIP de backup do Furia Clips.")

    with zipfile.ZipFile(archive_path, "r") as archive:
        info = _safe_member(archive, "database/editorial_learning.sqlite3")
        try:
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
        except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PersistentDataError("O backup não possui manifesto válido.") from exc
        if manifest.get("format") != "furia-clips-editorial-backup":
            raise PersistentDataError("Este ZIP não foi criado pelo backup editorial do Furia Clips.")

        with tempfile.TemporaryDirectory(prefix="furia-restore-") as temp_dir:
            candidate = os.path.join(temp_dir, "editorial_learning.sqlite3")
            with archive.open(info, "r") as source, open(candidate, "wb") as destination:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    destination.write(chunk)
            _validate_sqlite_database(candidate)

            pre_restore = create_editorial_backup() if os.path.isfile(DB_PATH) else None
            destination_path = Path(DB_PATH)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            replacement = destination_path.with_suffix(".restore.sqlite3")
            _sqlite_snapshot(candidate, str(replacement))
            os.replace(replacement, destination_path)

    return {
        "restored": True,
        "pre_restore_backup": pre_restore,
        "summary": get_editorial_data_summary(),
    }
