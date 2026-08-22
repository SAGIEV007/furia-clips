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
        if raw_observations is None:
            raw_observations = []
        if not isinstance(raw_observations, (list, tuple)):
            return None
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
            raw_priors = raw.get("hook_priors", [])
            if raw_priors is None:
                raw_priors = []
            if not isinstance(raw_priors, (list, tuple)):
                return None
            for item in raw_priors:
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
        raw_examples = raw.get("examples", [])
        raw_cohorts = raw.get("cohorts", [])
        if raw_examples is None:
            raw_examples = []
        if raw_cohorts is None:
            raw_cohorts = []
        if not isinstance(raw_examples, (list, tuple)) or not isinstance(raw_cohorts, (list, tuple)):
            return None
        normalized_accounts[account_key] = {
            "platform": str(raw.get("platform", "instagram") or "instagram").lower(),
            "hook_observations": observations[:1000],
            "examples": [item for item in raw_examples if isinstance(item, dict)][:100],
            "cohorts": [item for item in raw_cohorts if isinstance(item, dict)][:100],
        }
    if not normalized_accounts:
        return None
    default_account = str(payload.get("default_account", "@renansantosmbl") or "@renansantosmbl")
    return {
        "version": str(payload.get("version", "1") or "1")[:20],
        "source": "campaign-hub",
        "collected_at": str(payload.get("collected_at", "") or "")[:80],
        "default_account": default_account if default_account in SUPPORTED_ACCOUNTS else "@renansantosmbl",
        "accounts": normalized_accounts,
    }


def snapshot_status(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Return bounded read-only metadata and effective influence of a local snapshot."""
    explicit = path or os.environ.get("FURIA_CAMPAIGN_HUB_SNAPSHOT")
    candidates = [Path(explicit).expanduser()] if explicit else [DEFAULT_SNAPSHOT_PATH, PACKAGED_SNAPSHOT_PATH]
    first_problem = None
    for candidate in candidates:
        try:
            stat = candidate.stat()
            if not candidate.is_file():
                continue
            raw_text = candidate.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        except (OSError, UnicodeDecodeError) as exc:
            if first_problem is None:
                first_problem = {
                    "status": "invalid",
                    "path": str(candidate),
                    "message": f"Snapshot encontrado, mas não pôde ser lido: {str(exc)[:180]}",
                }
            continue

        if not raw_text.strip():
            problem = {
                "status": "empty",
                "path": str(candidate),
                "message": "O arquivo do snapshot existe, mas está vazio.",
            }
            if explicit:
                return _snapshot_status_payload(problem, read_only=True, auto_reload_on_next_analysis=False)
            if first_problem is None:
                first_problem = problem
            continue

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            problem = {
                "status": "invalid",
                "path": str(candidate),
                "message": f"O snapshot contém JSON inválido na linha {exc.lineno}, coluna {exc.colno}.",
            }
            if explicit:
                return _snapshot_status_payload(problem, read_only=True, auto_reload_on_next_analysis=False)
            if first_problem is None:
                first_problem = problem
            continue
        except (TypeError, ValueError) as exc:
            problem = {
                "status": "invalid",
                "path": str(candidate),
                "message": f"O snapshot não pôde ser interpretado: {str(exc)[:180]}",
            }
            if explicit:
                return _snapshot_status_payload(problem, read_only=True, auto_reload_on_next_analysis=False)
            if first_problem is None:
                first_problem = problem
            continue

        snapshot = normalize_snapshot(payload)
        if not snapshot:
            problem = {
                "status": "invalid",
                "path": str(candidate),
                "message": "O snapshot foi lido, mas não contém contas suportadas em formato válido.",
            }
            if explicit:
                return _snapshot_status_payload(problem, read_only=True, auto_reload_on_next_analysis=False)
            if first_problem is None:
                first_problem = problem
            continue

        metadata = _snapshot_metadata(snapshot, candidate, stat)
        if metadata["total_hook_observations"] <= 0:
            metadata.update({
                "available": False,
                "status": "empty",
                "message": "O snapshot tem estrutura válida, mas não contém observações de hooks utilizáveis pelo ranking.",
                "influences_ranking": False,
                "influence_scope": "nenhuma; são necessários priors de hooks observados",
            })
            return metadata
        return metadata

    if first_problem:
        return _snapshot_status_payload(first_problem, read_only=True, auto_reload_on_next_analysis=False)
    return {
        "available": False,
        "source": "campaign_hub_local_snapshot",
        "status": "missing",
        "message": "Nenhum snapshot editorial local foi encontrado.",
        "read_only": True,
        "auto_reload_on_next_analysis": False,
        "influences_ranking": False,
        "influence_scope": "nenhuma; o Furia usa apenas sinais do vídeo e dados locais",
    }


def _snapshot_status_payload(details: dict[str, Any], *, read_only: bool, auto_reload_on_next_analysis: bool) -> dict[str, Any]:
    return {
        "available": False,
        "source": "campaign_hub_local_snapshot",
        "status": details.get("status", "invalid"),
        "path": details.get("path", ""),
        "message": details.get("message", "Snapshot local indisponível."),
        "read_only": read_only,
        "auto_reload_on_next_analysis": auto_reload_on_next_analysis,
        "influences_ranking": False,
        "influence_scope": "nenhuma; o Furia continua operando sem prior histórico",
    }


def _snapshot_metadata(snapshot: dict[str, Any], candidate: Path, stat: os.stat_result) -> dict[str, Any]:
    from datetime import datetime, timezone

    accounts = snapshot.get("accounts", {}) if isinstance(snapshot, dict) else {}
    account_summary = {}
    total_hook_observations = 0
    total_examples = 0
    total_cohorts = 0
    for account, data in accounts.items():
        if not isinstance(data, dict):
            continue
        hook_count = len(data.get("hook_observations", []))
        example_count = len(data.get("examples", []))
        cohort_count = len(data.get("cohorts", []))
        total_hook_observations += hook_count
        total_examples += example_count
        total_cohorts += cohort_count
        account_summary[account] = {
            "hook_observations": hook_count,
            "examples": example_count,
            "cohorts": cohort_count,
        }
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
        "total_hook_observations": total_hook_observations,
        "total_examples": total_examples,
        "total_cohorts": total_cohorts,
        "influences_ranking": True,
        "influence_scope": "prior limitado de hooks históricos; não cria cortes, não substitui contexto e não promete viralidade",
        "read_only": True,
        "auto_reload_on_next_analysis": True,
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
    return {
        "available": available,
        "account": selected_account,
        "platform": account_data.get("platform", "instagram") if isinstance(account_data, dict) else "instagram",
        "hook_family": hook,
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
