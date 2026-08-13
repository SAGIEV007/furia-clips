#!/usr/bin/env python3
"""Analisa Reels locais com amostras visuais e Gemini multimodal via proxy OpenAI."""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "workspace" / "instagram_reserva"
OUT_DIR = ROOT / "docs" / "instagram_reserva_analysis"
MODEL = "gemini-3-flash-preview"

ITEMS = {
    "Db_OfZDjKMW": {
        "duration": 160.196,
        "width": 1080,
        "height": 1350,
        "caption": "Renan Santos foi questionado de forma dura por um seguidor do podcast 3 irmãos e respondeu sem titubear. #RenanSantos #Política #PartidoMissão #Eleições2026 #RenanPresidente",
    },
    "Db_R92njTCq": {
        "duration": 157.549,
        "width": 1080,
        "height": 1080,
        "caption": "A diferença entre Renan Santos e Flávio Bolsonaro fica gritante a cada entrevista, não há comparação! #RenanSantos #Política #PartidoMissão #Eleições2026 #RenanPresidente",
    },
    "Db_VUXqjnyO": {
        "duration": 32.486,
        "width": 1080,
        "height": 1080,
        "caption": "Discurso forte de Renan Santos em 1° Congresso do Partido Missão viralizou! #RenanSantos #Política #PartidoMissão #Eleições2026 #RenanPresidente",
    },
    "Db_Y07LFV7J": {
        "duration": 109.762,
        "width": 1080,
        "height": 1350,
        "caption": "Na contramão do que vem sendo feito pelos políticos tradicionais, Renan Santos explica que não importa esquerda ou direita, o que importa para população é ter seus problemas solucionados. #RenanSantos #Política #PartidoMissão #Eleições2026 #RenanPresidente",
    },
}

SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "observed_facts": {"type": "string"},
        "visual_timeline": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "timestamp": {"type": "string"},
                    "observation": {"type": "string"},
                },
                "required": ["timestamp", "observation"],
                "additionalProperties": False,
            },
        },
        "hook": {"type": "string"},
        "speech_structure": {"type": "string"},
        "framing": {"type": "string"},
        "captions_and_graphics": {"type": "string"},
        "pacing_and_cuts": {"type": "string"},
        "audio_observations": {"type": "string"},
        "context_and_completion": {"type": "string"},
        "recommended_cut_ranges": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start": {"type": "string"},
                    "end": {"type": "string"},
                    "reason": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["start", "end", "reason", "confidence"],
                "additionalProperties": False,
            },
        },
        "quality_label": {"type": "string", "enum": ["gold", "good", "needs_edit", "weak", "unknown"]},
        "clipability_score": {"type": "number"},
        "automation_rules": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "string"},
    },
    "required": [
        "id", "observed_facts", "visual_timeline", "hook", "speech_structure",
        "framing", "captions_and_graphics", "pacing_and_cuts", "audio_observations",
        "context_and_completion", "recommended_cut_ranges", "quality_label",
        "clipability_score", "automation_rules", "limitations",
    ],
    "additionalProperties": False,
}


def duration_seconds(video: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def extract_frames(video: Path, duration: float, work: Path) -> list[tuple[float, Path]]:
    count = 12 if duration > 90 else 8
    # Evita buscar exatamente no frame final, que pode não existir por arredondamento.
    margin = min(1.0, max(0.5, duration * 0.02))
    times = [min(duration - margin, duration * i / (count - 1)) for i in range(count)]
    frames: list[tuple[float, Path]] = []
    for index, timestamp in enumerate(times):
        frame = work / f"frame_{index:02d}.jpg"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{timestamp:.3f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=720:-2", "-q:v", "3", "-y", str(frame)],
            check=True,
        )
        frames.append((timestamp, frame))
    return frames


def image_part(path: Path, timestamp: float) -> dict:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{encoded}",
            "detail": "low",
        },
    }


def analyze_one(client: OpenAI, clip_id: str, meta: dict) -> dict:
    video = VIDEO_DIR / f"{clip_id}.mp4"
    actual_duration = duration_seconds(video)
    with tempfile.TemporaryDirectory(prefix=f"furia_{clip_id}_") as temp:
        frames = extract_frames(video, actual_duration, Path(temp))
        content: list[dict] = [{
            "type": "text",
            "text": (
                "Analise o Reel local abaixo como editor audiovisual profissional do perfil político "
                "Renan Santos/MBL. Use somente o que puder observar nas imagens amostradas, o áudio "
                "quando perceptível, os timestamps das amostras e a legenda pública fornecida. "
                "Não invente frases, cortes ou músicas que não estejam evidentes. Como não há transcrição "
                "confiável, marque limitações e trate os intervalos recomendados como aproximações. "
                "O objetivo é calibrar o Furia Clips para encontrar cortes autossuficientes, com hook, "
                "contexto, tese, conflito ou proposta e conclusão/payoff. Avalie também se o enquadramento "
                "deve preservar a proporção original ou pode ser refeito com segurança. Retorne apenas o JSON do schema.\n\n"
                f"ID: {clip_id}\n"
                f"Duração medida: {actual_duration:.3f}s\n"
                f"Resolução: {meta['width']}x{meta['height']}\n"
                f"Legenda pública: {meta['caption']}\n\n"
                "Cada imagem será precedida implicitamente pelo timestamp aproximado na ordem temporal. "
                "Inclua no visual_timeline os timestamps das amostras mais relevantes."
            ),
        }]
        for timestamp, frame in frames:
            content.append({"type": "text", "text": f"Quadro aproximado em {timestamp:.1f}s"})
            content.append(image_part(frame, timestamp))

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Você é um analista audiovisual rigoroso. Responda em português brasileiro."},
                {"role": "user", "content": content},
            ],
            max_tokens=10000,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "furia_reel_analysis", "strict": True, "schema": SCHEMA},
            },
        )
        if not getattr(response, "choices", None):
            raw_response = response.model_dump() if hasattr(response, "model_dump") else str(response)
            print(json.dumps(raw_response, ensure_ascii=False, indent=2), file=sys.stderr, flush=True)
            raise RuntimeError(f"Resposta sem choices para {clip_id}")
        payload = response.choices[0].message.content
        if not payload:
            raw_response = response.model_dump() if hasattr(response, "model_dump") else str(response)
            print(json.dumps(raw_response, ensure_ascii=False, indent=2), file=sys.stderr, flush=True)
            raise RuntimeError(f"Resposta vazia para {clip_id}")
        return json.loads(payload)


def main() -> int:
    client = OpenAI()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for clip_id, meta in ITEMS.items():
        output = OUT_DIR / f"{clip_id}.multimodal.json"
        print(f"ANALYZE {clip_id}", flush=True)
        try:
            result = analyze_one(client, clip_id, meta)
            output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"OK {output}", flush=True)
        except Exception as exc:
            print(f"ERROR {clip_id}: {exc}", file=sys.stderr, flush=True)
            traceback.print_exc()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
