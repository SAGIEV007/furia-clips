import io
import json
import sqlite3
from pathlib import Path

from flask import Flask, jsonify

import studio_adapter
from modules.editorial_disagreement import build_disagreement_record, summarize_records
from modules.editorial_learning_store import load_disagreement_records, save_disagreement_record


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
            export_path TEXT DEFAULT '',
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
    feedback_calls = []

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

    def reset_project_source_state(project_id):
        transcriptions.pop(project_id, None)
        with get_db() as connection:
            connection.execute("DELETE FROM clips WHERE project_id = ?", (project_id,))
            connection.commit()

    def adjust_clip_bounds(candidate, start, end, transcript_segments=None, duration=None, min_duration=1.0, snap_tolerance=2.0):
        if end <= start or end - start < min_duration:
            raise ValueError("intervalo positivo")
        return {"start": round(float(start), 3), "end": round(float(end), 3), "duration": round(float(end - start), 3)}

    def save_clip_adjustment(clip_id, adjustment, note=""):
        return adjustment

    def save_clip_feedback(clip_id, action, note="", **kwargs):
        if not get_clip(clip_id):
            raise ValueError("Clip não encontrado")
        feedback_calls.append({"clip_id": clip_id, "action": action, "note": note, **kwargs})
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
        "reset_project_source_state": reset_project_source_state,
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
        "get_all_settings": lambda: {"ai_backend": "auto", "gemini_api_key": "", "ollama_url": "http://localhost:11434", "ollama_model": "llama3.2:3b", "transcription_source": "auto", "whisper_model": "small", "whisper_device": "auto"},
        "_check_ai_status": lambda _settings: {"status": "offline", "backend": "auto", "mode": "nlp", "connected": False, "model": "llama3.2:3b"},
        "PROGRAM_VERSION": "6.61",
        "PROGRAM_REVISION": "test",
        "feedback_calls": feedback_calls,
        "build_disagreement_record": build_disagreement_record,
        "save_disagreement_record": lambda record, project_id=None, clip_id=None: save_disagreement_record(record, project_id=project_id, clip_id=clip_id, root=tmp_path / "editorial-sessions"),
        "load_disagreement_records": lambda project_id=None, limit=200: load_disagreement_records(project_id=project_id, limit=limit, root=tmp_path / "editorial-sessions"),
        "summarize_records": summarize_records,
    }
    return runtime, get_db, create_project


def test_studio_status_exposes_capabilities_without_secrets(tmp_path):
    runtime, _get_db, _create_project = _make_runtime(tmp_path)
    flask_app = Flask(__name__)
    flask_app.add_url_rule("/api/projects", endpoint="api_list_projects", view_func=lambda: jsonify([]), methods=["GET"])
    flask_app.add_url_rule("/api/projects/<int:project_id>", endpoint="api_get_project", view_func=lambda project_id: jsonify({}), methods=["GET"])
    studio_adapter.register_studio_routes(flask_app, runtime)
    response = flask_app.test_client().get("/api/studio/status")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload["whisper"]["available"], bool)
    assert payload["whisper"]["configured_source"] == "auto"
    assert payload["ai"]["gemini_configured"] is False
    assert "gemini_api_key" not in payload
    assert payload["ffmpeg"]["available"] in {True, False}


def test_decision_forwards_rejection_reason(tmp_path):
    runtime, get_db, create_project = _make_runtime(tmp_path)
    flask_app = Flask(__name__)
    flask_app.add_url_rule("/api/projects", endpoint="api_list_projects", view_func=lambda: jsonify([]), methods=["GET"])
    flask_app.add_url_rule("/api/projects/<int:project_id>", endpoint="api_get_project", view_func=lambda project_id: jsonify({}), methods=["GET"])
    studio_adapter.register_studio_routes(flask_app, runtime)
    project_id = create_project("Feedback", "")
    with get_db() as connection:
        cursor = connection.execute(
            "INSERT INTO clips (project_id, start_time, end_time, duration, transcript) VALUES (?, ?, ?, ?, ?)",
            (project_id, 1.0, 5.0, 4.0, "Trecho para revisar."),
        )
        connection.commit()
        clip_id = cursor.lastrowid
    response = flask_app.test_client().post(
        f"/api/clips/{clip_id}/decision",
        json={"decision": "rejected", "reason_code": "sem_payoff", "note": "Falta a conclusão."},
    )
    assert response.status_code == 200
    assert runtime["feedback_calls"][-1]["reason_code"] == "sem_payoff"
    assert runtime["feedback_calls"][-1]["note"] == "Falta a conclusão."


