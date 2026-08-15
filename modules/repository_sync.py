"""Safe Git synchronization for the local Furia Clips workspace.

The application keeps editorial learning in ``FuriaClipsData``.  Only a
sanitized feedback snapshot may be copied to the private repository.  Raw
SQLite data, source paths, media, transcripts, notes and API keys never enter
the Git synchronization flow.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import BASE_DIR
from database import get_db


SYNC_FORMAT = "furia-clips-editorial-feedback"
SYNC_FORMAT_VERSION = 2
DEFAULT_BRANCH = "manus/rebuild-opus-parity"
SNAPSHOT_RELATIVE_PATH = Path("data") / "editorial_feedback_snapshot.json"


class RepositorySyncError(RuntimeError):
    """Expected, user-facing repository synchronization error."""


def _repo_path(repo_path: str | None = None) -> Path:
    candidate = Path(repo_path or os.environ.get("FURIA_CLIPS_REPO_DIR") or BASE_DIR).expanduser().resolve()
    if not (candidate / ".git").exists():
        raise RepositorySyncError("A pasta do Furia Clips não contém um checkout Git válido.")
    return candidate


def _branch(repo: Path) -> str:
    return os.environ.get("FURIA_GIT_BRANCH", DEFAULT_BRANCH).strip() or DEFAULT_BRANCH


def _run_git(repo: Path, *args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(repo),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RepositorySyncError("Git não foi encontrado neste computador.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RepositorySyncError("A operação Git demorou mais do que o limite seguro e foi interrompida.") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        raise RepositorySyncError((detail[-1] if detail else "A operação Git falhou.")[:300])
    return result


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _quality_tags(value: Any) -> list[str]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            value = []
    if not isinstance(value, list):
        return []
    return [str(item).strip()[:48] for item in value if str(item).strip()][:12]


def _review_metadata(value: Any) -> dict[str, Any]:
    """Allowlist non-sensitive provenance fields from a feedback adjustment."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            value = {}
    if not isinstance(value, dict):
        return {}
    metadata = value.get("_review_metadata") if isinstance(value.get("_review_metadata"), dict) else value
    result: dict[str, Any] = {}
    origin = str(metadata.get("candidate_origin") or "").strip()[:40]
    if origin in {"gemini_primary", "ollama_primary", "local_primary", "local_fallback"}:
        result["candidate_origin"] = origin
    source = str(metadata.get("selection_source") or "").strip()[:24]
    if source in {"gemini", "llm", "nlp", "local"}:
        result["selection_source"] = source
    try:
        confidence = float(metadata.get("confidence"))
    except (TypeError, ValueError):
        confidence = None
    if confidence is not None and 0 <= confidence <= 1:
        result["confidence"] = round(confidence, 4)
    return result


def _feedback_snapshot_metadata(repo: Path) -> dict[str, Any]:
    """Read only non-sensitive snapshot metadata for transparent cross-device status."""
    target = repo / SNAPSHOT_RELATIVE_PATH
    metadata = {
        "feedback_snapshot_present": target.is_file(),
        "feedback_snapshot_valid": False,
        "feedback_snapshot_consistent": False,
        "feedback_snapshot_records": 0,
        "feedback_snapshot_version": None,
        "feedback_snapshot_generated_at": None,
    }
    if not target.is_file():
        return metadata
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return metadata
    if not isinstance(payload, dict) or payload.get("format") != SYNC_FORMAT:
        return metadata
    records = payload.get("records")
    try:
        version = int(payload.get("format_version") or 0) or None
    except (TypeError, ValueError):
        version = None
    records_count = len(records) if isinstance(records, list) else 0
    declared_count = payload.get("record_count")
    count_consistent = True
    if declared_count is not None:
        try:
            count_consistent = int(declared_count) == records_count
        except (TypeError, ValueError):
            count_consistent = False
    valid = isinstance(records, list) and version == SYNC_FORMAT_VERSION and count_consistent
    metadata.update(
        {
            "feedback_snapshot_valid": valid,
            "feedback_snapshot_consistent": count_consistent,
            "feedback_snapshot_records": records_count,
            "feedback_snapshot_version": version,
            "feedback_snapshot_generated_at": str(payload.get("generated_at") or "")[:40] or None,
        }
    )
    return metadata


