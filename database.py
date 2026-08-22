import sqlite3
import json
import os
import hashlib
import math
from datetime import datetime
from config import DB_PATH, DEFAULT_SETTINGS


_ALLOWED_CANDIDATE_ORIGINS = {
    "gemini_primary",
    "ollama_primary",
    "local_primary",
    "local_fallback",
}
_ALLOWED_SELECTION_SOURCES = {"gemini", "llm", "nlp", "local"}
_ALLOWED_TRANSCRIPT_SOURCES = {"manual", "public_subtitle", "gemini_video", "whisper", "automatic", "unknown"}
_ALLOWED_CONTEXT_SOURCES = {"local_dossier", "multimodal_auxiliary", "none"}
_ALLOWED_COVERAGE_STATUSES = {"covered", "complete", "partial", "mismatch_suspected", "empty", "pending", "unknown"}
_SUPPORTED_CAMPAIGN_HUB_ACCOUNTS = {"@renansantosmbl", "@renansantosreserva", "@partidomissao"}
_DEFAULT_CAMPAIGN_HUB_ACCOUNT = "@renansantosmbl"


def _parse_optional_bool(value):
    """Return a parsed boolean or None without inventing a value for unknown input."""
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value != 0
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "sim", "on", "enabled"}:
        return True
    if normalized in {"0", "false", "no", "não", "nao", "off", "disabled"}:
        return False
    return None


def _normalize_campaign_hub_account(value):
    account = str(value or "").strip()
    return account if account in _SUPPORTED_CAMPAIGN_HUB_ACCOUNTS else _DEFAULT_CAMPAIGN_HUB_ACCOUNT



def _normalize_dedup_context(value):
    """Keep a small, non-textual editorial signature for cross-run dedupe."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}
    if not isinstance(value, dict):
        return {}
    result = {}
    for key in ("question_answer_complete", "payoff_complete", "qa_bridge"):
        parsed = _parse_optional_bool(value.get(key))
        if parsed is not None:
            result[key] = parsed
    for key in ("closure_type", "political_editorial_type"):
        text = str(value.get(key) or "").strip()[:64]
        if text:
            result[key] = text
    try:
        chapter_id = int(value.get("chapter_primary_id"))
    except (TypeError, ValueError):
        chapter_id = None
    if chapter_id is not None and 0 <= chapter_id <= 1_000_000:
        result["chapter_primary_id"] = chapter_id
    return result



def _normalize_scene_boundary_adjustment(value):
    """Keep only finite, outward-only scene snapping metadata."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}
    if not isinstance(value, dict):
        return {}
    result = {}
    applied = _parse_optional_bool(value.get("applied"))
    if applied is not None:
        result["applied"] = applied
    for key in ("original_start", "original_end", "adjusted_start", "adjusted_end"):
        try:
            number = float(value.get(key))
        except (TypeError, ValueError):
            continue
        if math.isfinite(number) and number >= 0:
            result[key] = round(number, 3)
    direction = str(value.get("direction") or "").strip()[:24]
    if direction == "outward_only":
        result["direction"] = direction
    if result.get("applied") and not all(
        key in result for key in ("original_start", "original_end", "adjusted_start", "adjusted_end")
    ):
        return {}
    return result



def _normalize_review_provenance(value):
    """Keep only bounded, non-sensitive origin fields for local calibration."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}
    if not isinstance(value, dict):
        return {}
    if isinstance(value.get("_review_metadata"), dict):
        value = value["_review_metadata"]
    result = {}
    origin = str(value.get("candidate_origin") or "").strip()[:40]
    if origin in _ALLOWED_CANDIDATE_ORIGINS:
        result["candidate_origin"] = origin
    source = str(value.get("selection_source") or "").strip()[:24]
    if source in _ALLOWED_SELECTION_SOURCES:
        result["selection_source"] = source
    try:
        confidence = float(value.get("confidence"))
    except (TypeError, ValueError):
        confidence = None
    if confidence is not None and math.isfinite(confidence):
        result["confidence"] = round(max(0.0, min(1.0, confidence)), 3)

    transcript_source = str(value.get("transcript_source") or "").strip()[:24]
    if transcript_source in _ALLOWED_TRANSCRIPT_SOURCES:
        result["transcript_source"] = transcript_source
    context_source = str(value.get("context_source") or "").strip()[:24]
    if context_source in _ALLOWED_CONTEXT_SOURCES:
        result["context_source"] = context_source
    coverage_status = str(value.get("transcript_coverage_status") or "").strip()[:32]
    if coverage_status in _ALLOWED_COVERAGE_STATUSES:
        result["transcript_coverage_status"] = coverage_status
    transcript_archive_present = _parse_optional_bool(value.get("transcript_archive_present"))
    if transcript_archive_present is not None:
        result["transcript_archive_present"] = transcript_archive_present
    semantic_identity_verified = _parse_optional_bool(value.get("transcript_semantic_identity_verified"))
    if semantic_identity_verified is not None:
        result["transcript_semantic_identity_verified"] = semantic_identity_verified
    try:
        transcript_end_ratio = float(value.get("transcript_end_ratio"))
    except (TypeError, ValueError):
        transcript_end_ratio = None
    if transcript_end_ratio is not None and math.isfinite(transcript_end_ratio):
        result["transcript_end_ratio"] = round(max(0.0, min(1.0, transcript_end_ratio)), 3)

    if isinstance(value.get("framing"), dict):
        raw_framing = value["framing"]
    elif any(key in value for key in ("framing_mode", "framing_reason", "framing_confidence", "framing_review_required")):
        raw_framing = value
    else:
        raw_framing = {}
    framing = {}
    framing_mode = str(raw_framing.get("mode") or raw_framing.get("framing_mode") or "").strip()[:32]
    if framing_mode in {"face_tracking", "original_16_9", "center_crop", "reframe_9_16", "original"}:
        framing["mode"] = framing_mode
    framing_reason = str(raw_framing.get("reason") or raw_framing.get("framing_reason") or "").strip()[:240]
    if framing_reason:
        framing["reason"] = framing_reason
    review_required = _parse_optional_bool(raw_framing.get("review_required", raw_framing.get("framing_review_required")))
    if review_required is not None:
        framing["review_required"] = review_required
    try:
        framing_confidence = float(raw_framing.get("confidence", raw_framing.get("framing_confidence")))
    except (TypeError, ValueError):
        framing_confidence = None
    if framing_confidence is not None and math.isfinite(framing_confidence):
        framing["confidence"] = round(max(0.0, min(1.0, framing_confidence)), 3)

    if framing:
        result["framing"] = framing
    return result


def _normalize_quality_scorecard(value):
    """Keep only bounded scorecard fields suitable for local persistence."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {}
    if not isinstance(value, dict):
        return {}
    result = {}
    for key in ("context", "editorial_strength", "technical", "confidence"):
        try:
            number = float(value.get(key))
        except (TypeError, ValueError):
            continue
        result[key] = round(max(0.0, min(100.0, number)), 1)
    status = str(value.get("status") or "").strip().lower()
    if status in {"candidate", "review_required"}:
        result["status"] = status
    gate_status = str(value.get("gate_status") or "").strip().lower()
    if gate_status in {"pass", "review_required", "blocked"}:
        result["gate_status"] = gate_status
    return result


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _source_signature(source_video):
    """Return a lightweight content signature for local media when available.

    It samples the beginning and end of the file instead of hashing a multi-hour
    video in full. Empty signatures remain supported for legacy projects and
    non-local sources.
    """
    path = str(source_video or "").strip()
    if not path or not os.path.isfile(path):
        return ""
    try:
        stat = os.stat(path)
        sample_size = 1024 * 1024
        digest = hashlib.sha256()
        digest.update(str(stat.st_size).encode("ascii"))
        with open(path, "rb") as handle:
            digest.update(handle.read(sample_size))
            if stat.st_size > sample_size:
                handle.seek(max(0, stat.st_size - sample_size))
                digest.update(handle.read(sample_size))
        return digest.hexdigest()[:32]
    except (OSError, ValueError):
        return ""


def get_source_signature(source_video):
    """Expose the bounded local media signature for source-identity contracts."""
    return _source_signature(source_video)


def _editorial_clip_key(source_video, start_time, end_time, transcript):
    """Return a stable identity independent of the rendered output filename."""
    canonical = "|".join([
        str(source_video or "").replace("\\", "/").strip().lower(),
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
            source_signature TEXT DEFAULT '',
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
            reason_code TEXT DEFAULT '',
            quality_tags TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (clip_id) REFERENCES clips(id)
        );

        CREATE TABLE IF NOT EXISTS headline_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clip_id INTEGER,
            editorial_key TEXT,
            format_id TEXT NOT NULL,
            artwork_text TEXT NOT NULL,
            action TEXT NOT NULL DEFAULT 'selected',
            topic TEXT,
            transcript_excerpt TEXT,
            mini_context TEXT,
            source TEXT DEFAULT 'headline_studio',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (clip_id) REFERENCES clips(id)
        );

        CREATE TABLE IF NOT EXISTS performance_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_key TEXT NOT NULL,
            platform TEXT NOT NULL,
            format_id TEXT DEFAULT 'unknown',
            published_at TIMESTAMP,
            collected_at TIMESTAMP NOT NULL,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            saves INTEGER DEFAULT 0,
            engagement_actions INTEGER DEFAULT 0,
            engagement_rate REAL,
            age_hours REAL,
            view_velocity_per_hour REAL,
            ranking_position INTEGER,
            xp REAL,
            collection_state TEXT DEFAULT 'observed',
            source TEXT DEFAULT 'manual_or_authorized_export',
            payload TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    existing_columns = {
        row["name"] for row in cursor.execute("PRAGMA table_info(clips)").fetchall()
    }
    project_columns = {
        row["name"] for row in cursor.execute("PRAGMA table_info(projects)").fetchall()
    }
    project_migrations = {
        "source_signature": "ALTER TABLE projects ADD COLUMN source_signature TEXT DEFAULT ''",
    }
    for column, statement in project_migrations.items():
        if column not in project_columns:
            cursor.execute(statement)

    migrations = {
        "score_factors": "ALTER TABLE clips ADD COLUMN score_factors TEXT",
        "score_confidence": "ALTER TABLE clips ADD COLUMN score_confidence REAL DEFAULT 0",
        "editorial_score_version": "ALTER TABLE clips ADD COLUMN editorial_score_version TEXT",
        "editorial_key": "ALTER TABLE clips ADD COLUMN editorial_key TEXT",
        "review_status": "ALTER TABLE clips ADD COLUMN review_status TEXT DEFAULT 'pending'",
    }
    feedback_columns = {
        row["name"] for row in cursor.execute("PRAGMA table_info(clip_feedback)").fetchall()
    }
    feedback_migrations = {
        "reason_code": "ALTER TABLE clip_feedback ADD COLUMN reason_code TEXT DEFAULT ''",
        "quality_tags": "ALTER TABLE clip_feedback ADD COLUMN quality_tags TEXT DEFAULT '[]'",
    }
    for column, statement in feedback_migrations.items():
        if column not in feedback_columns:
            cursor.execute(statement)

    headline_columns = {
        row["name"] for row in cursor.execute("PRAGMA table_info(headline_feedback)").fetchall()
    }
    headline_migrations = {
        "clip_id": "ALTER TABLE headline_feedback ADD COLUMN clip_id INTEGER",
        "editorial_key": "ALTER TABLE headline_feedback ADD COLUMN editorial_key TEXT",
        "source": "ALTER TABLE headline_feedback ADD COLUMN source TEXT DEFAULT 'headline_studio'",
    }
    for column, statement in migrations.items():
        if column not in existing_columns:
            cursor.execute(statement)
    legacy_sources = cursor.execute(
        "SELECT id, source_video FROM projects WHERE source_signature IS NULL OR source_signature = ''"
    ).fetchall()
    for source_row in legacy_sources:
        signature = _source_signature(source_row["source_video"])
        if signature:
            cursor.execute("UPDATE projects SET source_signature = ? WHERE id = ?", (signature, source_row["id"]))
    for column, statement in headline_migrations.items():
        if column not in headline_columns:
            cursor.execute(statement)

    snapshot_columns = {
        row["name"] for row in cursor.execute("PRAGMA table_info(performance_snapshots)").fetchall()
    }
    snapshot_migrations = {
        "account_key": "ALTER TABLE performance_snapshots ADD COLUMN account_key TEXT DEFAULT ''",
        "observation_window": "ALTER TABLE performance_snapshots ADD COLUMN observation_window TEXT DEFAULT 'all'",
        "region": "ALTER TABLE performance_snapshots ADD COLUMN region TEXT DEFAULT 'all'",
    }
    for column, statement in snapshot_migrations.items():
        if column not in snapshot_columns:
            cursor.execute(statement)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clips_editorial_key ON clips(project_id, editorial_key)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_headline_feedback_format ON headline_feedback(format_id, action)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_headline_feedback_clip ON headline_feedback(clip_id, created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_content ON performance_snapshots(content_key, platform, collected_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_cohort ON performance_snapshots(platform, format_id, observation_window, region)")
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


def _decode_setting_value(raw_value, fallback=None):
    try:
        return json.loads(raw_value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback


def get_setting(key):
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    if row:
        value = _decode_setting_value(row["value"], DEFAULT_SETTINGS.get(key))
    else:
        value = DEFAULT_SETTINGS.get(key)
    return _normalize_campaign_hub_account(value) if key == "campaign_hub_account" else value


def set_setting(key, value):
    if key == "campaign_hub_account":
        value = _normalize_campaign_hub_account(value)
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, json.dumps(value))
    )
    conn.commit()
    conn.close()


def save_headline_feedback(
    format_id,
    artwork_text,
    action="selected",
    topic="",
    transcript_excerpt="",
    mini_context="",
    clip_id=None,
    editorial_key="",
    source="headline_studio",
):
    """Persist a headline decision, optionally linked to the exact generated clip."""
    conn = get_db()
    conn.execute(
        """INSERT INTO headline_feedback
           (clip_id, editorial_key, format_id, artwork_text, action, topic,
            transcript_excerpt, mini_context, source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            int(clip_id) if clip_id not in (None, "") else None,
            str(editorial_key or "").strip()[:80],
            str(format_id or "unknown")[:40],
            str(artwork_text or "").strip()[:300],
            str(action or "selected")[:24],
            str(topic or "").strip()[:80],
            str(transcript_excerpt or "").strip()[:600],
            str(mini_context or "").strip()[:280],
            str(source or "headline_studio")[:40],
        ),
    )
    conn.commit()
    conn.close()


def get_headline_feedback_summary(limit=8):
    """Return a compact, non-secret summary for the headline studio HUD."""
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) AS count FROM headline_feedback").fetchone()["count"]
    selected = conn.execute(
        "SELECT COUNT(*) AS count FROM headline_feedback WHERE action = 'selected'"
    ).fetchone()["count"]
    by_format = {
        row["format_id"]: row["count"]
        for row in conn.execute(
            """SELECT format_id, COUNT(*) AS count FROM headline_feedback
               WHERE action = 'selected' GROUP BY format_id ORDER BY count DESC"""
        ).fetchall()
    }
    examples = [
        dict(row)
        for row in conn.execute(
            """SELECT format_id, artwork_text, topic, created_at FROM headline_feedback
               WHERE action = 'selected' ORDER BY id DESC LIMIT ?""",
            (max(1, min(int(limit), 20)),),
        ).fetchall()
    ]
    conn.close()
    return {"total": total, "selected": selected, "by_format": by_format, "examples": examples}


def get_headline_learning_preferences(topic=""):
    """Return aggregate local preferences, never the private text of prior choices."""
    normalized_topic = str(topic or "").strip()[:80]
    conn = get_db()
    overall = {
        row["format_id"]: row["count"]
        for row in conn.execute(
            """SELECT format_id, COUNT(*) AS count FROM headline_feedback
               WHERE action = 'selected' GROUP BY format_id ORDER BY count DESC"""
        ).fetchall()
    }
    topic_counts = {}
    if normalized_topic:
        topic_counts = {
            row["format_id"]: row["count"]
            for row in conn.execute(
                """SELECT format_id, COUNT(*) AS count FROM headline_feedback
                   WHERE action = 'selected' AND topic = ?
                   GROUP BY format_id ORDER BY count DESC""",
                (normalized_topic,),
            ).fetchall()
        }
    selected = conn.execute(
        "SELECT COUNT(*) AS count FROM headline_feedback WHERE action = 'selected'"
    ).fetchone()["count"]
    conn.close()
    return {
        "selected_count": int(selected or 0),
        "overall_by_format": overall,
        "topic_by_format": topic_counts,
    }


def save_performance_snapshot(snapshot, project_id=None):
    """Persist one normalized, user-authorized performance observation."""
    conn = get_db()
    conn.execute(
        """INSERT INTO performance_snapshots
           (content_key, platform, format_id, account_key, observation_window, region,
            published_at, collected_at, views,
            likes, comments, shares, saves, engagement_actions, engagement_rate,
            age_hours, view_velocity_per_hour, ranking_position, xp,
            collection_state, source, payload)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(snapshot.get("content_key", ""))[:180],
            str(snapshot.get("platform", "other"))[:24],
            str(snapshot.get("format_id", "unknown"))[:40],
            str(snapshot.get("account_key", ""))[:180],
            str(snapshot.get("observation_window", "all"))[:20],
            str(snapshot.get("region", "all"))[:40],
            snapshot.get("published_at"),
            snapshot.get("collected_at"),
            int(snapshot.get("views") or 0),
            int(snapshot.get("likes") or 0),
            int(snapshot.get("comments") or 0),
            int(snapshot.get("shares") or 0),
            int(snapshot.get("saves") or 0),
            int(snapshot.get("engagement_actions") or 0),
            snapshot.get("engagement_rate"),
            snapshot.get("age_hours"),
            snapshot.get("view_velocity_per_hour"),
            snapshot.get("ranking_position"),
            snapshot.get("xp"),
            str(snapshot.get("collection_state", "observed"))[:40],
            str(snapshot.get("source", "manual_or_authorized_export"))[:80],
            json.dumps(snapshot, ensure_ascii=False),
        ),
    )
    snapshot_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    conn.commit()
    conn.close()
    return int(snapshot_id)


