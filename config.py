import json
import os
import sqlite3
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")
UPLOAD_DIR = os.path.join(WORKSPACE_DIR, "uploads")
PROCESSED_DIR = os.path.join(WORKSPACE_DIR, "processed")
EXPORT_DIR = os.path.join(WORKSPACE_DIR, "exports")
THUMBNAIL_DIR = os.path.join(WORKSPACE_DIR, "thumbnails")

# Dados editoriais pertencem ao usuário, não ao checkout do GitHub. Assim, uma
# atualização que substitua a pasta do programa não apaga decisões, projetos,
# transcrições, calibração ou fila persistente. A variável permite que equipes
# usem outro disco, OneDrive ou um diretório compartilhado deliberadamente.
PERSISTENT_DATA_SCHEMA_VERSION = 1
LEGACY_DATA_DIR = os.path.join(BASE_DIR, "data")
LEGACY_DB_PATH = os.path.join(LEGACY_DATA_DIR, "furia_clips.db")


def _resolve_persistent_data_dir():
    configured = str(os.environ.get("FURIA_CLIPS_DATA_DIR", "") or "").strip()
    if configured:
        return os.path.abspath(os.path.expanduser(configured))
    return os.path.join(os.path.expanduser("~"), "FuriaClipsData")


PERSISTENT_DATA_DIR = _resolve_persistent_data_dir()
PERSISTENT_DATABASE_DIR = os.path.join(PERSISTENT_DATA_DIR, "database")
PERSISTENT_PROJECTS_DIR = os.path.join(PERSISTENT_DATA_DIR, "projects")
PERSISTENT_TRANSCRIPTS_DIR = os.path.join(PERSISTENT_DATA_DIR, "transcripts")
PERSISTENT_ANALYSES_DIR = os.path.join(PERSISTENT_DATA_DIR, "analyses")
PERSISTENT_DECISIONS_DIR = os.path.join(PERSISTENT_DATA_DIR, "clip_decisions")
PERSISTENT_EXPORTS_DIR = os.path.join(PERSISTENT_DATA_DIR, "exports")
PERSISTENT_BACKUPS_DIR = os.path.join(PERSISTENT_DATA_DIR, "backups")
PERSISTENT_MEDIA_INDEX_DIR = os.path.join(PERSISTENT_DATA_DIR, "media_index")
PERSISTENT_SCHEMA_PATH = os.path.join(PERSISTENT_DATA_DIR, "schema_version.json")

# Mantém DATA_DIR como alias de compatibilidade para os módulos existentes.
DATA_DIR = PERSISTENT_DATABASE_DIR
DB_PATH = os.path.join(PERSISTENT_DATABASE_DIR, "editorial_learning.sqlite3")


def _sqlite_snapshot(source_path, destination_path):
    """Create a consistent SQLite copy, including changes held in WAL mode."""
    source = sqlite3.connect(source_path)
    destination = sqlite3.connect(destination_path)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()


