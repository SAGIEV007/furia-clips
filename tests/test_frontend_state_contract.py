from pathlib import Path


APP_JS = Path(__file__).resolve().parents[1] / "static" / "js" / "app.js"


def test_video_change_resets_review_workspace_state_and_hud():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function resetReviewWorkspaceForVideoChange()" in source
    assert "state.clips = [];" in source
    assert 'state.lastReviewAction = null;' in source
    assert 'if (resultsSection) resultsSection.style.display = "none";' in source
    assert 'if (resultsGrid) resultsGrid.innerHTML = "";' in source
    assert 'if (transcriptSearchBar) transcriptSearchBar.style.display = "none";' in source
    assert 'if (candidateNotice) {' in source
    assert 'candidateNotice.hidden = true;' in source
    assert 'state.transcriptArchive = null;' in source
    assert 'if (archiveList) {' in source
    assert 'archiveList.hidden = true;' in source
    assert 'if (changedVideo) {\n        resetReviewWorkspaceForVideoChange();' in source
    assert 'function deselectVideo() {\n    const keepPendingTranscript = state.manualTranscriptVideo === "pending-source";\n    resetReviewWorkspaceForVideoChange();' in source


def test_persisted_gemini_key_is_explained_without_exposing_secret():
    source = APP_JS.read_text(encoding="utf-8")

    assert "Gemini configurado nesta instalação; o valor permanece oculto. Deixe o campo vazio para preservar." in source
    assert 'geminiInput.placeholder = configured' in source
    assert 'Chave já configurada; deixe vazio para preservar' in source
    assert 'Uma chave já está salva. Digite outra somente para substituí-la.' in source


def test_visual_evidence_review_flag_reaches_contextual_hook_card():
    source = APP_JS.read_text(encoding="utf-8")

    assert "reviewFlags.visual_evidence_review_required" in source
    assert "confirmar gráfico, pesquisa ou imagem mencionada" in source
    assert "hook.visual_review_reason ||" in source


def test_review_card_exposes_speaker_review_reason_to_editor():
    source = APP_JS.read_text(encoding="utf-8")

    assert "const speakerReviewRequired = Boolean(" in source
    assert "Locutor/ponte para confirmar:" in source
    assert "speaker_review_reason" in source


def test_context_analysis_reset_clears_dossier_at_single_workspace_boundary():
    source = APP_JS.read_text(encoding="utf-8")
    reset_start = source.find("function resetReviewWorkspaceForVideoChange()")
    reset_end = source.find("function deselectVideo()", reset_start)
    block = source[reset_start:reset_end]

    assert "state.editorialContext = null;" in block
    assert 'state.contextAnalysisJobId = "";' in block
    assert 'state.contextAnalysisSourcePath = "";' in block
    assert "state.contextAnalysisController?.abort();" in block
    assert 'contextResult.hidden = true;' in block
    assert "renderEditorialAudit(null);" in block


def test_context_analysis_tracks_source_identity_and_clears_on_change():
    source = APP_JS.read_text(encoding="utf-8")

    assert 'contextAnalysisSourcePath: ""' in source
    assert "state.contextAnalysisSourcePath = sourcePath;" in source
    assert "state.contextAnalysisSourcePath = selectedVideoPathForRequest();" in source
    assert 'state.contextAnalysisSourcePath = "";' in source


def test_transcript_archive_failure_is_friendly_and_logged():
    source = APP_JS.read_text(encoding="utf-8")

    archive_start = source.find("async function loadTranscriptArchive()")
    archive_end = source.find("async function requestEditorialBackup", archive_start)
    block = source[archive_start:archive_end]
    assert "Arquivo de transcrições indisponível agora. Atualize o painel" in block
    assert "addConsoleLog(`[Arquivo de transcrições] Falha técnica:" in block
    assert "${error.message}" not in block


def test_display_results_clears_last_review_action_for_new_clip_queue():
    source = APP_JS.read_text(encoding="utf-8")

    display_start = source.find("function displayResults(clips, videoLayout = null)")
    display_end = source.find("function reviewStatusOf", display_start)
    block = source[display_start:display_end]
    assert "state.lastReviewAction = null;" in block
    assert "state.clips = Array.isArray(clips) ? clips : [];" in block


def test_context_recovery_is_presented_as_reviewable_opening():
    source = APP_JS.read_text(encoding="utf-8")

    assert "contextRecoveryApplied" in source
    assert "Abertura ampliada para contexto:" in source
    assert "confirme se o antecedente realmente explica o hook" in source
    assert "clip-review-risk" in source[source.find("Abertura ampliada para contexto:") - 180:source.find("Abertura ampliada para contexto:") + 260]


def test_progress_events_are_scoped_to_the_active_job():
    source = APP_JS.read_text(encoding="utf-8")
    progress_start = source.find("function isCurrentProgressEvent(data = {})")
    progress_end = source.find('// ─── Status Handlers ───', progress_start)
    block = source[progress_start:progress_end]

    assert "function isCurrentProgressEvent(data = {})" in block
    assert 'const eventJobId = String(data?.job_id || "");' in block
    assert 'if (!eventJobId) return !activeJobId;' in block
    assert "eventJobId === String(state.sourceImportJobId)" in block
    assert "eventJobId === activeJobId" in block
    assert 'if (!isCurrentProgressEvent(data)) return;' in block


