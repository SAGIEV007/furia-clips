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
    update_clip_review_status, save_clip_adjustment, get_feedback_calibration, get_daily_editorial_progress,
    save_headline_feedback, get_headline_feedback_summary, get_headline_learning_preferences,
    save_performance_snapshot, get_performance_snapshots, get_performance_summary
)
from modules.security import UnsafePathError, safe_workspace_path, unique_storage_name
from modules.native_dialogs import DialogError, choose_path, open_local_path
from modules.transcript_parser import parse_transcript_text, normalize_segment_payload, parse_timestamp
from modules.clip_adjustments import adjust_clip_bounds
from modules.editorial_block import build_editorial_block
from modules.performance_metrics import normalize_snapshot, metric_labels
from modules.transcript_archive import archive_transcription, list_archived_transcriptions, validate_transcription
from modules.source_boundary import detect_live_content_start, trim_transcription_to_live_start
from modules.source_ingest import (
    SourceIngestError,
    probe_public_url,
    download_public_video,
    download_public_audio,
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
from modules.editorial_learning_store import (
    save_transcription_bundle,
    save_context_bundle,
    save_headline_generation,
    save_headline_decision,
    save_clip_decision,
    write_session_manifest,
)
from modules.repository_sync import (
    RepositorySyncError,
    get_repository_status,
    push_feedback_snapshot,
    restore_feedback_snapshot,
    update_from_github,
)

# User-friendly error messages (Portuguese)
ERROR_MESSAGES = {
    "no_audio": "Este video NAO contem audio! Provavelmente foi baixado no formato DASH (so video). Baixe novamente com audio incluido. No yt-dlp use: -f bestvideo+bestaudio --merge-output-format mp4",
    "unsupported_format": "Formato de video nao suportado. Tente converter para MP4 primeiro.",
    "ffmpeg_not_found": "FFmpeg nao encontrado. Instale de: https://ffmpeg.org/download.html",
    "file_not_found": "Video nao encontrado no caminho especificado.",
    "ollama_unavailable": "Ollama nao detectado. Usando NLP basico (menos preciso). Instale em: https://ollama.com",
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


def _load_program_version():
    """Load the public release version from the repository's VERSION file."""
    version_path = os.path.join(BASE_DIR, "VERSION")
    try:
        with open(version_path, "r", encoding="utf-8") as handle:
            version = handle.read().strip()
    except (OSError, UnicodeError):
        version = "1.0"
    return version[:32] or "1.0"


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


PROGRAM_VERSION = _load_program_version()
PROGRAM_REVISION = _runtime_revision()

processing_lock = threading.Lock()
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


def emit_progress(message, level="info"):
    runtime_message = f"[Versão {PROGRAM_VERSION} · {PROGRAM_REVISION}] {str(message)}"
    socketio.emit(
        "progress",
        {
            "message": runtime_message,
            "level": level,
            "time": datetime.now().strftime("%H:%M:%S"),
            "program_version": PROGRAM_VERSION,
            "program_revision": PROGRAM_REVISION,
        },
    )


def emit_status(status, data=None):
    socketio.emit("status", {"status": status, "data": data or {}})


def _emit_job_update(job):
    if job:
        socketio.emit("job_update", job)


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


# Roughly one candidate per this many seconds of source. Calibrated against the
# Acervo benchmark: on a 98-minute live the pipeline stopped producing new
# candidates at 121, about one per 49s, so a budget below that only discards
# material the gates had already approved.
SECONDS_PER_CANDIDATE = 45
# Floor for short sources and a safety valve against pathological input. The
# ceiling is not an editorial decision: quality gates decide what survives.
MIN_CANDIDATE_BUDGET = 15
MAX_CANDIDATE_BUDGET = 400


def _selection_coverage_plan(source_video, video_duration):
    """Build a local-only plan for adaptive candidate coverage and deduplication.

    The budget follows the length of the source instead of a fixed ceiling. The
    previous cap of 36 gave a four-hour source practically the same allowance as
    a one-hour one, so the longer the video the more of it went unexamined. It is
    a budget, not a target: the pipeline stops on its own when the material runs
    out, and no minimum number of clips is ever produced to fill it.
    """
    fingerprints = get_existing_clip_fingerprints(source_video)
    try:
        span = max(0.0, float(video_duration or 0.0))
    except (TypeError, ValueError):
        span = 0.0
    if span < 120:
        max_clips = MIN_CANDIDATE_BUDGET
    else:
        max_clips = min(
            MAX_CANDIDATE_BUDGET,
            max(MIN_CANDIDATE_BUDGET, int(span // SECONDS_PER_CANDIDATE) + 6),
        )
    return {"previous_clip_fingerprints": fingerprints, "adaptive_max_clips": max_clips}


def _defer_context_incomplete_candidates(candidates):
    """Keep editorially unsafe candidates for review instead of rendering them ready.

    The ranker still exposes deferred candidates and their reasons. Rendering is the
    final publication-like boundary: a strong hook must not compensate for missing
    context or an explicit technical review requirement such as an unvalidated
    question bridge or a sensitive claim without evidence.
    """
    renderable = []
    deferred = []
    for candidate in candidates or []:
        review_flags = candidate.get("review_flags") or {}
        technical_status = candidate.get("technical_gate_status") or review_flags.get("technical_gate_status")
        technical_reasons = candidate.get("technical_gate_reasons") or review_flags.get("technical_gate_reasons") or []
        context_incomplete = "context_complete" in candidate and candidate.get("context_complete") is False
        technical_review = technical_status == "review"
        if not context_incomplete and not technical_review:
            renderable.append(candidate)
            continue

        reasons = []
        if context_incomplete:
            reasons.append("contexto autossuficiente não confirmado")
            if candidate.get("starts_mid_sentence"):
                reasons.append("início possivelmente no meio da frase")
            if candidate.get("starts_with_context_reference"):
                reasons.append("referência contextual sem antecedente recuperado")
        if technical_review:
            reasons.append("revisão técnica editorial obrigatória")
            reasons.extend(str(reason) for reason in technical_reasons if str(reason).strip())
        deferred.append({
            "start": candidate.get("start", candidate.get("start_time")),
            "end": candidate.get("end", candidate.get("end_time")),
            "duration": candidate.get("duration"),
            "reason": "; ".join(dict.fromkeys(reasons)),
            "review_flags": review_flags,
        })
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
    )
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


def _transcription_from_request(data, duration=None):
    """Return a canonical transcription when the user supplied one."""
    text = data.get("transcript_text") or data.get("manual_transcript") or ""
    if isinstance(text, str) and text.strip():
        result = parse_transcript_text(text, duration=duration)
        raw_result = parse_transcript_text(text, duration=None)
        result["raw_last_timestamp"] = max((float(item.get("end") if item.get("end") is not None else item.get("start", 0)) for item in raw_result.get("segments", [])), default=None)
        result["language"] = data.get("transcript_language", "pt")
        result["source"] = "manual"
        result["provenance"] = {
            "source": "manual",
            "input_kind": "transcript_text" if data.get("transcript_text") else "manual_transcript",
            "confirmed_by_editor": True,
        }
        return result
    segments = data.get("transcript_segments")
    if isinstance(segments, list) and segments:
        result = normalize_segment_payload(segments, duration=duration)
        result["raw_last_timestamp"] = max(
            (float(item.get("end") if item.get("end") is not None else item.get("start", 0)) for item in segments if isinstance(item, dict)),
            default=None,
        )
        result["language"] = data.get("transcript_language", "pt")
        result["source"] = "manual"
        result["provenance"] = {
            "source": "manual",
            "input_kind": "transcript_segments",
            "confirmed_by_editor": True,
        }
        return result
    return None


def _manual_transcript_was_supplied(data):
    data = data or {}
    text = data.get("transcript_text") or data.get("manual_transcript") or ""
    if isinstance(text, str) and text.strip():
        return True
    segments = data.get("transcript_segments")
    return isinstance(segments, list) and bool(segments)


def _transcript_reference_for_multimodal(transcription, max_chars=48000):
    """Build a bounded timestamped reference; local selection still uses all text."""
    if not isinstance(transcription, dict):
        return ""
    segments = [item for item in transcription.get("segments", []) if isinstance(item, dict) and str(item.get("text", "")).strip()]
    if not segments:
        return ""

    def line(item):
        start = float(item.get("start", 0) or 0)
        hours = int(start // 3600)
        minutes = int((start % 3600) // 60)
        seconds = start % 60
        return f"[{hours:02d}:{minutes:02d}:{seconds:06.3f}] {str(item.get('text', '')).strip()}"

    full = "\n".join(line(item) for item in segments)
    if len(full) <= max_chars:
        return full
    head_budget = max_chars // 3
    tail_budget = max_chars // 3
    head, tail = [], []
    used = 0
    for item in segments:
        value = line(item)
        if used + len(value) + 1 > head_budget:
            break
        head.append(value)
        used += len(value) + 1
    used = 0
    for item in reversed(segments):
        value = line(item)
        if used + len(value) + 1 > tail_budget:
            break
        tail.append(value)
        used += len(value) + 1
    middle_budget = max_chars - len("\n".join(head)) - len("\n".join(tail)) - 120
    middle = []
    step = max(1, len(segments) // max(1, middle_budget // 120))
    for item in segments[len(head): max(len(head), len(segments) - len(tail)): step]:
        value = line(item)
        if sum(len(entry) + 1 for entry in middle) + len(value) + 1 > middle_budget:
            break
        middle.append(value)
    return "\n".join([*head, "[...trechos intermediários amostrados...]"] + middle + ["[...fim da transcrição...]"] + list(reversed(tail)))


def _transcription_provenance(transcription, *, manual_supplied=False):
    transcription = transcription or {}
    coverage = transcription.get("coverage") if isinstance(transcription.get("coverage"), dict) else {}
    return {
        "source": str(transcription.get("source", "unknown") or "unknown"),
        "manual_supplied": bool(manual_supplied),
        "confirmed_by_editor": bool(manual_supplied or transcription.get("source") in {"manual", "manual_confirmed"}),
        "segment_count": int(transcription.get("segment_count", len(transcription.get("segments", [])) or 0) or 0),
        "coverage_status": str(coverage.get("status", "unknown") or "unknown"),
        "first_timestamp": coverage.get("first_timestamp"),
        "last_timestamp": coverage.get("last_timestamp"),
        "used_as_canonical_timeline": True,
    }


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
    from modules.campaign_hub import load_snapshot

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
    account = str(settings.get("campaign_hub_account", "@renansantosmbl") or "@renansantosmbl")
    account_data = (snapshot or {}).get("accounts", {}).get(account, {}) if isinstance(snapshot, dict) else {}
    family_priors = (snapshot or {}).get("instagram_family_priors", {}).get("family_priors", []) if isinstance(snapshot, dict) else []
    enriched["campaign_hub"] = {
        "used": bool(snapshot),
        "source": "campaign_hub_aggregate_snapshot" if snapshot else "unavailable",
        "account": account,
        "hook_observations": len(account_data.get("hook_observations", [])) if isinstance(account_data, dict) else 0,
        "family_prior_count": len(family_priors) if isinstance(family_priors, list) else 0,
        "role": "prior fraco e explicável; nunca substitui contexto, payoff ou revisão humana",
    }
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
    span_ratio = round(min(1.0, max(0.0, (last - first) / video_duration)), 3) if video_duration and first is not None and last is not None else None
    if out_of_bounds:
        status = "mismatch_suspected"
    elif video_duration and last is not None and end_ratio < 0.35:
        status = "partial"
    else:
        status = "covered"
    return {
        "status": status,
        "video_duration_seconds": round(video_duration, 3) if video_duration else None,
        "first_timestamp": round(first, 3) if first is not None else None,
        "last_timestamp": round(last, 3) if last is not None else None,
        "end_ratio": end_ratio,
        "span_ratio": span_ratio,
        "segment_count": len(valid),
        "semantic_identity_verified": False,
    }


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
        if "maximum number of tokens" in detail.lower() or "input token count" in detail.lower():
            emit_progress(
                "[Gemini] O pedido multimodal excedeu o limite de contexto. A cópia compactada e a transcrição canônica serão usadas nas próximas tentativas; nenhum corte será perdido por causa disso.",
                "warning",
            )
        elif "503" in detail or "high demand" in detail.lower():
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
        return float(value)
    try:
        return parse_timestamp(str(value or "0:00"))
    except (TypeError, ValueError):
        return None


def _attach_multimodal_visual_observations(clips, multimodal):
    """Attach the strongest overlapping Gemini visual observation to each clip."""
    if not isinstance(multimodal, dict):
        return clips
    identity_status = str(multimodal.get("source_identity_status", "unverified") or "unverified").lower()
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
        for key in ("visual_format", "text_panel", "fake_tweet", "social_post", "visual_meme", "split_screen", "external_evidence"):
            if key in observation:
                clip[key] = observation[key]
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
    if source == "manual":
        return bool(settings.get("gemini_manual_video_analysis", False))
    return bool(settings.get("gemini_video_analysis_with_transcript", False))


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


@app.route("/api/jobs/<job_id>", methods=["GET"])
def api_get_job(job_id):
    job = job_manager.get(job_id)
    if not job:
        return jsonify({"error": "Job não encontrado"}), 404
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
    """Rank and select a quality-gated portfolio across multiple live sources."""
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

    options = data.get("options") or {}
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
        )
    except (TypeError, ValueError) as exc:
        return jsonify({"error": f"Parâmetros de ranking inválidos: {exc}"}), 400
    return jsonify(portfolio)


@app.route("/api/clips/<int:clip_id>/feedback", methods=["GET", "POST"])
def api_clip_feedback(clip_id):
    if request.method == "GET":
        return jsonify({"feedback": get_clip_feedback(clip_id)})
    data = request.get_json(silent=True) or {}
    action = data.get("action", "")
    try:
        clip_before = get_clip(clip_id)
        if not clip_before:
            return jsonify({"error": "Clip não encontrado"}), 404
        save_clip_feedback(
            clip_id,
            action,
            adjustments=data.get("adjustments") or {},
            note=data.get("note", ""),
            reason_code=data.get("reason_code", ""),
            quality_tags=data.get("quality_tags") or [],
        )
        project = get_project(clip_before.get("project_id")) or {}
        try:
            save_clip_decision(
                {
                    "action": str(action or "")[:32],
                    "adjustments": data.get("adjustments") or {},
                    "note": str(data.get("note", "") or "")[:600],
                    "reason_code": str(data.get("reason_code", "") or "")[:48],
                    "quality_tags": list(data.get("quality_tags") or [])[:12],
                    "start_seconds": clip_before.get("start_time"),
                    "end_seconds": clip_before.get("end_time"),
                    "editorial_key": clip_before.get("editorial_key", ""),
                },
                project_id=clip_before.get("project_id"),
                clip_id=clip_id,
                source_video=project.get("source_video", ""),
            )
        except Exception as storage_error:
            app.logger.warning("Não foi possível arquivar decisão editorial: %s", storage_error)
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
    """Report bounded local Campaign Hub metadata without calling the MCP."""
    try:
        from modules.campaign_hub import snapshot_status
        from modules.campaign_hub_memory import memory_status
        settings = get_all_settings()
        snapshot_path = settings.get("campaign_hub_snapshot_path")
        snapshot = snapshot_status(snapshot_path)
        memory = memory_status(snapshot_path)
        # Keep the legacy top-level fields used by the current frontend while
        # exposing the richer memory contract for the new UX.
        snapshot["memory"] = memory
        snapshot["memory_available"] = bool(memory.get("available"))
        snapshot["memory_schema_version"] = memory.get("memory_schema_version", "")
        snapshot["record_counts"] = memory.get("record_counts", {})
        snapshot["last_sync_at"] = memory.get("last_sync_at", "")
        return jsonify(snapshot)
    except Exception as exc:
        return jsonify({
            "available": False,
            "source": "campaign_hub_local_snapshot",
            "status": "error",
            "read_only": True,
            "memory_available": False,
            "message": f"Não foi possível ler a memória local: {str(exc)[:240]}",
        }), 200


@app.route("/api/campaign-hub/memory/status", methods=["GET"])
def api_campaign_hub_memory_status():
    """Return the offline-first memory status without exposing its contents."""
    try:
        from modules.campaign_hub_memory import export_status_payload
        settings = get_all_settings()
        return jsonify(export_status_payload(settings.get("campaign_hub_snapshot_path")))
    except Exception as exc:
        return jsonify({
            "available": False,
            "source": "campaign_hub_local_memory",
            "status": "error",
            "read_only_runtime": True,
            "message": f"Não foi possível ler a memória local: {str(exc)[:240]}",
        }), 200


@app.route("/api/campaign-hub/memory/import", methods=["POST"])
def api_campaign_hub_memory_import():
    """Install an authorized JSON export; the app never contacts the MCP here."""
    uploaded = request.files.get("snapshot")
    if not uploaded or not uploaded.filename:
        return jsonify({"success": False, "error": "Envie um arquivo JSON de exportação do Campaign Hub."}), 400
    temp_path = None
    try:
        from modules.campaign_hub_memory import import_snapshot_file
        settings = get_all_settings()
        destination = settings.get("campaign_hub_snapshot_path") or None
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix="campaign-hub-import-",
            suffix=".json",
            dir=PERSISTENT_DATA_DIR,
            delete=False,
        ) as handle:
            uploaded.save(handle)
            temp_path = handle.name
        if os.path.getsize(temp_path) > 100 * 1024 * 1024:
            raise ValueError("O export do Campaign Hub excede o limite local de 100 MB.")
        merge = _coerce_bool(request.form.get("merge"), default=True)
        status = import_snapshot_file(temp_path, destination=destination, merge=merge)
        return jsonify({"success": True, "message": "Memória local atualizada com export autorizado.", **status})
    except (OSError, ValueError) as exc:
        return jsonify({"success": False, "error": str(exc)[:300]}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": f"Falha ao importar memória local: {str(exc)[:300]}"}), 500
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


@app.route("/api/editorial/blocks", methods=["GET"])
def api_editorial_blocks():
    """List blocks from local memory; network access is intentionally absent."""
    try:
        from modules.editorial_block_memory import list_blocks
        settings = get_all_settings()
        renan_value = request.args.get("renan_speaking")
        renan_speaking = None if renan_value in (None, "", "all") else _coerce_bool(renan_value)
        payload = list_blocks(
            settings.get("campaign_hub_snapshot_path"),
            query=str(request.args.get("q") or "").strip(),
            video_id=str(request.args.get("video_id") or "").strip() or None,
            renan_speaking=renan_speaking,
            prioritize_renan=request.args.get("prioritize_renan", "0") == "1",
            source_ref=str(request.args.get("source_ref") or "").strip() or None,
            limit=request.args.get("limit", 50),
            offset=request.args.get("offset", 0),
        )
        return jsonify(payload)
    except (TypeError, ValueError) as exc:
        return jsonify({"available": False, "blocks": [], "total": 0, "error": str(exc)[:240]}), 400
    except Exception as exc:
        return jsonify({"available": False, "blocks": [], "total": 0, "error": f"Não foi possível ler os blocos: {str(exc)[:240]}"}), 200


@app.route("/api/editorial/blocks/<block_id>", methods=["GET"])
def api_editorial_block(block_id):
    """Return one local block with bounded highlights and transcript sentences."""
    try:
        from modules.editorial_block_memory import get_block
        settings = get_all_settings()
        block = get_block(block_id, settings.get("campaign_hub_snapshot_path"))
        if not block:
            return jsonify({"error": "Bloco não encontrado na memória local."}), 404
        return jsonify({"available": True, "block": block})
    except Exception as exc:
        return jsonify({"available": False, "error": f"Não foi possível ler o bloco: {str(exc)[:240]}"}), 200


@app.route("/api/editorial/blocks/export", methods=["POST"])
def api_export_editorial_block_interval():
    """Render one selected local interval; remote range download is a later wave."""
    data = request.get_json(silent=True) or {}
    video_path = _resolve_media_input(data.get("video_path", ""))
    if not video_path or not os.path.isfile(video_path):
        return jsonify({"success": False, "error": "A fonte local do bloco não foi encontrada."}), 404
    try:
        start = max(0.0, float(data.get("start", 0)))
        end = float(data.get("end"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Informe início e fim numéricos para o intervalo."}), 400
    if end <= start:
        return jsonify({"success": False, "error": "O fim do intervalo precisa ser maior que o início."}), 400
    requested_start = start
    requested_end = end
    duration = _probe_video_duration_seconds(video_path)
    timeline_mapping = "source_timeline"
    if duration and end > duration + 0.25:
        # A block downloaded from Garimpo/Acervo starts at zero locally while
        # its Chub timestamps remain absolute in the long source. Infer this
        # only when the local duration closely matches the selected block span.
        block_span = end - start
        if abs(duration - block_span) <= max(15.0, block_span * 0.05):
            start = 0.0
            end = min(duration, block_span)
            timeline_mapping = "downloaded_block_timeline"
        else:
            return jsonify({"success": False, "error": f"O bloco termina em {requested_end:.1f}s, mas a fonte local tem apenas {duration:.1f}s e não parece ser esse bloco."}), 400
    if end - start > 15 * 60:
        return jsonify({"success": False, "error": "A exportação seletiva está limitada a 15 minutos por intervalo."}), 413
    try:
        from modules.video_cutter import VideoCutter
        block_id = str(data.get("block_id") or "intervalo")
        filename = unique_storage_name(
            f"bloco-{block_id}-{int(start)}-{int(end)}.mp4",
            extension=".mp4",
        )
        output_path = os.path.join(EXPORT_DIR, filename)
        cutter = VideoCutter(method="intelligent", target_duration=end - start, preset="shorts")
        rendered = cutter.cut_clip(
            video_path,
            start,
            end,
            output_path,
            vertical=False,
            emit_progress=None,
        )
        if not rendered:
            return jsonify({"success": False, "error": "A renderização do intervalo foi rejeitada pela validação de mídia."}), 422
        relative = os.path.relpath(rendered, WORKSPACE_DIR).replace(os.sep, "/")
        return jsonify({
            "success": True,
            "source_mode": "local_interval",
            "block_id": block_id,
            "start": start,
            "end": end,
            "requested_start": requested_start,
            "requested_end": requested_end,
            "duration": round(end - start, 3),
            "timeline_mapping": timeline_mapping,
            "path": relative,
            "download_url": f"/workspace/{relative}",
            "message": "Intervalo exportado no aspecto original; timestamps absolutos foram mapeados para a linha local quando a fonte parecia ser um bloco baixado.",
        })
    except Exception as exc:
        return jsonify({"success": False, "error": f"Não foi possível exportar o intervalo: {str(exc)[:300]}"}), 500


@app.route("/api/editorial/blocks/highlights/export", methods=["POST"])
def api_export_editorial_highlight():
    """Render one Campaign Hub highlight on the local block timeline."""
    data = request.get_json(silent=True) or {}
    video_path = _resolve_media_input(data.get("video_path", ""))
    if not video_path or not os.path.isfile(video_path):
        return jsonify({"success": False, "error": "A fonte local do bloco não foi encontrada."}), 404
    block_id = str(data.get("block_id") or "").strip()
    highlight_id = str(data.get("highlight_id") or "").strip()
    if not block_id or not highlight_id:
        return jsonify({"success": False, "error": "Informe block_id e highlight_id."}), 400
    try:
        from modules.editorial_block_memory import get_block
        from modules.editorial_benchmark import map_interval_to_local
        settings = get_all_settings()
        block = get_block(block_id, settings.get("campaign_hub_snapshot_path"))
        if not block:
            return jsonify({"success": False, "error": "Bloco não encontrado na memória local."}), 404
        highlight = next((item for item in block.get("highlights", []) if str(item.get("id")) == highlight_id), None)
        if not highlight:
            return jsonify({"success": False, "error": "Destaque não encontrado dentro do bloco."}), 404
        try:
            absolute_start = float(highlight.get("start_s"))
            absolute_end = float(highlight.get("end_s"))
            block_start = float(block.get("start", 0))
            block_end = float(block.get("end", block_start))
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "O destaque não possui timestamps válidos."}), 400
        duration = _probe_video_duration_seconds(video_path)
        mapped = map_interval_to_local(
            absolute_start,
            absolute_end,
            source_duration=duration,
            reference_start=block_start,
            reference_end=block_end,
        )
        start = float(mapped["start"])
        end = float(mapped["end"])
        if end <= start:
            return jsonify({"success": False, "error": "O destaque não produz um intervalo local válido."}), 400
        from modules.video_cutter import VideoCutter
        filename = unique_storage_name(
            f"highlight-{block_id}-{highlight_id.replace(':', '-')}.mp4",
            extension=".mp4",
        )
        output_path = os.path.join(EXPORT_DIR, filename)
        cutter = VideoCutter(method="intelligent", target_duration=end - start, preset="shorts")
        rendered = cutter.cut_clip(video_path, start, end, output_path, vertical=False, emit_progress=None)
        if not rendered:
            return jsonify({"success": False, "error": "A renderização do destaque foi rejeitada pela validação de mídia."}), 422
        relative = os.path.relpath(rendered, WORKSPACE_DIR).replace(os.sep, "/")
        return jsonify({
            "success": True,
            "source_mode": "local_highlight",
            "block_id": block_id,
            "highlight_id": highlight_id,
            "absolute_start": absolute_start,
            "absolute_end": absolute_end,
            "start": start,
            "end": end,
            "duration": round(end - start, 3),
            "timeline_mapping": mapped["timeline_mapping"],
            "path": relative,
            "download_url": f"/workspace/{relative}",
            "text": highlight.get("text") or "",
            "reason": highlight.get("reason") or "",
            "message": "Destaque exportado no aspecto original; a timeline absoluta foi mapeada para o MP4 local quando necessário.",
        })
    except Exception as exc:
        return jsonify({"success": False, "error": f"Não foi possível exportar o destaque: {str(exc)[:300]}"}), 500


@app.route("/api/editorial/benchmark", methods=["GET", "POST"])
def api_editorial_benchmark():
    """Persist or list local-only comparisons against Campaign Hub highlights."""
    if request.method == "GET":
        try:
            from modules.editorial_benchmark import list_benchmarks, load_benchmark
            benchmark_id = str(request.args.get("benchmark_id") or "").strip()
            if benchmark_id:
                payload = load_benchmark(benchmark_id)
                if not payload:
                    return jsonify({"available": False, "error": "Benchmark não encontrado."}), 404
                return jsonify({"available": True, "benchmark": payload})
            return jsonify({"available": True, "benchmarks": list_benchmarks()})
        except Exception as exc:
            return jsonify({"available": False, "error": f"Não foi possível ler o benchmark: {str(exc)[:240]}"}), 200

    data = request.get_json(silent=True) or {}
    block_id = str(data.get("block_id") or "").strip()
    candidates = data.get("candidates")
    if not block_id or not isinstance(candidates, list):
        return jsonify({"success": False, "error": "Informe block_id e uma lista de candidates."}), 400
    try:
        from modules.editorial_block_memory import get_block
        from modules.editorial_benchmark import compare_candidates, save_benchmark
        settings = get_all_settings()
        block = get_block(block_id, settings.get("campaign_hub_snapshot_path"))
        if not block:
            return jsonify({"success": False, "error": "Bloco não encontrado na memória local."}), 404
        video_path = _resolve_media_input(data.get("video_path", ""))
        source_duration = _probe_video_duration_seconds(video_path) if video_path and os.path.isfile(video_path) else None
        payload = compare_candidates(
            block,
            candidates,
            source_duration=source_duration,
            source_name=video_path or str(data.get("video_path") or ""),
            benchmark_version=str(data.get("benchmark_version") or "b354-v1")[:40],
        )
        target = save_benchmark(payload)
        measurement = payload.get("measurement") or {}
        message = "Benchmark salvo localmente; ele não altera o ranking nem consulta o Campaign Hub durante os cortes."
        if not measurement.get("reliable", True):
            message = (
                "Benchmark salvo, mas a medição não é comparável ao baseline: "
                + " ".join(measurement.get("warnings") or [])
            )
        return jsonify({
            "success": True,
            "benchmark_id": payload["benchmark_id"],
            "measurement": measurement,
            "metrics": payload["metrics"],
            "references": payload["references"],
            "candidate_count": payload["candidate_count"],
            "file": target.name,
            "message": message,
        })
    except (TypeError, ValueError) as exc:
        return jsonify({"success": False, "error": str(exc)[:300]}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": f"Não foi possível salvar o benchmark: {str(exc)[:300]}"}), 500


@app.route("/api/editorial/benchmark/<benchmark_id>", methods=["GET"])
def api_editorial_benchmark_detail(benchmark_id):
    try:
        from modules.editorial_benchmark import load_benchmark
        payload = load_benchmark(benchmark_id)
        if not payload:
            return jsonify({"available": False, "error": "Benchmark não encontrado."}), 404
        return jsonify({"available": True, "benchmark": payload})
    except Exception as exc:
        return jsonify({"available": False, "error": f"Não foi possível ler o benchmark: {str(exc)[:240]}"}), 200


@app.route("/api/repository/status", methods=["GET"])
def api_repository_status():
    """Report Git synchronization state without exposing remotes or secrets."""
    try:
        return jsonify(get_repository_status(fetch=request.args.get("fetch", "1") != "0"))
    except RepositorySyncError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@app.route("/api/repository/sync", methods=["POST"])
def api_repository_sync():
    """Update the checkout or publish only the sanitized editorial feedback projection."""
    data = request.get_json(silent=True) or {}
    action = str(data.get("action", "check") or "check").strip().lower()
    try:
        if action == "check":
            return jsonify(get_repository_status(fetch=True))
        if current_task.get("active"):
            return jsonify({"success": False, "error": "Aguarde ou cancele o processamento atual antes de sincronizar o programa."}), 409
        if action == "update":
            safety_backup = create_editorial_backup()
            result = update_from_github()
            result["safety_backup"] = safety_backup.get("filename")
            result["restart_required"] = bool(result.get("updated"))
            return jsonify(result)
        if action in {"push_feedback", "sync_feedback"}:
            return jsonify(push_feedback_snapshot())
        if action in {"restore_feedback", "import_feedback"}:
            return jsonify(restore_feedback_snapshot())
        return jsonify({"success": False, "error": "Ação de sincronização desconhecida."}), 400
    except (RepositorySyncError, PersistentDataError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@app.route("/api/editorial/restore", methods=["POST"])
def api_editorial_restore():
    if current_task.get("active"):
        return jsonify({"error": "Pare ou aguarde o processamento atual antes de restaurar dados editoriais."}), 409
    uploaded = request.files.get("backup")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "Selecione um arquivo ZIP de backup editorial."}), 400
    if not uploaded.filename.lower().endswith(".zip"):
        return jsonify({"error": "Selecione um arquivo ZIP criado pelo Furia Clips."}), 400
    from config import PERSISTENT_BACKUPS_DIR
    temp_handle = tempfile.NamedTemporaryFile(prefix="restore-", suffix=".zip", dir=PERSISTENT_BACKUPS_DIR, delete=False)
    temp_path = temp_handle.name
    temp_handle.close()
    try:
        uploaded.save(temp_path)
        result = restore_editorial_backup(temp_path)
        return jsonify({"success": True, **result})
    except PersistentDataError as exc:
        return jsonify({"error": str(exc)}), 400
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


# ─── Page Routes ───

@app.route("/")
def index():
    return render_template("index.html")


# ─── API: Settings ───

def _sync_env_key_to_db():
    """On startup, sync GEMINI_API_KEY from .env to DB if not already set."""
    env_key = os.environ.get("GEMINI_API_KEY", "")
    if env_key and len(env_key) > 10:
        db_key = get_setting("gemini_api_key")
        if not db_key:
            set_setting("gemini_api_key", env_key)


@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    settings = get_all_settings()
    for key in ("gemini_api_key", "claude_api_key"):
        configured = bool(settings.get(key))
        settings[key] = ""
        settings[f"{key}_configured"] = configured
    settings["program_version"] = PROGRAM_VERSION
    settings["program_revision"] = PROGRAM_REVISION
    return jsonify(settings)


@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    data = request.get_json(silent=True) or {}
    allowed_keys = set(get_all_settings().keys())
    for key, value in data.items():
        if key in allowed_keys and key not in {"gemini_api_key", "claude_api_key"}:
            set_setting(key, value)

    # Save Gemini key to .env AND os.environ for immediate use
    gemini_key = str(data.get("gemini_api_key", "") or "").strip()
    if gemini_key:
        set_setting("gemini_api_key", gemini_key)
        _save_key_to_env("GEMINI_API_KEY", gemini_key)
        os.environ["GEMINI_API_KEY"] = gemini_key
        print(f"[Settings] Gemini API key salva (tamanho: {len(gemini_key)} chars)")

    claude_key = str(data.get("claude_api_key", "") or "").strip()
    if claude_key:
        set_setting("claude_api_key", claude_key)
        _save_key_to_env("ANTHROPIC_API_KEY", claude_key)
        os.environ["ANTHROPIC_API_KEY"] = claude_key
        print(f"[Settings] Claude API key salva (tamanho: {len(claude_key)} chars)")

    ai_backend = data.get("ai_backend", "")
    if ai_backend:
        print(f"[Settings] Motor de IA: {ai_backend}")

    return jsonify({"success": True})


def _save_key_to_env(key_name, key_value):
    """Save an API key outside the checkout so it survives upgrades."""
    env_file = os.environ.get("FURIA_CLIPS_ENV_FILE") or os.path.join(
        PERSISTENT_DATA_DIR, "config", "local.env"
    )
    os.makedirs(os.path.dirname(env_file), exist_ok=True)
    lines = []
    found = False

    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                if line.strip().startswith(f"{key_name}="):
                    lines.append(f"{key_name}={key_value}\n")
                    found = True
                else:
                    lines.append(line)

    if not found:
        lines.append(f"{key_name}={key_value}\n")

    with open(env_file, "w") as f:
        f.writelines(lines)


# ─── API: File Manager ───

@app.route("/api/files", methods=["GET"])
def api_list_files():
    path = request.args.get("path", "")
    base = WORKSPACE_DIR
    try:
        target = safe_workspace_path(base, path, allow_missing=False)
    except (UnsafePathError, FileNotFoundError):
        return jsonify({"error": "Acesso negado"}), 403

    items = []
    if os.path.isdir(target):
        for name in sorted(os.listdir(target)):
            full = os.path.join(target, name)
            rel = os.path.relpath(full, base)
            is_dir = os.path.isdir(full)
            size = os.path.getsize(full) if not is_dir else 0
            ext = os.path.splitext(name)[1].lower() if not is_dir else ""
            items.append({
                "name": name,
                "path": rel,
                "is_dir": is_dir,
                "size": size,
                "size_human": _human_size(size),
                "extension": ext,
                "is_video": ext in ALLOWED_EXTENSIONS,
                "modified": datetime.fromtimestamp(os.path.getmtime(full)).isoformat(),
            })

    return jsonify({
        "current_path": os.path.relpath(target, base) if target != base else "",
        "items": items,
    })


@app.route("/api/files/upload", methods=["POST"])
def api_upload_file():
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nome de arquivo vazio"}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"Formato nao suportado: {ext}"}), 400

    dest_dir = request.form.get("path", "uploads")
    try:
        dest_path = safe_workspace_path(WORKSPACE_DIR, dest_dir, allow_missing=True)
    except UnsafePathError:
        return jsonify({"error": "Pasta de destino inválida"}), 403
    os.makedirs(dest_path, exist_ok=True)

    filename = unique_storage_name(file.filename, extension=ext)
    filepath = os.path.join(dest_path, filename)
    file.save(filepath)

    return jsonify({
        "success": True,
        "filename": filename,
        "path": os.path.relpath(filepath, WORKSPACE_DIR),
        "size": os.path.getsize(filepath),
    })


@app.route("/api/files/mkdir", methods=["POST"])
def api_mkdir():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    parent = data.get("parent", "")

    if not name:
        return jsonify({"error": "Nome da pasta nao informado"}), 400

    try:
        parent_path = safe_workspace_path(WORKSPACE_DIR, parent, allow_missing=True)
        target = safe_workspace_path(
            WORKSPACE_DIR,
            os.path.join(os.path.relpath(parent_path, WORKSPACE_DIR), name),
            allow_missing=True,
        )
    except UnsafePathError:
        return jsonify({"error": "Acesso negado"}), 403

    os.makedirs(target, exist_ok=True)
    return jsonify({"success": True, "path": os.path.relpath(target, WORKSPACE_DIR)})


@app.route("/api/dialog/choose", methods=["POST"])
def api_choose_dialog():
    """Open a native file/folder picker after an explicit user action."""
    data = request.get_json(silent=True) or {}
    mode = str(data.get("mode", "folder")).strip().lower()
    if mode not in {"folder", "file"}:
        return jsonify({"error": "Modo de diálogo inválido"}), 400
    try:
        selected = choose_path(
            mode=mode,
            initial_path=data.get("initial_path"),
            title=str(data.get("title", "Selecionar"))[:120],
        )
    except (DialogError, OSError, subprocess.SubprocessError) as exc:
        return jsonify({"error": str(exc)}), 500
    if not selected:
        return jsonify({"success": False, "cancelled": True, "path": ""})
    return jsonify({"success": True, "cancelled": False, "path": os.path.abspath(selected)})


@app.route("/api/files/delete", methods=["POST"])
def api_delete_file():
    data = request.get_json(silent=True) or {}
    path = data.get("path", "")
    try:
        target = safe_workspace_path(WORKSPACE_DIR, path, allow_missing=False)
    except (UnsafePathError, FileNotFoundError):
        return jsonify({"error": "Acesso negado"}), 403

    if target == os.path.realpath(WORKSPACE_DIR):
        return jsonify({"error": "Acesso negado"}), 403

    if os.path.isdir(target):
        shutil.rmtree(target)
    elif os.path.isfile(target):
        os.unlink(target)
    else:
        return jsonify({"error": "Arquivo nao encontrado"}), 404

    return jsonify({"success": True})


@app.route("/api/source/probe", methods=["POST"])
def api_source_probe():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify({"success": True, "source": probe_public_url(data.get("url", ""))})
    except SourceIngestError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


def _format_source_import_progress(update):
    """Present yt-dlp multi-stream progress without implying a single global percent."""
    status = update.get("status")
    stream = str(update.get("stream") or "mídia")
    if status == "downloading" and update.get("percent") is not None:
        return f"[Download · {stream}] {float(update['percent']):.1f}%"
    if status == "stream_finished":
        return f"[Download · {stream}] transferência concluída; preparando a próxima etapa..."
    if status == "retry":
        return f"[Download] nova tentativa {update.get('attempt')}/{update.get('max_attempts')}..."
    if status == "merging":
        return "[Download] Unindo vídeo e áudio no arquivo MP4 final..."
    if status == "merge_finished":
        return "[Download] Arquivo final pronto; conferindo a mídia..."
    return "[Download] Preparando arquivo final..."


@app.route("/api/source/import", methods=["POST"])
def api_source_import():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url", "")).strip()
    settings = get_all_settings()
    try:
        url = validate_public_url(url)
        destination = _resolve_source_destination(data.get("destination_dir"), settings)
    except (SourceIngestError, OSError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    with processing_lock:
        if current_task["active"]:
            return jsonify({"error": "Já existe um processamento em andamento"}), 409
        _set_legacy_task("source_import", active=True)

    max_height = data.get("max_height", settings.get("source_max_height", 1080))
    auto_transcribe = bool(data.get("auto_transcribe", True))
    set_setting("source_download_dir", destination)
    set_setting("source_max_height", max_height)

    def task():
        try:
            check_current_task_cancel()
            emit_progress("[Fonte] Preparando download de URL pública...", "info")
            result = download_public_video(
                url,
                destination,
                max_height=max_height,
                retries=settings.get("source_download_retries", 3),
                cancel_check=check_current_task_cancel,
                progress=lambda update: emit_progress(_format_source_import_progress(update), "info"),
            )
            result_path = os.path.abspath(result["path"])
            display_path = os.path.relpath(result_path, WORKSPACE_DIR) if _is_under(result_path, WORKSPACE_DIR) else result_path
            project_id = create_project(result.get("title") or os.path.basename(result_path), result_path)
            transcription = None
            subtitle_path = None
            transcript_archive = None
            transcript_files = {}
            manual_payload = data.get("manual_transcript")
            manual_segments = manual_payload.get("segments") if isinstance(manual_payload, dict) else data.get("transcript_segments")
            manual_language = (
                manual_payload.get("language", "pt")
                if isinstance(manual_payload, dict)
                else data.get("transcript_language", "pt")
            )
            if isinstance(manual_segments, list) and manual_segments:
                transcription = normalize_segment_payload(manual_segments, duration=result.get("duration"))
                transcription["language"] = manual_language or "pt"
                transcription["source"] = "manual_confirmed"
                transcript_source = "manual_confirmed"
                emit_progress(
                    f"[Transcrição manual] {transcription.get('segment_count', len(transcription.get('segments', [])))} segmentos confirmados; busca pública, Gemini e Whisper foram ignorados.",
                    "success",
                )
                transcript_files = _save_transcription_artifacts(result_path, transcription)
                transcript_archive = archive_transcription(
                    transcription,
                    source_video=result_path,
                    source=transcript_source,
                    source_artifact="manual-confirmed",
                    project_id=project_id,
                    duration=result.get("duration"),
                    archive_name=result.get("title") or os.path.basename(result_path),
                )
                save_transcription(
                    project_id,
                    transcription.get("segments", []),
                    transcription.get("full_text", ""),
                    transcription.get("language", "pt"),
                    transcript_source,
                )
                transcription["quality"] = transcript_archive.get("quality", {})
                transcription["archive"] = transcript_archive
                transcript_files = {**transcript_files, "archive": transcript_archive}
            elif auto_transcribe:
                transcription_mode = _transcription_source_mode({
                    **settings,
                    "transcription_source": data.get("transcription_source", settings.get("transcription_source", "auto")),
                })
                transcription_settings = {**settings, "transcription_source": transcription_mode}
                if transcription_mode != "whisper":
                    emit_progress("[Transcrição] Procurando legenda pública timestampada para a opção escolhida...", "info")
                    subtitle_path = download_public_subtitles(url, destination, cancel_check=check_current_task_cancel)
                    if subtitle_path:
                        emit_progress(f"[Transcrição] Legenda pública encontrada: {os.path.basename(subtitle_path)}", "success")
                else:
                    emit_progress("[Transcrição] Whisper local foi selecionado; a busca de legenda pública foi ignorada.", "info")
                emit_progress("[Transcrição] Gerando timestamps automaticamente antes da análise...", "info")
                try:
                    transcription = _transcribe_video_automatically(
                        result_path,
                        transcription_settings,
                        emit_progress,
                        transcript_fallback_path=subtitle_path,
                        cancel_check=check_current_task_cancel,
                    )
                    transcript_files = _save_transcription_artifacts(result_path, transcription)
                    transcript_source = "public_subtitle" if subtitle_path else str(transcription.get("source", "automatic"))
                    transcript_archive = archive_transcription(
                        transcription,
                        source_video=result_path,
                        source=transcript_source,
                        source_artifact=subtitle_path or "",
                        project_id=project_id,
                        duration=result.get("duration"),
                        archive_name=result.get("title") or os.path.basename(result_path),
                    )
                    save_transcription(
                        project_id,
                        transcription.get("segments", []),
                        transcription.get("full_text", ""),
                        transcription.get("language", "pt"),
                        transcript_source,
                    )
                    transcription["quality"] = transcript_archive.get("quality", {})
                    transcription["archive"] = transcript_archive
                    transcript_files = {**transcript_files, "archive": transcript_archive}
                    emit_progress(
                        f"[Transcrição] {transcription.get('segment_count', len(transcription.get('segments', [])))} segmentos prontos; arquivo persistente salvo para validação.",
                        "success",
                    )
                except Exception as transcript_exc:
                    transcript_files = {}
                    emit_progress(f"[Transcrição] Falha na geração automática; o vídeo continua disponível: {str(transcript_exc)[:220]}", "warning")

            event_data = {
                **result,
                "path": display_path,
                "absolute_path": result_path,
                "destination_dir": destination,
                "transcription": transcription,
                "transcription_files": transcript_files,
                "transcription_archive": transcript_archive,
                "project_id": project_id,
                "subtitle_path": subtitle_path,
                "auto_transcribe": auto_transcribe,
            }
            check_current_task_cancel()
            emit_status("source_import_complete", event_data)
            emit_progress(f"[Fonte] Vídeo importado em {display_path}", "success")
        except OperationCancelled as exc:
            emit_progress(f"[Fonte] Operação cancelada: {exc}", "warning")
            emit_status("cancelled", {"operation": "source_import", "message": str(exc)})
        except Exception as exc:
            emit_progress(f"[Fonte] Falha ao importar link: {str(exc)}", "error")
            emit_status("error", {"message": str(exc)})
        finally:
            _set_legacy_task("", active=False)

    threading.Thread(target=task, daemon=True).start()
    manual_requested = isinstance(data.get("manual_transcript"), dict) or bool(data.get("transcript_segments"))
    if manual_requested:
        message = "Download iniciado; a transcrição manual confirmada será reutilizada."
    elif auto_transcribe:
        message = "Download e transcrição da fonte iniciados."
    else:
        message = "Download da fonte iniciado sem transcrição."
    return jsonify({"success": True, "message": message, "destination_dir": destination})


@app.route("/api/source/transcribe", methods=["POST"])
def api_source_transcribe():
    """Download a public source and create a transcript without generating clips."""
    data = request.get_json(silent=True) or {}
    settings = get_all_settings()
    try:
        url = validate_public_url(data.get("url", ""))
        destination = _resolve_source_destination(data.get("destination_dir"), settings)
    except (SourceIngestError, OSError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 400

    media_type = str(data.get("media_type", "audio") or "audio").strip().lower()
    if media_type not in {"audio", "video"}:
        media_type = "audio"
    try:
        max_height = max(144, min(int(data.get("max_height", settings.get("source_max_height", 1080)) or 1080), 1080))
    except (TypeError, ValueError):
        max_height = 1080
    transcription_mode = _transcription_source_mode({
        **settings,
        "transcription_source": data.get("transcription_source", settings.get("transcription_source", "auto")),
    })
    transcription_settings = {**settings, "transcription_source": transcription_mode}
    set_setting("source_download_dir", destination)
    set_setting("source_max_height", max_height)

    def task(ctx):
        def job_message(message, level="info", stage=None, progress=None):
            emit_progress(message, level)
            if stage is not None or progress is not None:
                ctx.update(stage=stage, progress=progress, message=str(message)[:500])

        try:
            ctx.check_cancel()
            job_message("[Transcrição por URL] Preparando download da fonte pública...", "info", "downloading", 2)
            download_progress_state = {"last_bucket": -1}

            def on_download_progress(update):
                message = _format_source_import_progress(update)
                emit_progress(message, "info")
                percent = update.get("percent")
                if percent is None:
                    return
                try:
                    bucket = int(float(percent) // 5)
                except (TypeError, ValueError):
                    return
                if bucket <= download_progress_state["last_bucket"]:
                    return
                download_progress_state["last_bucket"] = bucket
                ctx.update(
                    stage="downloading",
                    progress=min(35, 5 + bucket * 2),
                    message=message[:500],
                )

            if media_type == "audio":
                result = download_public_audio(
                    url,
                    destination,
                    retries=settings.get("source_download_retries", 3),
                    cancel_check=ctx.check_cancel,
                    progress=on_download_progress,
                )
            else:
                result = download_public_video(
                    url,
                    destination,
                    max_height=max_height,
                    retries=settings.get("source_download_retries", 3),
                    cancel_check=ctx.check_cancel,
                    progress=on_download_progress,
                )
            result_path = os.path.abspath(result["path"])
            source_duration = result.get("duration") or _probe_video_duration_seconds(result_path)
            display_path = os.path.relpath(result_path, WORKSPACE_DIR) if _is_under(result_path, WORKSPACE_DIR) else result_path
            ctx.update(stage="downloaded", progress=38, message=f"Fonte {media_type} baixada e validada; preparando transcrição")
            emit_progress(f"[Transcrição por URL] Fonte validada: {display_path}", "success")
            ctx.check_cancel()

            subtitle_path = None
            if transcription_mode != "whisper":
                ctx.update(stage="public_subtitles", progress=42, message="Procurando legenda pública timestampada")
                emit_progress("[Transcrição por URL] Procurando legenda pública timestampada...", "info")
                subtitle_path = download_public_subtitles(
                    url,
                    destination,
                    cancel_check=ctx.check_cancel,
                )
                if subtitle_path:
                    emit_progress(f"[Transcrição por URL] Legenda pública encontrada: {os.path.basename(subtitle_path)}", "success")
                else:
                    emit_progress("[Transcrição por URL] Nenhuma legenda pública válida encontrada; seguindo para o motor configurado.", "warning")
            else:
                emit_progress("[Transcrição por URL] Whisper local forçado; busca de legenda pública ignorada.", "info")

            ctx.update(stage="transcribing", progress=48, message="Gerando transcrição timestampada sem gerar cortes")
            transcription = _transcribe_video_automatically(
                result_path,
                transcription_settings,
                lambda message, level="info": job_message(message, level, "transcribing", 52),
                transcript_fallback_path=subtitle_path,
                cancel_check=ctx.check_cancel,
            )
            if not isinstance(transcription, dict) or not transcription.get("segments"):
                raise SourceIngestError("A fonte foi baixada, mas não produziu segmentos timestampados.")

            transcription["source_url"] = url
            transcription["source_video"] = display_path
            transcription["source_duration_seconds"] = source_duration
            transcription["coverage"] = _transcription_coverage_report(transcription, source_duration)
            transcript_files = _save_transcription_artifacts(result_path, transcription)
            transcript_source = "public_subtitle" if subtitle_path else str(transcription.get("source", "automatic"))
            transcript_archive = archive_transcription(
                transcription,
                source_video=result_path,
                source=transcript_source,
                source_artifact=subtitle_path or "",
                project_id=None,
                duration=source_duration,
                archive_name=result.get("title") or os.path.basename(result_path),
            )
            transcription["quality"] = transcript_archive.get("quality", {})
            transcription["archive"] = transcript_archive
            transcription["transcription_files"] = transcript_files
            ctx.check_cancel()

            artifacts = [{
                "type": "transcription",
                "source_url": url,
                "source_video": display_path,
                "archive_dir": transcript_archive.get("relative_dir"),
                "quality": transcript_archive.get("quality", {}),
                "coverage": transcription.get("coverage", {}),
            }]
            event_data = {
                "job_id": ctx.job_id,
                "url": url,
                "source": {
                    **result,
                    "path": display_path,
                    "absolute_path": result_path,
                    "destination_dir": destination,
                },
                "transcription": transcription,
                "transcription_files": transcript_files,
                "transcription_archive": transcript_archive,
                "coverage": transcription.get("coverage", {}),
                "quality": transcript_archive.get("quality", {}),
                "mode": transcription_mode,
                "media_type": media_type,
            }
            ctx.update(stage="completed", progress=100, message="Transcrição por URL concluída", artifacts=artifacts)
            socketio.emit("source_transcription_complete", event_data)
            emit_status("source_transcription_complete", event_data)
            emit_progress(
                f"[Transcrição por URL] Concluída: {transcription.get('segment_count', len(transcription.get('segments', [])))} segmentos; nenhum corte foi gerado.",
                "success",
            )
            return {"artifacts": artifacts}
        except (JobCancelled, OperationCancelled):
            emit_progress("[Transcrição por URL] Operação cancelada com segurança.", "warning")
            raise
        except Exception as exc:
            emit_progress(f"[Transcrição por URL] Falha: {str(exc)[:240]}", "error")
            raise

    with processing_lock:
        if current_task["active"]:
            return jsonify({"error": ERROR_MESSAGES["processing_active"]}), 409
        job = job_manager.submit("source_transcription", task)
    return jsonify({
        "success": True,
        "message": "Transcrição por URL iniciada sem gerar cortes",
        "job_id": job["id"],
        "state": job["state"],
        "source_url": url,
        "destination_dir": destination,
        "transcription_source": transcription_mode,
        "media_type": media_type,
    })


@app.route("/api/transcript/parse", methods=["POST"])
def api_parse_transcript():
    data = request.get_json(silent=True) or {}
    try:
        duration = data.get("duration")
        if not duration and data.get("video_path"):
            resolved_video = _resolve_media_input(data.get("video_path"))
            if resolved_video and os.path.exists(resolved_video):
                duration = _probe_video_duration_seconds(resolved_video)
        result = parse_transcript_text(data.get("text", ""), duration=duration)
        result["language"] = data.get("language", "pt")
        return jsonify({"success": True, "transcription": result})
    except (TypeError, ValueError) as exc:
        return jsonify({"success": False, "error": str(exc)}), 400


@app.route("/api/transcript/parse-file", methods=["POST"])
def api_parse_transcript_file():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"success": False, "error": "Nenhum arquivo de transcrição enviado"}), 400
    try:
        text = uploaded.read().decode("utf-8-sig")
        result = parse_transcript_text(text, duration=request.form.get("duration"))
        result["language"] = request.form.get("language", "pt")
        return jsonify({"success": True, "transcription": result})
    except (UnicodeDecodeError, TypeError, ValueError) as exc:
        return jsonify({"success": False, "error": f"Transcrição inválida: {exc}"}), 400


@app.route("/workspace/<path:filepath>")
def serve_workspace_file(filepath):
    try:
        full = safe_workspace_path(WORKSPACE_DIR, filepath, allow_missing=False)
    except (UnsafePathError, FileNotFoundError):
        return "Acesso negado", 403
    if not os.path.isfile(full):
        return "Arquivo não encontrado", 404
    directory = os.path.dirname(full)
    filename = os.path.basename(full)
    return send_from_directory(directory, filename)


# ─── API: Projects ───

@app.route("/api/projects", methods=["GET"])
def api_list_projects():
    return jsonify(get_all_projects())


@app.route("/api/projects/<int:project_id>", methods=["GET"])
def api_get_project(project_id):
    project = get_project(project_id)
    if not project:
        return jsonify({"error": "Projeto nao encontrado"}), 404
    project["clips"] = get_clips(project_id)
    project["transcription"] = get_transcription(project_id)
    return jsonify(project)


# ─── API: Processing Actions ───

@app.route("/api/process/silence", methods=["POST"])
def api_remove_silence():
    data = request.get_json(silent=True) or {}
    video_path = _resolve_media_input(data.get("video_path", ""))
    if not video_path:
        return jsonify({"error": "Video não encontrado ou caminho inválido"}), 404

    if not os.path.exists(video_path):
        return jsonify({"error": "Video nao encontrado"}), 404

    def task():
        current_task["active"] = True
        try:
            from modules.silence_remover import SilenceRemover
            settings = get_all_settings()
            remover = SilenceRemover(
                silence_threshold=settings.get("silence_threshold", -35),
                min_silence_duration=settings.get("min_silence_duration", 0.5),
                padding=settings.get("padding", 0.25),
            )
            result = remover.remove_silence(video_path, emit_progress=emit_progress)
            if result:
                emit_status("silence_complete", result)
                emit_progress("Remocao de silencio concluida!", "success")
            else:
                emit_status("error", {"message": "Falha ao remover silencio"})
                emit_progress("Erro na remocao de silencio", "error")
        except Exception as e:
            emit_progress(f"Erro: {str(e)}", "error")
            emit_status("error", {"message": str(e)})
        finally:
            current_task["active"] = False

    if current_task["active"]:
        return jsonify({"error": "Ja existe um processamento em andamento"}), 409

    threading.Thread(target=task, daemon=True).start()
    return jsonify({"success": True, "message": "Remocao de silencio iniciada"})


@app.route("/api/process/transcribe", methods=["POST"])
def api_transcribe():
    data = request.get_json(silent=True) or {}
    video_path = _resolve_media_input(data.get("video_path", ""))
    if not video_path:
        return jsonify({"error": "Video não encontrado ou caminho inválido"}), 404
    project_id = data.get("project_id")

    if not os.path.exists(video_path):
        return jsonify({"error": "Video nao encontrado"}), 404

    def task():
        try:
            check_current_task_cancel()
            settings = get_all_settings()
            settings = {**settings, "transcription_source": data.get("transcription_source", settings.get("transcription_source", "auto"))}
            result = _transcription_from_request(data)
            if result:
                emit_progress(f"[Transcrição manual] {result['segment_count']} segmentos importados; Whisper não será executado.", "success")
            else:
                result = _transcribe_video_automatically(
                    video_path,
                    settings,
                    emit_progress,
                    cancel_check=check_current_task_cancel,
                )

            if project_id:
                save_transcription(
                    project_id, result["segments"], result["full_text"],
                    result["language"], result.get("source", settings.get("whisper_model", "small"))
                )

            check_current_task_cancel()
            emit_status("transcribe_complete", result)
            emit_progress("Transcricao concluida!", "success")
        except OperationCancelled as exc:
            emit_progress(f"[Transcrição] Operação cancelada: {exc}", "warning")
            emit_status("cancelled", {"operation": "transcription", "message": str(exc)})
        except Exception as e:
            emit_progress(f"Erro na transcricao: {str(e)}", "error")
            emit_status("error", {"message": str(e)})
        finally:
            _set_legacy_task("", active=False)

    with processing_lock:
        if current_task["active"]:
            return jsonify({"error": "Ja existe um processamento em andamento"}), 409
        _set_legacy_task("transcription", active=True)

    threading.Thread(target=task, daemon=True).start()
    return jsonify({"success": True, "message": "Transcricao iniciada"})


@app.route("/api/process/cut", methods=["POST"])
def api_cut_shorts():
    data = request.get_json(silent=True) or {}
    video_path = _resolve_media_input(data.get("video_path", ""))
    if not video_path:
        return jsonify({"error": "Video não encontrado ou caminho inválido"}), 404
    project_id = data.get("project_id")
    use_face_tracking = _coerce_bool(data.get("face_tracking"), default=True)
    transcription_source = data.get("transcription_source")
    user_context = str(data.get("user_context", "") or "").strip()
    video_genre = data.get("video_genre", "")
    audit_mode = str(data.get("audit_mode", "standard") or "standard").strip().lower()
    if audit_mode not in {"fast", "standard", "full"}:
        audit_mode = "standard"
    preferred_format = str(data.get("preferred_format", "auto") or "auto").strip().lower()
    if preferred_format not in {"auto", "vertical_916", "square_alfinetei", "fake_tweet"}:
        preferred_format = "auto"

    if not os.path.exists(video_path):
        return jsonify({"error": "Video nao encontrado"}), 404

    def task(ctx):
        try:
            ctx.update(stage="transcription", progress=5, message="Preparando transcrição e contexto")
            ctx.check_cancel()
            settings = get_all_settings()
            if transcription_source:
                settings = {**settings, "transcription_source": transcription_source}
            active_project_id = project_id
            if not active_project_id:
                auto_project_name = os.path.splitext(os.path.basename(video_path))[0]
                active_project_id = create_project(auto_project_name, data.get("video_path", video_path))
                emit_progress("[Projeto] Sessão de revisão criada automaticamente para salvar seus feedbacks.", "info")

            # Check AI status before starting
            ai_backend = settings.get("ai_backend", "gemini")
            ai_status = _check_ai_status(settings)
            emit_progress(f"[Modo] {ai_status['mode_label']}", "info")
            socketio.emit("ai_status", ai_status)

            # Context confirmation
            if user_context:
                emit_progress(f'[Contexto] Prompt do usuario: "{user_context[:100]}..."' if len(user_context) > 100 else f'[Contexto] Prompt do usuario: "{user_context}"', "info")
            else:
                emit_progress("[Contexto] Nenhum prompt manual; o Furia vai analisar transcrição, perguntas, capítulos, áudio e sinais visuais antes de selecionar.", "info")

            # Step 1: Transcribe or import the canonical manual transcript
            emit_progress("=== ETAPA 1/5: Transcricao e contexto ===", "info")
            from modules.transcriber import Transcriber
            video_duration = _probe_video_duration_seconds(video_path)
            manual_supplied = _manual_transcript_was_supplied(data)
            transcription = _transcription_from_request(data, duration=video_duration)
            multimodal_result = None
            selected_transcription_mode = _transcription_source_mode(settings)
            if not transcription and selected_transcription_mode in {"whisper", "public_subtitle"}:
                transcription = _transcribe_video_automatically(
                    video_path,
                    settings,
                    emit_progress,
                    cancel_check=ctx.check_cancel,
                )
            elif not transcription:
                multimodal_result = _run_gemini_video_analysis(
                    video_path,
                    settings,
                    {},
                    user_context,
                    emit_progress,
                    cancel_check=ctx.check_cancel,
                )
                transcription = _transcription_from_gemini_result(multimodal_result, settings.get("language", "pt"))
            if not transcription:
                transcriber = Transcriber(
                    model_name=settings.get("whisper_model", "small"),
                    language=settings.get("language", "pt"),
                    word_timestamps=settings.get("whisper_word_timestamps", True),
                    beam_size=settings.get("whisper_beam_size", 5),
                    device=settings.get("whisper_device", "auto"),
                )
                transcription = transcriber.transcribe(
                    video_path,
                    emit_progress=emit_progress,
                    cancel_check=ctx.check_cancel,
                )
                emit_progress(f"[Whisper] Motor: {transcriber._engine}", "info")

            if transcription:
                coverage = _transcription_coverage_report(transcription, video_duration)
                transcription["coverage"] = coverage
                if coverage["status"] == "mismatch_suspected" and transcription.get("source") in {"manual", "manual_confirmed"}:
                    raise ValueError(
                        "A transcrição manual contém timestamps além da duração do vídeo selecionado. "
                        "Ela provavelmente pertence a outro vídeo; selecione a mídia correta ou importe a legenda correspondente."
                    )
                if coverage["status"] == "partial":
                    emit_progress(
                        f"[Transcrição] Cobertura parcial: termina em {coverage['last_timestamp']:.1f}s de {coverage['video_duration_seconds']:.1f}s; "
                        "os cortes ficarão limitados ao trecho importado.",
                        "warning",
                    )
                transcription["provenance"] = _transcription_provenance(transcription, manual_supplied=manual_supplied)
                settings["transcription_provenance"] = transcription["provenance"]

                source = str(transcription.get("source", "") or "").lower()
                if source in {"manual", "manual_confirmed"}:
                    emit_progress(f"[Transcrição manual] {transcription['segment_count']} segmentos importados; Whisper não será executado.", "success")
                elif source == "gemini_video":
                    emit_progress(f"[Gemini] {transcription['segment_count']} segmentos obtidos da análise multimodal; Whisper não será executado.", "success")
                else:
                    emit_progress(f"[Transcrição canônica] {transcription['segment_count']} segmentos serão usados no contexto e na seleção.", "success")

            full_transcription = transcription
            source_boundary = detect_live_content_start(
                full_transcription,
                duration_seconds=video_duration,
                manual_start_seconds=data.get("content_start_seconds"),
            )
            selection_transcription = trim_transcription_to_live_start(full_transcription, source_boundary)
            # Keep temporal validation/provenance on the live-only view. Without
            # this, the context analyzer sees a new dict with no coverage and
            # marks every otherwise valid candidate as technically unverified.
            selection_transcription["coverage"] = dict(full_transcription.get("coverage") or {})
            selection_transcription["provenance"] = dict(full_transcription.get("provenance") or {})
            selection_transcription["source"] = full_transcription.get("source", "")
            settings["source_boundary"] = source_boundary
            if source_boundary.get("status") in {"detected", "manual"} and source_boundary.get("content_start_seconds", 0) > 0:
                emit_progress(
                    f"[Fonte] Conteúdo de live começa em {source_boundary['content_start_seconds']:.1f}s; "
                    "o pré-roll permanece arquivado, mas não entra na seleção.",
                    "info",
                )
            else:
                emit_progress("[Fonte] Nenhuma fronteira segura de pré-roll foi detectada; seleção usa a timeline completa.", "info")

            save_transcription(
                active_project_id, full_transcription["segments"], full_transcription["full_text"],
                full_transcription["language"], full_transcription.get("source", settings.get("whisper_model", "small"))
            )
            save_transcription_bundle(
                full_transcription,
                project_id=active_project_id,
                source_video=video_path,
                selection_transcription=selection_transcription,
            )

            from modules.editorial_context import analyze_transcript_context
            from modules.campaign_hub import load_snapshot
            campaign_hub_snapshot = load_snapshot(settings.get("campaign_hub_snapshot_path"))
            campaign_hub_account = str(
                settings.get("campaign_hub_account")
                or (campaign_hub_snapshot or {}).get("default_account", "@renansantosmbl")
            )
            editorial_context = analyze_transcript_context(
                selection_transcription,
                focus=settings.get("editorial_focus", "auto"),
                campaign_hub_snapshot=campaign_hub_snapshot,
                campaign_hub_account=campaign_hub_account,
            )
            editorial_context["transcription_provenance"] = transcription.get("provenance", {})
            editorial_context["transcript_reference"] = _transcript_reference_for_multimodal(selection_transcription)
            emit_progress(
                f"[Contexto editorial] {editorial_context['description']} | fonte temporal: {transcription.get('source', 'desconhecida')}; "
                f"{transcription.get('segment_count', len(transcription.get('segments', [])))} segmentos canônicos.",
                "info",
            )
            # A transcrição pública/manual/Whisper já resolveu a etapa temporal;
            # uma segunda análise multimodal só ocorre por opção explícita.
            allow_followup_video_analysis = _should_allow_followup_video_analysis(selection_transcription, settings)
            editorial_context = _enrich_editorial_context(
                video_path, settings, editorial_context, user_context, emit_progress,
                multimodal=multimodal_result,
                allow_video_analysis=allow_followup_video_analysis,
            )
            settings["editorial_context"] = editorial_context
            # The authorized snapshot stays in memory for this job; selection must
            # remain offline-first rather than calling MCP once per candidate.
            settings["campaign_hub_snapshot"] = campaign_hub_snapshot
            settings["campaign_hub_account"] = campaign_hub_account
            # Measured from the file on disk. Without it the guidance layer can
            # only trust the duration declared in the snapshot, which describes
            # the long source and leaves the seeds of a downloaded block in
            # absolute seconds while the local transcript starts at zero.
            settings["media_duration"] = video_duration
            settings["audit_mode"] = audit_mode
            settings["preferred_format"] = preferred_format
            settings["selection_transcription"] = selection_transcription
            editorial_audit = None
            if audit_mode in {"standard", "full"}:
                try:
                    from modules.headline_studio import generate_artwork_copy
                    editorial_audit = generate_artwork_copy(
                        selection_transcription.get("full_text", ""),
                        mini_context=user_context,
                        preferred_format=preferred_format,
                        ai_backend=None,
                        emit_progress=None,
                        editorial_learning=get_headline_learning_preferences(),
                    )
                    emit_progress(
                        f"[Auditoria editorial] Formato recomendado: {editorial_audit.get('recommended_format', 'auto')}; "
                        f"completude {editorial_audit.get('analysis', {}).get('context_completeness', 0)}/100.",
                        "info",
                    )
                    if audit_mode == "full":
                        flags = editorial_audit.get("review_flags", {})
                        if flags.get("needs_fact_review") or flags.get("needs_legal_review"):
                            emit_progress("[Auditoria editorial] Há alegações que exigem revisão factual/jurídica humana antes da publicação.", "warning")
                except Exception as exc:
                    emit_progress(f"[Auditoria editorial] Não concluída; o ranking principal continua ativo: {str(exc)[:160]}", "warning")

            ctx.update(stage="video_analysis", progress=28, message="Analisando layout e cenas")
            ctx.check_cancel()

            # Step 2: Layout detection + Scene detection
            emit_progress("=== ETAPA 2/5: Analise de Video ===", "info")
            video_layout = "unknown"
            scene_changes = None
            tracker = None

            try:
                from modules.face_tracker import FaceTracker
                tracker = FaceTracker()
                video_layout = tracker.detect_layout(
                    video_path, emit_progress=emit_progress,
                    video_genre=video_genre if video_genre else None
                )
            except Exception as e:
                emit_progress(f"Deteccao de layout indisponivel: {str(e)}", "warning")
            finally:
                if tracker is not None:
                    tracker.close()

            # Scene change detection
            try:
                from modules.video_cutter import VideoCutter as SceneDetector
                scene_det = SceneDetector()
                scene_changes = scene_det.detect_scenes(video_path, emit_progress=emit_progress)
            except Exception as e:
                emit_progress(f"Deteccao de cena indisponivel: {str(e)}", "warning")

            ctx.update(stage="candidate_generation", progress=48, message="Gerando candidatos editoriais")
            ctx.check_cancel()

            # Step 3: Intelligent clip selection
            emit_progress("=== ETAPA 3/5: Selecao Inteligente de Clips ===", "info")
            from modules.clip_selector import ClipSelector
            from modules.audio_analyzer import AudioAnalyzer

            analyzer = AudioAnalyzer()
            energy_profile = _analyze_energy_with_cancel(analyzer, video_path, emit_progress, ctx.check_cancel)
            try:
                from modules.editorial_context import detect_hook_candidates
                context_snapshot = settings.get("campaign_hub_snapshot")
                settings.setdefault("editorial_context", {})["hook_candidates"] = detect_hook_candidates(
                    selection_transcription.get("segments", []),
                    snapshot=context_snapshot,
                    account=settings.get("campaign_hub_account", "@renansantosmbl"),
                    energy_profile=energy_profile,
                )
            except Exception as exc:
                emit_progress(f"[Contexto] Hooks com áudio não disponíveis; mantendo sinais textuais: {str(exc)[:140]}", "warning")

            coverage_plan = _selection_coverage_plan(data.get("video_path", video_path), video_duration)
            if coverage_plan["previous_clip_fingerprints"]:
                emit_progress(
                    f"[Deduplicação] {len(coverage_plan['previous_clip_fingerprints'])} intervalos já gerados para esta fonte serão evitados.",
                    "info",
                )
            settings.update(coverage_plan)
            emit_progress(
                f"[Cobertura] Até {coverage_plan['adaptive_max_clips']} candidatos nesta execução; "
                "qualidade, contexto e diversidade continuam prioritários.",
                "info",
            )
            selector = ClipSelector(
                target_duration=settings.get("cut_duration", 45),
                max_clips=coverage_plan["adaptive_max_clips"],
                min_duration=20,
                max_duration=180,
            )
            top_clips = selector.select_clips(
                selection_transcription,
                energy_profile=energy_profile,
                user_context=user_context,
                settings=settings,
                emit_progress=emit_progress,
                scene_changes=scene_changes,
                video_layout=video_layout,
            )

            selection_source = selector.get_selection_source()
            candidate_diagnostics = selector.get_candidate_diagnostics()
            candidate_diagnostics["source_boundary"] = source_boundary
            candidate_diagnostics["selection_scope"] = selection_transcription.get("selection_scope", "full_source")
            socketio.emit("selection_mode", {"source": selection_source, "candidate_diagnostics": candidate_diagnostics})

            ctx.update(stage="ranking", progress=64, message=f"Ranqueando {len(top_clips)} candidatos")
            ctx.check_cancel()

            # Step 4: Rank and finalize scores
            emit_progress("=== ETAPA 4/5: Ranqueamento ===", "info")
            if scene_changes:
                for clip in top_clips:
                    start = float(clip.get("start", 0))
                    end = float(clip.get("end", start))
                    clip["scene_changes"] = [
                        change for change in scene_changes
                        if start <= float(change) <= end
                    ]
            from modules.viral_ranker import ViralRanker
            feedback_calibration = get_feedback_calibration()
            campaign_hub_snapshot = settings.get("campaign_hub_snapshot")
            campaign_hub_account = str(
                settings.get("campaign_hub_account")
                or (campaign_hub_snapshot or {}).get("default_account", "")
            )
            if campaign_hub_snapshot:
                emit_progress(
                    f"[Campaign Hub] Priors locais carregados para {campaign_hub_account or 'conta padrão'}; impacto limitado e explicável.",
                    "info",
                )
            if feedback_calibration.get("eligible"):
                emit_progress(
                    f"[Feedback editorial] Calibração aplicada com {feedback_calibration['sample_size']} decisões finais.",
                    "info",
                )
            else:
                emit_progress(
                    f"[Feedback editorial] Coletando decisões: {feedback_calibration['sample_size']}/{feedback_calibration['minimum_sample_size']} para calibrar o ranking.",
                    "info",
                )
            ranker = ViralRanker(
                channel_context=settings.get("channel_context", ""),
                editorial_profile=settings.get("editorial_profile", "renan_santos_politics"),
                feedback_calibration=feedback_calibration,
                campaign_hub_snapshot=campaign_hub_snapshot,
                campaign_hub_account=campaign_hub_account,
            )
            top_clips = ranker.rank_clips(
                top_clips,
                user_context=user_context,
                energy_profile=energy_profile,
            )
            top_clips, editorial_gate_rejections = _defer_context_incomplete_candidates(top_clips)
            candidate_diagnostics["render_deferred_context_count"] = sum(
                1 for item in editorial_gate_rejections if "contexto autossuficiente" in item.get("reason", "")
            )
            candidate_diagnostics["render_deferred_technical_count"] = sum(
                1 for item in editorial_gate_rejections if "revisão técnica editorial obrigatória" in item.get("reason", "")
            )
            if editorial_gate_rejections:
                emit_progress(
                    f"[Gate editorial] {len(editorial_gate_rejections)} candidato(s) adiados: contexto ou revisão técnica explícita.",
                    "warning",
                )

            ctx.update(stage="rendering", progress=76, message="Validando enquadramento e renderizando cortes")
            ctx.check_cancel()

            # Step 5: Cut clips with confidence-gated speaker framing
            emit_progress("=== ETAPA 5/5: Cortando Clips ===", "info")
            from modules.video_cutter import VideoCutter
            from modules.layout_planner import plan_layout
            cutter = VideoCutter(
                method="intelligent",
                target_duration=settings.get("cut_duration", 45),
                preset=settings.get("render_preset", "shorts"),
            )

            face_positions_map = {}
            original_aspect_indices = set()
            framing_by_index = {}
            layout_plans = {}
            target_aspect = get_preset(settings.get("render_preset", "shorts"))["aspect"]
            if use_face_tracking and tracker and video_layout not in {"debate", "unknown", "fullscreen"}:
                try:
                    emit_progress("[Layout] Detectando o locutor para enquadramento automático...", "info")
                    all_face_positions = tracker.detect_faces_in_video(video_path, sample_interval=2.0, emit_progress=emit_progress)
                    for index, clip in enumerate(top_clips):
                        start = float(clip.get("start", 0))
                        end = float(clip.get("end", start))
                        assessment = tracker.assess_segment_tracking(all_face_positions, start, end)
                        layout_plan = plan_layout(
                            detected_layout=video_layout,
                            tracking_assessment=assessment,
                            target_aspect=target_aspect,
                        )
                        layout_plans[index] = layout_plan
                        framing_mode = "reframe_9_16" if layout_plan.get("reframe_allowed") else "original"
                        framing_by_index[index] = {
                            "mode": framing_mode,
                            "reason": layout_plan["reason"],
                            "layout_family": layout_plan["layout_family"],
                            "confidence": layout_plan["confidence"],
                            "review_required": layout_plan["review_required"],
                        }
                        if layout_plan.get("reframe_allowed"):
                            face_positions_map[index] = assessment.get("positions", [])
                            emit_progress(f"[Layout] Clip {index + 1}: {layout_plan['reason']} Reframe {target_aspect} ativado.", "success")
                        else:
                            original_aspect_indices.add(index)
                            emit_progress(f"[Layout] Clip {index + 1}: {layout_plan['reason']}", "info")
                except Exception as exc:
                    original_aspect_indices.update(range(len(top_clips)))
                    reason = f"rastreamento indisponível: {str(exc)[:180]}"
                    for index in range(len(top_clips)):
                        layout_plan = plan_layout(detected_layout="unknown", target_aspect=target_aspect)
                        layout_plans[index] = {**layout_plan, "reason": reason, "reason_code": "tracking_unavailable"}
                        framing_by_index[index] = {
                            "mode": "original",
                            "reason": reason,
                            "layout_family": layout_plan["layout_family"],
                            "confidence": layout_plan["confidence"],
                            "review_required": True,
                        }
                    emit_progress(f"[Layout] Rastreamento não disponível: {str(exc)[:180]}. Mantendo 16:9.", "warning")
            else:
                reason = "múltiplos locutores ou layout sem segurança para reframe"
                for index in range(len(top_clips)):
                    layout_plan = plan_layout(detected_layout=video_layout, target_aspect=target_aspect)
                    layout_plans[index] = layout_plan
                    original_aspect_indices.add(index)
                    framing_by_index[index] = {
                        "mode": "original",
                        "reason": layout_plan["reason"] or reason,
                        "layout_family": layout_plan["layout_family"],
                        "confidence": layout_plan["confidence"],
                        "review_required": layout_plan["review_required"],
                    }
                emit_progress("[Layout] Composição ambígua ou multi-sujeito; preservando o quadro original.", "info")

            project_name = os.path.splitext(os.path.basename(video_path))[0]
            output_dir = settings.get("output_dir", "") or ""
            results = cutter.batch_cut(
                video_path, top_clips, project_name,
                use_face_tracking=bool(face_positions_map),
                face_positions_map=face_positions_map,
                original_aspect_indices=original_aspect_indices,
                emit_progress=emit_progress,
                output_dir=output_dir if output_dir else None,
                video_layout=video_layout,
                layout_plans=layout_plans,
            )
            render_rejections = list(editorial_gate_rejections)
            render_rejections.extend(getattr(cutter, "last_rejections", []))

            # Persist rendered clips so review decisions can calibrate future ranking.
            output_folder = ""
            clip_id_by_index = {}
            for i, res in enumerate(results):
                clip_data = top_clips[i] if i < len(top_clips) else {}
                clip_id_by_index[i] = save_clip(
                    active_project_id, res["path"], res["start"], res["end"],
                    res["duration"], clip_data.get("viral_score", 0),
                    clip_data.get("has_hook", False),
                    0,
                    res.get("text", "")
                )
                update_clip_editorial_score(
                    clip_id_by_index[i],
                    clip_data.get("editorial_potential_score", clip_data.get("viral_score", 0)),
                    clip_data.get("factors", {}),
                    clip_data.get("confidence", 0),
                    clip_data.get("editorial_score_version", "v1-explainable"),
                    review_flags=clip_data.get("review_flags", {}),
                    review_metadata={
                        "candidate_origin": clip_data.get("candidate_origin"),
                        "selection_source": selection_source,
                        "confidence": clip_data.get("confidence", 0),
                    },
                )
                if not output_folder:
                    output_folder = res.get("output_folder", "")

            clip_results = []
            for i, res in enumerate(results):
                clip_info = top_clips[i] if i < len(top_clips) else {}
                clip_results.append({
                    **res,
                    "viral_score": clip_info.get("viral_score", 0),
                    "has_hook": clip_info.get("has_hook", False),
                    "breakdown": clip_info.get("breakdown", {}),
                    "title": clip_info.get("title", ""),
                    "source": clip_info.get("source", "nlp"),
                    "candidate_origin": clip_info.get("candidate_origin", "local_primary"),
                    "candidate_origin_label": clip_info.get("candidate_origin_label", "Origem local registrada"),
                    "candidate_origin_note": clip_info.get("candidate_origin_note", "Origem registrada para transparência da revisão."),
                    "political_signals": clip_info.get("political_signals", {}),
                    "review_flags": clip_info.get("review_flags", {}),
                    "speaker": clip_info.get("speaker", ""),
                    "speaker_confidence": clip_info.get("speaker_confidence"),
                    "overlap_suspected": clip_info.get("overlap_suspected", False),
                    "editorial_block": build_editorial_block({
                        **clip_info,
                        "start": res.get("start"),
                        "end": res.get("end"),
                        "duration": res.get("duration"),
                        "review_status": "pending",
                    }),
                    "rank": res.get("rank", i + 1),
                    "clip_id": clip_id_by_index.get(i),
                    "framing": framing_by_index.get(i, {
                        "mode": "original",
                        "reason": "composição original preservada por segurança",
                    }),
                })

            emit_status("cut_complete", {
                "clips": clip_results,
                "selection_source": selection_source,
                "candidate_diagnostics": candidate_diagnostics,
                "video_layout": video_layout,
                "project_id": active_project_id,
                "output_folder": output_folder,
                "render_rejections": render_rejections,
                "editorial_audit": editorial_audit,
                "audit_mode": audit_mode,
                "preferred_format": preferred_format,
                "source_boundary": source_boundary,
            })

            source_label = "IA Inteligente" if selection_source == "llm" else "NLP Basico"
            if results:
                emit_progress(f"Corte completo! {len(results)} clips gerados via {source_label}.", "success")
            else:
                detail = "; ".join(
                    error
                    for rejection in render_rejections
                    for error in rejection.get("errors", [])
                )
                message = "Nenhum clip válido foi entregue; os arquivos rejeitados foram removidos."
                if detail:
                    message += f" Diagnóstico: {detail[:320]}"
                emit_progress(message, "error")
            return {
                "artifacts": [{
                    "type": "clips",
                    "project_id": active_project_id,
                    "count": len(clip_results),
                    "output_folder": output_folder,
                }]
            }

        except JobCancelled as exc:
            emit_progress(f"[Corte] Operação cancelada: {exc}", "warning")
            emit_status("cancelled", {"operation": "cut", "message": str(exc)})
            raise
        except OperationCancelled as exc:
            emit_progress(f"[Corte] Operação cancelada: {exc}", "warning")
            emit_status("cancelled", {"operation": "cut", "message": str(exc)})
            raise JobCancelled(str(exc)) from exc
        except ValueError as ve:
            friendly = _translate_error(str(ve))
            emit_progress(f"Erro: {friendly}", "error")
            emit_status("error", {"message": friendly})
            raise
        except Exception as e:
            friendly = _translate_error(str(e))
            emit_progress(f"Erro no corte: {friendly}", "error")
            emit_status("error", {"message": friendly, "technical": str(e)})
            raise
        finally:
            _set_legacy_task("", active=False)

    with processing_lock:
        if current_task["active"]:
            return jsonify({"error": ERROR_MESSAGES["processing_active"]}), 409
        _set_legacy_task("cut", active=True)
        job = job_manager.submit("cut_shorts", task, project_id=project_id)
        current_task["job_id"] = job["id"]

    return jsonify({
        "success": True,
        "message": "Corte de shorts iniciado",
        "job_id": job["id"],
        "state": job["state"],
    })


@app.route("/api/editorial/context", methods=["POST"])
def api_analyze_editorial_context():
    """Analyze the full source before cutting and return an explainable editorial dossier."""
    data = request.get_json(silent=True) or {}
    video_path = _resolve_media_input(data.get("video_path", ""))
    if not video_path:
        return jsonify({"error": "Video não encontrado ou caminho inválido"}), 404
    if not os.path.exists(video_path):
        return jsonify({"error": "Video não encontrado"}), 404
    project_id = data.get("project_id")
    user_context = str(data.get("user_context", "") or "").strip()
    analyze_video = _coerce_bool(data.get("analyze_video"), default=True)

    def task(ctx):
        def progress(message, level="info", percentage=None):
            current = int(percentage if percentage is not None else 10)
            ctx.update(stage="editorial_context", progress=current, message=str(message))
            socketio.emit(
                "progress",
                {
                    "message": f"[Versão {PROGRAM_VERSION} · {PROGRAM_REVISION}] {str(message)}",
                    "level": level,
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "job_id": ctx.job_id,
                    "program_version": PROGRAM_VERSION,
                    "program_revision": PROGRAM_REVISION,
                },
            )

        settings = get_all_settings()
        if user_context:
            settings["editorial_context_prompt"] = user_context
        video_duration = _probe_video_duration_seconds(video_path)
        progress("[Contexto] Preparando a análise integral da fonte...", "info", 5)
        ctx.check_cancel()
        manual_supplied = _manual_transcript_was_supplied(data)
        transcription = _transcription_from_request(data, duration=video_duration)
        if not transcription and project_id:
            transcription = get_transcription(project_id)
        multimodal_result = None
        if not transcription:
            progress("[Contexto] Não há transcrição confirmada; Gemini tentará gerar a leitura temporal.", "info", 18)
            multimodal_result = _run_gemini_video_analysis(
                video_path, settings, {}, user_context, progress, cancel_check=ctx.check_cancel
            )
            transcription = _transcription_from_gemini_result(multimodal_result, settings.get("language", "pt"))
        if not transcription:
            raise ValueError("Não foi possível obter uma transcrição para analisar o contexto.")
        coverage = _transcription_coverage_report(transcription, video_duration)
        transcription["coverage"] = coverage
        transcription["provenance"] = _transcription_provenance(transcription, manual_supplied=manual_supplied)
        progress(
            f"[Contexto] Transcrição canônica confirmada: {transcription.get('segment_count', len(transcription.get('segments', [])))} segmentos; "
            f"origem {transcription.get('source', 'desconhecida')}; cobertura {coverage.get('status', 'não verificada')}.",
            "success",
            35,
        )
        ctx.check_cancel()
        from modules.editorial_context import analyze_transcript_context
        editorial_context = analyze_transcript_context(
                transcription,
                focus=settings.get("editorial_focus", "auto"),
                campaign_hub_account=settings.get("campaign_hub_account", "@renansantosmbl"),
            )
        editorial_context["transcription_provenance"] = transcription.get("provenance", {})
        editorial_context["transcript_reference"] = _transcript_reference_for_multimodal(transcription)
        progress(
            "[Contexto] Identificando tese, perguntas, capítulos e possíveis payoffs; a transcrição canônica será preservada.",
            "info",
            55,
        )
        if analyze_video and multimodal_result is None:
            progress("[Contexto] Escutando e observando a fonte para validar o cenário, tom e participantes...", "info", 62)
            multimodal_result = _run_gemini_video_analysis(
                video_path, settings, editorial_context, user_context, progress, cancel_check=ctx.check_cancel
            )
        enriched = _enrich_editorial_context(
            video_path,
            settings,
            editorial_context,
            user_context,
            progress,
            multimodal=multimodal_result,
            allow_video_analysis=False,
        )
        if not multimodal_result or not analyze_video:
            try:
                progress(
                    "[Contexto] Auditoria local ativa: energia, hooks e priors do Campaign Hub serão calculados sem reenviar o vídeo.",
                    "info",
                    72,
                )
                enriched = _enrich_editorial_context_locally(
                    video_path,
                    transcription,
                    enriched,
                    settings,
                    progress,
                    cancel_check=ctx.check_cancel,
                )
                enriched["analysis_mode"] = "transcript_plus_local_audio"
            except (OperationCancelled, JobCancelled):
                raise
            except Exception as local_exc:
                progress(f"[Contexto] Auditoria local de áudio não concluída; mantendo sinais textuais: {str(local_exc)[:180]}", "warning", 78)
        enriched["transcription_quality"] = {
            "status": coverage.get("status", "unknown"),
            "segment_count": len(transcription.get("segments", [])),
            "last_timestamp": coverage.get("last_timestamp"),
            "video_duration_seconds": coverage.get("video_duration_seconds"),
        }
        if not enriched.get("analysis_mode"):
            enriched["analysis_mode"] = "transcript_plus_video" if multimodal_result else "transcript_only"
        if project_id:
            save_transcription(
                project_id,
                transcription.get("segments", []),
                transcription.get("full_text", ""),
                transcription.get("language", settings.get("language", "pt")),
                transcription.get("source", "editorial_context"),
            )
        transcript_files = save_transcription_bundle(
            transcription,
            project_id=project_id,
            source_video=video_path,
        )
        context_file = save_context_bundle(
            enriched,
            transcription_provenance=transcription.get("provenance", {}),
            project_id=project_id,
            source_video=video_path,
        )
        manifest_file = write_session_manifest(
            project_id=project_id,
            source_video=video_path,
            transcription_provenance=transcription.get("provenance", {}),
            context_status={"analysis_mode": enriched.get("analysis_mode"), "context_file": context_file},
        )
        enriched["session_artifacts"] = {**transcript_files, "context": context_file, "manifest": manifest_file}
        artifacts = [{"type": "editorial_context", "context": enriched}]
        ctx.update(stage="editorial_context", progress=100, message="Contexto integral concluído", artifacts=artifacts)
        socketio.emit("editorial_context_complete", {"context": enriched, "job_id": ctx.job_id})
        return {"artifacts": artifacts}

    with processing_lock:
        # O JobManager já serializa os workers; o estado legado não é alterado
        # aqui para que uma exceção de análise não deixe a interface travada.
        job = job_manager.submit("editorial_context", task, project_id=project_id)
    return jsonify({"success": True, "message": "Análise de contexto iniciada", "job_id": job["id"], "state": job["state"]})


@app.route("/api/process/subtitles", methods=["POST"])
def api_generate_subtitles():
    data = request.get_json(silent=True) or {}
    video_path = _resolve_media_input(data.get("video_path", ""))
    if not video_path:
        return jsonify({"error": "Video não encontrado ou caminho inválido"}), 404
    project_id = data.get("project_id")
    subtitle_settings = data.get("subtitle_settings", {})

    if not os.path.exists(video_path):
        return jsonify({"error": "Video nao encontrado"}), 404

    def task():
        current_task["active"] = True
        try:
            settings = get_all_settings()
            settings.update(subtitle_settings)

            # Transcribe if needed
            transcription = None
            if project_id:
                transcription = get_transcription(project_id)

            if not transcription:
                emit_progress("Transcrevendo para gerar legendas...", "info")
                from modules.transcriber import Transcriber
                transcriber = Transcriber(
                    model_name=settings.get("whisper_model", "small"),
                    language=settings.get("language", "pt"),
                )
                result = transcriber.transcribe(video_path, emit_progress=emit_progress)
                segments = result["segments"]
                if project_id:
                    save_transcription(
                        project_id, result["segments"], result["full_text"],
                        result["language"], settings.get("whisper_model", "small")
                    )
            else:
                segments = transcription["segments"]

            emit_progress("Gerando legendas estilizadas...", "info")
            from modules.subtitle_generator import SubtitleGenerator
            gen = SubtitleGenerator(settings)

            base = os.path.splitext(os.path.basename(video_path))[0]
            ass_path = os.path.join(PROCESSED_DIR, f"{base}.ass")
            gen.generate_ass_file(segments, ass_path)

            srt_path = os.path.join(PROCESSED_DIR, f"{base}.srt")
            gen.generate_srt(segments, srt_path)

            output_path = os.path.join(PROCESSED_DIR, f"{base}_legendado.mp4")
            result = gen.burn_subtitles(video_path, ass_path, output_path, emit_progress=emit_progress)

            if result:
                emit_status("subtitles_complete", {
                    "video_path": os.path.relpath(result, WORKSPACE_DIR),
                    "ass_path": os.path.relpath(ass_path, WORKSPACE_DIR),
                    "srt_path": os.path.relpath(srt_path, WORKSPACE_DIR),
                })
                emit_progress("Legendas geradas e queimadas no video!", "success")
            else:
                emit_status("error", {"message": "Falha ao gerar legendas"})

        except Exception as e:
            emit_progress(f"Erro nas legendas: {str(e)}", "error")
            emit_status("error", {"message": str(e)})
        finally:
            current_task["active"] = False

    if current_task["active"]:
        return jsonify({"error": "Ja existe um processamento em andamento"}), 409

    threading.Thread(target=task, daemon=True).start()
    return jsonify({"success": True, "message": "Geracao de legendas iniciada"})


@app.route("/api/process/seo", methods=["POST"])
def api_generate_seo():
    data = request.json
    transcript = data.get("transcript", "")
    clip_id = data.get("clip_id")

    if not transcript:
        return jsonify({"error": "Transcricao nao informada"}), 400

    def task():
        current_task["active"] = True
        try:
            settings = get_all_settings()
            from modules.ai_backend import AIBackend
            ai = AIBackend(
                backend=settings.get("ai_backend", "ollama"),
                settings=settings,
            )
            result = ai.generate_seo_content(
                transcript,
                channel_context=settings.get("channel_context", ""),
                emit_progress=emit_progress,
            )

            if clip_id and result:
                update_clip_seo(
                    clip_id,
                    result.get("titles", []),
                    result.get("tags", []),
                    result.get("description", ""),
                    result.get("hashtags", []),
                )

            emit_status("seo_complete", result)
            emit_progress("Conteudo SEO gerado!", "success")

        except Exception as e:
            emit_progress(f"Erro no SEO: {str(e)}", "error")
            emit_status("error", {"message": str(e)})
        finally:
            current_task["active"] = False

    if current_task["active"]:
        return jsonify({"error": "Ja existe um processamento em andamento"}), 409

    threading.Thread(target=task, daemon=True).start()
    return jsonify({"success": True, "message": "Geracao de SEO iniciada"})


@app.route("/api/performance/snapshots", methods=["POST"])
def api_save_performance_snapshot():
    """Persist metrics supplied by an authorized export or manual observation."""
    data = request.get_json(silent=True) or {}
    items = data.get("snapshots", data)
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list) or not items:
        return jsonify({"success": False, "error": "Envie um snapshot ou uma lista de snapshots."}), 400
    saved = []
    try:
        for item in items[:200]:
            normalized = normalize_snapshot(item)
            snapshot_id = save_performance_snapshot(normalized)
            saved.append({"id": snapshot_id, **normalized, "labels": metric_labels(normalized)})
        return jsonify({"success": True, "saved": saved, "summary": get_performance_summary()})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": f"Não foi possível salvar a métrica: {exc}"}), 500


@app.route("/api/performance/summary", methods=["GET"])
def api_performance_summary():
    format_id = request.args.get("format_id", "")
    platform = request.args.get("platform", "")
    observation_window = request.args.get("observation_window", "")
    region = request.args.get("region", "")
    filters = {
        "format_id": format_id or None,
        "platform": platform or None,
        "observation_window": observation_window or None,
        "region": region or None,
    }
    return jsonify({
        "success": True,
        "filters": {key: value for key, value in filters.items() if value is not None},
        "summary": get_performance_summary(**filters),
        "snapshots": get_performance_snapshots(limit=50, **filters),
    })


@app.route("/api/headline-studio/analyze", methods=["POST"])
def api_analyze_headline_studio():
    """Generate short artwork copy from an imported finished-cut transcript."""
    data = request.get_json(silent=True) or {}
    transcript = str(data.get("transcript", "") or "")
    mini_context = str(data.get("mini_context", "") or "")
    preferred_format = str(data.get("preferred_format", "auto") or "auto")
    use_ai = bool(data.get("use_ai", True))
    clip_id = data.get("clip_id")
    project_id = data.get("project_id")
    clip = None
    if clip_id not in (None, ""):
        try:
            clip_id = int(clip_id)
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Identificador de corte inválido."}), 400
        clip = get_clip(clip_id)
        if not clip:
            return jsonify({"success": False, "error": "Corte não encontrado no backup local."}), 404
        if not transcript.strip():
            transcript = str(clip.get("transcript") or "")
        if not mini_context.strip():
            mini_context = str(clip.get("title") or "")
        project_id = project_id or clip.get("project_id")
    if not transcript.strip():
        return jsonify({"success": False, "error": "Cole ou importe uma transcrição antes de gerar o texto de arte."}), 400
    if len(transcript) > 60000:
        return jsonify({"success": False, "error": "A transcrição excede o limite de 60.000 caracteres para esta análise."}), 400

    try:
        from modules.ai_backend import AIBackend
        from modules.headline_studio import generate_artwork_copy

        settings = get_all_settings()
        ai = None
        if use_ai:
            ai = AIBackend(backend=settings.get("ai_backend", "ollama"), settings=settings)
        result = generate_artwork_copy(
            transcript,
            mini_context=mini_context,
            preferred_format=preferred_format,
            ai_backend=ai,
            editorial_learning=get_headline_learning_preferences(),
        )
        result["clip_id"] = clip_id
        result["editorial_key"] = str((clip or {}).get("editorial_key") or "")
        result["source_interval"] = {
            "start": float((clip or {}).get("start_time", 0) or 0),
            "end": float((clip or {}).get("end_time", 0) or 0),
        } if clip else None
        project = get_project(project_id) if project_id not in (None, "") else {}
        try:
            result["session_artifact"] = save_headline_generation(
                data,
                result,
                project_id=project_id,
                clip_id=clip_id,
                source_video=(project or {}).get("source_video", ""),
            )
        except Exception as storage_error:
            app.logger.warning("Não foi possível arquivar geração de headline: %s", storage_error)
        return jsonify({"success": True, "studio": result})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": f"Não foi possível analisar o texto de arte: {exc}"}), 500


@app.route("/api/headline-studio/feedback", methods=["POST"])
def api_save_headline_studio_feedback():
    """Save a selected/rejected artwork-copy decision in local persistent data."""
    data = request.get_json(silent=True) or {}
    format_id = str(data.get("format_id", "") or "")
    artwork_text = str(data.get("artwork_text", "") or "").strip()
    action = str(data.get("action", "selected") or "selected")
    clip_id = data.get("clip_id")
    editorial_key = str(data.get("editorial_key", "") or "")
    clip = None
    project_id = data.get("project_id")
    if clip_id not in (None, ""):
        try:
            clip_id = int(clip_id)
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Identificador de corte inválido."}), 400
        clip = get_clip(clip_id)
        if not clip:
            return jsonify({"success": False, "error": "Corte não encontrado no backup local."}), 404
        project_id = project_id or clip.get("project_id")
        editorial_key = editorial_key or str(clip.get("editorial_key") or "")
    if format_id not in {"vertical_916", "square_alfinetei", "fake_tweet"}:
        return jsonify({"success": False, "error": "Formato editorial inválido."}), 400
    if not artwork_text or len(artwork_text) > 300:
        return jsonify({"success": False, "error": "Texto de arte inválido ou longo demais."}), 400
    if action not in {"selected", "rejected"}:
        return jsonify({"success": False, "error": "Ação editorial inválida."}), 400
    topic = str(data.get("topic", "") or "")
    transcript_excerpt = str(data.get("transcript_excerpt", "") or "")
    mini_context = str(data.get("mini_context", "") or "")
    save_headline_feedback(
        format_id,
        artwork_text,
        action=action,
        topic=topic,
        transcript_excerpt=transcript_excerpt,
        mini_context=mini_context,
        clip_id=clip_id,
        editorial_key=editorial_key,
        source="clip_headline_studio" if clip_id else "headline_studio",
    )
    project = get_project(project_id) if project_id not in (None, "") else {}
    try:
        save_headline_decision(
            {
                "format_id": format_id,
                "artwork_text": artwork_text,
                "action": action,
                "topic": topic,
                "transcript_excerpt": transcript_excerpt[:1200],
                "mini_context": mini_context[:500],
                "editorial_key": editorial_key,
            },
            project_id=project_id,
            clip_id=clip_id,
            source_video=(project or {}).get("source_video", ""),
        )
    except Exception as storage_error:
        app.logger.warning("Não foi possível arquivar decisão de headline: %s", storage_error)
    return jsonify({"success": True, "learning": get_headline_feedback_summary()})


@app.route("/api/headline-studio/learning", methods=["GET"])
def api_headline_studio_learning():
    return jsonify({"success": True, "learning": get_headline_feedback_summary()})


@app.route("/api/process/thumbnail", methods=["POST"])
def api_generate_thumbnail():
    data = request.get_json(silent=True) or {}
    video_path = _resolve_media_input(data.get("video_path", ""))
    if not video_path:
        return jsonify({"error": "Video não encontrado ou caminho inválido"}), 404
    time_seconds = data.get("time", 5)
    text = data.get("text", "")
    style = data.get("style", "dark_gold")
    clip_id = data.get("clip_id")

    if not os.path.exists(video_path):
        return jsonify({"error": "Video nao encontrado"}), 404

    def task():
        current_task["active"] = True
        try:
            from modules.thumbnail_generator import ThumbnailGenerator
            gen = ThumbnailGenerator()

            base = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(THUMBNAIL_DIR, f"{base}_thumb_{uuid.uuid4().hex[:8]}.jpg")

            result = gen.generate_thumbnail(
                video_path, time_seconds, text, output_path, style, emit_progress
            )

            if result and clip_id:
                update_clip_thumbnail(clip_id, os.path.relpath(result, WORKSPACE_DIR))

            if result:
                emit_status("thumbnail_complete", {
                    "path": os.path.relpath(result, WORKSPACE_DIR),
                })
                emit_progress("Thumbnail gerada!", "success")

        except Exception as e:
            emit_progress(f"Erro na thumbnail: {str(e)}", "error")
            emit_status("error", {"message": str(e)})
        finally:
            current_task["active"] = False

    if current_task["active"]:
        return jsonify({"error": "Ja existe um processamento em andamento"}), 409

    threading.Thread(target=task, daemon=True).start()
    return jsonify({"success": True, "message": "Geracao de thumbnail iniciada"})


@app.route("/api/process/complete", methods=["POST"])
def api_process_complete():
    data = request.get_json(silent=True) or {}
    video_path = _resolve_media_input(data.get("video_path", ""))
    if not video_path:
        return jsonify({"error": "Video não encontrado ou caminho inválido"}), 404
    user_context = data.get("user_context", "")
    video_genre = data.get("video_genre", "")
    transcription_source = data.get("transcription_source")

    if not os.path.exists(video_path):
        return jsonify({"error": "Video nao encontrado"}), 404

    def task(ctx):
        current_task["active"] = True
        try:
            settings = get_all_settings()
            if transcription_source:
                settings = {**settings, "transcription_source": transcription_source}
            ctx.update(stage="project", progress=3, message="Criando projeto")
            ctx.check_cancel()
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            project_id = create_project(video_name, video_path)

            # ── Step 1: Remove silence ──
            emit_progress("━━━ ETAPA 1/6: Removendo Silencio ━━━", "info")
            from modules.silence_remover import SilenceRemover
            remover = SilenceRemover(
                silence_threshold=settings.get("silence_threshold", -35),
                min_silence_duration=settings.get("min_silence_duration", 0.5),
                padding=settings.get("padding", 0.25),
            )
            silence_result = remover.remove_silence(video_path, emit_progress=emit_progress)
            ctx.update(stage="silence", progress=15, message="Análise de silêncio concluída")
            ctx.check_cancel()
            if silence_result:
                emit_progress(
                    "Versão sem silêncio gerada como artefato separado; "
                    "a seleção continuará usando a timeline original.",
                    "info",
                )
            # The original video remains canonical. Removing silence resets PTS
            # in the derived file, so its timestamps must never be used to cut
            # the source without an explicit TimelineMap conversion.
            working_video = video_path

            # ── Step 2: Import manual transcript or transcribe ──
            emit_progress("━━━ ETAPA 2/6: Transcrição e contexto ━━━", "info")
            from modules.transcriber import Transcriber
            transcription = _transcription_from_request(data)
            multimodal_result = None
            selected_transcription_mode = _transcription_source_mode(settings)
            if not transcription and selected_transcription_mode in {"whisper", "public_subtitle"}:
                transcription = _transcribe_video_automatically(
                    working_video,
                    settings,
                    emit_progress,
                    cancel_check=ctx.check_cancel,
                )
            elif not transcription:
                multimodal_result = _run_gemini_video_analysis(
                    working_video,
                    settings,
                    {},
                    user_context,
                    emit_progress,
                    cancel_check=ctx.check_cancel,
                )
                transcription = _transcription_from_gemini_result(multimodal_result, settings.get("language", "pt"))
            if transcription and transcription.get("source") == "manual":
                emit_progress(f"[Transcrição manual] {transcription['segment_count']} segmentos importados; Whisper não será executado.", "success")
            elif transcription and transcription.get("source") == "gemini_video":
                emit_progress(f"[Gemini] {transcription['segment_count']} segmentos obtidos da análise multimodal; Whisper não será executado.", "success")
            else:
                transcriber = Transcriber(
                    model_name=settings.get("whisper_model", "small"),
                    language=settings.get("language", "pt"),
                    word_timestamps=settings.get("whisper_word_timestamps", True),
                    beam_size=settings.get("whisper_beam_size", 5),
                    device=settings.get("whisper_device", "auto"),
                )
                transcription = transcriber.transcribe(
                    working_video,
                    emit_progress=emit_progress,
                    cancel_check=ctx.check_cancel,
                )
            video_duration = _probe_video_duration_seconds(working_video)
            coverage = _transcription_coverage_report(transcription, video_duration)
            transcription["coverage"] = coverage
            if coverage["status"] == "mismatch_suspected" and transcription.get("source") == "manual":
                raise ValueError(
                    "A transcrição manual contém timestamps além da duração do vídeo selecionado. "
                    "Ela provavelmente pertence a outro vídeo; selecione a mídia correta ou importe a legenda correspondente."
                )
            if coverage["status"] == "partial":
                emit_progress(
                    f"[Transcrição] Cobertura parcial: termina em {coverage['last_timestamp']:.1f}s de {coverage['video_duration_seconds']:.1f}s; "
                    "os cortes ficarão limitados ao trecho importado.",
                    "warning",
                )
            save_transcription(
                project_id, transcription["segments"], transcription["full_text"],
                transcription["language"], transcription.get("source", settings.get("whisper_model", "small"))
            )
            from modules.editorial_context import analyze_transcript_context
            editorial_context = analyze_transcript_context(
                transcription,
                focus=settings.get("editorial_focus", "auto"),
                campaign_hub_account=settings.get("campaign_hub_account", "@renansantosmbl"),
            )
            emit_progress(f"[Contexto editorial] {editorial_context['description']}", "info")
            editorial_context = _enrich_editorial_context(
                video_path, settings, editorial_context, user_context, emit_progress,
                multimodal=multimodal_result,
                allow_video_analysis=not (
                    transcription.get("source") == "manual"
                    and not settings.get("gemini_manual_video_analysis", False)
                ),
            )
            settings["editorial_context"] = editorial_context
            ctx.update(stage="transcription", progress=35, message="Transcrição e contexto concluídos")
            ctx.check_cancel()

            # ── Step 3: Intelligent clip selection ──
            emit_progress("━━━ ETAPA 3/6: Selecao Inteligente de Clips ━━━", "info")
            from modules.clip_selector import ClipSelector
            from modules.audio_analyzer import AudioAnalyzer

            analyzer = AudioAnalyzer()
            energy_profile = _analyze_energy_with_cancel(analyzer, working_video, emit_progress, ctx.check_cancel)
            try:
                from modules.editorial_context import detect_hook_candidates
                from modules.campaign_hub import load_snapshot
                context_snapshot = load_snapshot(settings.get("campaign_hub_snapshot_path"))
                settings.setdefault("editorial_context", {})["hook_candidates"] = detect_hook_candidates(
                    transcription.get("segments", []),
                    snapshot=context_snapshot,
                    account=settings.get("campaign_hub_account", "@renansantosmbl"),
                    energy_profile=energy_profile,
                )
            except Exception as exc:
                emit_progress(f"[Contexto] Hooks com áudio não disponíveis; mantendo sinais textuais: {str(exc)[:140]}", "warning")

            coverage_plan = _selection_coverage_plan(data.get("video_path", video_path), video_duration)
            if coverage_plan["previous_clip_fingerprints"]:
                emit_progress(
                    f"[Deduplicação] {len(coverage_plan['previous_clip_fingerprints'])} intervalos já gerados para esta fonte serão evitados.",
                    "info",
                )
            settings.update(coverage_plan)
            emit_progress(
                f"[Cobertura] Até {coverage_plan['adaptive_max_clips']} candidatos nesta execução; "
                "qualidade, contexto e diversidade continuam prioritários.",
                "info",
            )
            selector = ClipSelector(
                target_duration=settings.get("cut_duration", 45),
                max_clips=coverage_plan["adaptive_max_clips"],
                min_duration=20,
                max_duration=180,
            )
            top_clips = selector.select_clips(
                transcription,
                energy_profile=energy_profile,
                user_context=user_context,
                settings=settings,
                emit_progress=emit_progress,
            )
            top_clips = _attach_multimodal_visual_observations(top_clips, multimodal_result)
            ctx.update(stage="candidate_generation", progress=55, message=f"{len(top_clips)} candidatos encontrados")
            ctx.check_cancel()

            # ── Step 4: Rank and cut ──
            emit_progress("━━━ ETAPA 4/6: Ranqueando e Cortando ━━━", "info")
            from modules.viral_ranker import ViralRanker
            from modules.campaign_hub import load_snapshot
            from modules.video_cutter import VideoCutter
            from modules.layout_planner import plan_layout

            campaign_hub_snapshot = load_snapshot(settings.get("campaign_hub_snapshot_path"))
            campaign_hub_account = str(
                settings.get("campaign_hub_account")
                or (campaign_hub_snapshot or {}).get("default_account", "")
            )
            if campaign_hub_snapshot:
                emit_progress(
                    f"[Campaign Hub] Priors locais carregados para {campaign_hub_account or 'conta padrão'}; impacto limitado e explicável.",
                    "info",
                )
            feedback_calibration = get_feedback_calibration()
            ranker = ViralRanker(
                channel_context=settings.get("channel_context", ""),
                editorial_profile=settings.get("editorial_profile", "renan_santos_politics"),
                feedback_calibration=feedback_calibration,
                campaign_hub_snapshot=campaign_hub_snapshot,
                campaign_hub_account=campaign_hub_account,
            )
            top_clips = ranker.rank_clips(
                top_clips,
                user_context=user_context,
                energy_profile=energy_profile,
            )

            cutter = VideoCutter(
                method="intelligent",
                target_duration=settings.get("cut_duration", 45),
                preset=settings.get("render_preset", "shorts"),
            )

            # Layout detection + face tracking with confidence gating. Reframe is
            # enabled only for a stable speaker; interviews and visual compositions
            # preserve their original frame by default.
            video_layout = "unknown"
            tracker = None
            face_positions_map = {}
            original_aspect_indices = set()
            framing_by_index = {}
            layout_plans = {}
            try:
                from modules.face_tracker import FaceTracker
                tracker = FaceTracker()
                video_layout = tracker.detect_layout(
                    video_path, emit_progress=emit_progress,
                    video_genre=video_genre if video_genre else None
                )
            except Exception as exc:
                emit_progress(f"Face tracking indisponível: {str(exc)}", "warning")

            target_aspect = get_preset(settings.get("render_preset", "shorts"))["aspect"]
            if use_face_tracking and tracker and video_layout not in {"debate", "unknown", "fullscreen"}:
                try:
                    emit_progress("[Layout] Avaliando estabilidade do locutor para reframe...", "info")
                    ctx.check_cancel()
                    all_faces = tracker.detect_faces_in_video(video_path, sample_interval=2.0, emit_progress=emit_progress)
                    for index, clip in enumerate(top_clips):
                        assessment = tracker.assess_segment_tracking(all_faces, clip["start"], clip["end"])
                        layout_plan = plan_layout(
                            detected_layout=video_layout,
                            tracking_assessment=assessment,
                            visual_format=clip.get("visual_format"),
                            text_panel=bool(clip.get("text_panel")),
                            fake_tweet=bool(clip.get("fake_tweet") or clip.get("social_post")),
                            visual_meme=bool(clip.get("visual_meme")),
                            external_evidence=bool(clip.get("external_evidence")),
                            target_aspect=target_aspect,
                        )
                        layout_plans[index] = layout_plan
                        framing_by_index[index] = {
                            "mode": "reframe_9_16" if layout_plan.get("reframe_allowed") else "original",
                            "reason": layout_plan["reason"],
                            "layout_family": layout_plan["layout_family"],
                            "confidence": layout_plan["confidence"],
                            "review_required": layout_plan["review_required"],
                        }
                        if layout_plan.get("reframe_allowed"):
                            face_positions_map[index] = assessment.get("positions", [])
                        else:
                            original_aspect_indices.add(index)
                    ctx.check_cancel()
                except Exception as exc:
                    original_aspect_indices.update(range(len(top_clips)))
                    reason = f"rastreamento indisponível: {str(exc)[:180]}"
                    for index in range(len(top_clips)):
                        layout_plan = plan_layout(detected_layout="unknown", target_aspect=target_aspect)
                        layout_plans[index] = {**layout_plan, "reason": reason, "reason_code": "tracking_unavailable"}
                        framing_by_index[index] = {
                            "mode": "original",
                            "reason": reason,
                            "layout_family": layout_plan["layout_family"],
                            "confidence": layout_plan["confidence"],
                            "review_required": True,
                        }
                    emit_progress(f"[Layout] {reason}; mantendo o quadro original.", "warning")
            else:
                for index in range(len(top_clips)):
                    clip = top_clips[index]
                    layout_plan = plan_layout(
                        detected_layout=video_layout,
                        visual_format=clip.get("visual_format"),
                        text_panel=bool(clip.get("text_panel")),
                        fake_tweet=bool(clip.get("fake_tweet") or clip.get("social_post")),
                        visual_meme=bool(clip.get("visual_meme")),
                        external_evidence=bool(clip.get("external_evidence")),
                        target_aspect=target_aspect,
                    )
                    layout_plans[index] = layout_plan
                    original_aspect_indices.add(index)
                    framing_by_index[index] = {
                        "mode": "original",
                        "reason": layout_plan["reason"],
                        "layout_family": layout_plan["layout_family"],
                        "confidence": layout_plan["confidence"],
                        "review_required": layout_plan["review_required"],
                    }
                emit_progress("[Layout] Composição preservada: múltiplos locutores ou layout ambíguo.", "info")

            if tracker is not None:
                tracker.close()

            output_dir = settings.get("output_dir", "") or ""
            results = cutter.batch_cut(
                video_path, top_clips, video_name,
                use_face_tracking=bool(face_positions_map),
                face_positions_map=face_positions_map,
                original_aspect_indices=original_aspect_indices,
                emit_progress=emit_progress,
                output_dir=output_dir if output_dir else None,
                video_layout=video_layout,
                layout_plans=layout_plans,
            )
            ctx.update(stage="rendering", progress=72, message=f"{len(results)} clips renderizados")
            ctx.check_cancel()

            # ── Step 5: Generate subtitles for each clip ──
            emit_progress("━━━ ETAPA 5/6: Gerando Legendas ━━━", "info")
            from modules.subtitle_generator import SubtitleGenerator
            sub_gen = SubtitleGenerator(settings)

            for i, res in enumerate(results):
                ctx.check_cancel()
                clip_data = top_clips[i] if i < len(top_clips) else {}
                clip_segments = []
                for seg in transcription["segments"]:
                    if seg["end"] > res["start"] and seg["start"] < res["end"]:
                        adjusted = {
                            **seg,
                            "start": max(0, seg["start"] - res["start"]),
                            "end": min(res["duration"], seg["end"] - res["start"]),
                            "words": [
                                {
                                    **w,
                                    "start": max(0, w["start"] - res["start"]),
                                    "end": min(res["duration"], w["end"] - res["start"]),
                                }
                                for w in seg.get("words", [])
                                if w["end"] > res["start"] and w["start"] < res["end"]
                            ]
                        }
                        clip_segments.append(adjusted)

                if clip_segments:
                    base_clip = os.path.splitext(res["path"])[0]
                    ass_path = base_clip + ".ass"
                    preset = sub_gen.preset
                    sub_gen.generate_ass_file(
                        clip_segments, ass_path, preset["width"], preset["height"]
                    )
                    subtitled_path = base_clip + "_leg.mp4"
                    sub_result = sub_gen.burn_subtitles(res["path"], ass_path, subtitled_path, emit_progress)
                    if sub_result:
                        res["subtitled_path"] = subtitled_path

                clip_id = save_clip(
                    project_id, res["path"], res["start"], res["end"],
                    res["duration"], clip_data.get("viral_score", 0),
                    clip_data.get("has_hook", False),
                    clip_data.get("emotional_intensity", 0),
                    res.get("text", "")
                )
                res["clip_id"] = clip_id
                update_clip_editorial_score(
                    clip_id,
                    clip_data.get("editorial_potential_score", clip_data.get("viral_score", 0)),
                    clip_data.get("factors", {}),
                    clip_data.get("confidence", 0),
                    clip_data.get("editorial_score_version", "v1-explainable"),
                    review_flags=clip_data.get("review_flags", {}),
                    review_metadata={
                        "candidate_origin": clip_data.get("candidate_origin"),
                        "selection_source": settings.get("ai_backend", "local"),
                        "confidence": clip_data.get("confidence", 0),
                    },
                )

            ctx.update(stage="subtitles", progress=86, message="Legendas processadas")
            ctx.check_cancel()

            # ── Step 6/6: Optional publication metadata ──
            if settings.get("generate_seo_metadata", False):
                emit_progress("━━━ ETAPA 6/6: Gerando metadados opcionais ━━━", "info")
                from modules.ai_backend import AIBackend
                ai = AIBackend(
                    backend=settings.get("ai_backend", "ollama"),
                    settings=settings,
                )

                for res in results:
                    ctx.check_cancel()
                    text = res.get("text", "")
                    if text and res.get("clip_id"):
                        try:
                            seo = ai.generate_seo_content(
                                text,
                                channel_context=settings.get("channel_context", ""),
                                emit_progress=emit_progress,
                            )
                            if seo:
                                update_clip_seo(
                                    res["clip_id"],
                                    seo.get("titles", []),
                                    seo.get("tags", []),
                                    seo.get("description", ""),
                                    seo.get("hashtags", []),
                                )
                                res["seo"] = seo
                        except Exception as e:
                            emit_progress(f"Erro nos metadados opcionais do clip {res.get('clip_id')}: {str(e)}", "warning")
                ctx.update(stage="optional_metadata", progress=96, message="Metadados opcionais processados")
            else:
                emit_progress("━━━ ETAPA 6/6: Metadados de publicação desativados; fluxo focado em edição ━━━", "info")
                ctx.update(stage="editing_complete", progress=96, message="Fluxo de edição concluído")
            ctx.check_cancel()
            update_project_status(project_id, "completed")

            clip_results = []
            for i, res in enumerate(results):
                clip_info = top_clips[i] if i < len(top_clips) else {}
                planned_framing = framing_by_index.get(i, {
                    "mode": "original",
                    "reason": "composição original preservada por segurança",
                })
                applied_framing = {
                    **planned_framing,
                    "mode": res.get("framing_mode") or planned_framing.get("mode", "original"),
                    "reason": res.get("framing_reason") or planned_framing.get("reason", "composição original preservada por segurança"),
                }
                if res.get("framing_confidence") is not None:
                    applied_framing["confidence"] = res.get("framing_confidence")
                clip_results.append({
                    "path": os.path.relpath(res["path"], WORKSPACE_DIR),
                    "subtitled_path": os.path.relpath(res["subtitled_path"], WORKSPACE_DIR) if res.get("subtitled_path") else None,
                    "start": res["start"],
                    "end": res["end"],
                    "duration": res["duration"],
                    "viral_score": clip_info.get("viral_score", 0),
                    "editorial_potential_score": clip_info.get("editorial_potential_score", clip_info.get("viral_score", 0)),
                    "editorial_score_version": clip_info.get("editorial_score_version", "v1-explainable"),
                    "confidence": clip_info.get("confidence", 0),
                    "factors": clip_info.get("factors", {}),
                    "has_hook": clip_info.get("has_hook", False),
                    "breakdown": clip_info.get("breakdown", {}),
                    "title": clip_info.get("title", ""),
                    "source": clip_info.get("source", "nlp"),
                    "candidate_origin": clip_info.get("candidate_origin", "local_primary"),
                    "candidate_origin_label": clip_info.get("candidate_origin_label", "Origem local registrada"),
                    "candidate_origin_note": clip_info.get("candidate_origin_note", "Origem registrada para transparência da revisão."),
                    "political_signals": clip_info.get("political_signals", {}),
                    "review_flags": clip_info.get("review_flags", {}),
                    "closure_type": clip_info.get("closure_type", ""),
                    "starts_mid_sentence": bool(clip_info.get("starts_mid_sentence")),
                    "starts_with_context_reference": bool(clip_info.get("starts_with_context_reference")),
                    "payoff_weak_ending": bool(clip_info.get("payoff_weak_ending")),
                    "question_detected": bool(clip_info.get("question_detected")),
                    "question_answer_complete": bool(clip_info.get("question_answer_complete")),
                    "evidence_present": bool(clip_info.get("evidence_present")),
                    "payoff_complete": bool(clip_info.get("payoff_complete")),
                    "context_complete": bool(clip_info.get("context_complete")),
                    "duration_fit": clip_info.get("duration_fit"),
                    "duration_preference": clip_info.get("duration_preference", {}),
                    "transcript_segments": clip_segments,
                    "speaker": clip_info.get("speaker", ""),
                    "speaker_confidence": clip_info.get("speaker_confidence"),
                    "overlap_suspected": clip_info.get("overlap_suspected", False),
                    "multimodal_identity_status": clip_info.get("multimodal_identity_status", ""),
                    "multimodal_identity_confidence": clip_info.get("multimodal_identity_confidence"),
                    "visual_observation_review_required": bool(clip_info.get("visual_observation_review_required")),
                    "visual_observation_review_reason": clip_info.get("visual_observation_review_reason", ""),
                    "editorial_block": build_editorial_block({
                        **clip_info,
                        "start": res.get("start"),
                        "end": res.get("end"),
                        "duration": res.get("duration"),
                        "review_status": "pending",
                    }),
                    "text": res.get("text", ""),
                    "seo": res.get("seo", {}),
                    "clip_id": res.get("clip_id"),
                    "framing": applied_framing,
                })

            # Report where files are saved
            save_location = output_dir if output_dir else EXPORT_DIR
            emit_progress(f"Clips salvos em: {save_location}", "info")

            emit_status("complete_done", {
                "project_id": project_id,
                "clips": clip_results,
                "total_clips": len(clip_results),
                "video_layout": video_layout,
                "output_dir": save_location,
            })
            emit_progress(f"PROCESSO COMPLETO! {len(clip_results)} clips gerados, ranqueados e otimizados.", "success")

        except JobCancelled:
            emit_progress("Processo completo cancelado pelo usuário.", "warning")
            emit_status("cancelled", {})
            raise
        except Exception as e:
            emit_progress(f"Erro no processo completo: {str(e)}", "error")
            emit_status("error", {"message": str(e)})
            import traceback
            traceback.print_exc()
            raise
        finally:
            current_task["active"] = False

    if current_task["active"]:
        return jsonify({"error": "Ja existe um processamento em andamento"}), 409

    job = job_manager.submit("process_complete", task)
    return jsonify({
        "success": True,
        "message": "Processo completo iniciado",
        "job_id": job["id"],
        "state": job["state"],
    })


@app.route("/api/process/cancel", methods=["POST"])
def api_cancel():
    data = request.get_json(silent=True) or {}
    job_id = data.get("job_id")
    if job_id:
        try:
            return jsonify(job_manager.request_cancel(job_id))
        except KeyError:
            return jsonify({"error": "Job não encontrado"}), 404
    active_job_id = current_task.get("job_id")
    if active_job_id:
        try:
            return jsonify(job_manager.request_cancel(active_job_id))
        except KeyError:
            pass
    current_task["cancel"] = True
    return jsonify({"success": True, "message": "Cancelamento legado solicitado"})


# ─── WebSocket ───

# --- API: Ollama Status ---

@app.route("/api/ollama/status", methods=["GET"])
def api_ollama_status():
    settings = get_all_settings()
    status = _check_ai_status(settings)
    return jsonify(status)


# --- API: Open Folder / external output files ---

def _is_under(path, root):
    try:
        return os.path.commonpath([os.path.realpath(path), os.path.realpath(root)]) == os.path.realpath(root)
    except ValueError:
        return False


@app.route("/api/output_file", methods=["GET"])
def api_output_file():
    requested = str(request.args.get("path", "") or "").strip()
    if not requested:
        return jsonify({"error": "Arquivo não informado"}), 400
    target = os.path.abspath(os.path.expanduser(requested)) if os.path.isabs(requested) else _workspace_input_path(requested)
    settings = get_all_settings()
    allowed_roots = _allowed_media_roots(settings) + [settings.get("output_dir") or EXPORT_DIR]
    if not target or not os.path.isfile(target) or not any(_is_under(target, root) for root in allowed_roots if root):
        return jsonify({"error": "Arquivo não encontrado ou fora dos destinos permitidos"}), 404
    return send_file(target, conditional=True)


@app.route("/api/open_folder", methods=["POST"])
def api_open_folder():
    data = request.get_json(silent=True) or {}
    requested = str(data.get("path", "") or "").strip()
    if not requested:
        folder_path = EXPORT_DIR
    elif os.path.isabs(requested):
        folder_path = os.path.abspath(os.path.expanduser(requested))
    else:
        try:
            folder_path = safe_workspace_path(WORKSPACE_DIR, requested, allow_missing=False)
        except (UnsafePathError, FileNotFoundError):
            return jsonify({"error": "Pasta nao encontrada ou caminho invalido"}), 404

    if not os.path.isdir(folder_path):
        return jsonify({"error": "Pasta nao encontrada"}), 404
    settings = get_all_settings()
    allowed_roots = _allowed_media_roots(settings) + [settings.get("output_dir") or EXPORT_DIR]
    if not any(_is_under(folder_path, root) for root in allowed_roots if root):
        return jsonify({"error": "Pasta fora dos destinos configurados"}), 403

    try:
        open_local_path(folder_path)
        try:
            display_path = os.path.relpath(folder_path, WORKSPACE_DIR)
        except ValueError:
            display_path = folder_path
        return jsonify({"success": True, "path": display_path})
    except (FileNotFoundError, OSError) as exc:
        return jsonify({"error": "Não foi possível abrir a pasta", "detail": str(exc)[:200]}), 500


@socketio.on("connect")
def handle_connect():
    emit(
        "connected",
        {
            "message": f"Conectado ao Furia Clips · Versão {PROGRAM_VERSION} · revisão {PROGRAM_REVISION}",
            "program_version": PROGRAM_VERSION,
            "program_revision": PROGRAM_REVISION,
        },
    )
    # Send AI status on connect
    settings = get_all_settings()
    status = _check_ai_status(settings)
    emit("ai_status", status)
    # Also emit as ollama_status for backward compatibility
    emit("ollama_status", status)


@socketio.on("disconnect")
def handle_disconnect():
    pass


@socketio.on("check_ollama")
def handle_check_ollama():
    settings = get_all_settings()
    status = _check_ai_status(settings)
    emit("ai_status", status)
    emit("ollama_status", status)


# --- Helpers ---

def _check_ai_status(settings):
    """Check the selected AI backend without making any backend mandatory."""
    ai_backend = settings.get("ai_backend", "gemini")
    api_key = str(settings.get("gemini_api_key", "") or "").strip()
    ollama_url = settings.get("ollama_url", "http://localhost:11434")
    model = settings.get("ollama_model", "llama3.2:3b")

    # In automatic mode, use Gemini only when an existing key is available.
    if ai_backend in ("auto", "gemini") and api_key:
        try:
            resp = requests.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
                timeout=5
            )
            if resp.status_code == 200:
                return {
                    "connected": True,
                    "mode": "gemini",
                    "model": _configured_gemini_model(settings),
                    "model_available": True,
                    "status": "connected",
                    "backend": "gemini",
                    "mode_label": "Gemini Flash (Online)",
                }
        except Exception:
            pass

    # Ollama is optional and is checked for automatic, Gemini, and Ollama modes.
    if ai_backend in ("auto", "gemini", "ollama"):
        try:
            resp = requests.get(f"{ollama_url}/api/tags", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                has_model = any(model.split(":")[0] in m for m in models)
                return {
                    "connected": True,
                    "mode": "llm",
                    "model": model,
                    "model_available": has_model,
                    "available_models": models,
                    "status": "connected",
                    "backend": "ollama",
                    "mode_label": "IA Inteligente (Ollama)",
                }
        except Exception:
            pass

    return {
        "connected": False,
        "mode": "nlp",
        "model": model,
        "model_available": False,
        "available_models": [],
        "status": "no_key" if ai_backend == "gemini" and not api_key else "offline",
        "backend": "auto" if ai_backend == "auto" else ai_backend,
        "mode_label": "NLP local (sem chave ou serviço externo)",
    }


def _check_ollama_status(settings):
    """Legacy wrapper for Ollama status check."""
    return _check_ai_status(settings)


def _translate_error(error_msg):
    """Translate technical errors to user-friendly Portuguese messages."""
    error_lower = error_msg.lower()

    if "audio" in error_lower and ("stream" in error_lower or "contem" in error_lower):
        return ERROR_MESSAGES["no_audio"]
    if "codec" in error_lower or "unsupported" in error_lower or "invalid data" in error_lower:
        return ERROR_MESSAGES["unsupported_format"]
    if "ffmpeg" in error_lower and "not found" in error_lower:
        return ERROR_MESSAGES["ffmpeg_not_found"]
    if "no such file" in error_lower or "not found" in error_lower:
        return ERROR_MESSAGES["file_not_found"]
    if "no space" in error_lower or "disk full" in error_lower:
        return ERROR_MESSAGES["disk_full"]
    if "timeout" in error_lower or "timed out" in error_lower:
        return ERROR_MESSAGES["timeout"]

    # Return original if no translation found, but clean it up
    if len(error_msg) > 300:
        return error_msg[:300] + "..."
    return error_msg


def _human_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.1f} {units[i]}"


# --- Main ---

if __name__ == "__main__":
    init_db()
    _sync_env_key_to_db()

    # Startup AI check
    settings = get_all_settings()
    ai_status = _check_ai_status(settings)
    print("\n" + "=" * 50)
    print("   FURIA CLIPS - Corte. Ranqueie. Domine.")
    print(f"   [Versão] {PROGRAM_VERSION} · revisão {PROGRAM_REVISION}")
    print("=" * 50)
    backend = ai_status.get("backend", "gemini")
    if ai_status.get("mode") == "gemini" and ai_status["connected"]:
        print("   [IA] Gemini Flash conectado!")
        print("   [IA] Prioridade: analise online multimodal")
    elif ai_status.get("mode") == "llm" and ai_status["connected"]:
        print(f"   [IA] Ollama conectado! Modelo: {ai_status['model']}")
        print("   [IA] Fallback online indisponível; análise local avançada ativa")
    elif ai_status.get("status") == "no_key":
        print("   [IA] Gemini Online é a prioridade, mas nenhuma API key foi configurada.")
        print("   [IA] Fallback local ativo; configure a chave em Backend de IA para maior qualidade.")
    else:
        print("   [IA] Gemini Online indisponível; fallback NLP/Whisper local ativo.")
    host = os.environ.get("FURIA_HOST", "127.0.0.1")
    port = int(os.environ.get("FURIA_PORT", "3001"))
    print(f"   Acesse: http://{host}:{port}")
    print("=" * 50 + "\n")
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)
