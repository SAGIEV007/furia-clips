from pathlib import Path

path = Path("/home/ubuntu/furia-clips-rebuild/app.py")
source = path.read_text(encoding="utf-8")
start = source.index('@app.route("/api/process/cut", methods=["POST"])')
end = source.index('\n\n@app.route("/api/process/subtitles", methods=["POST"])', start)
route = source[start:end]

replacements = [
    (
        """    def task():
        try:
            check_current_task_cancel()
            settings = get_all_settings()
""",
        """    def task(ctx):
        try:
            ctx.update(stage="transcription", progress=5, message="Preparando transcrição e contexto")
            ctx.check_cancel()
            settings = get_all_settings()
""",
    ),
    ("cancel_check=check_current_task_cancel,", "cancel_check=ctx.check_cancel,"),
    (
        """            # Step 2: Layout detection + Scene detection
            emit_progress("=== ETAPA 2/5: Analise de Video ===", "info")
""",
        """            ctx.update(stage="video_analysis", progress=28, message="Analisando layout e cenas")
            ctx.check_cancel()

            # Step 2: Layout detection + Scene detection
            emit_progress("=== ETAPA 2/5: Analise de Video ===", "info")
""",
    ),
    (
        """            # Step 3: Intelligent clip selection
            emit_progress("=== ETAPA 3/5: Selecao Inteligente de Clips ===", "info")
""",
        """            ctx.update(stage="candidate_generation", progress=48, message="Gerando candidatos editoriais")
            ctx.check_cancel()

            # Step 3: Intelligent clip selection
            emit_progress("=== ETAPA 3/5: Selecao Inteligente de Clips ===", "info")
""",
    ),
    (
        """            # Step 4: Rank and finalize scores
            emit_progress("=== ETAPA 4/5: Ranqueamento ===", "info")
""",
        """            ctx.update(stage="ranking", progress=64, message=f"Ranqueando {len(top_clips)} candidatos")
            ctx.check_cancel()

            # Step 4: Rank and finalize scores
            emit_progress("=== ETAPA 4/5: Ranqueamento ===", "info")
""",
    ),
    (
        """            # Step 5: Cut clips with confidence-gated speaker framing
            emit_progress("=== ETAPA 5/5: Cortando Clips ===", "info")
""",
        """            ctx.update(stage="rendering", progress=76, message="Validando enquadramento e renderizando cortes")
            ctx.check_cancel()

            # Step 5: Cut clips with confidence-gated speaker framing
            emit_progress("=== ETAPA 5/5: Cortando Clips ===", "info")
""",
    ),
    (
        """            emit_progress(f"Corte completo! {len(results)} clips gerados via {source_label}.", "success")

        except OperationCancelled as exc:
            emit_progress(f"[Corte] Operação cancelada: {exc}", "warning")
            emit_status("cancelled", {"operation": "cut", "message": str(exc)})
        except ValueError as ve:
            friendly = _translate_error(str(ve))
            emit_progress(f"Erro: {friendly}", "error")
            emit_status("error", {"message": friendly})
        except Exception as e:
            friendly = _translate_error(str(e))
            emit_progress(f"Erro no corte: {friendly}", "error")
            emit_status("error", {"message": friendly, "technical": str(e)})
        finally:
            _set_legacy_task("", active=False)

    with processing_lock:
        if current_task["active"]:
            return jsonify({"error": ERROR_MESSAGES["processing_active"]}), 409
        _set_legacy_task("cut", active=True)

    threading.Thread(target=task, daemon=True).start()
    return jsonify({"success": True, "message": "Corte de shorts iniciado"})
""",
        """            emit_progress(f"Corte completo! {len(results)} clips gerados via {source_label}.", "success")
            return {
                "artifacts": [{
                    "type": "clips",
                    "project_id": active_project_id,
                    "count": len(clip_results),
                    "output_folder": output_folder,
                }]
            }

        except JobCancelled as exc:
            emit_progress(f"[Corte] Operação cancelada: {exc}", "warning")
            emit_status("cancelled", {"operation": "cut", "message": str(exc)})
            raise
        except OperationCancelled as exc:
            emit_progress(f"[Corte] Operação cancelada: {exc}", "warning")
            emit_status("cancelled", {"operation": "cut", "message": str(exc)})
            raise JobCancelled(str(exc)) from exc
        except ValueError as ve:
            friendly = _translate_error(str(ve))
            emit_progress(f"Erro: {friendly}", "error")
            emit_status("error", {"message": friendly})
            raise
        except Exception as e:
            friendly = _translate_error(str(e))
            emit_progress(f"Erro no corte: {friendly}", "error")
            emit_status("error", {"message": friendly, "technical": str(e)})
            raise
        finally:
            _set_legacy_task("", active=False)

    with processing_lock:
        if current_task["active"]:
            return jsonify({"error": ERROR_MESSAGES["processing_active"]}), 409
        _set_legacy_task("cut", active=True)
        job = job_manager.submit("cut_shorts", task, project_id=project_id)
        current_task["job_id"] = job["id"]

    return jsonify({
        "success": True,
        "message": "Corte de shorts iniciado",
        "job_id": job["id"],
        "state": job["state"],
    })
""",
    ),
]

for old, new in replacements:
    if old not in route:
        raise SystemExit(f"Bloco esperado não encontrado: {old[:80]!r}")
    route = route.replace(old, new, 1)

path.write_text(source[:start] + route + source[end:], encoding="utf-8")
print("Rota de corte migrada para JobManager.")
