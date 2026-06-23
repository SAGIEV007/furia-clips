import os
import sys
import json
import uuid
import shutil
import threading
from datetime import datetime

from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
from flask_socketio import SocketIO, emit

from config import (
    BASE_DIR, WORKSPACE_DIR, UPLOAD_DIR, PROCESSED_DIR,
    EXPORT_DIR, THUMBNAIL_DIR, ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE
)
from database import (
    init_db, get_all_settings, get_setting, set_setting,
    create_project, get_project, get_all_projects, update_project_status,
    save_clip, get_clips, update_clip_seo, update_clip_thumbnail,
    save_transcription, get_transcription, log_action
)

app = Flask(__name__)
app.config["SECRET_KEY"] = "furia-clips-secret-key"
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

processing_lock = threading.Lock()
current_task = {"active": False, "cancel": False}


def emit_progress(message, level="info"):
    socketio.emit("progress", {"message": message, "level": level, "time": datetime.now().strftime("%H:%M:%S")})


def emit_status(status, data=None):
    socketio.emit("status", {"status": status, "data": data or {}})


# ─── Page Routes ───

@app.route("/")
def index():
    return render_template("index.html")


# ─── API: Settings ───

@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    return jsonify(get_all_settings())


@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    data = request.json
    for key, value in data.items():
        set_setting(key, value)
    return jsonify({"success": True})


# ─── API: File Manager ───

@app.route("/api/files", methods=["GET"])
def api_list_files():
    path = request.args.get("path", "")
    base = WORKSPACE_DIR
    target = os.path.normpath(os.path.join(base, path))

    if not target.startswith(base):
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
    dest_path = os.path.join(WORKSPACE_DIR, dest_dir)
    os.makedirs(dest_path, exist_ok=True)

    filename = file.filename
    filepath = os.path.join(dest_path, filename)

    counter = 1
    base_name = os.path.splitext(filename)[0]
    while os.path.exists(filepath):
        filename = f"{base_name}_{counter}{ext}"
        filepath = os.path.join(dest_path, filename)
        counter += 1

    file.save(filepath)

    return jsonify({
        "success": True,
        "filename": filename,
        "path": os.path.relpath(filepath, WORKSPACE_DIR),
        "size": os.path.getsize(filepath),
    })


@app.route("/api/files/mkdir", methods=["POST"])
def api_mkdir():
    data = request.json
    name = data.get("name", "").strip()
    parent = data.get("parent", "")

    if not name:
        return jsonify({"error": "Nome da pasta nao informado"}), 400

    target = os.path.normpath(os.path.join(WORKSPACE_DIR, parent, name))
    if not target.startswith(WORKSPACE_DIR):
        return jsonify({"error": "Acesso negado"}), 403

    os.makedirs(target, exist_ok=True)
    return jsonify({"success": True, "path": os.path.relpath(target, WORKSPACE_DIR)})


@app.route("/api/files/delete", methods=["POST"])
def api_delete_file():
    data = request.json
    path = data.get("path", "")
    target = os.path.normpath(os.path.join(WORKSPACE_DIR, path))

    if not target.startswith(WORKSPACE_DIR) or target == WORKSPACE_DIR:
        return jsonify({"error": "Acesso negado"}), 403

    if os.path.isdir(target):
        shutil.rmtree(target)
    elif os.path.isfile(target):
        os.unlink(target)
    else:
        return jsonify({"error": "Arquivo nao encontrado"}), 404

    return jsonify({"success": True})