def get_performance_snapshots(content_key=None, limit=100, *, platform=None, format_id=None, observation_window=None, region=None):
    conn = get_db()
    params = []
    clauses = []
    query = "SELECT * FROM performance_snapshots"
    if content_key:
        clauses.append("content_key = ?")
        params.append(str(content_key)[:180])
    if platform:
        clauses.append("platform = ?")
        params.append(str(platform)[:24])
    if format_id:
        clauses.append("format_id = ?")
        params.append(str(format_id)[:40])
    if observation_window:
        clauses.append("observation_window = ?")
        params.append(str(observation_window)[:20])
    if region:
        clauses.append("region = ?")
        params.append(str(region)[:40])
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY collected_at DESC, id DESC LIMIT ?"
    params.append(max(1, min(int(limit), 500)))
    rows = [dict(row) for row in conn.execute(query, params).fetchall()]
    conn.close()
    return rows


def get_performance_summary(format_id=None, *, platform=None, observation_window=None, region=None):
    conn = get_db()
    params = []
    clauses = []
    if format_id:
        clauses.append("format_id = ?")
        params.append(str(format_id)[:40])
    if platform:
        clauses.append("platform = ?")
        params.append(str(platform)[:24])
    if observation_window:
        clauses.append("observation_window = ?")
        params.append(str(observation_window)[:20])
    if region:
        clauses.append("region = ?")
        params.append(str(region)[:40])
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    row = conn.execute(
        f"""SELECT COUNT(*) AS snapshots, COUNT(DISTINCT content_key) AS contents,
                   SUM(views) AS views, AVG(engagement_rate) AS avg_engagement_rate,
                   AVG(view_velocity_per_hour) AS avg_view_velocity_per_hour
            FROM performance_snapshots{where}""",
        params,
    ).fetchone()
    latest = conn.execute(
        f"""SELECT platform, format_id, collection_state, collected_at
            FROM performance_snapshots{where}
            ORDER BY collected_at DESC, id DESC LIMIT 1""",
        params,
    ).fetchone()
    conn.close()
    return {
        "snapshots": int(row["snapshots"] or 0),
        "contents": int(row["contents"] or 0),
        "views": int(row["views"] or 0),
        "avg_engagement_rate": round(float(row["avg_engagement_rate"]), 6) if row["avg_engagement_rate"] is not None else None,
        "avg_view_velocity_per_hour": round(float(row["avg_view_velocity_per_hour"]), 3) if row["avg_view_velocity_per_hour"] is not None else None,
        "latest": dict(latest) if latest else None,
    }


