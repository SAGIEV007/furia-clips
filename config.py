import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")
UPLOAD_DIR = os.path.join(WORKSPACE_DIR, "uploads")
PROCESSED_DIR = os.path.join(WORKSPACE_DIR, "processed")
EXPORT_DIR = os.path.join(WORKSPACE_DIR, "exports")
THUMBNAIL_DIR = os.path.join(WORKSPACE_DIR, "thumbnails")
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "furia_clips.db")

for d in [WORKSPACE_DIR, UPLOAD_DIR, PROCESSED_DIR, EXPORT_DIR, THUMBNAIL_DIR, DATA_DIR]:
    os.makedirs(d, exist_ok=True)

DEFAULT_SETTINGS = {
    "whisper_model": "small",
    "cut_method": "intelligent",
    "cut_duration": 45,
    "min_silence_duration": 0.5,
    "silence_threshold": -35,
    "padding": 0.25,
    "language": "pt",
    "ai_correction": True,
    "ai_backend": "auto",
    "ollama_model": "llama3.2:3b",
    "ollama_url": "http://localhost:11434",
    "claude_api_key": "",
    "gemini_api_key": "",
    "subtitle_font": "Arial",
    "subtitle_font_size": 28,
    "subtitle_color": "#FFFFFF",
    "subtitle_highlight_color": "#FFD700",
    "subtitle_alert_color": "#FF3B30",
    "subtitle_border_color": "#000000",
    "subtitle_border_size": 1.5,
    "subtitle_highlight_size": 5,
    "subtitle_position": "bottom",
    "subtitle_style": "word_by_word",
    "channel_context": "Canal de politica brasileira conservadora. Foco em cortes do Renan Santos e MBL. Conteudo voltado para engajamento, clareza e viralizacao em plataformas de video curto.",
    "editorial_profile": "renan_santos_politics",
    "editorial_profile_label": "Cortes politicos — Renan Santos/MBL",
    "political_audio_policy": "voice_and_ambience",
    "political_caption_mode": "keyword_impact",
    "export_format": "mp4",
    "export_quality": "high",
    "render_preset": "shorts",
    "output_dir": "",
    "source_download_dir": "",
    "source_max_height": 1080,
}

ALLOWED_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"}

MAX_UPLOAD_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB
