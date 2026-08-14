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
from pathlib import Path
from statistics import median
from typing import Any


DEFAULT_SNAPSHOT_PATH = Path.home() / "FuriaClipsData" / "campaign_hub" / "profile.json"
SUPPORTED_ACCOUNTS = {"@renansantosmbl", "@renansantosreserva", "@partidomissao"}

_HOOK_PATTERNS = (
    ("desafio-ao-espectador", (r"\?", r"presta muita aten", r"qual [ée]")),
    ("acusacao-direta", (r"\b(lula|fl[aá]vio|pt|pcc|crime|corrupt|mentir)\b", r"ningu[eé]m")),
    ("news-peg", (r"\b(hoje|agora|not[ií]cia|viral|debate|imagem|vazou)\b",)),
    ("curiosity-gap", (r"\b(veja|olha|descubra|o que [ée]|como assim)\b",)),
    ("revelacao-de-local", (r"\b(aqui|cidade|lugar|mundo por tr[aá]s)\b",)),
    ("callback", (r"\b(esse|isso|aquela|lembra)\b",)),
    ("tese-provocativa", (r"\b(vou|precisa|tem que|n[aã]o pode|vamos)\b", r"!")),
)


def load_snapshot(path: str | os.PathLike[str] | None = None) -> dict[str, Any] | None:
    """Load a user-owned snapshot; return None for absent or invalid data."""
    candidate = Path(path or os.environ.get("FURIA_CAMPAIGN_HUB_SNAPSHOT", DEFAULT_SNAPSHOT_PATH)).expanduser()
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return normalize_snapshot(payload)


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
        for item in raw.get("hook_observations", []):
            if not isinstance(item, dict):
                continue
            hook = str(item.get("hook") or "").strip().lower()
            try:
                ratio = float(item.get("ratio"))
            except (TypeError, ValueError):
                continue
            if hook and ratio >= 0:
                observations.append({"hook": hook[:80], "ratio": ratio})
        normalized_accounts[account_key] = {
            "platform": str(raw.get("platform", "instagram") or "instagram").lower(),
            "hook_observations": observations[:1000],
            "examples": [item for item in raw.get("examples", []) if isinstance(item, dict)][:100],
            "cohorts": [item for item in raw.get("cohorts", []) if isinstance(item, dict)][:100],
        }
    if not normalized_accounts:
        return None
    return {
        "version": str(payload.get("version", "1") or "1")[:20],
        "source": "campaign-hub",
        "collected_at": str(payload.get("collected_at", "") or "")[:80],
        "default_account": str(payload.get("default_account", "@renansantosmbl") or "@renansantosmbl") if str(payload.get("default_account", "@renansantosmbl")) in SUPPORTED_ACCOUNTS else "@renansantosmbl",
        "accounts": normalized_accounts,
    }


def classify_hook(text: str) -> str:
    """Return a transparent hook family; this is a prior, not a label claim."""
    normalized = _normalize(text)
    for family, patterns in _HOOK_PATTERNS:
        if any(re.search(pattern, normalized) for pattern in patterns):
            return family
    return "outro"


def build_performance_prior(
    text: str,
    *,
    account: str | None = None,
    snapshot: dict[str, Any] | None = None,
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
    observations = account_data.get("hook_observations", []) if isinstance(account_data, dict) else []
    hook = classify_hook(text)
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
    return {
        "available": available,
        "account": selected_account,
        "platform": account_data.get("platform", "instagram") if isinstance(account_data, dict) else "instagram",
        "hook_family": hook,
        "sample_count": sample_count,
        "observed_signal": round(signal, 1),
        "confidence": round(confidence, 2),
        "basis": "campaign_hub_settled_ratio_observation" if available else "insufficient_hook_sample",
    }


def _normalize(text: str) -> str:
    value = str(text or "").lower()
    return value.replace("á", "a").replace("à", "a").replace("ã", "a").replace("â", "a").replace("é", "e").replace("ê", "e").replace("í", "i").replace("ó", "o").replace("ô", "o").replace("õ", "o").replace("ú", "u").replace("ç", "c")
