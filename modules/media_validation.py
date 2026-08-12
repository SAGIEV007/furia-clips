"""Deterministic media validation helpers.

The validator intentionally returns data instead of raising for normal media
problems so the job layer can present actionable diagnostics to the user.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MediaValidation:
    valid: bool
    path: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    format_name: Optional[str] = None
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    has_audio: bool = False
    has_video: bool = False
    streams: int = 0
    raw_probe: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "valid": self.valid,
            "path": self.path,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "format_name": self.format_name,
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "has_audio": self.has_audio,
            "has_video": self.has_video,
            "streams": self.streams,
        }


def probe_media(path: str, timeout: int = 20) -> Dict[str, Any]:
    """Return ffprobe JSON or raise a useful runtime error."""

    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe não encontrado no PATH")
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    command = [
        ffprobe,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        path,
    ]
    completed = subprocess.run(
        command, capture_output=True, text=True, timeout=timeout, check=False
    )
    if completed.returncode != 0:
        detail = (completed.stderr or "falha desconhecida").strip()
        raise RuntimeError(f"ffprobe falhou: {detail[-500:]}")
    try:
        return json.loads(completed.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError("ffprobe retornou JSON inválido") from exc


def validate_media(
    path: str,
    *,
    expected_duration: Optional[float] = None,
    duration_tolerance: float = 1.0,
    expected_width: Optional[int] = None,
    expected_height: Optional[int] = None,
    require_audio: bool = True,
    require_video: bool = True,
) -> MediaValidation:
    """Validate a rendered media file using ffprobe metadata."""

    result = MediaValidation(valid=False, path=path)
    try:
        probe = probe_media(path)
    except (OSError, RuntimeError) as exc:
        result.errors.append(str(exc))
        return result

    result.raw_probe = probe
    streams = probe.get("streams") or []
    fmt = probe.get("format") or {}
    result.streams = len(streams)
    result.format_name = fmt.get("format_name")

    try:
        result.duration = float(fmt.get("duration"))
    except (TypeError, ValueError):
        result.errors.append("Duração ausente ou inválida")

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    result.has_video = video_stream is not None
    result.has_audio = audio_stream is not None

    if video_stream:
        try:
            result.width = int(video_stream.get("width"))
            result.height = int(video_stream.get("height"))
        except (TypeError, ValueError):
            result.errors.append("Resolução de vídeo ausente ou inválida")

    if require_video and not result.has_video:
        result.errors.append("Arquivo não contém stream de vídeo")
    if require_audio and not result.has_audio:
        result.errors.append("Arquivo não contém stream de áudio")
    if result.duration is not None and result.duration <= 0:
        result.errors.append("Arquivo possui duração inválida")
    if expected_duration is not None and result.duration is not None:
        if abs(result.duration - expected_duration) > duration_tolerance:
            result.errors.append(
                f"Duração {result.duration:.3f}s fora da tolerância de "
                f"{expected_duration:.3f}s ± {duration_tolerance:.3f}s"
            )
    if expected_width is not None and result.width != expected_width:
        result.errors.append(f"Largura {result.width} diferente de {expected_width}")
    if expected_height is not None and result.height != expected_height:
        result.errors.append(f"Altura {result.height} diferente de {expected_height}")

    if result.width and result.height and result.width / result.height < 0.4:
        result.warnings.append("Aspecto extremamente estreito; revise o enquadramento")
    if not os.path.getsize(path):
        result.errors.append("Arquivo vazio")

    result.valid = not result.errors
    return result