@app.route("/workspace/<path:filepath>")
def serve_workspace_file(filepath):
    full = os.path.normpath(os.path.join(WORKSPACE_DIR, filepath))
    if not full.startswith(WORKSPACE_DIR):
        return "Acesso negado", 403
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
    data = request.json
    video_path = os.path.join(WORKSPACE_DIR, data.get("video_path", ""))

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
    data = request.json
    video_path = os.path.join(WORKSPACE_DIR, data.get("video_path", ""))
    project_id = data.get("project_id")

    if not os.path.exists(video_path):
        return jsonify({"error": "Video nao encontrado"}), 404

    def task():
        current_task["active"] = True
        try:
            from modules.transcriber import Transcriber
            settings = get_all_settings()
            transcriber = Transcriber(
                model_name=settings.get("whisper_model", "small"),
                language=settings.get("language", "pt"),
            )
            result = transcriber.transcribe(video_path, emit_progress=emit_progress)

            if project_id:
                save_transcription(
                    project_id, result["segments"], result["full_text"],
                    result["language"], settings.get("whisper_model", "small")
                )

            emit_status("transcribe_complete", result)
            emit_progress("Transcricao concluida!", "success")
        except Exception as e:
            emit_progress(f"Erro na transcricao: {str(e)}", "error")
            emit_status("error", {"message": str(e)})
        finally:
            current_task["active"] = False

    if current_task["active"]:
        return jsonify({"error": "Ja existe um processamento em andamento"}), 409

    threading.Thread(target=task, daemon=True).start()
    return jsonify({"success": True, "message": "Transcricao iniciada"})


@app.route("/api/process/cut", methods=["POST"])
def api_cut_shorts():
    data = request.json
    video_path = os.path.join(WORKSPACE_DIR, data.get("video_path", ""))
    project_id = data.get("project_id")
    use_face_tracking = data.get("face_tracking", True)

    if not os.path.exists(video_path):
        return jsonify({"error": "Video nao encontrado"}), 404

    def task():
        current_task["active"] = True
        try:
            settings = get_all_settings()

            # Step 1: Transcribe
            emit_progress("=== ETAPA 1/5: Transcricao ===", "info")
            from modules.transcriber import Transcriber
            transcriber = Transcriber(
                model_name=settings.get("whisper_model", "small"),
                language=settings.get("language", "pt"),
            )
            transcription = transcriber.transcribe(video_path, emit_progress=emit_progress)

            if project_id:
                save_transcription(
                    project_id, transcription["segments"], transcription["full_text"],
                    transcription["language"], settings.get("whisper_model", "small")
                )

            # Step 2: Audio analysis
            emit_progress("=== ETAPA 2/5: Analise de Audio ===", "info")
            from modules.audio_analyzer import AudioAnalyzer
            analyzer = AudioAnalyzer()
            energy_profile = analyzer.analyze_energy(video_path, emit_progress=emit_progress)

            # Step 3: Find smart cuts
            emit_progress("=== ETAPA 3/5: Calculando Cortes ===", "info")
            from modules.video_cutter import VideoCutter
            cutter = VideoCutter(
                method=settings.get("cut_method", "intelligent"),
                target_duration=settings.get("cut_duration", 45),
            )
            candidates = cutter.find_smart_cuts(
                transcription["segments"], energy_profile,
                emit_progress=emit_progress
            )

            # Step 4: Rank by viral potential
            emit_progress("=== ETAPA 4/5: Ranqueamento Viral ===", "info")
            from modules.viral_ranker import ViralRanker
            ranker = ViralRanker(channel_context=settings.get("channel_context", ""))
            ranked = ranker.rank_clips(candidates, None)

            top_clips = ranked[:15]

            # Step 5: Cut clips with face tracking
            emit_progress("=== ETAPA 5/5: Cortando Clips ===", "info")

            face_positions_map = {}
            if use_face_tracking:
                try:
                    from modules.face_tracker import FaceTracker
                    tracker = FaceTracker()
                    all_faces = tracker.detect_faces_in_video(video_path, emit_progress=emit_progress)
                    for i, clip in enumerate(top_clips):
                        face_positions_map[i] = tracker.get_face_positions_for_segment(
                            all_faces, clip["start"], clip["end"]
                        )
                except Exception as e:
                    emit_progress(f"Face tracking indisponivel: {str(e)}. Usando crop centralizado.", "warning")

            project_name = os.path.splitext(os.path.basename(video_path))[0]
            output_dir = settings.get("output_dir", "") or ""
            results = cutter.batch_cut(
                video_path, top_clips, project_name,
                use_face_tracking=bool(face_positions_map),
                face_positions_map=face_positions_map,
                emit_progress=emit_progress,
                output_dir=output_dir if output_dir else None
            )

            # Save to DB
            if project_id:
                for i, res in enumerate(results):
                    clip_data = top_clips[i] if i < len(top_clips) else {}
                    save_clip(
                        project_id, res["path"], res["start"], res["end"],
                        res["duration"], clip_data.get("viral_score", 0),
                        clip_data.get("has_hook", False),
                        clip_data.get("emotional_intensity", 0),
                        res.get("text", "")
                    )

            clip_results = []
            for i, res in enumerate(results):
                clip_info = top_clips[i] if i < len(top_clips) else {}
                clip_results.append({
                    **res,
                    "viral_score": clip_info.get("viral_score", 0),
                    "has_hook": clip_info.get("has_hook", False),
                    "breakdown": clip_info.get("breakdown", {}),
                })

            emit_status("cut_complete", {"clips": clip_results})
            emit_progress(f"Corte completo! {len(results)} clips gerados e ranqueados.", "success")

        except Exception as e:
            emit_progress(f"Erro no corte: {str(e)}", "error")
            emit_status("error", {"message": str(e)})
        finally:
            current_task["active"] = False

    if current_task["active"]:
        return jsonify({"error": "Ja existe um processamento em andamento"}), 409

    threading.Thread(target=task, daemon=True).start()
    return jsonify({"success": True, "message": "Corte de shorts iniciado"})


