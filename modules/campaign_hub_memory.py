"""Persistent, offline-first Campaign Hub memory for Furia Clips.

This module deliberately does not call the Campaign Hub or MCP. It accepts an
authorized JSON export, validates it through the existing adapter contract and
atomically installs the latest valid snapshot outside the Git checkout.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .campaign_hub import DEFAULT_SNAPSHOT_PATH, normalize_snapshot

MEMORY_SCHEMA_VERSION = "campaign-hub-memory-v1"
DEFAULT_MEMORY_DIR = DEFAULT_SNAPSHOT_PATH.parent
DEFAULT_MANIFEST_PATH = DEFAULT_MEMORY_DIR / "manifest.json"
MAX_RECORDS_PER_COLLECTION = 50_000
COLLECTION_KEYS = (
    "sources",
    "transcripts",
    "sentences",
    "blocks",
    "highlights",
    "possible_cuts",
    "posts",
    "metrics",
    "entities",
    "topics",
    "benchmarks",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(payload: Any) -> str:
    return hashlib.sha256(_json_bytes(payload)).hexdigest()


def _bounded_dict_records(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    records: list[dict[str, Any]] = []
    for item in value[:MAX_RECORDS_PER_COLLECTION]:
        if isinstance(item, dict):
            # Copy the record so callers cannot mutate the input payload after
            # validation. The adapter remains intentionally schema-tolerant.
            records.append(dict(item))
    return records


def normalize_memory_payload(payload: Any) -> dict[str, Any] | None:
    """Normalize legacy aggregate snapshots and richer authorized exports.

    The existing ``normalize_snapshot`` remains the compatibility gate for
    accounts and hook priors. Rich collections are carried separately so the
    current ranker can keep working while later block/retrieval features adopt
    them incrementally.
    """
    if not isinstance(payload, dict):
        return None
    normalized = normalize_snapshot(payload)
    if not normalized:
        return None

    record_source = payload.get("records") if isinstance(payload.get("records"), dict) else payload
    records = {key: _bounded_dict_records(record_source.get(key)) for key in COLLECTION_KEYS}
    raw_metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    sync = payload.get("sync") if isinstance(payload.get("sync"), dict) else {}

    result = dict(normalized)
    result.update(
        {
            "schema_version": str(
                payload.get("schema_version")
                or payload.get("memory_schema_version")
                or MEMORY_SCHEMA_VERSION
            )[:80],
            "memory_schema_version": MEMORY_SCHEMA_VERSION,
            "metadata": {
                "source_label": str(
                    raw_metadata.get("source_label")
                    or payload.get("source_label")
                    or "Campaign Hub autorizado — snapshot local"
                )[:200],
                "privacy_contract": raw_metadata.get("privacy_contract")
                if isinstance(raw_metadata.get("privacy_contract"), dict)
                else payload.get("privacy_contract", {}),
            },
            "sync": {
                "last_sync_at": str(sync.get("last_sync_at") or payload.get("collected_at") or "")[:80],
                "cursor": str(sync.get("cursor") or "")[:200],
                "status": str(sync.get("status") or "ready")[:40],
                "source": str(sync.get("source") or "authorized_export")[:80],
            },
            "records": records,
        }
    )
    result["record_counts"] = {key: len(value) for key, value in records.items()}
    return result


def _candidate_paths(path: str | os.PathLike[str] | None = None) -> tuple[Path, Path]:
    snapshot_path = Path(path).expanduser() if path else DEFAULT_SNAPSHOT_PATH
    return snapshot_path, snapshot_path.with_name("manifest.json")


def read_memory(path: str | os.PathLike[str] | None = None) -> dict[str, Any] | None:
    """Read and normalize a local memory file without modifying it."""
    snapshot_path, _ = _candidate_paths(path)
    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return normalize_memory_payload(payload)


def build_manifest(snapshot: dict[str, Any], *, source: str, installed_at: str | None = None) -> dict[str, Any]:
    """Build a bounded manifest that contains no raw media or credentials."""
    accounts = snapshot.get("accounts", {}) if isinstance(snapshot, dict) else {}
    return {
        "manifest_schema_version": MEMORY_SCHEMA_VERSION,
        "installed_at": installed_at or _utc_now(),
        "last_sync_at": str((snapshot.get("sync") or {}).get("last_sync_at") or snapshot.get("collected_at") or "")[:80],
        "source": str(source or "authorized_export")[:120],
        "snapshot_version": str(snapshot.get("version") or "")[:80],
        "snapshot_sha256": _sha256(snapshot),
        "default_account": str(snapshot.get("default_account") or "@renansantosmbl"),
        "account_count": len(accounts) if isinstance(accounts, dict) else 0,
        "accounts": sorted(str(key) for key in accounts) if isinstance(accounts, dict) else [],
        "record_counts": dict(snapshot.get("record_counts") or {}),
        "privacy_contract": (snapshot.get("metadata") or {}).get("privacy_contract", {}),
    }


def _record_identity(record: dict[str, Any]) -> str:
    """Return a stable identity for incremental merge without trusting provider IDs."""
    for key in ("id", "uuid", "content_key", "source_id", "block_id", "sentence_id", "post_id"):
        value = record.get(key)
        if value not in (None, ""):
            return f"{key}:{value}"
    return f"json:{_sha256(record)}"


def _merge_record_lists(
    old_records: list[dict[str, Any]], new_records: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], int, int]:
    merged: dict[str, dict[str, Any]] = {}
    for record in old_records + new_records:
        if isinstance(record, dict):
            merged[_record_identity(record)] = dict(record)
    old_ids = {_record_identity(item) for item in old_records if isinstance(item, dict)}
    new_ids = {_record_identity(item) for item in new_records if isinstance(item, dict)}
    added = len(new_ids - old_ids)
    updated = sum(1 for item in new_records if isinstance(item, dict) and _record_identity(item) in old_ids)
    return list(merged.values())[:MAX_RECORDS_PER_COLLECTION], added, updated


def merge_memory_payload(
    existing_payload: dict[str, Any] | None,
    incoming_payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, int]]:
    """Merge a bounded authorized export into the latest valid local memory."""
    incoming = normalize_memory_payload(incoming_payload)
    if not incoming:
        raise ValueError("O export recebido não contém contas Campaign Hub válidas.")
    existing = normalize_memory_payload(existing_payload) if existing_payload else None
    if not existing:
        incoming.setdefault("sync", {})["status"] = "ready"
        incoming.setdefault("sync", {})["source"] = "authorized_export"
        return incoming, {"accounts_added": len(incoming.get("accounts", {})), "records_added": sum(incoming.get("record_counts", {}).values()), "records_updated": 0}

    merged = dict(existing)
    merged["version"] = incoming.get("version") or existing.get("version")
    merged["schema_version"] = incoming.get("schema_version") or existing.get("schema_version")
    merged["collected_at"] = incoming.get("collected_at") or existing.get("collected_at")
    merged["default_account"] = incoming.get("default_account") or existing.get("default_account")
    merged["metadata"] = {**(existing.get("metadata") or {}), **(incoming.get("metadata") or {})}
    merged["accounts"] = {**(existing.get("accounts") or {})}
    account_added = 0
    for account, data in (incoming.get("accounts") or {}).items():
        if account not in merged["accounts"]:
            account_added += 1
            merged["accounts"][account] = dict(data)
            continue
        previous = dict(merged["accounts"].get(account) or {})
        for key in ("platform",):
            if data.get(key):
                previous[key] = data[key]
        for key in ("hook_observations", "examples", "cohorts"):
            values, _, _ = _merge_record_lists(previous.get(key, []), data.get(key, []))
            previous[key] = values
        merged["accounts"][account] = previous

    merged["records"] = {**(existing.get("records") or {})}
    total_added = 0
    total_updated = 0
    for key in COLLECTION_KEYS:
        values, added, updated = _merge_record_lists(
            (existing.get("records") or {}).get(key, []),
            (incoming.get("records") or {}).get(key, []),
        )
        merged["records"][key] = values
        total_added += added
        total_updated += updated
    merged["record_counts"] = {key: len(merged["records"].get(key, [])) for key in COLLECTION_KEYS}
    merged["sync"] = {
        **(existing.get("sync") or {}),
        **(incoming.get("sync") or {}),
        "status": "ready",
        "source": "incremental_merge",
        "last_sync_at": (incoming.get("sync") or {}).get("last_sync_at") or _utc_now(),
    }
    for key in ("instagram_family_priors", "privacy_contract"):
        if key in incoming:
            merged[key] = incoming[key]
    return merged, {
        "accounts_added": account_added,
        "records_added": total_added,
        "records_updated": total_updated,
    }


def install_snapshot(
    payload: dict[str, Any],
    *,
    destination: str | os.PathLike[str] | None = None,
    source: str = "authorized_export",
    merge: bool = False,
) -> dict[str, Any]:
    """Validate and atomically install a local Campaign Hub snapshot.

    The previous valid snapshot remains untouched until both temporary files are
    fully written and replaced. The function returns only bounded metadata.
    """
    snapshot = normalize_memory_payload(payload)
    if not snapshot:
        raise ValueError("O snapshot não contém contas Campaign Hub válidas.")
    snapshot_path, manifest_path = _candidate_paths(destination)
    merge_stats = {"accounts_added": 0, "records_added": 0, "records_updated": 0}
    if merge:
        existing = read_memory(str(snapshot_path))
        snapshot, merge_stats = merge_memory_payload(existing, snapshot)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(snapshot, source=source)

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=snapshot_path.parent, prefix=".profile.", suffix=".tmp", delete=False
    ) as snapshot_file:
        json.dump(snapshot, snapshot_file, ensure_ascii=False, indent=2)
        snapshot_file.write("\n")
        snapshot_tmp = Path(snapshot_file.name)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=manifest_path.parent, prefix=".manifest.", suffix=".tmp", delete=False
    ) as manifest_file:
        json.dump(manifest, manifest_file, ensure_ascii=False, indent=2)
        manifest_file.write("\n")
        manifest_tmp = Path(manifest_file.name)
    try:
        os.replace(snapshot_tmp, snapshot_path)
        os.replace(manifest_tmp, manifest_path)
    finally:
        for temporary in (snapshot_tmp, manifest_tmp):
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
    status = memory_status(str(snapshot_path))
    status["merge"] = bool(merge)
    status["merge_stats"] = merge_stats
    return status


def import_snapshot_file(
    source_path: str | os.PathLike[str],
    *,
    destination: str | os.PathLike[str] | None = None,
    merge: bool = False,
) -> dict[str, Any]:
    """Import an authorized JSON export from disk into persistent memory."""
    source = Path(source_path).expanduser()
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Não foi possível ler o export do Campaign Hub: {exc}") from exc
    return install_snapshot(payload, destination=destination, source=f"file:{source.name}", merge=merge)


def memory_status(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Return frontend-safe status for the persistent local memory."""
    snapshot_path, manifest_path = _candidate_paths(path)
    base = {
        "available": False,
        "source": "campaign_hub_local_memory",
        "path": str(snapshot_path),
        "manifest_path": str(manifest_path),
        "read_only_runtime": True,
        "memory_schema_version": MEMORY_SCHEMA_VERSION,
        "status": "missing",
        "message": "Nenhuma memória editorial local foi instalada.",
    }
    if not snapshot_path.is_file():
        return base
    snapshot = read_memory(str(snapshot_path))
    if not snapshot:
        base.update(
            {
                "status": "invalid",
                "message": "A memória local existe, mas não passou pela validação.",
            }
        )
        return base
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        manifest = {}
    stat = snapshot_path.stat()
    sync = snapshot.get("sync") if isinstance(snapshot.get("sync"), dict) else {}
    accounts = snapshot.get("accounts") if isinstance(snapshot.get("accounts"), dict) else {}
    base.update(
        {
            "available": True,
            "status": "ready",
            "message": "Memória editorial local pronta; o próximo job a usará offline.",
            "version": snapshot.get("version", ""),
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "last_sync_at": sync.get("last_sync_at", ""),
            "sync_status": sync.get("status", "ready"),
            "sync_source": sync.get("source", "authorized_export"),
            "default_account": snapshot.get("default_account", "@renansantosmbl"),
            "accounts": {
                str(account): {
                    "hook_observations": len((data or {}).get("hook_observations", [])),
                    "examples": len((data or {}).get("examples", [])),
                    "cohorts": len((data or {}).get("cohorts", [])),
                }
                for account, data in accounts.items()
                if isinstance(data, dict)
            },
            "record_counts": dict(snapshot.get("record_counts") or {}),
            "manifest_present": manifest_path.is_file(),
            "snapshot_sha256": str(manifest.get("snapshot_sha256") or _sha256(snapshot))[:64],
            "privacy_contract": (snapshot.get("metadata") or {}).get("privacy_contract", {}),
        }
    )
    return base


def export_status_payload(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Return a bounded payload suitable for future sync/diagnostic endpoints."""
    status = memory_status(path)
    status.pop("privacy_contract", None)
    return status
