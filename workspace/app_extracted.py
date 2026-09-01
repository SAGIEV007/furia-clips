import os
import sys
import json
import uuid
import shutil
import threading
import subprocess
import platform
import secrets
import tempfile
import requests
import re
import unicodedata
import math
from datetime import datetime


def _coerce_bool(value, default=False):
    """Interpret JSON and form-style booleans consistently at API boundaries."""
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value).strip().lower()
    if not normalized:
        return bool(default)
    return normalized not in {"0", "false", "no", "off", "disabled", "nao", "não"}


# Load local environment files. The persistent file lives outside the checkout
# so replacing the GitHub folder does not remove the Gemini configuration.
_PROJECT_ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
_PERSISTENT_ROOT = os.environ.get("FURIA_CLIPS_DATA_DIR") or os.path.join(
    os.path.expanduser("~"), "FuriaClipsData"
)
_PERSISTENT_ENV_PATH = os.environ.get("FURIA_CLIPS_ENV_FILE") or os.path.join(
    os.path.abspath(os.path.expanduser(_PERSISTENT_ROOT)), "config", "local.env"
)
_ENV_PATHS = [_PERSISTENT_ENV_PATH, _PROJECT_ENV_PATH]


def _auto_fetch_chub_snapshot() -> None:
    """On startup, fetch a fresh Chub MCP snapshot if no local snapshot exists."""
    try:
        snapshot_path = os.path.join(
            os.path.abspath(os.path.expanduser(_PERSISTENT_ROOT)),
            "campaign_hub",
            "profile.json",
        )
        if os.path.exists(snapshot_path) and os.path.getsize(snapshot_path) > 0:
            return
        from modules.chub_mcp import fetch_snapshot
        account = os.environ.get("CHUB_MCP_ACCOUNT", "@renansantosmbl")
        snapshot = fetch_snapshot(account=account)
        if snapshot:
            os.makedirs(os.path.dirname(snapshot_path), exist_ok=True)
            with open(snapshot_path, "w", encoding="utf-8") as handle:
                json.dump(snapshot, handle, ensure_ascii=False, indent=2)
    except Exception:
        pass


_auto_fetch_chub_snapshot()
try:
    from dotenv import load_dotenv
    for _env_path in _ENV_PATHS:
        load_dotenv(_env_path, override=False)
except ImportError:
    # python-dotenv not installed — load local files manually
    for _env_path in _ENV_PATHS:
        if os.path.exists(_env_path):
            with open(_env_path, "r", encoding="utf-8") as _ef:
                for _line in _ef:
                    _line = _line.strip()
                    if _line and not _line.startswith("#") and "=" in _line:
                        _k, _v = _line.split("=", 1)
                        os.environ.setdefault(_k.strip(), _v.strip())

from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
try:
    from flask_socketio import SocketIO, emit
except ImportError:  # Optional dependency fallback for minimal local installs.
    def emit(*args, **kwargs):
        return None

    class SocketIO:
        def __init__(self, app, *args, **kwargs):
            self.app = app

        def on(self, _event):
            def decorator(func):
                return func
            return decorator

        def emit(self, *_args, **_kwargs):
            return None

        def run(self, app, **kwargs):
            kwargs.pop("allow_unsafe_werkzeug", None)
            return app.run(**kwargs)

from config import (
    BASE_DIR, WORKSPACE_DIR, UPLOAD_DIR, PROCESSED_DIR,
    EXPORT_DIR, THUMBNAIL_DIR, ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE, DB_PATH, PERSISTENT_DATA_DIR, PERSISTENT_TRANSCRIPTS_DIR
)
from database import (
    init_db, get_all_settings, get_setting, set_setting,
    create_project, get_project, get_all_projects, update_project_status,
    save_clip, get_clip, get_clips, update_clip_seo, update_clip_thumbnail,
    get_existing_clip_fingerprints, save_transcription, get_transcription, log_action,
    update_clip_editorial_score, save_clip_feedback, get_clip_feedback,
    update_clip_review_status, save_clip_adjustment, update_clip_rendered_file, get_feedback_calibration, get_approved_clip_feature_prior, get_daily_editorial_progress,
    get_source_signature,
    save_headline_feedback, get_headline_feedback_summary, get_headline_learning_preferences,
    save_performance_snapshot, get_performance_snapshots, get_performance_summary
)
from modules.security import UnsafePathError, safe_workspace_path, unique_storage_name
from modules.native_dialogs import DialogError, choose_path, open_local_path
from modules.transcript_parser import parse_transcript_text, normalize_segment_payload, parse_timestamp
from modules.clip_adjustments import adjust_clip_bounds
from modules.editorial_block import build_editorial_block
from modules.performance_metrics import normalize_snapshot, metric_labels, summarize_snapshots
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from modules.transcript_archive import archive_transcription, list_archived_transcriptions, validate_transcription
from modules.editorial_search import search_cached_campaign_hub
from modules.source_ingest import (
    SourceIngestError,
    probe_public_url,
    download_public_video,
    download_public_subtitles,
    validate_public_url,
)
from modules.job_manager import JobManager, JobCancelled
from modules.cancellation import OperationCancelled
from modules.batch_queue import build_manifest
from modules.render_presets import get_preset, list_presets
from modules.persistent_data import (
    PersistentDataError,
    create_editorial_backup,
    get_editorial_data_summary,
    restore_editorial_backup,
)
from modules.repository_sync import (
    RepositorySyncError,
    get_repository_status,
    push_feedback_snapshot,
    restore_feedback_snapshot,
    update_from_github,
)

# ---------------------------------------------------------------------------
# Logging setup — tudo que o Fúria faz é registrado em disco
# ---------------------------------------------------------------------------
_LOG_DIR = os.path.join(PERSISTENT_DATA_DIR, "logs")
os.makedirs(_LOG_DIR, exist_ok=True)
_LOG_PATH = os.path.join(_LOG_DIR, "furia.log")

_furia_logger = logging.getLogger("furia")
_furia_logger.setLevel(logging.DEBUG)
_furia_logger.propagate = False

_file_handler = RotatingFileHandler(
    _LOG_PATH, maxBytes=10 * 1024 * 1024, backupCount=20, encoding="utf-8"
)
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
))

_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s", datefmt="%H:%M:%S"
))

_furia_logger.addHandler(_file_handler)
_furia_logger.addHandler(_console_handler)

_job_context = threading.local()


def set_job_context(*, job_id=None, operation=None, source_video=None):
    _job_context.job_id = job_id
    _job_context.operation = operation
    _job_context.source_video = source_video


def clear_job_context():
    _job_context.job_id = None
    _job_context.operation = None
    _job_context.source_video = None


def _job_meta():
    job_id = getattr(_job_context, "job_id", None)
    operation = getattr(_job_context, "operation", None)
    source_video = getattr(_job_context, "source_video", None)
    parts = []
    if job_id:
        parts.append(f"job={job_id}")
    if operation:
        parts.append(f"op={operation}")
    if source_video:
        parts.append(f"src={os.path.basename(source_video)}")
    return " ".join(parts) if parts else ""


def _format_stage(stage, extra=""):
    meta = _job_meta()
    suffix = f" | {extra}" if extra else ""
    return f"[{stage}] {meta}{suffix}"


def log_info(message: str, *, stage: str = "") -> None:
    if stage:
        message = _format_stage(stage, message)
    _furia_logger.info(message)


def log_warning(message: str, *, stage: str = "") -> None:
    if stage:
        message = _format_stage(stage, message)
    _furia_logger.warning(message)


def log_error(message: str, *, stage: str = "", exc_info: bool = False) -> None:
    if stage:
        message = _format_stage(stage, message)
    _furia_logger.error(message, exc_info=exc_info)


def log_debug(message: str, *, stage: str = "") -> None:
    if stage:
        message = _format_stage(stage, message)
    _furia_logger.debug(message)


class StageTimer:
    def __init__(self, name, job_id=None, operation=None, source_video=None):
        self.name = name
        self.job_id = job_id
        self.operation = operation
        self.source_video = source_video
        self.start = None

    def __enter__(self):
        self.start = datetime.now()
        log_info(f"INICIO stage={self.name}", stage=self.name)
        set_job_context(job_id=self.job_id, operation=self.operation, source_video=self.source_video)
        return self

    def __exit__(self, exc_type, exc, tb):
        elapsed = (datetime.now() - self.start).total_seconds() if self.start else None
        meta = _job_meta()
        if exc_type:
            log_error(
                f"FALHA stage={self.name} elapsed={elapsed:.2f}s {meta}",
                stage=self.name,
                exc_info=True,
            )
        else:
            log_info(f"FIM stage={self.name} elapsed={elapsed:.2f}s {meta}", stage=self.name)
        clear_job_context()
        return False

# User-friendly error messages (Portuguese)
ERROR_MESSAGES = {
    "no_audio": "Este video NAO contem audio! Provavelmente foi baixado no formato DASH (so video). Baixe novamente com audio incluido. No yt-dlp use: -f bestvideo+bestaudio --merge-output-format mp4",
    "unsupported_format": "Formato de video nao suportado. Tente converter para MP4 primeiro.",
    "ffmpeg_not_found": "FFmpeg nao encontrado. Instale de: https://ffmpeg.org/download.html",
    "file_not_found": "Video nao encontrado no caminho especificado.",
    "ollama_unavailable": "Ollama não detectado. Usando NLP local (menos preciso). Instale em: https://ollama.com",
    "processing_active": "Ja existe um processamento em andamento. Aguarde o termino.",
    "disk_full": "Espaco em disco insuficiente para gerar os clips.",
    "timeout": "A operacao demorou muito e foi cancelada. Tente com um video menor.",
}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FURIA_SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE

