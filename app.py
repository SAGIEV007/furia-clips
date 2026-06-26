import os
import sys
import json
import uuid
import shutil
import threading
import subprocess
import platform
import requests
from datetime import datetime

# Load .env file for Gemini API key and other settings
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    # python-dotenv not installed — load .env manually
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(_env_path):
        with open(_env_path, "r") as _ef:
            for _line in _ef:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip())

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

    # Save Gemini key to .env for persistence across sessions
    gemini_key = data.get("gemini_api_key", "")
    if gemini_key:
        _save_key_to_env("GEMINI_API_KEY", gemini_key)

    return jsonify({"success": True})


def _save_key_to_env(key_name, key_value):
    """Save an API key to the .env file."""
    env_file = os.path.join(BASE_DIR, ".env")
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
    user_context = data.get("user_context", "")
    video_genre = data.get("video_genre", "")

    if not os.path.exists(video_path):
        return jsonify({"error": "Video nao encontrado"}), 404

    def task():
        current_task["active"] = True
        try:
            settings = get_all_settings()

            # Check AI status before starting
            ai_backend = settings.get("ai_backend", "gemini")
            ai_status = _check_ai_status(settings)
            emit_progress(f"[Modo] {ai_status['mode_label']}", "info")
            socketio.emit("ai_status", ai_status)

            # Context confirmation
            if user_context:
                emit_progress(f'[Contexto] Prompt do usuario: "{user_context[:100]}..."' if len(user_context) > 100 else f'[Contexto] Prompt do usuario: "{user_context}"', "info")
            else:
                emit_progress("[Contexto] Nenhum contexto definido. Cortes serao genericos.", "warning")

            # Step 1: Transcribe (with cache)
            emit_progress("=== ETAPA 1/5: Transcricao ===", "info")
            from modules.transcriber import Transcriber
            transcriber = Transcriber(
                model_name=settings.get("whisper_model", "small"),
                language=settings.get("language", "pt"),
            )
            transcription = transcriber.transcribe(video_path, emit_progress=emit_progress)
            emit_progress(f"[Whisper] Motor: {transcriber._engine}", "info")

            if project_id:
                save_transcription(
                    project_id, transcription["segments"], transcription["full_text"],
                    transcription["language"], settings.get("whisper_model", "small")
                )

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

            # Scene change detection
            try:
                from modules.video_cutter import VideoCutter as SceneDetector
                scene_det = SceneDetector()
                scene_changes = scene_det.detect_scenes(video_path, emit_progress=emit_progress)
            except Exception as e:
                emit_progress(f"Deteccao de cena indisponivel: {str(e)}", "warning")

            # Step 3: Intelligent clip selection
            emit_progress("=== ETAPA 3/5: Selecao Inteligente de Clips ===", "info")
            from modules.clip_selector import ClipSelector
            from modules.audio_analyzer import AudioAnalyzer

            analyzer = AudioAnalyzer()
            energy_profile = analyzer.analyze_energy(video_path, emit_progress=emit_progress)

            selector = ClipSelector(
                target_duration=settings.get("cut_duration", 45),
                max_clips=15,
                min_duration=20,
                max_duration=180,
            )
            top_clips = selector.select_clips(
                transcription,
                energy_profile=energy_profile,
                user_context=user_context,
                settings=settings,
                emit_progress=emit_progress,
                scene_changes=scene_changes,
                video_layout=video_layout,
            )

            selection_source = selector.get_selection_source()
            socketio.emit("selection_mode", {"source": selection_source})

            # Step 4: Rank and finalize scores
            emit_progress("=== ETAPA 4/5: Ranqueamento ===", "info")
            from modules.viral_ranker import ViralRanker
            ranker = ViralRanker(channel_context=settings.get("channel_context", ""))
            top_clips = ranker.rank_clips(top_clips)

            # Step 5: Cut clips (face tracking disabled for now)
            emit_progress("=== ETAPA 5/5: Cortando Clips ===", "info")
            from modules.video_cutter import VideoCutter
            cutter = VideoCutter(
                method="intelligent",
                target_duration=settings.get("cut_duration", 45),
            )

            # Face tracking disabled — focus on selection quality first
            face_positions_map = {}
            if video_layout == "debate":
                emit_progress("[Layout] Debate: preservando enquadramento original (sem crop).", "info")
            else:
                emit_progress("[Layout] Crop centralizado (face tracking desabilitado).", "info")

            project_name = os.path.splitext(os.path.basename(video_path))[0]
            output_dir = settings.get("output_dir", "") or ""
            results = cutter.batch_cut(
                video_path, top_clips, project_name,
                use_face_tracking=bool(face_positions_map),
                face_positions_map=face_positions_map,
                emit_progress=emit_progress,
                output_dir=output_dir if output_dir else None,
                video_layout=video_layout,
            )

            # Save to DB
            output_folder = ""
            if project_id:
                for i, res in enumerate(results):
                    clip_data = top_clips[i] if i < len(top_clips) else {}
                    save_clip(
                        project_id, res["path"], res["start"], res["end"],
                        res["duration"], clip_data.get("viral_score", 0),
                        clip_data.get("has_hook", False),
                        0,
                        res.get("text", "")
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
                    "rank": res.get("rank", i + 1),
                })

            emit_status("cut_complete", {
                "clips": clip_results,
                "selection_source": selection_source,
                "video_layout": video_layout,
                "output_folder": output_folder,
            })

            source_label = "IA Inteligente" if selection_source == "llm" else "NLP Basico"
            emit_progress(f"Corte completo! {len(results)} clips gerados via {source_label}.", "success")

        except ValueError as ve:
            friendly = _translate_error(str(ve))
            emit_progress(f"Erro: {friendly}", "error")
            emit_status("error", {"message": friendly})
        except Exception as e:
            friendly = _translate_error(str(e))
            emit_progress(f"Erro no corte: {friendly}", "error")
            emit_status("error", {"message": friendly, "technical": str(e)})
        finally:
            current_task["active"] = False

    if current_task["active"]:
        return jsonify({"error": ERROR_MESSAGES["processing_active"]}), 409

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
    user_context = data.get("user_context", "")
    video_genre = data.get("video_genre", "")

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

            # ── Step 2: Transcribe (with cache) ──
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

            # ── Step 3: Intelligent clip selection ──
            emit_progress("━━━ ETAPA 3/6: Selecao Inteligente de Clips ━━━", "info")
            from modules.clip_selector import ClipSelector
            from modules.audio_analyzer import AudioAnalyzer

            analyzer = AudioAnalyzer()
            energy_profile = analyzer.analyze_energy(working_video, emit_progress=emit_progress)

            selector = ClipSelector(
                target_duration=settings.get("cut_duration", 45),
                max_clips=15,
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

            # ── Step 4: Rank and cut ──
            emit_progress("━━━ ETAPA 4/6: Ranqueando e Cortando ━━━", "info")
            from modules.viral_ranker import ViralRanker
            from modules.video_cutter import VideoCutter

            ranker = ViralRanker(channel_context=settings.get("channel_context", ""))
            top_clips = ranker.rank_clips(top_clips)

            cutter = VideoCutter(
                method="intelligent",
                target_duration=settings.get("cut_duration", 45),
            )

            # Layout detection + Face tracking
            video_layout = "unknown"
            face_positions_map = {}
            try:
                from modules.face_tracker import FaceTracker
                tracker = FaceTracker()
                video_layout = tracker.detect_layout(
                    video_path, emit_progress=emit_progress,
                    video_genre=video_genre if video_genre else None
                )
                if video_layout != "debate":
                    all_faces = tracker.detect_faces_in_video(video_path, emit_progress=emit_progress)
                    if all_faces:
                        for i, clip in enumerate(top_clips):
                            positions = tracker.get_face_positions_for_segment(
                                all_faces, clip["start"], clip["end"]
                            )
                            if positions:
                                face_positions_map[i] = positions
                else:
                    emit_progress("[Layout] Debate: preservando enquadramento original.", "info")
            except Exception as e:
                emit_progress(f"Face tracking indisponivel: {str(e)}", "warning")

            output_dir = settings.get("output_dir", "") or ""
            results = cutter.batch_cut(
                video_path, top_clips, video_name,
                use_face_tracking=bool(face_positions_map),
                face_positions_map=face_positions_map,
                emit_progress=emit_progress,
                output_dir=output_dir if output_dir else None,
                video_layout=video_layout,
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
                    "title": clip_info.get("title", ""),
                    "source": clip_info.get("source", "nlp"),
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

# --- API: Ollama Status ---

@app.route("/api/ollama/status", methods=["GET"])
def api_ollama_status():
    settings = get_all_settings()
    status = _check_ai_status(settings)
    return jsonify(status)


# --- API: Open Folder ---

@app.route("/api/open_folder", methods=["POST"])
def api_open_folder():
    data = request.json
    folder_path = data.get("path", "")

    if not folder_path:
        folder_path = EXPORT_DIR

    if not os.path.isabs(folder_path):
        folder_path = os.path.join(WORKSPACE_DIR, folder_path)

    folder_path = os.path.normpath(folder_path)

    if not os.path.isdir(folder_path):
        return jsonify({"error": "Pasta nao encontrada"}), 404

    try:
        system = platform.system()
        if system == "Windows":
            os.startfile(folder_path)
        elif system == "Darwin":
            subprocess.Popen(["open", folder_path])
        else:
            subprocess.Popen(["xdg-open", folder_path])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e), "path": folder_path}), 500


