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
from difflib import SequenceMatcher
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


def _safe_text(value: Any, limit: int = 500) -> str:
    text = str(value or "").strip()
    return text[:limit]


def _safe_finite(value: Any, *, minimum: float | None = None, maximum: float | None = None) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in {float("inf"), float("-inf")}:
        return None
    if minimum is not None and number < minimum:
        return None
    if maximum is not None and number > maximum:
        return maximum
    return number


def _first_present(mapping: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None and value != "":
            return value
    return default


def _safe_labels(value: Any, limit: int = 12) -> list[str]:
    if isinstance(value, str):
        values = re.split(r"[,;|]", value)
    elif isinstance(value, (list, tuple)):
        values = value
    else:
        return []
    labels = []
    for item in values:
        if isinstance(item, dict):
            item = _first_present(item, "label", "name", "title", "topic", "text", default="")
        label = _safe_text(item, 100)
        if label and label not in labels:
            labels.append(label)
    return labels[:limit]


def _source_key(value: Any) -> str:
    if isinstance(value, dict):
        value = _first_present(value, "youtubeId", "videoId", "video_id", "id", "url", default="")
    text = _safe_text(value, 180)
    if not text:
        return ""
    match = re.search(r"(?:v=|youtu\.be/|youtube\.com/embed/)([A-Za-z0-9_-]{11})", text)
    return (match.group(1) if match else text).strip().lower()


def _normalize_time(value: Any) -> float | None:
    if isinstance(value, str) and ":" in value:
        parts = value.strip().replace(",", ".").split(":")
        try:
            if len(parts) == 2:
                value = float(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 3:
                value = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        except (TypeError, ValueError):
            return None
    return _safe_finite(value, minimum=0)


def _normalize_highlights(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    highlights = []
    for item in value:
        if not isinstance(item, dict):
            continue
        start = _normalize_time(_first_present(item, "startS", "start_seconds", "start", "timestamp"))
        end = _normalize_time(_first_present(item, "endS", "end_seconds", "end"))
        if start is None or end is None or end <= start:
            continue
        highlights.append({
            "start_seconds": start,
            "end_seconds": end,
            "text": _safe_text(_first_present(item, "text", "label", "title", default=""), 360),
            "reason": _safe_text(_first_present(item, "reason", "rationale", "description", default=""), 360),
        })
    return highlights[:20]


def _normalize_ignored_regions(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    regions = []
    for item in value:
        if not isinstance(item, dict):
            continue
        start = _normalize_time(_first_present(item, "startS", "start_seconds", "start"))
        end = _normalize_time(_first_present(item, "endS", "end_seconds", "end"))
        if start is None or end is None or end <= start:
            continue
        regions.append({
            "start_seconds": start,
            "end_seconds": end,
            "reason": _safe_text(_first_present(item, "reason", "label", "description", default="região fora de bloco"), 240),
            "kind": _safe_text(_first_present(item, "kind", "class", "type", default="ignored"), 60),
        })
    return regions[:30]


def _normalize_acervo_block(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    video = item.get("video") if isinstance(item.get("video"), dict) else {}
    start = _normalize_time(_first_present(item, "startS", "start_seconds", "start", "timestamp"))
    end = _normalize_time(_first_present(item, "endS", "end_seconds", "end"))
    if start is None or end is None or end <= start:
        return None
    density_rank = _safe_finite(_first_present(item, "densityRank", "density_rank"), minimum=0, maximum=100)
    self_contained_rank = _safe_finite(_first_present(item, "selfContainedRank", "self_contained_rank"), minimum=0, maximum=100)
    return {
        "block_id": _safe_text(_first_present(item, "id", "blockId", "block_id", default=""), 120),
        "source_video_id": _source_key(_first_present(video, "youtubeId", "videoId", "id", "url", default=_first_present(item, "videoId", "video_id", "sourceVideoId", default=""))),
        "source_url": _safe_text(_first_present(video, "youtubeUrl", "url", default=_first_present(item, "youtubeUrl", "url", "source_url", default="")), 260),
        "source_title": _safe_text(_first_present(video, "title", "name", default=_first_present(item, "sourceTitle", "source_title", default="")), 220),
        "start_seconds": start,
        "end_seconds": end,
        "duration_seconds": end - start,
        "title": _safe_text(_first_present(item, "title", "blockTitle", "label", "name", default=""), 260),
        "summary": _safe_text(_first_present(item, "summary", "description", "abstract", default=""), 700),
        "content_class": _safe_text(_first_present(item, "contentClass", "content_class", "class", default=""), 40).lower(),
        "category": _safe_text(_first_present(item, "category", "categoryLabel", default=""), 100),
        "topics": _safe_labels(_first_present(item, "topics", "tags", "contentTags", default=[])),
        "density_rank": density_rank,
        "self_contained_rank": self_contained_rank,
        "trust_tier": _safe_text(_first_present(item, "trustTier", "trust_tier", default=""), 30).lower(),
        "renan_speaking": _first_present(item, "renanSpeaking", "renan_speaking", default=None),
        "needs_context": bool(_first_present(item, "needsContext", "needs_context", default=False)),
        "gate_warnings": _safe_labels(_first_present(item, "gateWarnings", "gate_warnings", "riskFlags", default=[])),
        "highlights": _normalize_highlights(_first_present(item, "highlights", "moments", "blockHighlights", default=[])),
        "ignored_regions": _normalize_ignored_regions(_first_present(item, "ignoredRegions", "ignored_regions", default=[])),
        "pauta_reason": _safe_text(_first_present(item, "reason", "primaryReason", "rationale", default=""), 320),
        "pauta_score": _safe_finite(_first_present(item, "score.total", "score", "totalScore", default=None), minimum=0),
        "source_published_at": _safe_text(_first_present(video, "publishedAt", "published_at", default=""), 80),
    }


def _normalize_prior_rows(value: Any, limit: int = 200) -> list[dict[str, Any]]:
    if not isinstance(value, (list, tuple)):
        return []
    rows = []
    for item in value:
        if not isinstance(item, dict):
            continue
        row = {key: item[key] for key in ("tag", "category", "entity", "segment", "platform", "age", "sex") if item.get(key) not in (None, "")}
        signal = _safe_finite(_first_present(item, "signal", "score", "medianRatio", "median_ratio", default=None), minimum=0)
        sample = _safe_finite(_first_present(item, "sampleCount", "sample_count", "n", "observations", default=None), minimum=0)
        if signal is not None:
            row["signal"] = signal
        if sample is not None:
            row["sample_count"] = int(sample)
        if row:
            rows.append(row)
    return rows[:limit]


def _token_similarity(left: Any, right: Any) -> float:
    def tokens(value: Any) -> set[str]:
        normalized = _normalize(str(value or ""))
        return {token for token in re.findall(r"[a-z0-9à-ÿ]+", normalized) if len(token) > 2}
    left_tokens = tokens(left)
    right_tokens = tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    jaccard = len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))
    sequence = SequenceMatcher(None, " ".join(sorted(left_tokens)), " ".join(sorted(right_tokens))).ratio()
    return round(max(jaccard, sequence * 0.75), 4)


def _interval_overlap_ratio(start: float, end: float, other_start: float, other_end: float) -> float:
    overlap = max(0.0, min(end, other_end) - max(start, other_start))
    return overlap / max(0.001, min(end - start, other_end - other_start))


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
        acervo_root = payload.get("acervo") if isinstance(payload.get("acervo"), dict) else {}
        raw_blocks = raw.get("acervo_blocks", raw.get("blocks"))
        if raw_blocks is None:
            raw_blocks = acervo_root.get("blocks", [])
        if isinstance(raw_blocks, dict):
            raw_blocks = raw_blocks.get("items", raw_blocks.get("results", []))
        raw_pauta = raw.get("acervo_pauta", raw.get("pauta_candidates"))
        if raw_pauta is None:
            raw_pauta = acervo_root.get("pauta", acervo_root.get("primaryCandidates", []))
        if isinstance(raw_pauta, dict):
            raw_pauta = raw_pauta.get("primaryCandidates", raw_pauta.get("items", raw_pauta.get("results", [])))
        raw_audience = raw.get("audience_priors", raw.get("audience"))
        if raw_audience is None:
            raw_audience = acervo_root.get("audience", [])
        raw_entities = raw.get("entity_priors", raw.get("entities"))
        if raw_entities is None:
            raw_entities = acervo_root.get("entities", [])
        for rich_value in (raw_blocks, raw_pauta, raw_audience, raw_entities):
            if rich_value is None:
                continue
            if not isinstance(rich_value, (list, tuple)):
                return None
        normalized_blocks = [item for item in (_normalize_acervo_block(item) for item in (raw_blocks or [])) if item][:200]
        normalized_pauta = [item for item in (_normalize_acervo_block(item) for item in (raw_pauta or [])) if item][:100]
        normalized_accounts[account_key] = {
            "platform": str(raw.get("platform", "instagram") or "instagram").lower(),
            "hook_observations": observations[:1000],
            "examples": [item for item in raw_examples if isinstance(item, dict)][:100],
            "cohorts": [item for item in raw_cohorts if isinstance(item, dict)][:100],
            "acervo_blocks": normalized_blocks,
            "acervo_pauta": normalized_pauta,
            "audience_priors": _normalize_prior_rows(raw_audience),
            "entity_priors": _normalize_prior_rows(raw_entities),
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
        "acervo_version": _safe_text(_first_present(payload, "acervo_version", "acervoVersion", default=acervo_root.get("version", "") if isinstance(acervo_root, dict) else ""), 40),
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
        if metadata["total_hook_observations"] <= 0 and not metadata.get("rich_context_available"):
            metadata.update({
                "available": False,
                "status": "empty",
                "message": "O snapshot tem estrutura válida, mas não contém hooks, blocos Acervo ou pautas utilizáveis.",
                "influences_ranking": False,
                "influence_scope": "nenhuma; são necessários priors ou blocos contextuais importados",
            })
            return metadata
        if metadata.get("rich_context_available"):
            metadata["message"] = "Snapshot carregado com blocos Acervo/pauta; alinhamento só ocorre com mesma fonte e intervalo sobreposto."
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
    total_acervo_blocks = 0
    total_pauta_candidates = 0
    total_audience_priors = 0
    total_entity_priors = 0
    for account, data in accounts.items():
        if not isinstance(data, dict):
            continue
        hook_count = len(data.get("hook_observations", []))
        example_count = len(data.get("examples", []))
        cohort_count = len(data.get("cohorts", []))
        block_count = len(data.get("acervo_blocks", []))
        pauta_count = len(data.get("acervo_pauta", []))
        audience_count = len(data.get("audience_priors", []))
        entity_count = len(data.get("entity_priors", []))
        total_hook_observations += hook_count
        total_examples += example_count
        total_cohorts += cohort_count
        total_acervo_blocks += block_count
        total_pauta_candidates += pauta_count
        total_audience_priors += audience_count
        total_entity_priors += entity_count
        account_summary[account] = {
            "hook_observations": hook_count,
            "examples": example_count,
            "cohorts": cohort_count,
            "acervo_blocks": block_count,
            "pauta_candidates": pauta_count,
            "audience_priors": audience_count,
            "entity_priors": entity_count,
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
        "total_acervo_blocks": total_acervo_blocks,
        "total_pauta_candidates": total_pauta_candidates,
        "total_audience_priors": total_audience_priors,
        "total_entity_priors": total_entity_priors,
        "rich_context_available": bool(total_acervo_blocks or total_pauta_candidates),
        "influences_ranking": True,
        "influence_scope": "priors limitados de hooks e, quando importados, blocos Acervo alinhados à mesma fonte; não cria cortes, não substitui contexto e não promete viralidade",
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


def build_acervo_alignment(
    text: str,
    start: Any,
    end: Any,
    *,
    source_id: Any = "",
    account: str | None = None,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Match a local candidate only to a same-source, overlapping QA-gated block.

    This intentionally refuses text-only alignment: a similar sentence from a
    different live is not evidence that the current clip belongs to that block.
    The returned signal is a bounded prior and remains reviewable.
    """
    result = {
        "available": False,
        "signal": 50.0,
        "confidence": 0.0,
        "status": "no_snapshot_blocks",
        "review_required": False,
        "reason": "nenhum bloco Acervo local aplicável",
    }
    profile = snapshot if isinstance(snapshot, dict) else {}
    accounts = profile.get("accounts", {}) if isinstance(profile.get("accounts", {}), dict) else {}
    selected_account = account if account in SUPPORTED_ACCOUNTS else profile.get("default_account", "@renansantosmbl")
    account_data = accounts.get(selected_account, {}) if isinstance(accounts.get(selected_account, {}), dict) else {}
    blocks = list(account_data.get("acervo_blocks", []) or []) + list(account_data.get("acervo_pauta", []) or [])
    if not blocks:
        return result
    local_source = _source_key(source_id)
    local_start = _normalize_time(start)
    local_end = _normalize_time(end)
    if not local_source or local_start is None or local_end is None or local_end <= local_start:
        result.update({
            "status": "source_not_verified",
            "review_required": True,
            "reason": "identificador da fonte não foi confirmado; alinhamento Acervo não aplicado",
        })
        return result
    best = None
    for block in blocks:
        block_source = _source_key(block.get("source_video_id") or block.get("source_url"))
        if not block_source or block_source != local_source:
            continue
        block_start = _normalize_time(block.get("start_seconds"))
        block_end = _normalize_time(block.get("end_seconds"))
        if block_start is None or block_end is None or block_end <= block_start:
            continue
        overlap = _interval_overlap_ratio(local_start, local_end, block_start, block_end)
        if overlap <= 0:
            continue
        highlight_text = " ".join(
            f"{item.get('text', '')} {item.get('reason', '')}"
            for item in block.get("highlights", [])
            if isinstance(item, dict)
        )
        semantic = _token_similarity(text, " ".join((block.get("title", ""), block.get("summary", ""), highlight_text)))
        density = _safe_finite(block.get("density_rank"), minimum=0, maximum=100) or 0.0
        self_contained = _safe_finite(block.get("self_contained_rank"), minimum=0, maximum=100) or 0.0
        strength = max(0.0, min(1.0, overlap * 0.62 + semantic * 0.18 + (density / 100.0) * 0.12 + (self_contained / 100.0) * 0.08))
        candidate = (strength, block, overlap, semantic)
        if best is None or candidate[0] > best[0]:
            best = candidate
    if best is None:
        result.update({
            "status": "source_has_no_overlapping_block",
            "review_required": True,
            "reason": "há blocos locais, mas nenhum coincide com a fonte e o intervalo do candidato",
        })
        return result
    strength, block, overlap, semantic = best
    review_required = bool(block.get("gate_warnings") or block.get("needs_context") or block.get("content_class") != "fala")
    result.update({
        "available": True,
        "signal": round(50.0 + min(8.0, strength * 8.0), 1),
        "confidence": round(min(0.98, 0.45 + strength * 0.5), 2),
        "status": "aligned_same_source",
        "review_required": review_required,
        "reason": "bloco Acervo QA-gated sobreposto à mesma fonte; confirme áudio, legenda e contexto antes de aprovar",
        "account": selected_account,
        "block_id": block.get("block_id", ""),
        "origin": "pauta" if block in account_data.get("acervo_pauta", []) else "acervo_block",
        "title": block.get("title", ""),
        "summary": block.get("summary", ""),
        "category": block.get("category", ""),
        "topics": list(block.get("topics", []) or [])[:12],
        "trust_tier": block.get("trust_tier", ""),
        "density_rank": block.get("density_rank"),
        "self_contained_rank": block.get("self_contained_rank"),
        "overlap": round(overlap, 3),
        "semantic_similarity": semantic,
        "highlights": list(block.get("highlights", []) or [])[:5],
        "gate_warnings": list(block.get("gate_warnings", []) or [])[:8],
        "source_video_id": block.get("source_video_id", ""),
    })
    return result


def build_audience_fit(
    text: str,
    *,
    account: str | None = None,
    snapshot: dict[str, Any] | None = None,
    segment: str = "",
) -> dict[str, Any]:
    """Return a bounded audience prior only when an explicit segment is requested."""
    result = {
        "available": False,
        "signal": 50.0,
        "confidence": 0.0,
        "status": "segment_not_requested",
        "review_required": False,
    }
    requested = _normalize(segment).strip()
    if not requested:
        return result
    profile = snapshot if isinstance(snapshot, dict) else {}
    accounts = profile.get("accounts", {}) if isinstance(profile.get("accounts", {}), dict) else {}
    selected_account = account if account in SUPPORTED_ACCOUNTS else profile.get("default_account", "@renansantosmbl")
    account_data = accounts.get(selected_account, {}) if isinstance(accounts.get(selected_account, {}), dict) else {}
    rows = account_data.get("audience_priors", []) if isinstance(account_data.get("audience_priors", []), list) else []
    matching = []
    for row in rows:
        row_segment = _normalize(row.get("segment") or row.get("age") or row.get("sex") or "")
        if row_segment and (requested == row_segment or requested in row_segment or row_segment in requested):
            matching.append(row)
    if not matching:
        result.update({"status": "segment_not_in_snapshot", "review_required": True})
        return result
    similarities = [_token_similarity(text, " ".join(str(row.get(key, "")) for key in ("tag", "category", "entity"))) for row in matching]
    best_similarity = max(similarities or [0.0])
    sample = max(int(row.get("sample_count", 0) or 0) for row in matching)
    signal_values = [float(row.get("signal")) for row in matching if _safe_finite(row.get("signal"), minimum=0) is not None]
    signal = sum(signal_values) / len(signal_values) if signal_values else 50.0
    result.update({
        "available": sample >= 3 and bool(signal_values),
        "signal": round(max(42.0, min(58.0, signal)), 1),
        "confidence": round(min(1.0, sample / 20.0) * max(0.0, min(1.0, best_similarity + 0.25)), 2),
        "status": "available" if sample >= 3 and signal_values else "insufficient_sample",
        "segment": segment,
        "sample_count": sample,
        "matching_rows": len(matching),
        "review_required": True,
        "reason": "prior demográfico auxiliar; denominadores e plataforma devem ser confirmados",
    })
    return result


def attach_acervo_context(
    clips: list[dict[str, Any]],
    snapshot: dict[str, Any] | None,
    *,
    account: str | None = None,
    source_id: Any = "",
    audience_segment: str = "",
) -> list[dict[str, Any]]:
    """Attach only bounded, reviewable Acervo evidence to existing candidates."""
    if not isinstance(clips, list):
        return clips
    for clip in clips:
        if not isinstance(clip, dict):
            continue
        local_source = source_id or _first_present(clip, "source_id", "source_video_id", "video_id", "live_id", default="")
        alignment = build_acervo_alignment(
            clip.get("text", ""), clip.get("start"), clip.get("end"),
            source_id=local_source, account=account, snapshot=snapshot,
        )
        if alignment.get("available") or alignment.get("status") not in {"no_snapshot_blocks"}:
            clip["acervo_alignment"] = alignment
        audience = build_audience_fit(
            clip.get("text", ""), account=account, snapshot=snapshot, segment=audience_segment,
        )
        if audience.get("available") or audience.get("status") not in {"segment_not_requested"}:
            clip["audience_fit"] = audience
    return clips


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", str(text or "").lower())
    return "".join(char for char in value if not unicodedata.combining(char))
