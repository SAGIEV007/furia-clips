"""Backup and restore helpers for user-owned Furia Clips editorial data."""

from __future__ import annotations

import json
import os
import sqlite3
import stat
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from config import (
    DB_PATH,
    PERSISTENT_ANALYSES_DIR,
    PERSISTENT_BACKUPS_DIR,
    PERSISTENT_SCHEMA_PATH,
    PERSISTENT_TRANSCRIPTS_DIR,
    get_persistent_data_status,
)

BACKUP_FORMAT_VERSION = 1
MAX_RESTORE_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB of uncompressed SQLite data.
MAX_ANALYSIS_FILE_BYTES = 25 * 1024 * 1024
SAFE_ANALYSIS_SUFFIXES = {".json", ".jsonl", ".md", ".txt"}
SAFE_TRANSCRIPT_FILENAMES = {"transcript.txt", "transcript.json", "metadata.json"}
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


def _iter_safe_analysis_files():
    root = Path(PERSISTENT_ANALYSES_DIR).resolve()
    if not root.is_dir():
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink() or path.suffix.lower() not in SAFE_ANALYSIS_SUFFIXES:
            continue
        resolved = path.resolve()
        if os.path.commonpath([str(root), str(resolved)]) != str(root):
            continue
        if path.stat().st_size <= MAX_ANALYSIS_FILE_BYTES:
            yield path, resolved.relative_to(root).as_posix()


def _iter_safe_transcript_files():
    root = Path(PERSISTENT_TRANSCRIPTS_DIR).resolve()
    if not root.is_dir():
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink() or path.name not in SAFE_TRANSCRIPT_FILENAMES:
            continue
        resolved = path.resolve()
        if os.path.commonpath([str(root), str(resolved)]) != str(root):
            continue
        if path.stat().st_size <= MAX_RESTORE_BYTES:
            yield path, resolved.relative_to(root).as_posix()


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
    summary = {**status, "integrity": "missing", "projects": 0, "clips": 0, "feedback_events": 0, "archived_transcripts": 0}

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
                "archived_transcripts": len(list(Path(PERSISTENT_TRANSCRIPTS_DIR).glob("*/metadata.json"))),
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
            transcript_count = 0
            for transcript_file, relative in _iter_safe_transcript_files() or []:
                archive.write(transcript_file, arcname=f"transcripts/{relative}")
                transcript_count += 1
            manifest["transcript_file_count"] = transcript_count
            analysis_count = 0
            for analysis_file, relative in _iter_safe_analysis_files() or []:
                archive.write(analysis_file, arcname=f"analyses/{relative}")
                analysis_count += 1
            manifest["analysis_file_count"] = analysis_count
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
    normalized_name = str(member_name).replace("\\", "/")
    relative = Path(normalized_name)
    mode = (int(info.external_attr) >> 16) & 0o170000
    if info.is_dir() or info.file_size <= 0 or info.file_size > MAX_RESTORE_BYTES:
        raise PersistentDataError("O banco dentro do backup tem tamanho inválido.")
    if stat.S_ISLNK(mode) or ".." in relative.parts or relative.is_absolute():
        raise PersistentDataError("O backup contém um caminho de arquivo inválido.")
    return info


def _safe_auxiliary_members(archive: zipfile.ZipFile):
    """Validate transcript/analysis members before any database replacement."""
    transcripts = []
    analyses = []
    for member in archive.infolist():
        name = str(member.filename).replace("\\", "/")
        mode = (int(member.external_attr) >> 16) & 0o170000
        if member.is_dir():
            continue
        if stat.S_ISLNK(mode):
            if name.startswith("transcripts/") or name.startswith("analyses/"):
                raise PersistentDataError("O backup contém um symlink não permitido.")
            continue
        if name.startswith("transcripts/"):
            relative = Path(name.removeprefix("transcripts/"))
            if relative.is_absolute() or ".." in relative.parts or relative.name not in SAFE_TRANSCRIPT_FILENAMES:
                raise PersistentDataError("O backup contém um arquivo de transcrição inválido.")
            if member.file_size > MAX_RESTORE_BYTES:
                raise PersistentDataError("Uma transcrição do backup excede o tamanho permitido.")
            transcripts.append((member, relative))
        elif name.startswith("analyses/"):
            relative = Path(name.removeprefix("analyses/"))
            if relative.is_absolute() or ".." in relative.parts or relative.suffix.lower() not in SAFE_ANALYSIS_SUFFIXES:
                raise PersistentDataError("O backup contém um arquivo de análise inválido.")
            if member.file_size > MAX_ANALYSIS_FILE_BYTES:
                raise PersistentDataError("Uma análise do backup excede o tamanho permitido.")
            analyses.append((member, relative))
    return transcripts, analyses


