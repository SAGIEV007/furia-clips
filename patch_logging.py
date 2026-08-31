import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. api_upload_file INICIO
old = 'def api_upload_file():\n    if "file" not in request.files:'
new = 'def api_upload_file():\n    log_info(f"INICIO upload file={request.files.get(\'file\') and request.files[\'file\'].filename or \'vazio\'}", stage="upload")\n    if "file" not in request.files:'
content = content.replace(old, new, 1)

# 2. api_upload_file FIM
old = '    return jsonify({\n        "success": True,\n        "filename": filename,\n        "path": os.path.relpath(filepath, WORKSPACE_DIR),\n        "size": os.path.getsize(filepath),\n    })'
new = '    log_info(f"FIM upload file={file.filename} path={os.path.relpath(filepath, WORKSPACE_DIR)} size={os.path.getsize(filepath)}", stage="upload")\n    return jsonify({\n        "success": True,\n        "filename": filename,\n        "path": os.path.relpath(filepath, WORKSPACE_DIR),\n        "size": os.path.getsize(filepath),\n    })'
content = content.replace(old, new, 1)

# 3. api_transcribe INICIO
old = 'def api_transcribe():\n    data = request.get_json(silent=True) or {}\n    video_path = _resolve_media_input(data.get("video_path", ""))\n    log_info(f"[Transcrição] Requisição recebida para {video_path or \'caminho vazio\'}.", stage="transcription")\n    if not video_path:\n        log_error("[Transcrição] Caminho de vídeo não encontrado ou inválido.", stage="transcription")\n        return jsonify({"error": "Video não encontrado ou caminho inválido"}), 404\n    project_id = data.get("project_id")\n\n    if not os.path.exists(video_path):\n        return jsonify({"error": "Video nao encontrado"}), 404\n\n    legacy_job_id = f"legacy-{uuid.uuid4().hex}"\n\n    def task():\n        try:\n            check_current_task_cancel()'
new = 'def api_transcribe():\n    data = request.get_json(silent=True) or {}\n    video_path = _resolve_media_input(data.get("video_path", ""))\n    log_info(f"[Transcrição] Requisição recebida para {video_path or \'caminho vazio\'}.", stage="transcription")\n    if not video_path:\n        log_error("[Transcrição] Caminho de vídeo não encontrado ou inválido.", stage="transcription")\n        return jsonify({"error": "Video não encontrado ou caminho inválido"}), 404\n    project_id = data.get("project_id")\n\n    if not os.path.exists(video_path):\n        return jsonify({"error": "Video nao encontrado"}), 404\n\n    legacy_job_id = f"legacy-{uuid.uuid4().hex}"\n\n    def task():\n        log_info(f"INICIO transcribe video={os.path.basename(video_path)}", stage="transcription")\n        try:\n            check_current_task_cancel()'
content = content.replace(old, new, 1)

# 4. api_transcribe FIM
old = '        except Exception as e:\n            log_error(f"[Transcrição] Falha inesperada: {e}", stage="transcription", exc_info=True)\n            emit_progress(f"Erro na transcricao: {str(e)}", "error")\n            emit_status("error", {"message": str(e), "operation": "transcription"}, job_id=legacy_job_id)\n        finally:\n            _set_legacy_task("", active=False)\n\n    with processing_lock:\n        if current_task["active"]:\n            return jsonify({"error": "Ja existe um processamento em andamento"}), 409\n        _set_legacy_task("transcription", active=True, job_id=legacy_job_id)\n\n    threading.Thread(target=task, daemon=True).start()\n    return jsonify({"success": True, "message": "Transcricao iniciada", "job_id": legacy_job_id, "state": "running"})'
new = '        except Exception as e:\n            log_error(f"[Transcrição] Falha inesperada: {e}", stage="transcription", exc_info=True)\n            emit_progress(f"Erro na transcricao: {str(e)}", "error")\n            emit_status("error", {"message": str(e), "operation": "transcription"}, job_id=legacy_job_id)\n        finally:\n            log_info(f"FIM transcribe video={os.path.basename(video_path)}", stage="transcription")\n            _set_legacy_task("", active=False)\n\n    with processing_lock:\n        if current_task["active"]:\n            return jsonify({"error": "Ja existe um processamento em andamento"}), 409\n        _set_legacy_task("transcription", active=True, job_id=legacy_job_id)\n\n    threading.Thread(target=task, daemon=True).start()\n    return jsonify({"success": True, "message": "Transcricao iniciada", "job_id": legacy_job_id, "state": "running"})'
content = content.replace(old, new, 1)

# 5. api_source_import INICIO
old = '    def task():\n        try:\n            check_current_task_cancel()\n            emit_progress("[Fonte] Preparando download de URL pública...", "info")\n            result = download_public_video(\n                url,\n                destination,\n                max_height=max_height,\n                retries=settings.get("source_download_retries", 3),\n                cancel_check=check_current_task_cancel,\n                progress=lambda update: emit_progress(_format_source_import_progress(update), "info"),\n            )'
new = '    def task():\n        log_info(f"INICIO source_import url={str(data.get(\'url\', \'\'))[:80]}", stage="source_import")\n        try:\n            check_current_task_cancel()\n            emit_progress("[Fonte] Preparando download de URL pública...", "info")\n            result = download_public_video(\n                url,\n                destination,\n                max_height=max_height,\n                retries=settings.get("source_download_retries", 3),\n                cancel_check=check_current_task_cancel,\n                progress=lambda update: emit_progress(_format_source_import_progress(update), "info"),\n            )'
content = content.replace(old, new, 1)

# 6. api_source_import FIM
old = '        except Exception as exc:\n            log_error(f"[Fonte] Falha ao importar link: {exc}", stage="source_import", exc_info=True)\n            emit_progress(f"[Fonte] Falha ao importar link: {str(exc)}", "error")\n            emit_status("error", {"operation": "source_import", "message": str(exc)}, job_id=source_job_id)\n        finally:\n            _set_legacy_task("", active=False)\n\n    threading.Thread(target=task, daemon=True).start()'
new = '        except Exception as exc:\n            log_error(f"[Fonte] Falha ao importar link: {exc}", stage="source_import", exc_info=True)\n            emit_progress(f"[Fonte] Falha ao importar link: {str(exc)}", "error")\n            emit_status("error", {"operation": "source_import", "message": str(exc)}, job_id=source_job_id)\n        finally:\n            log_info("FIM source_import", stage="source_import")\n            _set_legacy_task("", active=False)\n\n    threading.Thread(target=task, daemon=True).start()'
content = content.replace(old, new, 1)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('patched')
