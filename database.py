import sqlite3
import json
import os
import hashlib
from datetime import datetime
from config import DB_PATH, DEFAULT_SETTINGS


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _editorial_clip_key(source_video, start_time, end_time, transcript):
    """Return a stable identity independent of the rendered output filename."""
    canonical = "|".join([
        str(source_video or "").replace("\\\\", "/").strip().lower(),
        f"{float(start_time or 0):.3f}",
        f"{float(end_time or 0):.3f}",
        " ".join(str(transcript or "").split()).lower(),
    ])
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


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
            score_factors TEXT,
            score_confidence REAL DEFAULT 0,
            editorial_score_version TEXT,
            editorial_key TEXT,
            review_status TEXT DEFAULT 'pending',
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

        CREATE TABLE IF NOT EXISTS clip_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clip_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            adjustments TEXT,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (clip_id) REFERENCES clips(id)
        );
    """)

    existing_columns = {
        row["name"] for row in cursor.execute("PRAGMA table_info(clips)").fetchall()
    }
    migrations = {
        "score_factors": "ALTER TABLE clips ADD COLUMN score_factors TEXT",
        "score_confidence": "ALTER TABLE clips ADD COLUMN score_confidence REAL DEFAULT 0",
        "editorial_score_version": "ALTER TABLE clips ADD COLUMN editorial_score_version TEXT",
        "editorial_key": "ALTER TABLE clips ADD COLUMN editorial_key TEXT",
        "review_status": "ALTER TABLE clips ADD COLUMN review_status TEXT DEFAULT 'pending'",
    }
    for column, statement in migrations.items():
        if column not in existing_columns:
            cursor.execute(statement)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clips_editorial_key ON clips(project_id, editorial_key)")
    missing_keys = cursor.execute(
        """SELECT clips.id, projects.source_video, clips.start_time, clips.end_time, clips.transcript
           FROM clips JOIN projects ON projects.id = clips.project_id
           WHERE clips.editorial_key IS NULL OR clips.editorial_key = ''"""
    ).fetchall()
    for row in missing_keys:
        cursor.execute(
            "UPDATE clips SET editorial_key = ? WHERE id = ?",
            (_editorial_clip_key(row["source_video"], row["start_time"], row["end_time"], row["transcript"]), row["id"]),
        )

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

    # Disponibiliza a chave do ambiente sem alterar o backend escolhido.
    # O modo "auto" decide em tempo de execução se Gemini, Ollama ou NLP local
    # está realmente disponível.
    env_key = os.environ.get("GEMINI_API_KEY", "")
    if env_key and not settings.get("gemini_api_key"):
        settings["gemini_api_key"] = env_key

    # Migra a configuração antiga que selecionava Gemini sem chave para o modo
    # automático, mantendo o funcionamento local em instalações já existentes.
    if settings.get("ai_backend") == "gemini" and not settings.get("gemini_api_key"):
        settings["ai_backend"] = "auto"

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
    rows = conn.execute(
        """SELECT projects.*,
                  (SELECT COUNT(*) FROM clips WHERE clips.project_id = projects.id) AS clip_count,
                  (SELECT COUNT(*) FROM clips WHERE clips.project_id = projects.id AND review_status = 'approved') AS approved_count,
                  (SELECT COUNT(*) FROM clips WHERE clips.project_id = projects.id AND review_status IN ('pending', 'needs_review')) AS review_count
           FROM projects
           ORDER BY created_at DESC"""
    ).fetchall()
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
    source_row = conn.execute("SELECT source_video FROM projects WHERE id = ?", (project_id,)).fetchone()
    source_video = source_row["source_video"] if source_row else ""
    editorial_key = _editorial_clip_key(source_video, start_time, end_time, transcript)
    existing = conn.execute(
        "SELECT id FROM clips WHERE project_id = ? AND editorial_key = ? ORDER BY id LIMIT 1",
        (project_id, editorial_key),
    ).fetchone()
    if existing:
        clip_id = existing["id"]
        conn.execute(
            """UPDATE clips SET file_path = ?, start_time = ?, end_time = ?, duration = ?,
               viral_score = ?, has_hook = ?, emotional_intensity = ?, transcript = ? WHERE id = ?""",
            (file_path, start_time, end_time, duration, viral_score, int(has_hook), emotional_intensity, transcript, clip_id),
        )
    else:
        cursor = conn.execute(
            """INSERT INTO clips (project_id, file_path, start_time, end_time, duration,
               viral_score, has_hook, emotional_intensity, transcript, editorial_key)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (project_id, file_path, start_time, end_time, duration,
             viral_score, int(has_hook), emotional_intensity, transcript, editorial_key)
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