_ALLOWED_CORS = [
    origin.strip()
    for origin in os.environ.get(
        "FURIA_CORS_ORIGINS",
        "http://127.0.0.1:3001,http://localhost:3001",
    ).split(",")
    if origin.strip()
]
socketio = SocketIO(app, cors_allowed_origins=_ALLOWED_CORS, async_mode="threading")


def _runtime_revision():
    """Return a safe checkout revision for diagnostics, never a secret."""
    configured = str(os.environ.get("FURIA_CLIPS_VERSION", "") or "").strip()
    if configured:
        return configured[:80]
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        ).strip() or "checkout-sem-revisão"
    except Exception:
        return "checkout-sem-revisão"


PROGRAM_VERSION = "rebuild-opus-parity"
PROGRAM_REVISION = _runtime_revision()


def _get_approved_clip_prior():
    """Prefer a real sanitized import when eligible; otherwise use local DB aggregates."""
    database_prior = get_approved_clip_feature_prior()
    try:
        from modules.approved_clip_priors import build_feature_prior, load_feature_records
        imported_prior = build_feature_prior(load_feature_records())
    except (OSError, TypeError, ValueError):
        imported_prior = {"available": False, "eligible": False}
    if imported_prior.get("eligible"):
        return imported_prior
    if database_prior.get("eligible") or database_prior.get("available"):
        return database_prior
    return imported_prior if imported_prior.get("available") else database_prior


processing_lock = threading.Lock()
adjust_render_lock = threading.Lock()
active_adjust_render_ids = set()


def _claim_adjust_render(clip_id):
    """Claim one clip for re-rendering so duplicate clicks cannot race."""
    try:
        normalized_id = int(clip_id)
    except (TypeError, ValueError):
        return False
    with adjust_render_lock:
        if normalized_id in active_adjust_render_ids:
            return False
        active_adjust_render_ids.add(normalized_id)
        return True


def _release_adjust_render(clip_id):
    try:
        normalized_id = int(clip_id)
    except (TypeError, ValueError):
        return
    with adjust_render_lock:
        active_adjust_render_ids.discard(normalized_id)


current_task = {
    "active": False,
    "cancel": False,
    "operation": "",
    "job_id": None,
    "started_at": None,
}


def check_current_task_cancel():
    if current_task.get("cancel"):
        raise OperationCancelled("Operação cancelada pelo usuário")


def _set_legacy_task(operation, active=True, job_id=None):
    current_task["active"] = active
    current_task["operation"] = operation if active else ""
    current_task["job_id"] = job_id if active else None
    if active:
        current_task["cancel"] = False
        current_task["started_at"] = datetime.now().isoformat(timespec="seconds")
    else:
        current_task["started_at"] = None


def emit_progress(message, level="info", job_id=None):
    effective_job_id = str(job_id or "").strip()
    if not effective_job_id and current_task.get("active") and current_task.get("job_id"):
        effective_job_id = str(current_task.get("job_id"))
    runtime_message = f"[Versão {PROGRAM_VERSION} · {PROGRAM_REVISION}] {str(message)}"
    socketio.emit(
        "progress",
        {
            "message": runtime_message,
            "level": level,
            "time": datetime.now().strftime("%H:%M:%S"),
            "job_id": effective_job_id or None,
            "program_version": PROGRAM_VERSION,
            "program_revision": PROGRAM_REVISION,
        },
    )


def _job_scoped_progress(job_id):
    def callback(message, level="info"):
        return emit_progress(message, level, job_id=job_id)
    return callback


def emit_status(status, data=None, job_id=None):
    payload = dict(data or {})
    if job_id:
        payload["job_id"] = str(job_id)
    payload.setdefault("program_version", PROGRAM_VERSION)
    payload.setdefault("program_revision", PROGRAM_REVISION)
    socketio.emit(
        "status",
        {
            "status": status,
            "data": payload,
            "job_id": str(job_id) if job_id else None,
            "program_version": PROGRAM_VERSION,
            "program_revision": PROGRAM_REVISION,
        },
    )


def _emit_job_update(job):
    if job:
        payload = {**job, "program_version": PROGRAM_VERSION, "program_revision": PROGRAM_REVISION}
        socketio.emit("job_update", payload)


job_manager = JobManager(DB_PATH, max_workers=1, on_event=_emit_job_update)
try:
    _recovered_jobs = job_manager.reconcile_stale()
    if _recovered_jobs:
        print(f"[Jobs] Recuperados {len(_recovered_jobs)} job(s) órfão(s) deixado(s) sem worker ativo.")
except Exception as _reconcile_error:
    print(f"[Jobs] Não foi possível reconciliar jobs antigos: {_reconcile_error}")


def _workspace_input_path(relative_path):
    try:
        return safe_workspace_path(WORKSPACE_DIR, relative_path, allow_missing=False)
    except (UnsafePathError, FileNotFoundError):
        return None


def _allowed_media_roots(settings=None):
    settings = settings or get_all_settings()
    roots = [WORKSPACE_DIR]
    for key in ("source_download_dir", "output_dir"):
        value = str(settings.get(key) or "").strip()
        if value:
            roots.append(os.path.abspath(os.path.expanduser(value)))
    return roots


def _configured_gemini_model(settings):
    """Return a safe Gemini model identifier from persisted settings."""
    model = str((settings or {}).get("gemini_model", "gemini-2.5-flash") or "").strip()
    return model if re.fullmatch(r"gemini-[a-z0-9.-]+", model) else "gemini-2.5-flash"


def _resolve_media_input(requested):
    """Resolve workspace-relative or explicitly configured external media."""
    value = str(requested or "").strip()
    if not value:
        return None
    if not os.path.isabs(value):
        return _workspace_input_path(value)
    target = os.path.abspath(os.path.expanduser(value))
    if not os.path.isfile(target):
        return None
    if os.path.splitext(target)[1].lower() not in ALLOWED_EXTENSIONS:
        return None
    settings = get_all_settings()
    if not any(_is_under(target, root) for root in _allowed_media_roots(settings)):
        return None
    return target


def _is_source_destination_placeholder(value):
    """Return True for UI placeholder text accidentally sent as a path."""
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    return normalized in {
        "a pasta sera escolhida ao importar",
        "a pasta sera escolhida ao baixar",
        "escolha uma pasta",
        "selecione uma pasta",
    }


def _resolve_source_destination(requested, settings=None):
    settings = settings or get_all_settings()
    requested_value = str(requested or "").strip()
    saved_value = str(settings.get("source_download_dir") or "").strip()
    if _is_source_destination_placeholder(requested_value):
        requested_value = ""
    if _is_source_destination_placeholder(saved_value):
        saved_value = ""
    value = requested_value or saved_value or UPLOAD_DIR
    target = os.path.abspath(os.path.expandvars(os.path.expanduser(value)))
    if os.path.isfile(target):
        raise OSError("O destino escolhido é um arquivo; selecione uma pasta para salvar o vídeo.")
    os.makedirs(target, exist_ok=True)
    return target


def _probe_video_duration_seconds(video_path):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", video_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        return float(result.stdout.strip()) if result.stdout.strip() else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _normalize_review_bounds(clip):
    """Expose canonical and active bounds without changing persisted clip columns."""
    def finite(value, fallback):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return float(fallback)
        return number if math.isfinite(number) else float(fallback)

    original_start = max(0.0, finite(clip.get("start_time"), 0.0))
    original_end = finite(clip.get("end_time"), original_start)
    if original_end <= original_start:
        original_end = original_start
    original = {
        "start": round(original_start, 3),
        "end": round(original_end, 3),
        "duration": round(max(0.0, original_end - original_start), 3),
    }
    active = dict(original)
    latest = clip.get("latest_adjustment")
    render_status = "canonical"
    if isinstance(latest, dict) and str(latest.get("render_status") or "").strip().lower() == "rendered":
        active_start = max(0.0, finite(latest.get("start"), original_start))
        active_end = finite(latest.get("end"), original_end)
        if active_end > active_start:
            active = {
                "start": round(active_start, 3),
                "end": round(active_end, 3),
                "duration": round(max(0.0, active_end - active_start), 3),
            }
            render_status = "rendered"

    clip["original_bounds"] = original
    clip["active_bounds"] = active
    clip["active_render_status"] = render_status
    clip["active_start"] = active["start"]
    clip["active_end"] = active["end"]
    clip["active_duration"] = active["duration"]
    # Review consumers use start/end for the file currently in the player.
    clip["start"] = active["start"]
    clip["end"] = active["end"]
    clip["duration"] = active["duration"]
    return clip


def _infer_adjustment_preserve_original_aspect(clip):
    """Prefer the source composition when a previous reframe cannot be replayed."""
    if not isinstance(clip, dict):
        return False
    framing = clip.get("framing") if isinstance(clip.get("framing"), dict) else None
    if framing is None:
        raw_factors = clip.get("score_factors")
        if isinstance(raw_factors, str):
            try:
                raw_factors = json.loads(raw_factors)
            except (TypeError, ValueError, json.JSONDecodeError):
                raw_factors = {}
        if isinstance(raw_factors, dict):
            metadata = raw_factors.get("_review_metadata")
            framing = metadata.get("framing") if isinstance(metadata, dict) else None
    if not isinstance(framing, dict):
        return False
    mode = str(framing.get("mode") or "").strip().lower()
    if mode in {"face_tracking", "reframe_9_16", "original", "original_16_9", "original_16:9"}:
        return True
    return _coerce_bool(framing.get("tracking_applied"), default=False)


