"""Persistent, cooperative background job orchestration."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from .cancellation import OperationCancelled


class JobCancelled(Exception):
    """Raised by a worker when the user requested cancellation."""


JobTarget = Callable[["JobContext"], Optional[Dict[str, Any]]]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobContext:
    def __init__(self, manager: "JobManager", job_id: str):
        self.manager = manager
        self.job_id = job_id

    def update(
        self,
        *,
        stage: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        artifacts: Optional[list] = None,
    ) -> dict:
        return self.manager.update(
            self.job_id,
            stage=stage,
            progress=progress,
            message=message,
            artifacts=artifacts,
        )

    def is_cancel_requested(self) -> bool:
        job = self.manager.get(self.job_id)
        return bool(job and job["state"] == "cancel_requested")

    def check_cancel(self) -> None:
        if self.is_cancel_requested():
            raise JobCancelled(f"Job {self.job_id} cancelado pelo usuário")


class JobManager:
    """A small SQLite-backed job manager suitable for the local application."""

    def __init__(self, db_path: str, max_workers: int = 1, on_event=None):
        self.db_path = db_path
        self.on_event = on_event
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="furia-job")
        self._futures: Dict[str, Future] = {}
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self):
        connection = self._connect()
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                project_id INTEGER,
                type TEXT NOT NULL,
                state TEXT NOT NULL,
                stage TEXT,
                progress INTEGER NOT NULL DEFAULT 0,
                message TEXT,
                artifacts TEXT NOT NULL DEFAULT '[]',
                error TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
        connection.close()

    def _emit(self, job: dict):
        if self.on_event:
            try:
                self.on_event(job)
            except Exception:
                pass

    def _row_to_dict(self, row) -> Optional[dict]:
        if row is None:
            return None
        item = dict(row)
        try:
            item["artifacts"] = json.loads(item.get("artifacts") or "[]")
        except (TypeError, json.JSONDecodeError):
            item["artifacts"] = []
        return item

    def create(self, job_type: str, project_id: Optional[int] = None) -> dict:
        job_id = str(uuid.uuid4())
        now = _now()
        connection = self._connect()
        connection.execute(
            """INSERT INTO jobs
               (id, project_id, type, state, stage, progress, message,
                artifacts, created_at, updated_at)
               VALUES (?, ?, ?, 'queued', 'queued', 0, ?, '[]', ?, ?)""",
            (job_id, project_id, job_type, "Aguardando execução", now, now),
        )
        connection.commit()
        connection.close()
        job = self.get(job_id)
        self._emit(job)
        return job

    def submit(self, job_type: str, target: JobTarget, project_id: Optional[int] = None) -> dict:
        job = self.create(job_type, project_id=project_id)
        future = self.executor.submit(self._run, job["id"], target)
        with self._lock:
            self._futures[job["id"]] = future
        return job

    def _run(self, job_id: str, target: JobTarget):
        # Claim the queued row atomically. If cancellation won the race while
        # the Future was waiting in the executor queue, the target must never
        # start; otherwise the UI can say "cancelled" while FFmpeg/Whisper has
        # already begun consuming the source.
        now = _now()
        connection = self._connect()
        cursor = connection.execute(
            """
            UPDATE jobs
               SET state = 'running', stage = 'starting', progress = 1,
                   message = ?, updated_at = ?, started_at = COALESCE(started_at, ?)
             WHERE id = ? AND state = 'queued'
            """,
            ("Job iniciado", now, now, job_id),
        )
        connection.commit()
        connection.close()
        if cursor.rowcount != 1:
            current = self.get(job_id)
            if current and current["state"] == "cancel_requested":
                self.update(
                    job_id,
                    state="cancelled",
                    stage="cancelled",
                    message="Job cancelado antes do início do worker.",
                    error="cancelled_before_start",
                )
            return

        context = JobContext(self, job_id)
        try:
            # A cancellation requested immediately after the atomic claim is
            # still honored before any target-side work begins.
            context.check_cancel()
            result = target(context) or {}
            context.check_cancel()
            self.update(
                job_id,
                state="completed",
                stage="completed",
                progress=100,
                message="Job concluído",
                artifacts=result.get("artifacts"),
            )
        except (JobCancelled, OperationCancelled) as exc:
            self.update(
                job_id,
                state="cancelled",
                stage="cancelled",
                message=str(exc),
                error=str(exc),
            )
        except Exception as exc:
            self.update(
                job_id,
                state="failed",
                stage="failed",
                message="Job falhou",
                error=str(exc)[:1000],
            )
        finally:
            with self._lock:
                self._futures.pop(job_id, None)

    def update(
        self,
        job_id: str,
        *,
        state: Optional[str] = None,
        stage: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        artifacts: Optional[list] = None,
        error: Optional[str] = None,
    ) -> dict:
        current = self.get(job_id)
        if current is None:
            raise KeyError(job_id)
        values = {
            "state": state if state is not None else current["state"],
            "stage": stage if stage is not None else current["stage"],
            "progress": max(0, min(100, int(progress))) if progress is not None else current["progress"],
            "message": message if message is not None else current["message"],
            "artifacts": json.dumps(artifacts if artifacts is not None else current["artifacts"]),
            "error": error if error is not None else current["error"],
            "updated_at": _now(),
        }
        if state == "running" and not current.get("started_at"):
            values["started_at"] = _now()
        if state in {"completed", "failed", "cancelled"}:
            values["finished_at"] = _now()
        assignments = [
            "state = :state", "stage = :stage", "progress = :progress",
            "message = :message", "artifacts = :artifacts", "error = :error",
            "updated_at = :updated_at",
        ]
        if "started_at" in values:
            assignments.append("started_at = :started_at")
        if "finished_at" in values:
            assignments.append("finished_at = :finished_at")
        values["id"] = job_id
        connection = self._connect()
        connection.execute(
            f"UPDATE jobs SET {', '.join(assignments)} WHERE id = :id", values
        )
        connection.commit()
        connection.close()
        job = self.get(job_id)
        self._emit(job)
        return job

    def request_cancel(self, job_id: str) -> dict:
        current = self.get(job_id)
        if current is None:
            raise KeyError(job_id)
        if current["state"] in {"completed", "failed", "cancelled"}:
            return current
        if current["state"] == "queued":
            # Nothing from the target has started yet. Marking it terminal is
            # safe and gives the UI an immediate answer; the worker entrypoint
            # also checks the row atomically before it can begin.
            return self.update(
                job_id,
                state="cancelled",
                stage="cancelled",
                message="Job cancelado antes do início do worker.",
                error="cancelled_before_start",
            )
        return self.update(
            job_id,
            state="cancel_requested",
            message="Cancelamento solicitado; aguardando etapa segura",
        )

    def get(self, job_id: str) -> Optional[dict]:
        connection = self._connect()
        row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        connection.close()
        return self._row_to_dict(row)

    def list(self, limit: int = 50) -> list:
        connection = self._connect()
        rows = connection.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (int(limit),)
        ).fetchall()
        connection.close()
        return [self._row_to_dict(row) for row in rows]

    def reconcile_stale(self, max_age_seconds: float = 12 * 60 * 60) -> list[dict]:
        """Mark orphaned jobs as failed after a conservative inactivity window.

        A process restart can leave a SQLite job in ``running`` even though no
        worker exists anymore. Only jobs whose ``updated_at`` is older than the
        configured window are recovered; active long-running jobs keep their
        state because progress/heartbeat updates refresh that timestamp.
        """
        cutoff = datetime.now(timezone.utc).timestamp() - max(60.0, float(max_age_seconds))
        connection = self._connect()
        rows = connection.execute(
            "SELECT id, updated_at FROM jobs WHERE state IN ('running', 'cancel_requested')"
        ).fetchall()
        connection.close()
        recovered = []
        for row in rows:
            try:
                updated_at = datetime.fromisoformat(str(row["updated_at"])).timestamp()
            except (TypeError, ValueError, KeyError):
                updated_at = 0.0
            if updated_at > cutoff:
                continue
            recovered.append(
                self.update(
                    row["id"],
                    state="failed",
                    stage="stale_recovered",
                    message="Job interrompido sem worker ativo; marcado como falho na recuperação.",
                    error="stale_job_recovered",
                )
            )
        return recovered

    def shutdown(self):
        self.executor.shutdown(wait=False, cancel_futures=False)
