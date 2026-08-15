#!/usr/bin/env python3
"""Build a portable, aggregate-only editorial prior pack.

The input may contain post references, queries, transcripts, or platform payloads.
This script intentionally exports only aggregate hook statistics and stable editorial
rules; it never copies raw media, post IDs, URLs, captions, or transcript text.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modules.instagram_editorial_priors import _aggregate_records


OBSERVED_PATTERNS = [
    {
        "family": "reacao_com_evidencia_externa",
        "selection_rule": "preserve_external_evidence_and_reaction_together",
        "layout_policy": "preserve_composition",
        "quality_gate": "evidence_present and payoff_complete",
    },
    {
        "family": "entrevista_pergunta_resposta",
        "selection_rule": "prefer_question_answer_complete",
        "layout_policy": "preserve_multi_subject_layout",
        "quality_gate": "question_answer_complete",
    },
    {
        "family": "talking_head_grafico",
        "selection_rule": "keep_thesis_and_documentary_overlay",
        "layout_policy": "preserve_composition",
        "quality_gate": "context_complete and evidence_present",
    },
    {
        "family": "conversa_descontraida",
        "selection_rule": "allow_non_political_value_when_payoff_is_complete",
        "layout_policy": "reframe_only_with_stable_single_speaker",
        "quality_gate": "payoff_complete and not starts_mid_sentence",
    },
]


def aggregate_account(account: dict) -> dict:
    grouped: dict[str, list[float]] = defaultdict(list)
    for item in account.get("hook_observations", []):
        hook = str(item.get("hook", "outro") or "outro")[:60]
        try:
            ratio = float(item.get("ratio", 0) or 0)
        except (TypeError, ValueError):
            continue
        if ratio >= 0:
            grouped[hook].append(ratio)

    hooks = []
    for hook, ratios in grouped.items():
        hooks.append({
            "hook": hook,
            "observations": len(ratios),
            "mean_ratio": round(sum(ratios) / len(ratios), 3),
            "max_ratio": round(max(ratios), 3),
        })
    hooks.sort(key=lambda item: (-item["mean_ratio"], item["hook"]))
    return {
        "platform": str(account.get("platform", "unknown"))[:24],
        "hook_priors": hooks,
        "example_count": len(account.get("examples", [])),
        "cohort_count": len(account.get("cohorts", [])),
    }


def build_payload(source: dict, instagram_dataset: dict | None = None) -> dict:
    accounts = {
        str(name): aggregate_account(account)
        for name, account in (source.get("accounts") or {}).items()
        if isinstance(account, dict)
    }
    return {
        "schema_version": "editorial-priors-v1-aggregate-only",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_label": "Campaign Hub aggregate observations",
        "default_account": str(source.get("default_account", "@renansantosmbl") or "@renansantosmbl"),
        "privacy_contract": {
            "raw_media_included": False,
            "transcripts_included": False,
            "post_ids_included": False,
            "urls_included": False,
            "queries_included": False,
            "purpose": "portable ranking priors, not model weights",
        },
        "accounts": accounts,
        "instagram_family_priors": instagram_dataset or {"family_priors": [], "layout_priors": [], "record_count": 0},
        "observed_patterns": OBSERVED_PATTERNS,
        "quality_gates": {
            "context_quality": 0.10,
            "completeness": 0.10,
            "question_answer_complete_bonus": 14,
            "starts_mid_sentence_penalty": -28,
            "unresolved_cliffhanger_penalty": -18,
            "duration_is_soft_preference": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path.home() / "FuriaClipsData/campaign_hub/profile.json")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "data/editorial_priors.json")
    parser.add_argument("--instagram-dataset", type=Path, default=Path.home() / "FuriaClipsData/analyses/instagram-editorial-dataset-v1-2026-08-15.json")
    args = parser.parse_args()
    source = json.loads(args.input.read_text(encoding="utf-8"))
    instagram_dataset = None
    if args.instagram_dataset.exists():
        try:
            raw_instagram = json.loads(args.instagram_dataset.read_text(encoding="utf-8"))
            if isinstance(raw_instagram.get("records"), list):
                instagram_dataset = _aggregate_records(raw_instagram["records"])
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            instagram_dataset = None
    payload = build_payload(source, instagram_dataset=instagram_dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote sanitized priors: {args.output}")
    print(f"accounts: {len(payload['accounts'])}; patterns: {len(payload['observed_patterns'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