@socketio.on("connect")
def handle_connect():
    emit("connected", {"message": "Conectado ao Furia Clips!"})
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
    """Check AI backend status (Gemini, Ollama, or NLP)."""
    ai_backend = settings.get("ai_backend", "gemini")

    if ai_backend == "gemini":
        api_key = settings.get("gemini_api_key", "")
        if api_key:
            try:
                resp = requests.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
                    timeout=5
                )
                if resp.status_code == 200:
                    return {
                        "connected": True,
                        "mode": "gemini",
                        "model": "gemini-2.5-flash",
                        "model_available": True,
                        "status": "connected",
                        "backend": "gemini",
                        "mode_label": "Gemini Flash (Online)",
                    }
            except Exception:
                pass
        return {
            "connected": False,
            "mode": "gemini_offline",
            "model": "gemini-2.5-flash",
            "model_available": False,
            "status": "no_key" if not api_key else "offline",
            "backend": "gemini",
            "mode_label": "Gemini (sem API key)" if not api_key else "Gemini (sem internet)",
        }

    # Ollama check
    ollama_url = settings.get("ollama_url", "http://localhost:11434")
    model = settings.get("ollama_model", "llama3.2:3b")

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
        "status": "offline",
        "backend": "ollama",
        "mode_label": "NLP Basico (sem IA)",
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

    # Startup AI check
    settings = get_all_settings()
    ai_status = _check_ai_status(settings)
    print("\n" + "=" * 50)
    print("   FURIA CLIPS - Corte. Ranqueie. Domine.")
    print("=" * 50)
    backend = ai_status.get("backend", "nlp")
    if backend == "gemini" and ai_status["connected"]:
        print(f"   [IA] Gemini Flash conectado!")
        print(f"   [IA] Modo: Selecao INTELIGENTE (online)")
    elif backend == "ollama" and ai_status["connected"]:
        print(f"   [IA] Ollama conectado! Modelo: {ai_status['model']}")
        print(f"   [IA] Modo: Selecao INTELIGENTE (offline)")
    else:
        print(f"   [AVISO] Nenhuma IA conectada.")
        print(f"   [AVISO] Modo: NLP basico (menos preciso)")
        print(f"   [DICA] Configure Gemini: https://aistudio.google.com/apikeys")
    print(f"   Acesse: http://localhost:3001")
    print("=" * 50 + "\n")
    socketio.run(app, host="0.0.0.0", port=3001, debug=False, allow_unsafe_werkzeug=True)
