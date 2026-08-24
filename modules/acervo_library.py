"""The blocks the Acervo already published for a source, kept next to the media.

The Garimpo reads the Acervo and hands back thematic blocks that a person
reviewed: title, the question that provoked them, the strong moments inside. For
a source that already went through that pipeline, nothing Furia derives on its
own will beat them — they carry human QA and Furia carries a heuristic.

Until now that evidence never reached a cut. The path to the export was a
settings field pointing at a file somebody had to produce with a script, so in
practice it stayed empty and every run read ``bloco_chub: null`` even for sources
with fourteen published blocks. This module closes that gap: exports live in one
folder named by the YouTube id, and the id is read off the media file itself.

Nothing here reaches the network. The export is a file the operator brings in,
and the privacy contract of the original conversion is preserved unchanged.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Downloaders join fields with underscores, dots and spaces, as in
# ``YTDown.com_YouTube_Media_o6yEVC-exk8_001_1080p_b2b50a903b74.mp4``. The hyphen
# is not a separator: it belongs to the id alphabet.
_SEPARATORS = re.compile(r"[^0-9A-Za-z_-]+|_")
_ID_SHAPE = re.compile(r"^[0-9A-Za-z_-]{11}$")


def youtube_id_from_url(url: str) -> str | None:
    """Recover the YouTube id from a standard URL."""
    from urllib.parse import urlparse, parse_qs
    try:
        parsed = urlparse(url)
        if parsed.hostname in ("youtu.be", "www.youtu.be"):
            return parsed.path[1:12] if len(parsed.path) >= 12 else None
        if parsed.hostname in ("youtube.com", "www.youtube.com", "m.youtube.com"):
            if parsed.path.startswith("/live/") or parsed.path.startswith("/shorts/"):
                return parsed.path.split("/")[2][:11]
            qs = parse_qs(parsed.query)
            if "v" in qs:
                return qs["v"][0][:11]
    except Exception:
        pass
    return None


def youtube_id_from_name(name: str) -> str | None:
    """Recover the YouTube id a downloader left in the file name.

    A YouTube id is eleven characters of an alphabet that overlaps with what
    downloaders put around it, so length alone is not enough: a twelve-character
    hash is rejected by length, but an eleven-character one would not be. What
    separates them is shape — a real id carries an upper-case letter, a hyphen or
    an underscore, and a lower-case hexadecimal fragment carries none of the
    three.

    A wrong guess costs nothing: it looks for an export that does not exist, and
    the run proceeds reading the source on its own. A right one saves configuring
    a path by hand for every video.
    """
    stem = Path(str(name or "")).stem
    for token in _SEPARATORS.split(stem):
        if not _ID_SHAPE.match(token or ""):
            continue
        if not any(char.isalpha() for char in token):
            continue
        if not (any(char.isupper() for char in token) or "-" in token or "_" in token):
            continue
        return token
    return None


def library_dir(data_dir: str | os.PathLike[str] | None = None) -> Path:
    """Where the exports live, beside the other local artefacts."""
    base = Path(data_dir or os.environ.get("FURIA_CLIPS_DATA_DIR") or (Path.home() / "FuriaClipsData"))
    return base / "acervo"


def snapshot_path_for(video_path: str | os.PathLike[str] | None, data_dir=None) -> Path | None:
    """The export that belongs to this media file, whether or not it exists."""
    if not video_path:
        return None
    youtube_id = youtube_id_from_name(Path(str(video_path)).name)
    if not youtube_id:
        return None
    return library_dir(data_dir) / f"{youtube_id}.json"


def find_snapshot_for(video_path, data_dir=None) -> Path | None:
    """The export for this media file, only when it is really there."""
    candidate = snapshot_path_for(video_path, data_dir)
    return candidate if candidate and candidate.is_file() else None


def describe_snapshot(path: str | os.PathLike[str] | None) -> dict[str, Any]:
    """What an export holds, in the terms the operator thinks in.

    Used to tell them, before any cut is made, whether this source arrives with
    blocks a person already reviewed or whether Furia will be reading it alone.
    """
    empty = {"available": False, "blocks": 0, "highlights": 0, "sentences": 0, "title": "", "video_id": ""}
    if not path:
        return empty
    try:
        payload = json.loads(Path(str(path)).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return empty
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, dict):
        return empty
    sources = records.get("sources") or []
    first = sources[0] if sources and isinstance(sources[0], dict) else {}
    # `possible_cuts` é contagem por bloco, não uma lista de cortes: o Acervo diz
    # quantos cortes cabem num bloco, não quais são. Contar o comprimento da
    # lista vazia dizia 0 num vídeo onde o rótulo humano prevê 65.
    cortes = sum(
        int((block or {}).get("possible_cuts") or 0)
        for block in (records.get("blocks") or [])
        if isinstance(block, dict)
    )
    return {
        "available": True,
        "blocks": len(records.get("blocks") or []),
        "highlights": len(records.get("highlights") or []),
        "sentences": len(records.get("sentences") or []),
        "possible_cuts": cortes,
        "title": str(first.get("title") or ""),
        "video_id": str(first.get("youtube_id") or first.get("id") or ""),
        "collected_at": str(payload.get("collected_at") or ""),
    }


def read_tool_result(payload: Any) -> dict[str, Any]:
    """Accept both a saved MCP envelope and the already-unwrapped payload.

    Different clients hand the same block result over differently: some keep the
    ``content[0].text`` envelope, others write the decoded object straight to
    disk. Rejecting the second shape only produced a confusing error about
    missing structured text.
    """
    if isinstance(payload, str):
        payload = json.loads(payload)
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
    """Turn one Campaign Hub block result into the local export shape."""
    items = [item for item in payload.get("items", []) if isinstance(item, dict) and item.get("kind") == "bloco"]
    blocks: list[dict] = []
    highlights: list[dict] = []
    sentences: list[dict] = []
    sources: dict[str, dict] = {}
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
            "speakers_note": item.get("speakersNote"),
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

    # E o resto da linha do tempo, quando a tabela de frases veio junto.
    #
    # Os blocos trazem só as frases que caíram dentro deles: em João Pessoa são
    # 1113 de 1266, e as 153 que sobram não são lixo — são as transições, as
    # perguntas soltas e os trechos que a rotulagem marcou como sem conteúdo.
    # Descartá-las custava duas coisas. A primeira é que um corte que precisa
    # recuar até a pergunta não encontrava a pergunta, porque ela mora na
    # fronteira e a fronteira ficava de fora. A segunda é maior: cada frase do
    # Acervo carrega `turn` e `speakerChange` já apurados por eles, que é
    # exatamente a informação que o Furia reconstrói na marra a partir dos ">>"
    # da legenda — e reconstrói pior, porque a marca diz que trocou e o `turn`
    # diz de quem para quem.
    conhecidas = {sentence["idx"] for sentence in sentences if sentence.get("idx") is not None}
    fora_de_bloco = 0
    if isinstance(transcript, dict):
        video_id = str((transcript.get("video") or {}).get("id") or next(iter(sources), ""))
        for sentence in transcript.get("sentences") or []:
            if not isinstance(sentence, dict) or sentence.get("idx") in conhecidas:
                continue
            sentences.append({
                "id": f"{video_id}:{sentence.get('idx')}",
                "block_id": None,
                "video_id": video_id,
                "idx": sentence.get("idx"),
                "start_s": sentence.get("startS"),
                "end_s": sentence.get("endS"),
                "turn": sentence.get("turn"),
                "speaker_change": sentence.get("speakerChange"),
                "text": sentence.get("text"),
                "audio_check_ranges": sentence.get("audioCheckRanges") or [],
            })
            fora_de_bloco += 1
        sentences.sort(key=lambda item: (item.get("idx") is None, item.get("idx") or 0))

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
        # Quantas frases vieram de fora dos blocos, para que ninguém confunda a
        # linha do tempo inteira com o recorte que passou pela rotulagem.
        "coverage": {
            "sentences_in_blocks": len(sentences) - fora_de_bloco,
            "sentences_outside_blocks": fora_de_bloco,
            "possible_cuts_total": sum(
                int(block.get("possible_cuts") or 0) for block in blocks
            ),
        },
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


def store_export(payload: Any, transcript: Any = None, *, video_path=None, data_dir=None) -> dict[str, Any]:
    """Convert an Acervo block result and file it under the source's id.

    The id comes from the export itself whenever the blocks carry one, and from
    the media file name otherwise, so an operator who pastes the right blocks for
    the wrong video is told instead of silently poisoning the next cut.
    """
    export = convert(read_tool_result(payload), read_tool_result(transcript) if transcript else None)
    sources = export["records"]["sources"]
    if not export["records"]["blocks"]:
        raise ValueError("O export não contém nenhum bloco do Acervo.")

    youtube_id = str((sources[0] if sources else {}).get("youtube_id") or "").strip()
    expected = youtube_id_from_name(Path(str(video_path)).name) if video_path else None
    if youtube_id and expected and youtube_id != expected:
        raise ValueError(
            f"Os blocos são do vídeo {youtube_id} e a mídia carregada é {expected}. "
            "Importe o export correspondente a este vídeo."
        )
    youtube_id = youtube_id or expected
    if not youtube_id:
        raise ValueError("Não foi possível identificar o vídeo do YouTube nem no export nem no nome do arquivo.")

    target = library_dir(data_dir) / f"{youtube_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(export, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"path": str(target), **describe_snapshot(target)}