def test_progress_bar_preserves_active_job_stage_message():
    source = APP_JS.read_text(encoding="utf-8")

    assert "const activeJob = state.activeJob;" in source
    assert 'activeStates = ["queued", "running", "cancel_requested"]' in source
    assert 'activeJob.message || activeJob.stage || "Processando"' in source
    assert 'cancelRequested: activeJob?.state === "cancel_requested"' in source


def test_operation_dashboard_uses_editorial_job_state_labels():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function operationJobStateLabel(state = \"queued\")" in source
    assert 'queued: "Na fila"' in source
    assert 'running: "Em andamento"' in source
    assert 'cancel_requested: "Parada solicitada"' in source
    assert 'failed: "Falhou · atenção necessária"' in source
    assert 'data-state="${escapeHtml(stateCode)}"' in source


def test_transcript_review_reason_is_specific_to_coverage_problem():
    source = APP_JS.read_text(encoding="utf-8")

    assert "const transcriptionReviewReasons = {" in source
    assert 'mismatch_suspected: "a transcrição pode pertencer a outra fonte; confirme identidade e trecho no vídeo"' in source
    assert 'empty: "a transcrição não tem segmentos utilizáveis; confirme o trecho diretamente no vídeo"' in source
    assert "transcriptionReviewReasons[transcriptionCoverageStatus]" in source


def test_transcript_provenance_uses_editorial_coverage_labels():
    source = APP_JS.read_text(encoding="utf-8")

    assert 'complete: "cobertura integral"' in source
    assert 'covered: "cobertura integral"' in source
    assert 'partial: "cobertura parcial · revisar"' in source
    assert 'mismatch_suspected: "fonte possivelmente incompatível · revisar"' in source
    assert 'unknown: "cobertura não validada · revisar"' in source
    assert "provenanceCoverageLabels[provenanceCoverageCode]" in source


def test_stale_recovered_job_message_is_editorial_and_not_technical():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function operationJobMessage(job = {})" in source
    assert 'String(job.stage || "") === "stale_recovered"' in source
    assert "nenhum novo corte foi executado" in source
    assert "function operationJobStateLabel(state = \"queued\")" in source
    assert "operationJobMessage(job)" in source


def test_cancel_request_uses_recovered_active_job_id():
    source = APP_JS.read_text(encoding="utf-8")
    cancel_start = source.find("async function requestCancelOperation()")
    cancel_end = source.find('document.getElementById("btnCancelOperation")?.addEventListener', cancel_start)
    block = source[cancel_start:cancel_end]

    assert 'state.activeJob && ["queued", "running", "cancel_requested"].includes(state.activeJob.state)' in block
    assert "const jobId =" in block
    assert 'body: JSON.stringify(jobId ? { job_id: jobId } : {})' in block
    assert "state.activeJob?.id === jobId" in block


def test_legacy_recovery_does_not_replace_active_persistent_job():
    source = APP_JS.read_text(encoding="utf-8")
    recovery_start = source.find("async function recoverLegacyOperation()")
    recovery_end = source.find("async function loadOperationDashboard", recovery_start)
    block = source[recovery_start:recovery_end]

    assert "persistentJobAlreadyActive" in block
    assert 'existingJobId.startsWith("legacy-")' in block
    assert "existingJobId !== recoveredJobId" in block
    assert "a recuperação legada não substituirá sua HUD" in block
    assert "return;" in block


def test_legacy_recovery_closes_stale_hud_when_backend_is_inactive():
    source = APP_JS.read_text(encoding="utf-8")
    recovery_start = source.find("async function recoverLegacyOperation()")
    recovery_end = source.find("async function loadOperationDashboard", recovery_start)
    block = source[recovery_start:recovery_end]

    assert "if (!payload.active)" in block
    assert 'activeJobId.startsWith("legacy-")' in block
    assert "legacyOperations.has(activeJobStage)" in block
    assert "state.activeJob = null;" in block
    assert "hideProgressBar();" in block
    assert "servidor já encerrou a operação" in block


def test_restored_feedback_refreshes_visible_cards_without_rerendering_source():
    source = APP_JS.read_text(encoding="utf-8")
    refresh_start = source.find("async function refreshVisibleReviewState()")
    refresh_end = source.find("async function loadProjectLibrary", refresh_start)
    refresh_block = source[refresh_start:refresh_end]

    assert "currentProjectId" in source
    assert "fetch(`/api/projects/${projectId}`)" in refresh_block
    assert "persistedById" in refresh_block
    assert "persistedByKey" in refresh_block
    assert "renderReviewCommandCenter();" in refresh_block
    assert "renderResultsGrid();" in refresh_block
    assert "await refreshVisibleReviewState();" in source
    assert "await loadProjectLibrary();" in source
    assert "await loadEditorialLearning();" in source
    assert "await loadDailyEditorialGoal();" in source
    assert "await loadEditorialData();" in source
    assert "state.currentProjectId = null;" in source
    assert "decisão(ões) local(is) mais nova(s)" in source
    assert "sem correspondência" in source
    assert "invalid || unmatched" in source


def test_repository_sync_explains_semantically_invalid_feedback_snapshot():
    source = APP_JS.read_text(encoding="utf-8")
    status_start = source.find("function renderRepositorySyncState(payload)")
    status_end = source.find("async function checkRepositorySync", status_start)
    block = source[status_start:status_end]

    assert "feedback_snapshot_invalid_records" in block
    assert "registro(s) precisam ser revisados" in block
    assert "snapshot inválido; revisão necessária" in block


def test_review_feedback_refreshes_daily_goal_and_editorial_integrity_hud():
    source = APP_JS.read_text(encoding="utf-8")
    review_start = source.find("async function setClipReview(index, action)")
    review_end = source.find("// --- Transcript Toggle ---", review_start)
    block = source[review_start:review_end]

    assert "loadEditorialLearning();" in block
    assert "loadDailyEditorialGoal();" in block
    assert "loadEditorialData();" in block
    assert "state.lastReviewAction = { action" in block
    assert "if (clip.clip_id) await refreshVisibleReviewState();" in block
    assert "Clip aprovado" in block
    assert "Clip rejeitado" in block


def test_transcription_completion_preserves_source_identity_after_video_change():
    source = APP_JS.read_text(encoding="utf-8")
    status_start = source.find('case "transcribe_complete"')
    status_end = source.find('case "source_import_complete"', status_start)
    block = source[status_start:status_end]

    assert 'transcriptionJobVideoPath: ""' in source
    assert 'state.transcriptionJobVideoPath = selectedVideoPathForRequest();' in source
    assert 'data.data?.source_video_path || state.transcriptionJobVideoPath' in block
    assert 'mediaPathsMatch(completedSourcePath, selectedSourcePath)' in block
    assert "não foi aplicado ao vídeo selecionado" in block
    assert 'state.transcriptionJobVideoPath = "";' in block

    import inspect
    import app as app_module
    backend_source = inspect.getsource(app_module.api_transcribe)
    assert 'result["source_video_path"]' in backend_source
    assert 'emit_status("transcribe_complete", result, job_id=legacy_job_id)' in backend_source


def test_context_dossier_is_sent_only_for_matching_selected_source():
    source = APP_JS.read_text(encoding="utf-8")
    cut_start = source.find("async function startSmartCut()")
    cut_end = source.find('document.getElementById("actionCut")', cut_start)
    block = source[cut_start:cut_end]

    assert "const currentVideoPath = selectedVideoPathForRequest();" in block
    assert "state.contextAnalysisSourcePath === currentVideoPath" in block
    assert 'editorial_context_source_path: boundEditorialContext ? currentVideoPath : ""' in block
    assert "...(boundEditorialContext ? { editorial_context: boundEditorialContext } : {})," in block

    import inspect
    import app as app_module
    backend_source = inspect.getsource(app_module.api_cut_shorts)
    assert "prefetched_context_matches" in backend_source
    assert "os.path.realpath(prefetched_context_path) == os.path.realpath(video_path)" in backend_source
    assert "Dossiê pré-analisado para esta fonte reutilizado" in backend_source

    complete_start = source.find('document.getElementById("actionComplete")')
    complete_end = source.find("// ─── Subtitle Modal", complete_start)
    complete_block = source[complete_start:complete_end]
    assert 'fetch("/api/process/complete"' in complete_block
    assert 'editorial_context_source_path: boundEditorialContext ? currentVideoPath : ""' in complete_block
    assert "...(boundEditorialContext ? { editorial_context: boundEditorialContext } : {})," in complete_block
    assert "prefetched_context_matches" in inspect.getsource(app_module.api_process_complete)


def test_source_import_response_rebinds_hud_to_new_job_and_message():
    import inspect
    import app as app_module

    source = APP_JS.read_text(encoding="utf-8")
    import_start = source.find("async function importSource(autoTranscribe = false)")
    import_end = source.find('document.getElementById("btnDownloadSource")', import_start)
    block = source[import_start:import_end]

    assert 'state.sourceImportJobId = String(data.job_id || "");' in block
    assert 'stage: "source_import"' in block
    assert 'state: data.state || "running"' in block
    assert 'showProcessingControls(`[Job ${state.sourceImportJobId.slice(0, 8)}] ${sourceMessage}`);' in block
    backend_source = inspect.getsource(app_module.api_source_import)
    assert '"state": "running"' in backend_source


def test_registered_operation_preserves_editorial_message_in_active_job():
    source = APP_JS.read_text(encoding="utf-8")

    assert 'stage: started.operation || "legacy"' in source
    assert "message," in source
    assert 'activeJob.message || activeJob.stage || "Processando"' in source


def test_cancel_request_marks_active_job_as_cancel_requested_immediately():
    source = APP_JS.read_text(encoding="utf-8")

    assert 'state.activeJob = { ...state.activeJob, state: data.state || "cancel_requested" };' in source
    assert 'Parada solicitada; aguardando encerramento seguro' in source
    assert 'cancelRequested: true' in source


def test_legacy_operation_recovery_preserves_active_persistent_job():
    source = APP_JS.read_text(encoding="utf-8")
    recovery_start = source.find("async function recoverLegacyOperation()")
    recovery_end = source.find("async function loadOperationDashboard()", recovery_start)
    block = source[recovery_start:recovery_end]

    assert "persistentJobAlreadyActive" in block
    assert 'existingJobId.startsWith("legacy-")' in block
    assert 'state.activeJob = {' in block
    assert "a recuperação legada não substituirá sua HUD" in block


def test_legacy_operation_recovery_restores_any_active_processing_state():
    source = APP_JS.read_text(encoding="utf-8")
    recovery_start = source.find("async function recoverLegacyOperation()")
    recovery_end = source.find("async function loadOperationDashboard()", recovery_start)
    block = source[recovery_start:recovery_end]

    assert 'fetch("/api/process/status")' in block
    assert 'if (payload.active && payload.job_id)' in block
    assert 'state.activeJob = {' in block
    assert 'state.sourceImportJobId = String(payload.job_id);' in block
    assert 'silence: "Remoção de silêncio ainda em andamento;' in block
    assert 'transcription: "Transcrição ainda em andamento;' in block
    assert 'subtitles: "Geração de legendas ainda em andamento;' in block
    assert 'thumbnail: "Geração de thumbnail ainda em andamento;' in block


def test_terminal_legacy_status_settles_active_job_before_hiding_hud():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function settleLegacyStatusJob(data = {})" in source
    assert "state.activeJob = {" in source
    assert "state: terminalState" in source
    assert "settleLegacyStatusJob(data);" in source
    assert "const jobStillActive = [\"queued\", \"running\", \"cancel_requested\"].includes(activeJobState)" in source


def test_legacy_processing_flows_register_started_jobs_in_shared_hud():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function registerStartedOperation(started, message = \"Operação adicionada à fila persistente.\")" in source
    assert "Remoção de silêncio em andamento." in source
    assert "Transcrição em andamento." in source
    assert 'fetch("/api/process/silence"' in source
    assert 'fetch("/api/process/transcribe"' in source
    assert "registerStartedOperation(data, \"Transcrição em andamento.\");" in source
    assert 'fetch("/api/process/subtitles"' in source
    assert 'registerStartedOperation(started, "Geração de legendas em andamento.");' in source
    assert 'fetch("/api/process/thumbnail"' in source
    assert 'registerStartedOperation(started, "Geração de thumbnail em andamento.");' in source


def test_cut_flows_only_send_transcript_bound_to_selected_video():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function transcriptPayloadForSelectedVideo()" in source
    assert "if (!linkedPath || linkedPath === \"pending-source\" || !mediaPathsMatch(linkedPath, selectedPath)) return null;" in source
    assert "const boundTranscript = transcriptPayloadForSelectedVideo();" in source
    assert "...(boundTranscript ? {" in source
    assert "transcript_segments: boundTranscript.segments" in source


def test_transcript_archive_folder_action_is_explicit_and_non_destructive():
    source = APP_JS.read_text(encoding="utf-8")

    assert "data-open-transcript-folder" in source
    assert "Pasta persistente aberta. Nenhum arquivo foi aplicado ao vídeo atual." in source
    assert 'fetch("/api/editorial/transcripts/open"' in source
    assert 'body: JSON.stringify({ relative_dir: relativeDir })' in source


def test_transcript_archive_list_shows_conservative_temporal_coverage():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function transcriptArchiveCoverage(item = {})" in source
    assert "duração da fonte não informada · revisar" in source
    assert "sem cobertura temporal utilizável · revisar" in source
    assert "último timestamp antes do fim da fonte · revisar" in source
    assert "timestamps cobrem quase toda a duração informada · confirmar no vídeo" in source
    assert "transcript-archive-coverage" in source


def test_transcript_archive_list_shows_source_compatibility_without_auto_apply():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function transcriptArchiveCompatibility(item = {})" in source
    assert "fonte atual registrada" in source
    assert "mesmo nome-base · confirmar arquivo" in source
    assert "fonte diferente da seleção · não aplicar automaticamente" in source
    assert "transcript-archive-compatibility" in source


def test_transcript_archive_list_does_not_present_structural_quality_as_semantic_validation():
    source = APP_JS.read_text(encoding="utf-8")

    assert "qualityLabels = {" in source
    assert "estrutura timestampada válida" in source
    assert "semântica não validada" in source
    assert "quality.semantic_accuracy_verified" in source
    assert "valid_segment_count" in source
    assert "const archiveClass = quality.quality === \"structurally_ok\" && quality.semantic_accuracy_verified" in source


def test_source_import_notice_does_not_overwrite_current_transcript_status():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function showSourceOnlyStatus(message, type = \"\")" in source
    assert "showSourceOnlyStatus(\"Fonte importada; a seleção atual foi preservada." in source
    assert "const transcriptStatus = document.getElementById(\"transcriptStatus\");" in source
    assert "function showSourceStatus(message, type = \"\")" in source


def test_transcript_status_explains_source_link_and_archive_presence():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function hydrateTranscriptEditor(transcription, archive = null)" in source
    assert "const linkedPath = String(state.manualTranscriptVideo || \"\").trim();" in source
    assert "Aguardando vínculo com um vídeo selecionado." in source
    assert "Fonte da transcrição não identificada; revise antes do corte." in source
    assert "Arquivo persistente ainda não identificado." in source
    assert "Transcrição pronta:" in source


def test_source_import_identity_is_cleared_on_terminal_failure_or_recovery():
    source = APP_JS.read_text(encoding="utf-8")

    assert "state.sourceImportInitialVideoPath = \"\";" in source
    assert "if (!payload.active)" in source
    assert "if (state.sourceImportActive)" in source
    assert "state.sourceImportJobId = \"\";" in source
    assert "showSourceStatus(error.message, \"error\");" in source


def test_source_import_completion_preserves_selection_changed_during_download():
    source = APP_JS.read_text(encoding="utf-8")

    assert "sourceImportInitialVideoPath: \"\"" in source
    assert "const preserveCurrentSelection = Boolean(" in source
    assert "!mediaPathsMatch(state.selectedVideo, state.sourceImportInitialVideoPath)" in source
    assert "if (preserveCurrentSelection) return;" in source
    assert "seleção atual foi preservada" in source


def test_terminal_old_job_cannot_take_over_active_source_import_hud():
    source = APP_JS.read_text(encoding="utf-8")

    assert "const sourceImportOwnsHud = Boolean(" in source
    assert "state.sourceImportActive" in source
    assert 'String(state.sourceImportJobId) !== String(job?.id || "")' in source
    assert "if (sourceImportOwnsHud) return;" in source


def test_new_operation_resets_terminal_guards_without_clearing_history():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function prepareNewOperationHud()" in source
    assert "state.terminalEventKeys = {};" in source
    assert "state.progressSuppressed = false;" in source
    assert "prepareNewOperationHud();" in source
    assert "state.operationJobs" in source


def test_terminal_events_are_idempotent_per_job():
    source = APP_JS.read_text(encoding="utf-8")

    assert "terminalEventKeys: {}" in source
    assert "function terminalEventWasHandled(data = {})" in source
    assert "if (!eventJobId || !terminalStatuses.has(status)) return false;" in source
    assert "const key = `${eventJobId}:${status}`;" in source
    assert "if (state.terminalEventKeys[key]) return true;" in source
    assert "if (!isCurrentJobEvent(data) || terminalEventWasHandled(data)) return;" in source


def test_status_without_job_id_cannot_hide_active_persistent_job():
    source = APP_JS.read_text(encoding="utf-8")

    assert "const activeStates = [\"queued\", \"running\", \"cancel_requested\"];" in source
    assert 'if (!eventJobId && activeJobId && activeStates.includes(String(state.activeJob?.state || ""))) return false;' in source
    assert "return eventJobId === activeJobId;" in source


def test_socket_reconnect_rehydrates_persisted_jobs():
    source = APP_JS.read_text(encoding="utf-8")

    assert 'const recovered = socketRecoveryNotice;' in source
    assert "if (recovered) recoverActiveJobs();" in source
    assert "async function recoverActiveJobs()" in source
    assert "await loadOperationDashboard();" in source


def test_context_analysis_abort_controller_discards_obsolete_requests():
    source = APP_JS.read_text(encoding="utf-8")

    assert "contextAnalysisController: null" in source
    assert "state.contextAnalysisController?.abort();" in source
    assert "const controller = new AbortController();" in source
    assert "signal: controller.signal" in source
    assert "error?.name === \"AbortError\"" in source
    assert "state.contextAnalysisController = null;" in source


def test_progress_hud_ignores_late_messages_after_terminal_hide():
    source = APP_JS.read_text(encoding="utf-8")

    assert "progressHideTimer: null" in source
    assert "progressSuppressed: false" in source
    assert "if (!state.progressSuppressed || jobStillActive) showProgressBar();" in source
    assert "window.clearTimeout(state.progressHideTimer);" in source
    assert "state.progressHideTimer = window.setTimeout(() =>" in source
    assert "if (jobStillActive)" in source


def test_legacy_provenance_unknown_enters_review_queue_without_overriding_explicit_decision():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function reviewStatusOf(clip)" in source
    assert "clip?.review_provenance?.transcript_coverage_status" in source
    assert 'return "needs_review";' in source
    assert 'if (explicitStatus) return explicitStatus;' in source


def test_transcript_coverage_status_can_force_review_for_legacy_clips():
    source = APP_JS.read_text(encoding="utf-8")

    assert 'const transcriptionCoverageNeedsReview = ["partial", "mismatch_suspected", "empty", "unknown"].includes(transcriptionCoverageStatus);' in source
    assert "transcriptionCoverageNeedsReview" in source
    assert "cobertura parcial da transcrição; confirme o trecho no vídeo" in source
    assert "clip.review_provenance?.transcript_coverage_status" in source


def test_framing_card_does_not_call_review_required_reframe_safe():
    source = APP_JS.read_text(encoding="utf-8")

    assert "const framingReviewRequired = Boolean(" in source
    assert 'label: "Reframe 9:16 planejado · revisar"' in source
    assert 'label: "Reframe 9:16 seguro"' in source
    assert "reenquadramento depende de confirmação visual" in source


def test_review_queue_actions_use_stable_clip_index_after_sorting():
    source = APP_JS.read_text(encoding="utf-8")

    assert "const originalIndex = state.clips.indexOf(clip);" in source
    assert "setClipReview(${originalIndex}" in source
    assert "previewClipBoundary(${originalIndex})" in source
    assert "generateClipHeadline(${originalIndex})" in source


def test_failed_and_cancelled_jobs_update_workflow_and_console():
    source = APP_JS.read_text(encoding="utf-8")

    assert 'updateWorkspaceWorkflow("source", "Atenção necessária")' in source
    assert "const failureMessage = String(job.error || job.message || \"O job falhou\")" in source
    assert "Operação cancelada com segurança" in source
    assert "hideProcessingControls();" in source


def test_terminal_error_event_without_payload_keeps_a_safe_fallback_message():
    source = APP_JS.read_text(encoding="utf-8")
    error_start = source.find('case "error":')
    error_end = source.find('break;', error_start)
    block = source[error_start:error_end]
    assert 'showToast(data.data?.message || "Erro no processamento", "error");' in block


def test_review_actions_disable_while_feedback_is_saving():
    source = APP_JS.read_text(encoding="utf-8")

    assert "clip.review_busy" in source
    assert "Salvando…" in source
    assert "${reviewBusy ? 'disabled' : ''}" in source
    assert "finally {\n        clip.review_busy = false;" in source


def test_url_download_only_reuses_transcript_marked_for_next_source():
    source = APP_JS.read_text(encoding="utf-8")

    assert "transcriptIsPendingForNextSource" in source
    assert "autoTranscribe && transcriptIsPendingForNextSource && state.manualTranscript?.segments?.length" in source


def test_context_websocket_event_requires_current_job_id():
    source = APP_JS.read_text(encoding="utf-8")

    assert "contextAnalysisJobId" in source
    assert "eventJobId !== String(state.contextAnalysisJobId || \"\")" in source
    assert "state.contextAnalysisJobId = \"\"" in source


def test_deselect_video_clears_editorial_search_generation():
    source = APP_JS.read_text(encoding="utf-8")

    reset_start = source.find("function resetReviewWorkspaceForVideoChange()")
    reset_end = source.find("function deselectVideo()", reset_start)
    reset_block = source[reset_start:reset_end]
    assert "resetCampaignSearchPanel();" in reset_block

    deselect_start = source.find("function deselectVideo()")
    deselect_end = source.find("function ", deselect_start + 1)
    block = source[deselect_start:deselect_end if deselect_end >= 0 else None]
    assert "resetReviewWorkspaceForVideoChange();" in block


def test_results_mode_badge_uses_explicit_backend_labels():
    source = APP_JS.read_text(encoding="utf-8")
    badge_start = source.find("function updateResultsModeBadge(source)")
    badge_end = source.find("function renderCandidateVolumeNotice", badge_start)
    block = source[badge_start:badge_end]
    assert 'badge.textContent = "Gemini Flash";' in block
    assert 'badge.textContent = "Ollama";' in block
    assert 'badge.textContent = "NLP local";' in block
    assert "NLP Basico" not in block


def test_clip_card_exposes_sanitized_transcript_provenance():
    source = APP_JS.read_text(encoding="utf-8")

    assert "review_provenance" in source
    assert "transcriptSourceLabels" in source
    assert '"gemini": "Gemini Flash"' in source
    assert '"llm": "Ollama"' in source
    assert '"nlp": "NLP local"' in source
    assert "transcript_archive_present" in source
    assert "Base usada no corte:" in source
    assert "source_video" not in source[source.find("const provenanceMarkup"):source.find("const provenanceMarkup") + 900]


def test_partial_transcript_coverage_explains_late_start():
    source = APP_JS.read_text(encoding="utf-8")

    assert "first_ratio" in source
    assert "first_timestamp" in source
    assert "começa em" in source
    assert "cortes ficarão limitados a esse trecho" in source


def test_review_results_keep_safe_source_identity():
    source = APP_JS.read_text(encoding="utf-8")

    assert 'resultSourceIdentity: ""' in source
    assert 'state.resultSourceIdentity = String(data.data.source_identity || "").trim();' in source
    assert 'state.resultSourceIdentity = "";' in source
    assert "Fonte: ${state.resultSourceIdentity}" in source


def test_status_and_selection_events_are_bound_to_active_job():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function isCurrentJobEvent(data = {})" in source
    assert "data?.job_id || data?.data?.job_id" in source
    assert "activeJob?.id" in source
    assert "if (!isCurrentJobEvent(data)) return;" in source


def test_stale_concurrent_job_updates_do_not_override_active_hud():
    source = APP_JS.read_text(encoding="utf-8")

    assert "staleConcurrentJob" in source
    assert "currentJob.id !== job.id" in source
    assert "if (staleConcurrentJob)" in source
    assert "state.activeJob = job" in source


def test_cancel_requested_job_disables_repeat_cancel_action():
    source = APP_JS.read_text(encoding="utf-8")

    assert "cancelRequested" in source
    assert "Parada solicitada; aguardando encerramento seguro" in source
    assert "job.state === \"cancel_requested\"" in source


def test_context_analysis_discards_stale_source_results():
    source = APP_JS.read_text(encoding="utf-8")

    assert "contextAnalysisToken" in source
    assert "requestToken !== state.contextAnalysisToken" in source
    assert "selectedVideoPathForRequest() !== sourcePath" in source
    assert "if (requestToken === state.contextAnalysisToken)" in source


def test_campaign_search_increments_token_for_each_request():
    source = APP_JS.read_text(encoding="utf-8")
    search_start = source.find("async function searchCampaignHubEditorial()")
    search_end = source.find('document.getElementById("btnCampaignSearch")?.addEventListener', search_start)
    block = source[search_start:search_end]

    assert "const searchToken = ++state.campaignSearchToken;" in block
    assert "if (searchToken !== state.campaignSearchToken) return;" in block


def test_campaign_search_exposes_garimpo_dossier_and_platform_scope():
    source = APP_JS.read_text(encoding="utf-8")
    template = (APP_JS.parents[2] / "templates" / "index.html").read_text(encoding="utf-8")
    search_start = source.find("async function searchCampaignHubEditorial()")
    search_end = source.find('document.getElementById("btnCampaignSearch")?.addEventListener', search_start)
    block = source[search_start:search_end]

    assert 'id="campaignSearchPlatform"' in template
    assert 'value="youtube">YouTube / longform' in template
    assert "platform: platform?.value || \"\"," in block
    assert "function renderCampaignSearchMoments(moments)" in source
    assert "campaign-search-copy" in source
    assert "item.source_url || item.url" in source
    assert "item.needs_context" in source


def test_campaign_hub_account_persists_through_settings():
    source = APP_JS.read_text(encoding="utf-8")

    assert 'if (s.campaign_hub_account) document.getElementById("settingCampaignHubAccount").value = s.campaign_hub_account;' in source
    assert 'campaign_hub_account: document.getElementById("settingCampaignHubAccount").value' in source


def test_ai_backend_selector_matches_automatic_gemini_priority_default():
    template = (APP_JS.parents[2] / "templates" / "index.html").read_text(encoding="utf-8")
    assert 'value="auto" selected>Automático (Gemini Online prioritário → Ollama → NLP local)' in template
    assert 'value="gemini">Gemini Online (prioritário → fallback local)' in template


def test_campaign_hub_accounts_are_separate_in_editorial_controls():
    template = (APP_JS.parents[2] / "templates" / "index.html").read_text(encoding="utf-8")

    assert 'value="@renansantosmbl"' in template
    assert 'value="@renansantosreserva"' in template
    assert 'value="@partidomissao"' in template
    assert "As três contas" in template
    assert "Base histórica de clipping" in template


def test_non_core_panels_stay_hidden_in_editing_flow():
    template = (APP_JS.parents[2] / "templates" / "index.html").read_text(encoding="utf-8")

    assert 'id="performanceMetricsSection" hidden' in template
    assert 'id="actionThumbnail" data-action="thumbnail" hidden' in template
    assert 'id="actionSeo"' not in template
    assert "Não decide cortes" in template


def test_media_identity_normalization_protects_transcript_and_source_matching():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function normalizedMediaIdentity(value)" in source
    assert "function mediaPathsMatch(left, right)" in source
    assert 'replaceAll("\\\\", "/")' in source
    assert "mediaPathsMatch(completedSourcePath, selectedSourcePath)" in source
    assert "mediaPathsMatch(state.manualTranscriptVideo, item.path)" in source
    assert "!mediaPathsMatch(state.selectedVideo, state.sourceImportInitialVideoPath)" in source
    assert "!mediaPathsMatch(linkedPath, selectedPath)" in source
    assert "!mediaPathsMatch(state.selectedVideo, item.path)" in source


def test_video_change_explains_previous_job_scope_in_processing_hud():
    source = APP_JS.read_text(encoding="utf-8")
    selection_start = source.find("function selectVideo(item, sourceElement = null)")
    selection_end = source.find("async function openOutputFolderForVideo", selection_start)
    block = source[selection_start:selection_end]

    assert "state.activeJob.state" in block
    assert "A operação anterior continua; Parar cancela o job anterior, não o vídeo novo." in block
    assert "tarefa anterior continua vinculada ao vídeo anterior" in block
    assert "cancelRequested: state.activeJob.state === \"cancel_requested\"" in block


def test_video_change_clears_unbound_transcript_and_source_identity():
    source = APP_JS.read_text(encoding="utf-8")

    assert 'if (!transcriptBelongsToItem)' in source
    assert 'state.manualTranscriptVideo = ""' in source
    assert 'state.transcriptArchive = null' in source
    assert 'input.value = ""' in source


def test_persisted_boundary_adjustment_preserves_transcript_source():
    source = APP_JS.read_text(encoding="utf-8")

    assert "clip.latest_adjustment?.boundary_adjustment" in source
    assert 'source === "transcript"' in source
    assert "Limites alinhados à transcrição." in source
    assert "Limites manuais preservados." in source


def test_operation_dashboard_exposes_persisted_candidate_diagnostic():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function operationJobDiagnosticSummary(job)" in source
    assert 'item?.type === "candidate_diagnostics"' in source
    assert "Diagnóstico editorial:" in source
    assert "operation-job-diagnostic" in source


def test_candidate_volume_notice_separates_render_failures_from_editorial_shortage():
    source = APP_JS.read_text(encoding="utf-8")

    assert "render_failed_after_selection" in source
    assert "partial_render_failure" in source
    assert "Havia candidatos selecionados, mas o render não entregou um arquivo válido" in source
    assert "ocorrência(s) foram registradas no job" in source


def test_candidate_volume_notice_prioritizes_render_failure_over_fallback_pool():
    source = APP_JS.read_text(encoding="utf-8")
    notice_start = source.find("function renderCandidateVolumeNotice")
    notice_end = source.find("// --- Open Folder Button ---", notice_start)
    block = source[notice_start:notice_end]
    render_position = block.find('diagnosticReason === "render_failed_after_selection"')
    fallback_position = block.find('if (fallback > 0)')
    assert render_position >= 0
    assert fallback_position >= 0
    assert render_position < fallback_position


def test_candidate_volume_notice_translates_final_diagnostic_reasons():
    source = APP_JS.read_text(encoding="utf-8")

    assert "no_candidates: \"A fonte não entregou candidatos autossuficientes para revisar.\"" in source
    assert "all_intervals_already_processed" in source
    assert "all_candidates_redundant" in source
    assert "quality_pool_below_reference" in source
    assert "escapeHtml(diagnosticReasonLabel)" in source


def test_candidate_volume_notice_explains_previous_deduplication():
    source = APP_JS.read_text(encoding="utf-8")

    assert "previous_discarded_count" in source
    assert "previous_discarded_approved" in source
    assert "previous_discarded_rejected" in source
    assert "novas partes permaneceram elegíveis" in source


def test_entity_context_review_is_explained_without_name_only_classification():
    source = APP_JS.read_text(encoding="utf-8")

    assert "entity_context_review_required" in source
    assert "primary_entity_role" in source
    assert "O nome não é usado sozinho para classificar o tema." in source
    assert "Entidade citada lateralmente" in source


def test_format_time_is_safe_for_invalid_or_negative_timestamps():
    source = APP_JS.read_text(encoding="utf-8")

    assert "const numeric = Number(seconds);" in source
    assert 'if (!Number.isFinite(numeric)) return "—";' in source
    assert "const safeSeconds = Math.max(0, numeric);" in source


def test_empty_or_unknown_transcript_coverage_is_not_presented_as_ready():
    source = APP_JS.read_text(encoding="utf-8")

    assert "nenhum segmento timestampado utilizável; importe uma transcrição válida antes de cortar" in source
    assert "cobertura temporal não validada; confirme a sincronização no vídeo antes de cortar" in source
    assert '["partial", "empty", "unknown"].includes(coverageStatus)' in source


def test_manual_transcript_parse_uses_selected_video_path_for_coverage():
    source = APP_JS.read_text(encoding="utf-8")

    assert "const selectedVideoPath = selectedVideoPathForRequest();" in source
    assert "const selectedVideoDuration = Number.isFinite(previewDuration) && previewDuration > 0 ? previewDuration : null;" in source
    assert "video_path: selectedVideoPath || null" in source
    assert "state.manualTranscriptVideo = selectedVideoPath || \"pending-source\";" in source


def test_legacy_operation_recovery_rehydrates_source_import_state():
    source = APP_JS.read_text(encoding="utf-8")

    assert "async function recoverLegacyOperation()" in source
    assert 'fetch("/api/process/status")' in source
    assert 'payload.operation === "source_import" && payload.job_id' in source
    assert "Importação de fonte ainda em andamento" in source
    assert "await recoverLegacyOperation();" in source


def test_source_import_tracks_job_until_terminal_status():
    source = APP_JS.read_text(encoding="utf-8")

    assert 'sourceImportJobId: ""' in source
    assert "function setSourceImportBusy(active)" in source
    assert "state.sourceImportJobId = String(data.job_id || \"\");" in source
    assert "setSourceImportBusy(false);" in source
    assert "sourceEventJobId !== String(state.sourceImportJobId)" in source


def test_editorial_search_does_not_overpromise_cached_download():
    source = APP_JS.read_text(encoding="utf-8")

    assert "referência + timestamps; download local não habilitado" in source
    assert "download_action_available ? \"download disponível\"" in source


def test_editorial_search_discards_stale_responses_after_panel_reset():
    source = APP_JS.read_text(encoding="utf-8")

    assert "campaignSearchToken: 0" in source
    assert "state.campaignSearchToken += 1;" in source
    assert "const searchToken = ++state.campaignSearchToken;" in source
    assert "if (searchToken !== state.campaignSearchToken) return;" in source


def test_preview_reset_remains_separate_from_review_workspace_reset():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function clearVideoPreview()" in source
    assert "state.previewToken += 1;" in source
    assert "function resetReviewWorkspaceForVideoChange()" in source
    assert "clearVideoPreview();" in source
    assert source.index("function clearVideoPreview()") < source.index("function resetReviewWorkspaceForVideoChange()")


def test_job_hud_exposes_active_stage_timing_without_replacing_safe_cancellation_copy():
    source = APP_JS.read_text(encoding="utf-8")
    assert "function formatJobStageTiming(job = {})" in source
    assert "job.stage_started_at || job.updated_at" in source
    assert "s nesta etapa" in source
    assert "Parada solicitada; aguardando encerramento seguro${timing}" in source


def test_repeated_context_analysis_clears_previous_dossier_before_polling():
    source = APP_JS.read_text(encoding="utf-8")
    analysis_start = source.find('document.getElementById("btnAnalyzeEditorialContext")')
    analysis_end = source.find("// ─── Results Display ───", analysis_start)
    block = source[analysis_start:analysis_end]
    assert "state.editorialContext = null;" in block
    assert 'state.contextAnalysisSourcePath = "";' in block
    assert 'contextResult.hidden = true;' in block
    assert 'contextResult.innerHTML = "";' in block
    assert "const requestToken = ++state.contextAnalysisToken;" in block


def test_review_card_exposes_quality_scorecard_dimensions_and_status():
    source = APP_JS.read_text(encoding="utf-8")

    assert "const qualityScorecard = clip.quality_scorecard" in source
    assert '["context", "Contexto", "account_tree"]' in source
    assert '["editorial_strength", "Força editorial", "bolt"]' in source
    assert '["technical", "Técnica", "graphic_eq"]' in source
    assert 'class="clip-quality-status' in source
    assert "São dimensões independentes" in source


def test_cut_response_propagates_quality_scorecard_to_review_state():
    source = Path(__file__).resolve().parents[1] / "app.py"
    text = source.read_text(encoding="utf-8")

    assert '"quality_scorecard": clip_info.get("quality_scorecard", {}),' in text
    assert '"editorial_potential_score": clip_info.get("editorial_potential_score"' in text


def test_refresh_review_state_normalizes_persisted_bounds_and_scorecard():
    source = APP_JS.read_text(encoding="utf-8")
    refresh_start = source.find("async function refreshVisibleReviewState()")
    refresh_end = source.find("function transcriptQualityLabel", refresh_start)
    block = source[refresh_start:refresh_end]

    assert "persisted.start ?? persisted.start_time ?? clip.start ?? 0" in block
    assert "persisted.end ?? persisted.end_time ?? clip.end ?? 0" in block
    assert "persisted.quality_scorecard || clip.quality_scorecard || {}" in block