def build_feedback_snapshot() -> dict[str, Any]:
    """Build a portable, non-sensitive projection of final editorial decisions."""
    connection = get_db()
    try:
        rows = connection.execute(
            """WITH ranked_feedback AS (
                    SELECT c.editorial_key, c.start_time, c.end_time, c.duration,
                           c.viral_score, c.editorial_score_version,
                           f.action, f.reason_code, f.quality_tags, f.adjustments, f.created_at,
                           ROW_NUMBER() OVER (
                               PARTITION BY f.clip_id
                               ORDER BY f.id DESC
                           ) AS feedback_rank
                      FROM clip_feedback AS f
                      JOIN clips AS c ON c.id = f.clip_id
                     WHERE COALESCE(c.editorial_key, '') <> ''
                )
                SELECT editorial_key, start_time, end_time, duration,
                       viral_score, editorial_score_version,
                       action, reason_code, quality_tags, adjustments, created_at
                  FROM ranked_feedback
                 WHERE feedback_rank = 1
                 ORDER BY editorial_key ASC, start_time ASC"""
        ).fetchall()
    finally:
        connection.close()

    records: list[dict[str, Any]] = []
    for row in rows:
        records.append(
            {
                "editorial_key": str(row[0])[:80],
                "start_seconds": round(float(row[1] or 0), 3),
                "end_seconds": round(float(row[2] or 0), 3),
                "duration_seconds": round(float(row[3] or 0), 3),
                "score": int(row[4] or 0),
                "score_version": str(row[5] or "")[:64],
                "action": str(row[6] or "")[:24],
                "reason_code": str(row[7] or "")[:48],
                "quality_tags": _quality_tags(row[8]),
                "review_metadata": _review_metadata(row[9]),
                "created_at": str(row[10] or "")[:40],
            }
        )
    return {
        "format": SYNC_FORMAT,
        "format_version": SYNC_FORMAT_VERSION,
        "generated_at": _utc_now(),
        "records": records,
        "record_count": len(records),
    }


def write_feedback_snapshot(repo_path: str | None = None) -> dict[str, Any]:
    """Atomically write the sanitized feedback projection into the checkout."""
    repo = _repo_path(repo_path)
    target = repo / SNAPSHOT_RELATIVE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = build_feedback_snapshot()
    fd, temporary = tempfile.mkstemp(prefix="editorial-feedback-", suffix=".json", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, target)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return {"path": str(target), "relative_path": SNAPSHOT_RELATIVE_PATH.as_posix(), **payload}


def _status_files(repo: Path) -> list[str]:
    result = _run_git(repo, "status", "--porcelain=v1")
    return [line[3:].strip() for line in result.stdout.splitlines() if len(line) >= 4]


def _head(repo: Path, ref: str) -> str | None:
    try:
        return _run_git(repo, "rev-parse", ref).stdout.strip() or None
    except RepositorySyncError:
        return None


def get_repository_status(repo_path: str | None = None, fetch: bool = False) -> dict[str, Any]:
    repo = _repo_path(repo_path)
    branch = _branch(repo)
    current = _run_git(repo, "branch", "--show-current").stdout.strip()
    if fetch:
        _run_git(repo, "fetch", "--quiet", "origin", branch, timeout=60)
    local_sha = _head(repo, "HEAD")
    remote_sha = _head(repo, f"origin/{branch}")
    dirty = _status_files(repo)
    snapshot_relative = SNAPSHOT_RELATIVE_PATH.as_posix()
    feedback_snapshot_dirty = snapshot_relative in dirty
    code_dirty_files = [item for item in dirty if item != snapshot_relative]
    update_available = bool(remote_sha and local_sha and remote_sha != local_sha)
    return {
        "success": True,
        "is_git": True,
        "branch": branch,
        "current_branch": current,
        "on_expected_branch": current == branch,
        "local_sha": local_sha,
        "remote_sha": remote_sha,
        "update_available": update_available,
        "dirty_files": dirty,
        "code_dirty_files": code_dirty_files,
        "feedback_snapshot_dirty": feedback_snapshot_dirty,
        "feedback_snapshot_path": snapshot_relative,
        **_feedback_snapshot_metadata(repo),
    }


