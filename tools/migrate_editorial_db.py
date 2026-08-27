"""Import a Furia 1/editorial_learning SQLite database into the local Studio.

Usage:
    python tools/migrate_editorial_db.py C:\\path\\editorial_learning.sqlite3

The source is opened read-only and copied with SQLite backup semantics. Existing
Studio data is preserved as a timestamped backup before replacement.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_TABLES = {"projects", "clips", "transcriptions", "clip_feedback", "jobs", "settings"}


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def count_tables(path: Path) -> dict[str, int]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        names = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return {name: int(connection.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]) for name in names}
    finally:
        connection.close()


def backup_copy(source: Path, destination: Path) -> None:
    source_connection = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    destination_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Importar uma base editorial local para o Furia Studio")
    parser.add_argument("source", type=Path)
    parser.add_argument("--data-dir", type=Path, default=None, help="Diretório FuriaStudioData de destino")
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    if not source.is_file():
        parser.error(f"Base de origem não encontrada: {source}")
    try:
        source_counts = count_tables(source)
    except sqlite3.DatabaseError as exc:
        parser.error(f"SQLite de origem inválido: {exc}")
    missing = sorted(REQUIRED_TABLES - set(source_counts))
    if missing:
        parser.error("A base não parece ser Furia 1/editorial_learning; faltam: " + ", ".join(missing))

    configured_dir = os.environ.get("FURIA_CLIPS_DATA_DIR", "").strip()
    data_dir = (args.data_dir or (Path(configured_dir).expanduser() if configured_dir else (Path.home() / "FuriaStudioData"))).resolve()
    database_dir = data_dir / "database"
    backup_dir = data_dir / "backups"
    database_dir.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)
    destination = database_dir / "editorial_learning.sqlite3"
    backup = None
    if destination.exists():
        backup = backup_dir / f"before-editorial-import-{now_stamp()}.sqlite3"
        shutil.copy2(destination, backup)
    backup_copy(source, destination)
    connection = sqlite3.connect(destination)
    try:
        connection.execute("CREATE TABLE IF NOT EXISTS studio_project_meta (project_id INTEGER PRIMARY KEY, payload TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL)")
        connection.commit()
    finally:
        connection.close()
    report = {
        "source": str(source),
        "destination": str(destination),
        "backup": str(backup) if backup else None,
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "tables": source_counts,
        "source_unchanged": True,
    }
    report_path = data_dir / "migration-last.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