def get_all_settings():
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    settings = {}
    for row in rows:
        settings[row["key"]] = _decode_setting_value(row["value"], DEFAULT_SETTINGS.get(row["key"]))
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
    settings["campaign_hub_account"] = _normalize_campaign_hub_account(settings.get("campaign_hub_account"))

    return settings


def create_project(name, source_video, source_signature=None):
    conn = get_db()
    signature = _source_signature(source_video) if source_signature is None else str(source_signature or "")[:64]
    cursor = conn.execute(
        "INSERT INTO projects (name, source_video, source_signature, status) VALUES (?, ?, ?, 'pending')",
        (name, source_video, signature)
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


def get_existing_clip_fingerprints(source_video=""):
    """Return stable local fingerprints used to avoid repeating a source interval.

    The lookup is intentionally local-only. It uses the normalized basename only
    to discover candidate projects across checkouts, then requires a matching
    lightweight content signature whenever both source files have one. This allows
    reruns from another checkout/path while preventing same-name files from sharing
    intervals; legacy records without a signature remain compatible. No transcript
    text leaves the local database.
    """
    source_text = str(source_video or "").replace("\\", "/").strip().lower()
    source_basename = source_text.rsplit("/", 1)[-1]
    if not source_basename:
        return []
    conn = get_db()
    normalized_source = "lower(replace(projects.source_video, char(92), '/'))"
    rows = conn.execute(
        f"""SELECT clips.start_time, clips.end_time, clips.duration,
                         clips.transcript, clips.review_status, clips.editorial_key,
                         projects.source_signature, projects.source_video,
                         (SELECT adjustments
                            FROM clip_feedback AS feedback
                           WHERE feedback.clip_id = clips.id
                             AND feedback.action = 'adjusted'
                           ORDER BY feedback.created_at DESC, feedback.id DESC
                           LIMIT 1) AS latest_adjustment,
                         clips.score_factors
           FROM clips
           JOIN projects ON projects.id = clips.project_id
          WHERE {normalized_source} = ? OR {normalized_source} LIKE ?""",
        (source_basename, f"%/{source_basename}"),
    ).fetchall()
    conn.close()
    current_signature = _source_signature(source_video)
    fingerprints = []
    seen_identities = set()
    for row in rows:
        try:
            start = float(row[0] or 0)
            end = float(row[1] or 0)
        except (TypeError, ValueError):
            continue
        if end <= start:
            continue
        stored_signature = str(row[6] or "")
        stored_source = str(row[7] or "").replace("\\", "/").strip().lower()
        if current_signature and stored_signature and stored_signature != current_signature:
            continue
        # Legacy projects may lack a content signature. If the current file has
        # one, do not let a same-basename file from another location inherit
        # those intervals; an exact path remains backward-compatible.
        if current_signature and not stored_signature and stored_source != source_text:
            continue
        fingerprint = {
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(float(row[2] or end - start), 3),
            "text": " ".join(str(row[3] or "").split()),
            "review_status": str(row[4] or "pending"),
            "editorial_key": str(row[5] or "")[:64],
            "source_signature": stored_signature,
            "interval_source": "canonical",
        }
        identity = fingerprint["editorial_key"] or (
            f"{fingerprint['start']:.3f}|{fingerprint['end']:.3f}|{fingerprint['text'].lower()}"
        )
        if identity not in seen_identities:
            seen_identities.add(identity)
            fingerprints.append(fingerprint)

        try:
            score_factors = json.loads(row[9] or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            score_factors = {}
        if isinstance(score_factors, dict):
            fingerprint.update(_normalize_dedup_context(score_factors.get("_dedup_context")))

        try:
            adjustment = json.loads(row[8] or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            adjustment = {}
        if not isinstance(adjustment, dict):
            adjustment = {}
        try:
            adjusted_start = float(adjustment.get("start"))
            adjusted_end = float(adjustment.get("end"))
        except (TypeError, ValueError):
            adjusted_start = adjusted_end = None
        if (
            adjusted_start is None
            or adjusted_end is None
            or not all(math.isfinite(value) for value in (adjusted_start, adjusted_end))
            or adjusted_start < 0
            or adjusted_end <= adjusted_start
            or (abs(adjusted_start - start) < 0.001 and abs(adjusted_end - end) < 0.001)
        ):
            continue
        adjusted_fingerprint = dict(fingerprint)
        adjusted_fingerprint.update({
            "start": round(adjusted_start, 3),
            "end": round(adjusted_end, 3),
            "duration": round(adjusted_end - adjusted_start, 3),
            "interval_source": "manual_adjustment",
        })
        adjusted_identity = (
            f"{adjusted_fingerprint['editorial_key']}|adjusted|"
            f"{adjusted_fingerprint['start']:.3f}|{adjusted_fingerprint['end']:.3f}"
        )
        if adjusted_identity not in seen_identities:
            seen_identities.add(adjusted_identity)
            fingerprints.append(adjusted_fingerprint)
    return fingerprints


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
        """SELECT clips.*,
                  (SELECT adjustments FROM clip_feedback
                   WHERE clip_feedback.clip_id = clips.id
                     AND clip_feedback.action = 'adjusted'
                   ORDER BY clip_feedback.id DESC LIMIT 1) AS latest_adjustment,
                  (SELECT reason_code FROM clip_feedback
                   WHERE clip_feedback.clip_id = clips.id
                     AND clip_feedback.action IN ('approved', 'rejected', 'needs_review')
                   ORDER BY clip_feedback.id DESC LIMIT 1) AS latest_feedback_reason,
                  (SELECT quality_tags FROM clip_feedback
                   WHERE clip_feedback.clip_id = clips.id
                     AND clip_feedback.action IN ('approved', 'rejected', 'needs_review')
                   ORDER BY clip_feedback.id DESC LIMIT 1) AS latest_feedback_tags
           FROM clips
           WHERE project_id = ?
           ORDER BY viral_score DESC""",
        (project_id,)
    ).fetchall()
    conn.close()
    clips = []
    for row in rows:
        clip = dict(row)
        review_flags = {}
        factors = {}
        raw_factors = clip.get("score_factors")
        if raw_factors:
            try:
                factors = json.loads(raw_factors)
                if isinstance(factors, dict) and isinstance(factors.get("_review_flags"), dict):
                    review_flags = factors["_review_flags"]
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
        clip["review_flags"] = review_flags
        clip["quality_scorecard"] = _normalize_quality_scorecard(
            factors.get("_quality_scorecard") if isinstance(factors, dict) else None
        )
        clip["scene_boundary_adjustment"] = _normalize_scene_boundary_adjustment(
            factors.get("_scene_boundary_adjustment") if isinstance(factors, dict) else None
        )
        raw_review_provenance = factors.get("_review_metadata") if isinstance(factors, dict) else None
        normalized_provenance = _normalize_review_provenance(raw_review_provenance)
        if not normalized_provenance and isinstance(review_flags, dict):
            normalized_provenance = _normalize_review_provenance({
                "candidate_origin": review_flags.get("candidate_origin"),
                "selection_source": review_flags.get("selection_source"),
                "confidence": review_flags.get("confidence"),
                "transcript_source": review_flags.get("transcript_source"),
                "transcript_coverage_status": review_flags.get("transcription_coverage_status"),
                "transcript_archive_present": review_flags.get("transcript_archive_present"),
                "context_source": review_flags.get("context_source"),
            })
        if not normalized_provenance:
            normalized_provenance = {
                "transcript_source": "unknown",
                "transcript_coverage_status": "unknown",
                "transcript_archive_present": False,
                "context_source": "none",
            }
        clip["review_provenance"] = normalized_provenance
        clip["framing"] = dict(normalized_provenance.get("framing") or {
            "mode": "",
            "review_required": True,
            "reason": "metadata de enquadramento ausente ou legada; confirme a composição visual",
        })
        raw_context_recovery = factors.get("_context_recovery") if isinstance(factors, dict) else None
        clip["context_recovery"] = (
            raw_context_recovery
            if isinstance(raw_context_recovery, dict)
            else {"applied": bool(review_flags.get("context_recovery_applied")), "reason": "antecedente recuperado; confirme a abertura"}
            if review_flags.get("context_recovery_applied")
            else {"applied": False, "reason": "antecedente não precisou ser recuperado"}
        )
        raw_adjustment = clip.get("latest_adjustment")
        if raw_adjustment:
            try:
                clip["latest_adjustment"] = json.loads(raw_adjustment)
            except (TypeError, ValueError, json.JSONDecodeError):
                clip["latest_adjustment"] = None
        else:
            clip["latest_adjustment"] = None
        try:
            parsed_tags = json.loads(clip.get("latest_feedback_tags") or "[]")
            clip["latest_feedback_tags"] = parsed_tags if isinstance(parsed_tags, list) else []
        except (TypeError, ValueError, json.JSONDecodeError):
            clip["latest_feedback_tags"] = []
        clips.append(clip)
    return clips


def update_clip_seo(clip_id, titles, tags, description, hashtags):
    conn = get_db()
    conn.execute(
        """UPDATE clips SET suggested_titles = ?, suggested_tags = ?,
           suggested_description = ?, suggested_hashtags = ? WHERE id = ?""",
        (json.dumps(titles), json.dumps(tags), description, json.dumps(hashtags), clip_id)
    )
    conn.commit()
    conn.close()


def update_clip_editorial_score(clip_id, score, factors, confidence, version="v1-explainable", review_flags=None, review_metadata=None, context_recovery=None, quality_scorecard=None, scene_boundary_adjustment=None):
    conn = get_db()
    score_payload = dict(factors or {})
    if isinstance(review_flags, dict) and review_flags:
        score_payload["_review_flags"] = review_flags
    if isinstance(context_recovery, dict) and context_recovery:
        score_payload["_context_recovery"] = context_recovery
    normalized_scorecard = _normalize_quality_scorecard(quality_scorecard)
    if normalized_scorecard:
        score_payload["_quality_scorecard"] = normalized_scorecard
    normalized_dedup_context = _normalize_dedup_context(
        (factors or {}).get("_dedup_context") if isinstance(factors, dict) else None
    )
    if normalized_dedup_context:
        score_payload["_dedup_context"] = normalized_dedup_context
    normalized_scene_adjustment = _normalize_scene_boundary_adjustment(scene_boundary_adjustment)
    if normalized_scene_adjustment:
        score_payload["_scene_boundary_adjustment"] = normalized_scene_adjustment
    normalized_metadata = _normalize_review_provenance(review_metadata)
    if normalized_metadata:
        score_payload["_review_metadata"] = normalized_metadata
    conn.execute(
        """UPDATE clips SET viral_score = ?, score_factors = ?,
           score_confidence = ?, editorial_score_version = ? WHERE id = ?""",
        (int(score), json.dumps(score_payload), float(confidence or 0), version, clip_id)
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


def save_clip_feedback(clip_id, action, adjustments=None, note="", reason_code="", quality_tags=None):
    if action not in {"approved", "rejected", "needs_review", "adjusted", "rendered"}:
        raise ValueError("Ação de feedback inválida")
    normalized_reason = str(reason_code or "").strip()[:48]
    normalized_tags = []
    for tag in (quality_tags or []):
        value = str(tag or "").strip()[:48]
        if value and value not in normalized_tags:
            normalized_tags.append(value)
    normalized_tags = normalized_tags[:12]
    conn = get_db()
    clip_row = conn.execute("SELECT id FROM clips WHERE id = ?", (clip_id,)).fetchone()
    if not clip_row:
        conn.close()
        raise ValueError("Clip não encontrado")
    status = action if action in {"approved", "rejected", "needs_review"} else "needs_review"
    conn.execute(
        """INSERT INTO clip_feedback
           (clip_id, action, adjustments, note, reason_code, quality_tags)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            clip_id,
            action,
            json.dumps(adjustments or {}),
            str(note or "")[:600],
            normalized_reason,
            json.dumps(normalized_tags, ensure_ascii=False),
        ),
    )
    conn.execute("UPDATE clips SET review_status = ? WHERE id = ?", (status, clip_id))
    conn.commit()
    conn.close()


def restore_feedback_snapshot(records):
    """Replay sanitized final decisions into matching local clips, idempotently.

    The repository snapshot carries no local clip id, so ``editorial_key`` is the
    portable identity. A local decision with a newer timestamp always wins.
    """
    if not isinstance(records, list):
        raise ValueError("Snapshot de feedback inválido: records deve ser uma lista")
    final_actions = {"approved", "rejected", "needs_review"}
    counters = {
        "records_seen": len(records),
        "imported": 0,
        "already_current": 0,
        "skipped_older": 0,
        "unmatched": 0,
        "invalid": 0,
    }

    def parse_timestamp(value):
        text = str(value or "").strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
        if parsed.tzinfo:
            parsed = parsed.astimezone().replace(tzinfo=None)
        return parsed

    conn = get_db()
    try:
        for record in records:
            if not isinstance(record, dict):
                counters["invalid"] += 1
                continue
            editorial_key = str(record.get("editorial_key") or "").strip()[:80]
            action = str(record.get("action") or "").strip()[:24]
            if not editorial_key or action not in final_actions:
                counters["invalid"] += 1
                continue
            reason_code = str(record.get("reason_code") or "").strip()[:48]
            tags = []
            raw_tags = record.get("quality_tags")
            if isinstance(raw_tags, list):
                for tag in raw_tags:
                    normalized = str(tag or "").strip()[:48]
                    if normalized and normalized not in tags:
                        tags.append(normalized)
            tags = tags[:12]
            incoming_timestamp = parse_timestamp(record.get("created_at"))
            if incoming_timestamp is None:
                counters["invalid"] += 1
                continue
            source_signature = str(record.get("source_signature") or "").strip()[:64]
            clip = conn.execute(
                """SELECT c.id, p.source_signature
                     FROM clips AS c
                     JOIN projects AS p ON p.id = c.project_id
                    WHERE c.editorial_key = ?
                    ORDER BY c.id DESC LIMIT 1""",
                (editorial_key,),
            ).fetchone()
            if clip:
                stored_signature = str(clip["source_signature"] or "").strip()[:64]
                if source_signature and stored_signature and source_signature != stored_signature:
                    clip = None
            if not clip:
                try:
                    start_seconds = float(record.get("start_seconds"))
                    end_seconds = float(record.get("end_seconds"))
                except (TypeError, ValueError):
                    start_seconds = end_seconds = None
                if source_signature and start_seconds is not None and end_seconds is not None:
                    clip = conn.execute(
                        """SELECT c.id FROM clips AS c
                              JOIN projects AS p ON p.id = c.project_id
                             WHERE p.source_signature = ?
                               AND ABS(c.start_time - ?) <= 0.5
                               AND ABS(c.end_time - ?) <= 0.5
                             ORDER BY c.id DESC LIMIT 1""",
                        (source_signature, start_seconds, end_seconds),
                    ).fetchone()
            if not clip:
                counters["unmatched"] += 1
                continue
            latest = conn.execute(
                """SELECT action, reason_code, quality_tags, created_at
                     FROM clip_feedback
                    WHERE clip_id = ? AND action IN ('approved', 'rejected', 'needs_review')
                    ORDER BY id DESC LIMIT 1""",
                (clip["id"],),
            ).fetchone()
            if latest:
                try:
                    current_tags = json.loads(latest["quality_tags"] or "[]")
                except (TypeError, ValueError, json.JSONDecodeError):
                    current_tags = []
                current_tags = current_tags if isinstance(current_tags, list) else []
                current_timestamp = parse_timestamp(latest["created_at"])
                if (
                    latest["action"] == action
                    and latest["reason_code"] == reason_code
                    and current_tags == tags
                ):
                    counters["already_current"] += 1
                    continue
                if incoming_timestamp and current_timestamp and incoming_timestamp <= current_timestamp:
                    counters["skipped_older"] += 1
                    continue
            conn.execute(
                """INSERT INTO clip_feedback
                   (clip_id, action, adjustments, note, reason_code, quality_tags)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    clip["id"],
                    action,
                    json.dumps({}, ensure_ascii=False),
                    "Restaurado do snapshot editorial sanitizado.",
                    reason_code,
                    json.dumps(tags, ensure_ascii=False),
                ),
            )
            conn.execute("UPDATE clips SET review_status = ? WHERE id = ?", (action, clip["id"]))
            counters["imported"] += 1
        conn.commit()
    finally:
        conn.close()
    return counters


def get_clip(clip_id):
    """Return one persisted clip or ``None`` without applying a draft adjustment."""
    conn = get_db()
    row = conn.execute("SELECT * FROM clips WHERE id = ?", (clip_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_clip_adjustment(clip_id, adjustment, note=""):
    """Persist a validated temporal draft as an editorial feedback event."""
    if not isinstance(adjustment, dict):
        raise ValueError("Ajuste inválido")
    try:
        start = float(adjustment["start"])
        end = float(adjustment["end"])
        duration = float(adjustment.get("duration", end - start))
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Ajuste temporal inválido") from exc
    if start < 0 or end <= start or duration <= 0:
        raise ValueError("Os limites ajustados devem formar um intervalo positivo")
    payload = dict(adjustment)
    payload.update({"start": round(start, 3), "end": round(end, 3), "duration": round(duration, 3)})
    save_clip_feedback(clip_id, "adjusted", adjustments=payload, note=note)
    return payload


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
        try:
            parsed_tags = json.loads(item.get("quality_tags") or "[]")
            item["quality_tags"] = parsed_tags if isinstance(parsed_tags, list) else []
        except (TypeError, ValueError, json.JSONDecodeError):
            item["quality_tags"] = []
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
    they are not final editorial verdicts. Legacy clips may not contain
    ``score_factors``; in that case we expose a bounded duration signal derived
    from the reviewed intervals instead of pretending missing factors exist.
    """
    conn = get_db()
    rows = conn.execute(
        """SELECT clips.id, viral_score, duration, score_factors, review_status,
                  (SELECT reason_code FROM clip_feedback
                   WHERE clip_feedback.clip_id = clips.id
                     AND clip_feedback.action IN ('approved', 'rejected')
                   ORDER BY clip_feedback.id DESC LIMIT 1) AS reason_code,
                  (SELECT quality_tags FROM clip_feedback
                   WHERE clip_feedback.clip_id = clips.id
                     AND clip_feedback.action IN ('approved', 'rejected')
                   ORDER BY clip_feedback.id DESC LIMIT 1) AS quality_tags
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
            "duration": max(0.0, float(item.get("duration") or 0)),
            "factors": {
                key: float(value)
                for key, value in factors.items()
                if isinstance(value, (int, float))
            },
            "provenance": _normalize_review_provenance(factors),
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

    reason_counts = {"approved": {}, "rejected": {}}
    for row in rows:
        status = str(row["review_status"] or "")
        reason = str(row["reason_code"] or "").strip()
        if status in reason_counts and reason:
            reason_counts[status][reason] = reason_counts[status].get(reason, 0) + 1

    reason_categories = {
        "hook": {"good_hook", "weak_hook", "no_hook"},
        "context_payoff": {"excellent_context", "missing_context", "no_payoff"},
        "speaker_audio": {"wrong_speaker", "audio_overlap"},
        "duration": {"too_long"},
        "framing": {"bad_framing"},
    }
    reason_coverage_categories = {}
    explicit_reason_total = 0
    for category, codes in reason_categories.items():
        approved_total = sum(reason_counts["approved"].get(code, 0) for code in codes)
        rejected_total = sum(reason_counts["rejected"].get(code, 0) for code in codes)
        reason_coverage_categories[category] = {
            "approved": approved_total,
            "rejected": rejected_total,
            "total": approved_total + rejected_total,
            "codes": sorted(codes),
            "usable": approved_total + rejected_total >= 3,
        }
        explicit_reason_total += approved_total + rejected_total
    reason_coverage = {
        "explicit_reason_total": explicit_reason_total,
        "final_decision_total": sample_size,
        "unattributed_final_decisions": max(0, sample_size - explicit_reason_total),
        "categories": reason_coverage_categories,
        "interpretation": (
            "motivos agrupados por sinal editorial; decisões sem motivo não foram reclassificadas"
            if explicit_reason_total
            else             "nenhum motivo explícito disponível para calibrar categorias; decisões sem motivo não foram reclassificadas"

        ),
    }

    approved_duration = mean([item["duration"] for item in approved])
    rejected_duration = mean([item["duration"] for item in rejected])
    duration_gap = round(rejected_duration - approved_duration, 2)
    # Duration is a preference only. Require a meaningful gap and cap the
    # influence so an old, small editorial sample cannot override context.
    duration_signal_usable = bool(
        eligible and approved and rejected and abs(duration_gap) >= 3.0
    )
    if duration_signal_usable:
        factor_deltas["duration_fit"] = round(
            max(-25.0, min(25.0, duration_gap * 2.0)), 2
        )

    # Origin is a source-quality signal, not a replacement for editorial evidence.
    # Require both outcomes per origin so one lucky approval cannot bias the ranker.
    origin_groups = {}
    for outcome in ("approved", "rejected"):
        for item in groups[outcome]:
            origin = str(item.get("provenance", {}).get("candidate_origin") or "")
            if not origin:
                continue
            group = origin_groups.setdefault(origin, {"approved": 0, "rejected": 0})
            group[outcome] += 1
    global_approval_rate = round(
        (len(approved) + 1) / (sample_size + 2),
        4,
    ) if sample_size else 0.0
    candidate_origin_deltas = {}
    origin_calibration = []
    for origin in sorted(origin_groups):
        counts = origin_groups[origin]
        origin_sample = counts["approved"] + counts["rejected"]
        origin_rate = round(
            (counts["approved"] + 1) / (origin_sample + 2),
            4,
        ) if origin_sample else 0.0
        enough_origin_data = bool(
            eligible
            and origin_sample >= 4
            and counts["approved"] >= 2
            and counts["rejected"] >= 2
        )
        lift_points = round((origin_rate - global_approval_rate) * 100.0, 2)
        bounded_lift = round(max(-20.0, min(20.0, lift_points)), 2) if enough_origin_data else 0.0
        if enough_origin_data:
            candidate_origin_deltas[origin] = bounded_lift
        origin_calibration.append({
            "candidate_origin": origin,
            "approved_count": counts["approved"],
            "rejected_count": counts["rejected"],
            "sample_size": origin_sample,
            "approval_rate": origin_rate,
            "lift_points": bounded_lift,
            "eligible": enough_origin_data,
            "interpretation": (
                "origem com sinal equilibrado; ajuste limitado aplicado"
                if enough_origin_data and bounded_lift
                else "origem equilibrada sem diferença relevante nesta amostra"
                if enough_origin_data
                else "amostra insuficiente para calibrar por origem"
            ),
        })

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
        "candidate_origin_deltas": candidate_origin_deltas,
        "origin_calibration": {
            "eligible": bool(candidate_origin_deltas),
            "global_approval_rate": global_approval_rate,
            "minimum_origin_sample_size": 4,
            "minimum_origin_per_outcome": 2,
            "origins": origin_calibration,
        },
        "reason_counts": reason_counts,
        "reason_coverage": reason_coverage,
        "top_rejection_reasons": [
            {"reason": reason, "count": count}
            for reason, count in sorted(reason_counts["rejected"].items(), key=lambda item: (-item[1], item[0]))[:5]
        ],
        "duration_signal": {
            "usable": duration_signal_usable,
            "approved_mean_seconds": round(approved_duration, 2),
            "rejected_mean_seconds": round(rejected_duration, 2),
            "gap_seconds": duration_gap,
            "interpretation": (
                "aprovados tendem a ser mais curtos, sem transformar duração em limite"
                if duration_signal_usable and duration_gap > 0
                else "aprovados tendem a ser mais longos nesta amostra; usar apenas como sinal fraco"
                if duration_signal_usable
                else "amostra insuficiente ou diferença pequena para orientar duração"
            ),
        },
    }



def get_approved_clip_feature_prior(min_samples=12):
    """Build aggregate-only priors from local final clip decisions.

    Raw transcript, file paths and headline text are never returned. This is a
    local calibration aid, not model fine-tuning and not a Campaign Hub write.
    """
    from modules.approved_clip_priors import build_feature_prior

    conn = get_db()
    rows = conn.execute(
        """SELECT clips.duration, clips.score_factors, clips.review_status,
                  (SELECT format_id FROM headline_feedback
                   WHERE headline_feedback.clip_id = clips.id
                     AND headline_feedback.action = 'selected'
                   ORDER BY headline_feedback.id DESC LIMIT 1) AS format_id,
                  (SELECT artwork_text FROM headline_feedback
                   WHERE headline_feedback.clip_id = clips.id
                     AND headline_feedback.action = 'selected'
                   ORDER BY headline_feedback.id DESC LIMIT 1) AS artwork_text,
                  (SELECT topic FROM headline_feedback
                   WHERE headline_feedback.clip_id = clips.id
                     AND headline_feedback.action = 'selected'
                   ORDER BY headline_feedback.id DESC LIMIT 1) AS topic
           FROM clips
           WHERE clips.review_status IN ('approved', 'rejected')"""
    ).fetchall()
    conn.close()
    records = []
    for row in rows:
        try:
            factors = json.loads(row["score_factors"] or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            factors = {}
        if not isinstance(factors, dict):
            factors = {}
        numeric_factors = {
            key: value for key, value in factors.items()
            if isinstance(key, str) and isinstance(value, (int, float)) and math.isfinite(float(value))
        }
        records.append({
            "decision": row["review_status"],
            "duration": row["duration"],
            "format_id": row["format_id"] or "unknown",
            "headline": row["artwork_text"] or "",
            "topic": row["topic"] or "unknown",
            "hook_family": factors.get("editorial_family") or factors.get("hook_family") or "unknown",
            "factors": numeric_factors,
        })
    return build_feature_prior(records, min_samples=min_samples)


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