def update_from_github(repo_path: str | None = None) -> dict[str, Any]:
    """Fast-forward only; never overwrite uncommitted user work."""
    repo = _repo_path(repo_path)
    branch = _branch(repo)
    status = get_repository_status(str(repo), fetch=True)
    if status["current_branch"] != branch:
        raise RepositorySyncError(f"O checkout está na branch '{status['current_branch'] or 'desconhecida'}', não em '{branch}'.")
    snapshot_path = repo / SNAPSHOT_RELATIVE_PATH
    snapshot_was_dirty = SNAPSHOT_RELATIVE_PATH.as_posix() in status["dirty_files"]
    dirty = [item for item in status["dirty_files"] if item != SNAPSHOT_RELATIVE_PATH.as_posix()]
    if dirty:
        raise RepositorySyncError("Há alterações locais não publicadas. Faça backup ou publique-as antes de atualizar: " + ", ".join(dirty[:5]))
    if not status["update_available"]:
        return {**status, "updated": False, "message": "O programa já está atualizado."}
    preserved_snapshot = snapshot_path.read_bytes() if snapshot_was_dirty and snapshot_path.is_file() else None
    if snapshot_was_dirty:
        snapshot_path.unlink(missing_ok=True)
    try:
        _run_git(repo, "merge", "--ff-only", f"origin/{branch}", timeout=60)
    finally:
        if preserved_snapshot is not None:
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_bytes(preserved_snapshot)
    return {**get_repository_status(str(repo), fetch=False), "updated": True, "message": "Atualização aplicada por fast-forward; as decisões locais permanecem no armazenamento persistente."}


def push_feedback_snapshot(repo_path: str | None = None) -> dict[str, Any]:
    """Commit and push only the sanitized feedback snapshot."""
    repo = _repo_path(repo_path)
    branch = _branch(repo)
    status = get_repository_status(str(repo), fetch=True)
    if status["current_branch"] != branch:
        raise RepositorySyncError(f"O checkout está na branch '{status['current_branch'] or 'desconhecida'}', não em '{branch}'.")
    dirty = list(status.get("code_dirty_files") or [])
    if dirty:
        raise RepositorySyncError("Há alterações locais fora do snapshot de feedback; nenhuma publicação foi feita: " + ", ".join(dirty[:5]))
    if status.get("update_available"):
        raise RepositorySyncError("A branch remota recebeu mudanças. Atualize o programa antes de publicar o feedback local.")
    snapshot = write_feedback_snapshot(str(repo))
    _run_git(repo, "add", "--", SNAPSHOT_RELATIVE_PATH.as_posix())
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", SNAPSHOT_RELATIVE_PATH.as_posix()],
        cwd=str(repo),
        capture_output=True,
        check=False,
        timeout=30,
    )
    if staged.returncode == 0:
        refreshed = get_repository_status(str(repo), fetch=False)
        return {**refreshed, **snapshot, "published": False, "message": "O snapshot de feedback já estava sincronizado."}
    _run_git(repo, "commit", "-m", "chore: sync editorial feedback", timeout=60)
    _run_git(repo, "push", "origin", branch, timeout=120)
    return {**get_repository_status(str(repo), fetch=False), **snapshot, "published": True, "message": "Feedback editorial sanitizado publicado."}