def _selection_coverage_plan(source_video, video_duration):
    """Build a local-only plan for adaptive candidate coverage and deduplication."""
    fingerprints = get_existing_clip_fingerprints(source_video)
    try:
        span = max(0.0, float(video_duration or 0.0))
    except (TypeError, ValueError):
        span = 0.0
    max_clips = min(36, max(15, int(span // 240) + 6)) if span >= 120 else 15
    return {"previous_clip_fingerprints": fingerprints, "adaptive_max_clips": max_clips}


def _defer_context_incomplete_candidates(candidates):
    """Keep editorially unsafe candidates for review instead of rendering them ready.

    The ranker exposes the reasons, but rendering is the final publication-like
    boundary: a strong hook must not compensate for missing context or an
    explicit technical review requirement such as an unvalidated Q&A bridge.
    """
    renderable = []
    deferred = []
    for candidate in candidates or []:
        if not isinstance(candidate, dict):
            continue
        review_flags = candidate.get("review_flags") or {}
        technical_status = candidate.get("technical_gate_status") or review_flags.get("technical_gate_status")
        technical_reasons = candidate.get("technical_gate_reasons") or review_flags.get("technical_gate_reasons") or []
        context_incomplete = "context_complete" in candidate and not _coerce_bool(candidate.get("context_complete"), default=True)
        payoff_complete = _coerce_bool(candidate.get("payoff_complete"), default=True)
        technical_review = str(technical_status or "").strip().lower() in {"review", "review_required", "blocked"}

        if context_incomplete:
            reasons = []
            reasons.append("contexto autossuficiente não confirmado")
            if _coerce_bool(candidate.get("starts_mid_sentence")):
                reasons.append("início possivelmente no meio da frase")
            if _coerce_bool(candidate.get("starts_with_context_reference")):
                reasons.append("referência contextual sem antecedente recuperado")
            if technical_review:
                reasons.append("revisão técnica editorial obrigatória")
                reasons.extend(str(reason) for reason in technical_reasons if str(reason).strip())
            deferred.append({
                "start": candidate.get("start", candidate.get("start_time")),
                "end": candidate.get("end", candidate.get("end_time")),
                "duration": candidate.get("duration"),
                "reason": "; ".join(dict.fromkeys(reasons)),
                "errors": ["; ".join(dict.fromkeys(reasons))],
                "review_flags": review_flags,
            })
            continue

        if technical_review and not payoff_complete:
            reasons = ["revisão técnica editorial obrigatória", "payoff ou fechamento não confirmado"]
            reasons.extend(str(reason) for reason in technical_reasons if str(reason).strip())
            deferred.append({
                "start": candidate.get("start", candidate.get("start_time")),
                "end": candidate.get("end", candidate.get("end_time")),
                "duration": candidate.get("duration"),
                "reason": "; ".join(dict.fromkeys(reasons)),
                "errors": ["; ".join(dict.fromkeys(reasons))],
                "review_flags": review_flags,
            })
            continue

        if technical_review:
            candidate["post_render_review_required"] = True
            candidate["post_review_reasons"] = list(technical_reasons)

        renderable.append(candidate)
    return renderable, deferred


def _transcription_source_mode(settings):
    mode = str((settings or {}).get("transcription_source", "auto") or "auto").strip().lower()
    aliases = {"public_subtitles": "public_subtitle", "captions": "public_subtitle", "local_whisper": "whisper"}
    return aliases.get(mode, mode) if mode in {"auto", "public_subtitle", "public_subtitles", "captions", "whisper", "local_whisper"} else "auto"


def _transcribe_video_automatically(video_path, settings, emit_progress, transcript_fallback_path=None, cancel_check=None):
    """Use the explicit source preference, preserving Gemini-first behavior in auto mode."""
    mode = _transcription_source_mode(settings)
    if mode == "whisper":
        emit_progress("[Transcrição] Preferência: Whisper local forçado; Gemini e legenda pública serão ignorados.", "info")
    elif mode == "public_subtitle":
        emit_progress("[Transcrição] Preferência: legenda pública timestampada; Whisper será fallback se ela não existir.", "info")
    else:
        emit_progress("[Transcrição] Modo automático: Gemini multimodal online → legenda pública → Whisper CPU.", "info")
    if cancel_check:
        cancel_check()

    if mode == "auto" and transcript_fallback_path and os.path.isfile(transcript_fallback_path):
        emit_progress(
            "[Transcrição] Legenda pública timestampada já disponível; Gemini multimodal foi ignorado para evitar duplicidade e limite de tokens.",
            "info",
        )
    elif mode == "auto":
        gemini_kwargs = {"cancel_check": cancel_check} if cancel_check else {}
        multimodal = _run_gemini_video_analysis(video_path, settings, {}, "", emit_progress, **gemini_kwargs)
        transcription = _transcription_from_gemini_result(multimodal, settings.get("language", "pt"))
        if transcription:
            emit_progress("[Transcrição] Gemini forneceu timestamps; Whisper CPU não será iniciado.", "success")
            transcription["source"] = "gemini_video"
            return transcription

    if mode != "whisper" and transcript_fallback_path and os.path.isfile(transcript_fallback_path):
        try:
            with open(transcript_fallback_path, "r", encoding="utf-8-sig") as handle:
                transcription = parse_transcript_text(handle.read(), duration=None)
            transcription["source"] = "public_subtitles"
            emit_progress(
                f"[Transcrição] Legenda pública timestampada usada ({transcription.get('segment_count', len(transcription.get('segments', [])))} segmentos); Whisper CPU não será iniciado.",
                "success",
            )
            return transcription
        except Exception as exc:
            emit_progress(f"[Transcrição] Legenda pública não pôde ser interpretada: {str(exc)[:180]}", "warning")

    if mode == "public_subtitle":
        emit_progress("[Transcrição] Legenda pública não disponível ou inválida; iniciando fallback local faster-whisper.", "warning")
    elif mode == "whisper":
        emit_progress("[Transcrição] Iniciando faster-whisper por solicitação do usuário.", "info")
    else:
        emit_progress("[Transcrição] Gemini/legenda pública não entregaram timestamps; iniciando fallback local faster-whisper.", "warning")
    from modules.transcriber import Transcriber
    requested_model = settings.get("whisper_model", "small")
    requested_device = settings.get("whisper_device", "auto")
    duration = _probe_video_duration_seconds(video_path)
    threshold_minutes = float(settings.get("whisper_long_video_threshold_minutes", 45) or 45)
    long_model = str(settings.get("whisper_long_video_model", "base") or "base")
    probe = Transcriber(model_name=requested_model, device=requested_device)
    resolved_device = probe._detect_device()
    model_name = requested_model
    if (
        duration is not None
        and duration >= threshold_minutes * 60
        and resolved_device == "cpu"
        and str(requested_model).lower() == "small"
        and long_model
    ):
        model_name = long_model
        emit_progress(
            f"[Whisper] Vídeo longo ({duration / 60:.1f} min) em CPU; usando modelo {model_name} para descoberta rápida. "
            "O modelo Small continua disponível para refinamento posterior.",
            "warning",
        )
    emit_progress(
        f"[Whisper] Fallback local preparado; dispositivo candidato {resolved_device.upper()} com modelo {model_name}. "
        "A configuração final será confirmada ao carregar o motor.",
        "info",
    )
    transcriber = Transcriber(
        model_name=model_name,
        language=settings.get("language", "pt"),
        word_timestamps=settings.get("whisper_word_timestamps", True),
        beam_size=settings.get("whisper_beam_size", 5),
        device=resolved_device,
        condition_on_previous_text=settings.get("whisper_condition_on_previous_text", True),
        vad_min_silence_ms=settings.get("whisper_vad_min_silence_ms", 500),
        vad_speech_pad_ms=settings.get("whisper_vad_speech_pad_ms", 200),
        temperature=settings.get("whisper_temperature", 0.0),
        chunk_length=settings.get("whisper_chunk_length", 30),
    )
    transcriber.apply_preset(settings.get("whisper_preset", "default"))
    transcribe_kwargs = {"emit_progress": emit_progress}
    if cancel_check:
        transcribe_kwargs["cancel_check"] = cancel_check
    transcription = transcriber.transcribe(video_path, **transcribe_kwargs)
    transcription["source"] = "whisper"
    emit_progress(
        f"[Whisper] Motor: {transcriber._engine} em {transcriber.device}; "
        "timestamps por segmento gerados.",
        "success",
    )
    return transcription


def _save_transcription_artifacts(video_path, transcription):
    """Save human-readable Tactiq-style and machine-readable transcript files."""
    base, _ = os.path.splitext(video_path)
    txt_path = f"{base}.transcript.txt"
    json_path = f"{base}.transcript.json"
    with open(txt_path, "w", encoding="utf-8") as handle:
        for segment in transcription.get("segments", []):
            start = float(segment.get("start", 0))
            hours = int(start // 3600)
            minutes = int((start % 3600) // 60)
            seconds = start % 60
            handle.write(f"{hours:02d}:{minutes:02d}:{seconds:06.3f} {segment.get('text', '').strip()}\n")
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(transcription, handle, ensure_ascii=False, indent=2)
    return {"text": txt_path, "json": json_path}


def _max_finite_transcript_timestamp(items):
    values = []
    for item in items if isinstance(items, (list, tuple)) else []:
        if not isinstance(item, dict):
            continue
        try:
            value = float(item.get("end") if item.get("end") is not None else item.get("start", 0))
        except (TypeError, ValueError):
            continue
        if math.isfinite(value):
            values.append(value)
    return max(values, default=None)


def _transcription_from_request(data, duration=None):
    """Return a canonical transcription when the user supplied one."""
    text = data.get("transcript_text") or data.get("manual_transcript") or ""
    if isinstance(text, str) and text.strip():
        result = parse_transcript_text(text, duration=duration)
        raw_result = parse_transcript_text(text, duration=None)
        result["raw_last_timestamp"] = _max_finite_transcript_timestamp(raw_result.get("segments", []))
        result["language"] = data.get("transcript_language", "pt")
        result["source"] = "manual"
        return result
    segments = data.get("transcript_segments")
    if isinstance(segments, list) and segments:
        result = normalize_segment_payload(segments, duration=duration)
        result["raw_last_timestamp"] = _max_finite_transcript_timestamp(segments)
        result["language"] = data.get("transcript_language", "pt")
        result["source"] = "manual"
        return result
    return None


def _project_matches_video(project_id, video_path):
    """Only reuse a project transcript when its source identity matches the video."""
    if project_id in (None, "") or not video_path:
        return False
    try:
        project = get_project(int(project_id))
    except (TypeError, ValueError):
        return False
    if not project:
        return False
    stored_source = _resolve_media_input(project.get("source_video", ""))
    if stored_source and os.path.realpath(stored_source) == os.path.realpath(video_path):
        return True
    stored_signature = str(project.get("source_signature") or "").strip()
    current_signature = get_source_signature(video_path)
    return bool(stored_signature and current_signature and stored_signature == current_signature)


def _analyze_energy_with_cancel(analyzer, video_path, emit_progress, cancel_check=None):
    """Call audio analysis with cooperative cancellation while preserving test/plugin compatibility."""
    kwargs = {"emit_progress": emit_progress}
    if cancel_check is None:
        return analyzer.analyze_energy(video_path, **kwargs)
    try:
        return analyzer.analyze_energy(video_path, cancel_check=cancel_check, **kwargs)
    except TypeError as exc:
        if "cancel_check" not in str(exc):
            raise
        return analyzer.analyze_energy(video_path, **kwargs)


def _enrich_editorial_context_locally(video_path, transcription, editorial_context, settings, emit_progress, cancel_check=None):
    """Add local audio and hook evidence without uploading the source video."""
    from modules.audio_analyzer import AudioAnalyzer
    from modules.editorial_context import detect_hook_candidates
    from modules.campaign_hub import attach_acervo_context, merge_acervo_seed_candidates, load_snapshot, snapshot_status

    analyzer = AudioAnalyzer()
    energy_profile = _analyze_energy_with_cancel(analyzer, video_path, emit_progress, cancel_check)
    high_energy = analyzer.find_high_energy_moments(energy_profile, threshold=0.62, min_duration=2.0)
    snapshot = load_snapshot(settings.get("campaign_hub_snapshot_path"))
    hooks = detect_hook_candidates(
        (transcription or {}).get("segments", []),
        snapshot=snapshot,
        account=settings.get("campaign_hub_account", "@renansantosmbl"),
        energy_profile=energy_profile,
        limit=20,
    )
    enriched = dict(editorial_context or {})
    enriched["hook_candidates"] = hooks
    enriched["hook_count"] = len(hooks)
    enriched["local_audio"] = {
        "available": True,
        "window_seconds": 1.0,
        "window_count": len(energy_profile),
        "high_energy_moments": high_energy[:12],
        "source": "local_streaming_ffmpeg",
    }
    signals = dict(enriched.get("signals") or {})
    signals.update({
        "local_audio_available": True,
        "local_audio_window_count": len(energy_profile),
        "local_high_energy_count": len(high_energy),
    })
    enriched["signals"] = signals
    return enriched


def _transcription_coverage_report(transcription, duration):
    """Summarize temporal coverage without pretending to verify semantic identity."""
    try:
        video_duration = float(duration or 0)
    except (TypeError, ValueError):
        video_duration = 0.0
    segments = (transcription or {}).get("segments", []) if isinstance(transcription, dict) else []
    valid = []
    for segment in segments if isinstance(segments, list) else []:
        if not isinstance(segment, dict):
            continue
        try:
            start = float(segment.get("start", 0))
            end = float(segment.get("end", start))
        except (TypeError, ValueError):
            continue
        if start >= 0 and end > start:
            valid.append((start, end))
    first = min((item[0] for item in valid), default=None)
    last = max((item[1] for item in valid), default=None)
    raw_last = (transcription or {}).get("raw_last_timestamp") if isinstance(transcription, dict) else None
    try:
        raw_last = float(raw_last) if raw_last is not None else None
    except (TypeError, ValueError):
        raw_last = None
    out_of_bounds = bool(video_duration and ((raw_last is not None and raw_last > video_duration * 1.05) or any(end > video_duration * 1.05 for _, end in valid)))
    end_ratio = round(min(1.0, last / video_duration), 3) if video_duration and last is not None else None
    first_ratio = round(min(1.0, max(0.0, first / video_duration)), 3) if video_duration and first is not None else None
    span_ratio = round(min(1.0, max(0.0, (last - first) / video_duration)), 3) if video_duration and first is not None and last is not None else None
    coverage_is_narrow = bool(
        video_duration
        and (
            (first_ratio is not None and first_ratio > 0.20)
            or (span_ratio is not None and span_ratio < 0.55)
        )
    )
    if not valid:
        status = "empty"
    elif out_of_bounds:
        status = "mismatch_suspected"
    elif video_duration and last is not None and (end_ratio < 0.35 or coverage_is_narrow):
        status = "partial"
    else:
        status = "covered"
    return {
        "status": status,
        "video_duration_seconds": round(video_duration, 3) if video_duration else None,
        "first_timestamp": round(first, 3) if first is not None else None,
        "last_timestamp": round(last, 3) if last is not None else None,
        "end_ratio": end_ratio,
        "first_ratio": first_ratio,
        "span_ratio": span_ratio,
        "segment_count": len(valid),
        "semantic_identity_verified": False,
    }


def _review_provenance(transcription=None, editorial_context=None, context_source=None):
    """Return bounded origin metadata safe for clip review and local persistence."""
    source = str((transcription or {}).get("source", "unknown") or "unknown").strip().lower()
    if "subtitle" in source:
        transcript_source = "public_subtitle"
    elif "gemini" in source:
        transcript_source = "gemini_video"
    elif "whisper" in source:
        transcript_source = "whisper"
    elif source in {"manual", "manual_confirmed"}:
        transcript_source = "manual"
    elif source in {"automatic", "unknown"}:
        transcript_source = source
    else:
        transcript_source = "unknown"
    coverage = (transcription or {}).get("coverage", {}) if isinstance(transcription, dict) else {}
    coverage_status = str(coverage.get("status", "unknown") or "unknown").strip()
    if coverage_status not in {"covered", "partial", "mismatch_suspected", "empty", "unknown"}:
        coverage_status = "unknown"
    selected_context_source = str(context_source or ("local_dossier" if isinstance(editorial_context, dict) else "none"))
    if selected_context_source not in {"local_dossier", "multimodal_auxiliary", "none"}:
        selected_context_source = "none"
    try:
        transcript_end_ratio = float(coverage.get("end_ratio"))
    except (TypeError, ValueError):
        transcript_end_ratio = None
    return {
        "transcript_source": transcript_source,
        "transcript_coverage_status": coverage_status,
        "transcript_archive_present": bool(
            isinstance(transcription, dict)
            and (transcription.get("archive") or transcription.get("archive_metadata") or transcription.get("quality"))
        ),
        "transcript_semantic_identity_verified": _coerce_bool(coverage.get("semantic_identity_verified"), default=False),
        "transcript_end_ratio": (
            round(max(0.0, min(1.0, transcript_end_ratio)), 3)
            if transcript_end_ratio is not None
            else None
        ),
        "context_source": selected_context_source,
    }


def _score_factors_with_dedup_context(clip):
    """Persist only bounded non-textual signals needed for cross-run dedupe."""
    factors = dict(clip.get("factors") or {}) if isinstance(clip, dict) else {}
    if not isinstance(clip, dict):
        return factors
    dedup_context = {}
    review_flags = clip.get("review_flags") if isinstance(clip.get("review_flags"), dict) else {}
    for key in (
        "question_answer_complete",
        "payoff_complete",
        "qa_bridge",
        "closure_type",
        "political_editorial_type",
        "chapter_primary_id",
    ):
        value = clip.get(key)
        if value in (None, ""):
            value = review_flags.get(key)
        if value not in (None, ""):
            dedup_context[key] = value
    if dedup_context:
        factors["_dedup_context"] = dedup_context
    return factors


def _run_gemini_video_analysis(video_path, settings, editorial_context, user_context, emit_progress, cancel_check=None):
    backend = str(settings.get("ai_backend", "gemini") or "gemini").lower()
    api_key = str(settings.get("gemini_api_key", "") or "").strip()
    model = _configured_gemini_model(settings)
    if backend not in {"auto", "gemini"}:
        emit_progress(f"[Gemini] Backend definido como {backend}; Gemini online não será usado nesta execução.", "info")
        return None
    if not api_key:
        emit_progress("[Gemini] Nenhuma API key configurada; não é possível usar Gemini online. Configure-a em Backend de IA; fallback local ativado.", "warning")
        return None
    try:
        from modules.gemini_video import analyze_video_with_gemini
        enriched_context = {
            **(editorial_context if isinstance(editorial_context, dict) else {}),
            "source_file_name": os.path.basename(video_path),
            "multimodal_expected_focus": (editorial_context or {}).get("focus", "participante principal / contexto político") if isinstance(editorial_context, dict) else "participante principal / contexto político",
        }
        result = analyze_video_with_gemini(
            video_path,
            api_key,
            editorial_context=enriched_context,
            user_context=user_context,
            emit_progress=emit_progress,
            cancel_check=cancel_check,
            model=model,
        )
        emit_progress("[Gemini] Análise multimodal concluída; sinais de áudio, imagem e entrevista incorporados.", "success")
        return result
    except OperationCancelled:
        raise
    except Exception as exc:
        detail = str(exc)[:220]
        if "503" in detail or "high demand" in detail.lower():
            emit_progress(
                "[Gemini] Serviço temporariamente sobrecarregado (HTTP 503). A chave e o vídeo foram aceitos; seguindo para legenda pública/Whisper local sem reenviar o arquivo.",
                "warning",
            )
        else:
            emit_progress(f"[Gemini] Análise multimodal não concluída; seguindo com sinais locais: {detail}", "warning")
        return None


def _transcription_from_gemini_result(result, language="pt"):
    if not isinstance(result, dict) or not isinstance(result.get("transcript_segments"), list):
        return None
    segments = []
    for item in result["transcript_segments"]:
        if not isinstance(item, dict) or not item.get("text"):
            continue
        try:
            start = parse_timestamp(str(item.get("start", "0:00"))) if isinstance(item.get("start"), str) else float(item.get("start", 0))
            end_value = item.get("end")
            end = parse_timestamp(str(end_value)) if isinstance(end_value, str) else (float(end_value) if end_value is not None else start + 2)
        except (TypeError, ValueError):
            continue
        segments.append({
            "start": start,
            "end": end,
            "text": str(item["text"]),
            "speaker": item.get("speaker", "desconhecido"),
        })
    if not segments:
        return None
    result = normalize_segment_payload(segments)
    result["language"] = language
    result["source"] = "gemini_video"
    return result


def _timestamp_value(value):
    if isinstance(value, (int, float)):
        candidate = float(value)
    else:
        try:
            candidate = parse_timestamp(str(value or "0:00"))
        except (TypeError, ValueError):
            return None
    return candidate if candidate is not None and math.isfinite(candidate) else None


def _coerce_visual_flag(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value or "").strip().lower() in {"1", "true", "yes", "sim", "on"}


def _attach_multimodal_nonverbal_moments(clips, multimodal):
    """Attach one conservative overlapping nonverbal observation per clip."""
    if not isinstance(multimodal, dict):
        return clips
    identity_status = str(multimodal.get("source_identity_status", "unverified") or "unverified").strip().lower()
    try:
        identity_confidence = float(multimodal.get("source_identity_confidence", 0) or 0)
    except (TypeError, ValueError):
        identity_confidence = 0.0
    if not math.isfinite(identity_confidence):
        identity_confidence = 0.0
    max_confidence = 1.0 if identity_status == "validated" and identity_confidence >= 0.65 else 0.35
    moments = multimodal.get("nonverbal_moments")
    allowed_kinds = {
        "risada", "reacao", "gesto", "objeto", "animal", "montaria", "cavalgada",
        "berrante", "musica", "paisagem", "interacao", "silencio_expressivo",
        "acao_visual", "outro",
    }
    if not isinstance(moments, list) or identity_status == "mismatch":
        return clips
    for clip in clips or []:
        try:
            clip_start = float(clip.get("start", 0))
            clip_end = float(clip.get("end", clip_start))
        except (TypeError, ValueError):
            continue
        ranked = []
        for moment in moments:
            if not isinstance(moment, dict):
                continue
            start = _timestamp_value(moment.get("start"))
            end = _timestamp_value(moment.get("end"))
            kind = str(moment.get("kind") or "").strip().lower()
            description = str(moment.get("description") or "").strip()
            if start is None or end is None or end <= start or kind not in allowed_kinds or not description:
                continue
            overlap = max(0.0, min(clip_end, end) - max(clip_start, start))
            if overlap <= 0:
                continue
            try:
                confidence = float(moment.get("confidence", 0) or 0)
            except (TypeError, ValueError):
                confidence = 0.0
            if not math.isfinite(confidence):
                confidence = 0.0
            confidence = max(0.0, min(max_confidence, confidence))
            ranked.append((overlap * max(confidence, 0.25), overlap, moment))
        if not ranked:
            continue
        _, _, moment = max(ranked, key=lambda item: (item[0], item[1]))
        moment_start = _timestamp_value(moment.get("start"))
        moment_end = _timestamp_value(moment.get("end"))
        description = str(moment.get("description") or "").strip()
        editorial_value = str(moment.get("editorial_value") or "").strip()
        kind = str(moment.get("kind") or "outro").strip().lower()
        if description:
            clip["nonverbal_moment"] = description[:400]
        if editorial_value:
            clip["nonverbal_editorial_value"] = editorial_value[:400]
        clip["nonverbal_moment_kind"] = kind[:40]
        clip["nonverbal_moment_start"] = moment_start
        clip["nonverbal_moment_end"] = moment_end
        try:
            moment_confidence = float(moment.get("confidence", 0) or 0)
        except (TypeError, ValueError):
            moment_confidence = 0.0
        clip["nonverbal_moment_confidence"] = (
            max(0.0, min(max_confidence, moment_confidence))
            if math.isfinite(moment_confidence) else 0.0
        )
        requires_review = (
            _coerce_visual_flag(moment.get("requires_visual_review"))
            if "requires_visual_review" in moment else True
        )
        clip["nonverbal_moment_review_required"] = (
            requires_review
            or identity_status != "validated"
            or clip["nonverbal_moment_confidence"] < 0.75
        )
        if clip["nonverbal_moment_review_required"]:
            clip["nonverbal_moment_review_reason"] = (
                "momento não verbal é evidência auxiliar; confirme imagem, áudio e contexto antes de aprovar"
            )
    return clips


def _attach_multimodal_visual_observations(clips, multimodal):
    """Attach the strongest overlapping Gemini visual observation to each clip."""
    if not isinstance(multimodal, dict):
        return clips
    _attach_multimodal_nonverbal_moments(clips, multimodal)
    identity_status = str(multimodal.get("source_identity_status", "unverified") or "unverified").strip().lower()
    try:
        identity_confidence = max(0.0, min(1.0, float(multimodal.get("source_identity_confidence", 0) or 0)))
    except (TypeError, ValueError):
        identity_confidence = 0.0
    max_visual_confidence = 1.0 if identity_status == "validated" and identity_confidence >= 0.65 else 0.35
    observations = multimodal.get("visual_observations")
    if not isinstance(observations, list):
        observations = []
    for clip in clips or []:
        clip["multimodal_identity_status"] = identity_status
        clip["multimodal_identity_confidence"] = identity_confidence
        if identity_status == "mismatch":
            clip["visual_observation_review_required"] = True
            clip["visual_observation_review_reason"] = "observações visuais recusadas: fonte multimodal incompatível"
            continue
        try:
            clip_start = float(clip.get("start", 0))
            clip_end = float(clip.get("end", clip_start))
        except (TypeError, ValueError):
            continue
        ranked = []
        for observation in observations:
            if not isinstance(observation, dict):
                continue
            start = _timestamp_value(observation.get("start"))
            end = _timestamp_value(observation.get("end"))
            if start is None or end is None or end <= start:
                continue
            overlap = max(0.0, min(clip_end, end) - max(clip_start, start))
            if overlap <= 0:
                continue
            try:
                confidence = max(0.0, min(max_visual_confidence, float(observation.get("confidence", 0) or 0)))
            except (TypeError, ValueError):
                confidence = 0.0
            ranked.append((overlap * max(confidence, 0.25), overlap, observation))
        if not ranked:
            continue
        _, _, observation = max(ranked, key=lambda item: (item[0], item[1]))
        if "visual_format" in observation:
            clip["visual_format"] = str(observation.get("visual_format") or "desconhecido").strip()[:40]
        visual_flag_aliases = {
            "text_panel": ("text_panel", "has_text_panel"),
            "fake_tweet": ("fake_tweet",),
            "social_post": ("social_post",),
            "visual_meme": ("visual_meme",),
            "split_screen": ("split_screen",),
            "external_evidence": ("external_evidence",),
        }
        for key, aliases in visual_flag_aliases.items():
            for alias in aliases:
                if alias in observation:
                    clip[key] = _coerce_visual_flag(observation.get(alias))
                    break
        if observation.get("composition_note"):
            clip["visual_observation"] = str(observation["composition_note"])[:400]
        if observation.get("confidence") is not None:
            clip["visual_observation_confidence"] = min(max_visual_confidence, float(observation.get("confidence") or 0))
        if identity_status != "validated":
            clip["visual_observation_review_required"] = True
            clip["visual_observation_review_reason"] = "identidade da fonte multimodal não validada"

    return clips


def _should_allow_followup_video_analysis(transcription, settings):
    """Return whether an explicit second multimodal pass is allowed.

    Manual, public-caption and Whisper transcripts already provide the canonical
    timeline. A second upload is therefore opt-in, otherwise a long Gemini poll
    can make a finished transcription look like a frozen job.
    """
    source = str((transcription or {}).get("source", "") or "").strip().lower()
    settings = settings or {}
    if source in {"manual", "manual_confirmed"}:
        return _coerce_bool(settings.get("gemini_manual_video_analysis"), default=False)
    return _coerce_bool(settings.get("gemini_video_analysis_with_transcript"), default=False)


def _should_request_editorial_context_multimodal(transcription, analyze_video, multimodal_result, settings):
    """Decide whether the context worker may start a second video upload.

    The worker can receive a canonical transcript before it reaches the context
    stage. In that case, ``analyze_video=True`` means that visual/audio review is
    desirable, not that the same source must be uploaded again. The advanced
    settings remain the explicit opt-in for that second pass.
    """
    if multimodal_result is not None or not analyze_video:
        return False
    return _should_allow_followup_video_analysis(transcription, settings)


def _enrich_editorial_context(video_path, settings, editorial_context, user_context, emit_progress, multimodal=None, allow_video_analysis=True):
    """Use Gemini multimodal analysis as optional enrichment, never as a hard dependency."""
    if multimodal is None and allow_video_analysis:
        multimodal = _run_gemini_video_analysis(video_path, settings, editorial_context, user_context, emit_progress)
    if multimodal:
        return {**editorial_context, "multimodal": multimodal}
    if not allow_video_analysis:
        emit_progress("[Gemini] Transcrição manual fornecida; análise multimodal adicional não será reenviada. Usando sinais locais.", "info")
    else:
        emit_progress("[Gemini] Análise multimodal indisponível; usando transcrição e sinais locais.", "info")
    return editorial_context


@app.route("/api/jobs", methods=["GET"])
def api_list_jobs():
    try:
        limit = min(max(int(request.args.get("limit", 50)), 1), 200)
    except (TypeError, ValueError):
        limit = 50
    return jsonify({"jobs": job_manager.list(limit=limit)})


@app.route("/api/process/status", methods=["GET"])
def api_process_status():
    """Expose only the current legacy operation for frontend recovery."""
    return jsonify({
        "active": bool(current_task.get("active")),
        "operation": str(current_task.get("operation") or ""),
        "job_id": current_task.get("job_id"),
        "started_at": current_task.get("started_at"),
        "program_version": PROGRAM_VERSION,
        "program_revision": PROGRAM_REVISION,
    })


@app.route("/api/jobs/<job_id>", methods=["GET"])
def api_get_job(job_id):
    job = job_manager.get(job_id)
    if not job:
        return jsonify({"error": "Job não encontrado"}), 404
    rendered_count = 0
    render_rejection_count = 0
    try:
        for artifact in job.get("artifacts") or []:
            if not isinstance(artifact, dict):
                continue
            if artifact.get("type") == "candidate_diagnostics":
                rendered_count = int(artifact.get("rendered_count") or 0)
                render_rejection_count = int(artifact.get("render_rejection_count") or 0)
    except (TypeError, ValueError):
        rendered_count = 0
        render_rejection_count = 0
    job.setdefault("rendered_count", rendered_count)
    job.setdefault("failed_render_count", render_rejection_count)
    total_candidates = job.get("candidate_count") or job.get("total_candidates") or 0
    rendered_count = job.get("rendered_count", rendered_count)
    # Derive total_candidates from artifacts if not persisted in the job row.
    if not total_candidates:
        for artifact in job.get("artifacts") or []:
            if not isinstance(artifact, dict):
                continue
            if artifact.get("type") == "candidate_diagnostics":
                total_candidates = (
                    artifact.get("pre_render_candidate_count")
                    or artifact.get("expected_count")
                    or artifact.get("final_count")
                    or artifact.get("primary_count")
                    or 0
                )
                break
    discard_rate = max(0.0, (total_candidates - rendered_count) / total_candidates) if total_candidates > 0 else 0.0
    job["discard_rate"] = round(discard_rate, 3)
    job.setdefault("review_required_count", job.get("review_required_count", 0))
    return jsonify(job)


@app.route("/api/jobs/<job_id>/cancel", methods=["POST"])
def api_cancel_job(job_id):
    try:
        return jsonify(job_manager.request_cancel(job_id))
    except KeyError:
        return jsonify({"error": "Job não encontrado"}), 404


@app.route("/api/render-presets", methods=["GET"])
def api_render_presets():
    return jsonify({"presets": list_presets()})


@app.route("/api/batch/scan", methods=["POST"])
def api_batch_scan():
    data = request.get_json(silent=True) or {}
    relative_root = data.get("path", "uploads")
    try:
        root = safe_workspace_path(WORKSPACE_DIR, relative_root, allow_missing=False)
    except (UnsafePathError, FileNotFoundError):
        return jsonify({"error": "Pasta de lote inválida"}), 403
    if not os.path.isdir(root):
        return jsonify({"error": "Pasta de lote não encontrada"}), 404
    manifest = build_manifest(root, ALLOWED_EXTENSIONS)
    manifest["relative_root"] = os.path.relpath(root, WORKSPACE_DIR)
    return jsonify(manifest)


@app.route("/api/batch/rank", methods=["POST"])
def api_batch_rank():
    """Rank and select a quality-gated portfolio and persist a bounded A/B run."""
    data = request.get_json(silent=True) or {}
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        return jsonify({"error": "Envie uma lista candidates"}), 400
    if len(candidates) > 2000:
        return jsonify({"error": "Limite de 2000 candidatos por requisição"}), 413
    if not all(isinstance(candidate, dict) for candidate in candidates):
        return jsonify({"error": "Cada candidato deve ser um objeto JSON"}), 400

    from modules.viral_ranker import ViralRanker
    from modules.campaign_hub import load_snapshot
    from modules.ab_exporter import ALLOWED_MODES, export_run_candidates

    options = data.get("options") or {}
    requested_mode = str(options.get("favorability_mode", "off") or "off").strip().lower()
    favorability_mode = requested_mode if requested_mode in ALLOWED_MODES else "off"
    campaign_hub_snapshot = load_snapshot(options.get("campaign_hub_snapshot_path"))
    campaign_hub_account = str(
        options.get("campaign_hub_account")
        or data.get("campaign_hub_account")
        or (campaign_hub_snapshot or {}).get("default_account", "")
    )
    feedback_calibration = get_feedback_calibration()
    ranker = ViralRanker(
        channel_context=str(data.get("channel_context") or ""),
        editorial_profile=str(data.get("editorial_profile") or "renan_santos_politics"),
        feedback_calibration=feedback_calibration,
        campaign_hub_snapshot=campaign_hub_snapshot,
        campaign_hub_account=campaign_hub_account,
    )
    try:
        portfolio = ranker.rank_daily_portfolio(
            candidates,
            user_context=str(data.get("user_context") or ""),
            min_score=float(options.get("min_score", 62)),
            target_min=int(options.get("target_min", 39)),
            max_clips=min(50, int(options.get("max_clips", 50))),
            max_per_source=max(1, int(options.get("max_per_source", 8))),
            max_per_family=max(1, int(options.get("max_per_family", 14))),
            favorability_mode=favorability_mode,
            favorability_min=float(options.get("favorability_min", 60) or 60),
        )
    except (TypeError, ValueError) as exc:
        return jsonify({"error": f"Parâmetros de ranking inválidos: {exc}"}), 400

    run_id = str(options.get("run_id") or data.get("run_id") or f"run_{uuid.uuid4().hex[:16]}")
    seeds_enabled = _coerce_bool(
        options.get("seeds_enabled"),
        default=bool(campaign_hub_snapshot) or any(bool(item.get("context_seed_only") or item.get("from_acervo_seed")) for item in candidates),
    )
    ai_backend = str(options.get("ai_backend") or data.get("ai_backend") or get_all_settings().get("ai_backend") or "unknown")
    source_id = str(data.get("source_id") or options.get("source_id") or "batch")
    try:
        run_export = export_run_candidates(
            run_id=run_id,
            source_id=source_id,
            favorability_mode=favorability_mode,
            ai_backend=ai_backend,
            seeds_enabled=seeds_enabled,
            candidates=portfolio.get("clips", []),
        )
    except (OSError, TypeError, ValueError) as exc:
        return jsonify({"error": f"Não foi possível exportar o run A/B: {str(exc)[:240]}"}), 500
    portfolio["run"] = {
        "run_id": run_export["run_id"],
        "source_id": source_id[:128],
        "favorability_mode": favorability_mode,
        "ai_backend": ai_backend[:32].lower(),
        "seeds_enabled": seeds_enabled,
        "candidates_n": run_export["candidates_n"],
        "export": run_export,
        "warning": "modo inválido recebeu fallback off" if requested_mode != favorability_mode else "",
    }
    portfolio["run_id"] = run_export["run_id"]
    portfolio["favorability_mode"] = favorability_mode
    portfolio["seeds_enabled"] = seeds_enabled
    if isinstance(portfolio.get("summary"), dict):
        portfolio["summary"].update({
            "run_id": run_export["run_id"],
            "favorability_mode": favorability_mode,
            "seeds_enabled": seeds_enabled,
        })
    return jsonify(portfolio)


@app.route("/api/editorial/runs/export", methods=["POST"])
def api_editorial_run_export():
    """Explicitly export a bounded candidate list for a human A/B run."""
    data = request.get_json(silent=True) or {}
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not all(isinstance(item, dict) for item in candidates):
        return jsonify({"ok": False, "error": "candidates deve ser uma lista de objetos"}), 400
    from modules.ab_exporter import export_run_candidates
    try:
        result = export_run_candidates(
            run_id=data.get("run_id") or f"run_{uuid.uuid4().hex[:16]}",
            source_id=data.get("source_id") or "manual",
            favorability_mode=data.get("favorability_mode", "off"),
            ai_backend=data.get("ai_backend", "unknown"),
            seeds_enabled=data.get("seeds_enabled", False),
            candidates=candidates,
            generated_at=data.get("generated_at"),
        )
    except (OSError, TypeError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)[:300]}), 400
    return jsonify({"ok": True, **result})


@app.route("/api/editorial/runs/<run_id>/export", methods=["GET"])
def api_editorial_run_export_get(run_id):
    """Read a previously exported JSON or CSV A/B run from persistent storage."""
    from modules.ab_exporter import DEFAULT_AB_RUN_DIR, load_run_export
    payload = load_run_export(run_id)
    if not payload:
        return jsonify({"ok": False, "error": "Run A/B não encontrado"}), 404
    requested_format = str(request.args.get("format", "json") or "json").lower()
    if requested_format == "json":
        return jsonify(payload)
    if requested_format != "csv":
        return jsonify({"ok": False, "error": "format deve ser json ou csv"}), 400
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(run_id)).strip("._-")[:100]
    csv_path = DEFAULT_AB_RUN_DIR / f"{safe_id}.csv"
    if not csv_path.is_file():
        return jsonify({"ok": False, "error": "CSV do run não encontrado"}), 404
    return send_file(csv_path, mimetype="text/csv", as_attachment=True, download_name=f"{safe_id}.csv")


@app.route("/api/clips/<int:clip_id>/feedback", methods=["GET", "POST"])
def api_clip_feedback(clip_id):
    if request.method == "GET":
        return jsonify({"feedback": get_clip_feedback(clip_id)})
    data = request.get_json(silent=True) or {}
    action = data.get("action", "")
    try:
        save_clip_feedback(
            clip_id,
            action,
            adjustments=data.get("adjustments") or {},
            note=data.get("note", ""),
            reason_code=data.get("reason_code", ""),
            quality_tags=data.get("quality_tags") or [],
        )
        return jsonify({
            "success": True,
            "clip_id": clip_id,
            "review_status": action,
            "reason_code": str(data.get("reason_code", "") or "")[:48],
            "quality_tags": list(data.get("quality_tags") or [])[:12],
            "calibration": get_feedback_calibration(),
        })
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/clips/adjust", methods=["POST"])
def api_adjust_clip_bounds():
    """Preview safe clip boundary changes without mutating media or database."""
    data = request.get_json(silent=True) or {}
    clip = data.get("clip")
    if not isinstance(clip, dict):
        return jsonify({"error": "Informe um clip válido."}), 400
    try:
        adjusted = adjust_clip_bounds(
            clip,
            start=data.get("start"),
            end=data.get("end"),
            transcript_segments=data.get("transcript_segments"),
            duration=data.get("duration"),
            snap_tolerance=data.get("snap_tolerance", 2.0),
            min_duration=data.get("min_duration", 3.0),
        )
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"success": True, "clip": adjusted, "mutated": False})