def test_studio_decision_writes_and_reads_disagreement_matrix(tmp_path):
    runtime, get_db, create_project = _make_runtime(tmp_path)
    flask_app = Flask(__name__)
    flask_app.add_url_rule("/api/projects", endpoint="api_list_projects", view_func=lambda: jsonify([]), methods=["GET"])
    flask_app.add_url_rule("/api/projects/<int:project_id>", endpoint="api_get_project", view_func=lambda project_id: jsonify({}), methods=["GET"])
    studio_adapter.register_studio_routes(flask_app, runtime)
    project_id = create_project("Matriz", "")
    with get_db() as connection:
        cursor = connection.execute(
            "INSERT INTO clips (project_id, start_time, end_time, duration, viral_score, score_factors, review_status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (project_id, 2.0, 9.0, 7.0, 88, json.dumps({"flow": 90, "_review_flags": {"context_complete": False}}), "pending"),
        )
        connection.commit()
        clip_id = cursor.lastrowid
    client = flask_app.test_client()
    response = client.post(f"/api/clips/{clip_id}/decision", json={"decision": "approved", "reason_code": "excellent_context"})
    assert response.status_code == 200
    assert response.get_json()["disagreement"]["saved"] is True
    matrix = client.get(f"/api/editorial/disagreements?project_id={project_id}")
    assert matrix.status_code == 200
    payload = matrix.get_json()
    assert payload["summary"]["count"] == 1
    assert payload["summary"]["discordance_counts"]["warning_human_approved"] == 1
    assert payload["records"][0]["human"]["reason_code"] == "excellent_context"
    assert payload["read_only"] is True


def test_transcribe_route_reuses_saved_transcript_without_whisper(tmp_path):
    runtime, _get_db, create_project = _make_runtime(tmp_path)
    captured = {}

    class CapturingJobs:
        def submit(self, job_type, task, **kwargs):
            captured.update({"job_type": job_type, "task": task, "kwargs": kwargs})
            return {"id": "cached-transcript-job", "state": "queued"}

    runtime["job_manager"] = CapturingJobs()
    flask_app = Flask(__name__)
    flask_app.add_url_rule("/api/projects", endpoint="api_list_projects", view_func=lambda: jsonify([]), methods=["GET"])
    flask_app.add_url_rule("/api/projects/<int:project_id>", endpoint="api_get_project", view_func=lambda project_id: jsonify({}), methods=["GET"])
    studio_adapter.register_studio_routes(flask_app, runtime)
    project_id = create_project("Transcript cache", str(tmp_path / "source.mp4"))
    runtime["save_transcription"](project_id, [{"start": 0, "end": 2, "text": "texto persistido"}], "texto persistido", "pt", "manual_confirmed")

    response = flask_app.test_client().post(f"/api/projects/{project_id}/transcribe", json={})
    assert response.status_code == 200
    assert response.get_json()["cached"] is True
    assert captured["job_type"] == "studio_transcribe_cached"


def test_normalize_official_chub_mirror():
    mirror = json.loads((Path(__file__).parents[1] / "data" / "espelho_chub.json").read_text(encoding="utf-8"))
    normalized = studio_adapter._normalize_chub(mirror)
    assert normalized["source"] == "campaign-hub"
    assert normalized["schemaVersion"] == "espelho-chub-v1"
    assert normalized["channel"] == "@renansantosmbl"
    assert normalized["hooks"]
    assert normalized["scope"]["metric"] == "aggregate_reference"