def update_clip_editorial_score(clip_id, score, factors, confidence, version="v1-explainable"):
    conn = get_db()
    conn.execute(
        """UPDATE clips SET viral_score = ?, score_factors = ?,
           score_confidence = ?, editorial_score_version = ? WHERE id = ?""",
        (int(score), json.dumps(factors or {}), float(confidence or 0), version, clip_id)
    )
    conn.commit()
    conn.close()


def update_clip_review_status(clip_id, status):
    if status not in {"pending", "approved", "rejected", "needs_review"}:
        raise ValueError("Estado de revisão inválido")
    conn = get_db()
    conn.execute("UPDATE clips SET review_status = ? WHERE id = ?", (status, clip_id))
    conn.commit()
    conn.close()


def save_clip_feedback(clip_id, action, adjustments=None, note=""):
    if action not in {"approved", "rejected", "needs_review", "adjusted", "rendered"}:
        raise ValueError("Ação de feedback inválida")
    conn = get_db()
    status = action if action in {"approved", "rejected", "needs_review"} else "needs_review"
    conn.execute(
        "INSERT INTO clip_feedback (clip_id, action, adjustments, note) VALUES (?, ?, ?, ?)",
        (clip_id, action, json.dumps(adjustments or {}), note or ""),
    )
    conn.execute("UPDATE clips SET review_status = ? WHERE id = ?", (status, clip_id))
    conn.commit()
    conn.close()


def get_clip_feedback(clip_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM clip_feedback WHERE clip_id = ? ORDER BY created_at DESC", (clip_id,)
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["adjustments"] = json.loads(item.get("adjustments") or "{}")
        except json.JSONDecodeError:
            item["adjustments"] = {}
        result.append(item)
    return result


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


def get_feedback_calibration(min_samples=12, min_per_outcome=3):
    """Summarize final review decisions without claiming statistical certainty.

    The result becomes eligible only when there are enough approved and rejected
    clips. Pending and context-review items are intentionally excluded because
    they are not final editorial verdicts.
    """
    conn = get_db()
    rows = conn.execute(
        """SELECT viral_score, score_factors, review_status
           FROM clips
           WHERE review_status IN ('approved', 'rejected')"""
    ).fetchall()
    conn.close()

    groups = {"approved": [], "rejected": []}
    for row in rows:
        item = dict(row)
        try:
            factors = json.loads(item.get("score_factors") or "{}")
        except (TypeError, json.JSONDecodeError):
            factors = {}
        groups[item["review_status"]].append({
            "score": float(item.get("viral_score") or 0),
            "factors": {
                key: float(value)
                for key, value in factors.items()
                if isinstance(value, (int, float))
            },
        })

    approved = groups["approved"]
    rejected = groups["rejected"]
    sample_size = len(approved) + len(rejected)
    eligible = (
        sample_size >= int(min_samples)
        and len(approved) >= int(min_per_outcome)
        and len(rejected) >= int(min_per_outcome)
    )

    def mean(values):
        return sum(values) / len(values) if values else 0.0

    common_factors = set.intersection(
        *[set(item["factors"]) for item in approved + rejected]
    ) if approved and rejected else set()
    factor_deltas = {
        factor: round(
            mean([item["factors"][factor] for item in approved])
            - mean([item["factors"][factor] for item in rejected]),
            2,
        )
        for factor in sorted(common_factors)
    }

    return {
        "eligible": eligible,
        "sample_size": sample_size,
        "approved_count": len(approved),
        "rejected_count": len(rejected),
        "minimum_sample_size": int(min_samples),
        "score_gap": round(
            mean([item["score"] for item in approved])
            - mean([item["score"] for item in rejected]),
            2,
        ),
        "factor_deltas": factor_deltas,
    }



def get_daily_editorial_progress(target_min=39, target_max=50):
    """Summarize today's review workflow from persisted clip decisions.

    The dashboard deliberately counts only approved clips toward the publishing
    target. Pending and context-review clips remain visible as a revision queue,
    preventing the system from treating generated volume as completed work.
    """
    conn = get_db()
    rows = conn.execute(
        """SELECT review_status, COUNT(*) AS total
           FROM clips
           WHERE date(created_at, 'localtime') = date('now', 'localtime')
           GROUP BY review_status"""
    ).fetchall()
    conn.close()
    counts = {row["review_status"] or "pending": int(row["total"] or 0) for row in rows}
    approved = counts.get("approved", 0)
    pending = counts.get("pending", 0)
    needs_review = counts.get("needs_review", 0)
    rejected = counts.get("rejected", 0)
    return {
        "target_min": int(target_min),
        "target_max": int(target_max),
        "approved": approved,
        "pending": pending,
        "needs_review": needs_review,
        "rejected": rejected,
        "review_queue": pending + needs_review,
        "remaining_to_minimum": max(0, int(target_min) - approved),
        "progress_percent": round(min(100.0, approved / max(1, int(target_min)) * 100.0), 1),
        "target_reached": approved >= int(target_min),
    }
