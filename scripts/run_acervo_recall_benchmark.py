#!/usr/bin/env python3
"""Measure Furia selection against a whole Acervo-labelled video.

The existing benchmark (`run_editorial_benchmark.py`) compares a handful of
already-persisted candidates against one block. This one runs the real selector
over the full transcript of a long source and scores it against every QA-gated
block and highlight the Acervo produced for that same video.

It needs no media file: the selector works on the transcript timeline, so a
transcript export is enough to get a reproducible recall number. Audio energy and
scene changes are absent, which the report states explicitly instead of hiding.

Nothing here approves a clip and nothing is written back to the Campaign Hub.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.clip_selector import ClipSelector  # noqa: E402


def _load(path: Path) -> dict:
    return json.loads(path.expanduser().read_text(encoding="utf-8"))


def _float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _overlap(left: tuple[float, float], right: tuple[float, float]) -> float:
    return max(0.0, min(left[1], right[1]) - max(left[0], right[0]))


def _iou(left: tuple[float, float], right: tuple[float, float]) -> float:
    union = max(left[1], right[1]) - min(left[0], right[0])
    return round(_overlap(left, right) / union, 4) if union > 0 else 0.0


def transcript_segments(transcript: dict) -> list[dict]:
    """Turn the Acervo sentence table into the segment shape the selector reads."""
    segments = []
    for sentence in transcript.get("sentences") or []:
        text = str(sentence.get("text") or "").strip()
        if not text:
            continue
        segments.append({
            "id": sentence.get("idx"),
            "start": _float(sentence.get("startS")),
            "end": _float(sentence.get("endS")),
            "text": text,
            # ``turn`` marks a caption-detected change, never an identity, so it
            # travels as a timing signal and never as a speaker name.
            "speaker_turn_valid": True,
        })
    return segments


def references(snapshot: dict, video_youtube_id: str) -> tuple[list[dict], list[dict]]:
    records = snapshot.get("records") or {}
    source_ids = {
        str(item.get("id"))
        for item in records.get("sources") or []
        if str(item.get("youtube_id") or "") == video_youtube_id
    }
    blocks = [
        block for block in records.get("blocks") or []
        if not source_ids or str(block.get("video_id")) in source_ids
    ]
    block_ids = {str(block.get("id")) for block in blocks}
    highlights = [
        highlight for highlight in records.get("highlights") or []
        if str(highlight.get("block_id")) in block_ids
    ]
    return blocks, highlights


def score(candidates: list[dict], blocks: list[dict], highlights: list[dict], ignored: list[dict]) -> dict:
    spans = [(_float(item.get("start")), _float(item.get("end"))) for item in candidates]
    spans = [span for span in spans if span[1] > span[0]]

    covered_highlights = []
    for highlight in highlights:
        window = (_float(highlight.get("start_s")), _float(highlight.get("end_s")))
        if window[1] <= window[0]:
            continue
        best = max((_overlap(span, window) / (window[1] - window[0]) for span in spans), default=0.0)
        covered_highlights.append({
            "block_id": highlight.get("block_id"),
            "sentence_idx": highlight.get("sentence_idx"),
            "start_s": window[0],
            "end_s": window[1],
            "contained_fraction": round(best, 4),
            # A highlight only counts as recovered when the candidate carries it
            # whole. A clip that clips the punchline did not recover it.
            "recovered": best >= 0.999,
            "text": str(highlight.get("text") or "")[:120],
        })

    covered_blocks = []
    for block in blocks:
        window = (_float(block.get("start_s")), _float(block.get("end_s")))
        if window[1] <= window[0]:
            continue
        best_iou = max((_iou(span, window) for span in spans), default=0.0)
        touching = [span for span in spans if _overlap(span, window) > 0]
        covered_blocks.append({
            "block_id": block.get("id"),
            "title": str(block.get("title") or "")[:90],
            "start_s": window[0],
            "end_s": window[1],
            "renan_speaking": block.get("renan_speaking"),
            "density_rank": block.get("density_rank"),
            "candidates_touching": len(touching),
            "best_iou": best_iou,
            "touched": bool(touching),
        })

    # Candidates landing where the Acervo said there is no usable content are a
    # precision failure the previous benchmark could not see at all.
    ignored_spans = [
        (_float(region.get("startS")), _float(region.get("endS")))
        for region in ignored
        if _float(region.get("endS")) > _float(region.get("startS"))
    ]
    in_ignored = []
    for span in spans:
        wasted = sum(_overlap(span, region) for region in ignored_spans)
        length = span[1] - span[0]
        if length > 0 and wasted / length >= 0.5:
            in_ignored.append({"start": span[0], "end": span[1], "ignored_fraction": round(wasted / length, 3)})

    # Precision side of the ledger. A block is a stretch the Acervo judged to be a
    # coherent unit, so a candidate sitting mostly inside one is on labelled
    # content. Blocks do not tile the whole source, so a candidate outside every
    # block is not automatically wrong — it is unendorsed, and reported as such.
    block_spans = [
        (_float(block.get("start_s")), _float(block.get("end_s")))
        for block in blocks
        if _float(block.get("end_s")) > _float(block.get("start_s"))
    ]
    on_block = 0
    off_block = 0
    carrying_highlight = 0
    for span in spans:
        length = span[1] - span[0]
        covered = max((_overlap(span, block) for block in block_spans), default=0.0)
        if length > 0 and covered / length >= 0.5:
            on_block += 1
        elif covered <= 0:
            off_block += 1
        if any(
            _overlap(span, (_float(h.get("start_s")), _float(h.get("end_s")))) > 0
            for h in highlights
        ):
            carrying_highlight += 1

    durations = [span[1] - span[0] for span in spans]
    recovered = sum(1 for item in covered_highlights if item["recovered"])
    touched = sum(1 for item in covered_blocks if item["touched"])
    return {
        "candidate_count": len(spans),
        "on_block_candidates": on_block,
        "off_block_candidates": off_block,
        "candidates_carrying_highlight": carrying_highlight,
        "precision_on_block": round(on_block / len(spans), 4) if spans else None,
        "precision_carrying_highlight": round(carrying_highlight / len(spans), 4) if spans else None,
        "highlight_total": len(covered_highlights),
        "highlight_recovered": recovered,
        "highlight_recall": round(recovered / len(covered_highlights), 4) if covered_highlights else None,
        "block_total": len(covered_blocks),
        "block_touched": touched,
        "block_coverage": round(touched / len(covered_blocks), 4) if covered_blocks else None,
        "mean_best_iou": round(sum(item["best_iou"] for item in covered_blocks) / len(covered_blocks), 4) if covered_blocks else None,
        "candidates_in_ignored_regions": len(in_ignored),
        "duration_s": {
            "min": round(min(durations), 2) if durations else None,
            "mean": round(sum(durations) / len(durations), 2) if durations else None,
            "max": round(max(durations), 2) if durations else None,
        },
        "highlights": covered_highlights,
        "blocks": covered_blocks,
        "ignored_region_hits": in_ignored,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Mede o recall do Furia contra um vídeo inteiro rotulado pelo Acervo.")
    parser.add_argument("--transcript", type=Path, required=True, help="Export de chub_acervo_transcript.")
    parser.add_argument("--memory", type=Path, required=True, help="Snapshot local convertido dos blocos.")
    parser.add_argument("--video", required=True, help="ID do YouTube do vídeo medido.")
    parser.add_argument("--max-clips", type=int, default=40)
    parser.add_argument("--min-duration", type=int, default=20)
    parser.add_argument("--max-duration", type=int, default=180)
    parser.add_argument("--guided", action="store_true", help="Ativa o caminho campaign_hub_guided.")
    parser.add_argument("--out", type=Path, help="Grava o relatório completo em JSON.")
    args = parser.parse_args()

    transcript = _load(args.transcript)
    snapshot = _load(args.memory)
    segments = transcript_segments(transcript)
    if not segments:
        raise SystemExit("A transcrição informada não contém frases utilizáveis.")

    blocks, highlights = references(snapshot, args.video)
    if not blocks:
        raise SystemExit(f"O snapshot não contém blocos para o vídeo {args.video}.")

    media_duration = _float((transcript.get("video") or {}).get("durationS")) or max(item["end"] for item in segments)
    settings = {"media_duration": media_duration, "editorial_context": {}}
    if args.guided:
        settings["campaign_hub_snapshot"] = snapshot
        settings["campaign_hub_account"] = snapshot.get("default_account")

    selector = ClipSelector(
        max_clips=args.max_clips,
        min_duration=args.min_duration,
        max_duration=args.max_duration,
    )
    candidates = selector.select_clips({"segments": segments}, settings=settings) or []

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "video": {
            "youtube_id": args.video,
            "title": (transcript.get("video") or {}).get("title"),
            "duration_s": media_duration,
            "sentence_count": len(segments),
        },
        "run": {
            "selection_source": selector.get_selection_source(),
            "guided_path": bool(args.guided),
            "max_clips": args.max_clips,
            "min_duration": args.min_duration,
            "max_duration": args.max_duration,
            # Stated rather than implied: this measures transcript-driven
            # selection, not the full production pipeline.
            "energy_profile": False,
            "scene_changes": False,
        },
        "caption_provenance": transcript.get("captionProvenance"),
        "speaker_attribution_note": transcript.get("speakerAttributionNote"),
        "metrics": score(candidates, blocks, highlights, transcript.get("ignoredRegions") or []),
    }

    metrics = report["metrics"]
    print(json.dumps({
        "video": report["video"]["title"],
        "duration_s": media_duration,
        "selection_source": report["run"]["selection_source"],
        "candidate_count": metrics["candidate_count"],
        "highlight_recall": f"{metrics['highlight_recovered']}/{metrics['highlight_total']}",
        "block_coverage": f"{metrics['block_touched']}/{metrics['block_total']}",
        "precision_on_block": metrics["precision_on_block"],
        "precision_carrying_highlight": metrics["precision_carrying_highlight"],
        "off_block_candidates": metrics["off_block_candidates"],
        "mean_best_iou": metrics["mean_best_iou"],
        "candidates_in_ignored_regions": metrics["candidates_in_ignored_regions"],
        "duration_s_stats": metrics["duration_s"],
    }, ensure_ascii=False, indent=2))

    if args.out:
        args.out.expanduser().parent.mkdir(parents=True, exist_ok=True)
        args.out.expanduser().write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nRelatório completo: {args.out.expanduser()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