def _write_persistent_schema_metadata(migrated_from=None):
    metadata = {
        "schema_version": PERSISTENT_DATA_SCHEMA_VERSION,
        "data_dir": PERSISTENT_DATA_DIR,
        "database": os.path.basename(DB_PATH),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if migrated_from:
        metadata["migrated_from"] = migrated_from
    elif os.path.isfile(PERSISTENT_SCHEMA_PATH):
        try:
            with open(PERSISTENT_SCHEMA_PATH, "r", encoding="utf-8") as handle:
                previous = json.load(handle)
            metadata["created_at"] = previous.get("created_at")
            metadata["migrated_from"] = previous.get("migrated_from")
        except (OSError, ValueError, TypeError):
            pass
    metadata["created_at"] = metadata.get("created_at") or metadata["updated_at"]
    with open(PERSISTENT_SCHEMA_PATH, "w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)


def _ensure_persistent_data_layout():
    directories = [
        WORKSPACE_DIR,
        UPLOAD_DIR,
        PROCESSED_DIR,
        EXPORT_DIR,
        THUMBNAIL_DIR,
        PERSISTENT_DATA_DIR,
        PERSISTENT_DATABASE_DIR,
        PERSISTENT_PROJECTS_DIR,
        PERSISTENT_TRANSCRIPTS_DIR,
        PERSISTENT_ANALYSES_DIR,
        PERSISTENT_DECISIONS_DIR,
        PERSISTENT_EXPORTS_DIR,
        PERSISTENT_BACKUPS_DIR,
        PERSISTENT_MEDIA_INDEX_DIR,
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

    # Migra uma instalação anterior sem destruir a cópia existente dentro do
    # repositório. O snapshot preserva alterações ainda presentes no WAL.
    if not os.path.exists(DB_PATH) and os.path.isfile(LEGACY_DB_PATH):
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        migration_snapshot = os.path.join(PERSISTENT_BACKUPS_DIR, f"legacy-furia-clips-{timestamp}.sqlite3")
        _sqlite_snapshot(LEGACY_DB_PATH, DB_PATH)
        _sqlite_snapshot(LEGACY_DB_PATH, migration_snapshot)
        _write_persistent_schema_metadata(migrated_from=LEGACY_DB_PATH)
    else:
        _write_persistent_schema_metadata()


def get_persistent_data_status():
    """Expose non-sensitive storage health for the UI and support diagnostics."""
    return {
        "data_dir": PERSISTENT_DATA_DIR,
        "database_path": DB_PATH,
        "backup_dir": PERSISTENT_BACKUPS_DIR,
        "database_exists": os.path.isfile(DB_PATH),
        "legacy_database_detected": os.path.isfile(LEGACY_DB_PATH),
        "using_custom_data_dir": bool(str(os.environ.get("FURIA_CLIPS_DATA_DIR", "") or "").strip()),
        "schema_version": PERSISTENT_DATA_SCHEMA_VERSION,
    }


_ensure_persistent_data_layout()

WHISPER_PRESETS = {
    "default": {
        "beam_size": 5,
        "chunk_length": 30,
        "vad_min_silence_ms": 500,
        "temperature": 0.0,
    },
    "high_accuracy": {
        "beam_size": 10,
        "chunk_length": 15,
        "vad_min_silence_ms": 400,
        "temperature": 0.0,
    },
}


DEFAULT_SETTINGS = {
    "whisper_model": "small",
    "whisper_word_timestamps": False,
    "whisper_beam_size": 5,
    "whisper_condition_on_previous_text": True,
    "whisper_vad_min_silence_ms": 500,
    "whisper_vad_speech_pad_ms": 200,
    "whisper_temperature": 0.0,
    "whisper_chunk_length": 30,
    "whisper_preset": "default",
    "whisper_device": "auto",
    "whisper_long_video_threshold_minutes": 45,
    "whisper_long_video_model": "base",
    "cut_method": "intelligent",
    "cut_duration": 45,
    "min_silence_duration": 0.5,
    "silence_threshold": -35,
    "padding": 0.25,
    "language": "pt",
    "transcription_source": "auto",
    "ai_correction": True,
    "ai_backend": "auto",
    "ollama_model": "llama3.2:3b",
    "ollama_url": "http://localhost:11434",
    "claude_api_key": "",
    "gemini_api_key": "",
    "gemini_model": "gemini-2.5-flash",
    "subtitle_font": "Montserrat",
    "subtitle_font_size": 56,
    "subtitle_color": "#FFFFFF",
    "subtitle_highlight_color": "#FFD700",
    "subtitle_alert_color": "#FF3B30",
    "subtitle_border_color": "#000000",
    "subtitle_border_size": 1.5,
    "subtitle_back_color": "#80000000",
    "subtitle_highlight_size": 5,
    "subtitle_position": "bottom",
    "subtitle_style": "word_by_word",
    "channel_context": "Canal de politica brasileira conservadora. Foco em cortes do Renan Santos e MBL. Conteudo voltado para engajamento, clareza e viralizacao em plataformas de video curto.",
    "editorial_profile": "renan_santos_politics",
    "editorial_profile_label": "Cortes politicos — Renan Santos/MBL",
    "campaign_hub_account": "@renansantosmbl",
    "editorial_focus": "auto",
    "gemini_manual_video_analysis": False,
    "political_audio_policy": "voice_and_ambience",
    "political_caption_mode": "keyword_impact",
    "export_format": "mp4",
    "export_quality": "high",
    "render_preset": "shorts",
    "output_dir": "",
    "source_download_dir": "",
    "source_max_height": 1080,
    "source_download_retries": 3,
    "generate_seo_metadata": False,
}

ALLOWED_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"}

MAX_UPLOAD_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB
