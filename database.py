import sqlite3
import json
import os
from datetime import datetime
from config import DB_PATH, DEFAULT_SETTINGS


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            source_video TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS clips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            start_time REAL NOT NULL,
            end_time REAL NOT NULL,
            duration REAL NOT NULL,
            viral_score INTEGER DEFAULT 0,
            has_hook INTEGER DEFAULT 0,
            emotional_intensity REAL DEFAULT 0,
            transcript TEXT,
            suggested_titles TEXT,
            suggested_tags TEXT,
            suggested_description TEXT,
            suggested_hashtags TEXT,
            thumbnail_path TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS transcriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            segments TEXT NOT NULL,
            full_text TEXT NOT NULL,
            language TEXT DEFAULT 'pt',
            model_used TEXT DEFAULT 'small',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS processing_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            status TEXT DEFAULT 'completed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
    """)

    for key, value in DEFAULT_SETTINGS.items():
        cursor.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, json.dumps(value))
        )

    conn.commit()
    conn.close()


def get_setting(key):
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    if row:
        return json.loads(row["value"])
    return DEFAULT_SETTINGS.get(key)


def set_setting(key, value):
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, json.dumps(value))
    )
    conn.commit()
    conn.close()


def get_all_settings():
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    settings = {}
    for row in rows:
        settings[row["key"]] = json.loads(row["value"])
    for key, value in DEFAULT_SETTINGS.items():
        if key not in settings:
            settings[key] = value

    # Override Gemini API key from environment if available and not set in DB
    env_key = os.environ.get("GEMINI_API_KEY", "")
    if env_key and not settings.get("gemini_api_key"):
        settings["gemini_api_key"] = env_key
        # Auto-switch to Gemini if key is available and backend is default
        if settings.get("ai_backend") == "ollama":
            settings["ai_backend"] = "gemini"

    return settings


def create_project(name, source_video):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO projects (name, source_video, status) VALUES (?, ?, 'pending')",
        (name, source_video)
    )
    project_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return project_id


def get_project(project_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_projects():
    conn = get_db()
    rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_project_status(project_id, status):
    conn = get_db()
    conn.execute(
        "UPDATE projects SET status = ?, updated_at = ? WHERE id = ?",
        (status, datetime.now().isoformat(), project_id)
    )
    conn.commit()
    conn.close()


def save_clip(project_id, file_path, start_time, end_time, duration,
              viral_score=0, has_hook=False, emotional_intensity=0.0, transcript=""):
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO clips (project_id, file_path, start_time, end_time, duration,
           viral_score, has_hook, emotional_intensity, transcript)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (project_id, file_path, start_time, end_time, duration,
         viral_score, int(has_hook), emotional_intensity, transcript)
    )
    clip_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return clip_id


def get_clips(project_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM clips WHERE project_id = ? ORDER BY viral_score DESC",
        (project_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_clip_seo(clip_id, titles, tags, description, hashtags):
    conn = get_db()
    conn.execute(
        """UPDATE clips SET suggested_titles = ?, suggested_tags = ?,
           suggested_description = ?, suggested_hashtags = ? WHERE id = ?""",
        (json.dumps(titles), json.dumps(tags), description, json.dumps(hashtags), clip_id)
    )
    conn.commit()
    conn.close()


def update_clip_thumbnail(clip_id, thumbnail_path):
    conn = get_db()
    conn.execute(
        "UPDATE clips SET thumbnail_path = ? WHERE id = ?",
        (thumbnail_path, clip_id)
    )
    conn.commit()
    conn.close()


def save_transcription(project_id, segments, full_text, language, model_used):
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO transcriptions (project_id, segments, full_text, language, model_used)
           VALUES (?, ?, ?, ?, ?)""",
        (project_id, json.dumps(segments), full_text, language, model_used)
    )
    tid = cursor.lastrowid
    conn.commit()
    conn.close()
    return tid


def get_transcription(project_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM transcriptions WHERE project_id = ? ORDER BY id DESC LIMIT 1",
        (project_id,)
    ).fetchone()
    conn.close()
    if row:
        result = dict(row)
        result["segments"] = json.loads(result["segments"])
        return result
    return None


def log_action(project_id, action, details="", status="completed"):
    conn = get_db()
    conn.execute(
        "INSERT INTO processing_history (project_id, action, details, status) VALUES (?, ?, ?, ?)",
        (project_id, action, details, status)
    )
    conn.commit()
    conn.close()