@app.route("/api/clips/<int:clip_id>/adjust", methods=["POST"])
def api_persist_clip_adjustment(clip_id):
    """Persist a validated temporal draft without changing the rendered file."""
    data = request.get_json(silent=True) or {}
    clip = get_clip(clip_id)
    if not clip:
        return jsonify({"error": "Clip não encontrado."}), 404
    adjustment = data.get("adjustment") or data.get("clip") or {}
    if not isinstance(adjustment, dict):
        return jsonify({"error": "Informe um ajuste válido."}), 400
    try:
        normalized = adjust_clip_bounds(
            {
                "start": clip.get("start_time", 0),
                "end": clip.get("end_time", 0),
                "duration": clip.get("duration", 0),
            },
            start=adjustment.get("start"),
            end=adjustment.get("end"),
            transcript_segments=data.get("transcript_segments") or [],
            duration=data.get("source_duration"),
            snap_tolerance=data.get("snap_tolerance", 2.0),
            min_duration=data.get("min_duration", 3.0),
        )
        normalized["original_start"] = float(clip.get("start_time", 0) or 0)
        normalized["original_end"] = float(clip.get("end_time", 0) or 0)
        normalized["render_status"] = "preview_only"
        persisted = save_clip_adjustment(
            clip_id,
            normalized,
            note=str(data.get("note", "") or "").strip(),
        )
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({
        "success": True,
        "clip_id": clip_id,
        "review_status": "needs_review",
        "adjustment": persisted,
        "original": {
            "start": float(clip.get("start_time", 0) or 0),
            "end": float(clip.get("end_time", 0) or 0),
            "duration": float(clip.get("duration", 0) or 0),
        },
        "render_status": "preview_only",
    })


@app.route("/api/clips/<int:clip_id>/adjust/render", methods=["POST"])
def api_render_adjusted_clip(clip_id):
    """Render one validated temporal adjustment from the persisted source video."""
    from modules.video_cutter import VideoCutter

    data = request.get_json(silent=True) or {}
    clip = get_clip(clip_id)
    if not clip:
        return jsonify({"error": "Clip não encontrado."}), 404
    project = get_project(clip.get("project_id"))
    if not project:
        return jsonify({"error": "Projeto do clip não encontrado."}), 404
    source_path = _resolve_media_input(project.get("source_video"))
    if not source_path:
        return jsonify({"error": "A fonte original deste clip não está disponível no workspace permitido."}), 404

    adjustment = data.get("adjustment") or data.get("clip") or {}
    if not isinstance(adjustment, dict):
        return jsonify({"error": "Informe um ajuste válido."}), 400

    source_duration = data.get("source_duration")
    if source_duration in (None, ""):
        try:
            probe = VideoCutter().get_video_info(source_path)
            source_duration = (probe.get("format") or {}).get("duration")
        except Exception:
            source_duration = None
    try:
        normalized = adjust_clip_bounds(
            {
                "start": clip.get("start_time", 0),
                "end": clip.get("end_time", 0),
                "duration": clip.get("duration", 0),
                "title": str(data.get("title") or "").strip(),
                "text": str(data.get("text") or "").strip(),
            },
            start=adjustment.get("start"),
            end=adjustment.get("end"),
            transcript_segments=data.get("transcript_segments") or [],
            duration=source_duration,
            snap_tolerance=data.get("snap_tolerance", 2.0),
            min_duration=data.get("min_duration", 3.0),
        )
        normalized["original_start"] = float(clip.get("start_time", 0) or 0)
        normalized["original_end"] = float(clip.get("end_time", 0) or 0)
        normalized["render_status"] = "rendering"

        settings = get_all_settings()
        requested_preset = str(
            data.get("render_preset") or settings.get("render_preset") or "shorts"
        ).strip().lower()
        try:
            active_preset = get_preset(requested_preset)
        except ValueError:
            requested_preset = "shorts"
            active_preset = get_preset(requested_preset)
        preserve_original = _coerce_bool(
            data.get("preserve_original_aspect"),
            default=_infer_adjustment_preserve_original_aspect(clip),
        )
        project_name = str(project.get("name") or f"projeto-{project.get('id', clip_id)}")
        title = str(data.get("title") or clip.get("file_path") or f"clip-{clip_id}").strip()
        normalized["title"] = title
        normalized["text"] = str(data.get("text") or clip.get("transcript") or "").strip()
        if not _claim_adjust_render(clip_id):
            return jsonify({"error": "Este clip já está sendo renderizado. Aguarde a conclusão antes de iniciar outro ajuste."}), 409
        note = str(data.get("note") or "Ajuste temporal renderizado na bancada editorial.").strip()

        def task(ctx):
            from modules.video_cutter import VideoCutter

            progress_value = 10
            rendered = None
            persisted = False

            def emit_progress(message, level="info"):
                nonlocal progress_value
                progress_value = min(88, progress_value + 8)
                text = str(message)
                ctx.check_cancel()
                ctx.update(stage="adjust_render", progress=progress_value, message=text)
                socketio.emit(
                    "progress",
                    {
                        "message": f"[Versão {PROGRAM_VERSION} · {PROGRAM_REVISION}] {text}",
                        "level": level,
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "job_id": ctx.job_id,
                        "program_version": PROGRAM_VERSION,
                        "program_revision": PROGRAM_REVISION,
                    },
                )

            try:
                ctx.update(
                    stage="adjust_render",
                    progress=5,
                    message="Preparando re-renderização do ajuste",
                    artifacts=[{"type": "adjustment_render_pending", "clip_id": clip_id}],
                )
                ctx.check_cancel()
                cutter = VideoCutter(
                    method="intelligent",
                    target_duration=normalized["duration"],
                    preset=active_preset,
                )
                results = cutter.batch_cut(
                    source_path,
                    [normalized],
                    f"{project_name}-ajustes",
                    use_face_tracking=False,
                    emit_progress=emit_progress,
                    output_dir=EXPORT_DIR,
                    video_layout=None,
                    preset=active_preset,
                    original_aspect_indices={0} if preserve_original else set(),
                    source_duration=source_duration,
                    cancel_check=ctx.check_cancel,
                )
                ctx.check_cancel()
                if not results:
                    rejection = cutter.last_rejections[0] if cutter.last_rejections else {}
                    errors = "; ".join(rejection.get("errors") or []) or "o renderizador não produziu um arquivo válido"
                    raise RuntimeError(f"Não foi possível renderizar o ajuste: {errors[:300]}")
                rendered = results[0]
                ctx.update(stage="persisting_adjustment", progress=92, message="Salvando o MP4 ajustado e os limites editoriais")
                ctx.check_cancel()
                persisted_data = dict(normalized)
                persisted_data.update({
                    "render_status": "rendered",
                    "render_path": rendered.get("path"),
                    "render_start": rendered.get("render_start"),
                    "render_end": rendered.get("render_end"),
                    "render_duration": rendered.get("render_duration"),
                    "render_boundary_policy": rendered.get("render_boundary_policy", ""),
                    "preset": rendered.get("preset", requested_preset),
                })
                persisted_payload = save_clip_adjustment(clip_id, persisted_data, note=note)
                update_clip_rendered_file(clip_id, rendered["path"])
                persisted = True
                socketio.emit("clip_adjust_render_complete", {
                    "job_id": ctx.job_id,
                    "clip_id": clip_id,
                    "review_status": "needs_review",
                    "adjustment": persisted_payload,
                    "render": rendered,
                    "render_status": "rendered",
                    "source": {"path": source_path, "duration": source_duration},
                })
                return {
                    "artifacts": [{
                        "type": "adjusted_clip",
                        "clip_id": clip_id,
                        "path": rendered.get("path"),
                        "render_duration": rendered.get("render_duration"),
                    }],
                }
            except Exception:
                if rendered and not persisted:
                    try:
                        render_path = rendered.get("path")
                        if render_path and os.path.exists(render_path):
                            os.remove(render_path)
                    except OSError:
                        pass
                raise
            finally:
                _release_adjust_render(clip_id)

        try:
            job = job_manager.submit("adjust_clip_render", task, project_id=clip.get("project_id"))
        except Exception:
            _release_adjust_render(clip_id)
            raise
        return jsonify({
            "success": True,
            "clip_id": clip_id,
            "job_id": job["id"],
            "operation": "adjust_clip_render",
            "review_status": "needs_review",
            "adjustment": {**normalized, "render_status": "queued"},
            "render_status": "queued",
            "source": {"duration": source_duration},
        }), 202
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Falha ao renderizar o ajuste: {str(exc)[:240]}"}), 500