def _read_or_infer_manifest(archive: zipfile.ZipFile):
    """Read a native manifest or recognize a safe manual editorial export.

    A manual export is accepted only when it has the canonical database member;
    the SQLite integrity and required-table checks still run before replacement.
    This supports user-selected folders copied from FuriaClipsData without
    weakening path validation or allowing arbitrary archives.
    """
    try:
        manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
        if "database/editorial_learning.sqlite3" not in archive.namelist():
            raise PersistentDataError("O backup não possui manifesto válido nem banco editorial canônico.")
        return {
            "format": "furia-clips-editorial-backup",
            "format_version": 0,
            "manual_import": True,
        }
    if not isinstance(manifest, dict) or manifest.get("format") != "furia-clips-editorial-backup":
        raise PersistentDataError("Este ZIP não foi criado pelo backup editorial do Furia Clips.")
    return manifest


def restore_editorial_backup(archive_path: str):
    """Validate a backup and atomically replace the persistent database.

    The current database is backed up first. Callers must ensure no processing
    is running before invoking this function. Native backups include a
    manifest; manual exports with the canonical database path are also accepted
    after the same SQLite, path and transcript validation.
    """
    if not archive_path or not os.path.isfile(archive_path):
        raise PersistentDataError("Arquivo de backup não encontrado.")
    if not zipfile.is_zipfile(archive_path):
        raise PersistentDataError("Selecione um arquivo ZIP de backup do Furia Clips.")

    with zipfile.ZipFile(archive_path, "r") as archive:
        info = _safe_member(archive, "database/editorial_learning.sqlite3")
        manifest = _read_or_infer_manifest(archive)
        transcript_members, analysis_members = _safe_auxiliary_members(archive)

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

            transcript_root = Path(PERSISTENT_TRANSCRIPTS_DIR).resolve()
            transcript_root.mkdir(parents=True, exist_ok=True)
            for member, relative in transcript_members:
                target = (transcript_root / relative).resolve()
                if os.path.commonpath([str(transcript_root), str(target)]) != str(transcript_root):
                    raise PersistentDataError("O backup contém um caminho de transcrição inseguro.")
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member, "r") as source, open(target, "wb") as destination_file:
                    destination_file.write(source.read(MAX_RESTORE_BYTES + 1))
                if target.stat().st_size > MAX_RESTORE_BYTES:
                    raise PersistentDataError("Uma transcrição do backup excede o tamanho permitido.")

            analysis_root = Path(PERSISTENT_ANALYSES_DIR).resolve()
            analysis_root.mkdir(parents=True, exist_ok=True)
            for member, relative in analysis_members:
                target = (analysis_root / relative).resolve()
                if os.path.commonpath([str(analysis_root), str(target)]) != str(analysis_root):
                    raise PersistentDataError("O backup contém um caminho de análise inseguro.")
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member, "r") as source, open(target, "wb") as destination_file:
                    destination_file.write(source.read(MAX_ANALYSIS_FILE_BYTES + 1))
                if target.stat().st_size > MAX_ANALYSIS_FILE_BYTES:
                    raise PersistentDataError("Uma análise do backup excede o tamanho permitido.")

    return {
        "restored": True,
        "backup_kind": "manual_import" if manifest.get("manual_import") else "native",
        "pre_restore_backup": pre_restore,
        "summary": get_editorial_data_summary(),
    }
