"""Platform-oriented render presets for social short-form video."""

from __future__ import annotations

from copy import deepcopy


PRESETS = {
    "shorts": {
        "name": "YouTube Shorts",
        "width": 1080,
        "height": 1920,
        "aspect": "9:16",
        "max_duration": 180,
        "safe_top": 180,
        "safe_bottom": 300,
    },
    "political_shorts": {
        "name": "Politica Editorial — 9:16",
        "width": 1080,
        "height": 1920,
        "aspect": "9:16",
        "max_duration": 180,
        "safe_top": 220,
        "safe_bottom": 360,
        "editorial_profile": "renan_santos_politics",
        "caption_mode": "keyword_impact",
        "audio_policy": "voice_and_ambience",
    },
    "reels": {
        "name": "Instagram Reels",
        "width": 1080,
        "height": 1920,
        "aspect": "9:16",
        "max_duration": 90,
        "safe_top": 180,
        "safe_bottom": 320,
    },
    "tiktok": {
        "name": "TikTok",
        "width": 1080,
        "height": 1920,
        "aspect": "9:16",
        "max_duration": 600,
        "safe_top": 220,
        "safe_bottom": 360,
    },
    "square": {
        "name": "Quadrado",
        "width": 1080,
        "height": 1080,
        "aspect": "1:1",
        "max_duration": 600,
        "safe_top": 100,
        "safe_bottom": 140,
    },
    "landscape": {
        "name": "Paisagem",
        "width": 1920,
        "height": 1080,
        "aspect": "16:9",
        "max_duration": 900,
        "safe_top": 80,
        "safe_bottom": 120,
    },
}


def get_preset(name: str = "shorts") -> dict:
    key = (name or "shorts").lower().strip()
    if key not in PRESETS:
        raise ValueError(f"Preset de vídeo desconhecido: {name}")
    return deepcopy(PRESETS[key])


def list_presets() -> list:
    return [{"id": key, **value} for key, value in PRESETS.items()]


def ffmpeg_video_filter(preset: dict, *, layout: str = "center") -> str | None:
    width = int(preset["width"])
    height = int(preset["height"])
    aspect = width / height
    if abs(aspect - 1.0) < 0.01:
        crop = r"crop=min(iw\,ih):min(iw\,ih)"
    elif aspect > 1.0:
        crop = f"crop=iw:iw/{aspect:.6f}"
    else:
        crop = f"crop=ih*{aspect:.6f}:ih"
    if layout == "debate" and preset["aspect"] == "9:16":
        return f"scale={width}:-2,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
    return f"{crop},scale={width}:{height}"