@app.route("/api/editorial/learning", methods=["GET"])
def api_editorial_learning():
    """Return a whitelist of aggregate-only priors; never return raw rows."""
    prior = _get_approved_clip_prior()
    allowed = {
        "available", "eligible", "record_count", "approved_count", "rejected_count", "minimum_samples",
        "approved_mean_duration", "rejected_mean_duration", "approved_median_duration", "rejected_median_duration",
        "duration_median_approved", "duration_p25_approved", "duration_p75_approved",
        "approved_by_format", "rejected_by_format", "overall_by_format", "approved_by_hook_family", "rejected_by_hook_family",
        "family_share_approved", "opening_pattern_share_approved", "rejection_reason_share", "format_by_family", "topic_by_format",
        "has_qa_bridge_rate_approved", "headline_shape", "factor_deltas", "headline_learning_thresholds", "influence_scope",
    }
    public_prior = {key: prior[key] for key in allowed if key in prior}
    return jsonify({
        "ok": True,
        "available": bool(prior.get("available")),
        "eligible": bool(prior.get("eligible")),
        "sample_size_approved": int(prior.get("approved_count", 0) or 0),
        "sample_size_rejected": int(prior.get("rejected_count", 0) or 0),
        "priors": public_prior,
        "headline_learning_thresholds": public_prior.get("headline_learning_thresholds", {"min_topic_format_count": 2, "min_overall_format_count": 4}),
        "raw_rows_exposed": False,
        "store_path_hint": "FuriaClipsData/learning",
    })