@app.route("/api/process/subtitles", methods=["POST"])
def api_generate_subtitles():
    data = request.json
    video_path = os.path.join(WORKSPACE_DIR, data.get("video_path", ""))
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


@app.route("/api/process/thumbnail", methods=["POST"])
def api_generate_thumbnail():
    data = request.json
    video_path = os.path.join(WORKSPACE_DIR, data.get("video_path", ""))
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
    data = request.json
    video_path = os.path.join(WORKSPACE_DIR, data.get("video_path", ""))

    if not os.path.exists(video_path):
        return jsonify({"error": "Video nao encontrado"}), 404

    def task():
        current_task["active"] = True
        try:
            settings = get_all_settings()
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            project_id = create_project(video_name, data.get("video_path", ""))

            # ── Step 1: Remove silence ──
            emit_progress("━━━ ETAPA 1/6: Removendo Silencio ━━━", "info")
            from modules.silence_remover import SilenceRemover
            remover = SilenceRemover(
                silence_threshold=settings.get("silence_threshold", -35),
                min_silence_duration=settings.get("min_silence_duration", 0.5),
                padding=settings.get("padding", 0.25),
            )
            silence_result = remover.remove_silence(video_path, emit_progress=emit_progress)
            working_video = silence_result["output_path"] if silence_result else video_path

            # ── Step 2: Transcribe ──
            emit_progress("━━━ ETAPA 2/6: Transcrevendo ━━━", "info")
            from modules.transcriber import Transcriber
            transcriber = Transcriber(
                model_name=settings.get("whisper_model", "small"),
                language=settings.get("language", "pt"),
            )
            transcription = transcriber.transcribe(working_video, emit_progress=emit_progress)
            save_transcription(
                project_id, transcription["segments"], transcription["full_text"],
                transcription["language"], settings.get("whisper_model", "small")
            )

            # ── Step 3: Audio analysis ──
            emit_progress("━━━ ETAPA 3/6: Analisando Audio ━━━", "info")
            from modules.audio_analyzer import AudioAnalyzer
            analyzer = AudioAnalyzer()
            energy_profile = analyzer.analyze_energy(working_video, emit_progress=emit_progress)

            # ── Step 4: Smart cuts + ranking ──
            emit_progress("━━━ ETAPA 4/6: Cortando e Ranqueando ━━━", "info")
            from modules.video_cutter import VideoCutter
            from modules.viral_ranker import ViralRanker

            cutter = VideoCutter(
                method=settings.get("cut_method", "intelligent"),
                target_duration=settings.get("cut_duration", 45),
            )
            candidates = cutter.find_smart_cuts(
                transcription["segments"], energy_profile,
                emit_progress=emit_progress
            )

            ranker = ViralRanker(channel_context=settings.get("channel_context", ""))
            ranked = ranker.rank_clips(candidates)
            top_clips = ranked[:15]

            # Face tracking
            face_positions_map = {}
            try:
                from modules.face_tracker import FaceTracker
                tracker = FaceTracker()
                all_faces = tracker.detect_faces_in_video(video_path, emit_progress=emit_progress)
                for i, clip in enumerate(top_clips):
                    face_positions_map[i] = tracker.get_face_positions_for_segment(
                        all_faces, clip["start"], clip["end"]
                    )
            except Exception as e:
                emit_progress(f"Face tracking indisponivel: {str(e)}", "warning")

            output_dir = settings.get("output_dir", "") or ""
            results = cutter.batch_cut(
                video_path, top_clips, video_name,
                use_face_tracking=bool(face_positions_map),
                face_positions_map=face_positions_map,
                emit_progress=emit_progress,
                output_dir=output_dir if output_dir else None
            )

            # ── Step 5: Generate subtitles for each clip ──
            emit_progress("━━━ ETAPA 5/6: Gerando Legendas ━━━", "info")
            from modules.subtitle_generator import SubtitleGenerator
            sub_gen = SubtitleGenerator(settings)

            for i, res in enumerate(results):
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
                    sub_gen.generate_ass_file(clip_segments, ass_path, 1080, 1920)
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

            # ── Step 6: Generate SEO content ──
            emit_progress("━━━ ETAPA 6/6: Gerando Conteudo SEO ━━━", "info")
            from modules.ai_backend import AIBackend
            ai = AIBackend(
                backend=settings.get("ai_backend", "ollama"),
                settings=settings,
            )

            for res in results:
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
                        emit_progress(f"Erro SEO clip {res.get('clip_id')}: {str(e)}", "warning")

            update_project_status(project_id, "completed")

            clip_results = []
            for i, res in enumerate(results):
                clip_info = top_clips[i] if i < len(top_clips) else {}
                clip_results.append({
                    "path": os.path.relpath(res["path"], WORKSPACE_DIR),
                    "subtitled_path": os.path.relpath(res["subtitled_path"], WORKSPACE_DIR) if res.get("subtitled_path") else None,
                    "start": res["start"],
                    "end": res["end"],
                    "duration": res["duration"],
                    "viral_score": clip_info.get("viral_score", 0),
                    "has_hook": clip_info.get("has_hook", False),
                    "breakdown": clip_info.get("breakdown", {}),
                    "text": res.get("text", ""),
                    "seo": res.get("seo", {}),
                    "clip_id": res.get("clip_id"),
                })

            # Report where files are saved
            save_location = output_dir if output_dir else EXPORT_DIR
            emit_progress(f"Clips salvos em: {save_location}", "info")

            emit_status("complete_done", {
                "project_id": project_id,
                "clips": clip_results,
                "total_clips": len(clip_results),
                "output_dir": save_location,
            })
            emit_progress(f"PROCESSO COMPLETO! {len(clip_results)} clips gerados, ranqueados e otimizados.", "success")

        except Exception as e:
            emit_progress(f"Erro no processo completo: {str(e)}", "error")
            emit_status("error", {"message": str(e)})
            import traceback
            traceback.print_exc()
        finally:
            current_task["active"] = False

    if current_task["active"]:
        return jsonify({"error": "Ja existe um processamento em andamento"}), 409

    threading.Thread(target=task, daemon=True).start()
    return jsonify({"success": True, "message": "Processo completo iniciado"})


@app.route("/api/process/cancel", methods=["POST"])
def api_cancel():
    current_task["cancel"] = True
    return jsonify({"success": True, "message": "Cancelamento solicitado"})


# ─── WebSocket ───

@socketio.on("connect")
def handle_connect():
    emit("connected", {"message": "Conectado ao Furia Clips!"})


@socketio.on("disconnect")
def handle_disconnect():
    pass


# ─── Helpers ───

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


# ─── Main ───

if __name__ == "__main__":
    init_db()
    print("\n" + "=" * 50)
    print("   FURIA CLIPS - Corte. Ranqueie. Domine.")
    print("=" * 50)
    print(f"   Acesse: http://localhost:3001")
    print("=" * 50 + "\n")
    socketio.run(app, host="0.0.0.0", port=3001, debug=False, allow_unsafe_werkzeug=True)
