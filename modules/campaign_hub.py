"""Optional local adapter for authorized Campaign Hub observations.

The local Furia Clips app must not call the MCP directly. Instead, an authorized
export/snapshot is stored outside the checkout and loaded opportunistically. The
adapter treats metrics as post-publication observations, never as a promise of
virality or a replacement for editorial completeness.
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path
from statistics import median
from typing import Any


DEFAULT_SNAPSHOT_PATH = Path.home() / "FuriaClipsData" / "campaign_hub" / "profile.json"
PACKAGED_SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "data" / "editorial_priors.json"
SUPPORTED_ACCOUNTS = {"@renansantosmbl", "@renansantosreserva", "@partidomissao"}
MEMORY_COLLECTION_KEYS = (
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
MAX_MEMORY_COLLECTION_ITEMS = 50_000

# Rules are intentionally descriptive rather than generative. They expose why a
# hook family was assigned, while the historical prior remains separately capped.
_HOOK_RULES = (
    ("tese-provocativa", (
        r"\b(eu\s+)?vou\b", r"\bvamos\b", r"\btem\s+que\b", r"\bprecisa\b",
        r"\bn[aã]o\s+pode\b", r"\beu\s+de\s+extrema[- ]direita\b",
    )),
    ("news-peg", (
        r"\bhoje\b", r"\bagora\b", r"\bnot[ií]cia\b", r"\bdebate(s)?\b",
        r"\bimagem\b", r"\bvazou\b", r"\burgente\b", r"\bevento\b",
    )),
    ("acusacao-direta", (
        r"\b(lula|pt|pcc|crime|corrupt|mentir|ningu[eé]m|presidente)\b",
        r"\bh[aá]\s+\d+\s+anos\b", r"\beles\s+n[aã]o\s+querem\b",
    )),
    ("revelacao-de-local", (
        r"\bmundo\s+por\s+tr[aá]s\b", r"\baqui\b", r"\bcidade\b", r"\blugar\b",
        r"\bpor\s+tr[aá]s\s+da\b",
    )),
    ("curiosity-gap", (
        r"\bveja\b", r"\bolha\b", r"\bdescubra\b", r"\bo\s+que\s+[eé]\b",
        r"\bcomo\s+assim\b", r"\bser[aá]\s+que\b",
    )),
    ("desafio-ao-espectador", (
        r"\?", r"presta\s+muita\s+aten[cç][aã]o", r"presta\s+aten[cç][aã]o",
        r"\bqual\s+[eé]\b",
    )),
    ("callback", (
        r"\b(esse|isso|aquela|lembra)\b",
    )),
)


def load_snapshot(path: str | os.PathLike[str] | None = None) -> dict[str, Any] | None:
    """Load a user snapshot, falling back to aggregate priors shipped with the app."""
    explicit = path or os.environ.get("FURIA_CAMPAIGN_HUB_SNAPSHOT")
    candidates = [Path(explicit).expanduser()] if explicit else [DEFAULT_SNAPSHOT_PATH, PACKAGED_SNAPSHOT_PATH]
    for candidate in candidates:
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        normalized = normalize_snapshot(payload)
        if normalized:
            return normalized
    return None


def normalize_snapshot(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    accounts = payload.get("accounts")
    if not isinstance(accounts, dict):
        return None
    normalized_accounts: dict[str, dict[str, Any]] = {}
    for account, raw in accounts.items():
        account_key = str(account or "").strip()
        if account_key not in SUPPORTED_ACCOUNTS or not isinstance(raw, dict):
            continue
        observations = []
        raw_observations = raw.get("hook_observations", [])
        for item in raw_observations:
            if not isinstance(item, dict):
                continue
            hook = str(item.get("hook") or "").strip().lower()
            try:
                ratio = float(item.get("ratio"))
            except (TypeError, ValueError):
                continue
            if hook and ratio >= 0:
                observations.append({"hook": hook[:80], "ratio": ratio})
        # Aggregate-only packs expose mean/max and observation count instead of
        # post-level rows. Reconstruct bounded pseudo-observations solely so the
        # existing conservative prior logic can consume the portable format.
        if not observations:
            for item in raw.get("hook_priors", []):
                if not isinstance(item, dict):
                    continue
                hook = str(item.get("hook") or "").strip().lower()
                try:
                    ratio = float(item.get("mean_ratio", 0) or 0)
                    count = max(1, min(20, int(item.get("observations", 1) or 1)))
                except (TypeError, ValueError):
                    continue
                if hook and ratio >= 0:
                    observations.extend({"hook": hook[:80], "ratio": ratio} for _ in range(count))
        normalized_accounts[account_key] = {
            "platform": str(raw.get("platform", "instagram") or "instagram").lower(),
            "hook_observations": observations[:1000],
            "examples": [item for item in raw.get("examples", []) if isinstance(item, dict)][:100],
            "cohorts": [item for item in raw.get("cohorts", []) if isinstance(item, dict)][:100],
        }
    if not normalized_accounts:
        return None
    default_account = str(payload.get("default_account", "@renansantosmbl") or "@renansantosmbl")
    record_source = payload.get("records") if isinstance(payload.get("records"), dict) else payload
    records = {}
    for key in MEMORY_COLLECTION_KEYS:
        raw_records = record_source.get(key, []) if isinstance(record_source, dict) else []
        records[key] = [dict(item) for item in raw_records[:MAX_MEMORY_COLLECTION_ITEMS] if isinstance(item, dict)] if isinstance(raw_records, list) else []
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    sync = payload.get("sync") if isinstance(payload.get("sync"), dict) else {}
    normalized_payload = {
        "version": str(payload.get("version", "1") or "1")[:80],
        "schema_version": str(payload.get("schema_version", "") or "")[:80],
        "source": "campaign-hub",
        "collected_at": str(payload.get("collected_at", "") or "")[:80],
        "default_account": default_account if default_account in SUPPORTED_ACCOUNTS else "@renansantosmbl",
        "accounts": normalized_accounts,
        "records": records,
        "record_counts": {key: len(value) for key, value in records.items()},
        "metadata": metadata,
        "sync": {
            "last_sync_at": str(sync.get("last_sync_at") or payload.get("collected_at") or "")[:80],
            "cursor": str(sync.get("cursor") or "")[:200],
            "status": str(sync.get("status") or "ready")[:40],
            "source": str(sync.get("source") or "authorized_export")[:80],
        },
    }
    # Preserve validated aggregate structures used by the current ranker while
    # allowing richer exports to carry them alongside blocks and transcripts.
    for key in ("instagram_family_priors", "privacy_contract"):
        if key in payload:
            normalized_payload[key] = payload[key]
    return normalized_payload


def snapshot_status(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Return bounded local metadata for the read-only editorial snapshot."""
    explicit = path or os.environ.get("FURIA_CAMPAIGN_HUB_SNAPSHOT")
    candidates = [Path(explicit).expanduser()] if explicit else [DEFAULT_SNAPSHOT_PATH, PACKAGED_SNAPSHOT_PATH]
    for candidate in candidates:
        try:
            stat = candidate.stat()
        except (FileNotFoundError, OSError):
            continue
        snapshot = load_snapshot(str(candidate))
        if not snapshot:
            return {
                "available": False,
                "source": "campaign_hub_local_snapshot",
                "path": str(candidate),
                "status": "invalid",
                "message": "Snapshot local encontrado, mas não passou pela validação.",
                "read_only": True,
            }
        accounts = snapshot.get("accounts", {}) if isinstance(snapshot, dict) else {}
        account_summary = {}
        for account, data in accounts.items():
            if not isinstance(data, dict):
                continue
            account_summary[account] = {
                "hook_observations": len(data.get("hook_observations", [])),
                "examples": len(data.get("examples", [])),
                "cohorts": len(data.get("cohorts", [])),
            }
        from datetime import datetime, timezone
        return {
            "available": True,
            "source": "campaign_hub_local_snapshot",
            "path": str(candidate),
            "status": "ready",
            "version": snapshot.get("version", ""),
            "collected_at": snapshot.get("collected_at", ""),
            "modified_at": datetime.fromtimestamp(float(stat.st_mtime), tz=timezone.utc).isoformat(),
            "default_account": snapshot.get("default_account", ""),
            "accounts": account_summary,
            "read_only": True,
            "auto_reload_on_next_analysis": True,
        }
    return {
        "available": False,
        "source": "campaign_hub_local_snapshot",
        "status": "missing",
        "message": "Nenhum snapshot editorial local foi encontrado.",
        "read_only": True,
        "auto_reload_on_next_analysis": False,
    }