@app.route("/api/editorial/learning/import", methods=["POST"])
def api_editorial_learning_import():
    """Import a real local or uploaded CSV/JSON/JSONL export with strict reporting."""
    from modules.approved_clip_priors import build_feature_prior, load_feature_records
    from modules.learning_importer import DEFAULT_LEARNING_DIR, import_review_dataset, import_review_rows

    data = request.get_json(silent=True) or {}
    temporary_path = None
    try:
        upload = request.files.get("file")
        if upload and upload.filename:
            suffix = Path(upload.filename).suffix.lower()
            if suffix not in {".csv", ".json", ".jsonl"}:
                return jsonify({"ok": False, "error": "expected csv, json array, or jsonl"}), 400
            DEFAULT_LEARNING_DIR.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(prefix="learning_upload_", suffix=suffix, dir=DEFAULT_LEARNING_DIR, delete=False) as handle:
                temporary_path = handle.name
            upload.save(temporary_path)
            manifest = import_review_dataset(temporary_path, output_dir=DEFAULT_LEARNING_DIR, strict=True)
        elif isinstance(data.get("items"), list):
            manifest = import_review_rows(data["items"], output_dir=DEFAULT_LEARNING_DIR, source_name="inline_items", strict=True)
        else:
            requested = str(data.get("path") or data.get("input_path") or "").strip()
            if not requested:
                return jsonify({"ok": False, "error": "Informe path/input_path, items ou um arquivo multipart."}), 400
            target = os.path.abspath(os.path.expanduser(requested)) if os.path.isabs(requested) else os.path.abspath(os.path.join(_PERSISTENT_ROOT, requested))
            allowed_roots = [os.path.abspath(_PERSISTENT_ROOT), os.path.abspath(WORKSPACE_DIR)]
            if not any(_is_under(target, root) for root in allowed_roots) or not os.path.isfile(target):
                return jsonify({"ok": False, "error": "O dataset deve existir em FuriaClipsData ou no workspace local."}), 400
            manifest = import_review_dataset(target, output_dir=DEFAULT_LEARNING_DIR, strict=_coerce_bool(data.get("strict"), default=True))
        prior = build_feature_prior(load_feature_records(manifest.get("output_path")))
        response = {key: value for key, value in manifest.items() if key not in {"source_path", "output_path"}}
        response.update({
            "ok": True,
            "priors_updated": bool(manifest.get("accepted", 0)),
            "prior": prior,
            "store_path_hint": "FuriaClipsData/learning",
        })
        return jsonify(response)
    except (OSError, ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return jsonify({"ok": False, "error": str(exc)[:300]}), 400
    finally:
        if temporary_path:
            try:
                os.unlink(temporary_path)
            except OSError:
                pass


@app.route("/api/editorial/calibration", methods=["GET"])
def api_editorial_calibration():
    return jsonify(get_feedback_calibration())


@app.route("/api/editorial/daily-progress", methods=["GET"])
def api_editorial_daily_progress():
    return jsonify(get_daily_editorial_progress())


@app.route("/api/editorial/data", methods=["GET"])
def api_editorial_data():
    """Expose persistent editorial-storage health without returning secrets."""
    return jsonify(get_editorial_data_summary())


@app.route("/api/editorial/transcripts", methods=["GET"])
def api_editorial_transcripts():
    try:
        limit = min(200, max(1, int(request.args.get("limit", 100))))
    except (TypeError, ValueError):
        limit = 100
    return jsonify({
        "transcripts": [
            {
                **item,
                "download_text": f"/api/editorial/transcripts/{item['relative_dir']}/transcript.txt",
                "download_json": f"/api/editorial/transcripts/{item['relative_dir']}/transcript.json",
            }
            for item in list_archived_transcriptions(limit)
        ],
        "persistent_dir": PERSISTENT_TRANSCRIPTS_DIR,
    })


@app.route("/api/editorial/transcripts/open", methods=["POST"])
def api_open_editorial_transcript_folder():
    data = request.get_json(silent=True) or {}
    relative_dir = str(data.get("relative_dir", "") or "").strip()
    root = os.path.abspath(PERSISTENT_TRANSCRIPTS_DIR)
    folder = os.path.abspath(os.path.join(root, relative_dir))
    try:
        inside_root = os.path.commonpath([root, folder]) == root
    except ValueError:
        inside_root = False
    if not inside_root or not os.path.isdir(folder):
        return jsonify({"error": "Pasta persistente de transcrição inválida ou não encontrada"}), 404
    try:
        open_local_path(folder)
        return jsonify({"success": True, "relative_dir": os.path.relpath(folder, root)})
    except (FileNotFoundError, OSError) as exc:
        return jsonify({"error": "Não foi possível abrir a pasta persistente", "detail": str(exc)[:200]}), 500


@app.route("/api/editorial/transcripts/<path:relative_file>", methods=["GET"])
def api_editorial_transcript_file(relative_file):
    root = os.path.abspath(PERSISTENT_TRANSCRIPTS_DIR)
    candidate = os.path.abspath(os.path.join(root, relative_file))
    allowed = {"transcript.txt", "transcript.json", "metadata.json"}
    if os.path.commonpath([root, candidate]) != root or os.path.basename(candidate) not in allowed:
        return jsonify({"error": "Arquivo de transcrição inválido"}), 400
    if not os.path.isfile(candidate):
        return jsonify({"error": "Transcrição não encontrada"}), 404
    return send_file(candidate, as_attachment=False, download_name=os.path.basename(candidate))


@app.route("/api/editorial/backup", methods=["POST"])
def api_editorial_backup():
    try:
        backup = create_editorial_backup()
        return jsonify({
            "success": True,
            "filename": backup["filename"],
            "size_bytes": backup["size_bytes"],
            "summary": backup["summary"],
        })
    except PersistentDataError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/editorial/backup/<filename>", methods=["GET"])
def api_download_editorial_backup(filename):
    if os.path.basename(filename) != filename or not filename.startswith("furia-editorial-backup-") or not filename.endswith(".zip"):
        return jsonify({"error": "Arquivo de backup inválido"}), 400
    from config import PERSISTENT_BACKUPS_DIR
    candidate = os.path.join(PERSISTENT_BACKUPS_DIR, filename)
    if not os.path.isfile(candidate):
        return jsonify({"error": "Backup não encontrado"}), 404
    return send_file(candidate, as_attachment=True, download_name=filename)


@app.route("/api/campaign-hub/status", methods=["GET"])
def api_campaign_hub_status():
    """Report bounded local Campaign Hub snapshot metadata without any write path."""
    try:
        from modules.campaign_hub import snapshot_status
        settings = get_all_settings()
        return jsonify(snapshot_status(settings.get("campaign_hub_snapshot_path")))
    except Exception as exc:
        return jsonify({
            "available": False,
            "source": "campaign_hub_local_snapshot",
            "status": "error",
            "read_only": True,
            "message": f"Não foi possível ler o snapshot local: {str(exc)[:240]}",
        }), 200


@app.route("/api/repository/status", methods=["GET"])
def api_repository_status():
    """Report Git synchronization state without exposing remotes or secrets."""
    try:
        return jsonify(get_repository_status(fetch=False))
    except RepositorySyncError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@app.route("/api/repository/sync", methods=["POST"])
def api_repository_sync():
    """Update the checkout or publish only the sanitized editorial feedback projection."""
    data = request.get_json(silent=True) or {}
