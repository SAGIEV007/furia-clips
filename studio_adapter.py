"""Poolsuite Studio compatibility layer over the Furia 1 engine.

This module deliberately does not import or expose the Furia 2 namespace.  It
adapts the existing Furia 1 persistence and services to the small, local Studio
surface while keeping one Flask process and one database.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from flask import jsonify, request, send_file
from werkzeug.utils import secure_filename


ALLOWED_CHANNELS = {"@renansantosmbl", "@renansantosreserva", "@partidomissao"}


def register_studio_routes(flask_app, runtime):
    """Register the Studio adapter against globals from the Furia 1 app module."""
    runtime["init_db"]()
    _ensure_meta_table(runtime)

    def db():
        return runtime["get_db"]()

    def workspace_path(value):
        return os.path.abspath(str(value or ""))

    def safe_url(path):
        return _studio_url(path, runtime)

    @flask_app.get("/studio-file", endpoint="studio_file")
    def studio_file():
        requested = request.args.get("path", "")
        target = workspace_path(requested)
        roots = [runtime.get(name, "") for name in ("WORKSPACE_DIR", "UPLOAD_DIR", "THUMBNAIL_DIR", "PROCESSED_DIR", "EXPORT_DIR", "PERSISTENT_DATA_DIR")]
        if not target or not os.path.isfile(target) or not any(_is_under(target, workspace_path(root)) for root in roots if root):
            return jsonify({"error": "Arquivo local não encontrado ou fora do workspace."}), 404
        return send_file(target, conditional=True)

    def source_duration(path):
        try:
            return float(runtime["_probe_video_duration_seconds"](path) or 0)
        except Exception:
            return 0.0

    def clip_payload(row):
        return _clip_payload(row, runtime, source_duration)

    def project_payload(project_id, detail=False):
        return _project_payload(project_id, runtime, safe_url, source_duration, detail=detail)

    @flask_app.route("/api/projects", methods=["POST"], endpoint="studio_create_project")
    def studio_create_project():
        payload = request.get_json(silent=True) or {}
        name = str(payload.get("name") or "Novo projeto").strip()[:160]
        project_id = runtime["create_project"](name, "")
        return jsonify(project_payload(project_id, detail=True)), 201

    @flask_app.route("/api/projects/<int:project_id>/import", methods=["POST"], endpoint="studio_import_local")
    def studio_import_local(project_id):
        uploaded = request.files.get("video")
        if not uploaded or not uploaded.filename:
            return jsonify({"error": "Selecione um vídeo para importar."}), 400
        extension = Path(uploaded.filename).suffix.lower()
        allowed = runtime.get("ALLOWED_EXTENSIONS", {".mp4", ".mov", ".mkv", ".webm", ".m4v"})
        if extension not in allowed:
            return jsonify({"error": "Formato não suportado. Use MP4, MOV, MKV, WEBM ou M4V."}), 400
        project = runtime["get_project"](project_id)
        if not project:
            return jsonify({"error": "Projeto não encontrado."}), 404
        upload_dir = runtime["UPLOAD_DIR"]
        os.makedirs(upload_dir, exist_ok=True)
        filename = secure_filename(uploaded.filename) or f"source{extension}"
        unique = runtime.get("unique_storage_name")
        stored_name = unique(filename, extension=extension) if unique else filename
        path = os.path.join(upload_dir, stored_name)
        uploaded.save(path)
        duration = source_duration(path)
        if duration <= 0:
            try:
                os.unlink(path)
            except OSError:
                pass
            return jsonify({"error": "Não foi possível ler a duração do vídeo com FFprobe."}), 422
        old_source = str(project.get("source_video") or "").strip()
        if old_source:
            _reset_source_state(runtime, project_id)
        with db() as conn:
            conn.execute(
                "UPDATE projects SET name = ?, source_video = ?, status = 'pending', updated_at = ? WHERE id = ?",
                (Path(uploaded.filename).stem[:160], path, _now(), project_id),
            )
            _save_meta(conn, project_id, {"filename": stored_name, "original_filename": uploaded.filename, "probe": _probe_media(path)})
        return jsonify(project_payload(project_id, detail=True))

    @flask_app.route("/api/projects/<int:project_id>/transcript", methods=["POST"], endpoint="studio_attach_transcript")
    def studio_attach_transcript(project_id):
        uploaded = request.files.get("transcript")
        if not uploaded or not uploaded.filename:
            return jsonify({"error": "Selecione um arquivo de transcrição."}), 400
        project = runtime["get_project"](project_id)
        if not project:
            return jsonify({"error": "Projeto não encontrado."}), 404
        try:
            text = uploaded.read().decode("utf-8-sig")
            duration = source_duration(project.get("source_video"))
            parsed = runtime["parse_transcript_text"](text, duration=duration or None)
            segments = parsed.get("segments", [])
            if not segments:
                raise ValueError("Nenhum segmento timestampado foi encontrado.")
            runtime["save_transcription"](
                project_id,
                segments,
                parsed.get("full_text", ""),
                parsed.get("language", "pt"),
                "manual_confirmed",
                provenance={"source": "local_file", "filename": uploaded.filename},
            )
            return jsonify(project_payload(project_id, detail=True))
        except (UnicodeDecodeError, TypeError, ValueError) as exc:
            return jsonify({"error": f"Transcrição inválida: {exc}"}), 400

    @flask_app.get("/api/studio/status", endpoint="studio_status")
    def studio_status():
        settings = runtime["get_all_settings"]()
        ai_checker = runtime.get("_check_ai_status")
        try:
            ai = ai_checker(settings) if ai_checker else {"status": "unknown", "backend": settings.get("ai_backend", "auto")}
        except Exception as exc:
            ai = {"status": "error", "backend": settings.get("ai_backend", "auto"), "error": str(exc)[:180]}
        try:
            whisper_fast = importlib.util.find_spec("faster_whisper") is not None
        except (ImportError, ValueError):
            whisper_fast = False
        try:
            whisper_openai = importlib.util.find_spec("whisper") is not None
        except (ImportError, ValueError):
            whisper_openai = False
        return jsonify({
            "program_version": runtime.get("PROGRAM_VERSION", ""),
            "program_revision": runtime.get("PROGRAM_REVISION", ""),
            "ai": {
                **ai,
                "gemini_configured": bool(str(settings.get("gemini_api_key", "") or "").strip()),
                "ollama_url": str(settings.get("ollama_url", "") or ""),
                "ollama_model": str(settings.get("ollama_model", "") or ""),
            },
            "whisper": {
                "configured_source": str(settings.get("transcription_source", "auto") or "auto"),
                "model": str(settings.get("whisper_model", "small") or "small"),
                "faster_whisper_installed": whisper_fast,
                "openai_whisper_installed": whisper_openai,
                "available": whisper_fast or whisper_openai,
                "device": str(settings.get("whisper_device", "auto") or "auto"),
            },
            "ffmpeg": {"available": bool(shutil.which("ffmpeg")), "ffprobe_available": bool(shutil.which("ffprobe"))},
            "chub": {"optional": True, "attached_to_project": False},
        })

    @flask_app.route("/api/projects/<int:project_id>/transcribe", methods=["POST"], endpoint="studio_transcribe")
    def studio_transcribe(project_id):
        payload = request.get_json(silent=True) or {}
        project = runtime["get_project"](project_id)
        if not project or not project.get("source_video"):
            return jsonify({"error": "Importe um vídeo antes de transcrever."}), 400
        source = project["source_video"]
        saved = runtime["get_transcription"](project_id) or {}
        if saved.get("segments") and not bool(payload.get("force_whisper")):
            def cached_task(ctx):
                segments = list(saved.get("segments") or [])
                ctx.update(stage="transcription_cached", progress=100, message="Transcript persistido reutilizado; Whisper não foi executado")
                return {"artifacts": [{"type": "transcription_cached", "project_id": project_id, "segments": len(segments)}]}

            job = runtime["job_manager"].submit("studio_transcribe_cached", cached_task, project_id=project_id)
            return jsonify({"jobId": job["id"], "job_id": job["id"], "state": job.get("state", "queued"), "cached": True})

        def task(ctx):
            settings = runtime["get_all_settings"]()
            if bool(payload.get("force_whisper")):
                settings = {**settings, "transcription_source": "whisper"}
                ctx.update(stage="transcribing", message="Whisper local selecionado manualmente")
            result = runtime["_transcribe_video_automatically"](
                source,
                settings,
                lambda message, level="info": ctx.update(stage="transcribing", message=str(message)[:500], level=level),
                cancel_check=ctx.check_cancel,
            )
            if not result or not result.get("segments"):
                raise RuntimeError("A transcrição não produziu segmentos timestampados.")
            runtime["save_transcription"](
                project_id,
                result["segments"],
                result.get("full_text", ""),
                result.get("language", "pt"),
                result.get("source", "whisper"),
                provenance={"source": result.get("source", "automatic")},
            )
            return {"artifacts": [{"type": "transcription", "project_id": project_id, "segments": len(result["segments"])}]}

        job = runtime["job_manager"].submit("studio_transcribe", task, project_id=project_id)
        return jsonify({"jobId": job["id"], "job_id": job["id"], "state": job.get("state", "queued")})

    @flask_app.route("/api/clips/<int:clip_id>/decision", methods=["POST"], endpoint="studio_decision")
    def studio_decision(clip_id):
        payload = request.get_json(silent=True) or {}
        decision = str(payload.get("decision") or "").strip().lower()
        if decision == "suggested":
            decision = "needs_review"
        if decision not in {"approved", "rejected", "needs_review"}:
            return jsonify({"error": "Decisão inválida."}), 400
        try:
            row = runtime["get_clip"](clip_id)
            if not row:
                return jsonify({"error": "Clip não encontrado."}), 404
            reason_code = str(payload.get("reason_code") or "").strip()[:48]
            quality_tags = payload.get("quality_tags") if isinstance(payload.get("quality_tags"), list) else []
            note = str(payload.get("note") or "Decisão registrada na Revisão do Studio.")[:600]
            runtime["save_clip_feedback"](
                clip_id,
                decision,
                note=note,
                reason_code=reason_code,
                quality_tags=quality_tags[:12],
            )
            matrix_saved = False
            builder = runtime.get("build_disagreement_record")
            saver = runtime.get("save_disagreement_record")
            if builder and saver:
                try:
                    project_id = row.get("project_id")
                    chub = _chub_summary(_get_meta(runtime, project_id).get("chub_context"))
                    record = builder(
                        row,
                        {"action": decision, "reason_code": reason_code, "quality_tags": quality_tags, "note": note},
                        project_context=chub,
                    )
                    saver(record, project_id=project_id, clip_id=clip_id)
                    matrix_saved = True
                except Exception as storage_error:
                    # A matrix is auxiliary; a failure must never block the human decision.
                    flask_app.logger.warning("Não foi possível registrar a matriz de discordância: %s", storage_error)
            result = clip_payload(runtime["get_clip"](clip_id) or row)
            result["disagreement"] = {"saved": matrix_saved, "schema_version": "editorial-disagreement-v1"}
            return jsonify(result)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @flask_app.route("/api/editorial/disagreements", methods=["GET"], endpoint="studio_disagreements")
    def studio_disagreements():
        loader = runtime.get("load_disagreement_records")
        if not loader:
            return jsonify({"records": [], "summary": {"status": "unavailable"}})
        try:
            project_id = request.args.get("project_id", type=int)
            clip_id = request.args.get("clip_id", type=int)
            limit = min(500, max(1, int(request.args.get("limit", 200))))
        except (TypeError, ValueError):
            return jsonify({"error": "Parâmetros de matriz inválidos."}), 400
        records = loader(project_id=project_id, limit=limit) if project_id is not None else []
        if clip_id is not None:
            records = [
                item for item in records
                if isinstance(item.get("clip"), dict) and str(item["clip"].get("clip_id")) == str(clip_id)
            ]
        summarizer = runtime.get("summarize_records")
        summary = summarizer(records, limit=limit) if summarizer else {"status": "unavailable"}
        return jsonify({"records": records, "summary": summary, "read_only": True})

    @flask_app.route("/api/clips/<int:clip_id>/range", methods=["POST"], endpoint="studio_range")
    def studio_range(clip_id):
        payload = request.get_json(silent=True) or {}
        row = runtime["get_clip"](clip_id)
        if not row:
            return jsonify({"error": "Clip não encontrado."}), 404
        try:
            start = float(payload.get("start"))
            end = float(payload.get("end"))
        except (TypeError, ValueError):
            return jsonify({"error": "Intervalo inválido."}), 400
        project = runtime["get_project"](row["project_id"])
        duration = source_duration(project.get("source_video")) if project else None
        transcript = runtime["get_transcription"](row["project_id"]) or {}
        candidate = {
            "start": float(row.get("start_time") or 0),
            "end": float(row.get("end_time") or 0),
            "duration": float(row.get("duration") or 0),
        }
        snap_value = payload.get("snap_to_transcript", False)
        snap_to_transcript = str(snap_value).strip().lower() in {"1", "true", "yes", "on"}
        try:
            adjusted = runtime["adjust_clip_bounds"](
                candidate,
                start=start,
                end=end,
                transcript_segments=transcript.get("segments", []),
                duration=duration or None,
                min_duration=1.0,
                snap_tolerance=2.0 if snap_to_transcript else 0.0,
            )
            runtime["save_clip_adjustment"](clip_id, adjusted, note="Intervalo ajustado na janela de Revisão.")
            with db() as conn:
                conn.execute(
                    "UPDATE clips SET start_time = ?, end_time = ?, duration = ?, file_path = '', export_path = '', status = 'pending', review_status = 'needs_review' WHERE id = ?",
                    (adjusted["start"], adjusted["end"], adjusted["duration"], clip_id),
                )
            return jsonify(clip_payload(runtime["get_clip"](clip_id)))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @flask_app.route("/api/clips/<int:clip_id>/title", methods=["POST"], endpoint="studio_title")
    def studio_title(clip_id):
        payload = request.get_json(silent=True) or {}
        title = str(payload.get("title") or "").strip()[:300]
        if not title:
            return jsonify({"error": "A headline não pode ficar vazia."}), 400
        row = runtime["get_clip"](clip_id)
        if not row:
            return jsonify({"error": "Clip não encontrado."}), 404
        with db() as conn:
            conn.execute("UPDATE clips SET suggested_titles = ? WHERE id = ?", (json.dumps([title], ensure_ascii=False), clip_id))
        return jsonify(clip_payload(runtime["get_clip"](clip_id)))

    @flask_app.route("/api/projects/<int:project_id>/seo", methods=["POST"], endpoint="studio_seo")
    def studio_seo(project_id):
        payload = request.get_json(silent=True) or {}
        clip_id = payload.get("clip_id")
        clips = runtime["get_clips"](project_id)
        row = next((item for item in clips if str(item.get("id")) == str(clip_id)), None) if clip_id else (clips[0] if clips else None)
        if not row:
            return jsonify({"error": "Nenhum corte disponível para gerar headline."}), 404
        transcription = runtime["get_transcription"](project_id) or {}
        transcript = str(row.get("transcript") or transcription.get("full_text") or "").strip()
        if not transcript:
            return jsonify({"error": "Anexe ou gere uma transcrição antes da headline."}), 400
        try:
            from modules.headline_studio import generate_artwork_copy
            result = generate_artwork_copy(
                transcript,
                mini_context=str(row.get("title") or "Renan Santos"),
                preferred_format="vertical_916",
                editorial_learning=runtime["get_headline_learning_preferences"](),
                segments=transcription.get("segments") or None,
            )
            suggestions = ((result.get("formats") or {}).get("vertical_916") or {}).get("suggestions") or []
            titles = [str(item.get("headline") or "").strip() for item in suggestions if str(item.get("headline") or "").strip()]
            if not titles:
                titles = [str(row.get("title") or "Corte editorial").strip()]
            hashtags = _hashtags(transcript)
            runtime["update_clip_seo"](
                int(row["id"]),
                titles[:5],
                _topic_tags(transcript),
                str(result.get("recommendation_reason") or "Headline local baseada na transcrição.")[:600],
                hashtags,
            )
            return jsonify({"title": titles[0], "titles": titles[:5], "hashtags": hashtags, "description": result.get("recommendation_reason", ""), "studio": result})
        except Exception as exc:
            return jsonify({"error": f"Não foi possível gerar a headline: {exc}"}), 500

    @flask_app.route("/api/projects/<int:project_id>/chub-context", methods=["POST"], endpoint="studio_chub_attach")
    def studio_chub_attach(project_id):
        try:
            normalized = _normalize_chub(request.get_json(silent=True) or {})
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        if not runtime["get_project"](project_id):
            return jsonify({"error": "Projeto não encontrado."}), 404
        with db() as conn:
            _save_meta(conn, project_id, {"chub_context": normalized})
        return jsonify(project_payload(project_id, detail=True))

    @flask_app.route("/api/projects/<int:project_id>/chub-context", methods=["DELETE"], endpoint="studio_chub_clear")
    def studio_chub_clear(project_id):
        if not runtime["get_project"](project_id):
            return jsonify({"error": "Projeto não encontrado."}), 404
        with db() as conn:
            _save_meta(conn, project_id, {"chub_context": {}})
        return jsonify(project_payload(project_id, detail=True))

    @flask_app.route("/api/clips/<int:clip_id>/export", methods=["POST"], endpoint="studio_export")
    def studio_export(clip_id):
        row = runtime["get_clip"](clip_id)
        if not row:
            return jsonify({"error": "Clip não encontrado."}), 404
        if row.get("review_status") != "approved":
            return jsonify({"error": "Aprove o corte antes de exportar."}), 409
        project = runtime["get_project"](row["project_id"])
        if not project or not project.get("source_video"):
            return jsonify({"error": "A fonte original não está disponível."}), 404
        source = project["source_video"]
        start = float(row.get("start_time") or 0)
        end = float(row.get("end_time") or 0)
        name = _safe_name(project.get("name") or "projeto")
        export_root = os.path.join(runtime["EXPORT_DIR"], name)
        os.makedirs(export_root, exist_ok=True)
        output = os.path.join(export_root, f"{name}_clip_{clip_id}.mp4")

        def task(ctx):
            from modules.video_cutter import VideoCutter
            cutter = VideoCutter(method="intelligent", target_duration=max(1, end - start), preset="shorts")
            ctx.update(stage="rendering", progress=15, message="Renderizando formato vertical")
            def render_progress(message, level="info"):
                ctx.update(message=str(message)[:500], stage="rendering", level=level)

            rendered = cutter.cut_clip(
                source,
                start,
                end,
                output,
                vertical=True,
                emit_progress=render_progress,
                cancel_check=ctx.check_cancel,
            )
            if not rendered:
                raise RuntimeError("O FFmpeg não conseguiu renderizar o corte vertical.")
            transcription = runtime["get_transcription"](row["project_id"]) or {}
            segments = []
            for segment in transcription.get("segments", []):
                seg_start = float(segment.get("start", 0))
                seg_end = float(segment.get("end", 0))
                if seg_end > start and seg_start < end:
                    segments.append({**segment, "start": max(0.0, seg_start - start), "end": max(0.2, min(end, seg_end) - start)})
            if segments:
                from modules.subtitle_generator import SubtitleGenerator
                settings = runtime["get_all_settings"]()
                with tempfile.TemporaryDirectory(dir=runtime["EXPORT_DIR"]) as temp_dir:
                    ass_path = os.path.join(temp_dir, "captions.ass")
                    captioned = os.path.join(temp_dir, "captioned.mp4")
                    SubtitleGenerator(settings).generate_ass_file(segments, ass_path, video_width=1080, video_height=1920)
                    captioned_result = SubtitleGenerator(settings).burn_subtitles(rendered, ass_path, captioned, emit_progress=lambda message: ctx.update(message=str(message)[:500], stage="captions"))
                    if captioned_result and os.path.isfile(captioned_result):
                        os.replace(captioned_result, rendered)
            with db() as conn:
                conn.execute("UPDATE clips SET export_path = ?, status = 'completed' WHERE id = ?", (rendered, clip_id))
            ctx.update(stage="completed", progress=100, message="Export vertical pronto")
            return {"artifacts": [{"type": "export", "clip_id": clip_id, "path": rendered}]}

        job = runtime["job_manager"].submit("studio_export", task, project_id=row["project_id"])
        return jsonify({"jobId": job["id"], "job_id": job["id"], "state": job.get("state", "queued")})

    def studio_list_projects():
        projects = runtime["get_all_projects"]()
        return jsonify([_project_payload(item["id"], runtime, safe_url, source_duration, detail=False) for item in projects])

    def studio_get_project(project_id):
        payload = project_payload(project_id, detail=True)
        if payload.get("error"):
            return jsonify(payload), 404
        return jsonify(payload)

    # Replace only the two legacy view callables; all processing routes and the
    # database engine remain the original Furia 1 implementation.
    flask_app.view_functions["api_list_projects"] = studio_list_projects
    flask_app.view_functions["api_get_project"] = studio_get_project


def _ensure_meta_table(runtime):
    path = runtime["DB_PATH"]
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS studio_project_meta (project_id INTEGER PRIMARY KEY, payload TEXT NOT NULL DEFAULT '{}', updated_at TEXT NOT NULL)")
        conn.commit()
    finally:
        conn.close()


def _reset_source_state(runtime, project_id):
    """Invalidate source-specific state before replacing a project video."""
    reset = runtime.get("reset_project_source_state")
    if callable(reset):
        reset(project_id)
        return
    conn = runtime["get_db"]()
    try:
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
        clip_ids = []
        if "clips" in tables:
            clip_ids = [row["id"] for row in conn.execute("SELECT id FROM clips WHERE project_id = ?", (project_id,)).fetchall()]
        if clip_ids:
            placeholders = ",".join("?" for _ in clip_ids)
            for table in ("clip_feedback", "headline_feedback"):
                if table in tables:
                    conn.execute(f"DELETE FROM {table} WHERE clip_id IN ({placeholders})", clip_ids)
        if "clips" in tables:
            conn.execute("DELETE FROM clips WHERE project_id = ?", (project_id,))
        if "transcriptions" in tables:
            conn.execute("DELETE FROM transcriptions WHERE project_id = ?", (project_id,))
        conn.commit()
    finally:
        conn.close()


def _save_meta(conn, project_id, updates):
    row = conn.execute("SELECT payload FROM studio_project_meta WHERE project_id = ?", (project_id,)).fetchone()
    payload = {}
    if row:
        try:
            value = json.loads(row[0] or "{}")
            payload = value if isinstance(value, dict) else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = {}
    payload.update(updates)
    conn.execute(
        "INSERT OR REPLACE INTO studio_project_meta (project_id, payload, updated_at) VALUES (?, ?, ?)",
        (project_id, json.dumps(payload, ensure_ascii=False), _now()),
    )


def _get_meta(runtime, project_id):
    conn = runtime["get_db"]()
    try:
        row = conn.execute("SELECT payload FROM studio_project_meta WHERE project_id = ?", (project_id,)).fetchone()
    finally:
        conn.close()
    if not row:
        return {}
    try:
        value = json.loads(row[0] or "{}")
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _project_payload(project_id, runtime, safe_url, duration_fn, detail=False):
    project = runtime["get_project"](project_id)
    if not project:
        return {"error": "Projeto não encontrado."}
    raw_clips = runtime["get_clips"](project_id)
    transcription = runtime["get_transcription"](project_id) or {}
    source = project.get("source_video") or ""
    duration = duration_fn(source) if source else 0.0
    meta = _get_meta(runtime, project_id)
    probe = meta.get("probe") if isinstance(meta.get("probe"), dict) else _probe_media(source)
    status = str(project.get("status") or "pending")
    if raw_clips:
        status = "ready_review"
    elif source and status == "completed":
        status = "ready_no_results"
    elif source:
        status = "ready"
    else:
        status = "empty"
    clip_count = len(raw_clips)
    clips = [_clip_payload(item, runtime, duration_fn) for item in raw_clips] if detail else []
    approved_count = sum(1 for item in raw_clips if str(item.get("review_status") or "") == "approved")
    exported_count = sum(1 for item in raw_clips if str(item.get("review_status") or "") == "approved" and str(item.get("export_path") or "") and os.path.isfile(str(item.get("export_path"))))
    review_count = sum(1 for item in raw_clips if str(item.get("review_status") or "pending") not in {"approved", "rejected"})
    result = {
        "id": project["id"],
        "name": project.get("name") or "Projeto local",
        "filename": os.path.basename(source) if source else "",
        "sourceVideo": source,
        "duration": round(duration, 3),
        "width": int(probe.get("width") or 0),
        "height": int(probe.get("height") or 0),
        "status": status,
        "stage": f"{clip_count} momentos encontrados" if clip_count else ("Análise concluída; nenhum corte pronto" if status == "ready_no_results" else "Fonte importada" if source else "Aguardando uma fonte"),
        "progress": 100 if clip_count or status == "ready_no_results" else 0,
        "candidateCount": clip_count,
        "approvedCount": approved_count,
        "reviewCount": review_count,
        "exportedCount": exported_count,
        "thumbnail": next((clip.get("thumbnail") for clip in clips if clip.get("thumbnail")), safe_url(_thumbnail_for_project(source, runtime))),
        "videoUrl": safe_url(source),
        "createdAt": project.get("created_at", ""),
        "updatedAt": project.get("updated_at", ""),
        "transcriptCount": len(transcription.get("segments", [])),
        "chub": _chub_summary(meta.get("chub_context")),
        "clips": clips,
    }
    if detail:
        result["transcript"] = transcription.get("segments", [])
        result["transcription"] = transcription
        result["analysis"] = {"candidate_count": clip_count, "method": "Furia 1 editorial engine + local persistence", "confidence": "explainable"}
        result["chubContext"] = meta.get("chub_context") or {}
    return result


def _clip_payload(row, runtime, duration_fn):
    if not row:
        return {}
    titles = _json_list(row.get("suggested_titles"))
    title = titles[0] if titles else _title_from_transcript(row.get("transcript"))
    score = int(row.get("viral_score") or 0)
    raw_factors = row.get("score_factors")
    factors = _json_object(raw_factors)
    reasons = []
    for key, value in factors.items():
        if key.startswith("_"):
            continue
        if isinstance(value, (int, float)):
            reasons.append(f"{key.replace('_', ' ')} {round(float(value), 1)}")
        elif isinstance(value, str) and value.strip():
            reasons.append(value.strip()[:120])
    if not reasons:
        reasons = ["gancho editorial", "fala contínua", "sinais locais"]
    review = str(row.get("review_status") or "pending")
    status = {"pending": "suggested", "needs_review": "suggested", "approved": "approved", "rejected": "rejected"}.get(review, "suggested")
    review_flags = row.get("review_flags") if isinstance(row.get("review_flags"), dict) else _json_object(row.get("review_flags"))
    if not review_flags and isinstance(factors.get("_review_flags"), dict):
        review_flags = dict(factors.get("_review_flags") or {})
    review_codes = [str(item).strip()[:80] for item in _json_list(review_flags.get("review_reason_codes")) if str(item).strip()]
    review_reasons = [str(item).strip()[:240] for item in _json_list(review_flags.get("review_reasons")) if str(item).strip()]
    starts_with_question_only = bool(row.get("starts_with_question_only") or review_flags.get("starts_with_question_only"))
    ending_interruption = bool(row.get("ending_interruption") or review_flags.get("ending_interruption"))
    if starts_with_question_only and "starts_with_question_only" not in review_codes:
        review_codes.append("starts_with_question_only")
    if ending_interruption and "ending_interruption" not in review_codes:
        review_codes.append("ending_interruption")
    export_path = row.get("export_path") or ""
    if export_path and os.path.isfile(str(export_path)) and review == "approved":
        status = "exported"
    thumb = row.get("thumbnail_path") or ""
    source_project = runtime["get_project"](row.get("project_id")) or {}
    source = source_project.get("source_video") or ""
    block = {}
    try:
        block = runtime["build_editorial_block"]({
            "index": row.get("id"),
            "start": float(row.get("start_time") or 0),
            "end": float(row.get("end_time") or 0),
            "duration": float(row.get("duration") or 0),
            "text": str(row.get("transcript") or ""),
            "title": title,
            "thesis": title,
            "reason": reasons[0] if reasons else "sinais editoriais locais",
            "source_family": "furia1_local",
            "tags": _topic_tags(row.get("transcript") or ""),
            "confidence": float(row.get("score_confidence") or 0),
            "review_required": review not in {"approved"},
            "context_contract": {"source": "local", "score_separate_from_memory": True},
        })
    except Exception:
        block = {"state": "review", "thesis": title, "moment_reason": reasons[0] if reasons else "sinais editoriais locais", "suggested_moments": []}
    return {
        "id": row.get("id"),
        "projectId": row.get("project_id"),
        "start": round(float(row.get("start_time") or 0), 3),
        "end": round(float(row.get("end_time") or 0), 3),
        "duration": round(float(row.get("duration") or 0), 3),
        "title": title[:300],
        "score": score,
        "reasons": reasons[:8],
        "status": status,
        "reviewStatus": review,
        "transcript": str(row.get("transcript") or ""),
        "thumbnail": _studio_url(thumb, runtime),
        "exportUrl": _studio_url(export_path, runtime),
        "sourceVideo": source,
        "scoreFactors": factors,
        "confidence": float(row.get("score_confidence") or 0),
        "reviewFlags": review_flags,
        "review_flags": review_flags,
        "reviewReasonCodes": review_codes[:12],
        "review_reason_codes": review_codes[:12],
        "reviewReasons": review_reasons[:12],
        "review_reasons": review_reasons[:12],
        "startsWithQuestionOnly": starts_with_question_only,
        "starts_with_question_only": starts_with_question_only,
        "endingInterruption": ending_interruption,
        "ending_interruption": ending_interruption,
        "reviewRequired": review != "approved" or bool(review_codes),
        "editorialKey": row.get("editorial_key") or "",
        "editorialBlock": block,
    }


def _studio_url(path, runtime):
    if not path:
        return ""
    raw = os.path.abspath(str(path))
    roots = [runtime.get(name, "") for name in ("WORKSPACE_DIR", "UPLOAD_DIR", "THUMBNAIL_DIR", "PROCESSED_DIR", "EXPORT_DIR", "PERSISTENT_DATA_DIR")]
    if any(_is_under(raw, os.path.abspath(str(root))) for root in roots if root):
        return "/studio-file?path=" + quote(raw)
    return ""


def _probe_media(path):
    if not path or not os.path.isfile(str(path)):
        return {}
    try:
        result = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height:format=duration",
            "-of", "json", str(path),
        ], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        payload = json.loads(result.stdout or "{}")
        stream = (payload.get("streams") or [{}])[0]
        fmt = payload.get("format") or {}
        return {"width": int(stream.get("width") or 0), "height": int(stream.get("height") or 0), "duration": float(fmt.get("duration") or 0)}
    except (OSError, ValueError, TypeError, subprocess.SubprocessError, json.JSONDecodeError):
        return {}


def _thumbnail_for_project(source, runtime):
    if not source:
        return ""
    base = os.path.splitext(os.path.basename(source))[0]
    candidate = os.path.join(runtime.get("THUMBNAIL_DIR", ""), f"{base}.jpg")
    return candidate if os.path.isfile(candidate) else ""


def _json_list(raw):
    try:
        value = json.loads(raw or "[]") if isinstance(raw, str) else raw
        return value if isinstance(value, list) else []
    except (TypeError, ValueError, json.JSONDecodeError):
        return []


def _json_object(raw):
    try:
        value = json.loads(raw or "{}") if isinstance(raw, str) else raw
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _title_from_transcript(raw):
    text = " ".join(str(raw or "").split())
    if not text:
        return "Corte editorial"
    sentence = re.split(r"[.!?]", text)[0].strip()
    return (sentence or text)[:120]


def _normalize_chub(payload):
    if not isinstance(payload, dict):
        raise ValueError("Selecione um JSON de contexto do Campaign Hub.")

    # Official profile snapshots carry account-scoped aggregates rather than the
    # compact Studio shape. Adapt only bounded editorial metadata: never copy raw
    # transcripts, blocks or metrics into the project attachment.
    if isinstance(payload.get("accounts"), dict):
        default_account = str(payload.get("default_account") or "@renansantosmbl").strip()
        channel = default_account if default_account in ALLOWED_CHANNELS else "@renansantosmbl"
        account_data = payload.get("accounts", {}).get(channel, {})
        if not isinstance(account_data, dict):
            account_data = {}
        hooks = []
        raw_hooks = account_data.get("hook_observations") or account_data.get("hook_priors") or []
        if isinstance(raw_hooks, list):
            for item in raw_hooks[:100]:
                if not isinstance(item, dict):
                    continue
                hook = str(item.get("hook") or item.get("family") or "").strip()
                if not hook:
                    continue
                hooks.append({
                    "label": hook[:80],
                    "family": hook[:80],
                    "observations": item.get("observations", item.get("n")),
                    "medianRatio": item.get("median_ratio", item.get("mean_ratio", item.get("median"))),
                    "p90": item.get("p90"),
                })
        records = payload.get("records") if isinstance(payload.get("records"), dict) else {}
        raw_posts = records.get("posts", []) if isinstance(records.get("posts"), list) else []
        top_posts = [item for item in raw_posts[:50] if isinstance(item, dict)]
        platforms = []
        for item in (account_data.get("platforms") or [account_data.get("platform")]):
            value = str(item or "").strip()
            if value and value not in platforms:
                platforms.append(value)
        sync = payload.get("sync") if isinstance(payload.get("sync"), dict) else {}
        return {
            "schemaVersion": str(payload.get("schema_version") or payload.get("version") or "1.0")[:20],
            "source": "campaign-hub",
            "fetchedAt": str(payload.get("collected_at") or sync.get("last_sync_at") or "")[:60],
            "channel": channel,
            "scope": {"platforms": platforms[:8], "metric": "aggregate_reference", "windowDays": None},
            "topPosts": top_posts,
            "hooks": hooks[:50],
            "cohorts": [item for item in (account_data.get("cohorts") or [])[:25] if isinstance(item, dict)],
            "references": [{"source": "campaign-hub-profile", "syncStatus": str(sync.get("status") or "ready")[:40]}],
            "recordCounts": payload.get("record_counts") if isinstance(payload.get("record_counts"), dict) else {},
            "accounts": sorted(str(key) for key in payload.get("accounts", {}) if str(key) in ALLOWED_CHANNELS),
            "readOnly": True,
            "scoreTechnical": False,
        }

    # The official local mirror is an aggregate export. It has no single
    # `source=campaign-hub` record, so adapt its bounded historical aggregates
    # into the same read-only context shape used by the project attachment.
    if str(payload.get("schema") or "").lower() == "espelho-chub-v1":
        channel = str(payload.get("default_account") or "@renansantosmbl").strip()
        if channel not in ALLOWED_CHANNELS:
            channel = "@renansantosmbl"
        hooks = []
        for item in payload.get("ganchos", []) if isinstance(payload.get("ganchos"), list) else []:
            if not isinstance(item, dict) or str(item.get("conta") or "").strip() not in {"", channel}:
                continue
            hooks.append({
                "channel": item.get("conta") or channel,
                "platform": item.get("plataforma", ""),
                "family": item.get("familia", ""),
                "observations": item.get("n", 0),
                "median": item.get("mediana"),
                "p90": item.get("p90"),
            })
        platforms = []
        for item in hooks:
            platform = str(item.get("platform") or "").strip()
            if platform and platform not in platforms:
                platforms.append(platform)
        return {
            "schemaVersion": "espelho-chub-v1",
            "source": "campaign-hub",
            "fetchedAt": str(payload.get("gerado_em") or "")[:60],
            "channel": channel,
            "scope": {"platforms": platforms[:8], "metric": "aggregate_reference", "windowDays": None},
            "topPosts": [],
            "hooks": hooks[:50],
            "cohorts": [],
            "references": [{"source": "espelho-chub-v1", "origin": payload.get("origem", "")}],
            "accounts": [channel],
            "readOnly": True,
            "scoreTechnical": False,
        }
    if str(payload.get("source") or "").lower() != "campaign-hub":
        raise ValueError("JSON não reconhecido. Use um contexto com source=campaign-hub ou o espelho agregado schema=espelho-chub-v1.")
    channel = str(payload.get("channel") or "").strip()
    if channel not in ALLOWED_CHANNELS:
        raise ValueError("Conta chub desconhecida.")
    scope = payload.get("scope") if isinstance(payload.get("scope"), dict) else {}
    return {
        "schemaVersion": str(payload.get("schemaVersion") or "1.0")[:20],
        "source": "campaign-hub",
        "fetchedAt": str(payload.get("fetchedAt") or "")[:60],
        "channel": channel,
        "scope": {
            "platforms": [str(item)[:24] for item in scope.get("platforms", []) if str(item).strip()][:8],
            "metric": str(scope.get("metric") or "settled_ratio")[:60],
            "windowDays": int(scope["windowDays"]) if str(scope.get("windowDays", "")).isdigit() else None,
        },
        "topPosts": payload.get("topPosts", [])[:50] if isinstance(payload.get("topPosts"), list) else [],
        "hooks": payload.get("hooks", [])[:50] if isinstance(payload.get("hooks"), list) else [],
        "cohorts": payload.get("cohorts", [])[:25] if isinstance(payload.get("cohorts"), list) else [],
        "references": payload.get("references", [])[:50] if isinstance(payload.get("references"), list) else [],
        "recordCounts": payload.get("recordCounts", {}) if isinstance(payload.get("recordCounts"), dict) else {},
        "accounts": [channel],
        "readOnly": True,
        "scoreTechnical": False,
    }


def _chub_summary(context):
    if not isinstance(context, dict) or context.get("source") != "campaign-hub":
        return {"available": False}
    scope = context.get("scope") if isinstance(context.get("scope"), dict) else {}
    return {
        "available": True,
        "channel": context.get("channel", ""),
        "fetchedAt": context.get("fetchedAt", ""),
        "schemaVersion": context.get("schemaVersion", ""),
        "platforms": scope.get("platforms", []),
        "metric": scope.get("metric", "settled_ratio"),
        "windowDays": scope.get("windowDays"),
        "topPosts": context.get("topPosts", [])[:3],
        "hooks": context.get("hooks", [])[:5],
        "cohorts": context.get("cohorts", [])[:3],
        "recordCounts": context.get("recordCounts", {}) if isinstance(context.get("recordCounts"), dict) else {},
        "accounts": context.get("accounts", [context.get("channel", "")]),
        "readOnly": True,
        "scoreTechnical": False,
    }


def _hashtags(text):
    words = re.findall(r"[A-Za-zÀ-ÿ0-9]{5,}", str(text or "").lower())
    stop = {"porque", "quando", "muito", "sobre", "também", "assim", "aquela", "aquele", "vocês", "estão", "seria"}
    result = []
    for word in words:
        normalized = word.replace("á", "a").replace("ã", "a").replace("é", "e").replace("ê", "e").replace("ç", "c")
        tag = f"#{normalized}"
        if word not in stop and tag not in result:
            result.append(tag)
    return result[:6] or ["#RenanSantos", "#politica"]


def _topic_tags(text):
    return [tag.lstrip("#") for tag in _hashtags(text)]


def _safe_name(value):
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value or "projeto").strip().lower()).strip("-")
    return cleaned[:80] or "projeto"


def _is_under(path, root):
    try:
        return os.path.commonpath([os.path.abspath(path), os.path.abspath(root)]) == os.path.abspath(root)
    except (OSError, ValueError):
        return False


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
