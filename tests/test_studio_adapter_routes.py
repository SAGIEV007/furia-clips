import io
import json
import sqlite3
from pathlib import Path

from flask import Flask, jsonify

import studio_adapter


def _make_runtime(tmp_path):
    db_path = tmp_path / "studio.sqlite3"
    upload_dir = tmp_path / "uploads"
    export_dir = tmp_path / "exports"
    upload_dir.mkdir()
    export_dir.mkdir()
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            source_video TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT ''
        );
        CREATE TABLE clips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            file_path TEXT DEFAULT '',
            start_time REAL,
            end_time REAL,
            duration REAL,
            viral_score INTEGER DEFAULT 0,
            has_hook INTEGER DEFAULT 0,
            emotional_intensity REAL DEFAULT 0,
            transcript TEXT DEFAULT '',
            editorial_key TEXT DEFAULT '',
            review_status TEXT DEFAULT 'pending',
            status TEXT DEFAULT 'pending',
            suggested_titles TEXT DEFAULT '[]',
            suggested_tags TEXT DEFAULT '[]',
            suggested_description TEXT DEFAULT '',
            suggested_hashtags TEXT DEFAULT '[]',
            score_factors TEXT DEFAULT '{}',
            score_confidence REAL DEFAULT 0,
            thumbnail_path TEXT DEFAULT ''
        );
        CREATE TABLE studio_project_meta (
            project_id INTEGER PRIMARY KEY,
            payload TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL DEFAULT ''
        );
        """
    )
    conn.commit()
    conn.close()
    transcriptions = {}

    def get_db():
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def get_project(project_id):
        with get_db() as connection:
            row = connection.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return dict(row) if row else None

    def get_all_projects():
        with get_db() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM projects ORDER BY id")]

    def get_clips(project_id):
        with get_db() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM clips WHERE project_id = ? ORDER BY viral_score DESC, id", (project_id,))]

    def get_clip(clip_id):
        with get_db() as connection:
            row = connection.execute("SELECT * FROM clips WHERE id = ?", (clip_id,)).fetchone()
        return dict(row) if row else None

    def create_project(name, _source=""):
        with get_db() as connection:
            cursor = connection.execute("INSERT INTO projects (name, source_video) VALUES (?, ?)", (name, _source))
            connection.commit()
            return cursor.lastrowid

    def save_transcription(project_id, segments, full_text, language, source, provenance=None):
        transcriptions[project_id] = {"segments": segments, "full_text": full_text, "language": language, "source": source}

    def adjust_clip_bounds(candidate, start, end, transcript_segments=None, duration=None, min_duration=1.0):
        if end <= start or end - start < min_duration:
            raise ValueError("intervalo positivo")
        return {"start": round(float(start), 3), "end": round(float(end), 3), "duration": round(float(end - start), 3)}

    def save_clip_adjustment(clip_id, adjustment, note=""):
        return adjustment

    def save_clip_feedback(clip_id, action, note="", **_kwargs):
        if not get_clip(clip_id):
            raise ValueError("Clip não encontrado")
        with get_db() as connection:
            connection.execute("UPDATE clips SET review_status = ?, status = ? WHERE id = ?", (action, action, clip_id))
            connection.commit()

    def update_clip_seo(clip_id, titles, tags, description, hashtags):
        with get_db() as connection:
            connection.execute(
                "UPDATE clips SET suggested_titles = ?, suggested_tags = ?, suggested_description = ?, suggested_hashtags = ? WHERE id = ?",
                (json.dumps(titles), json.dumps(tags), description, json.dumps(hashtags), clip_id),
            )
            connection.commit()

    runtime = {
        "init_db": lambda: None,
        "get_db": get_db,
        "DB_PATH": str(db_path),
        "get_project": get_project,
        "get_all_projects": get_all_projects,
        "get_clips": get_clips,
        "get_clip": get_clip,
        "create_project": create_project,
        "save_transcription": save_transcription,
        "get_transcription": lambda project_id: transcriptions.get(project_id, {}),
        "parse_transcript_text": studio_adapter.__dict__.get("parse_transcript_text") or __import__("modules.transcript_parser", fromlist=["parse_transcript_text"]).parse_transcript_text,
        "adjust_clip_bounds": adjust_clip_bounds,
        "save_clip_adjustment": save_clip_adjustment,
        "save_clip_feedback": save_clip_feedback,
        "update_clip_seo": update_clip_seo,
        "get_headline_learning_preferences": lambda: {},
        "build_editorial_block": lambda payload: {"state": "review", "thesis": payload.get("title"), "moment_reason": payload.get("reason"), "tags": payload.get("tags", []), "suggested_moments": []},
        "_probe_video_duration_seconds": lambda _path: 30.0,
        "ALLOWED_EXTENSIONS": {".mp4"},
        "UPLOAD_DIR": str(upload_dir),
        "EXPORT_DIR": str(export_dir),
        "WORKSPACE_DIR": str(tmp_path),
        "THUMBNAIL_DIR": str(tmp_path / "thumbs"),
        "PROCESSED_DIR": str(tmp_path / "processed"),
        "PERSISTENT_DATA_DIR": str(tmp_path),
        "unique_storage_name": lambda filename, extension=None: filename,
        "job_manager": type("FakeJobs", (), {"submit": lambda self, *_args, **_kwargs: {"id": "fake-export-job", "state": "queued"}})(),
    }
    return runtime, get_db, create_project


def test_adapter_routes_round_trip_without_private_media(tmp_path, monkeypatch):
    runtime, get_db, create_project = _make_runtime(tmp_path)
    flask_app = Flask(__name__)
    flask_app.add_url_rule("/api/projects", endpoint="api_list_projects", view_func=lambda: jsonify([]), methods=["GET"])
    flask_app.add_url_rule("/api/projects/<int:project_id>", endpoint="api_get_project", view_func=lambda project_id: jsonify({}), methods=["GET"])
    studio_adapter.register_studio_routes(flask_app, runtime)
    client = flask_app.test_client()

    created = client.post("/api/projects", json={"name": "Fixture Renan"})
    assert created.status_code == 201
    project_id = created.get_json()["id"]

    imported = client.post(
        f"/api/projects/{project_id}/import",
        data={"video": (io.BytesIO(b"not-a-real-video"), "debate.mp4")},
        content_type="multipart/form-data",
    )
    assert imported.status_code == 200
    assert imported.get_json()["filename"] == "debate.mp4"

    srt = "1\n00:00:00,000 --> 00:00:04,000\nA proposta reduz o desperdício.\n\n2\n00:00:04,000 --> 00:00:09,000\nQual é o próximo passo?\n"
    transcript = client.post(
        f"/api/projects/{project_id}/transcript",
        data={"transcript": (io.BytesIO(srt.encode("utf-8")), "fixture.srt")},
        content_type="multipart/form-data",
    )
    assert transcript.status_code == 200
    assert transcript.get_json()["transcriptCount"] == 2

    with get_db() as connection:
        cursor = connection.execute(
            "INSERT INTO clips (project_id, start_time, end_time, duration, viral_score, transcript, score_factors) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, 1.0, 8.0, 7.0, 78, "A proposta reduz o desperdício. Qual é o próximo passo?", json.dumps({"hook": 9})),
        )
        connection.commit()
        clip_id = cursor.lastrowid

    changed = client.post(f"/api/clips/{clip_id}/range", json={"start": 1.5, "end": 7.5})
    assert changed.status_code == 200
    assert changed.get_json()["reviewStatus"] == "needs_review"
    assert changed.get_json()["exportUrl"] == ""
    approved = client.post(f"/api/clips/{clip_id}/decision", json={"decision": "approved"})
    assert approved.status_code == 200
    assert approved.get_json()["reviewStatus"] == "approved"

    monkeypatch.setattr(
        "modules.headline_studio.generate_artwork_copy",
        lambda *args, **kwargs: {"formats": {"vertical_916": {"suggestions": [{"headline": "A proposta que muda o jogo"}, {"headline": "Qual é o próximo passo?"}, {"headline": "Renan explica a resposta"}]}}, "recommendation_reason": "Gerada a partir da legenda local."},
    )
    seo = client.post(f"/api/projects/{project_id}/seo", json={"clip_id": clip_id})
    assert seo.status_code == 200
    assert len(seo.get_json()["titles"]) == 3
    assert "A proposta que muda o jogo" == seo.get_json()["title"]

    chub_payload = {"source": "campaign-hub", "channel": "@renansantosmbl", "scope": {"platforms": ["instagram"]}, "topPosts": [{"id": "x"}], "hooks": [{"text": "hook"}]}
    attached = client.post(f"/api/projects/{project_id}/chub-context", json=chub_payload)
    assert attached.status_code == 200
    assert attached.get_json()["chub"]["available"] is True
    cleared = client.delete(f"/api/projects/{project_id}/chub-context")
    assert cleared.status_code == 200
    assert cleared.get_json()["chub"]["available"] is False

    export = client.post(f"/api/clips/{clip_id}/export")
    assert export.status_code == 200
    assert export.get_json()["jobId"] == "fake-export-job"
