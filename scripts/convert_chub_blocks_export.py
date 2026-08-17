#!/usr/bin/env python3
"""Convert one Campaign Hub block-tool result into a Furia local-memory export.

The input is the JSON envelope saved by manus-mcp-cli. This script keeps
metadata, blocks, highlights and transcript sentences, never raw media.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _read_tool_result(path: Path) -> dict:
    """Accept both a saved MCP envelope and the already-unwrapped payload.

    Different clients hand the same block result over differently: some keep the
    ``content[0].text`` envelope, others write the decoded object straight to
    disk. Rejecting the second shape only produced a confusing error about
    missing structured text.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "items" in payload:
        return payload
    text = ((payload.get("content") or [{}])[0]).get("text", "") if isinstance(payload, dict) else ""
    if not text:
        raise ValueError("O retorno do Campaign Hub não contém texto estruturado nem uma lista 'items'.")
    return json.loads(text)


def ignored_regions(transcript: dict | None, video_id: str) -> list[dict]:
    """Regions the Acervo labelled as unusable, kept as an exclusion signal.

    These are not gaps in the data: each one carries a reason, such as an
    unintelligible stretch or an isolated fragment. Feeding them to the selector
    stops candidates from being spent on parts of the source that the labelling
    pipeline already judged to hold no editorial content.
    """
    if not isinstance(transcript, dict):
        return []
    regions = []
    for region in transcript.get("ignoredRegions") or transcript.get("ignored_regions") or []:
        if not isinstance(region, dict):
            continue
        start = region.get("startS", region.get("start_s"))
        end = region.get("endS", region.get("end_s"))
        if start is None or end is None:
            continue
        regions.append({
            "video_id": video_id,
            "start_s": start,
            "end_s": end,
            "duration_s": region.get("durationS", region.get("duration_s")),
            "start_sentence_idx": region.get("startSentenceIdx", region.get("start_sentence_idx")),
            "end_sentence_idx": region.get("endSentenceIdx", region.get("end_sentence_idx")),
            "reason": region.get("reason"),
            "provenance": region.get("provenance"),
        })
    return regions


def convert(payload: dict, transcript: dict | None = None) -> dict:
    items = [item for item in payload.get("items", []) if isinstance(item, dict) and item.get("kind") == "bloco"]
    blocks = []
    highlights = []
    sentences = []
    sources = {}
    for item in items:
        video = item.get("video") if isinstance(item.get("video"), dict) else {}
        video_id = str(video.get("id") or "")
        block_id = str(item.get("id") or "")
        video_metadata = video.get("metadata") if isinstance(video.get("metadata"), dict) else {}
        source = {
            "id": video_id,
            "platform": video.get("platform"),
            "youtube_id": video.get("youtubeId"),
            "url": video.get("url"),
            "title": video.get("title"),
            "duration_s": video.get("durationS"),
            "published_at": video.get("publishedAt"),
            "live_status": video.get("liveStatus"),
            "caption_status": video.get("captionStatus"),
            "channel_title": video_metadata.get("channelTitle"),
        }
        if video_id:
            sources[video_id] = source
        blocks.append({
            "id": block_id,
            "block_version_id": item.get("blockVersionId"),
            "sentence_table_id": item.get("sentenceTableId"),
            "video_id": video_id,
            "title": item.get("title"),
            "summary": item.get("summary"),
            "category": item.get("category"),
            "topics": item.get("topics") or [],
            "start_sentence_idx": item.get("startSentenceIdx"),
            "end_sentence_idx": item.get("endSentenceIdx"),
            "start_s": item.get("startS"),
            "end_s": item.get("endS"),
            "duration_s": item.get("durationS"),
            "density_rank": item.get("densityRank"),
            "self_contained_rank": item.get("selfContainedRank"),
            "needs_context": item.get("needsContext"),
            "possible_cuts": item.get("possibleCuts"),
            "renan_speaking": item.get("renanSpeaking"),
            "trigger_question": item.get("triggerQuestion"),
            "risk_flags": item.get("riskFlags") or [],
            "gate_warnings": item.get("gateWarnings") or [],
            "trust_tier": item.get("trustTier"),
            "trust_tier_label": item.get("trustTierLabel"),
            "labeler_version": item.get("labelerVersion"),
            "source_url": item.get("youtubeUrl") or video.get("url"),
        })
        for highlight in item.get("highlights") or []:
            highlights.append({
                "id": f"{block_id}:{highlight.get('sentenceIdx')}:{highlight.get('startS')}",
                "block_id": block_id,
                "video_id": video_id,
                "sentence_idx": highlight.get("sentenceIdx"),
                "start_s": highlight.get("startS"),
                "end_s": highlight.get("endS"),
                "text": highlight.get("text"),
                "reason": highlight.get("reason"),
            })
        for sentence in item.get("sentences") or []:
            sentences.append({
                "id": f"{video_id}:{sentence.get('idx')}",
                "block_id": block_id,
                "video_id": video_id,
                "idx": sentence.get("idx"),
                "start_s": sentence.get("startS"),
                "end_s": sentence.get("endS"),
                "turn": sentence.get("turn"),
                "speaker_change": sentence.get("speakerChange"),
                "text": sentence.get("text"),
                "audio_check_ranges": sentence.get("audioCheckRanges") or [],
            })

    ignored = ignored_regions(transcript, next(iter(sources), ""))

    # Do not invent performance ratios for Acervo blocks. The account record is
    # only the adapter identity required by the legacy snapshot contract.
    return {
        "schema_version": "campaign-hub-acervo-export-v1",
        "version": "acervo-export-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "default_account": "@renansantosmbl",
        "accounts": {"@renansantosmbl": {"platform": "youtube", "hook_observations": []}},
        "metadata": {
            "source_label": "Campaign Hub Acervo — export autorizado de blocos",
            "query": payload.get("query", ""),
            "retrieval": payload.get("retrieval", {}),
            "caption_provenance_note": payload.get("captionProvenanceNote", ""),
            "model_score_caveat": payload.get("modelScoreCaveat", ""),
            "privacy_contract": {
                "raw_media_included": False,
                "transcripts_included": True,
                "post_ids_included": False,
                "urls_included": True,
                "purpose": "blocos, destaques e contexto para pré-análise local; não são pesos de modelo",
            },
        },
        "sync": {"status": "ready", "source": "campaign_hub_acervo_export"},
        "records": {
            "sources": list(sources.values()),
            "blocks": blocks,
            "highlights": highlights,
            "sentences": sentences,
            "ignored_regions": ignored,
            "transcripts": [],
            "possible_cuts": [],
            "posts": [],
            "metrics": [],
            "entities": [],
            "topics": [],
            "benchmarks": [],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Converte blocos Campaign Hub em export local do Furia.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--transcript",
        type=Path,
        help="Export de chub_acervo_transcript; traz as regiões que o Acervo marcou como sem conteúdo.",
    )
    args = parser.parse_args()
    payload = _read_tool_result(args.input)
    transcript = json.loads(args.transcript.expanduser().read_text(encoding="utf-8")) if args.transcript else None
    export = convert(payload, transcript)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(export, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"blocks": len(export["records"]["blocks"]), "highlights": len(export["records"]["highlights"]), "sentences": len(export["records"]["sentences"]), "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