def test_reimport_clears_source_specific_state(tmp_path):
    runtime, get_db, _create_project = _make_runtime(tmp_path)
    flask_app = Flask(__name__)
    flask_app.add_url_rule("/api/projects", endpoint="api_list_projects", view_func=lambda: jsonify([]), methods=["GET"])
    flask_app.add_url_rule("/api/projects/<int:project_id>", endpoint="api_get_project", view_func=lambda project_id: jsonify({}), methods=["GET"])
    studio_adapter.register_studio_routes(flask_app, runtime)
    client = flask_app.test_client()
    project_id = client.post("/api/projects", json={"name": "Troca de fonte"}).get_json()["id"]
    first = client.post(
        f"/api/projects/{project_id}/import",
        data={"video": (io.BytesIO(b"first"), "first.mp4")},
        content_type="multipart/form-data",
    )
    assert first.status_code == 200
    srt = "1\n00:00:00,000 --> 00:00:04,000\nTranscript antigo.\n"
    assert client.post(
        f"/api/projects/{project_id}/transcript",
        data={"transcript": (io.BytesIO(srt.encode("utf-8")), "old.srt")},
        content_type="multipart/form-data",
    ).status_code == 200
    with get_db() as connection:
        connection.execute(
            "INSERT INTO clips (project_id, start_time, end_time, duration, transcript) VALUES (?, ?, ?, ?, ?)",
            (project_id, 1.0, 3.0, 2.0, "Transcript antigo."),
        )
        connection.commit()
    second = client.post(
        f"/api/projects/{project_id}/import",
        data={"video": (io.BytesIO(b"second"), "second.mp4")},
        content_type="multipart/form-data",
    )
    assert second.status_code == 200
    payload = second.get_json()
    assert payload["filename"] == "second.mp4"
    assert payload["transcriptCount"] == 0
    assert payload["candidateCount"] == 0
    assert payload["clips"] == []


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
    assert imported.get_json()["reviewCount"] == 0

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
    rendered_path = tmp_path / "preliminary-render.mp4"
    rendered_path.write_bytes(b"rendered")
    with get_db() as connection:
        connection.execute("UPDATE clips SET file_path = ? WHERE id = ?", (str(rendered_path), clip_id))
        connection.commit()
    pending_aggregate = studio_adapter._project_payload(project_id, runtime, lambda _path: "", lambda _path: 30.0, detail=False)
    assert pending_aggregate["approvedCount"] == 0
    assert pending_aggregate["exportedCount"] == 0
    assert pending_aggregate["reviewCount"] == 1

    changed = client.post(f"/api/clips/{clip_id}/range", json={"start": 1.5, "end": 7.5})
    assert changed.status_code == 200
    assert changed.get_json()["start"] == 1.5
    assert changed.get_json()["end"] == 7.5
    assert changed.get_json()["reviewStatus"] == "needs_review"
    assert changed.get_json()["exportUrl"] == ""
    approved = client.post(f"/api/clips/{clip_id}/decision", json={"decision": "approved"})
    assert approved.status_code == 200
    assert approved.get_json()["reviewStatus"] == "approved"
    aggregate = studio_adapter._project_payload(project_id, runtime, lambda _path: "", lambda _path: 30.0, detail=False)
    assert aggregate["reviewCount"] == 0
    assert aggregate["exportedCount"] == 0
    approved_detail = studio_adapter._project_payload(project_id, runtime, lambda _path: "", lambda _path: 30.0, detail=True)
    assert approved_detail["clips"][0]["status"] == "approved"
    assert approved_detail["clips"][0]["exportUrl"] == ""

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


def test_normalize_chub_accepts_official_account_snapshot_as_read_only_context():
    payload = {
        "version": "2",
        "schema_version": "campaign-hub-profile-v2",
        "default_account": "@renansantosmbl",
        "collected_at": "2026-08-27T16:48:53Z",
        "accounts": {
            "@renansantosmbl": {
                "platforms": ["instagram", "facebook", "tiktok", "x"],
                "hook_priors": [{"hook": "tese-provocativa", "observations": 6, "mean_ratio": 1.2}],
                "cohorts": [{"query": "segurança pública", "n": 4}],
            },
            "@renansantosreserva": {"hook_priors": [{"hook": "outro", "observations": 3, "mean_ratio": 0.9}]},
        },
        "records": {
            "posts": [{"id": "post-1", "title": "Exemplo histórico", "metrics": {"views": 10}}],
            "transcripts": [{"full_text": "não deve ser copiado para o contexto"}],
        },
        "record_counts": {"posts": 1, "transcripts": 1},
        "sync": {"status": "ready", "last_sync_at": "2026-08-27T16:48:53Z"},
    }
    normalized = studio_adapter._normalize_chub(payload)
    assert normalized["channel"] == "@renansantosmbl"
    assert normalized["readOnly"] is True
    assert normalized["scoreTechnical"] is False
    assert normalized["accounts"] == ["@renansantosmbl", "@renansantosreserva"]
    assert normalized["recordCounts"]["transcripts"] == 1
    assert normalized["hooks"][0]["family"] == "tese-provocativa"
    assert normalized["topPosts"][0]["id"] == "post-1"
    assert "transcripts" not in normalized


def test_chub_summary_exposes_provenance_without_exposing_raw_memory():
    summary = studio_adapter._chub_summary({
        "source": "campaign-hub",
        "schemaVersion": "2",
        "channel": "@renansantosmbl",
        "fetchedAt": "2026-08-27T16:48:53Z",
        "scope": {"platforms": ["instagram"], "metric": "aggregate_reference"},
        "recordCounts": {"blocks": 19},
        "accounts": ["@renansantosmbl"],
        "readOnly": True,
        "scoreTechnical": False,
    })
    assert summary["available"] is True
    assert summary["schemaVersion"] == "2"
    assert summary["recordCounts"]["blocks"] == 19
    assert summary["readOnly"] is True
    assert summary["scoreTechnical"] is False