def classify_hook_details(text: str) -> dict[str, Any]:
    """Return a transparent hook family plus matched evidence.

    The first matching rule is deliberately deterministic. Explicit thesis and
    news cues precede generic question marks, so a question containing a clear
    proposal is not reduced to ``desafio-ao-espectador``. This is a routing hint,
    not a claim about performance or truth.
    """
    normalized = _normalize(text)
    for family, patterns in _HOOK_RULES:
        evidence = [pattern for pattern in patterns if re.search(pattern, normalized)]
        if evidence:
            return {
                "family": family,
                "evidence": evidence[:4],
                "confidence": round(min(0.95, 0.58 + len(evidence) * 0.10), 2),
                "basis": "regra_textual_explicita",
            }
    return {
        "family": "outro",
        "evidence": [],
        "confidence": 0.35,
        "basis": "sem_sinal_textual_suficiente",
    }


def classify_hook(text: str) -> str:
    """Return a transparent hook family; this is a prior, not a label claim."""
    return classify_hook_details(text)["family"]


def build_block_evidence(
    text: str,
    *,
    start: float | None = None,
    end: float | None = None,
    account: str | None = None,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Find local Acervo block evidence without making it a hard gate.

    Temporal overlap is preferred when the incoming source is known. Text/topic
    overlap is only a weak fallback because captions can be noisy. The return
    value is explanatory and intentionally bounded; it never claims that a
    block proves speaker identity or factual truth.
    """
    profile = snapshot or {}
    records = profile.get("records", {}) if isinstance(profile, dict) else {}
    blocks = records.get("blocks", []) if isinstance(records, dict) else []
    if not isinstance(blocks, list) or not blocks:
        return {"available": False, "matches": [], "observed_signal": 50.0, "confidence": 0.0, "basis": "no_local_blocks"}
    account_key = account if account in SUPPORTED_ACCOUNTS else profile.get("default_account", "@renansantosmbl")
    query_tokens = set(re.findall(r"[a-z0-9à-ÿ]{4,}", _normalize(text)))
    try:
        clip_start = float(start) if start is not None else None
        clip_end = float(end) if end is not None else None
    except (TypeError, ValueError):
        clip_start = clip_end = None
    ranked = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if block.get("account") and block.get("account") != account_key:
            continue
        block_start = block.get("start_s")
        block_end = block.get("end_s")
        try:
            block_start = float(block_start)
            block_end = float(block_end)
        except (TypeError, ValueError):
            block_start = block_end = None
        overlap = 0.0
        temporal = 0.0
        if clip_start is not None and clip_end is not None and block_start is not None and block_end is not None:
            overlap = max(0.0, min(clip_end, block_end) - max(clip_start, block_start))
            clip_duration = max(0.1, clip_end - clip_start)
            block_duration = max(0.1, block_end - block_start)
            temporal = max(overlap / clip_duration, overlap / block_duration)
        block_text = " ".join(
            str(block.get(key) or "") for key in ("title", "summary", "trigger_question")
        ) + " " + " ".join(str(item) for item in (block.get("topics") or []))
        block_tokens = set(re.findall(r"[a-z0-9à-ÿ]{4,}", _normalize(block_text)))
        lexical = len(query_tokens & block_tokens) / max(1, len(query_tokens)) if query_tokens else 0.0
        evidence_score = max(temporal, lexical * 0.75)
        if evidence_score <= 0.18:
            continue
        rank = 0.65 * temporal + 0.35 * lexical
        ranked.append((rank, block, temporal, lexical))
    ranked.sort(key=lambda item: item[0], reverse=True)
    matches = []
    for rank, block, temporal, lexical in ranked[:3]:
        matches.append({
            "block_id": block.get("id"),
            "title": block.get("title", ""),
            "start": block.get("start_s"),
            "end": block.get("end_s"),
            "temporal_overlap": round(temporal, 3),
            "text_overlap": round(lexical, 3),
            "renan_speaking": block.get("renan_speaking"),
            "self_contained_rank": block.get("self_contained_rank"),
            "needs_context": bool(block.get("needs_context")),
            "risk_flags": block.get("risk_flags") or [],
            "trust_tier": block.get("trust_tier", ""),
        })
    best = matches[0] if matches else None
    signal = 50.0
    confidence = 0.0
    if best:
        signal = 50.0 + min(8.0, max(0.0, float(best.get("temporal_overlap", 0)) * 8.0))
        if best.get("renan_speaking") is True:
            signal += 2.0
        if best.get("needs_context"):
            signal -= 2.0
        confidence = round(min(1.0, max(float(best.get("temporal_overlap", 0)), float(best.get("text_overlap", 0)))), 2)
    return {
        "available": bool(matches),
        "account": account_key,
        "matches": matches,
        "observed_signal": round(max(42.0, min(60.0, signal)), 1),
        "confidence": confidence,
        "basis": "local_acervo_temporal_and_text_overlap" if matches else "no_matching_local_block",
    }


def _hook_observations(account_data: Any) -> list[dict[str, Any]]:
    """The per-hook ratios of an account, in either shape the snapshot may use.

    This function is why the Campaign Hub hook prior had never once fired. The
    code asked the account for ``hook_observations``; every published snapshot,
    the one shipped with the program included, writes ``hook_priors`` — already
    grouped, with ``observations`` and ``mean_ratio`` instead of one row per
    post. The key simply did not exist, so the list came back empty, the sample
    count was zero, and ``available`` was False on every clip ever scored,
    including text that lands squarely in the account's strongest hook family.

    Measured on the packaged snapshot before this: "Eu vou dizer uma coisa: o PT
    mentiu por trinta anos" — textbook `tese-provocativa`, six observations on
    file — came back `available=False, sample_count=0, observed_signal=50.0`.

    The grouped shape is expanded back into one row per observation. Repeating
    the group's mean is not an invention of data: the mean is the best estimate
    of that group's centre, and the count is exactly what the snapshot reports.
    The three-observation floor below still decides whether any of it is used.
    """
    if not isinstance(account_data, dict):
        return []
    detalhado = account_data.get("hook_observations")
    if isinstance(detalhado, list) and detalhado:
        return [item for item in detalhado if isinstance(item, dict)]
    agrupado = account_data.get("hook_priors")
    if not isinstance(agrupado, list):
        return []
    expandido: list[dict[str, Any]] = []
    for item in agrupado:
        if not isinstance(item, dict):
            continue
        try:
            razao = float(item.get("mean_ratio"))
            quantas = int(item.get("observations") or 0)
        except (TypeError, ValueError):
            continue
        hook = str(item.get("hook") or "").strip()
        if not hook or quantas <= 0:
            continue
        expandido.extend({"hook": hook, "ratio": razao} for _ in range(min(quantas, 500)))
    return expandido


def build_performance_prior(
    text: str,
    *,
    account: str | None = None,
    snapshot: dict[str, Any] | None = None,
    start: float | None = None,
    end: float | None = None,
) -> dict[str, Any]:
    """Build a conservative hook prior from observed settled ratios.

    A prior is available only with at least three observations for the hook. It
    is deliberately capped so performance history cannot overpower context,
    completeness, speaker, or visual composition gates.
    """
    profile = snapshot or {}
    accounts = profile.get("accounts", {}) if isinstance(profile, dict) else {}
    selected_account = account if account in SUPPORTED_ACCOUNTS else profile.get("default_account", "@renansantosmbl")
    account_data = accounts.get(selected_account, {}) if isinstance(accounts, dict) else {}
    observations = _hook_observations(account_data)
    hook_details = classify_hook_details(text)
    hook = hook_details["family"]
    hook_values = [float(item["ratio"]) for item in observations if item.get("hook") == hook]
    all_values = [float(item["ratio"]) for item in observations if isinstance(item.get("ratio"), (int, float))]
    sample_count = len(hook_values)
    available = sample_count >= 3 and bool(all_values)
    signal = 50.0
    confidence = 0.0
    if available:
        baseline = max(0.001, float(median(all_values)))
        relative = float(median(hook_values)) / baseline
        signal = max(42.0, min(58.0, 50.0 + (relative - 1.0) * 18.0))
        confidence = min(1.0, sample_count / 10.0)
    block_evidence = build_block_evidence(
        text,
        start=start,
        end=end,
        account=selected_account,
        snapshot=profile,
    )
    return {
        "available": available,
        "account": selected_account,
        "platform": account_data.get("platform", "instagram") if isinstance(account_data, dict) else "instagram",
        "hook_family": hook,
        "block_evidence": block_evidence,
        "hook_evidence": hook_details["evidence"],
        "hook_classification_confidence": hook_details["confidence"],
        "sample_count": sample_count,
        "observed_signal": round(signal, 1),
        "confidence": round(confidence, 2),
        "basis": "campaign_hub_settled_ratio_observation" if available else "insufficient_hook_sample",
    }


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", str(text or "").lower())
    return "".join(char for char in value if not unicodedata.combining(char))
