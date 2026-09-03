#!/usr/bin/env python3
"""Renderiza cortes aprovados do Flow News #065 sem legendas, ratio original."""
import json, subprocess, os
from pathlib import Path

CLIPS_PATH = "FuriaClipsData/calibration/clips-flow-065.json"
SOURCE = "FuriaClipsData/downloads/RENAN_SANTOS_-_Flow_News_065 [oGK5E24zTbI].mp4"
OUT_DIR = Path("FuriaClipsData/exports/flow-news-065")
OUT_DIR.mkdir(parents=True, exist_ok=True)

with open(CLIPS_PATH, "r", encoding="utf-8") as f:
    clips = json.load(f)

print(f"Renderizando {len(clips)} cortes...")
for i, clip in enumerate(clips, 1):
    start = clip.get("start", 0)
    duration = clip.get("duration", 0)
    end = clip.get("end", start + duration)
    text = clip.get("text", "")[:80].replace("\n", " ")
    
    out_path = OUT_DIR / f"clip-{i:02d}-{start:.0f}s-{end:.0f}s.mp4"
    
    cmd = [
        "ffmpeg", "-y", "-ss", str(start), "-i", SOURCE,
        "-t", str(duration),
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(out_path)
    ]
    
    print(f"[{i}/{len(clips)}] {start:.1f}s-{end:.1f}s ({duration:.1f}s) -> {out_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        size_mb = out_path.stat().st_size / (1024 * 1024)
        print(f"  OK ({size_mb:.1f} MB)")
    else:
        print(f"  ERRO: {result.stderr[:200]}")

print(f"\nRenderização concluída. Arquivos em: {OUT_DIR}")
