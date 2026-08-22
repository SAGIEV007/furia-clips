// ═══════════════════════════════════════════════════
// FURIA CLIPS - Frontend Application v2.0
// ═══════════════════════════════════════════════════

const state = {
    selectedVideo: null,
    selectedVideoName: "",
    currentPath: "",
    settings: {},
    clips: [],
    mediaFiles: [],
    connected: false,
    outputDir: "",
    ollamaStatus: "checking",
    processingMode: "unknown",
    selectionSource: "unknown",
    candidateDiagnostics: {},
    resultSourceIdentity: "",
    outputFolder: "",
    currentProjectId: null,
    activeJob: null,
    operationJobs: [],
    operationProjects: [],
    manualTranscript: null,
    manualTranscriptVideo: "",
    transcriptArchive: null,
    editorialContext: null,
    reviewFilter: "all",
    reviewSort: "score",
    videoLayout: "unknown",
    lastReviewAction: null,
    sourceUrl: "",
    sourceDownloadDir: "",
    sourceMaxHeight: 1080,
    sourceImportActive: false,
    sourceImportJobId: "",
    sourceImportInitialVideoPath: "",
    operationDashboardLoading: false,
    lastJobConsoleKey: "",
    repositorySync: null,
    repositorySyncBusy: false,
    campaignHubSnapshotStatus: null,
    campaignHubStatusTimer: null,
    campaignSearchToken: 0,
    contextAnalysisToken: 0,
    contextAnalysisJobId: "",
    contextAnalysisSourcePath: "",
    contextAnalysisController: null,
    transcriptionJobVideoPath: "",
    faceTracking: true,
    previewToken: 0,
    progressHideTimer: null,
    progressSuppressed: false,
    terminalEventKeys: {},
};

// ─── WebSocket Connection ───

const socket = io({
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 10000,
    timeout: 20000,
});
let socketRecoveryNotice = false;

socket.on("connect", () => {
    const recovered = socketRecoveryNotice;
    state.connected = true;
    socketRecoveryNotice = false;
    addConsoleLog(
        recovered ? "[Sistema] Conexão restaurada; os jobs persistidos continuam disponíveis." : "[Sistema] Conectado ao servidor.",
        "success",
    );
    if (recovered) recoverActiveJobs();
});

socket.on("disconnect", (reason) => {
    state.connected = false;
    if (reason === "io client disconnect") {
        addConsoleLog("[Sistema] Desconectado pelo cliente.", "warning");
        return;
    }
    if (!socketRecoveryNotice) {
        socketRecoveryNotice = true;
        addConsoleLog(
            `[Sistema] Conexão interrompida (${reason || "motivo desconhecido"}); reconexão automática em andamento.`,
            "warning",
        );
    }
});

socket.on("connect_error", (error) => {
    if (!socketRecoveryNotice) {
        socketRecoveryNotice = true;
        addConsoleLog(
            `[Sistema] Não foi possível manter o canal em tempo real (${error?.message || "erro de conexão"}); tentando novamente.`,
            "warning",
        );
    }
});

socket.on("connected", (data) => {
    addConsoleLog(`[Sistema] ${data.message}`, "success");
});

function isCurrentProgressEvent(data = {}) {
    const eventJobId = String(data?.job_id || "");
    const activeJobId = String(state.activeJob?.id || "");
    if (!eventJobId) return !activeJobId;
    if (state.sourceImportJobId && eventJobId === String(state.sourceImportJobId)) return true;
    return Boolean(activeJobId && eventJobId === activeJobId);
}

socket.on("progress", (data) => {
    if (!isCurrentProgressEvent(data)) return;
    const time = data.time || new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    const version = data.program_version && !String(data.message || "").includes("[Versão")
        ? `[Versão ${data.program_version}${data.program_revision ? ` · ${data.program_revision}` : ""}] `
        : "";
    addConsoleLog(`[${time}] ${version}${data.message || "Progresso recebido"}`, data.level);
    const activeJobState = String(state.activeJob?.state || "");
    const jobStillActive = ["queued", "running", "cancel_requested"].includes(activeJobState) || state.sourceImportActive;
    if (!state.progressSuppressed || jobStillActive) showProgressBar();
});

socket.on("status", (data) => {
    handleStatusUpdate(data);
});

socket.on("job_update", (job) => {
    handleJobUpdate(job);
});

socket.on("editorial_context_complete", (data) => {
    const eventJobId = String(data?.job_id || "");
    if (!eventJobId || eventJobId !== String(state.contextAnalysisJobId || "")) return;
    state.editorialContext = data?.context || null;
    state.contextAnalysisSourcePath = selectedVideoPathForRequest();
    state.contextAnalysisJobId = "";
    renderEditorialContextPreview(state.editorialContext || {});
    const status = document.getElementById("contextAnalysisStatus");
    if (status) status.textContent = "Contexto pronto. O próximo corte poderá usar esta leitura como referência.";
});

// ─── Ollama Status ───

socket.on("ollama_status", (data) => {
    state.ollamaStatus = data.status;
    state.processingMode = data.mode;
    updateOllamaStatusBadge(data);
});

socket.on("ai_status", (data) => {
    state.ollamaStatus = data.status;
    state.processingMode = data.mode;
    updateOllamaStatusBadge(data);
});

socket.on("selection_mode", (data) => {
    if (!isCurrentJobEvent(data)) return;
    state.selectionSource = data.source;
    state.candidateDiagnostics = data.candidate_diagnostics || {};
    renderCandidateVolumeNotice(state.candidateDiagnostics);
});

function updateOllamaStatusBadge(data) {
    const dot = document.getElementById("ollamaStatusDot");
    const label = document.getElementById("ollamaStatusLabel");
    const modeIndicator = document.getElementById("ollamaModeIndicator");
    const modeIcon = document.getElementById("ollamaModeIcon");
    const modeLabel = document.getElementById("ollamaModeLabel");

    if (!dot || !label) return;

    dot.className = "status-dot";
    modeIndicator.className = "ollama-mode-indicator";

    const backend = data.backend || "ollama";

    if (backend === "gemini" && data.connected) {
        dot.classList.add("connected");
        label.textContent = "Gemini Conectado";
        modeIndicator.classList.add("llm-mode");
        modeIcon.textContent = "cloud";
        modeLabel.textContent = "Gemini Flash";
    } else if (backend === "gemini" && !data.connected) {
        const withoutKey = data.status === "no_key";
        dot.classList.add("offline");
        label.textContent = withoutKey ? "Gemini sem chave · NLP local ativo" : (data.mode_label || "Gemini Offline");
        modeIndicator.classList.add("nlp-mode");
        modeIcon.textContent = withoutKey ? "text_fields" : "cloud_off";
        modeLabel.textContent = withoutKey ? "NLP local" : "Gemini Offline";
    } else if (data.connected) {
        dot.classList.add("connected");
        const backendLabel = data.mode_label || "Ollama Conectado";
        label.textContent = data.model_available && data.model
            ? `${backendLabel} · ${data.model}`
            : backendLabel;
        modeIndicator.classList.add("llm-mode");
        modeIcon.textContent = data.fallback_from ? "sync_problem" : "psychology";
        modeLabel.textContent = data.fallback_from ? "Fallback local" : "IA Inteligente";
    } else {
        dot.classList.add("offline");
        label.textContent = "Ollama Offline";
        modeIndicator.classList.add("nlp-mode");
        modeIcon.textContent = "text_fields";
        modeLabel.textContent = "NLP Basico";
    }
}

// ─── Status Handlers ───

function isCurrentJobEvent(data = {}) {
    const eventJobId = String(data?.job_id || data?.data?.job_id || "");
    const activeJobId = String(state.activeJob?.id || "");
    const activeStates = ["queued", "running", "cancel_requested"];
    if (state.sourceImportJobId && eventJobId === String(state.sourceImportJobId)) return true;
    if (!eventJobId && activeJobId && activeStates.includes(String(state.activeJob?.state || ""))) return false;
    if (!eventJobId || !activeJobId) return true;
    return eventJobId === activeJobId;
}

function terminalEventWasHandled(data = {}) {
    const terminalStatuses = new Set([
        "silence_complete", "transcribe_complete", "source_import_complete", "cut_complete",
        "subtitles_complete", "seo_complete", "thumbnail_complete", "complete_done", "cancelled", "error",
    ]);
    const status = String(data.status || "");
    const eventJobId = String(data.job_id || data.data?.job_id || "");
    if (!eventJobId || !terminalStatuses.has(status)) return false;
    const key = `${eventJobId}:${status}`;
    if (state.terminalEventKeys[key]) return true;
    state.terminalEventKeys[key] = Date.now();
    const keys = Object.keys(state.terminalEventKeys);
    if (keys.length > 64) {
        keys.sort((left, right) => state.terminalEventKeys[left] - state.terminalEventKeys[right])
            .slice(0, keys.length - 64)
            .forEach((oldKey) => delete state.terminalEventKeys[oldKey]);
    }
    return false;
}

function settleLegacyStatusJob(data = {}) {
    const eventJobId = String(data?.job_id || data?.data?.job_id || "");
    const activeJobId = String(state.activeJob?.id || "");
    const terminalStatuses = new Set([
        "silence_complete", "transcribe_complete", "source_import_complete", "cut_complete",
        "subtitles_complete", "seo_complete", "thumbnail_complete", "complete_done", "cancelled", "error",
    ]);
    if (!eventJobId || !activeJobId || eventJobId !== activeJobId || !terminalStatuses.has(String(data.status || ""))) return;
    const terminalState = data.status === "cancelled"
        ? "cancelled"
        : data.status === "error"
            ? "failed"
            : "completed";
    state.activeJob = {
        ...state.activeJob,
        state: terminalState,
        message: data.data?.message || state.activeJob.message || "Operação encerrada.",
    };
}

function handleStatusUpdate(data) {
    if (!isCurrentJobEvent(data) || terminalEventWasHandled(data)) return;
    const sourceEvent = data.status === "source_import_complete" || data.data?.operation === "source_import";
    const sourceEventJobId = String(data?.job_id || data?.data?.job_id || "");
    if (sourceEvent && !state.sourceImportActive && !state.sourceImportJobId) return;
    if (sourceEvent && state.sourceImportJobId && sourceEventJobId && sourceEventJobId !== String(state.sourceImportJobId)) return;
    settleLegacyStatusJob(data);
    switch (data.status) {
        case "silence_complete":
            hideProgressBar();
            showToast("Silencio removido com sucesso!", "success");
            loadMediaFiles();
            break;
        case "transcribe_complete": {
            hideProgressBar();
            const completedSourcePath = String(data.data?.source_video_path || state.transcriptionJobVideoPath || "");
            const selectedSourcePath = selectedVideoPathForRequest();
            const sourceStillSelected = mediaPathsMatch(completedSourcePath, selectedSourcePath);
            if (data.data) {
                state.manualTranscript = data.data;
                state.manualTranscriptVideo = completedSourcePath || (sourceStillSelected ? selectedSourcePath : "pending-source");
                if (sourceStillSelected || !completedSourcePath) {
                    hydrateTranscriptEditor(data.data, data.data.archive_metadata || data.data.archive);
                    showToast("Transcricao concluida!", "success");
                } else {
                    showSourceOnlyStatus("Transcrição concluída para a fonte anterior; selecione esse vídeo para validá-la antes do corte.", "warning");
                    addConsoleLog("[Transcrição] Resultado mantido com a identidade da fonte; não foi aplicado ao vídeo selecionado.", "warning");
                    showToast("Transcrição concluída para outra fonte; seleção atual preservada.", "warning");
                }
            } else {
                showToast("Transcricao concluida, mas sem segmentos disponíveis.", "warning");
            }
            state.transcriptionJobVideoPath = "";
            break;
        }
        case "source_import_complete": {
            hideProgressBar();
            setSourceImportBusy(false);
            const importedPath = data.data.path || data.data.absolute_path || "";
            const preserveCurrentSelection = Boolean(
                state.selectedVideo && !mediaPathsMatch(state.selectedVideo, state.sourceImportInitialVideoPath)
            );
            state.sourceImportJobId = "";
            state.sourceDownloadDir = data.data.destination_dir || state.sourceDownloadDir;
            if (!preserveCurrentSelection) {
                state.transcriptArchive = data.data.transcription_archive || data.data.transcription_files?.archive || null;
                if (data.data.transcription) {
                    state.manualTranscript = data.data.transcription;
                    state.manualTranscriptVideo = importedPath;
                    hydrateTranscriptEditor(data.data.transcription, state.transcriptArchive);
                    const transcriptCount = data.data.transcription.segment_count || data.data.transcription.segments?.length || 0;
                    const transcriptFile = data.data.transcription_archive?.text || data.data.transcription_files?.archive?.text || data.data.transcription_files?.text;
                    const transcriptLabel = transcriptFile ? ` Arquivo persistente: ${transcriptFile}` : "";
                    showSourceStatus(`Fonte importada e transcrição automática pronta: ${transcriptCount} segmentos.${transcriptLabel}`, "success");
                } else {
                    showSourceStatus("Fonte importada; a transcrição automática não ficou disponível. Você pode clicar em Gerar do vídeo.", "warning");
                }
            } else {
                showSourceOnlyStatus("Fonte importada; a seleção atual foi preservada. Selecione a nova fonte na biblioteca para usar sua transcrição.", "warning");
                addConsoleLog("[Fonte] Importação concluída; seleção atual preservada para evitar trocar o contexto silenciosamente.", "warning");
            }
            const externalImported = {
                path: importedPath,
                name: data.data.title || (importedPath || "Vídeo importado").split(/[\\/]/).pop(),
                size_human: "Fonte pública",
            };
            loadMediaFiles().then(() => {
                if (preserveCurrentSelection) return;
                const imported = state.mediaFiles.find(item => item.path === importedPath);
                selectVideo(imported || externalImported, null);
            });
            state.sourceImportInitialVideoPath = "";
            showToast(
                preserveCurrentSelection
                    ? "Vídeo importado; seleção atual preservada."
                    : (data.data.transcription ? "Vídeo e transcrição importados!" : "Vídeo do link importado!"),
                preserveCurrentSelection ? "warning" : "success",
            );
            break;
        }
        case "cut_complete": {
            hideProgressBar();
            const completedClips = Array.isArray(data.data.clips) ? data.data.clips : [];
            updateWorkspaceWorkflow("review", completedClips.length ? "Revisão pronta" : "Revisão requer atenção");
            state.selectionSource = data.data.selection_source || "nlp";
            state.candidateDiagnostics = data.data.candidate_diagnostics || state.candidateDiagnostics || {};
            state.resultSourceIdentity = String(data.data.source_identity || "").trim();
            state.currentProjectId = data.data.project_id || state.currentProjectId || null;
            state.outputFolder = data.data.output_folder || "";
            if (completedClips.length) {
                showToast(`${completedClips.length} clips gerados e ranqueados!`, "success");
            } else {
                const rejection = (data.data.render_rejections || [])
                    .flatMap(item => item.errors || [])
                    .filter(Boolean)[0];
                showToast(
                    rejection ? `Nenhum clip válido: ${rejection}` : "Nenhum clip válido foi entregue; revise o diagnóstico do console.",
                    "error",
                );
            }
            renderEditorialAudit(data.data.editorial_audit, data.data.audit_mode || "standard");
            renderCandidateVolumeNotice(state.candidateDiagnostics);
            displayResults(completedClips, data.data.video_layout || null);
            updateResultsModeBadge(state.selectionSource);
            updateOpenFolderButton(state.outputFolder);
            break;
        }
        case "subtitles_complete":
            hideProgressBar();
            showToast("Legendas geradas com sucesso!", "success");
            loadMediaFiles();
            break;
        case "seo_complete":
            hideProgressBar();
            showToast("Conteudo SEO gerado!", "success");
            if (data.data) displaySeoResult(data.data);
            break;
        case "thumbnail_complete":
            hideProgressBar();
            showToast("Thumbnail gerada!", "success");
            if (data.data && data.data.path) {
                showThumbnailPreview(data.data.path);
            }
            break;
        case "complete_done":
            hideProgressBar();
            updateWorkspaceWorkflow("review", "Revisão pronta");
            state.outputFolder = data.data.output_dir || "";
            state.currentProjectId = data.data.project_id || state.currentProjectId || null;
            showToast(`Processo completo! ${data.data.total_clips} clips gerados e ranqueados.`, "success");
            displayResults(data.data.clips, data.data.video_layout || null);
            updateOpenFolderButton(state.outputFolder);
            loadMediaFiles();
            break;
        case "cancelled":
            hideProgressBar();
            if (data.data?.operation === "source_import") {
                setSourceImportBusy(false);
                state.sourceImportJobId = "";
                state.sourceImportInitialVideoPath = "";
            }
            updateWorkspaceWorkflow("source", "Operação pausada");
            showToast(data.data?.message || "Operação cancelada.", "warning");
            addConsoleLog("[Sistema] Operação cancelada com segurança.", "warning");
            break;
        case "error":
            hideProgressBar();
            if (data.data?.operation === "source_import") {
                setSourceImportBusy(false);
                state.sourceImportJobId = "";
                state.sourceImportInitialVideoPath = "";
            }
            updateWorkspaceWorkflow("source", "Atenção necessária");
            showToast(data.data?.message || "Erro no processamento", "error");
            break;
    }
}

// ─── Console ───

function addConsoleLog(message, level = "info") {
    const console_el = document.getElementById("consoleOutput");
    const line = document.createElement("div");
    line.className = `console-line ${level}`;
    line.textContent = message;
    console_el.appendChild(line);
    console_el.scrollTop = console_el.scrollHeight;
    updateProcessingJourney(message, level);

    // Keep max 200 lines
    while (console_el.children.length > 200) {
        console_el.removeChild(console_el.firstChild);
    }
}

function showProcessingControls(label = "Processamento em andamento.", options = {}) {
    const controls = document.getElementById("processingControls");
    const status = document.getElementById("processingOperationStatus");
    const button = document.getElementById("btnCancelOperation");
    const journey = document.getElementById("processingJourney");
    if (controls) controls.style.display = "flex";
    if (status) status.textContent = label;
    if (button) button.disabled = Boolean(options.cancelRequested);
    if (journey && journey.style.display !== "block") {
        resetProcessingJourney();
        journey.style.display = "block";
    }
    const journeyLabel = document.getElementById("processingJourneyLabel");
    if (journeyLabel) journeyLabel.textContent = label;
}

function hideProcessingControls() {
    const controls = document.getElementById("processingControls");
    const button = document.getElementById("btnCancelOperation");
    const journey = document.getElementById("processingJourney");
    if (controls) controls.style.display = "none";
    if (journey) journey.style.display = "none";
    if (button) button.disabled = false;
}

function updateWorkspaceWorkflow(stage = "source", stateLabel = "") {
    const order = ["source", "analysis", "review", "learning"];
    const index = Math.max(0, order.indexOf(stage));
    document.querySelectorAll(".workflow-step").forEach((step, stepIndex) => {
        step.classList.toggle("active", stepIndex === index);
        step.classList.toggle("complete", stepIndex < index);
    });
    const state = document.getElementById("workspaceState");
    if (state) {
        const label = state.querySelector("span:last-child");
        if (label && stateLabel) label.textContent = stateLabel;
        state.classList.toggle("is-busy", stage === "analysis");
        state.classList.toggle("is-review", stage === "review");
    }
}

function resetProcessingJourney() {
    document.querySelectorAll("[data-process-step]").forEach((step) => {
        step.classList.remove("active", "complete", "error");
    });
    const source = document.querySelector('[data-process-step="source"]');
    if (source) source.classList.add("active");
    updateWorkspaceWorkflow("source", "Pronto para analisar");
}

function updateProcessingJourney(message = "", level = "info") {
    const journey = document.getElementById("processingJourney");
    if (!journey || journey.style.display === "none") return;
    const value = String(message).toLowerCase();
    const stages = ["source", "transcript", "context", "ranking", "render"];
    let current = null;
    if (/\[fonte\]|download|importando|vídeo importado/.test(value)) current = "source";
    else if (/transcri|gemini|whisper|legenda pública/.test(value)) current = "transcript";
    else if (/contexto|analise de video|análise de vídeo|\[layout\]|detec[cç][aã]o de cena/.test(value)) current = "context";
    else if (/selecao|seleção|ranqueamento|ranking|\[nlp\]/.test(value)) current = "ranking";
    else if (/cortando|corte completo|renderizando|clip.*gerado/.test(value)) current = "render";
    if (!current) return;

    const currentIndex = stages.indexOf(current);
    const workspaceStage = current === "source" ? "source" : "analysis";
    updateWorkspaceWorkflow(workspaceStage, current === "source" ? "Preparando fonte" : "Analisando contexto");
    stages.forEach((stage, index) => {
        const element = document.querySelector(`[data-process-step="${stage}"]`);
        if (!element) return;
        element.classList.toggle("complete", index < currentIndex);
        element.classList.toggle("active", index === currentIndex && level !== "error");
        element.classList.toggle("error", index === currentIndex && level === "error");
    });
    const label = document.getElementById("processingJourneyLabel");
    if (label) label.textContent = message.replace(/^\[[^\]]+\]\s*/, "").slice(0, 100);
}

async function requestCancelOperation() {
    const button = document.getElementById("btnCancelOperation");
    const status = document.getElementById("processingOperationStatus");
    if (button) button.disabled = true;
    if (status) status.textContent = "Solicitando parada segura...";
    addConsoleLog("[Sistema] Solicitação de parada enviada; aguardando a etapa segura.", "warning");
    try {
        const jobId = state.activeJob && ["queued", "running", "cancel_requested"].includes(state.activeJob.state)
            ? state.activeJob.id
            : null;
        const response = await fetch("/api/process/cancel", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(jobId ? { job_id: jobId } : {}),
        });
        const data = await parseJsonResponse(response, "Cancelamento");
        if (!response.ok || data.error) throw new Error(data.error || "Não foi possível solicitar o cancelamento");
        if (jobId && state.activeJob?.id === jobId) {
            state.activeJob = { ...state.activeJob, state: data.state || "cancel_requested" };
            showProcessingControls(`[Job ${String(jobId).slice(0, 8)}] Parada solicitada; aguardando encerramento seguro`, { cancelRequested: true });
        }
        if (status) status.textContent = "Parada solicitada; a operação será encerrada com segurança.";
    } catch (error) {
        if (button) button.disabled = false;
        if (status) status.textContent = error.message;
        showToast(error.message, "error");
    }
}

document.getElementById("btnCancelOperation")?.addEventListener("click", requestCancelOperation);
document.getElementById("btnRefreshOperations")?.addEventListener("click", loadOperationDashboard);

document.getElementById("btnEditorialBackup")?.addEventListener("click", requestEditorialBackup);
document.getElementById("btnRefreshTranscriptArchive")?.addEventListener("click", loadTranscriptArchive);
document.getElementById("btnEditorialRestore")?.addEventListener("click", () => document.getElementById("editorialRestoreInput")?.click());
document.getElementById("editorialRestoreInput")?.addEventListener("change", restoreEditorialBackup);
document.getElementById("btnRepositoryCheck")?.addEventListener("click", () => checkRepositorySync(true));
document.getElementById("btnRepositoryUpdate")?.addEventListener("click", () => runRepositorySync("update"));
document.getElementById("btnRepositoryPushFeedback")?.addEventListener("click", () => runRepositorySync("push_feedback"));
document.getElementById("btnRepositoryRestoreFeedback")?.addEventListener("click", () => runRepositorySync("restore_feedback"));

function prepareNewOperationHud() {
    state.terminalEventKeys = {};
    state.progressSuppressed = false;
    if (state.progressHideTimer) {
        window.clearTimeout(state.progressHideTimer);
        state.progressHideTimer = null;
    }
}

function registerStartedOperation(started, message = "Operação adicionada à fila persistente.") {
    if (!started?.job_id) return false;
    prepareNewOperationHud();
    state.activeJob = {
        id: String(started.job_id),
        state: started.state || "queued",
        stage: started.operation || "legacy",
        message,
    };
    showProcessingControls(message);
    return true;
}

function showProgressBar() {
    if (state.progressHideTimer) {
        window.clearTimeout(state.progressHideTimer);
        state.progressHideTimer = null;
    }
    state.progressSuppressed = false;
    const activeJob = state.activeJob;
    const activeStates = ["queued", "running", "cancel_requested"];
    const label = activeJob && activeStates.includes(activeJob.state)
        ? activeJob.state === "cancel_requested"
            ? `[Job ${String(activeJob.id || "").slice(0, 8)}] Parada solicitada; aguardando encerramento seguro`
            : `[Job ${String(activeJob.id || "").slice(0, 8)}] ${activeJob.message || activeJob.stage || "Processando"}`
        : "Processamento em andamento.";
    showProcessingControls(label, { cancelRequested: activeJob?.state === "cancel_requested" });
    const container = document.getElementById("progressBarContainer");
    const bar = document.getElementById("progressBar");
    container.style.display = "block";
    if (!bar.dataset.animating) {
        bar.dataset.animating = "true";
        let width = 0;
        const interval = setInterval(() => {
            if (width >= 95) {
                clearInterval(interval);
            } else {
                width += Math.random() * 3;
                bar.style.width = Math.min(width, 95) + "%";
            }
        }, 500);
        bar.dataset.interval = interval;
    }
}

function formatOperationJobType(type) {
    const labels = {
        cut_shorts: "Corte inteligente",
        process_complete: "Processo completo",
    };
    return labels[type] || String(type || "Processamento").replaceAll("_", " ");
}

function operationJobTime(value) {
    if (!value) return "agora";
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? "agora" : parsed.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

function operationJobMessage(job = {}) {
    if (String(job.stage || "") === "stale_recovered" || String(job.error || "") === "stale_job_recovered") {
        return "Operação interrompida após recuperação do servidor; nenhum novo corte foi executado. Confira a fonte e inicie novamente.";
    }
    return String(job.error || job.message || job.stage || "Aguardando execução");
}

function operationJobStateLabel(state = "queued") {
    const labels = {
        queued: "Na fila",
        running: "Em andamento",
        cancel_requested: "Parada solicitada",
        completed: "Concluída",
        failed: "Falhou · atenção necessária",
        cancelled: "Cancelada com segurança",
    };
    return labels[String(state || "queued")] || "Estado não identificado";
}

function operationJobDiagnosticSummary(job) {
    const artifact = Array.isArray(job?.artifacts)
        ? job.artifacts.find((item) => item?.type === "candidate_diagnostics")
        : null;
    if (!artifact) return "";
    const labels = {
        no_candidates: "a fonte não entregou candidatos autossuficientes",
        all_intervals_already_processed: "os intervalos já haviam sido processados",
        all_candidates_redundant: "os candidatos eram redundantes",
        quality_pool_below_reference: "os gates preservaram apenas momentos autossuficientes",
        render_failed_after_selection: "os candidatos foram selecionados, mas o render falhou",
        partial_render_failure: "parte dos renders falhou",
        short_source: "a fonte é curta e não exige uma quota artificial",
        adequate_pool: "o pool editorial foi considerado adequado",
    };
    const reason = labels[String(artifact.reason || "").trim().toLowerCase()] || "o diagnóstico depende dos sinais editoriais disponíveis";
    const finalCount = Number(artifact.rendered_count ?? artifact.final_count ?? 0);
    const rejected = Number(artifact.render_rejection_count || 0);
    return `Diagnóstico editorial: ${finalCount} arquivo(s) renderizado(s); ${reason}${rejected ? ` · ${rejected} ocorrência(s) de render registrada(s)` : ""}.`;
}

function renderOperationDashboard({ jobs = state.operationJobs || [] } = {}) {
    const list = Array.isArray(jobs) ? jobs : [];
    const active = list.filter((job) => job.state === "running").length;
    const queued = list.filter((job) => ["queued", "cancel_requested"].includes(job.state)).length;
    const completed = list.filter((job) => job.state === "completed").length;
    const attention = list.filter((job) => ["failed", "cancelled"].includes(job.state)).length;
    const setCount = (id, value) => {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    };
    setCount("operationActiveCount", active);
    setCount("operationQueuedCount", queued);
    setCount("operationCompletedCount", completed);
    setCount("operationAttentionCount", attention);

    const subtitle = document.getElementById("operationSubtitle");
    if (subtitle) {
        subtitle.textContent = list.length
            ? `${active + queued} tarefa(s) em execução ou aguardando; histórico recente salvo neste computador.`
            : "Nenhuma tarefa recente. Importe uma live para iniciar a fila visual.";
    }

    const container = document.getElementById("operationJobs");
    if (!container) return;
    if (!list.length) {
        container.innerHTML = `<div class="operation-empty">A fila aparecerá aqui com o andamento de cada live.</div>`;
        return;
    }
    container.innerHTML = list.slice(0, 8).map((job) => {
        const progress = Math.max(0, Math.min(100, Number(job.progress || 0)));
        const message = escapeHtml(operationJobMessage(job));
        const diagnosticSummary = operationJobDiagnosticSummary(job);
        const stateCode = String(job.state || "queued");
        const stateLabel = escapeHtml(operationJobStateLabel(stateCode));
        return `<article class="operation-job ${escapeHtml(stateCode)}" data-state="${escapeHtml(stateCode)}">
            <div class="operation-job-head">
                <div class="operation-job-type"><span class="material-icons-round">${job.type === "cut_shorts" ? "content_cut" : "auto_awesome"}</span>${escapeHtml(formatOperationJobType(job.type))}</div>
                <span class="operation-job-state">${stateLabel}</span>
            </div>
            <p class="operation-job-message">${message}</p>
            ${diagnosticSummary ? `<small class="operation-job-diagnostic">${escapeHtml(diagnosticSummary)}</small>` : ""}
            <div class="operation-job-progress"><div style="width:${progress}%"></div></div>
            <div class="operation-job-meta"><span>${progress}%</span><span>${operationJobTime(job.updated_at || job.created_at)}</span></div>
        </article>`;
    }).join("");
}

function renderEditorialLearning(calibration = {}) {
    const panel = document.getElementById("editorialLearning");
    const title = document.getElementById("editorialLearningTitle");
    const text = document.getElementById("editorialLearningText");
    const badge = document.getElementById("editorialLearningBadge");
    const coverageTarget = document.getElementById("editorialLearningCoverage");
    if (!panel || !title || !text || !badge) return;
    const sample = Number(calibration.sample_size || 0);
    const minimum = Number(calibration.minimum_sample_size || 12);
    const approved = Number(calibration.approved_count || 0);
    const rejected = Number(calibration.rejected_count || 0);
    const durationSignal = calibration.duration_signal || {};
    const durationGap = Number(durationSignal.gap_seconds || 0);
    const topRejection = Array.isArray(calibration.top_rejection_reasons) ? calibration.top_rejection_reasons[0] : null;
    const coverageCategories = calibration.reason_coverage?.categories || {};
    const coverageLabels = {
        hook: "Hook",
        context_payoff: "Contexto/payoff",
        speaker_audio: "Locutor/áudio",
        duration: "Duração",
        framing: "Enquadramento",
    };
    if (coverageTarget) {
        const coverageEntries = Object.entries(coverageLabels).map(([key, label]) => {
            const item = coverageCategories[key] || {};
            const total = Number(item.total || 0);
            const usable = safeBooleanFlag(item.usable);
            return `<span class="editorial-learning-coverage-chip ${usable ? "usable" : "insufficient"}" title="${usable ? "Amostra suficiente para este sinal" : "Ainda sem amostra suficiente para calibrar"}"><b>${escapeHtml(label)}</b> ${total} ${usable ? "utilizável" : "insuficiente"}</span>`;
        });
        coverageTarget.innerHTML = `<span class="editorial-learning-coverage-label">Cobertura dos motivos:</span>${coverageEntries.join("")}`;
    }
    const calibrationEligible = safeBooleanFlag(calibration.eligible);
    panel.classList.toggle("is-active", calibrationEligible);
    if (calibrationEligible) {
        title.textContent = "Calibração editorial ativa";
        const durationNote = safeBooleanFlag(durationSignal.usable) && Math.abs(durationGap) >= 0.1
            ? ` A amostra indica preferência por cortes ${durationGap > 0 ? 'mais curtos' : 'mais longos'} em ${Math.abs(durationGap).toFixed(1)}s, como sinal fraco.`
            : " A duração continua sendo apenas uma preferência contextual.";
        const reasonNote = topRejection ? ` Motivo de rejeição mais frequente: ${String(topRejection.reason).replaceAll('_', ' ')} (${topRejection.count}).` : "";
        text.textContent = `${sample} decisões finais (${approved} aprovadas e ${rejected} rejeitadas) ajustam o ranking de forma limitada e explicável.${durationNote}${reasonNote}`;
        badge.textContent = "ATIVA";
    } else {
        const remaining = Math.max(0, minimum - sample);
        title.textContent = "Aprendizado editorial em coleta";
        const reasonNote = topRejection ? ` Motivo mais registrado: ${String(topRejection.reason).replaceAll('_', ' ')}.` : "";
        text.textContent = `${sample} decisão(ões) final(is) registradas. Faltam ${remaining} para avaliar uma calibração conservadora.${reasonNote}`;
        badge.textContent = `${sample}/${minimum}`;
    }
}

async function loadEditorialLearning() {
    try {
        const response = await fetch("/api/editorial/calibration");
        const payload = await parseJsonResponse(response, "Aprendizado editorial");
        if (!response.ok) throw new Error(payload.error || "Não foi possível carregar a calibração");
        renderEditorialLearning(payload);
    } catch (error) {
        const text = document.getElementById("editorialLearningText");
        if (text) text.textContent = "O histórico editorial ficará disponível assim que a próxima revisão for salva.";
    }
}

function formatDataSize(bytes) {
    const value = Number(bytes || 0);
    if (!value) return "0 B";
    const units = ["B", "KB", "MB", "GB"];
    let index = 0;
    let size = value;
    while (size >= 1024 && index < units.length - 1) {
        size /= 1024;
        index += 1;
    }
    return `${size.toFixed(size >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

function renderEditorialData(data = {}) {
    const card = document.getElementById("editorialDataCard");
    const title = document.getElementById("editorialDataTitle");
    const text = document.getElementById("editorialDataText");
    const badge = document.getElementById("editorialDataBadge");
    if (!card || !title || !text || !badge) return;
    const healthy = data.integrity === "ok";
    const pending = data.integrity === "missing";
    badge.classList.toggle("attention", !healthy);
    if (healthy) {
        title.textContent = "Dados editoriais protegidos fora do programa";
        text.textContent = `${Number(data.projects || 0)} projeto(s), ${Number(data.clips || 0)} clip(s) e ${Number(data.feedback_events || 0)} aprovação(ões)/rejeição(ões) ficam preservados fora do GitHub; o ZIP também inclui transcrições e ajustes.`;
        badge.textContent = "ÍNTEGRO";
    } else if (pending) {
        title.textContent = "Base editorial pronta para o primeiro projeto";
        text.textContent = "As próximas aprovações/rejeições serão salvas fora do código. O backup ZIP inclui decisões, transcrições e ajustes; crie um após sua primeira revisão.";
        badge.textContent = "PRONTO";
    } else {
        title.textContent = "Dados editoriais exigem atenção";
        text.textContent = "Não foi possível confirmar a integridade agora. Crie um backup ou restaure uma cópia conhecida antes de atualizar o programa.";
        badge.textContent = "REVISAR";
    }
}

function renderDailyEditorialGoal(progress = {}) {
    const panel = document.getElementById("dailyEditorialGoal");
    const title = document.getElementById("dailyEditorialTitle");
    const value = document.getElementById("dailyEditorialValue");
    const text = document.getElementById("dailyEditorialText");
    const bar = document.getElementById("dailyEditorialProgressBar");
    const badge = document.getElementById("dailyEditorialBadge");
    if (!panel || !title || !value || !text || !bar || !badge) return;
    const minimum = Number(progress.target_min || 39);
    const maximum = Number(progress.target_max || 50);
    const approved = Number(progress.approved || 0);
    const queue = Number(progress.review_queue || 0);
    const remaining = Math.max(0, Number(progress.remaining_to_minimum ?? (minimum - approved)));
    const reached = safeBooleanFlag(progress.target_reached);
    panel.classList.toggle("is-reached", reached);
    value.textContent = `${approved} / ${minimum} aprovados`;
    bar.style.width = `${Math.max(0, Math.min(100, Number(progress.progress_percent || 0)))}%`;
    if (reached) {
        title.textContent = "Meta mínima diária atingida";
        text.textContent = `${approved} cortes aprovados; a faixa operacional continua até ${maximum}. ${queue ? `${queue} ainda aguardam revisão.` : ""}`.trim();
        badge.textContent = "META ATINGIDA";
    } else {
        title.textContent = "Meta diária editorial";
        text.textContent = `${remaining} aprovação(ões) faltam para a meta mínima. ${queue ? `${queue} corte(s) aguardam sua revisão.` : "Processe uma live para criar candidatos."}`;
        badge.textContent = `${approved}/${minimum}`;
    }
}

function renderProjectLibrary(projects = state.operationProjects || []) {
    const list = Array.isArray(projects) ? projects : [];
    const container = document.getElementById("projectLibraryList");
    const summary = document.getElementById("projectLibrarySummary");
    if (!container || !summary) return;
    summary.textContent = list.length ? `${list.length} projeto(s) preservados neste computador` : "Nenhuma live processada ainda";
    if (!list.length) {
        container.innerHTML = '<div class="project-library-empty">Cada live processada aparecerá aqui com seus candidatos, aprovações e pendências de revisão.</div>';
        return;
    }
    container.innerHTML = list.slice(0, 6).map((project) => {
        const name = escapeHtml(String(project.name || "Live sem nome"));
        const status = escapeHtml(String(project.status || "pending").replaceAll("_", " "));
        const clips = Number(project.clip_count || 0);
        const approved = Number(project.approved_count || 0);
        const review = Number(project.review_count || 0);
        return `<article class="project-library-item" title="${name}">
            <div class="project-library-name">${name}</div>
            <div class="project-library-meta"><span>${clips} clips</span><span><b>${approved}</b> aprovados</span><span>${review} revisar</span></div>
            <span class="project-library-status">${status}</span>
        </article>`;
    }).join("");
}

async function refreshVisibleReviewState() {
    const projectId = Number(state.currentProjectId);
    if (!Number.isInteger(projectId) || projectId <= 0 || !Array.isArray(state.clips) || !state.clips.length) return false;
    try {
        const response = await fetch(`/api/projects/${projectId}`);
        const payload = await parseJsonResponse(response, "Estado persistente da revisão");
        if (!response.ok || !Array.isArray(payload.clips)) throw new Error(payload.error || "Não foi possível atualizar os estados dos clips");
        const persistedById = new Map(payload.clips.filter((clip) => clip?.id != null).map((clip) => [String(clip.id), clip]));
        const persistedByKey = new Map(payload.clips.filter((clip) => clip?.editorial_key).map((clip) => [String(clip.editorial_key), clip]));
        state.clips = state.clips.map((clip) => {
            const persisted = persistedById.get(String(clip.clip_id ?? clip.id)) || persistedByKey.get(String(clip.editorial_key || ""));
            if (!persisted) return clip;
            return {
                ...clip,
                start: Number(persisted.start ?? persisted.start_time ?? clip.start ?? 0),
                end: Number(persisted.end ?? persisted.end_time ?? clip.end ?? 0),
                duration: Number(persisted.duration ?? clip.duration ?? 0),
                path: persisted.file_path || clip.path,
                review_status: persisted.review_status || clip.review_status,
                review_updated_at: persisted.review_updated_at || clip.review_updated_at,
                latest_feedback_reason: persisted.latest_feedback_reason || clip.latest_feedback_reason,
                latest_feedback_tags: Array.isArray(persisted.latest_feedback_tags) ? persisted.latest_feedback_tags : (clip.latest_feedback_tags || []),
                quality_scorecard: persisted.quality_scorecard || clip.quality_scorecard || {},
            };
        });
        renderReviewCommandCenter();
        renderResultsGrid();
        return true;
    } catch (error) {
        addConsoleLog(`[Revisão] Estados restaurados não foram refletidos nos cards: ${error.message}`, "warning");
        return false;
    }
}

async function loadProjectLibrary() {
    try {
        const response = await fetch("/api/projects");
        const payload = await parseJsonResponse(response, "Biblioteca de lives");
        if (!response.ok || !Array.isArray(payload)) throw new Error("Não foi possível carregar os projetos");
        state.operationProjects = payload;
        renderProjectLibrary(payload);
    } catch (error) {
        const summary = document.getElementById("projectLibrarySummary");
        if (summary) summary.textContent = "Biblioteca indisponível no momento";
    }
}

async function loadDailyEditorialGoal() {
    try {
        const response = await fetch("/api/editorial/daily-progress");
        const payload = await parseJsonResponse(response, "Meta diária editorial");
        if (!response.ok) throw new Error(payload.error || "Não foi possível carregar a meta diária");
        renderDailyEditorialGoal(payload);
    } catch (error) {
        const text = document.getElementById("dailyEditorialText");
        if (text) text.textContent = "A meta diária será atualizada quando houver decisões editoriais registradas.";
    }
}

async function loadEditorialData() {
    try {
        const response = await fetch("/api/editorial/data");
        const payload = await parseJsonResponse(response, "Dados editoriais");
        if (!response.ok) throw new Error(payload.error || "Não foi possível verificar os dados editoriais");
        renderEditorialData(payload);
    } catch (error) {
        const text = document.getElementById("editorialDataText");
        const badge = document.getElementById("editorialDataBadge");
        if (text) text.textContent = "A verificação local ficará disponível quando o servidor responder.";
        if (badge) {
            badge.textContent = "INDISPONÍVEL";
            badge.classList.add("attention");
        }
    }
}

function transcriptQualityLabel(quality = {}) {
    const label = quality.quality || "não validada";
    const score = Number(quality.score);
    return Number.isFinite(score) ? `${label} · ${score}/100` : label;
}

function renderTranscriptArchive(items = []) {
    const list = document.getElementById("transcriptArchiveList");
    const summary = document.getElementById("transcriptArchiveSummary");
    if (!list || !summary) return;
    if (!items.length) {
        summary.textContent = "Nenhuma transcrição persistente foi arquivada ainda.";
        list.innerHTML = "";
        return;
    }
    summary.textContent = `${items.length} transcrição(ões) arquivada(s) fora da pasta do programa.`;
    list.innerHTML = items.map(item => {
        const quality = item.quality || {};
        const warning = quality.quality !== "structurally_ok";
        const source = escapeHtml(item.source || "automática");
        const project = item.project_id ? `Projeto #${item.project_id}` : "sem projeto";
        return `<div class="transcript-archive-item">
            <div class="transcript-archive-meta"><strong>${escapeHtml(item.source_video || item.relative_dir || "Transcrição")}</strong><small>${source} · ${project} · ${safeNonNegativeCount(item.valid_segment_count)} segmentos válidos</small></div>
            <span class="transcript-quality ${warning ? "warning" : ""}">${escapeHtml(transcriptQualityLabel(quality))}</span>
            <div class="transcript-archive-actions"><a class="btn btn-sm" href="${escapeHtml(item.download_text || "#")}" target="_blank" rel="noopener">TXT</a><a class="btn btn-sm" href="${escapeHtml(item.download_json || "#")}" target="_blank" rel="noopener">JSON</a></div>
        </div>`;
    }).join("");
}

async function loadTranscriptArchive() {
    try {
        const response = await fetch("/api/editorial/transcripts?limit=100");
        const payload = await parseJsonResponse(response, "Arquivo de transcrições");
        if (!response.ok) throw new Error(payload.error || "Não foi possível carregar as transcrições arquivadas");
        renderTranscriptArchive(payload.transcripts || []);
    } catch (error) {
        const detail = String(error?.message || "falha não identificada").trim();
        const summary = document.getElementById("transcriptArchiveSummary");
        if (summary) summary.textContent = "Arquivo de transcrições indisponível agora. Atualize o painel; o detalhe técnico foi registrado no console.";
        addConsoleLog(`[Arquivo de transcrições] Falha técnica: ${detail}`, "error");
    }
}

async function requestEditorialBackup() {
    const button = document.getElementById("btnEditorialBackup");
    if (button) button.disabled = true;
    try {
        const response = await fetch("/api/editorial/backup", { method: "POST" });
        const payload = await parseJsonResponse(response, "Backup editorial");
        if (!response.ok || !payload.success) throw new Error(payload.error || "Não foi possível criar o backup");
        const downloadLink = document.createElement("a");
        downloadLink.href = `/api/editorial/backup/${encodeURIComponent(payload.filename)}`;
        downloadLink.download = payload.filename || "furia-editorial-backup.zip";
        downloadLink.rel = "noopener";
        document.body.appendChild(downloadLink);
        downloadLink.click();
        downloadLink.remove();
        showToast(`Backup criado (${formatDataSize(payload.size_bytes)}). Guarde o arquivo fora da pasta do programa.`, "success");
        renderEditorialData(payload.summary || {});
        await checkRepositorySync(false);
    } catch (error) {
        showToast(error.message || "Não foi possível criar o backup editorial", "error");
    } finally {
        if (button) button.disabled = false;
    }
}

async function restoreEditorialBackup(event) {
    const input = event.target;
    const file = input?.files?.[0];
    if (!file) return;
    const confirmed = window.confirm(
        "Restaurar substitui a base editorial atual. O Furia Clips criará um backup de segurança antes da troca. Continuar?"
    );
    if (!confirmed) {
        input.value = "";
        return;
    }
    const button = document.getElementById("btnEditorialRestore");
    if (button) button.disabled = true;
    try {
        const formData = new FormData();
        formData.append("backup", file);
        const response = await fetch("/api/editorial/restore", { method: "POST", body: formData });
        const payload = await parseJsonResponse(response, "Restauração editorial");
        if (!response.ok || !payload.success) throw new Error(payload.error || "Não foi possível restaurar o backup");
        renderEditorialData(payload.summary || {});
        showToast("Dados editoriais restaurados. O backup anterior foi preservado automaticamente.", "success");
        await loadOperationDashboard();
        await checkRepositorySync(false);
    } catch (error) {
        showToast(error.message || "Não foi possível restaurar o backup", "error");
    } finally {
        input.value = "";
        if (button) button.disabled = false;
    }
}

function renderCampaignHubLocalStatus(payload) {
    const element = document.getElementById("campaignHubLocalStatus");
    if (!element) return;
    const dot = element.querySelector(".status-dot");
    const label = element.querySelector("span:last-child");
    const previous = state.campaignHubSnapshotStatus;
    state.campaignHubSnapshotStatus = payload || null;
    if (!payload?.available) {
        if (dot) dot.className = `status-dot ${payload?.status === "invalid" ? "warning" : "offline"}`;
        if (label) label.textContent = payload?.message || "Sem snapshot editorial local";
        element.title = "O Furia funciona offline, mas não recebeu memória editorial local.";
        return;
    }
    const changed = Boolean(previous?.modified_at && payload.modified_at && previous.modified_at !== payload.modified_at);
    if (dot) dot.className = `status-dot ${changed ? "warning" : "online"}`;
    const accountCount = Object.keys(payload.accounts || {}).length;
    if (label) label.textContent = changed
        ? `Novo snapshot detectado · ${accountCount} perfil(is) · será usado no próximo corte`
        : `Memória local pronta · ${accountCount} perfil(is) · somente leitura`;
    element.title = `${payload.version || "Snapshot editorial"}${payload.modified_at ? ` · atualizado em ${new Date(payload.modified_at).toLocaleString("pt-BR")}` : ""}. O próximo job relê o arquivo automaticamente.`;
}

async function loadCampaignHubLocalStatus() {
    try {
        const response = await fetch("/api/campaign-hub/status", { cache: "no-store" });
        const payload = await parseJsonResponse(response, "Status da memória editorial");
        renderCampaignHubLocalStatus(payload);
        return payload;
    } catch (error) {
        renderCampaignHubLocalStatus({ available: false, status: "error", message: "Memória editorial local indisponível agora" });
        return null;
    }
}

function startCampaignHubLocalStatusPolling() {
    loadCampaignHubLocalStatus();
    if (state.campaignHubStatusTimer) window.clearInterval(state.campaignHubStatusTimer);
    state.campaignHubStatusTimer = window.setInterval(loadCampaignHubLocalStatus, 60000);
}

function setRepositorySyncStatus(message, level = "info") {
    const element = document.getElementById("repositorySyncStatus");
    if (!element) return;
    element.textContent = message;
    element.dataset.level = level;
}

function syncRepositoryRestoreAvailability() {
    const button = document.getElementById("btnRepositoryRestoreFeedback");
    if (!button) return;
    if (state.repositorySyncBusy) {
        button.disabled = true;
        return;
    }
    const payload = state.repositorySync || {};
    const available = safeBooleanFlag(payload.feedback_snapshot_present) && safeBooleanFlag(payload.feedback_snapshot_valid);
    button.disabled = !available;
    button.title = available
        ? "Reconciliar no banco local as decisões finais existentes no snapshot deste checkout"
        : (payload.feedback_snapshot_present
            ? "O snapshot local não passou na validação; envie um snapshot válido antes de restaurar"
            : "Nenhum snapshot válido neste checkout; use “Enviar feedback ao GitHub” em outro notebook primeiro");
}

function setRepositorySyncButtonsDisabled(disabled) {
    ["btnRepositoryCheck", "btnRepositoryUpdate", "btnRepositoryPushFeedback", "btnRepositoryRestoreFeedback"].forEach((id) => {
        const button = document.getElementById(id);
        if (button) button.disabled = disabled;
    });
    if (!disabled) syncRepositoryRestoreAvailability();
}

async function fetchRepositoryJson(url, options = {}, timeoutMs = 15000) {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
    try {
        return await fetch(url, { ...options, signal: controller.signal });
    } catch (error) {
        if (error?.name === "AbortError") {
            throw new Error("A verificação demorou mais de 15 segundos. O servidor local ou o Git pode estar ocupado; tente novamente.");
        }
        throw error;
    } finally {
        window.clearTimeout(timeout);
    }
}

function renderRepositorySyncState(payload) {
    const snapshotPath = String(payload.feedback_snapshot_path || "data/editorial_feedback_snapshot.json");
    const codeDirty = Array.isArray(payload.code_dirty_files)
        ? payload.code_dirty_files
        : (payload.dirty_files || []).filter((item) => item !== snapshotPath);
    const snapshotPresent = safeBooleanFlag(payload.feedback_snapshot_present);
    const snapshotValid = safeBooleanFlag(payload.feedback_snapshot_valid);
    const snapshotRecords = safeNonNegativeCount(payload.feedback_snapshot_records);
    const invalidSnapshotRecords = safeNonNegativeCount(payload.feedback_snapshot_invalid_records);
    const snapshotLabel = snapshotPresent
        ? (snapshotValid
            ? `${snapshotRecords} decisão(ões) no snapshot`
            : invalidSnapshotRecords
                ? `snapshot inválido: ${invalidSnapshotRecords} registro(s) precisam ser revisados`
                : "snapshot inválido; revisão necessária")
        : "snapshot ainda não criado";
    syncRepositoryRestoreAvailability();
    if (payload.update_available) {
        setRepositorySyncStatus(`Código novo disponível na branch ${payload.branch}. Faça backup e use “Atualizar programa”. · ${snapshotLabel}`, "warning");
    } else if (codeDirty.length) {
        setRepositorySyncStatus(`Atualização bloqueada: há ${codeDirty.length} alteração(ões) locais de código. Faça backup ou preserve-as antes. · ${snapshotLabel}`, "warning");
    } else if (payload.feedback_snapshot_dirty) {
        setRepositorySyncStatus(`Feedback local pendente de envio. Use “Enviar feedback ao GitHub”; ele não bloqueia a atualização do código. · ${snapshotLabel}`, "info");
    } else {
        setRepositorySyncStatus(`Código sincronizado · ${String(payload.local_sha || "local").slice(0, 7)} · ${snapshotLabel}`, snapshotPresent && !snapshotValid ? "warning" : "success");
    }
}

async function checkRepositorySync(fetchRemote = true) {
    setRepositorySyncStatus(fetchRemote ? "Consultando o GitHub…" : "Lendo o estado local…", "info");
    try {
        const response = await fetchRepositoryJson(`/api/repository/status?fetch=${fetchRemote ? "1" : "0"}`);
        const payload = await parseJsonResponse(response, "Estado da atualização");
        if (!response.ok || payload.success === false) throw new Error(payload.error || "Não foi possível verificar o programa");
        state.repositorySync = payload;
        renderRepositorySyncState(payload);
        return payload;
    } catch (error) {
        setRepositorySyncStatus(error.message || "Não foi possível verificar a atualização.", "error");
        return null;
    }
}

async function runRepositorySync(action) {
    if (state.repositorySyncBusy) return;
    state.repositorySyncBusy = true;
    setRepositorySyncButtonsDisabled(true);
    try {
        if (action === "update") {
            setRepositorySyncStatus("Criando backup de segurança e baixando a atualização...", "info");
        } else if (action === "push_feedback") {
            setRepositorySyncStatus("Preparando somente o snapshot sanitizado de feedback...", "info");
        } else if (action === "restore_feedback") {
            setRepositorySyncStatus("Validando o snapshot e reconciliando decisões neste notebook...", "info");
        }
        const response = await fetchRepositoryJson("/api/repository/sync", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action }),
        }, action === "update" ? 90000 : 30000);
        const payload = await parseJsonResponse(response, "Sincronização do programa");
        if (!response.ok || payload.success === false) throw new Error(payload.error || "A sincronização não foi concluída");
        state.repositorySync = payload;
        // Keep the detailed state rendered above: it distinguishes code freshness,
        // local code changes, and feedback pending instead of hiding it behind a
        // generic success message. Restore refreshes the local status below because
        // its response is a reconciliation summary, not a repository-status payload.
        if (action !== "restore_feedback") renderRepositorySyncState(payload);
        if (action === "update" && payload.updated) {
            showToast("Atualização aplicada. Feche e abra o run.bat novamente para carregar o novo código.", "success");
            addConsoleLog("[Sincronização] Código atualizado por fast-forward; backup de segurança preservado.", "success");
        } else if (action === "push_feedback") {
            showToast(payload.published ? "Feedback sanitizado sincronizado no GitHub." : "Feedback já estava sincronizado.", "success");
            addConsoleLog("[Sincronização] Nenhum vídeo, transcrição ou chave foi enviado; somente decisões editoriais agregadas.", "info");
        } else if (action === "restore_feedback") {
            const imported = Number(payload.imported || 0);
            const current = Number(payload.already_current || 0);
            const unmatched = Number(payload.unmatched || 0);
            const stale = Number(payload.skipped_older || 0);
            const invalid = Number(payload.invalid || 0);
            const restoreDetails = [
                stale ? `${stale} decisão(ões) local(is) mais nova(s)` : "",
                unmatched ? `${unmatched} sem correspondência` : "",
                invalid ? `${invalid} inválido(s) ignorado(s)` : "",
            ].filter(Boolean).join(" · ");
            const restoreLevel = invalid || unmatched ? "warning" : "success";
            showToast(`Feedback reconciliado: ${imported} importado(s), ${current} já atual(is)${restoreDetails ? ` · ${restoreDetails}` : ""}.`, restoreLevel);
            addConsoleLog(`[Sincronização] Snapshot sanitizado reconciliado: ${imported} importado(s), ${current} já atual(is), ${stale} antigo(s), ${unmatched} sem correspondência, ${invalid} inválido(s) ignorado(s).`, invalid ? "warning" : "info");
            await refreshVisibleReviewState();
            await loadProjectLibrary();
            await loadEditorialLearning();
            await loadDailyEditorialGoal();
            await loadEditorialData();
            await checkRepositorySync(false);
        }
        return payload;
    } catch (error) {
        setRepositorySyncStatus(error.message || "Sincronização não concluída.", "error");
        showToast(error.message || "Sincronização não concluída.", "error");
        return null;
    } finally {
        state.repositorySyncBusy = false;
        setRepositorySyncButtonsDisabled(false);
    }
}

async function recoverLegacyOperation() {
    try {
        const response = await fetch("/api/process/status");
        const payload = await parseJsonResponse(response, "Estado da operação");
        if (!response.ok) throw new Error(payload.error || "Não foi possível recuperar a operação");
        const operation = String(payload.operation || "");
        const sourceImportRecovery = payload.operation === "source_import" && payload.job_id;
        const operationMessages = {
            source_import: "Importação de fonte ainda em andamento; aguardando a conclusão do download e da transcrição.",
            silence: "Remoção de silêncio ainda em andamento; aguardando o encerramento seguro.",
            transcription: "Transcrição ainda em andamento; aguardando o arquivo persistente.",
            subtitles: "Geração de legendas ainda em andamento; aguardando o arquivo final.",
            thumbnail: "Geração de thumbnail ainda em andamento; aguardando o arquivo final.",
            seo: "Operação editorial legada ainda em andamento; aguardando o encerramento.",
        };
        if (payload.active && payload.job_id) {
            const message = operationMessages[operation] || "Operação ainda em andamento; aguardando o encerramento seguro.";
            const recoveredJobId = String(payload.job_id);
            const existingJobId = String(state.activeJob?.id || "");
            const existingJobState = String(state.activeJob?.state || "");
            const persistentJobAlreadyActive = Boolean(
                existingJobId
                && !existingJobId.startsWith("legacy-")
                && ["queued", "running", "cancel_requested"].includes(existingJobState)
                && existingJobId !== recoveredJobId
            );
            if (persistentJobAlreadyActive) {
                addConsoleLog("[Operação] Uma operação persistente já está ativa; a recuperação legada não substituirá sua HUD.", "warning");
                return;
            }
            state.activeJob = {
                id: String(payload.job_id),
                state: "running",
                stage: operation,
                message,
            };
            showProgressBar();
            showProcessingControls(`[Job ${String(payload.job_id).slice(0, 8)}] ${message}`);
            if (operation === "source_import") {
                state.sourceImportJobId = String(payload.job_id);
                setSourceImportBusy(true);
                showSourceStatus(message, "");
            } else {
                addConsoleLog(`[Operação] ${message}`, "info");
            }
            return;
        }
        if (!payload.active) {
            const legacyOperations = new Set(["source_import", "silence", "transcription", "subtitles", "thumbnail", "seo"]);
            const activeJobId = String(state.activeJob?.id || "");
            const activeJobStage = String(state.activeJob?.stage || "");
            const staleLegacyJob = Boolean(
                state.activeJob
                && (activeJobId.startsWith("legacy-") || legacyOperations.has(activeJobStage))
                && ["queued", "running", "cancel_requested"].includes(String(state.activeJob.state || ""))
            );
            if (staleLegacyJob) {
                state.activeJob = null;
                hideProgressBar();
                addConsoleLog("[Operação] O servidor já encerrou a operação durante a desconexão; a HUD foi sincronizada com segurança.", "info");
            }
            if (state.sourceImportActive) {
                setSourceImportBusy(false);
                state.sourceImportJobId = "";
                state.sourceImportInitialVideoPath = "";
            }
        }
    } catch (error) {
        addConsoleLog(`[Operação] Recuperação do estado indisponível: ${error.message}`, "warning");
    }
}

async function loadOperationDashboard() {
    if (state.operationDashboardLoading) return;
    state.operationDashboardLoading = true;
    try {
        const response = await fetch("/api/jobs?limit=12");
        const payload = await parseJsonResponse(response, "Histórico de operações");
        if (!response.ok) throw new Error(payload.error || "Não foi possível carregar os jobs");
        state.operationJobs = Array.isArray(payload.jobs) ? payload.jobs : [];
        await recoverLegacyOperation();
        renderOperationDashboard();
        loadEditorialLearning();
        loadEditorialData();
        loadDailyEditorialGoal();
        loadProjectLibrary();
        loadTranscriptArchive();
        const active = state.operationJobs.find((job) => ["queued", "running", "cancel_requested"].includes(job.state));
        if (active) handleJobUpdate(active, { refreshDashboard: false });
    } catch (error) {
        const subtitle = document.getElementById("operationSubtitle");
        if (subtitle) subtitle.textContent = "Não foi possível carregar o histórico local agora.";
    } finally {
        state.operationDashboardLoading = false;
    }
}

checkRepositorySync(false);

function formatJobStageTiming(job = {}) {
    const stage = String(job.stage || "").trim();
    if (!stage) return "";
    const startedAt = Date.parse(String(job.stage_started_at || job.updated_at || ""));
    if (!Number.isFinite(startedAt)) return "";
    const elapsed = Math.max(0, (Date.now() - startedAt) / 1000);
    if (elapsed < 1) return "";
    const value = elapsed < 10 ? elapsed.toFixed(1) : Math.round(elapsed).toString();
    return ` · ${value}s nesta etapa`;
}

function handleJobUpdate(job, options = {}) {
    const currentJob = state.activeJob;
    const activeStates = ["queued", "running", "cancel_requested"];
    const staleConcurrentJob = Boolean(
        currentJob?.id
        && job?.id
        && currentJob.id !== job.id
        && activeStates.includes(currentJob.state)
    );
    const existingIndex = (state.operationJobs || []).findIndex((item) => item.id === job.id);
    if (existingIndex >= 0) state.operationJobs[existingIndex] = job;
    else state.operationJobs = [job, ...(state.operationJobs || [])];
    renderOperationDashboard();
    if (staleConcurrentJob) {
        return;
    }
    const sourceImportOwnsHud = Boolean(
        state.sourceImportActive
        && state.sourceImportJobId
        && String(state.sourceImportJobId) !== String(job?.id || "")
    );
    if (sourceImportOwnsHud) return;
    state.activeJob = job;
    if (["queued", "running", "cancel_requested"].includes(job.state)) state.progressSuppressed = false;
    if (options.refreshDashboard !== false) window.clearTimeout(state.operationRefreshTimer);
    if (options.refreshDashboard !== false) {
        state.operationRefreshTimer = window.setTimeout(loadOperationDashboard, 1200);
    }
    const container = document.getElementById("progressBarContainer");
    const bar = document.getElementById("progressBar");
    if (container && bar && ["queued", "running", "cancel_requested"].includes(job.state)) {
        container.style.display = "block";
        bar.dataset.animating = "false";
        bar.style.width = `${Math.max(2, Math.min(100, job.progress || 0))}%`;
        const consoleKey = `${job.id}:${job.state}:${job.stage || ""}:${job.message || ""}:${Math.round(Number(job.progress || 0))}`;
        if (state.lastJobConsoleKey !== consoleKey) {
            state.lastJobConsoleKey = consoleKey;
            addConsoleLog(`[Job ${job.id.slice(0, 8)}] ${job.message || job.stage || job.state}`, "info");
        }
    }
    if (["queued", "running", "cancel_requested"].includes(job.state)) {
        const timing = formatJobStageTiming(job);
        showProcessingControls(
            job.state === "cancel_requested"
                ? `[Job ${job.id.slice(0, 8)}] Parada solicitada; aguardando encerramento seguro${timing}`
                : `[Job ${job.id.slice(0, 8)}] ${job.message || job.stage || "Processando"}${timing}`,
            { cancelRequested: job.state === "cancel_requested" },
        );
    }
    if (job.state === "completed") {
        if (bar) bar.style.width = "100%";
        setTimeout(hideProgressBar, 250);
    } else if (job.state === "failed") {
        hideProgressBar();
        hideProcessingControls();
        updateWorkspaceWorkflow("source", "Atenção necessária");
        const failureMessage = String(job.error || job.message || "O job falhou").trim().slice(0, 360);
        addConsoleLog(`[Job ${String(job.id || "").slice(0, 8)}] Falha${job.stage ? ` em ${job.stage}` : ""}: ${failureMessage}`, "error");
        showToast(failureMessage || "O job falhou", "error");
    } else if (job.state === "cancelled") {
        hideProgressBar();
        hideProcessingControls();
        updateWorkspaceWorkflow("source", "Operação pausada");
        addConsoleLog(`[Job ${String(job.id || "").slice(0, 8)}] Operação cancelada com segurança.`, "warning");
        showToast("Processamento cancelado com segurança", "warning");
    }
}

async function recoverActiveJobs() {
    await loadOperationDashboard();
}

function hideProgressBar() {
    state.progressSuppressed = true;
    if (state.progressHideTimer) window.clearTimeout(state.progressHideTimer);
    hideProcessingControls();
    const container = document.getElementById("progressBarContainer");
    const bar = document.getElementById("progressBar");
    bar.style.width = "100%";
    if (bar.dataset.interval) {
        clearInterval(parseInt(bar.dataset.interval));
        bar.dataset.animating = "";
    }
    state.progressHideTimer = window.setTimeout(() => {
        state.progressHideTimer = null;
        const activeJobState = String(state.activeJob?.state || "");
        const jobStillActive = ["queued", "running", "cancel_requested"].includes(activeJobState) || state.sourceImportActive;
        if (jobStillActive) {
            state.progressSuppressed = false;
            return;
        }
        container.style.display = "none";
        bar.style.width = "0%";
    }, 1000);
}

// ─── Media Library ───

async function loadMediaFiles() {
    try {
        const res = await fetch("/api/files?path=uploads");
        const data = await res.json();
        state.mediaFiles = data.items.filter(f => f.is_video);
        renderMediaLibrary();
    } catch (e) {
        addConsoleLog(`[Erro] Falha ao carregar midias: ${e.message}`, "error");
    }
}

function renderMediaLibrary() {
    const grid = document.getElementById("mediaGrid");
    const dropZone = document.getElementById("mediaDropZone");

    if (state.mediaFiles.length === 0) {
        grid.style.display = "none";
        dropZone.style.display = "flex";
        return;
    }

    dropZone.style.display = "none";
    grid.style.display = "grid";
    grid.innerHTML = "";

    state.mediaFiles.forEach(file => {
        const card = document.createElement("div");
        card.className = "media-card" + (state.selectedVideo === file.path ? " selected" : "");
        card.innerHTML = `
            <div class="media-thumb">
                <video preload="metadata" muted>
                    <source src="/workspace/${file.path}" type="video/mp4">
                </video>
                <div class="media-play-overlay">
                    <span class="material-icons-round">play_circle_filled</span>
                </div>
                <div class="media-duration">${file.size_human}</div>
                <button class="media-delete-btn" title="Excluir video" data-path="${file.path}">
                    <span class="material-icons-round">delete</span>
                </button>
            </div>
            <div class="media-info">
                <span class="media-name" title="${file.name}">${truncateName(file.name, 30)}</span>
            </div>
        `;

        card.addEventListener("click", (e) => {
            if (e.target.closest(".media-delete-btn")) return;
            selectVideo(file, card);
        });

        const deleteBtn = card.querySelector(".media-delete-btn");
        deleteBtn.addEventListener("click", async (e) => {
            e.stopPropagation();
            if (!confirm(`Excluir "${file.name}"?`)) return;
            await deleteMediaFile(file);
        });

        grid.appendChild(card);
    });
}

async function deleteMediaFile(file) {
    try {
        const res = await fetch("/api/files/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: file.path }),
        });
        const data = await res.json();
        if (data.success) {
            showToast(`"${file.name}" excluido!`, "success");
            if (state.selectedVideo === file.path) {
                deselectVideo();
            }
            await loadMediaFiles();
        } else {
            showToast(data.error || "Erro ao excluir", "error");
        }
    } catch (e) {
        showToast("Erro ao excluir arquivo", "error");
    }
}

function truncateName(name, max) {
    if (name.length <= max) return name;
    const ext = name.split('.').pop();
    return name.substring(0, max - ext.length - 4) + "..." + ext;
}

// ─── Video Selection & Preview ───

function selectVideo(item, sourceElement = null) {
    if (!item || !item.path) {
        showToast("Não foi possível selecionar este vídeo: caminho inválido.", "error");
        return;
    }
    const changedVideo = state.selectedVideo && !mediaPathsMatch(state.selectedVideo, item.path);
    const transcriptBelongsToItem = state.manualTranscript && (
        mediaPathsMatch(state.manualTranscriptVideo, item.path) || state.manualTranscriptVideo === "pending-source"
    );
    const transcriptToRestore = transcriptBelongsToItem ? state.manualTranscript : null;
    const transcriptArchiveToRestore = transcriptBelongsToItem
        ? (state.transcriptArchive || state.manualTranscript?.archive || state.manualTranscript?.archive_metadata || null)
        : null;
    state.selectedVideo = item.path;
    state.selectedVideoName = item.name;
    if (transcriptBelongsToItem && state.manualTranscriptVideo === "pending-source") {
        state.manualTranscriptVideo = item.path;
    }
    if (changedVideo) {
        resetReviewWorkspaceForVideoChange();
        state.editorialContext = null;
        const contextResult = document.getElementById("contextAnalysisResult");
        if (contextResult) {
            contextResult.hidden = true;
            contextResult.innerHTML = "";
        }
        const contextStatus = document.getElementById("contextAnalysisStatus");
        if (contextStatus) contextStatus.textContent = "Vídeo alterado. Execute uma nova análise de contexto para esta fonte.";
        renderEditorialAudit(null);
    }
    if (transcriptBelongsToItem) {
        hydrateTranscriptEditor(transcriptToRestore, transcriptArchiveToRestore);
    }
    if (!transcriptBelongsToItem) {
        state.manualTranscript = null;
        state.manualTranscriptVideo = "";
        state.transcriptArchive = null;
        const input = document.getElementById("manualTranscriptInput");
        if (input) input.value = "";
        const status = document.getElementById("transcriptStatus");
        if (status) {
            status.textContent = "Nenhuma transcrição manual carregada para este vídeo.";
            status.className = "source-status";
        }
    }

    // Update sidebar info
    const info = document.getElementById("selectedVideoInfo");
    info.className = "selected-video has-video";
    info.innerHTML = `
        <div class="video-info-selected">
            <span class="material-icons-round" style="color:var(--gold);font-size:20px">movie</span>
            <div>
                <span class="video-name">${truncateName(item.name, 25)}</span>
                <span class="video-meta">${item.size_human}</span>
            </div>
            <button class="btn btn-sm btn-outline" onclick="openOutputFolderForVideo()" title="Abrir pasta do vídeo">
                <span class="material-icons-round" style="font-size:14px">folder_open</span>
            </button>
            <button class="btn btn-sm btn-deselect" onclick="deselectVideo()" title="Remover selecao">
                <span class="material-icons-round" style="font-size:14px">close</span>
            </button>
        </div>`;

    // Update media grid selection
    document.querySelectorAll(".media-card").forEach(el => el.classList.remove("selected"));
    if (sourceElement?.classList) sourceElement.classList.add("selected");

    // Show video preview
        showVideoPreview(item);
    if (changedVideo && state.activeJob && ["queued", "running", "cancel_requested"].includes(state.activeJob.state)) {
        const jobLabel = String(state.activeJob.id || "").slice(0, 8);
        const previousOperationMessage = state.activeJob.state === "cancel_requested"
            ? "Parada da operação anterior aguardando encerramento seguro."
            : "A operação anterior continua; Parar cancela o job anterior, não o vídeo novo.";
        showProcessingControls(`[Job ${jobLabel}] ${previousOperationMessage}`, { cancelRequested: state.activeJob.state === "cancel_requested" });
        addConsoleLog("[Sistema] A nova seleção foi liberada; a tarefa anterior continua vinculada ao vídeo anterior.", "info");
    }
    addConsoleLog(`[Sistema] Video selecionado: ${item.name}`, "info");
    showToast(`Video selecionado: ${truncateName(item.name, 30)}`, "success");
}

async function openOutputFolderForVideo() {
    const videoPath = typeof state.selectedVideo === "string" ? state.selectedVideo : state.selectedVideo?.path;
    if (!videoPath) {
        showToast("Nenhum vídeo selecionado.", "warning");
        return;
    }
    const normalized = String(videoPath).replaceAll("\\", "/").replace(/\/+$/, "");
    const separator = normalized.lastIndexOf("/");
    let folderPath = separator >= 0 ? normalized.slice(0, separator) : "";
    if (/^[A-Za-z]:$/.test(folderPath)) folderPath += "/";
    if (!folderPath) {
        showToast("A pasta deste vídeo não pôde ser identificada.", "warning");
        return;
    }
    await openOutputFolder(folderPath);
}
function showVideoPreview(item) {
    const section = document.getElementById("videoPreviewSection");
    const video = document.getElementById("videoPreview");
    const source = document.getElementById("videoPreviewSource");
    const nameEl = document.getElementById("previewVideoName");
    const status = document.getElementById("videoPreviewStatus");
    if (!section || !video || !source || !item?.path) return;
    const token = ++state.previewToken;
    section.style.display = "block";
    nameEl.textContent = item.name || "Vídeo selecionado";
    if (status) {
        status.textContent = "Carregando mídia…";
        status.className = "preview-status loading";
    }
    video.pause();
    video.removeAttribute("src");
    source.removeAttribute("src");
    video.load();
    const onMetadata = () => {
        if (token !== state.previewToken) return;
        const duration = Number.isFinite(video.duration) ? formatTime(video.duration) : "—";
        const resolution = video.videoWidth && video.videoHeight ? `${video.videoWidth}x${video.videoHeight}` : "—";
        document.getElementById("videoDuration").textContent = `Duração: ${duration}`;
        document.getElementById("videoResolution").textContent = `Resolução: ${resolution}`;
        if (status) {
            status.textContent = "Mídia pronta";
            status.className = "preview-status ready";
        }
    };
    const onError = () => {
        if (token !== state.previewToken) return;
        if (status) {
            status.textContent = "Não foi possível carregar este arquivo";
            status.className = "preview-status error";
        }
        addConsoleLog(`[Preview] Falha ao carregar ${item.name || "o vídeo"}. Verifique se o arquivo ainda existe e tente selecioná-lo novamente.`, "warning");
    };
    video.addEventListener("loadedmetadata", onMetadata, { once: true });
    video.addEventListener("error", onError, { once: true });
    source.src = mediaUrlForPath(item.path);
    video.load();
}

function clearVideoPreview() {
    state.previewToken += 1;
    const section = document.getElementById("videoPreviewSection");
    const video = document.getElementById("videoPreview");
    const source = document.getElementById("videoPreviewSource");
    if (video) {
        video.pause();
        video.removeAttribute("src");
        video.load();
    }
    if (source) source.removeAttribute("src");
    if (section) section.style.display = "none";
}

function resetReviewWorkspaceForVideoChange() {
    state.contextAnalysisController?.abort();
    state.contextAnalysisController = null;
    state.contextAnalysisToken += 1;
    state.contextAnalysisJobId = "";
    state.contextAnalysisSourcePath = "";
    state.editorialContext = null;
    state.clips = [];
    state.reviewFilter = "all";
    state.reviewSort = "score";
    state.videoLayout = "unknown";
    state.selectionSource = "unknown";
    state.candidateDiagnostics = {};
    state.resultSourceIdentity = "";
    state.outputFolder = "";
    state.currentProjectId = null;
    state.lastReviewAction = null;
    state.transcriptArchive = null;
    resetCampaignSearchPanel();

    const resultsSection = document.getElementById("resultsSection");
    const reviewCenter = document.getElementById("reviewCommandCenter");
    const resultsGrid = document.getElementById("resultsGrid");
    const transcriptSearchBar = document.getElementById("transcriptSearchBar");
    const transcriptSearchInput = document.getElementById("transcriptSearchInput");
    const searchCount = document.getElementById("searchCount");
    const clearSearch = document.getElementById("btnClearSearch");
    const resultsSummary = document.getElementById("resultsSummary");
    const resultModeBadge = document.getElementById("resultModeBadge");
    const audit = document.getElementById("editorialAuditSummary");
    const candidateNotice = document.getElementById("candidateVolumeNotice");
    const archiveList = document.getElementById("transcriptArchiveList");
    const openFolder = document.getElementById("btnOpenFolder");
    const contextResult = document.getElementById("contextAnalysisResult");
    const contextStatus = document.getElementById("contextAnalysisStatus");

    if (resultsSection) resultsSection.style.display = "none";
    if (reviewCenter) reviewCenter.style.display = "none";
    if (resultsGrid) resultsGrid.innerHTML = "";
    if (transcriptSearchBar) transcriptSearchBar.style.display = "none";
    if (transcriptSearchInput) transcriptSearchInput.value = "";
    if (searchCount) searchCount.textContent = "";
    if (clearSearch) clearSearch.style.display = "none";
    if (resultsSummary) resultsSummary.textContent = "";
    if (resultModeBadge) resultModeBadge.textContent = "";
    if (audit) {
        audit.innerHTML = "";
        audit.style.display = "none";
    }
    if (candidateNotice) {
        candidateNotice.innerHTML = "";
        candidateNotice.hidden = true;
    }
    if (archiveList) {
        archiveList.innerHTML = "";
        archiveList.hidden = true;
    }
    if (openFolder) openFolder.style.display = "none";
    if (contextResult) {
        contextResult.hidden = true;
        contextResult.innerHTML = "";
    }
    if (contextStatus) contextStatus.textContent = "Selecione um vídeo para analisar o contexto antes do corte.";
    renderEditorialAudit(null);
    closeContextReview();
}

function deselectVideo() {
    const keepPendingTranscript = state.manualTranscriptVideo === "pending-source";
    resetReviewWorkspaceForVideoChange();
    state.selectedVideo = null;
    state.selectedVideoName = "";
    state.editorialContext = null;
    if (!keepPendingTranscript) {
        state.manualTranscript = null;
        state.manualTranscriptVideo = "";
        state.transcriptArchive = null;
        const transcriptInput = document.getElementById("manualTranscriptInput");
        if (transcriptInput) transcriptInput.value = "";
        const transcriptStatus = document.getElementById("transcriptStatus");
        if (transcriptStatus) {
            transcriptStatus.textContent = "Nenhuma transcrição manual carregada para um vídeo selecionado.";
            transcriptStatus.className = "source-status";
        }
    }
    const contextResult = document.getElementById("contextAnalysisResult");
    if (contextResult) {
        contextResult.hidden = true;
        contextResult.innerHTML = "";
    }
    const contextStatus = document.getElementById("contextAnalysisStatus");
    if (contextStatus) contextStatus.textContent = "Selecione um vídeo para analisar o contexto antes do corte.";
    document.querySelectorAll(".media-card").forEach(el => el.classList.remove("selected"));

    const info = document.getElementById("selectedVideoInfo");
    info.className = "selected-video";
    info.innerHTML = `
        <div class="no-video">
            <span class="material-icons-round">videocam_off</span>
            <p>Nenhum video selecionado</p>
        </div>`;

    // Hide and invalidate preview so an old media event cannot repaint this state.
    clearVideoPreview();
}

// ─── File Upload ───

document.getElementById("btnImportMedia").addEventListener("click", () => {
    document.getElementById("fileInput").click();
});

document.getElementById("fileInput").addEventListener("change", async (e) => {
    const files = e.target.files;
    if (!files.length) return;

    for (const file of files) {
        await uploadFile(file);
    }
    await loadMediaFiles();

    // Auto-select the first uploaded file
    if (state.mediaFiles.length > 0 && !state.selectedVideo) {
        const lastFile = state.mediaFiles[state.mediaFiles.length - 1];
        // Simulate click on last uploaded media card
        setTimeout(() => {
            const cards = document.querySelectorAll(".media-card");
            if (cards.length > 0) {
                cards[cards.length - 1].click();
            }
        }, 100);
    }

    e.target.value = "";
});

async function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("path", "uploads");

    addConsoleLog(`[Upload] Enviando ${file.name}...`, "info");
    showToast(`Importando ${file.name}...`, "info");

    try {
        const res = await fetch("/api/files/upload", {
            method: "POST",
            body: formData,
        });
        const data = await res.json();
        if (data.success) {
            addConsoleLog(`[Upload] ${file.name} importado com sucesso!`, "success");
            showToast(`${file.name} importado!`, "success");
        } else {
            addConsoleLog(`[Upload] Erro: ${data.error}`, "error");
            showToast(data.error, "error");
        }
    } catch (e) {
        addConsoleLog(`[Upload] Erro: ${e.message}`, "error");
        showToast("Erro ao importar arquivo", "error");
    }
}

function isArtworkTranscriptFile(file) {
    return Boolean(file?.name && /\.(txt|srt|vtt)$/i.test(file.name));
}

function isVideoFile(file) {
    return Boolean(file?.name && /\.(mp4|mkv|avi|mov|webm|flv|wmv|m4v|mpeg|mpg)$/i.test(file.name));
}

async function selectLastImportedMedia(force = false) {
    await loadMediaFiles();
    setTimeout(() => {
        const cards = document.querySelectorAll(".media-card");
        if (cards.length > 0 && (force || !state.selectedVideo)) cards[cards.length - 1].click();
    }, 100);
}

async function importArtworkTranscriptFile(file) {
    if (!file || !isArtworkTranscriptFile(file)) return false;
    try {
        const text = await file.text();
        const input = document.getElementById("artworkTranscriptInput");
        if (!input || !text.trim()) throw new Error("o arquivo está vazio");
        input.value = text;
        document.getElementById("headlineStudioSection")?.scrollIntoView({ behavior: "smooth", block: "start" });
        setHeadlineStudioStatus(`${file.name} importado automaticamente. Revise a transcrição e escolha o formato antes de gerar.`, "success");
        addConsoleLog(`[Estúdio] ${file.name} importado por arrastar e soltar.`, "success");
        showToast("Transcrição importada no Estúdio de Texto de Arte.", "success");
        return true;
    } catch (error) {
        setHeadlineStudioStatus(`Não foi possível importar ${file.name}: ${error.message}`, "error");
        showToast("Falha ao importar a legenda.", "error");
        return false;
    }
}

const artworkTranscriptDropTarget = document.getElementById("artworkTranscriptDropTarget");
if (artworkTranscriptDropTarget) {
    artworkTranscriptDropTarget.addEventListener("dragover", (event) => {
        event.preventDefault();
        event.stopPropagation();
        artworkTranscriptDropTarget.classList.add("drag-over");
        if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
    });
    artworkTranscriptDropTarget.addEventListener("dragleave", (event) => {
        if (!artworkTranscriptDropTarget.contains(event.relatedTarget)) artworkTranscriptDropTarget.classList.remove("drag-over");
    });
    artworkTranscriptDropTarget.addEventListener("drop", async (event) => {
        event.preventDefault();
        event.stopPropagation();
        artworkTranscriptDropTarget.classList.remove("drag-over");
        const files = Array.from(event.dataTransfer?.files || []);
        const transcript = files.find(isArtworkTranscriptFile);
        const video = files.find(isVideoFile);
        if (transcript) await importArtworkTranscriptFile(transcript);
        if (video) {
            setHeadlineStudioStatus(`${video.name} será importado na Biblioteca de mídia.`, "info");
            await uploadFile(video);
            await selectLastImportedMedia(true);
            setHeadlineStudioStatus(`${video.name} importado. A transcrição do corte pode ser usada no Estúdio quando estiver disponível.`, "success");
        }
        if (!transcript && !video && files.length) {
            setHeadlineStudioStatus("Solte um TXT, SRT, VTT ou vídeo nesta área.", "warning");
        }
    });
}

// Drag and drop on media library: vídeos são enviados à biblioteca; legendas vão direto ao Estúdio.
const mediaDropZone = document.getElementById("mediaDropZone");
const mediaSection = document.getElementById("mediaLibrarySection");

[mediaDropZone, mediaSection].filter(Boolean).forEach(el => {
    el.addEventListener("dragover", (e) => {
        e.preventDefault();
        mediaDropZone?.classList.add("drag-over");
    });
    el.addEventListener("dragleave", (e) => {
        if (!el.contains(e.relatedTarget)) mediaDropZone?.classList.remove("drag-over");
    });
    el.addEventListener("drop", async (e) => {
        e.preventDefault();
        e.stopPropagation();
        mediaDropZone?.classList.remove("drag-over");
        const files = Array.from(e.dataTransfer?.files || []);
        for (const file of files) {
            if (isArtworkTranscriptFile(file)) await importArtworkTranscriptFile(file);
            else if (isVideoFile(file)) await uploadFile(file);
        }
        if (files.some(isVideoFile)) await selectLastImportedMedia();
    });
});

// ─── Close Preview ───

document.getElementById("btnClosePreview").addEventListener("click", () => {
    clearVideoPreview();
});

// ─── Actions ───

function requireVideo() {
    if (!state.selectedVideo) {
        showToast("Selecione um video primeiro na biblioteca!", "warning");
        return false;
    }
    return true;
}

function transcriptPayloadForSelectedVideo() {
    if (!state.manualTranscript || !state.selectedVideo) return null;
    const linkedPath = String(state.manualTranscriptVideo || "").trim();
    const selectedPath = String(selectedVideoPathForRequest() || "").trim();
    if (!linkedPath || linkedPath === "pending-source" || !mediaPathsMatch(linkedPath, selectedPath)) return null;
    return state.manualTranscript;
}

document.getElementById("actionSilence").querySelector(".btn-action").addEventListener("click", async () => {
    if (!requireVideo()) return;
    addConsoleLog("[Acao] Iniciando remocao de silencio...", "info");
    prepareNewOperationHud();
    showProgressBar();
    try {
        const response = await fetch("/api/process/silence", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ video_path: state.selectedVideo }),
        });
        const started = await parseJsonResponse(response, "Remoção de silêncio");
        if (!response.ok || started.error) throw new Error(started.error || "Não foi possível iniciar a remoção de silêncio");
        registerStartedOperation(started, "Remoção de silêncio em andamento.");
        showProgressBar();
    } catch (error) {
        hideProgressBar();
        showToast(error.message || "Não foi possível iniciar a remoção de silêncio", "error");
    }
});

function openCutOptionsModal() {
    if (!requireVideo()) return;
    const modal = document.getElementById("cutOptionsModal");
    if (!modal) return;
    const name = document.getElementById("cutOptionsVideoName");
    if (name) name.textContent = state.selectedVideoName || "vídeo selecionado";
    const enabled = document.getElementById("faceTrackingEnabled");
    if (enabled) enabled.checked = state.faceTracking !== false;
    modal.classList.add("active");
}
function closeCutOptionsModal() {
    document.getElementById("cutOptionsModal")?.classList.remove("active");
}
async function startSmartCut() {
    closeCutOptionsModal();
    if (!requireVideo()) return;
    state.faceTracking = Boolean(document.getElementById("faceTrackingEnabled")?.checked);
    const userContext = document.getElementById("userContextInput").value.trim();
    const boundTranscript = transcriptPayloadForSelectedVideo();
    const currentVideoPath = selectedVideoPathForRequest();
    const boundEditorialContext = state.editorialContext
        && mediaPathsMatch(state.contextAnalysisSourcePath, currentVideoPath)
        ? state.editorialContext
        : null;
    addConsoleLog("[Acao] Iniciando corte inteligente de shorts...", "info");
    if (boundEditorialContext) {
        addConsoleLog("[Contexto] Dossiê pré-analisado desta fonte será reutilizado no ranking.", "success");
    } else {
        addConsoleLog("[Contexto] Nenhum dossiê pré-analisado está vinculado a esta fonte; o corte seguirá com os sinais disponíveis. Execute Revisar contexto antes de cortar para orientar Q&A, capítulos e payoff.", "warning");
    }
    addConsoleLog(`[Enquadramento] Facetracking ${state.faceTracking ? "ativado" : "desativado"}; o fallback mantém a proporção original quando necessário.`, "info");
    if (userContext) addConsoleLog(`[Contexto] "${userContext}"`, "info");
    const videoGenre = document.getElementById("settingVideoGenre").value;
    const geminiKey = document.getElementById("settingGeminiKey").value.trim();
    const aiBackend = document.getElementById("settingAiBackend").value;
    if (geminiKey.length > 10 || aiBackend) {
        await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                gemini_api_key: geminiKey,
                gemini_model: document.getElementById("settingGeminiModel").value.trim(),
                ai_backend: aiBackend,
            }),
        });
    }
    const response = await fetch("/api/process/cut", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            video_path: state.selectedVideo,
            face_tracking: state.faceTracking,
            user_context: userContext,
            video_genre: videoGenre,
            transcription_source: document.getElementById("settingTranscriptionSource")?.value || "auto",
            audit_mode: document.getElementById("settingAuditMode")?.value || "standard",
            preferred_format: document.getElementById("settingPreferredFormat")?.value || "auto",
            editorial_context_source_path: boundEditorialContext ? currentVideoPath : "",
            ...(boundEditorialContext ? { editorial_context: boundEditorialContext } : {}),
            ...(boundTranscript ? {
                transcript_segments: boundTranscript.segments,
                transcript_language: boundTranscript.language || "pt",
            } : {}),
        }),
    });
    const started = await parseJsonResponse(response, "Corte inteligente");
    if (!response.ok || started.error) throw new Error(started.error || "Não foi possível iniciar o corte");
    registerStartedOperation(started, "Corte adicionado à fila persistente.");
}
document.getElementById("actionCut").querySelector(".btn-action").addEventListener("click", openCutOptionsModal);
document.getElementById("btnStartSmartCut")?.addEventListener("click", startSmartCut);
document.getElementById("btnCloseCutOptions")?.addEventListener("click", closeCutOptionsModal);
document.getElementById("btnCloseCutOptionsSecondary")?.addEventListener("click", closeCutOptionsModal);

document.getElementById("actionArtwork")?.querySelector(".btn-action")?.addEventListener("click", () => {
    document.getElementById("headlineStudioSection")?.scrollIntoView({ behavior: "smooth", block: "start" });
    document.getElementById("artworkTranscriptInput")?.focus({ preventScroll: true });
});

document.getElementById("actionThumbnail").querySelector(".btn-action").addEventListener("click", () => {
    if (!requireVideo()) return;
    openThumbnailModal();
});

document.getElementById("actionComplete").querySelector(".btn-action").addEventListener("click", async () => {
    if (!requireVideo()) return;
    if (!confirm("Executar o pipeline completo? Isso pode demorar alguns minutos dependendo do tamanho do video.")) return;
    const userContext = document.getElementById("userContextInput").value.trim();
    const boundTranscript = transcriptPayloadForSelectedVideo();
    const currentVideoPath = selectedVideoPathForRequest();
    const boundEditorialContext = state.editorialContext
        && mediaPathsMatch(state.contextAnalysisSourcePath, currentVideoPath)
        ? state.editorialContext
        : null;
    addConsoleLog("[Acao] Iniciando processo completo...", "info");
    if (boundEditorialContext) {
        addConsoleLog("[Contexto] Dossiê pré-analisado desta fonte será reutilizado no processo completo.", "success");
    } else {
        addConsoleLog("[Contexto] Nenhum dossiê pré-analisado está vinculado a esta fonte; o processo seguirá com os sinais disponíveis. Execute Revisar contexto antes de iniciar para orientar Q&A, capítulos e payoff.", "warning");
    }
    if (userContext) addConsoleLog(`[Contexto] "${userContext}"`, "info");
    const videoGenreComplete = document.getElementById("settingVideoGenre").value;
    const response = await fetch("/api/process/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            video_path: state.selectedVideo,
            output_dir: state.outputDir || "",
            user_context: userContext,
            video_genre: videoGenreComplete,
            transcription_source: document.getElementById("settingTranscriptionSource")?.value || "auto",
            editorial_context_source_path: boundEditorialContext ? currentVideoPath : "",
            ...(boundEditorialContext ? { editorial_context: boundEditorialContext } : {}),
            ...(boundTranscript ? {
                transcript_segments: boundTranscript.segments,
                transcript_language: boundTranscript.language || "pt",
            } : {}),
        }),
    });
    const started = await parseJsonResponse(response, "Processo completo");
    if (!response.ok || started.error) throw new Error(started.error || "Não foi possível iniciar o processo completo");
    registerStartedOperation(started, "Processo completo adicionado à fila persistente.");
});

// ─── Subtitle Modal ───

function openSubtitleModal() {
    if (!requireVideo()) return;
    document.getElementById("subtitleModal").classList.add("active");
    updateSubtitlePreview();
}

function closeSubtitleModal() {
    document.getElementById("subtitleModal").classList.remove("active");
}

function updateSubtitlePreview() {
    const preview = document.getElementById("subtitlePreview");
    const textColor = document.getElementById("subTextColor").value;
    const highlightColor = document.getElementById("subHighlightColor").value;
    const borderColor = document.getElementById("subBorderColor").value;
    const fontSize = document.getElementById("subFontSize").value;
    const position = document.getElementById("subPosition").value;

    preview.innerHTML = `
        <div style="width:100%; height:100%; display:flex; align-items:${position === 'bottom' ? 'flex-end' : 'flex-start'};
                    justify-content:center; padding:16px; background:#111; border-radius:8px;">
            <div style="text-align:center;">
                <span style="color:${textColor}; font-size:${Math.max(12, fontSize * 0.6)}px; font-weight:700;
                             text-shadow: -1px -1px 0 ${borderColor}, 1px -1px 0 ${borderColor},
                                          -1px 1px 0 ${borderColor}, 1px 1px 0 ${borderColor};">
                    Exemplo de </span><span style="color:${highlightColor}; font-size:${Math.max(14, fontSize * 0.65)}px;
                    font-weight:800; text-shadow: -2px -2px 0 ${borderColor}, 2px -2px 0 ${borderColor},
                    -2px 2px 0 ${borderColor}, 2px 2px 0 ${borderColor};">legenda</span>
            </div>
        </div>`;
}

async function generateSubtitles() {
    if (!requireVideo()) return;
    closeSubtitleModal();

    const subtitleSettings = {
        subtitle_color: document.getElementById("subTextColor").value,
        subtitle_highlight_color: document.getElementById("subHighlightColor").value,
        subtitle_border_color: document.getElementById("subBorderColor").value,
        subtitle_font_size: parseInt(document.getElementById("subFontSize").value),
        subtitle_highlight_size: parseInt(document.getElementById("subHighlightSize").value),
        subtitle_border_size: parseFloat(document.getElementById("subBorderSize").value),
        subtitle_style: document.getElementById("subStyle").value,
        subtitle_position: document.getElementById("subPosition").value,
    };

    addConsoleLog("[Acao] Iniciando geracao de legendas...", "info");
    prepareNewOperationHud();
    showProgressBar();
    try {
        const response = await fetch("/api/process/subtitles", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                video_path: state.selectedVideo,
                subtitle_settings: subtitleSettings,
            }),
        });
        const started = await parseJsonResponse(response, "Geração de legendas");
        if (!response.ok || !started.success) throw new Error(started.error || "Não foi possível iniciar a geração de legendas");
        registerStartedOperation(started, "Geração de legendas em andamento.");
        showProgressBar();
    } catch (error) {
        hideProgressBar();
        showToast(error.message || "Não foi possível iniciar a geração de legendas", "error");
    }
}

// Subtitle preview updates
["subTextColor", "subHighlightColor", "subBorderColor", "subFontSize", "subPosition"].forEach(id => {
    document.getElementById(id).addEventListener("input", updateSubtitlePreview);
});

// Range value displays
document.getElementById("subFontSize").addEventListener("input", (e) => {
    document.getElementById("fontSizeValue").textContent = e.target.value + "pt";
});
document.getElementById("subHighlightSize").addEventListener("input", (e) => {
    document.getElementById("highlightSizeValue").textContent = e.target.value;
});
document.getElementById("subBorderSize").addEventListener("input", (e) => {
    document.getElementById("borderSizeValue").textContent = e.target.value;
});

// Color value displays
document.querySelectorAll('.color-picker-group input[type="color"]').forEach(input => {
    input.addEventListener("input", (e) => {
        e.target.nextElementSibling.textContent = e.target.value.toUpperCase();
    });
});

// ─── Thumbnail Modal ───

function openThumbnailModal() {
    document.getElementById("thumbnailModal").classList.add("active");
}

function closeThumbnailModal() {
    document.getElementById("thumbnailModal").classList.remove("active");
}

async function generateThumbnail() {
    if (!requireVideo()) return;
    closeThumbnailModal();

    const text = document.getElementById("thumbText").value;
    const style = document.getElementById("thumbStyle").value;
    const time = parseFloat(document.getElementById("thumbTime").value) || 5;

    addConsoleLog("[Acao] Gerando thumbnail...", "info");
    prepareNewOperationHud();
    showProgressBar();
    try {
        const response = await fetch("/api/process/thumbnail", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                video_path: state.selectedVideo,
                text, style, time,
            }),
        });
        const started = await parseJsonResponse(response, "Geração de thumbnail");
        if (!response.ok || !started.success) throw new Error(started.error || "Não foi possível iniciar a geração de thumbnail");
        registerStartedOperation(started, "Geração de thumbnail em andamento.");
        showProgressBar();
    } catch (error) {
        hideProgressBar();
        showToast(error.message || "Não foi possível iniciar a geração de thumbnail", "error");
    }
}

function showThumbnailPreview(path) {
    showToast("Thumbnail salva em: " + path, "success");
}

// ─── Output Directory ───

document.getElementById("btnChangeOutputDir").addEventListener("click", async () => {
    try {
        const res = await fetch("/api/dialog/choose", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mode: "folder", initial_path: state.outputDir || "", title: "Escolha a pasta de saída dos cortes" }),
        });
        const data = await res.json();
        if (data.success && data.path) {
            state.outputDir = data.path;
            document.getElementById("outputDirText").textContent = data.path;
            await fetch("/api/settings", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ output_dir: data.path }),
            });
            showToast("Pasta de saída atualizada pelo explorador.", "success");
            return;
        }
        if (data.cancelled) return;
        throw new Error(data.error || "Diálogo não disponível");
    } catch (error) {
        // Keep the previous manual modal as a non-destructive fallback.
        document.getElementById("outputDirInput").value = state.outputDir || "";
        document.getElementById("outputDirModal").classList.add("active");
        showToast("Explorador nativo indisponível; você pode informar o caminho manualmente.", "warning");
    }
});

function closeOutputDirModal() {
    document.getElementById("outputDirModal").classList.remove("active");
}

function saveOutputDir() {
    const dir = document.getElementById("outputDirInput").value.trim();
    state.outputDir = dir;
    document.getElementById("outputDirText").textContent = dir || "workspace/exports (padrao)";
    closeOutputDirModal();

    // Save to settings
    fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ output_dir: dir }),
    });

    showToast("Pasta de saida atualizada!", "success");
}

function selectedVideoPathForRequest() {
    return typeof state.selectedVideo === "string" ? state.selectedVideo : (state.selectedVideo?.path || "");
}

async function openConfiguredDownloadsFolder() {
    try {
        const configuredSourceDir = String(state.sourceDownloadDir || "").trim();
        const folderPath = configuredSourceDir || await chooseSourceDirectory();
        if (!folderPath) return;
        const response = await fetch("/api/open_folder", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: folderPath }),
        });
        const data = await parseJsonResponse(response, "Pasta de downloads");
        if (!response.ok || data.error) throw new Error(data.error || "Não foi possível abrir a pasta de downloads");
        showToast(`Pasta de downloads aberta: ${folderPath}`, "success");
    } catch (error) {
        showToast(error.message, "error");
    }
}

document.getElementById("btnOpenDownloadsDir")?.addEventListener("click", openConfiguredDownloadsFolder);
document.getElementById("btnCopyConsoleLog")?.addEventListener("click", async () => {
    const text = document.getElementById("consoleOutput")?.innerText?.trim() || "";
    if (!text) {
        showToast("Ainda não há log para copiar.", "warning");
        return;
    }
    try {
        await navigator.clipboard.writeText(text);
        showToast("Log completo copiado.", "success");
    } catch (error) {
        showToast("Não foi possível copiar o log automaticamente.", "error");
    }
});

function renderEditorialContextPreview(context = {}) {
    const result = document.getElementById("contextAnalysisResult");
    if (!result) return;
    const qa = Array.isArray(context.qa_candidates) ? context.qa_candidates.length : 0;
    const chapters = Array.isArray(context.editorial_chapters) ? context.editorial_chapters.length : 0;
    const windows = Array.isArray(context.interview_windows) ? context.interview_windows.length : 0;
    const hooks = Array.isArray(context.hook_candidates) ? context.hook_candidates.slice(0, 5) : [];
    const quality = context.transcription_quality || {};
    const speakerDetection = context.speaker_detection || {};
    const localAudio = context.local_audio || {};
    const multimodal = context.multimodal || {};
    const signals = context.signals || {};
    const qaCandidates = Array.isArray(context.qa_candidates) ? context.qa_candidates.slice(0, 8) : [];
    const editorialChapters = Array.isArray(context.editorial_chapters) ? context.editorial_chapters.slice(0, 8) : [];
    const multimodalStatus = String(multimodal.source_identity_status || "").toLowerCase();
    const highEnergyMoments = Array.isArray(localAudio.high_energy_moments) ? localAudio.high_energy_moments.slice(0, 8) : [];
    const mode = context.analysis_mode === "transcript_plus_video"
        ? "transcrição + vídeo/áudio"
        : context.analysis_mode === "transcript_plus_local_audio"
            ? "transcrição + áudio local"
            : "transcrição";
    const speakerMarkup = speakerDetection.status === "validated"
        ? `<span class="context-speaker-status validated">locutor(es) marcado(s) em toda a transcrição</span>`
        : speakerDetection.status === "partial"
            ? `<span class="context-speaker-status review" title="${escapeHtml(speakerDetection.message || "Diarização parcial")}">diarização parcial · confirmar trocas</span>`
            : `<span class="context-speaker-status review" title="${escapeHtml(speakerDetection.message || "Locutor não validado")}">locutor não diarizado · confirmar no vídeo</span>`;
    const hookMarkup = hooks.length
        ? `<div class="context-hook-list"><div class="context-hook-heading"><span class="material-icons-round">bolt</span><strong>Hooks potenciais para revisar</strong><small>Não são promessa de viralização; confirme imagem, voz e payoff.</small></div>${hooks.map((hook, index) => {
            const start = Number(hook.start || 0);
            const end = Number(hook.end || hook.hook_end || start);
            const score = Number(hook.score || 0).toFixed(1);
            const reviewReasons = [];
            if (hook.needs_speaker_review) reviewReasons.push(hook.speaker_review_reason || "confirmar locutor");
            if (hook.needs_visual_review) reviewReasons.push(hook.visual_review_reason || (hook.visual_evidence_required ? "confirmar gráfico, pesquisa ou imagem mencionada" : "revisar sobreposição visual/áudio"));
            if (hook.audio_signal?.available === false) reviewReasons.push("áudio sem sinal local");
            const review = reviewReasons.length ? ` · ${reviewReasons.map(escapeHtml).join(" · ")}` : "";
            const confidence = Number(hook.confidence);
            const confidenceLabel = Number.isFinite(confidence) ? ` · confiança ${Math.round(Math.max(0, Math.min(1, confidence)) * 100)}%` : "";
            return `<article class="context-hook-card"><div class="context-hook-card-head"><strong>#${index + 1} · ${escapeHtml(hook.family || "outro")}</strong><span>${formatTime(start)}–${formatTime(end)} · ${score}/100</span></div><blockquote>${escapeHtml(hook.hook_text || "Fala de abertura não disponível.")}</blockquote><p>${escapeHtml(hook.reason || "Sinal contextual detectado.")}</p><small>${hook.payoff_confirmed ? "Payoff próximo detectado" : "Payoff ainda precisa de validação"}${confidenceLabel}${review}</small></article>`;
        }).join("")}</div>`
        : `<div class="context-hook-empty"><span class="material-icons-round">search_off</span><span>Nenhum hook textual robusto foi isolado; o editor pode revisar a transcrição por capítulos.</span></div>`;
    const localAudioMarkup = localAudio.available && highEnergyMoments.length
        ? `<div class="context-local-audio"><div class="context-hook-heading"><span class="material-icons-round">graphic_eq</span><strong>Picos locais de energia para revisar</strong><small>São pistas de ênfase vocal; confirme o sentido e o payoff na imagem e na fala.</small></div><div class="context-energy-list">${highEnergyMoments.map(moment => `<span><b>${formatTime(Number(moment.start || 0))}–${formatTime(Number(moment.end || 0))}</b> · ${Math.round(Number(moment.avg_energy || 0) * 100)}% relativo</span>`).join("")}</div></div>`
        : "";
    const multimodalMarkup = multimodalStatus === "validated"
        ? `<span class="context-source-status validated" title="A identidade da fonte foi confirmada pela análise remota">fonte multimodal validada</span>`
        : multimodalStatus === "mismatch"
            ? `<span class="context-source-status review" title="As observações remotas foram descartadas por incompatibilidade de fonte">fonte remota incompatível · descartada</span>`
            : multimodalStatus
                ? `<span class="context-source-status review" title="A análise remota é apenas evidência auxiliar até a identidade ser confirmada">vídeo remoto · evidência auxiliar</span>`
                : "";
    const riskItems = [];
    if (quality.review_required) riskItems.push("cobertura temporal da transcrição exige conferência");
    if (speakerDetection.review_required) riskItems.push(speakerDetection.message || "trocas de locutor exigem conferência");
    if (signals.possible_overlap) riskItems.push(`${Number(signals.overlap_count || 0)} possível(is) sobreposição(ões) de fala`);
    if (multimodalStatus === "mismatch") riskItems.push("observação remota descartada por identidade incompatível");
    const riskMarkup = riskItems.length
        ? `<ul class="context-risk-list">${riskItems.map(item => `<li><span class="material-icons-round">priority_high</span>${escapeHtml(item)}</li>`).join("")}</ul>`
        : `<p class="context-empty-copy"><span class="material-icons-round">verified</span>Nenhum risco estrutural automático nesta leitura.</p>`;
    const qaMarkup = qaCandidates.length
        ? qaCandidates.map((candidate, index) => {
            const start = Number(candidate.start || 0);
            const end = Number(candidate.end || candidate.response_end || start);
            const basis = String(candidate.boundary_basis || candidate.qa_boundary_basis || "janela temporal").replaceAll("_", " ");
            const review = candidate.needs_speaker_review ? " · confirmar locutor" : "";
            return `<article class="context-dossier-item"><div><strong>#${index + 1} · ${formatTime(start)}–${formatTime(end)}</strong><span>${escapeHtml(basis)}${escapeHtml(review)}</span></div><p>${escapeHtml(candidate.question_text || candidate.text || "Pergunta–resposta detectada")}</p></article>`;
        }).join("")
        : `<p class="context-empty-copy"><span class="material-icons-round">question_mark</span>Nenhum bloco pergunta–resposta robusto foi isolado.</p>`;
    const chapterMarkup = editorialChapters.length
        ? editorialChapters.map((chapter, index) => `<article class="context-dossier-item"><div><strong>${index + 1}. ${escapeHtml(chapter.label || "Capítulo editorial")}</strong><span>${formatTime(Number(chapter.start || 0))}–${formatTime(Number(chapter.end || 0))}</span></div><p>${escapeHtml(chapter.summary || chapter.description || "Bloco temporal disponível para revisão.")}</p></article>`).join("")
        : `<p class="context-empty-copy"><span class="material-icons-round">view_agenda</span>Capítulos ainda não disponíveis.</p>`;
    const signalMarkup = `<div class="context-signal-grid"><span><b>${Number(signals.speaker_markers || 0)}</b><small>marcadores de locutor</small></span><span><b>${Number(signals.overlap_count || 0)}</b><small>sobreposições possíveis</small></span><span><b>${signals.long_form ? "sim" : "não"}</b><small>fonte longa</small></span><span><b>${escapeHtml(String(signals.transcription_coverage_status || quality.status || "não verificada"))}</b><small>cobertura temporal</small></span></div>`;
    result.hidden = false;
    const participantConfidence = Number(context.participant_confidence);
    const participantMarkup = Number.isFinite(participantConfidence)
        ? `<span title="Referência textual e sinais de locutor; não é identificação visual">participante ${Math.round(Math.max(0, Math.min(1, participantConfidence)) * 100)}%</span>`
        : "";
    result.innerHTML = `<div class="context-result-summary"><div class="context-dossier-kicker"><span class="material-icons-round">fact_check</span><span>Dossiê editorial · ${escapeHtml(mode)}</span></div><strong>${escapeHtml(context.description || "Contexto editorial analisado.")}</strong><div class="context-result-facts"><span>${qa} bloco(s) Q&A</span><span>${chapters} capítulo(s)</span><span>${windows} janela(s) de entrevista</span><span>${Number(quality.segment_count || 0)} segmentos</span>${participantMarkup}${speakerMarkup}${multimodalMarkup}</div></div><div class="context-dossier-grid"><section class="context-dossier-card"><header><span class="material-icons-round">account_tree</span><div><strong>Estrutura da fonte</strong><small>O que foi identificado antes do corte</small></div></header>${signalMarkup}</section><section class="context-dossier-card"><header><span class="material-icons-round">warning_amber</span><div><strong>Riscos para revisar</strong><small>Alertas não são rejeição automática</small></div></header>${riskMarkup}</section><section class="context-dossier-card"><header><span class="material-icons-round">question_answer</span><div><strong>Blocos pergunta–resposta</strong><small>Intervalos com fechamento e fronteira explicável</small></div></header><div class="context-dossier-list">${qaMarkup}</div></section><section class="context-dossier-card"><header><span class="material-icons-round">view_agenda</span><div><strong>Capítulos editoriais</strong><small>Blocos para navegar pela fonte sem contar cortes artificiais</small></div></header><div class="context-dossier-list">${chapterMarkup}</div></section></div>${localAudioMarkup}${hookMarkup}`;
}

async function pollEditorialContextJob(jobId, button, status, requestToken, sourcePath, signal) {
    const started = Date.now();
    while (Date.now() - started < 20 * 60 * 1000) {
        await new Promise(resolve => setTimeout(resolve, 1200));
        if (requestToken !== state.contextAnalysisToken || selectedVideoPathForRequest() !== sourcePath) {
            return { stale: true };
        }
        const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`, { signal });
        const job = await parseJsonResponse(response, "Status da análise de contexto");
        if (!response.ok) throw new Error(job.error || "Não foi possível consultar a análise");
        if (status) {
            const progress = Number(job.progress);
            const progressLabel = Number.isFinite(progress) && progress > 0 ? `${Math.round(progress)}% · ` : "";
            const stageLabel = job.stage === "editorial_context" ? "Dossiê editorial" : "Análise";
            status.textContent = `${progressLabel}${stageLabel}: ${job.message || "processando sinais"}`;
        }
        if (job.state === "completed") {
            if (requestToken !== state.contextAnalysisToken || selectedVideoPathForRequest() !== sourcePath) {
                return { stale: true };
            }
            const artifact = Array.isArray(job.artifacts) ? job.artifacts.find(item => item?.type === "editorial_context") : null;
            state.editorialContext = artifact?.context || null;
            state.contextAnalysisSourcePath = sourcePath;
            state.contextAnalysisJobId = "";
            renderEditorialContextPreview(state.editorialContext || {});
            if (status) status.textContent = "Contexto pronto. O próximo corte poderá usar esta leitura como referência.";
            return;
        }
        if (job.state === "failed" || job.state === "cancelled") {
            throw new Error(job.error || job.message || "A análise de contexto não foi concluída.");
        }
    }
    throw new Error("A análise de contexto excedeu o tempo esperado; verifique o console.");
}

document.getElementById("btnAnalyzeEditorialContext")?.addEventListener("click", async () => {
    const videoPath = selectedVideoPathForRequest();
    const status = document.getElementById("contextAnalysisStatus");
    const button = document.getElementById("btnAnalyzeEditorialContext");
    if (!videoPath) {
        if (status) status.textContent = "Selecione um vídeo antes de analisar o contexto.";
        showToast("Selecione um vídeo primeiro.", "warning");
        return;
    }
    const linkedTranscript = transcriptPayloadForSelectedVideo();
    const typedTranscript = document.getElementById("manualTranscriptInput")?.value.trim() || "";
    const transcript = linkedTranscript
        ? formatTranscriptForEditor(linkedTranscript)
        : state.manualTranscript
            ? ""
            : typedTranscript;
    if (state.manualTranscript && !linkedTranscript) {
        addConsoleLog("[Contexto] Transcrição carregada não está vinculada ao vídeo selecionado; análise integral seguirá sem essa fonte.", "warning");
    }
    state.contextAnalysisController?.abort();
    const controller = new AbortController();
    state.contextAnalysisController = controller;
    const requestToken = ++state.contextAnalysisToken;
    state.editorialContext = null;
    state.contextAnalysisSourcePath = "";
    const contextResult = document.getElementById("contextAnalysisResult");
    if (contextResult) {
        contextResult.hidden = true;
        contextResult.innerHTML = "";
    }
    button.disabled = true;
    button.classList.add("loading");
    if (status) status.textContent = "Preparando análise integral...";
    addConsoleLog("[Contexto] Análise integral antes do corte solicitada.", "info");
    try {
        const response = await fetch("/api/editorial/context", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                video_path: videoPath,
                project_id: state.selectedProjectId || state.currentProjectId || null,
                transcript_text: transcript,
                transcript_language: document.getElementById("settingLanguage")?.value || "pt",
                user_context: document.getElementById("userContextInput")?.value.trim() || "",
                analyze_video: document.getElementById("contextAnalyzeVideo")?.checked !== false,
            }),
            signal: controller.signal,
        });
        const data = await parseJsonResponse(response, "Análise de contexto");
        if (!response.ok || !data.success) throw new Error(data.error || "Não foi possível iniciar a análise de contexto");
        state.contextAnalysisJobId = String(data.job_id || "");
        const pollResult = await pollEditorialContextJob(data.job_id, button, status, requestToken, videoPath, controller.signal);
        if (pollResult?.stale) return;
        addConsoleLog("[Contexto] Dossiê integral concluído e exibido no painel.", "success");
        showToast("Contexto analisado antes do corte.", "success");
    } catch (error) {
        const isCurrentRequest = requestToken === state.contextAnalysisToken;
        if (isCurrentRequest) state.contextAnalysisJobId = "";
        if (error?.name === "AbortError" || controller.signal.aborted || !isCurrentRequest) return;
        if (status) status.textContent = error.message;
        addConsoleLog(`[Contexto] ${error.message}`, "error");
        showToast(error.message, "error");
    } finally {
        if (requestToken === state.contextAnalysisToken) {
            state.contextAnalysisController = null;
            state.contextAnalysisJobId = "";
            button.disabled = false;
            button.classList.remove("loading");
        }
    }
});

// ─── Results Display ───

function mediaUrlForPath(path) {
    if (!path) return "";
    const value = String(path).replaceAll("\\", "/");
    if (value.startsWith("/workspace/") || value.startsWith("workspace/")) {
        const relative = value.replace(/^\/+workspace\//, "").replace(/^workspace\//, "");
        return `/workspace/${relative.split("/").filter(Boolean).map(encodeURIComponent).join("/")}`;
    }
    if (/^[A-Za-z]:\//.test(value) || value.startsWith("/")) {
        return `/api/output_file?path=${encodeURIComponent(path)}`;
    }
    return `/workspace/${value.split("/").filter(Boolean).map(encodeURIComponent).join("/")}`;
}

function normalizedMediaIdentity(value) {
    const raw = String(value || "").trim().replaceAll("\\", "/").replace(/\/+/g, "/");
    const withoutDot = raw.replace(/^\.\//, "");
    return /^[A-Z]:\//i.test(withoutDot) ? withoutDot.toLowerCase() : withoutDot;
}

function mediaPathsMatch(left, right) {
    const normalizedLeft = normalizedMediaIdentity(left);
    const normalizedRight = normalizedMediaIdentity(right);
    return Boolean(normalizedLeft && normalizedRight && normalizedLeft === normalizedRight);
}

function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>'"]/g, (character) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "'": "&#39;",
        '"': "&quot;",
    }[character]));
}

function safeExternalUrl(value) {
    const candidate = String(value || "").trim();
    if (!candidate) return "";
    try {
        const parsed = new URL(candidate, window.location.origin);
        return parsed.protocol === "http:" || parsed.protocol === "https:" ? candidate : "";
    } catch (_error) {
        return "";
    }
}

function mediaUrlForClip(clip) {
    return mediaUrlForPath(clip.subtitled_path || clip.path);
}

const editorialFormatLabels = {
    vertical_916: "9:16 — headline central",
    square_alfinetei: "1:1 — Alfinetei",
    fake_tweet: "Fake tweet",
};

function renderEditorialAudit(audit, mode = "standard") {
    const element = document.getElementById("editorialAuditSummary");
    if (!element) return;
    if (!audit || typeof audit !== "object") {
        element.style.display = "none";
        element.innerHTML = "";
        return;
    }
    const flags = audit.review_flags || {};
    const analysis = audit.analysis || {};
    const warnings = [
        flags.needs_fact_review ? "Revisão factual" : "",
        flags.needs_legal_review ? "Revisão jurídica" : "",
        flags.entity_context_review_required ? "Entidade citada lateralmente" : "",
        flags.transcript_ends_incomplete ? "Transcrição termina incompleta" : "",
    ].filter(Boolean);
    const warningHtml = warnings.length
        ? `<span class="audit-warning"><span class="material-icons-round">warning</span>${escapeHtml(warnings.join(" · "))}</span>`
        : `<span class="audit-ok"><span class="material-icons-round">verified</span>Sem alerta estrutural automático</span>`;
    element.innerHTML = `
        <div class="audit-result-head">
            <span class="material-icons-round">fact_check</span>
            <div><strong>Auditoria ${mode === "full" ? "completa" : "editorial"}</strong><small>Qualidade editorial separada do potencial observado</small></div>
            <span class="audit-format-badge">${escapeHtml(editorialFormatLabels[audit.recommended_format] || "Formato a revisar")}</span>
        </div>
        <p class="audit-result-reason">${escapeHtml(audit.recommendation_reason || "Formato recomendado pelos sinais editoriais disponíveis.")}</p>
        <div class="audit-result-signals">
            <span>Contexto <b>${Number(analysis.context_completeness || 0)}/100</b></span>
            <span>Tese <b>${Number(analysis.claim_strength || 0)}/100</b></span>
            <span>Conflito <b>${Number(analysis.conflict_or_stakes || 0)}/100</b></span>
            ${warningHtml}
        </div>`;
    element.style.display = "block";
}

function displayResults(clips, videoLayout = null) {
    state.clips = Array.isArray(clips) ? clips : [];
    state.lastReviewAction = null;
    state.reviewFilter = "all";
    state.reviewSort = "score";
    state.videoLayout = videoLayout || "unknown";

    renderReviewCommandCenter();
    renderResultsGrid();
    document.getElementById("resultsSection").scrollIntoView({ behavior: "smooth" });
}

function reviewStatusOf(clip) {
    const explicitStatus = String(clip?.review_status || "").trim();
    if (explicitStatus) return explicitStatus;
    const coverageStatus = String(
        clip?.transcription_coverage_status
        || clip?.review_flags?.transcription_coverage_status
        || clip?.review_provenance?.transcript_coverage_status
        || ""
    ).trim().toLowerCase();
    if (["partial", "mismatch_suspected", "empty", "unknown"].includes(coverageStatus)) return "needs_review";
    return "pending";
}

function reviewStatusMeta(status) {
    const labels = {
        pending: { label: "NA FILA", icon: "pending_actions", hint: "Aguardando sua decisão" },
        approved: { label: "APROVADO", icon: "check_circle", hint: "Decisão salva no histórico editorial" },
        rejected: { label: "REJEITADO", icon: "cancel", hint: "Retirado da seleção final" },
        needs_review: { label: "REVISAR CONTEXTO", icon: "visibility", hint: "Separado para confirmar contexto" },
        adjusted: { label: "AJUSTE SALVO", icon: "tune", hint: "Ajuste salvo; confirme novamente" },
        rendered: { label: "RENDERIZADO", icon: "movie", hint: "Renderização validada" },
    };
    return labels[status] || labels.pending;
}

function reviewStats(clips = state.clips) {
    const all = Array.isArray(clips) ? clips : [];
    const count = (status) => all.filter((clip) => reviewStatusOf(clip) === status).length;
    const pending = count("pending");
    const approved = count("approved");
    const rejected = count("rejected");
    const needsReview = count("needs_review");
    return {
        total: all.length,
        pending,
        approved,
        rejected,
        needsReview,
        reviewed: approved + rejected + needsReview,
    };
}

function labelForLayout(videoLayout) {
    const labels = {
        single_speaker: "locutor principal detectado",
        speaker: "locutor principal detectado",
        debate: "múltiplos participantes",
        fullscreen: "quadro original protegido",
        unknown: "enquadramento a confirmar",
    };
    return labels[videoLayout] || labels.unknown;
}

function renderReviewCommandCenter() {
    const center = document.getElementById("reviewCommandCenter");
    if (!center) return;
    const stats = reviewStats();
    const sourceMap = { gemini: "Gemini", llm: "Ollama", nlp: "NLP" };
    const source = stats.total > 0 ? (sourceMap[state.clips[0]?.source] || "NLP") : "NLP";
    const reviewedPercent = stats.total ? Math.round((stats.reviewed / stats.total) * 100) : 0;

    center.style.display = "block";
    document.getElementById("reviewTotalCount").textContent = stats.total;
    document.getElementById("reviewPendingCount").textContent = stats.pending;
    document.getElementById("reviewApprovedCount").textContent = stats.approved;
    document.getElementById("reviewNeedsReviewCount").textContent = stats.needsReview;
    const decisionLabel = { approved: "aprovado", rejected: "rejeitado", needs_review: "marcado para revisar contexto" };
    const latestDecision = state.lastReviewAction ? ` Última decisão: ${decisionLabel[state.lastReviewAction.action] || state.lastReviewAction.action}.` : "";
    document.getElementById("reviewOverviewText").textContent = `${source} identificou ${stats.total} candidatos. Revise primeiro os que mantêm ideia, evidência e conclusão no mesmo intervalo.${latestDecision}`;
    document.getElementById("reviewQueueText").textContent = `${stats.reviewed} de ${stats.total} revisados`;
    document.getElementById("reviewQueueFill").style.width = `${reviewedPercent}%`;
    document.getElementById("reviewLayoutSummary").innerHTML = `
        <span class="layout-summary-chip"><span class="material-icons-round">aspect_ratio</span>${labelForLayout(state.videoLayout)}</span>
        <span class="layout-summary-chip"><span class="material-icons-round">tips_and_updates</span>score explicável</span>`;

    const counts = {
        all: stats.total,
        pending: stats.pending,
        approved: stats.approved,
        needs_review: stats.needsReview,
        rejected: stats.rejected,
    };
    document.querySelectorAll("[data-review-filter]").forEach((button) => {
        const filter = button.dataset.reviewFilter;
        button.classList.toggle("active", filter === state.reviewFilter);
        const countElement = button.querySelector("span");
        if (countElement) countElement.textContent = counts[filter] ?? 0;
        button.onclick = () => {
            state.reviewFilter = filter;
            renderReviewCommandCenter();
            renderResultsGrid();
        };
    });

    const sort = document.getElementById("reviewSort");
    if (sort) {
        sort.value = state.reviewSort || "score";
        sort.onchange = () => {
            state.reviewSort = sort.value;
            renderResultsGrid();
        };
    }
}

function clipsForReviewQueue() {
    const filter = state.reviewFilter || "all";
    const clips = [...(state.clips || [])].filter((clip) => filter === "all" || reviewStatusOf(clip) === filter);
    const sort = state.reviewSort || "score";
    return clips.sort((left, right) => {
        if (sort === "duration") return Number(right.duration || 0) - Number(left.duration || 0);
        if (sort === "timeline") return Number(left.start || 0) - Number(right.start || 0);
        return Number(right.viral_score || 0) - Number(left.viral_score || 0);
    });
}

function layoutMetaForClip(clip) {
    const framing = clip.framing || {};
    const framingReviewRequired = [
        framing.review_required,
        clip.framing_review_required,
        clip.review_flags?.framing_review_required,
    ].some((value) => safeBooleanFlag(value));
    if (framing.mode === "reframe_9_16") {
        return framingReviewRequired
            ? { icon: "visibility", label: "Reframe 9:16 planejado · revisar", hint: framing.reason || "reenquadramento depende de confirmação visual" }
            : { icon: "center_focus_strong", label: "Reframe 9:16 seguro", hint: framing.reason || "locutor estável detectado" };
    }
    if (framing.mode === "original") {
        return { icon: "aspect_ratio", label: "Quadro original", hint: framing.reason || "composição preservada" };
    }
    return { icon: "visibility", label: "Enquadramento a revisar", hint: "a decisão depende da revisão visual" };
}

function renderResultsGrid() {
    const section = document.getElementById("resultsSection");
    const grid = document.getElementById("resultsGrid");
    const summary = document.getElementById("resultsSummary");
    const searchBar = document.getElementById("transcriptSearchBar");
    const allClips = state.clips || [];
    const clips = clipsForReviewQueue();
    section.style.display = "block";
    grid.innerHTML = "";

    if (searchBar) searchBar.style.display = "flex";

    const finiteScores = allClips.map((clip) => Number(clip.viral_score)).filter((score) => Number.isFinite(score));
    const avgScore = finiteScores.length ? finiteScores.reduce((total, score) => total + score, 0) / finiteScores.length : 0;
    const highScoreCount = allClips.filter((clip) => Number.isFinite(Number(clip.viral_score)) && Number(clip.viral_score) >= 70).length;
    const sourceMap = { "gemini": "Gemini", "llm": "Ollama", "nlp": "NLP" };
    const source = allClips.length > 0 ? (sourceMap[allClips[0].source] || "NLP") : "NLP";
    const sourceIdentity = state.resultSourceIdentity ? ` | Fonte: ${state.resultSourceIdentity}` : "";
    summary.textContent = `${clips.length} de ${allClips.length} visíveis | Média: ${avgScore.toFixed(0)} | ${highScoreCount} com alto potencial | via ${source}${sourceIdentity}`;

    const sorted = clips;

    sorted.forEach((clip, i) => {
        const originalIndex = state.clips.indexOf(clip);
        const rank = clip.rank || (i + 1);
        const clipScore = Number(clip.viral_score);
        const displayScore = Number.isFinite(clipScore) ? clipScore : 0;
        const scoreClass = displayScore >= 70 ? "high" : displayScore >= 40 ? "medium" : "low";
        const seo = clip.seo || {};
        const titles = seo.titles || [];
        const tags = seo.tags || [];
        const hashtags = seo.hashtags || [];
        const breakdown = clip.breakdown || {};
        const factors = clip.factors || {};
        const politicalType = clip.political_editorial_type || "";
        const topicSignature = String(clip.topic_signature || "");
        const diversityPenalty = Math.round(Number(clip.diversity_penalty || 0));
        const diversityReason = String(clip.diversity_reason || "").trim();
        const reviewFlags = clip.review_flags || {};
        const contextRecovery = (clip.context_recovery && typeof clip.context_recovery === "object")
            ? clip.context_recovery
            : (reviewFlags.context_recovery && typeof reviewFlags.context_recovery === "object" ? reviewFlags.context_recovery : {});
        const contextRecoveryApplied = [contextRecovery.applied, reviewFlags.context_recovery_applied].some((value) => safeBooleanFlag(value));
        const contextRecoveryLabel = String(contextRecovery.reason || (contextRecoveryApplied ? "antecedente recuperado antes do início" : "")).trim();
        const contextReferenceFlag = [clip.starts_with_context_reference, reviewFlags.starts_with_context_reference].some((value) => safeBooleanFlag(value));
        const weakPayoffFlag = [clip.payoff_weak_ending, reviewFlags.payoff_weak_ending].some((value) => safeBooleanFlag(value));
        const closureType = String(clip.closure_type || "");
        const closureLabels = { conclusion: "conclusão", closed_statement: "frase fechada", cliffhanger: "continuidade", open: "fecho a revisar" };
        const speakerLabel = String(clip.speaker || clip.speaker_role || "").trim();
        const speakerConfidence = Number(clip.speaker_confidence);
        const overlapSuspected = [clip.overlap_suspected, clip.speaker_overlap, reviewFlags.overlap_suspected].some((value) => safeBooleanFlag(value));
        const visualFormat = String(clip.visual_format || clip.format_family || "").trim();
        const visualFormatConfidence = Number(clip.visual_format_confidence);
        const framing = clip.framing || {};
        const framingMode = String(framing.mode || clip.framing_mode || "").trim().toLowerCase();
        const framingReason = String(framing.reason || clip.framing_reason || "").trim();
        const framingConfidence = Number(framing.confidence ?? clip.framing_confidence);
        const framingLabels = {
            face_tracking: "facetracking aplicado",
            original_16_9: "composição original preservada",
            center_crop: "crop centralizado",
            reframe_9_16: "reframe 9:16 planejado",
            original: "composição original preservada",
        };
        const multimodalIdentityStatus = String(clip.multimodal_identity_status || reviewFlags.multimodal_identity_status || "").trim().toLowerCase();
        const multimodalIdentityConfidence = Number(clip.multimodal_identity_confidence ?? reviewFlags.multimodal_identity_confidence);
        const multimodalIdentityReview = multimodalIdentityStatus && multimodalIdentityStatus !== "validated";
        const multimodalIdentityLabel = multimodalIdentityStatus === "mismatch"
            ? "fonte multimodal incompatível; observações visuais recusadas"
            : "identidade multimodal não validada; confirmar no vídeo";
        const visualFormatLabels = {
            talking_head: "talking head",
            selfie_proximo: "selfie próximo",
            entrevista: "entrevista",
            podcast: "podcast",
            react: "react / evidência",
            split_screen: "split-screen",
            evidencia_externa: "evidência externa",
            b_roll_argumentativo: "B-roll argumentativo",
            palco: "palco",
            institucional: "institucional",
            campanha: "campanha",
            testemunhal: "testemunhal",
            unboxing: "unboxing",
            humor_bastidor: "humor / bastidor",
            text_panel: "painel textual",
            fake_tweet: "fake tweet / post social",
            visual_meme: "meme / arte composta",
            desconhecido: "formato a revisar",
        };
        const preserveComposition = [clip.preserve_composition, reviewFlags.preserve_composition].some((value) => safeBooleanFlag(value))
            || clip.reframe_policy === "preservar_composicao";
        const needsFactReview = [reviewFlags.needs_fact_review, reviewFlags.needsFactReview].some((value) => safeBooleanFlag(value));
        const needsLegalReview = [reviewFlags.needs_legal_review, reviewFlags.needsLegalReview].some((value) => safeBooleanFlag(value));
        const primaryEntityRole = String(clip.primary_entity_role || reviewFlags.primary_entity_role || "").trim().toLowerCase();
        const entityContextReviewRequired = [clip.entity_context_review_required, reviewFlags.entity_context_review_required].some((value) => safeBooleanFlag(value));
        const entityContextReviewHint = primaryEntityRole === "lateral"
            ? "A entidade aparece, mas a tese do trecho pode estar em outro assunto."
            : "Confirme se a entidade é alvo central ou apenas comparação no trecho.";
        const chapterCount = safeNonNegativeCount(clip.chapter_count, reviewFlags.chapter_count);
        const chapterScore = Number(clip.chapter_coherence_score ?? reviewFlags.chapter_coherence_score);
        const chapterBridge = [clip.qa_bridge, reviewFlags.qa_bridge].some((value) => safeBooleanFlag(value));
        const qaBoundaryBasis = String(clip.qa_boundary_basis || reviewFlags.qa_boundary_basis || "").trim();
        const qaBoundaryReviewRequired = [clip.qa_boundary_review_required, reviewFlags.qa_boundary_review_required].some((value) => safeBooleanFlag(value));
        const speakerReviewRequired = safeBooleanFlag(clip.speaker_review_required)
            || safeBooleanFlag(reviewFlags.speaker_review_required)
            || (safeBooleanFlag(clip.qa_boundary_review_required) && safeBooleanFlag(clip.question_detected));
        const topicReviewRequired = [
            clip.topic_review_required,
            reviewFlags.topic_review_required,
            clip.topic_boundary,
            clip.topic_change_detected,
            reviewFlags.topic_boundary,
            reviewFlags.topic_change_detected,
        ].some((value) => safeBooleanFlag(value));
        const topicReviewReason = String(
            clip.topic_review_reason
            || reviewFlags.topic_review_reason
            || "mudança de tópico detectada; confirme a continuidade do assunto"
        ).trim();
        const speakerReviewReason = String(
            clip.speaker_review_reason
            || reviewFlags.speaker_review_reason
            || "locutor ou ponte pergunta–resposta sem confirmação confiável; revisar áudio e vídeo"
        ).trim();
        const qaBoundaryLabels = {
            mudanca_de_locutor: "mudança de locutor",
            marcador_de_locutor: "marcador de locutor",
            segunda_troca_de_locutor: "segunda troca de locutor",
            sem_diarizacao: "sem diarização confiável",
        };
        const qaBoundaryLabel = qaBoundaryLabels[qaBoundaryBasis] || qaBoundaryBasis.replaceAll("_", " ");
        const rawDurationSeconds = Number(clip.duration || ((clip.end || 0) - (clip.start || 0)) || 0);
        const durationSeconds = Number.isFinite(rawDurationSeconds) && rawDurationSeconds >= 0 ? rawDurationSeconds : 0;
        const displayDurationSeconds = durationSeconds;
        const durationFit = Number(clip.duration_fit ?? factors.duration_fit);
        const durationPreference = clip.duration_preference || {};
        const durationStatus = String(durationPreference.status || reviewFlags.duration_preference || (
            durationSeconds <= 180 ? "curto_preferencial" : "longo_para_revisao"
        ));
        const durationException = [durationPreference.exception, reviewFlags.duration_exception].some((value) => safeBooleanFlag(value))
            || durationStatus === "excecao_contextual";
        const durationPolicyMeta = {
            curto_preferencial: {
                label: "Corte curto por preferência",
                hint: "O menor intervalo autossuficiente foi priorizado; hook, contexto e fecho permanecem juntos.",
                icon: "bolt",
                className: "preferred",
            },
            excecao_contextual: {
                label: "Exceção contextual acima de 3 min",
                hint: "O corte foi mantido mais longo porque encurtar poderia remover pergunta, prova, argumento ou conclusão.",
                icon: "account_tree",
                className: "exception",
            },
            longo_para_revisao: {
                label: "Acima da preferência de 3 min",
                hint: "A duração não é proibida, mas vale revisar se o mesmo contexto pode ser preservado em menos tempo.",
                icon: "schedule",
                className: "review",
            },
        };
        const durationMeta = durationPolicyMeta[durationStatus] || durationPolicyMeta.curto_preferencial;
        const campaignPrior = clip.campaign_hub_prior || {};
        const contextualHook = clip.contextual_hook || {};
        const contextualPayoffSignals = Array.isArray(contextualHook.payoff_signals)
            ? contextualHook.payoff_signals.map((signal) => String(signal || "").trim()).filter(Boolean).slice(0, 3)
            : [];
        const contextualHookAvailable = Boolean(contextualHook.hook_text || contextualHook.family);
        const contextualHookScoreValue = Number(contextualHook.score);
        const contextualHookScoreLabel = Number.isFinite(contextualHookScoreValue)
            ? `${Math.max(0, Math.min(100, contextualHookScoreValue)).toFixed(1)}/100`
            : "score não validado";
        const contextualPayoffConfirmed = safeBooleanFlag(contextualHook.payoff_confirmed);
        const contextualHookReview = [clip.hook_review_required, reviewFlags.hook_review_required, reviewFlags.visual_evidence_review_required].some((value) => safeBooleanFlag(value));
        const contextualHookReviewReasons = [];
        if (contextualHookReview) {
            if (speakerReviewRequired || clip.speaker_turn_valid == null) contextualHookReviewReasons.push("locutor não diarizado");
            if (contextualHook.audio_signal && contextualHook.audio_signal.available === false) contextualHookReviewReasons.push("áudio sem sinal contextual");
            if ([clip.overlap_suspected, reviewFlags.overlap_suspected].some((value) => safeBooleanFlag(value))) contextualHookReviewReasons.push("possível sobreposição");
            if (contextualHook.visual_evidence_required || contextualHook.visual_review_reason) contextualHookReviewReasons.push(String(contextualHook.visual_review_reason || "confirmar gráfico, pesquisa ou imagem mencionada"));
        }
        const contextualHookReviewHint = contextualHookReviewReasons.join(" · ") || "confirmar no vídeo";
        const transcriptionCoverageStatus = String(clip.transcription_coverage_status || reviewFlags.transcription_coverage_status || clip.review_provenance?.transcript_coverage_status || "").trim().toLowerCase();
        const transcriptionCoverageNeedsReview = ["partial", "mismatch_suspected", "empty", "unknown"].includes(transcriptionCoverageStatus);
        const transcriptionReviewRequired = [clip.transcription_review_required, reviewFlags.transcription_review_required].some((value) => safeBooleanFlag(value))
            || transcriptionCoverageNeedsReview;
        const transcriptionReviewReasons = {
            partial: "cobertura parcial da transcrição; confirme o trecho no vídeo",
            mismatch_suspected: "a transcrição pode pertencer a outra fonte; confirme identidade e trecho no vídeo",
            empty: "a transcrição não tem segmentos utilizáveis; confirme o trecho diretamente no vídeo",
            unknown: "a cobertura temporal da transcrição não foi validada; confirme o trecho no vídeo",
        };
        const transcriptionReviewReason = String(clip.transcription_review_reason || reviewFlags.transcription_review_reason || transcriptionReviewReasons[transcriptionCoverageStatus] || "identidade temporal da transcrição não validada; confirme o trecho no vídeo").trim();
        const campaignPriorAvailable = [campaignPrior.available, reviewFlags.campaign_hub_prior_available].some((value) => safeBooleanFlag(value));
        const campaignHookFamily = String(campaignPrior.hook_family || reviewFlags.campaign_hub_hook_family || "").trim();
        const campaignSampleCount = safeNonNegativeCount(campaignPrior.sample_count, reviewFlags.campaign_hub_sample_count);
        const feedbackCalibration = clip.feedback_calibration || {};
        const feedbackDurationSignal = feedbackCalibration.duration_signal || {};
        const feedbackCalibrationAvailable = [feedbackCalibration.eligible, reviewFlags.feedback_calibration_eligible].some((value) => safeBooleanFlag(value));
        const feedbackSampleSize = safeNonNegativeCount(feedbackCalibration.sample_size, reviewFlags.feedback_sample_size);
        const feedbackDurationGap = Number(feedbackDurationSignal.gap_seconds ?? reviewFlags.feedback_duration_gap_seconds ?? 0);
        const reviewStatus = reviewStatusOf(clip);
        const reviewMeta = reviewStatusMeta(reviewStatus);
        const rawConfidence = Number(clip.confidence);
        const confidence = Number.isFinite(rawConfidence)
            ? Math.round(Math.max(0, Math.min(1, rawConfidence)) * 100)
            : 0;
        const clipSource = clip.source || "nlp";
        const sourceLabels = { "gemini": "Gemini Flash", "llm": "Ollama", "nlp": "NLP local" };
        const sourceLabel = sourceLabels[clipSource] || "NLP";
        const sourceClass = clipSource === "gemini" ? "source-gemini" : (clipSource === "llm" ? "source-llm" : "source-nlp");
        const candidateOrigin = String(clip.candidate_origin || "local_primary");
        const candidateOriginLabel = String(clip.candidate_origin_label || "Origem local registrada");
        const candidateOriginNote = String(clip.candidate_origin_note || "Origem registrada para transparência da revisão.");
        const reviewProvenance = clip.review_provenance || {};
        const transcriptSourceLabels = {
            manual: "transcrição manual",
            public_subtitle: "legenda pública",
            gemini_video: "Gemini multimodal",
            whisper: "Whisper local",
            automatic: "transcrição automática",
            unknown: "origem não identificada",
        };
        const contextSourceLabels = {
            local_dossier: "dossiê local",
            multimodal_auxiliary: "evidência multimodal auxiliar",
            none: "sem dossiê contextual",
        };
        const provenanceSource = transcriptSourceLabels[String(reviewProvenance.transcript_source || "unknown")] || "origem não identificada";
        const provenanceCoverageCode = String(reviewProvenance.transcript_coverage_status || "unknown").trim().toLowerCase();
        const provenanceCoverageLabels = {
            complete: "cobertura integral",
            covered: "cobertura integral",
            partial: "cobertura parcial · revisar",
            mismatch_suspected: "fonte possivelmente incompatível · revisar",
            empty: "sem cobertura utilizável · revisar",
            pending: "cobertura pendente · revisar",
            unknown: "cobertura não validada · revisar",
        };
        const provenanceCoverage = provenanceCoverageLabels[provenanceCoverageCode] || `cobertura ${provenanceCoverageCode || "não validada"} · revisar`;
        const provenanceContext = contextSourceLabels[String(reviewProvenance.context_source || "none")] || "sem dossiê contextual";
        const provenanceMarkup = reviewProvenance.transcript_source || reviewProvenance.context_source
            ? `<div class="clip-provenance-note"><span class="material-icons-round">source</span><span><b>Base usada no corte:</b> ${escapeHtml(provenanceSource)} · ${escapeHtml(provenanceCoverage)} · ${escapeHtml(provenanceContext)}${reviewProvenance.transcript_archive_present ? " · arquivo persistente presente" : ""}</span></div>`
            : "";
        const originClass = candidateOrigin === "local_fallback" ? "candidate-origin-fallback" : "candidate-origin-primary";
        const transcriptId = `transcript-${originalIndex}`;
        const layoutMeta = layoutMetaForClip(clip);
        const editorialBlock = clip.editorial_block || {};
        const blockTags = Array.isArray(editorialBlock.tags) ? editorialBlock.tags : [];
        const latestAdjustment = clip.latest_adjustment || {};
        const adjustmentState = clip.adjustment_state || (latestAdjustment.start != null ? "saved" : "");
        const clipTranscriptText = String(clip.text || clip.transcript || "");
        const qualityScorecard = clip.quality_scorecard && typeof clip.quality_scorecard === "object" ? clip.quality_scorecard : {};
        const qualityScorecardItems = [
            ["context", "Contexto", "account_tree"],
            ["editorial_strength", "Força editorial", "bolt"],
            ["technical", "Técnica", "graphic_eq"],
            ["confidence", "Confiança", "verified"],
        ];
        const qualityStatus = String(qualityScorecard.status || "").trim().toLowerCase();
        const qualityGateStatus = String(qualityScorecard.gate_status || "").trim().toLowerCase();
        const qualityRequiresReview = qualityStatus === "review_required"
            || ["review", "weak", "review_required", "blocked"].includes(qualityStatus)
            || ["review", "weak", "review_required", "blocked"].includes(qualityGateStatus);
        const qualityStatusLabel = qualityRequiresReview ? "revisão necessária" : qualityStatus === "candidate" ? "candidato" : "status não informado";
        const qualityScorecardMarkup = qualityScorecardItems.some(([key]) => Number.isFinite(Number(qualityScorecard[key])))
            ? `<section class="clip-quality-scorecard" aria-label="Scorecard de qualidade do corte">
                <div class="clip-quality-scorecard-head"><span><span class="material-icons-round">analytics</span><b>Scorecard de qualidade</b></span><span class="clip-quality-status ${qualityRequiresReview ? "review" : "candidate"}">${escapeHtml(qualityStatusLabel)}</span></div>
                <div class="clip-quality-scorecard-grid">${qualityScorecardItems.map(([key, label, icon]) => {
                    const rawValue = Number(qualityScorecard[key]);
                    const value = Number.isFinite(rawValue) ? Math.max(0, Math.min(100, rawValue)) : 0;
                    return `<div class="clip-quality-score"><span class="material-icons-round">${icon}</span><span class="clip-quality-score-label">${label}</span><strong>${Math.round(value)}</strong><div class="clip-quality-score-track"><i style="width:${value}%"></i></div></div>`;
                }).join("")}</div>
                <small>São dimensões independentes: um corte pode ter força editorial alta e ainda exigir revisão técnica ou de contexto.</small>
            </section>`
            : "";
        const reviewBusy = safeBooleanFlag(clip.review_busy);
        const feedbackReasonOptions = [
            ["", "Motivo opcional"],
            ["excellent_context", "Contexto e payoff excelentes"],
            ["good_hook", "Hook forte"],
            ["too_long", "Bom, mas longo"],
            ["missing_context", "Sem contexto suficiente"],
            ["starts_late", "Começa no meio da fala"],
            ["no_payoff", "Não conclui o raciocínio"],
            ["wrong_speaker", "Orador errado ou incerto"],
            ["bad_framing", "Enquadramento ruim"],
            ["audio_overlap", "Áudio sobreposto ou confuso"],
            ["duplicate", "Repetido ou parecido com outro"],
            ["fact_review", "Precisa de revisão factual"],
        ];
        const feedbackReasonLabels = Object.fromEntries(feedbackReasonOptions.filter(([value]) => value).map(([value, label]) => [value, label]));
        const savedFeedbackReason = String(clip.latest_feedback_reason || "").trim();
        const savedFeedbackReasonLabel = feedbackReasonLabels[savedFeedbackReason] || ({
            editor_approved: "Decisão aprovada pelo editor",
            editor_rejected: "Decisão rejeitada pelo editor",
            context_review: "Separado para revisar contexto",
        }[savedFeedbackReason] || (savedFeedbackReason ? savedFeedbackReason.replaceAll("_", " ") : ""));
        const feedbackReasonMarkup = `<div class="clip-feedback-controls"><label for="feedback-reason-${originalIndex}"><span class="material-icons-round">label</span><span>Motivo rápido</span></label><select id="feedback-reason-${originalIndex}" data-feedback-reason="${originalIndex}">${feedbackReasonOptions.map(([value, label]) => `<option value="${value}" ${String(clip.latest_feedback_reason || "") === value ? "selected" : ""}>${label}</option>`).join("")}</select></div>`;

        // Grade color helper
        const gradeColor = (grade) => {
            if (grade === 'A') return '#22c55e';
            if (grade === 'B') return '#f59e0b';
            return '#ef4444';
        };

        const card = document.createElement("div");
        card.className = `result-card review-${reviewStatus}`;
        card.innerHTML = `
            <div class="result-header-bar" style="position:relative">
                <div class="result-rank">#${rank}</div>
                <div class="viral-score-badge ${scoreClass}">
                    <span class="material-icons-round">trending_up</span>
                    <span class="score-value">${displayScore}</span>
                    <span class="score-label">/100</span>
                </div>
                ${clip.has_hook ? '<span class="hook-badge"><span class="material-icons-round" style="font-size:12px">flash_on</span> Gancho</span>' : ''}
                <span class="clip-source-badge ${sourceClass}">${sourceLabel}</span>
                <span class="candidate-origin-badge ${originClass}" title="${escapeHtml(candidateOriginNote)}"><span class="material-icons-round">${candidateOrigin === "local_fallback" ? "alt_route" : "verified"}</span>${escapeHtml(candidateOriginLabel)}</span>
                ${politicalType ? `<span class="clip-source-badge source-editorial">${escapeHtml(politicalType)}</span>` : ''}
                <span class="review-state-chip ${reviewMeta.label === "APROVADO" ? "approved" : reviewMeta.label === "REJEITADO" ? "rejected" : reviewStatus}" title="${escapeHtml(reviewMeta.hint)}" aria-label="${escapeHtml(reviewMeta.hint)}"><span class="material-icons-round">${escapeHtml(reviewMeta.icon)}</span>${escapeHtml(reviewMeta.label)}</span>
                ${savedFeedbackReasonLabel ? `<span class="clip-feedback-reason-chip ${reviewStatus}" title="Motivo editorial salvo com a decisão" aria-label="Motivo editorial salvo: ${escapeHtml(savedFeedbackReasonLabel)}"><span class="material-icons-round">label</span><span>${escapeHtml(savedFeedbackReasonLabel)}</span></span>` : ''}
                ${clip.review_updated_at ? `<span class="clip-review-timestamp" title="Decisão registrada localmente">${new Date(clip.review_updated_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</span>` : ''}
                ${adjustmentState === "saved" ? '<span class="clip-adjustment-chip saved"><span class="material-icons-round">save</span> ajuste salvo</span>' : ''}
                ${adjustmentState === "preview" ? '<span class="clip-adjustment-chip preview"><span class="material-icons-round">preview</span> prévia</span>' : ''}
            </div>

            ${clip.title ? `<div class="result-title">${escapeHtml(clip.title)}</div>` : ''}

            <div class="result-video-preview">
                <video controls preload="metadata" poster="">
                    <source src="${mediaUrlForClip(clip)}" type="video/mp4">
                </video>
            </div>
            <div class="result-info">
                ${politicalType ? `<div style="font-size:12px; color:#f59e0b; margin-bottom:6px"><span class="material-icons-round" style="font-size:14px; vertical-align:middle">account_balance</span> Formato editorial: ${escapeHtml(politicalType)}</div>` : ''}
                ${visualFormat ? `<div class="clip-visual-format-note ${preserveComposition ? 'preserve' : ''}"><span class="material-icons-round">${preserveComposition ? 'aspect_ratio' : 'center_focus_strong'}</span><span><b>${escapeHtml(visualFormatLabels[visualFormat] || visualFormat)}</b> · ${preserveComposition ? 'preservar composição' : 'reframe somente se seguro'}${Number.isFinite(visualFormatConfidence) ? ` · ${Math.round(Math.max(0, Math.min(1, visualFormatConfidence)) * 100)}%` : ''}${clip.visual_format_reason ? ` — ${escapeHtml(String(clip.visual_format_reason))}` : ''}</span></div>` : ''}
                ${framingMode ? `<div class="clip-visual-format-note ${framingMode === 'face_tracking' ? '' : 'preserve'}"><span class="material-icons-round">${framingMode === 'face_tracking' ? 'center_focus_strong' : 'aspect_ratio'}</span><span><b>Enquadramento: ${escapeHtml(framingLabels[framingMode] || framingMode)}</b>${Number.isFinite(framingConfidence) ? ` · ${Math.round(Math.max(0, Math.min(1, framingConfidence)) * 100)}%` : ''}${framingReason ? ` — ${escapeHtml(framingReason)}` : ''}</span></div>` : ''}
                ${multimodalIdentityReview ? `<div class="clip-review-risk ${multimodalIdentityStatus === 'mismatch' ? 'legal' : ''}"><span class="material-icons-round">visibility_off</span><span><b>Identidade multimodal:</b> ${escapeHtml(multimodalIdentityLabel)}${Number.isFinite(multimodalIdentityConfidence) ? ` · ${Math.round(Math.max(0, Math.min(1, multimodalIdentityConfidence)) * 100)}%` : ''}</span></div>` : ''}
                ${clip.visual_observation ? `<div class="clip-visual-observation"><span class="material-icons-round">visibility</span><span><b>Evidência visual:</b> ${escapeHtml(String(clip.visual_observation))}${Number.isFinite(Number(clip.visual_observation_confidence)) ? ` · ${Math.round(Math.max(0, Math.min(1, Number(clip.visual_observation_confidence))) * 100)}% de confiança` : ''}</span></div>` : ''}
                ${(chapterCount > 0 || qaBoundaryBasis) ? `<div class="clip-chapter-note ${chapterCount > 0 && chapterScore < 60 ? 'warning' : ''}"><span class="material-icons-round">account_tree</span><span><b>Contexto temporal:</b> ${chapterCount > 0 ? `${chapterCount} capítulo(s)${Number.isFinite(chapterScore) ? ` · coerência ${Math.round(Math.max(0, Math.min(100, chapterScore)))}%` : ''}${chapterBridge ? ' · ponte pergunta–resposta preservada' : chapterCount > 1 ? ' · atravessa capítulos; revisar continuidade' : ' · dentro do mesmo bloco'}` : 'fronteira Q&A registrada'}${qaBoundaryBasis ? ` · fronteira: ${escapeHtml(qaBoundaryLabel)}${qaBoundaryReviewRequired ? ' · confirmar locutor' : ''}` : ''}</span></div>` : ''}
                ${campaignPriorAvailable ? `<div class="clip-performance-prior"><span class="material-icons-round">insights</span><span><b>Histórico observado:</b> hook ${escapeHtml(campaignHookFamily || 'não classificado')} · amostra ${Math.max(0, campaignSampleCount)} · influência limitada ao ranking</span></div>` : ''}
                ${transcriptionReviewRequired ? `<div class="clip-review-risk"><span class="material-icons-round">history_edu</span><span><b>Transcrição para revisão:</b> ${escapeHtml(transcriptionReviewReason)}${transcriptionCoverageStatus ? ` · status ${escapeHtml(transcriptionCoverageStatus)}` : ''}</span></div>` : ''}
                ${provenanceMarkup}
                ${contextualHookAvailable ? `<div class="clip-hook-provenance ${contextualHookReview ? 'review' : ''}"><span class="material-icons-round">bolt</span><span><b>Hook contextual:</b> ${escapeHtml(String(contextualHook.family || 'não classificado'))} · ${contextualHookScoreLabel}${contextualPayoffConfirmed ? ' · payoff próximo' : ' · payoff a confirmar'}${contextualHookReview ? ` · ${escapeHtml(contextualHookReviewHint)}` : ''}<br><q>${escapeHtml(String(contextualHook.hook_text || ''))}</q>${contextualPayoffSignals.length ? `<small class="clip-hook-payoff-signals">Evidência: ${escapeHtml(contextualPayoffSignals.join(' · '))}</small>` : ''}</span></div>` : ''}
                ${contextRecoveryApplied ? `<div class="clip-review-risk"><span class="material-icons-round">history</span><span><b>Abertura ampliada para contexto:</b> ${escapeHtml(contextRecoveryLabel)}${Number.isFinite(Number(contextRecovery.original_start)) && Number.isFinite(Number(contextRecovery.added_start)) ? ` · início recuperado de ${formatTime(contextRecovery.original_start)} para ${formatTime(contextRecovery.added_start)}` : ''}${Number.isFinite(Number(contextRecovery.gap_seconds)) ? ` · pausa ${Number(contextRecovery.gap_seconds).toFixed(1)}s` : ''} · confirme se o antecedente realmente explica o hook.</span></div>` : ''}
                ${feedbackCalibrationAvailable ? `<div class="clip-feedback-prior"><span class="material-icons-round">tune</span><span><b>Feedback editorial aplicado:</b> ${Math.max(0, feedbackSampleSize)} decisões finais${Math.abs(feedbackDurationGap) >= 0.1 ? ` · aprovados ${feedbackDurationGap > 0 ? 'tendem a ser mais curtos' : 'tiveram duração média maior'} em ${Math.abs(feedbackDurationGap).toFixed(1)}s` : ''} · influência limitada</span></div>` : ''}
                ${(needsFactReview || needsLegalReview) ? `<div class="clip-review-risk ${needsLegalReview ? 'legal' : ''}"><span class="material-icons-round">${needsLegalReview ? 'gavel' : 'fact_check'}</span> ${needsLegalReview ? 'Revisão factual e jurídica' : 'Revisão factual recomendada'}</div>` : ''}
                ${entityContextReviewRequired ? `<div class="clip-review-risk"><span class="material-icons-round">manage_search</span><span><b>Entidade para confirmar:</b> ${escapeHtml(entityContextReviewHint)} O nome não é usado sozinho para classificar o tema.</span></div>` : ''}
                ${speakerReviewRequired ? `<div class="clip-review-risk"><span class="material-icons-round">record_voice_over</span><span><b>Locutor/ponte para confirmar:</b> ${escapeHtml(speakerReviewReason)}</span></div>` : ''}
                ${topicReviewRequired ? `<div class="clip-review-risk"><span class="material-icons-round">account_tree</span><span><b>Continuidade do tópico para confirmar:</b> ${escapeHtml(topicReviewReason)}</span></div>` : ''}
                ${topicSignature ? `<div class="clip-topic-chip" title="Sinal lexical usado somente para diversificar o portfólio">Tema: ${escapeHtml(topicSignature.replace(':', ' · ').replaceAll('-', ', '))}</div>` : ''}
                ${durationStatus ? `<div class="clip-duration-policy ${durationMeta.className}" title="${escapeHtml(String(durationPreference.reason || durationMeta.hint))}"><span class="material-icons-round">${durationMeta.icon}</span><span><b>${escapeHtml(durationMeta.label)}</b>${Number.isFinite(durationFit) ? ` · brevidade ${Math.round(Math.max(0, Math.min(100, durationFit)))}%` : ''}${durationException ? ' · contexto excepcional preservado' : ''}</span></div>` : ''}
                ${closureType ? `<div class="clip-closure-chip ${escapeHtml(closureType)}"><span class="material-icons-round">${closureType === 'conclusion' ? 'task_alt' : closureType === 'cliffhanger' ? 'hourglass_top' : 'subtitles'}</span> ${escapeHtml(closureLabels[closureType] || closureType)}</div>` : ''}
                ${contextReferenceFlag ? `<div class="clip-review-risk"><span class="material-icons-round">link_off</span><span><b>Abertura dependente:</b> o trecho começa com uma referência sem antecedente claro.</span></div>` : ''}
                ${weakPayoffFlag ? `<div class="clip-review-risk"><span class="material-icons-round">pending</span><span><b>Payoff a revisar:</b> o final pode continuar o raciocínio em vez de concluí-lo.</span></div>` : ''}
                ${(speakerLabel || overlapSuspected || Number.isFinite(speakerConfidence)) ? `<div class="clip-speaker-note ${overlapSuspected ? 'warning' : ''}"><span class="material-icons-round">${overlapSuspected ? 'record_voice_over' : 'person'}</span> ${speakerLabel ? `Locutor: ${escapeHtml(speakerLabel)}` : 'Locutor não identificado'}${Number.isFinite(speakerConfidence) ? ` · ${Math.round(Math.max(0, Math.min(1, speakerConfidence)) * 100)}%` : ''}${overlapSuspected ? ' · possível sobreposição' : ''}</div>` : ''}
                ${diversityPenalty >= 20 ? `<div class="clip-diversity-note"><span class="material-icons-round">filter_list</span> Similaridade com outro corte: ${diversityPenalty}%${diversityReason ? ` · ${escapeHtml(diversityReason)}` : ''}</div>` : ''}
                <div class="result-duration">
                    <span class="material-icons-round" style="font-size:14px">schedule</span>
                    ${formatTime(clip.start)} - ${formatTime(clip.end)} (${displayDurationSeconds.toFixed(1)}s)
                </div>
                ${qualityScorecardMarkup}
                ${(editorialBlock.thesis || editorialBlock.context_summary || blockTags.length) ? `<div class="editorial-block-dossier">
                    <div class="editorial-block-kicker"><span class="material-icons-round">inventory_2</span> Dossiê do bloco · ${escapeHtml(editorialBlock.state || "candidato")}</div>
                    ${editorialBlock.thesis ? `<strong>${escapeHtml(editorialBlock.thesis)}</strong>` : ''}
                    ${editorialBlock.context_summary ? `<p>${escapeHtml(editorialBlock.context_summary)}</p>` : ''}
                    ${editorialBlock.moment_reason ? `<small><b>Momento:</b> ${escapeHtml(editorialBlock.moment_reason)}</small>` : ''}
                    ${blockTags.length ? `<div class="editorial-block-tags">${blockTags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join('')}</div>` : ''}
                </div>` : ''}
                <button class="btn btn-sm btn-boundary-toggle" onclick="toggleBoundaryEditor(${originalIndex})" title="Remover falas desnecessárias antes ou depois do trecho"><span class="material-icons-round">content_cut</span> Cortar fala antes/depois</button>
                <div class="clip-boundary-editor" id="boundary-editor-${originalIndex}" hidden>
                    <div class="clip-boundary-fields">
                        <label>Entrada <input type="number" min="0" step="0.1" data-boundary-start="${originalIndex}" value="${Number(clip.start || 0).toFixed(1)}"></label>
                        <label>Saída <input type="number" min="0" step="0.1" data-boundary-end="${originalIndex}" value="${Number(clip.end || 0).toFixed(1)}"></label>
                        <button class="btn btn-sm btn-primary" onclick="previewClipBoundary(${originalIndex})"><span class="material-icons-round">preview</span> Pré-visualizar</button>
                        <button class="btn btn-sm btn-success" onclick="persistClipBoundary(${originalIndex})" ${clip.clip_id ? "" : "disabled"}><span class="material-icons-round">save</span> Salvar ajuste</button>
                    </div>
                    <small><b>Como usar:</b> Entrada = primeiro segundo útil; saída = último segundo útil. “Pré-visualizar” atualiza somente este card e mantém o arquivo original. “Salvar ajuste” registra a decisão para o próximo render; não cria um MP4 novo nesta etapa.</small>
                    <div class="clip-boundary-feedback" id="boundary-feedback-${originalIndex}" aria-live="polite"></div>
                </div>
                <div class="review-format-chip" title="${escapeHtml(layoutMeta.hint)}"><span class="material-icons-round">${escapeHtml(layoutMeta.icon)}</span>${escapeHtml(layoutMeta.label)}</div>
                <div class="clip-storyline" aria-label="Jornada editorial do corte">
                    <div class="clip-storyline-header"><span>Jornada editorial</span><span>${clip.has_hook ? "gancho identificado" : "abertura a revisar"}</span></div>
                    <div class="clip-storyline-track">
                        <span class="story-marker hook" style="left: 9%">entrada</span>
                        <span class="story-marker" style="left: 50%">ideia</span>
                        <span class="story-marker payoff" style="left: 91%">fecho</span>
                    </div>
                </div>

                ${breakdown.hook ? `
                <div class="score-breakdown-grades">
                    <div class="grade-item">
                        <span class="grade-label">Gancho</span>
                        <span class="grade-value" style="color:${gradeColor(breakdown.hook)}">${breakdown.hook}</span>
                    </div>
                    <div class="grade-item">
                        <span class="grade-label">Fluidez</span>
                        <span class="grade-value" style="color:${gradeColor(breakdown.flow)}">${breakdown.flow}</span>
                    </div>
                    <div class="grade-item">
                        <span class="grade-label">Valor</span>
                        <span class="grade-value" style="color:${gradeColor(breakdown.value)}">${breakdown.value}</span>
                    </div>
                    <div class="grade-item">
                        <span class="grade-label">Energia</span>
                        <span class="grade-value" style="color:${gradeColor(breakdown.energy)}">${breakdown.energy}</span>
                    </div>
                </div>` : ''}

                ${Object.keys(factors).length > 0 ? `
                <div class="editorial-factors" style="margin:10px 0; padding:10px; border-radius:8px; background:rgba(255,255,255,0.04)">
                    <div style="display:flex; justify-content:space-between; gap:8px; font-size:12px; opacity:.9; margin-bottom:6px">
                        <span>Potencial editorial explicável</span><span>Confiança: ${confidence}%</span>
                    </div>
                    ${Object.entries(factors).filter(([key]) => key !== 'diversity').slice(0, 7).map(([key, value]) => `
                        <div style="display:flex; align-items:center; gap:8px; margin:4px 0; font-size:11px">
                            <span style="width:112px">${escapeHtml(key.replaceAll('_', ' '))}</span>
                            <div style="flex:1; height:5px; background:rgba(255,255,255,.12); border-radius:4px"><div style="width:${Math.max(0, Math.min(100, Number(value)))}%; height:100%; background:#f59e0b; border-radius:4px"></div></div>
                            <span style="width:28px; text-align:right">${Number(value).toFixed(0)}</span>
                        </div>`).join('')}
                    ${clip.reason ? `<div style="font-size:11px; opacity:.75; margin-top:7px">${escapeHtml(clip.reason)}</div>` : ''}
                </div>` : ''}

                <div class="result-text-preview">${clip.text ? escapeHtml(clip.text.substring(0, 150) + (clip.text.length > 150 ? '...' : '')) : "Sem transcricao"}</div>

                ${clip.text ? `
                <button class="btn-show-transcript" onclick="toggleTranscript('${transcriptId}')">
                    <span class="material-icons-round" style="font-size:14px">description</span>
                    Ver Transcricao
                </button>
                <div class="clip-transcript" id="${transcriptId}">
                    <div class="clip-transcript-content">${escapeHtml(clip.text)}</div>
                </div>` : ''}

                <div class="result-actions">
                    <button class="btn btn-sm btn-primary" onclick="downloadClip(${originalIndex})">
                        <span class="material-icons-round">download</span> Baixar corte
                    </button>
                    <button class="btn btn-sm btn-headline-action" onclick="toggleClipHeadlineStudio(${originalIndex})">
                        <span class="material-icons-round">title</span> Headline do corte
                    </button>
                </div>
                <div class="clip-headline-studio" id="clip-headline-studio-${originalIndex}" hidden>
                    <div class="clip-headline-studio-header">
                        <div><span class="artwork-format-kicker">ESTÚDIO DO CORTE</span><h4>Headline baseada neste intervalo</h4></div>
                        <span class="clip-headline-source">Transcrição + contexto + formato</span>
                    </div>
                    <div class="clip-headline-studio-grid">
                        <label>Transcrição do corte
                            <textarea data-clip-headline-transcript rows="6" placeholder="A transcrição deste corte aparecerá aqui para revisão.">${escapeHtml(clipTranscriptText)}</textarea>
                        </label>
                        <div class="clip-headline-controls">
                            <label>Formato de publicação
                                <select data-clip-headline-format>
                                    <option value="auto">Escolher por mim</option>
                                    <option value="vertical_916">9:16 central</option>
                                    <option value="square_alfinetei">1:1 Alfinetei</option>
                                    <option value="fake_tweet">Fake tweet</option>
                                </select>
                            </label>
                            <label>Minicontexto opcional
                                <textarea data-clip-headline-context rows="3" maxlength="280" placeholder="Ex.: resposta de Renan sobre propostas econômicas.">${escapeHtml(clip.title || "")}</textarea>
                            </label>
                            <button class="btn btn-sm btn-primary" type="button" data-generate-clip-headline onclick="generateClipHeadline(${originalIndex})"><span class="material-icons-round">bolt</span> Gerar headline deste formato</button>
                        </div>
                    </div>
                    <div class="clip-headline-results" id="clip-headline-results-${originalIndex}" aria-live="polite"><p class="clip-headline-feedback">Edite a transcrição se necessário e escolha o formato antes de gerar.</p></div>
                </div>
                ${feedbackReasonMarkup}
                <div class="review-actions" aria-label="Decisão editorial">
                    <button class="btn btn-sm btn-success ${reviewStatus === 'approved' ? 'is-current' : ''}" ${reviewBusy ? 'disabled' : ''} aria-pressed="${reviewStatus === 'approved'}" onclick="setClipReview(${originalIndex}, 'approved')"><span class="material-icons-round">check_circle</span>${reviewBusy ? 'Salvando…' : reviewStatus === 'approved' ? 'Aprovado' : 'Aprovar'}</button>
                    <button class="btn btn-sm btn-review-context ${reviewStatus === 'needs_review' ? 'is-current' : ''}" ${reviewBusy ? 'disabled' : ''} aria-pressed="${reviewStatus === 'needs_review'}" title="Não aprova nem rejeita; abre a transcrição completa e coloca o clip na fila de revisão." onclick="openContextReview(${originalIndex})"><span class="material-icons-round">visibility</span>${reviewBusy ? 'Salvando…' : reviewStatus === 'needs_review' ? 'Contexto aberto' : 'Revisar contexto'}</button>
                    <button class="btn btn-sm btn-danger ${reviewStatus === 'rejected' ? 'is-current' : ''}" ${reviewBusy ? 'disabled' : ''} aria-pressed="${reviewStatus === 'rejected'}" onclick="setClipReview(${originalIndex}, 'rejected')"><span class="material-icons-round">close</span>${reviewBusy ? 'Salvando…' : reviewStatus === 'rejected' ? 'Rejeitado' : 'Rejeitar'}</button>
                </div>
            </div>`;

        grid.appendChild(card);
    });

    if (clips.length === 0) {
        grid.innerHTML = `<div class="review-empty-state"><span class="material-icons-round">filter_alt_off</span><strong>Nenhum corte nesta fila</strong><p>Altere o filtro para revisar os outros candidatos.</p></div>`;
    }
}

function toggleBoundaryEditor(index) {
    const editor = document.getElementById(`boundary-editor-${index}`);
    if (!editor) return;
    editor.hidden = !editor.hidden;
}

async function previewClipBoundary(index) {
    const clip = state.clips[index];
    if (!clip) return;
    const startInput = document.querySelector(`[data-boundary-start="${index}"]`);
    const endInput = document.querySelector(`[data-boundary-end="${index}"]`);
    const feedback = document.getElementById(`boundary-feedback-${index}`);
    const start = Number(startInput?.value);
    const end = Number(endInput?.value);
    if (!Number.isFinite(start) || !Number.isFinite(end)) {
        if (feedback) feedback.textContent = "Informe entrada e saída válidas.";
        return;
    }
    const rawSourceDuration = Number(clip.source_duration ?? clip.video_duration ?? clip.duration);
    const sourceDuration = Number.isFinite(rawSourceDuration) && rawSourceDuration > 0 ? rawSourceDuration : null;
    if (sourceDuration !== null && (start < 0 || end > sourceDuration)) {
        if (feedback) feedback.textContent = `Os limites precisam ficar entre 0:00 e ${formatTime(sourceDuration)}.`;
        return;
    }
    if (end <= start) {
            if (feedback) feedback.textContent = "A saída precisa ser maior que a entrada.";
            return;
        }
        if (feedback) feedback.textContent = "Localizando limites seguros e removendo sobras de fala...";
    try {
        const response = await fetch("/api/clips/adjust", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                clip,
                start,
                end,
                duration: sourceDuration,
                transcript_segments: clip.transcript_segments || clip.segments || [],
            }),
        });
        const data = await parseJsonResponse(response, "Ajuste de limites");
        if (!response.ok || data.error) throw new Error(data.error || "Não foi possível ajustar os limites");
        const originalBounds = clip.original_bounds || {
            start: Number(clip.original_start ?? clip.start ?? 0),
            end: Number(clip.original_end ?? clip.end ?? 0),
            duration: Number(clip.original_duration ?? clip.duration ?? 0),
        };
        state.clips[index] = {
            ...clip,
            ...data.clip,
            original_bounds: originalBounds,
            adjustment_state: "preview",
            latest_adjustment: { ...data.clip, render_status: "preview_only" },
        };
        renderReviewCommandCenter();
        renderResultsGrid();
        const removedBefore = Math.max(0, Number(data.clip.start || 0) - Number(originalBounds.start || 0));
        const removedAfter = Math.max(0, Number(originalBounds.end || 0) - Number(data.clip.end || 0));
        const removalSummary = `Removeu ${removedBefore.toFixed(1)}s antes e ${removedAfter.toFixed(1)}s depois`;
        const boundary = data.clip.boundary_adjustment || {};
        const snapped = [boundary.snapped_start, boundary.snapped_end].some((value) => safeBooleanFlag(value));
        const boundarySummary = snapped
            ? "Os limites foram aproximados aos blocos da transcrição para evitar cortar uma fala."
            : "Os limites permaneceram exatamente como informados manualmente.";
        if (feedback) feedback.textContent = `Prévia aplicada: ${formatTime(data.clip.start)}–${formatTime(data.clip.end)}. ${boundarySummary} ${removalSummary}. Nada foi salvo ainda; revise o vídeo e clique em “Salvar ajuste” somente se estiver limpo.`;
        showToast(`Prévia limpa aplicada. ${snapped ? "Limites alinhados à transcrição." : "Limites manuais."}`, "success");
    } catch (error) {
        if (feedback) feedback.textContent = error.message;
        showToast(error.message, "error");
    }
}

async function persistClipBoundary(index) {
    const clip = state.clips[index];
    if (!clip) return;
    const feedback = document.getElementById(`boundary-feedback-${index}`);
    if (!clip.clip_id) {
        if (feedback) feedback.textContent = "Este resultado ainda não possui um registro persistente.";
        return;
    }
    const adjustment = {
        ...(clip.latest_adjustment || {
            start: Number(clip.start),
            end: Number(clip.end),
            duration: Number.isFinite(Number(clip.duration))
                ? Number(clip.duration)
                : Math.max(0, Number(clip.end) - Number(clip.start)),
        }),
        boundary_adjustment: {
            ...(clip.latest_adjustment?.boundary_adjustment || clip.boundary_adjustment || {}),
            source: (clip.latest_adjustment?.boundary_adjustment?.source || clip.boundary_adjustment?.source) === "transcript"
                ? "transcript"
                : "manual",
        },
    };
    if (!Number.isFinite(Number(adjustment.start)) || !Number.isFinite(Number(adjustment.end))) {
        if (feedback) feedback.textContent = "Pré-visualize limites válidos antes de salvar.";
        return;
    }
    if (feedback) feedback.textContent = "Salvando ajuste editorial...";
    try {
        const response = await fetch(`/api/clips/${clip.clip_id}/adjust`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                adjustment,
                note: "Corte limpo: removidas falas desnecessárias antes/depois do trecho.",
                transcript_segments: clip.transcript_segments || clip.segments || [],
            }),
        });
        const data = await parseJsonResponse(response, "Persistência do ajuste");
        if (!response.ok || data.error) throw new Error(data.error || "Não foi possível salvar o ajuste");
        state.clips[index] = {
            ...clip,
            start: data.adjustment.start,
            end: data.adjustment.end,
            duration: data.adjustment.duration,
            latest_adjustment: data.adjustment,
            adjustment_state: "saved",
            review_status: data.review_status || "needs_review",
        };
        renderReviewCommandCenter();
        renderResultsGrid();
        const persistedSource = data.adjustment?.boundary_adjustment?.source === "transcript" ? "transcript" : "manual";
        if (feedback) feedback.textContent = `Ajuste salvo: ${formatTime(data.adjustment.start)}–${formatTime(data.adjustment.end)}. ${persistedSource === "transcript" ? "Limites alinhados à transcrição." : "Limites manuais preservados."} O MP4 original foi preservado; revise novamente o resultado antes de aprovar.`;
        showToast("Ajuste salvo no histórico editorial; o MP4 original foi preservado.", "success");
    } catch (error) {
        if (feedback) feedback.textContent = error.message;
        showToast(error.message, "error");
    }
}

function transcriptSegmentsForClip(clip) {
    const linkedPath = String(state.manualTranscriptVideo || "").trim();
    const selectedPath = String(selectedVideoPathForRequest() || "").trim();
    const globalTranscriptBelongsToSelection = Boolean(
        state.manualTranscript
        && linkedPath
        && linkedPath !== "pending-source"
        && selectedPath
        && mediaPathsMatch(linkedPath, selectedPath)
    );
    const allSegments = globalTranscriptBelongsToSelection && Array.isArray(state.manualTranscript?.segments)
        ? state.manualTranscript.segments
        : [];
    const fallback = Array.isArray(clip?.transcript_segments) ? clip.transcript_segments : (Array.isArray(clip?.segments) ? clip.segments : []);
    const segments = allSegments.length ? allSegments : fallback;
    const start = Number(clip?.start ?? clip?.start_time ?? 0);
    const end = Number(clip?.end ?? clip?.end_time ?? start);
    if (!segments.length) return { full: [], excerpt: [] };
    const excerptIndexes = [];
    segments.forEach((segment, index) => {
        const segmentStart = Number(segment.start || 0);
        const segmentEnd = Number(segment.end || segmentStart);
        if (segmentEnd >= start && segmentStart <= end) excerptIndexes.push(index);
    });
    if (!excerptIndexes.length) return { full: segments, excerpt: segments.slice(0, 12) };
    const first = Math.max(0, excerptIndexes[0] - 1);
    const last = Math.min(segments.length, excerptIndexes[excerptIndexes.length - 1] + 2);
    return { full: segments, excerpt: segments.slice(first, last) };
}

function openContextReview(index) {
    const clip = state.clips[index];
    if (!clip) return;
    setClipReview(index, "needs_review");
    const panel = document.getElementById("contextReviewPanel");
    const title = document.getElementById("contextReviewTitle");
    const meta = document.getElementById("contextReviewMeta");
    const excerpt = document.getElementById("contextReviewExcerpt");
    const full = document.getElementById("contextReviewFull");
    if (!panel || !title || !meta || !excerpt || !full) return;
    const transcript = transcriptSegmentsForClip(clip);
    title.textContent = "Revisão de contexto do clip";
    const reviewFlags = clip.review_flags || {};
    const contextRecovery = (clip.context_recovery && typeof clip.context_recovery === "object")
        ? clip.context_recovery
        : (reviewFlags.context_recovery && typeof reviewFlags.context_recovery === "object" ? reviewFlags.context_recovery : {});
    const contextRecoveryApplied = [contextRecovery.applied, reviewFlags.context_recovery_applied].some((value) => safeBooleanFlag(value));
    const recoveryTiming = Number.isFinite(Number(contextRecovery.original_start)) && Number.isFinite(Number(contextRecovery.added_start))
        ? ` · início recuperado de ${formatTime(contextRecovery.original_start)} para ${formatTime(contextRecovery.added_start)}`
        : "";
    const recoverySummary = contextRecoveryApplied
        ? ` · abertura ampliada para contexto: ${String(contextRecovery.reason || "antecedente ampliado").trim()}${recoveryTiming}${Number.isFinite(Number(contextRecovery.gap_seconds)) ? ` · pausa ${Number(contextRecovery.gap_seconds).toFixed(1)}s` : ""} · confirme se o antecedente realmente explica o hook`
        : "";
    meta.textContent = `${clip.text || "Trecho sem transcrição"} · ${Number(clip.start || 0).toFixed(1)}s–${Number(clip.end || 0).toFixed(1)}s${recoverySummary}`;
    excerpt.textContent = transcript.excerpt.length ? formatTranscriptForEditor({ segments: transcript.excerpt }) : "O trecho não possui transcrição timestampada disponível.";
    full.textContent = transcript.full.length ? formatTranscriptForEditor({ segments: transcript.full }) : "A transcrição completa ainda não foi arquivada para este vídeo.";
    panel.hidden = false;
    panel.scrollIntoView({ behavior: "smooth", block: "center" });
}

function closeContextReview() {
    const panel = document.getElementById("contextReviewPanel");
    if (panel) panel.hidden = true;
}

async function setClipReview(index, action) {
    const clip = state.clips[index];
    if (!clip || clip.review_busy) return;
    const rawConfidence = Number(clip.confidence);
    clip.review_busy = true;
    const previousStatus = reviewStatusOf(clip);
    const previousUpdatedAt = clip.review_updated_at;
    const previousReason = clip.latest_feedback_reason;
    const previousTags = clip.latest_feedback_tags;
    const reasonSelect = document.querySelector(`[data-feedback-reason="${index}"]`);
    const fallbackReasonByAction = { approved: "editor_approved", rejected: "editor_rejected", needs_review: "context_review" };
    const reasonCode = String(reasonSelect?.value || fallbackReasonByAction[action] || "editor_rejected");
    const qualityTags = reasonCode ? [reasonCode] : [];
    const decisionAt = new Date().toISOString();
    let feedbackData = null;
    clip.review_status = action;
        clip.review_updated_at = decisionAt;
        clip.latest_feedback_reason = reasonCode;
        clip.latest_feedback_tags = qualityTags;
    renderReviewCommandCenter();
    renderResultsGrid();
    try {
        if (clip.clip_id) {
            const reviewMetadata = {
                candidate_origin: String(clip.candidate_origin || ""),
                selection_source: String(clip.selection_source || state.selectionSource || ""),
                confidence: Number.isFinite(rawConfidence) ? Math.max(0, Math.min(1, rawConfidence)) : 0,
            };
            const feedbackAdjustments = { _review_metadata: reviewMetadata };
            const response = await fetch(`/api/clips/${clip.clip_id}/feedback`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    action,
                    adjustments: feedbackAdjustments,
                    reason_code: reasonCode,
                    quality_tags: qualityTags,
                    note: reasonCode ? `Motivo editorial: ${reasonCode}` : "",
                }),
            });
            feedbackData = await parseJsonResponse(response, "Feedback editorial");
            if (!response.ok) throw new Error(feedbackData.error || "feedback rejected");
        }
        const messages = {
            approved: "Clip aprovado",
            rejected: "Clip rejeitado",
            needs_review: "Clip marcado para revisão de contexto",
        };
        state.lastReviewAction = { action, clip_id: clip.clip_id || null, reason_code: reasonCode, at: decisionAt };
        if (clip.clip_id) await refreshVisibleReviewState();
        if (feedbackData?.calibration) renderEditorialLearning(feedbackData.calibration);
        renderReviewCommandCenter();
        renderResultsGrid();
        showToast(messages[action] || "Feedback salvo", action === "approved" ? "success" : "warning");
        loadEditorialLearning();
        loadDailyEditorialGoal();
        loadEditorialData();
    } catch (error) {
        clip.review_status = previousStatus;
        clip.review_updated_at = previousUpdatedAt;
        clip.latest_feedback_reason = previousReason;
        clip.latest_feedback_tags = previousTags;
        renderReviewCommandCenter();
        renderResultsGrid();
        const feedbackError = error?.message || "erro desconhecido";
        addConsoleLog(`[Revisão] Feedback não salvo: ${feedbackError}`, "error");
        showToast(`Não foi possível salvar o feedback: ${feedbackError}`, "error");
    } finally {
        clip.review_busy = false;
        renderReviewCommandCenter();
        renderResultsGrid();
    }
}

// --- Transcript Toggle ---

function toggleTranscript(id) {
    const el = document.getElementById(id);
    if (el) {
        el.classList.toggle("expanded");
    }
}

// --- Results Mode Badge ---

function updateResultsModeBadge(source) {
    const badge = document.getElementById("resultModeBadge");
    if (!badge) return;
    badge.className = "results-mode-badge";
    if (source === "gemini") {
        badge.classList.add("mode-llm");
        badge.textContent = "Gemini Flash";
    } else if (source === "llm") {
        badge.classList.add("mode-llm");
        badge.textContent = "Ollama";
    } else {
        badge.classList.add("mode-nlp");
        badge.textContent = "NLP local";
    }
}

function renderCandidateVolumeNotice(diagnostics = {}) {
    const notice = document.getElementById("candidateVolumeNotice");
    if (!notice) return;
    const expected = safeNonNegativeCount(diagnostics.expected_count);
    const primary = safeNonNegativeCount(diagnostics.primary_count);
    const fallback = safeNonNegativeCount(diagnostics.fallback_count);
    const discarded = safeNonNegativeCount(diagnostics.fallback_discarded_count);
    const discardedOverlap = safeNonNegativeCount(diagnostics.fallback_discarded_overlap);
    const discardedSimilarity = safeNonNegativeCount(diagnostics.fallback_discarded_similarity);
    const previousDiscarded = safeNonNegativeCount(diagnostics.previous_discarded_count);
    const previousApproved = safeNonNegativeCount(diagnostics.previous_discarded_approved);
    const previousRejected = safeNonNegativeCount(diagnostics.previous_discarded_rejected);
    const previousNote = previousDiscarded > 0
        ? ` ${previousDiscarded} intervalo(s) já gerado(s) foram evitados${previousApproved || previousRejected ? ` (${previousApproved} aprovado(s) e ${previousRejected} rejeitado(s) no histórico)` : ''}; novas partes permaneceram elegíveis.`
        : '';
    const finalCount = safeNonNegativeCount(diagnostics.final_count);
    const renderableCount = safeNonNegativeCount(diagnostics.renderable_candidate_count, finalCount);
    const deferredByGate = safeNonNegativeCount(diagnostics.editorial_gate_deferred_count);
    const diagnosticReason = String(diagnostics.reason || "").trim().toLowerCase();
    const reasonLabels = {
        no_candidates: "A fonte não entregou candidatos autossuficientes para revisar.",
        all_intervals_already_processed: "Os intervalos encontrados já foram processados em execuções anteriores.",
        all_candidates_redundant: "Os candidatos encontrados eram redundantes entre si e foram descartados.",
        quality_pool_below_reference: "A seleção preservou apenas momentos que passaram pelos gates de contexto e qualidade.",
        editorial_gate_blocked: "Nenhum candidato foi liberado: todos exigem revisão editorial ou técnica antes do render.",
        render_failed_after_selection: "Havia candidatos selecionados, mas o render não entregou um arquivo válido; revise os erros técnicos do job.",
        partial_render_failure: "Parte dos candidatos passou, mas alguns renders falharam; revise os erros técnicos antes de repetir.",
    };
    const diagnosticReasonLabel = reasonLabels[diagnosticReason] || "A quantidade final depende do material autossuficiente encontrado e dos gates editoriais.";
    if (!expected && !primary && !finalCount && !deferredByGate && !previousDiscarded) {
        notice.hidden = true;
        notice.textContent = "";
        return;
    }
    notice.hidden = false;
    notice.className = "candidate-volume-notice";
    if (diagnosticReason === "render_failed_after_selection" || diagnosticReason === "partial_render_failure") {
        notice.classList.add("warning");
        const rejected = safeNonNegativeCount(diagnostics.render_rejection_count);
        notice.innerHTML = `<span class="material-icons-round">build_circle</span><span>${escapeHtml(diagnosticReasonLabel)} ${rejected ? `${rejected} ocorrência(s) foram registradas no job.` : "Consulte o console para a causa."}</span>`;
        return;
    }
    if (fallback > 0) {
        notice.classList.add("fallback");
        const discardedNote = discarded > 0
            ? ` ${discarded} alternativa(s) foram descartadas por redundância${discardedOverlap > 0 ? ` (${discardedOverlap} por sobreposição` : " ("}${discardedSimilarity > 0 ? `${discardedOverlap > 0 ? ", " : ""}${discardedSimilarity} por repetição textual` : ""}).`
            : " Nenhuma alternativa foi descartada por redundância.";
        notice.innerHTML = `<span class="material-icons-round">alt_route</span><span>Pool ampliado com segurança: ${primary} candidato(s) da fonte principal + ${fallback} alternativa(s) locais.${discardedNote} Os gates de contexto permaneceram ativos.</span>`;
        return;
    }
    if (deferredByGate > 0) {
        notice.classList.add("warning");
        const renderSummary = renderableCount > 0
            ? `${renderableCount} candidato(s) liberado(s) para render`
            : "Nenhum candidato foi liberado para render";
        notice.innerHTML = `<span class="material-icons-round">rule</span><span>${renderSummary}; ${deferredByGate} foram adiados antes do render por contexto incompleto ou revisão técnica obrigatória. O editor pode conferir os motivos no diagnóstico.</span>`;
        return;
    }
    if (expected && finalCount < expected) {
        notice.classList.add("warning");
        notice.innerHTML = `<span class="material-icons-round">info</span><span>${finalCount} candidato(s) chegaram à revisão; a referência estrutural era ${expected}. ${escapeHtml(diagnosticReasonLabel)}${previousNote}</span>`;
        return;
    }
    notice.innerHTML = `<span class="material-icons-round">check_circle</span><span>Pool editorial adequado: ${finalCount} candidato(s) distintos chegaram à revisão. ${escapeHtml(diagnosticReasonLabel)}${previousNote}</span>`;
}

// --- Open Folder Button ---

function updateOpenFolderButton(folderPath) {
    const btn = document.getElementById("btnOpenFolder");
    if (!btn) return;
    if (folderPath) {
        btn.style.display = "inline-flex";
        btn.onclick = () => openOutputFolder(folderPath);
    } else {
        btn.style.display = "none";
    }
}

async function openOutputFolder(folderPath) {
    if (!folderPath) {
        showToast("Pasta não informada.", "warning");
        return;
    }
    try {
        const res = await fetch("/api/open_folder", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: folderPath }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.success) {
            throw new Error(data.error || `Servidor recusou a abertura (${res.status})`);
        }
        showToast("Pasta aberta!", "success");
    } catch (e) {
        addConsoleLog(`[Pasta] ${e.message || "Falha ao abrir pasta"}`, "warning");
        showToast(e.message || "Erro ao abrir pasta", "error");
    }
}

function displaySeoResult(seo) {
    // Update the last clip that was generating SEO
    addConsoleLog(`[SEO] Titulos: ${(seo.titles || []).join(' | ')}`, "success");
    addConsoleLog(`[SEO] Tags: ${(seo.tags || []).slice(0, 5).join(', ')}...`, "info");
}

function formatTime(seconds) {
    const numeric = Number(seconds);
    if (!Number.isFinite(numeric)) return "—";
    const safeSeconds = Math.max(0, numeric);
    const m = Math.floor(safeSeconds / 60);
    const s = Math.floor(safeSeconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

function downloadClip(index) {
    const clip = state.clips[index];
    if (clip) {
        const path = clip.subtitled_path || clip.path;
        const a = document.createElement("a");
        a.href = mediaUrlForPath(path);
        a.download = String(path).split(/[\\\\/]/).pop();
        a.click();
        showToast("Download iniciado!", "success");
    }
}

async function generateClipSeo(index) {
    const clip = state.clips[index];
    if (!clip || !clip.text) {
        showToast("Clip sem transcricao para gerar SEO", "warning");
        return;
    }
    addConsoleLog(`[SEO] Gerando conteudo para Clip...`, "info");
    await fetch("/api/process/seo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            transcript: clip.text,
            clip_id: clip.clip_id,
        }),
    });
}

async function generateClipThumb(index) {
    const clip = state.clips[index];
    if (!clip) return;

    const text = prompt("Texto para a thumbnail:", clip.text ? clip.text.substring(0, 40) : "");
    if (text === null) return;

    addConsoleLog(`[Thumbnail] Gerando capa...`, "info");
    await fetch("/api/process/thumbnail", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            video_path: clip.path,
            text: text,
            time: 3,
            style: "dark_gold",
            clip_id: clip.clip_id,
        }),
    });
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast("Copiado!", "success");
    });
}

// ─── Source Intake ───

async function parseJsonResponse(response, context = "servidor") {
    const raw = await response.text();
    if (!raw) {
        throw new Error(`${context}: resposta vazia (HTTP ${response.status}). Veja o console do launcher.`);
    }
    try {
        return JSON.parse(raw);
    } catch (error) {
        const preview = raw.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim().slice(0, 180);
        throw new Error(`${context}: resposta inválida do servidor (HTTP ${response.status})${preview ? ` — ${preview}` : ""}`);
    }
}

function formatTranscriptForEditor(transcription) {
    const segments = Array.isArray(transcription?.segments) ? transcription.segments : [];
    return segments.map(segment => {
        const start = Number(segment.start || 0);
        const hours = Math.floor(start / 3600).toString().padStart(2, "0");
        const minutes = Math.floor((start % 3600) / 60).toString().padStart(2, "0");
        const seconds = (start % 60).toFixed(3).padStart(6, "0");
        return `${hours}:${minutes}:${seconds} ${String(segment.text || "").trim()}`.trim();
    }).join("\n");
}

function hydrateTranscriptEditor(transcription, archive = null) {
    state.manualTranscript = transcription;
    state.transcriptArchive = archive || transcription?.archive_metadata || null;
    const input = document.getElementById("manualTranscriptInput");
    if (input) input.value = formatTranscriptForEditor(transcription);
    const count = transcription?.segment_count || transcription?.segments?.length || 0;
    const structuralQuality = transcription?.quality?.quality || transcription?.archive_metadata?.quality?.quality || "não validada";
    const structuralQualityLabels = {
        structurally_ok: "estrutura timestampada válida",
        review_recommended: "estrutura válida · revisar avisos",
        needs_attention: "estrutura requer atenção",
    };
    const structuralQualityLabel = structuralQualityLabels[structuralQuality] || "estrutura timestampada não validada";
    const semanticAccuracyVerified = safeBooleanFlag(
        transcription?.quality?.semantic_accuracy_verified
            ?? transcription?.archive_metadata?.quality?.semantic_accuracy_verified,
    );
    const semanticLabel = semanticAccuracyVerified ? "semântica validada" : "semântica não validada";
    const qualityScore = transcription?.quality?.score || transcription?.archive_metadata?.quality?.score;
    const suffix = Number.isFinite(Number(qualityScore))
        ? ` Estrutura timestampada: ${qualityScore}/100 (${structuralQualityLabel}); ${semanticLabel}.`
        : ` Estrutura timestampada: ${structuralQualityLabel}; ${semanticLabel}.`;
    const linkedPath = String(state.manualTranscriptVideo || "").trim();
    const linkedName = linkedPath && linkedPath !== "pending-source" ? linkedPath.split(/[\\/]/).pop() : "vídeo ainda não confirmado";
    const selectedPath = String(selectedVideoPathForRequest() || "").trim();
    const transcriptLinkedToSelection = linkedPath && selectedPath && mediaPathsMatch(linkedPath, selectedPath);
    const linkage = linkedPath === "pending-source"
        ? "Aguardando vínculo com um vídeo selecionado."
        : transcriptLinkedToSelection
            ? `Vinculada a ${linkedName}.`
            : linkedPath
                ? `Fonte registrada: ${linkedName}; confirme se corresponde ao vídeo atual.`
                : "Fonte da transcrição não identificada; revise antes do corte.";
    const archivePath = String(archive?.text || archive?.json || archive?.archive || "").trim();
    const archiveLabel = archivePath ? ` Arquivo persistente: ${archivePath.split(/[\\/]/).pop()}.` : " Arquivo persistente ainda não identificado.";
    const status = document.getElementById("transcriptStatus");
    if (status) {
        status.textContent = `Transcrição pronta: ${count} segmentos. ${linkage}${archiveLabel}${suffix}`;
        status.className = `source-status ${structuralQuality === "structurally_ok" && transcriptLinkedToSelection ? "success" : "warning"}`;
    }
}

function transcriptArchiveCoverage(item = {}) {
    const quality = item.quality || {};
    const duration = Number(quality.duration_seconds || 0);
    const lastTimestamp = Number(quality.last_timestamp || 0);
    if (!Number.isFinite(duration) || duration <= 0) return "duração da fonte não informada · revisar";
    if (!Number.isFinite(lastTimestamp) || lastTimestamp <= 0) return "sem cobertura temporal utilizável · revisar";
    if (lastTimestamp < duration * 0.95) return "último timestamp antes do fim da fonte · revisar";
    return "timestamps cobrem quase toda a duração informada · confirmar no vídeo";
}

function transcriptArchiveCompatibility(item = {}) {
    const selectedPath = String(selectedVideoPathForRequest() || "").replaceAll("\\", "/").trim();
    const archivedPath = String(item.source_video || "").replaceAll("\\", "/").trim();
    if (!selectedPath) return "selecione um vídeo para comparar";
    if (!archivedPath) return "fonte arquivada não identificada · revisar";
    if (mediaPathsMatch(selectedPath, archivedPath)) return "fonte atual registrada";
    const selectedName = selectedPath.split("/").pop().toLowerCase();
    const archivedName = archivedPath.split("/").pop().toLowerCase();
    return selectedName && selectedName === archivedName
        ? "mesmo nome-base · confirmar arquivo"
        : "fonte diferente da seleção · não aplicar automaticamente";
}

function renderTranscriptArchiveList(items = [], persistentDir = "") {
    const list = document.getElementById("transcriptArchiveList");
    const pathLabel = document.getElementById("transcriptArchivePath");
    if (pathLabel) pathLabel.textContent = persistentDir ? `Pasta persistente: ${persistentDir}` : "Pasta persistente ainda não criada.";
    if (!list) return;
    list.hidden = false;
    if (!items.length) {
        list.innerHTML = '<div class="transcript-archive-empty">Nenhuma transcrição arquivada ainda. Gere, importe ou confirme uma transcrição para criar o primeiro registro.</div>';
        return;
    }
    list.innerHTML = items.map(item => {
        const quality = item.quality || {};
        const sourceVideo = String(item.source_video || "").split(/[\\\\/]/).pop() || "fonte não identificada";
        const qualityLabels = {
            structurally_ok: "estrutura timestampada válida",
            review_recommended: "estrutura válida · revisar avisos",
            needs_attention: "estrutura requer atenção",
        };
        const qualityLabel = qualityLabels[String(quality.quality || "")] || "qualidade estrutural não validada";
        const scoreValue = Number(quality.score);
        const scoreLabel = Number.isFinite(scoreValue) ? `${scoreValue.toFixed(0)}/100` : "sem score";
        const semanticVerified = safeBooleanFlag(quality.semantic_accuracy_verified);
        const semanticLabel = semanticVerified ? "semântica validada" : "semântica não validada";
        const source = String(item.source || "automatic").replace(/_/g, " ");
        const compatibility = transcriptArchiveCompatibility(item);
        const coverageLabel = transcriptArchiveCoverage(item);
        const archiveClass = quality.quality === "structurally_ok" && semanticVerified ? "" : " warning";
        return `<article class="transcript-archive-item${archiveClass}"><div><strong>${escapeHtml(sourceVideo)}</strong><small>${escapeHtml(source)} · ${escapeHtml(scoreLabel)} · ${escapeHtml(qualityLabel)} · ${escapeHtml(semanticLabel)} · ${safeNonNegativeCount(quality.valid_segment_count)} segmentos válidos</small><small class="transcript-archive-coverage">${escapeHtml(coverageLabel)}</small><small class="transcript-archive-compatibility">${escapeHtml(compatibility)}</small></div><div class="transcript-archive-links"><a class="btn btn-sm btn-outline" href="${escapeHtml(item.download_text || "#")}" target="_blank" rel="noopener">TXT</a><a class="btn btn-sm btn-outline" href="${escapeHtml(item.download_json || "#")}" target="_blank" rel="noopener">JSON</a><button type="button" class="btn btn-sm btn-outline" data-open-transcript-folder="${escapeHtml(item.relative_dir || "")}">Pasta</button></div></article>`;
    }).join("");
}

async function loadTranscriptArchive() {
    const button = document.getElementById("btnLoadTranscriptArchive");
    if (button) button.disabled = true;
    try {
        const response = await fetch("/api/editorial/transcripts?limit=30");
        const data = await parseJsonResponse(response, "Arquivo de transcrições");
        if (!response.ok) throw new Error(data.error || "Não foi possível consultar o arquivo");
        renderTranscriptArchiveList(data.transcripts || [], data.persistent_dir || "");
    } catch (error) {
        const list = document.getElementById("transcriptArchiveList");
        if (list) {
            list.hidden = false;
            list.innerHTML = `<div class="transcript-archive-empty error">${escapeHtml(error.message || "Não foi possível consultar o arquivo")}</div>`;
        }
    } finally {
        if (button) button.disabled = false;
    }
}

document.getElementById("btnLoadTranscriptArchive")?.addEventListener("click", loadTranscriptArchive);

document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-open-transcript-folder]");
    if (!button) return;
    const relativeDir = String(button.dataset.openTranscriptFolder || "").trim();
    if (!relativeDir) {
        showToast("Esta transcrição não informa uma pasta persistente válida.", "warning");
        return;
    }
    button.disabled = true;
    try {
        const response = await fetch("/api/editorial/transcripts/open", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ relative_dir: relativeDir }),
        });
        const payload = await parseJsonResponse(response, "Pasta da transcrição");
        if (!response.ok || !payload.success) throw new Error(payload.error || "Não foi possível abrir a pasta persistente");
        showToast("Pasta persistente aberta. Nenhum arquivo foi aplicado ao vídeo atual.", "success");
    } catch (error) {
        showToast(error.message || "Não foi possível abrir a pasta persistente", "error");
    } finally {
        button.disabled = false;
    }
});

function showSourceOnlyStatus(message, type = "") {
    const sourceStatus = document.getElementById("sourceStatus");
    if (!sourceStatus) return;
    sourceStatus.textContent = message;
    sourceStatus.className = `source-status ${type}`.trim();
}

function showSourceStatus(message, type = "") {
    const transcriptStatus = document.getElementById("transcriptStatus");
    const sourceStatus = document.getElementById("sourceStatus");
    [transcriptStatus, sourceStatus].forEach(el => {
        if (!el) return;
        el.textContent = message;
        el.className = `source-status ${type}`.trim();
    });
}

function safeNonNegativeCount(...values) {
    for (const value of values) {
        const parsed = Number(value);
        if (Number.isFinite(parsed) && parsed >= 0) return Math.floor(parsed);
    }
    return 0;
}

function safeBooleanFlag(value, fallback = false) {
    if (typeof value === "boolean") return value;
    if (typeof value === "number" && Number.isFinite(value)) return value !== 0;
    if (value == null) return Boolean(fallback);
    const normalized = String(value).trim().toLowerCase();
    if (!normalized) return Boolean(fallback);
    if (["0", "false", "no", "não", "nao", "off", "disabled"].includes(normalized)) return false;
    if (["1", "true", "yes", "sim", "on", "enabled"].includes(normalized)) return true;
    return Boolean(fallback);
}

function transcriptCoverageLabel(transcription) {
    const coverage = transcription?.coverage || transcription?.transcription_quality || {};
    const status = String(coverage.status || "unknown");
    const segments = safeNonNegativeCount(coverage.segment_count, transcription?.segment_count, Array.isArray(transcription?.segments) ? transcription.segments.length : 0);
    const endRatio = Number(coverage.end_ratio);
    const firstRatio = Number(coverage.first_ratio);
    const first = Number(coverage.first_timestamp);
    const last = Number(coverage.last_timestamp);
    const duration = Number(coverage.video_duration_seconds);
    if (status === "mismatch_suspected") return `timestamps incompatíveis com o vídeo selecionado; revise antes de cortar`;
    if (status === "empty") return "nenhum segmento timestampado utilizável; importe uma transcrição válida antes de cortar";
    if (status === "unknown") return "cobertura temporal não validada; confirme a sincronização no vídeo antes de cortar";
    if (status === "partial" && Number.isFinite(last) && Number.isFinite(duration) && duration > 0) {
        const lateStart = Number.isFinite(first) && first > 0 && Number.isFinite(firstRatio) && firstRatio > 0.2
            ? `; começa em ${formatTime(first)}`
            : "";
        return `cobertura parcial até ${formatTime(last)} de ${formatTime(duration)}${lateStart}; cortes ficarão limitados a esse trecho`;
    }
    if (status === "covered" && Number.isFinite(endRatio) && endRatio > 0) {
        const identityNote = coverage.semantic_identity_verified === false
            ? "; identidade da transcrição ainda não validada"
            : "";
        return `${segments} segmentos com cobertura temporal até ${Math.round(endRatio * 100)}% do vídeo${identityNote}`;
    }
    return `${segments} segmentos timestampados; confira a sincronização no vídeo`;
}

function activateSourceTab(name) {
    document.querySelectorAll(".source-tab").forEach(tab => {
        tab.classList.toggle("active", tab.dataset.sourceTab === name);
    });
    document.querySelectorAll(".source-panel").forEach(panel => {
        const active = panel.id === `sourcePanel${name.charAt(0).toUpperCase()}${name.slice(1)}`;
        panel.classList.toggle("active", active);
        panel.style.display = active ? "block" : "none";
    });
}

document.querySelectorAll(".source-tab").forEach(tab => {
    tab.addEventListener("click", () => activateSourceTab(tab.dataset.sourceTab));
});

document.getElementById("btnImportTranscript")?.addEventListener("click", () => {
    document.getElementById("transcriptFileInput")?.click();
});

document.getElementById("transcriptFileInput")?.addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
        const text = await file.text();
        document.getElementById("manualTranscriptInput").value = text;
        showSourceStatus(`Arquivo ${file.name} carregado. Clique em Usar transcrição.`, "success");
    } catch (error) {
        showSourceStatus(`Falha ao ler o arquivo: ${error.message}`, "error");
    }
});

document.getElementById("btnApplyTranscript")?.addEventListener("click", async () => {
    const text = document.getElementById("manualTranscriptInput")?.value.trim();
    const selectedVideoPath = selectedVideoPathForRequest();
    const previewDuration = Number(document.getElementById("videoPreview")?.duration);
    const selectedVideoDuration = Number.isFinite(previewDuration) && previewDuration > 0 ? previewDuration : null;
    if (!text) {
        showSourceStatus("Cole ou importe uma transcrição primeiro.", "error");
        return;
    }
    try {
        const res = await fetch("/api/transcript/parse", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                text,
                language: document.getElementById("settingLanguage")?.value || "pt",
                duration: selectedVideoDuration,
                video_path: selectedVideoPath || null,
            }),
        });
        const data = await parseJsonResponse(res, "Transcrição");
        if (!res.ok || !data.success) throw new Error(data.error || "Transcrição inválida");
        state.manualTranscript = data.transcription;
        state.manualTranscriptVideo = selectedVideoPath || "pending-source";
        const coverageStatus = String(data.transcription.coverage?.status || "");
        const statusType = coverageStatus === "mismatch_suspected" ? "error" : ["partial", "empty", "unknown"].includes(coverageStatus) ? "warning" : "success";
        showSourceStatus(`Transcrição ${data.transcription.format} pronta: ${transcriptCoverageLabel(data.transcription)}. Ela será usada no próximo corte sem Whisper.`, statusType);
        showToast("Transcrição manual aplicada.", "success");
    } catch (error) {
        state.manualTranscript = null;
        showSourceStatus(error.message, "error");
        showToast("Não foi possível interpretar a transcrição.", "error");
    }
});

document.getElementById("btnGenerateTranscript")?.addEventListener("click", async () => {
    if (!requireVideo()) return;
    state.transcriptionJobVideoPath = selectedVideoPathForRequest();
    prepareNewOperationHud();
    showProgressBar();
    showSourceStatus("Gerando transcrição do vídeo; isso pode levar alguns minutos...", "");
    addConsoleLog("[Transcrição] Geração automática solicitada.", "info");
    try {
        const res = await fetch("/api/process/transcribe", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                video_path: state.selectedVideo,
                transcript_language: document.getElementById("settingLanguage")?.value || "pt",
                transcription_source: document.getElementById("settingTranscriptionSource")?.value || "auto",
            }),
        });
        const data = await parseJsonResponse(res, "Transcrição automática");
        if (!res.ok || !data.success) throw new Error(data.error || "Não foi possível iniciar a transcrição");
        registerStartedOperation(data, "Transcrição em andamento.");
        showProgressBar();
        showSourceStatus("Transcrição iniciada; acompanhe o console abaixo.", "");
    } catch (error) {
        hideProgressBar();
        state.transcriptionJobVideoPath = "";
        showSourceStatus(error.message, "error");
        showToast(error.message, "error");
    }
});

// ─── Artwork Headline Studio ───

const artworkFormatLabels = {
    auto: "Escolher por mim",
    vertical_916: "9:16 — headline central",
    square_alfinetei: "1:1 — Alfinetei",
    fake_tweet: "Fake tweet — publicação simulada",
};

function selectedArtworkFormat() {
    return document.querySelector('input[name="artworkFormat"]:checked')?.value || "auto";
}

function setHeadlineStudioStatus(message, type = "") {
    const status = document.getElementById("headlineStudioStatus");
    if (!status) return;
    status.textContent = message;
    status.className = `headline-studio-status ${type}`.trim();
}

function artworkCopyButton(value, label = "Copiar") {
    return `<button class="btn btn-sm btn-outline artwork-copy-button" type="button" data-artwork-copy="${encodeURIComponent(value)}"><span class="material-icons-round">content_copy</span>${label}</button>`;
}

function artworkFeedbackButton(format, value, clipIndex = null) {
    const clipAttribute = Number.isInteger(clipIndex) ? ` data-artwork-clip-index="${clipIndex}"` : "";
    return `<button class="btn btn-sm artwork-feedback-button" type="button" data-artwork-format="${escapeHtml(format)}" data-artwork-feedback="${encodeURIComponent(value)}"${clipAttribute}><span class="material-icons-round">bookmark_add</span>Escolher</button>`;
}

function renderArtworkHeadline(suggestion, format, clipIndex = null) {
    const eyebrow = escapeHtml(suggestion.eyebrow || "");
    const lines = Array.isArray(suggestion.headline_lines) && suggestion.headline_lines.length
        ? suggestion.headline_lines : [suggestion.headline || ""];
    const headline = escapeHtml(suggestion.headline || "");
    const emphasis = escapeHtml(suggestion.emphasis || "");
    const artwork = lines.map(line => `<span>${escapeHtml(line)}</span>`).join("");
    return `<article class="artwork-suggestion-card ${format}">
        <div class="artwork-preview ${suggestion.accent === "red_on_white" ? "has-red-accent" : ""}">
            ${eyebrow ? `<div class="artwork-eyebrow">${eyebrow}</div>` : ""}
            <div class="artwork-headline">${artwork}</div>
            ${emphasis ? `<div class="artwork-emphasis">Destaque sugerido: ${emphasis}</div>` : ""}
        </div>
        <div class="artwork-suggestion-footer"><span>${Number(suggestion.character_count || headline.length)} caracteres · ${Number(suggestion.word_count || String(suggestion.headline || "").trim().split(/\s+/).filter(Boolean).length)} palavras</span><div>${artworkCopyButton(suggestion.headline || "", "Copiar headline")}${artworkFeedbackButton(format, suggestion.headline || "", clipIndex)}</div></div>
        ${suggestion.layout_hint ? `<p class="artwork-layout-hint"><span class="material-icons-round">grid_view</span>${escapeHtml(suggestion.layout_hint)}</p>` : ""}
    </article>`;
}

function renderHeadlineStudioResults(studio, options = {}) {
    const container = options.container || document.getElementById(options.containerId || "headlineStudioResults");
    const clipIndex = Number.isInteger(options.clipIndex) ? options.clipIndex : null;
    if (!container) return;
    state.headlineStudio = studio;
    const formats = studio.formats || {};
    const flags = studio.review_flags || {};
    const recommended = studio.recommended_format || "vertical_916";
    const learning = studio.learning_applied || {};
    const learningLabel = learning.applied
        ? `aprendizado aplicado (${Number(learning.selected_count || 0)} escolha(s))`
        : "aprendizado em coleta";
    const reviewChips = [
        flags.transcript_ends_incomplete ? '<span class="artwork-review-chip warning"><span class="material-icons-round">pending</span>final da transcrição incompleto</span>' : "",
        flags.needs_fact_review ? '<span class="artwork-review-chip"><span class="material-icons-round">fact_check</span>revisar afirmação factual</span>' : "",
        flags.needs_legal_review ? '<span class="artwork-review-chip legal"><span class="material-icons-round">gavel</span>revisar formulação jurídica</span>' : "",
    ].filter(Boolean).join("");
    const selectedFormat = studio.generated_format || recommended;
    const availableFormats = [selectedFormat].filter(format => ["vertical_916", "square_alfinetei"].includes(format));
    const formatCards = availableFormats.map(format => {
        const config = formats[format] || {};
        const suggestions = Array.isArray(config.suggestions) ? config.suggestions : [];
        return `<section class="artwork-format-result ${format === recommended ? "recommended" : ""}">
            <div class="artwork-format-result-head"><div><span class="artwork-format-kicker">${format === recommended ? "FORMATO RECOMENDADO" : "ALTERNATIVA"}</span><h4>${escapeHtml(config.label || artworkFormatLabels[format])}</h4></div><span class="artwork-limit">${escapeHtml(config.description || "")}</span></div>
            <div class="artwork-suggestion-grid">${suggestions.map(item => renderArtworkHeadline(item, format, clipIndex)).join("") || '<p class="artwork-empty">Sem alternativa disponível.</p>'}</div>
        </section>`;
    }).join("");
    const tweets = Array.isArray(formats.fake_tweet?.suggestions) ? formats.fake_tweet.suggestions : [];
    const tweetCard = selectedFormat === "fake_tweet" && formats.fake_tweet ? `<section class="artwork-format-result fake-tweet ${recommended === "fake_tweet" ? "recommended" : ""}">
        <div class="artwork-format-result-head"><div><span class="artwork-format-kicker">${recommended === "fake_tweet" ? "FORMATO RECOMENDADO" : "ALTERNATIVA"}</span><h4>Fake tweet — rascunho de publicação</h4></div><span class="artwork-limit">Revisar antes de atribuir ao perfil</span></div>
        <div class="fake-tweet-options">${tweets.map(item => `<article class="fake-tweet-card"><p>${escapeHtml(item.post_text || "")}</p><footer><span>${Number(item.character_count || 0)} caracteres</span><div>${artworkCopyButton(item.post_text || "", "Copiar texto")}${artworkFeedbackButton("fake_tweet", item.post_text || "", clipIndex)}</div></footer></article>`).join("") || '<p class="artwork-empty">Sem alternativa disponível.</p>'}        </div>
    </section>` : "";
    container.innerHTML = `<div class="headline-studio-result-summary">
<div><span class="artwork-format-kicker">LEITURA EDITORIAL</span><h4>${escapeHtml(artworkFormatLabels[recommended] || recommended)}</h4><p>${escapeHtml(studio.recommendation_reason || "")}</p></div><div class="artwork-analysis-metrics"><span>Tema: <strong>${escapeHtml(studio.topic || "geral")}</strong></span><span>Contexto: <strong>${Math.round(Number(studio.analysis?.context_completeness || 0))}/100</strong></span><span>Fonte: <strong>${studio.generation_source === "ai_refined" ? "IA + regras" : "regras editoriais"}</strong></span><span>Preferência: <strong>${escapeHtml(learningLabel)}</strong></span></div></div><div class="artwork-review-chips">${reviewChips || '<span class="artwork-review-chip safe"><span class="material-icons-round">verified</span>sem alerta lexical automático</span>'}</div><div class="artwork-format-results">${formatCards}${tweetCard}</div>`;
    container.style.display = "block";
    container.querySelectorAll(".artwork-copy-button").forEach(button => {
        button.addEventListener("click", () => copyToClipboard(decodeURIComponent(button.dataset.artworkCopy || "")));
    });
    container.querySelectorAll(".artwork-feedback-button").forEach(button => {
        button.addEventListener("click", () => saveArtworkFeedback(button));
    });
}

function renderHeadlineLearning(learning = {}) {
    const target = document.getElementById("headlineLearningStatus");
    if (!target) return;
    const selected = Number(learning.selected || 0);
    const formats = learning.by_format || {};
    const detail = Object.entries(formats).map(([format, count]) => `${artworkFormatLabels[format] || format}: ${count}`).join(" · ");
    target.textContent = selected
        ? `${selected} escolha(s) de texto de arte salvas neste computador.${detail ? ` ${detail}.` : ""}`
        : "Suas escolhas de headline ficarão salvas neste computador e calibrarão as próximas sugestões.";
}

async function loadHeadlineLearning() {
    try {
        const response = await fetch("/api/headline-studio/learning");
        const data = await parseJsonResponse(response, "Aprendizado editorial");
        if (response.ok && data.success) renderHeadlineLearning(data.learning);
    } catch (_) {
        const target = document.getElementById("headlineLearningStatus");
        if (target) target.textContent = "O aprendizado editorial ficará disponível após a primeira escolha salva.";
    }
}

async function saveArtworkFeedback(button) {
    const artworkText = decodeURIComponent(button.dataset.artworkFeedback || "");
    const formatId = button.dataset.artworkFormat || "";
    const clipIndex = button.dataset.artworkClipIndex === undefined ? null : Number(button.dataset.artworkClipIndex);
    if (!artworkText || !formatId) return;
    button.disabled = true;
    try {
        const clip = Number.isInteger(clipIndex) ? state.clips?.[clipIndex] : null;
        const studio = clip?.headline_studio || state.headlineStudio || {};
        const response = await fetch("/api/headline-studio/feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                clip_id: clip?.clip_id || clip?.id || null,
                editorial_key: clip?.editorial_key || studio.editorial_key || "",
                format_id: formatId,
                artwork_text: artworkText,
                action: "selected",
                topic: studio.topic || "",
                transcript_excerpt: studio.transcript?.excerpt || clip?.text || "",
                mini_context: studio.mini_context || clip?.title || "",
            }),
        });
        const data = await parseJsonResponse(response, "Aprendizado editorial");
        if (!response.ok || !data.success) throw new Error(data.error || "Não foi possível salvar a escolha");
        button.classList.add("saved");
        button.innerHTML = '<span class="material-icons-round">bookmark_added</span>Escolhido';
        renderHeadlineLearning(data.learning);
        showToast("Escolha salva no aprendizado editorial.", "success");
    } catch (error) {
        button.disabled = false;
        showToast(error.message, "error");
    }
}

loadHeadlineLearning();

function toggleClipHeadlineStudio(index) {
    const panel = document.getElementById(`clip-headline-studio-${index}`);
    if (!panel) return;
    panel.hidden = !panel.hidden;
    if (!panel.hidden) {
        panel.querySelector("textarea")?.focus();
    }
}

async function generateClipHeadline(index) {
    const clip = state.clips?.[index];
    const panel = document.getElementById(`clip-headline-studio-${index}`);
    const results = document.getElementById(`clip-headline-results-${index}`);
    const button = panel?.querySelector("[data-generate-clip-headline]");
    const transcript = panel?.querySelector("[data-clip-headline-transcript]")?.value.trim() || "";
    const miniContext = panel?.querySelector("[data-clip-headline-context]")?.value.trim() || "";
    const preferredFormat = panel?.querySelector("[data-clip-headline-format]")?.value || "auto";
    if (!clip || !panel || !results) return;
    if (!transcript) {
        results.innerHTML = '<div class="clip-headline-feedback error">Este corte não tem transcrição disponível. Cole a fala completa do intervalo antes de gerar.</div>';
        return;
    }
    if (button) {
        button.disabled = true;
        button.classList.add("loading");
    }
    results.innerHTML = `<div class="clip-headline-feedback">Lendo a tese do corte e criando alternativas para ${preferredFormat === "auto" ? "o formato recomendado" : "o formato selecionado"}...</div>`;
    try {
        const response = await fetch("/api/headline-studio/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                clip_id: clip.clip_id || clip.id || null,
                transcript,
                mini_context: miniContext,
                preferred_format: preferredFormat,
                use_ai: document.getElementById("artworkUseAi")?.checked !== false,
            }),
        });
        const data = await parseJsonResponse(response, "Headline do corte");
        if (!response.ok || !data.success) throw new Error(data.error || "Não foi possível gerar as headlines");
        state.clips[index] = { ...clip, headline_studio: data.studio };
        renderHeadlineStudioResults(data.studio, { container: results, clipIndex: index });
        if (button) button.innerHTML = '<span class="material-icons-round">refresh</span> Regenerar com novo contexto';
        showToast("Sugestões de headline geradas para este corte.", "success");
    } catch (error) {
        results.innerHTML = `<div class="clip-headline-feedback error">${escapeHtml(error.message)}</div>`;
        showToast("Não foi possível gerar a headline do corte.", "error");
    } finally {
        if (button) {
            button.disabled = false;
            button.classList.remove("loading");
        }
    }
}

function renderPerformanceSummary(summary = {}) {
    const target = document.getElementById("performanceMetricsSummary");
    if (!target) return;
    const formatNumber = (value) => new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(Number(value || 0));
    const engagement = summary.avg_engagement_rate == null ? "—" : `${(Number(summary.avg_engagement_rate) * 100).toFixed(2).replace(".", ",")}%`;
    const velocity = summary.avg_view_velocity_per_hour == null ? "—" : `${formatNumber(summary.avg_view_velocity_per_hour)}/h`;
    target.innerHTML = `<div class="performance-metric"><span>Conteúdos</span><strong>${formatNumber(summary.contents)}</strong></div><div class="performance-metric"><span>Snapshots</span><strong>${formatNumber(summary.snapshots)}</strong></div><div class="performance-metric"><span>Views observadas</span><strong>${formatNumber(summary.views)}</strong></div><div class="performance-metric"><span>Engajamento informado</span><strong>${escapeHtml(engagement)}</strong></div><div class="performance-metric"><span>Velocidade média</span><strong>${escapeHtml(velocity)}</strong></div>`;
}

async function loadPerformanceMetrics() {
    try {
        const params = new URLSearchParams();
        const filters = {
            platform: document.getElementById("performanceMetricPlatform")?.value,
            format_id: document.getElementById("performanceMetricFormat")?.value,
            observation_window: document.getElementById("performanceMetricWindow")?.value,
            region: document.getElementById("performanceMetricRegion")?.value,
        };
        Object.entries(filters).forEach(([key, value]) => { if (value) params.set(key, value); });
        const response = await fetch(`/api/performance/summary${params.toString() ? `?${params}` : ""}`);
        const data = await parseJsonResponse(response, "Métricas observadas");
        if (!response.ok || !data.success) throw new Error(data.error || "não foi possível carregar o histórico");
        renderPerformanceSummary(data.summary || {});
        const status = document.getElementById("performanceMetricsStatus");
        const activeFilters = Object.keys(data.filters || {}).length;
        if (status) status.textContent = data.summary?.snapshots
            ? `${activeFilters ? "Coorte filtrada" : "Histórico local"} atualizado.`
            : `${activeFilters ? "Nenhum snapshot nesta coorte" : "Nenhum snapshot observado nesta instalação."}`;
    } catch (error) {
        const status = document.getElementById("performanceMetricsStatus");
        if (status) status.textContent = `Métricas indisponíveis: ${error.message}`;
    }
}

async function savePerformanceMetrics() {
    const input = document.getElementById("performanceMetricsInput");
    const status = document.getElementById("performanceMetricsStatus");
    if (!input?.value.trim()) {
        if (status) status.textContent = "Cole um snapshot JSON antes de salvar.";
        return;
    }
    try {
        const payload = JSON.parse(input.value);
        const response = await fetch("/api/performance/snapshots", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await parseJsonResponse(response, "Salvar métricas");
        if (!response.ok || !data.success) throw new Error(data.error || "não foi possível salvar");
        if (status) status.textContent = `${data.saved.length} snapshot(s) salvo(s) localmente.`;
        input.value = "";
        await loadPerformanceMetrics();
    } catch (error) {
        if (status) status.textContent = `Falha nas métricas: ${error.message}`;
    }
}

const performanceToggle = document.getElementById("btnTogglePerformanceMetrics");
const performanceBody = document.getElementById("performanceMetricsBody");
performanceToggle?.addEventListener("click", async () => {
    const willOpen = Boolean(performanceBody?.hidden);
    if (performanceBody) performanceBody.hidden = !willOpen;
    performanceToggle.setAttribute("aria-expanded", String(willOpen));
    performanceToggle.innerHTML = `<span class="material-icons-round">${willOpen ? "expand_less" : "expand_more"}</span> ${willOpen ? "Fechar histórico" : "Abrir histórico"}`;
    if (willOpen) await loadPerformanceMetrics();
});
document.getElementById("btnSavePerformanceMetrics")?.addEventListener("click", savePerformanceMetrics);
document.getElementById("btnRefreshPerformanceMetrics")?.addEventListener("click", loadPerformanceMetrics);
["performanceMetricPlatform", "performanceMetricFormat", "performanceMetricWindow", "performanceMetricRegion"].forEach((id) => {
    document.getElementById(id)?.addEventListener("change", loadPerformanceMetrics);
});
document.getElementById("btnImportArtworkTranscript")?.addEventListener("click", () => {
    document.getElementById("artworkTranscriptFileInput")?.click();
});

document.getElementById("artworkTranscriptFileInput")?.addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
        const text = await file.text();
        const input = document.getElementById("artworkTranscriptInput");
        if (input) input.value = text;
        setHeadlineStudioStatus(`${file.name} carregado. Revise ou gere os textos de arte.`, "success");
    } catch (error) {
        setHeadlineStudioStatus(`Falha ao ler o arquivo: ${error.message}`, "error");
    }
});

document.getElementById("btnUseLoadedTranscript")?.addEventListener("click", () => {
    if (!state.manualTranscript) {
        setHeadlineStudioStatus("Nenhuma transcrição carregada na fonte. Importe um TXT/SRT/VTT ou cole o texto acima.", "warning");
        return;
    }
    const input = document.getElementById("artworkTranscriptInput");
    if (input) input.value = formatTranscriptForEditor(state.manualTranscript) || state.manualTranscript.full_text || "";
    setHeadlineStudioStatus("A transcrição já carregada foi copiada para o estúdio de texto de arte.", "success");
});

document.getElementById("btnGenerateArtworkCopy")?.addEventListener("click", async () => {
    const transcript = document.getElementById("artworkTranscriptInput")?.value.trim();
    const miniContext = document.getElementById("artworkMiniContext")?.value.trim() || "";
    if (!transcript) {
        setHeadlineStudioStatus("Cole ou importe uma transcrição antes de gerar o texto de arte.", "error");
        return;
    }
    const button = document.getElementById("btnGenerateArtworkCopy");
    button.disabled = true;
    button.classList.add("loading");
    setHeadlineStudioStatus("Lendo a tese do corte e criando alternativas curtas...", "");
    try {
        const response = await fetch("/api/headline-studio/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                transcript,
                mini_context: miniContext,
                preferred_format: selectedArtworkFormat(),
                use_ai: document.getElementById("artworkUseAi")?.checked !== false,
            }),
        });
        const data = await parseJsonResponse(response, "Texto de arte");
        if (!response.ok || !data.success) throw new Error(data.error || "Não foi possível gerar o texto de arte");
        renderHeadlineStudioResults(data.studio);
        setHeadlineStudioStatus("Textos de arte prontos. Copie uma opção e ajuste apenas o necessário.", "success");
    } catch (error) {
        setHeadlineStudioStatus(error.message, "error");
        showToast("Não foi possível gerar os textos de arte.", "error");
    } finally {
        button.disabled = false;
        button.classList.remove("loading");
    }
});

document.getElementById("btnOpenTactiq")?.addEventListener("click", () => {
    const input = document.getElementById("sourceUrlInput");
    const url = normalizePublicUrlInput(input?.value);
    if (!url) {
        showSourceStatus("Informe primeiro uma URL pública do YouTube para abrir a transcrição assistida.", "error");
        return;
    }
    if (!/youtube\.com|youtu\.be/i.test(url)) {
        showSourceStatus("O Tactiq assistido aceita links do YouTube; para outras fontes, use a transcrição pública ou o Whisper.", "warning");
        return;
    }
    const tactiqUrl = `https://tactiq.io/tools/youtube-transcript?yt=${encodeURIComponent(url)}`;
    window.open(tactiqUrl, "_blank", "noopener,noreferrer");
    showSourceStatus("Tactiq aberto em uma nova aba. Copie ou baixe a transcrição e importe o TXT/SRT/VTT na aba Transcrição; o programa não faz scraping da página.", "success");
    addConsoleLog("[Tactiq] Transcrição assistida aberta; importe o arquivo ou cole o texto para validar timestamps antes do corte.", "info");
});

document.getElementById("btnProbeSource")?.addEventListener("click", async () => {
    const input = document.getElementById("sourceUrlInput");
    const url = normalizePublicUrlInput(input?.value);
    if (input && url) input.value = url;
    if (!url) {
        showSourceStatus("Informe uma URL pública.", "error");
        return;
    }
    showSourceStatus("Verificando fonte pública...", "");
    try {
        const res = await fetch("/api/source/probe", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url }),
        });
        const data = await parseJsonResponse(res, "Verificação da fonte");
        if (!res.ok || !data.success) throw new Error(data.error || "Fonte indisponível");
        state.sourceUrl = url;
        const duration = data.source.duration ? ` — ${formatTime(data.source.duration)}` : "";
        showSourceStatus(`${data.source.title || "Fonte válida"}${duration}. Pronta para importar.`, "success");
    } catch (error) {
        showSourceStatus(error.message, "error");
    }
});

async function chooseSourceDirectory() {
    try {
        const res = await fetch("/api/dialog/choose", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                mode: "folder",
                initial_path: state.sourceDownloadDir || "",
                title: "Escolha onde salvar o vídeo baixado",
            }),
        });
        const data = await parseJsonResponse(res, "Escolha da pasta");
        if (!res.ok || !data.success || !data.path) {
            if (data.cancelled) return "";
            throw new Error(data.error || "Não foi possível escolher a pasta");
        }
        state.sourceDownloadDir = data.path;
        const label = document.getElementById("sourceDestinationText");
        if (label) label.textContent = data.path;
        await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ source_download_dir: data.path }),
        });
        return data.path;
    } catch (error) {
        showSourceStatus(`Não foi possível abrir o explorador: ${error.message}`, "error");
        return "";
    }
}

document.getElementById("btnChooseSourceDir")?.addEventListener("click", async () => {
    await chooseSourceDirectory();
});

function isPlaceholderSourceDirectory(value) {
    const normalized = String(value || "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/\s+/g, " ")
        .trim()
        .toLowerCase();
    return [
        "a pasta sera escolhida ao importar",
        "a pasta sera escolhida ao baixar",
        "escolha uma pasta",
        "selecione uma pasta",
        "pasta padrao",
        "workspace/uploads",
    ].includes(normalized);
}

async function ensureSourceDirectory() {
    const existing = String(state.sourceDownloadDir || "").trim();
    if (existing && !isPlaceholderSourceDirectory(existing)) {
        const label = document.getElementById("sourceDestinationText");
        if (label) label.textContent = existing;
        return existing;
    }

    // Recover a path already rendered by settings or a previous selection so
    // importing a source never opens the native picker twice in one workflow.
    const label = document.getElementById("sourceDestinationText");
    const rendered = String(label?.textContent || "").trim();
    if (rendered && !isPlaceholderSourceDirectory(rendered)) {
        state.sourceDownloadDir = rendered;
        return rendered;
    }
    state.sourceDownloadDir = "";
    return chooseSourceDirectory();
}

function setSourceImportBusy(active) {
    state.sourceImportActive = Boolean(active);
    const buttons = [
        document.getElementById("btnDownloadSource"),
        document.getElementById("btnDownloadTranscribeSource"),
    ].filter(Boolean);
    buttons.forEach(button => {
        button.disabled = state.sourceImportActive;
        button.classList.toggle("loading", state.sourceImportActive);
    });
}

async function importSource(autoTranscribe = false) {
    if (state.sourceImportActive) return;
    const input = document.getElementById("sourceUrlInput");
    const url = normalizePublicUrlInput(input?.value);
    if (input && url) input.value = url;
    if (!url) {
        showSourceStatus("Informe uma URL pública.", "error");
        return;
    }
    const destination = await ensureSourceDirectory();
    if (!destination) {
        showSourceStatus("Importação cancelada: escolha uma pasta para salvar o vídeo.", "warning");
        return;
    }
    const maxHeight = parseInt(document.getElementById("sourceMaxHeight")?.value || state.sourceMaxHeight || 1080, 10);
    const transcriptIsPendingForNextSource = state.manualTranscriptVideo === "pending-source";
    const confirmedTranscript = autoTranscribe && transcriptIsPendingForNextSource && state.manualTranscript?.segments?.length
        ? {
            segments: state.manualTranscript.segments,
            language: state.manualTranscript.language || "pt",
        }
        : null;
    prepareNewOperationHud();
    state.sourceImportInitialVideoPath = state.selectedVideo || "";
    setSourceImportBusy(true);
    state.sourceImportJobId = "";
    state.sourceMaxHeight = maxHeight;
    showProgressBar();
    showSourceStatus(
        confirmedTranscript
            ? "Download iniciado; a transcrição manual confirmada será anexada sem nova busca."
            : autoTranscribe
                ? "Download e transcrição iniciados; acompanhe o console abaixo."
                : "Download iniciado; nenhuma transcrição será gerada.",
        "",
    );
    try {
        const res = await fetch("/api/source/import", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                url,
                destination_dir: destination,
                max_height: maxHeight,
                auto_transcribe: autoTranscribe,
                manual_transcript: confirmedTranscript,
                transcription_source: document.getElementById("settingTranscriptionSource")?.value || "auto",
            }),
        });
        const data = await parseJsonResponse(res, "Importação da fonte");
        if (!res.ok || !data.success) throw new Error(data.error || "Não foi possível iniciar a importação");
        state.sourceUrl = url;
        state.sourceImportJobId = String(data.job_id || "");
        const receivedJobId = state.sourceImportJobId;
        const terminalStatus = ["source_import_complete", "cancelled", "error"]
            .find(status => receivedJobId && state.terminalEventKeys[`${receivedJobId}:${status}`]);
        if (terminalStatus) {
            state.sourceImportJobId = "";
            state.sourceImportInitialVideoPath = "";
            setSourceImportBusy(false);
            addConsoleLog(`[Fonte] O servidor concluiu a importação antes da resposta de inicialização (${terminalStatus}); o resultado já foi aplicado.`, "info");
            return;
        }
        if (!receivedJobId) throw new Error("O servidor iniciou a importação sem informar um identificador de job.");
        const sourceMessage = confirmedTranscript
            ? "Download iniciado; a transcrição manual confirmada será anexada sem nova busca."
            : autoTranscribe
                ? "Download e transcrição iniciados; acompanhe o console abaixo."
                : "Download iniciado; nenhuma transcrição será gerada.";
        state.activeJob = {
            id: state.sourceImportJobId,
            state: data.state || "running",
            stage: "source_import",
            message: sourceMessage,
        };
        showProcessingControls(`[Job ${state.sourceImportJobId.slice(0, 8)}] ${sourceMessage}`);
        showProgressBar();
        addConsoleLog(`[Fonte] Download iniciado em ${destination}, limite de qualidade ${maxHeight}p.`, "info");
        if (confirmedTranscript) addConsoleLog("[Transcrição manual] Será reutilizada após o download; Gemini e Whisper serão ignorados.", "success");
        else if (autoTranscribe) addConsoleLog("[Fonte] A transcrição será gerada após o download, apenas se não houver fonte manual confirmada.", "info");
    } catch (error) {
        hideProgressBar();
        setSourceImportBusy(false);
        state.sourceImportJobId = "";
        state.sourceImportInitialVideoPath = "";
        showSourceStatus(error.message, "error");
        showToast(error.message, "error");
    }
}

document.getElementById("btnDownloadSource")?.addEventListener("click", () => importSource(false));
document.getElementById("btnDownloadTranscribeSource")?.addEventListener("click", () => importSource(true));

function normalizePublicUrlInput(rawUrl) {
    const value = String(rawUrl || "").trim();
    if (!value) return "";
    if (value.startsWith("//")) return `https:${value}`;
    if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(value)) return `https://${value}`;
    return value;
}

// ─── Settings ───

async function loadSettings() {
    try {
        const res = await fetch("/api/settings");
        state.settings = await res.json();
        applySettings();
    } catch (e) {
        console.error("Erro ao carregar settings:", e);
    }
}

function applySettings() {
    const s = state.settings;
    const runtimeVersion = document.getElementById("runtimeVersion");
    if (runtimeVersion && (s.program_version || s.program_revision)) {
        runtimeVersion.textContent = `${s.program_version || "build"} · ${s.program_revision || "local"}`;
        runtimeVersion.title = `Versão em uso: ${s.program_version || "desconhecida"} · revisão ${s.program_revision || "local"}`;
    }
    if (s.whisper_model) document.getElementById("settingWhisperModel").value = s.whisper_model;
    if (s.cut_method) document.getElementById("settingCutMethod").value = s.cut_method;
    if (s.cut_duration) document.getElementById("settingCutDuration").value = s.cut_duration;
    if (s.render_preset) document.getElementById("settingRenderPreset").value = s.render_preset;
    if (s.editorial_profile) document.getElementById("settingEditorialProfile").value = s.editorial_profile;
    if (s.editorial_focus) document.getElementById("settingEditorialFocus").value = s.editorial_focus;
    if (s.campaign_hub_account) document.getElementById("settingCampaignHubAccount").value = s.campaign_hub_account;
    if (s.min_silence_duration != null) {
        document.getElementById("settingSilenceDuration").value = s.min_silence_duration;
        document.getElementById("silenceValue").textContent = s.min_silence_duration + "s";
    }
    if (s.language) document.getElementById("settingLanguage").value = s.language;
    if (s.transcription_source) document.getElementById("settingTranscriptionSource").value = s.transcription_source;
    if (s.ai_correction != null) {
        document.getElementById("settingAiCorrection").dataset.active = s.ai_correction;
    }
    if (s.ai_backend) {
        document.getElementById("settingAiBackend").value = s.ai_backend;
        updateAiConfigVisibility(s.ai_backend);
    }
    if (s.ollama_model) document.getElementById("settingOllamaModel").value = s.ollama_model;
    const geminiStatus = document.getElementById("geminiKeyStatus");
    const geminiInput = document.getElementById("settingGeminiKey");
    if (geminiStatus) {
        const configured = safeBooleanFlag(s.gemini_api_key_configured) || Boolean(String(s.gemini_api_key || "").trim());
        geminiStatus.textContent = configured ? "Gemini configurado nesta instalação; o valor permanece oculto. Deixe o campo vazio para preservar." : "Gemini sem chave nesta instalação; o app usará legenda pública ou fallback local.";
        geminiStatus.className = `ai-key-status ${configured ? "configured" : "missing"}`;
        if (geminiInput) {
            geminiInput.placeholder = configured
                ? "Chave já configurada; deixe vazio para preservar"
                : "Cole a chave; ela será salva fora do checkout";
            geminiInput.title = configured
                ? "Uma chave já está salva. Digite outra somente para substituí-la."
                : "A chave será salva fora do checkout, em FuriaClipsData/config/local.env.";
        }
    }
    if (s.gemini_api_key && geminiInput) geminiInput.value = s.gemini_api_key;
    if (s.gemini_model) document.getElementById("settingGeminiModel").value = s.gemini_model;
    if (s.claude_api_key) document.getElementById("settingClaudeKey").value = s.claude_api_key;
    if (s.output_dir) {
        state.outputDir = s.output_dir;
        document.getElementById("outputDirText").textContent = s.output_dir || "workspace/exports (padrao)";
    }
    if (s.source_download_dir && !isPlaceholderSourceDirectory(s.source_download_dir)) {
        state.sourceDownloadDir = s.source_download_dir;
        const sourceLabel = document.getElementById("sourceDestinationText");
        if (sourceLabel) sourceLabel.textContent = s.source_download_dir;
    } else {
        state.sourceDownloadDir = "";
        const sourceLabel = document.getElementById("sourceDestinationText");
        if (sourceLabel) sourceLabel.textContent = "A pasta será escolhida ao importar";
    }
    if (s.source_max_height) {
        state.sourceMaxHeight = Math.min(1080, Number(s.source_max_height) || 1080);
        const quality = document.getElementById("sourceMaxHeight");
        if (quality) quality.value = String(state.sourceMaxHeight);
    }
}

function updateAiConfigVisibility(backend) {
    const automatic = backend === "auto";
    document.getElementById("ollamaConfig").style.display = (automatic || backend === "ollama") ? "block" : "none";
    document.getElementById("geminiConfig").style.display = (automatic || backend === "gemini") ? "block" : "none";
    document.getElementById("claudeConfig").style.display = backend === "claude" ? "block" : "none";

    const status = document.getElementById("aiStatus");
    const labels = {
        auto: "Modo automático: Gemini → Ollama → local",
        ollama: "Ollama local selecionado",
        gemini: "Google Gemini selecionado (chave opcional)",
        claude: "Claude API selecionado",
    };
    status.querySelector("span:last-child").textContent = labels[backend] || backend;
}

// Auto-save Gemini key when changed (no need to click Save)
document.getElementById("settingGeminiKey").addEventListener("change", async (e) => {
    const key = e.target.value.trim();
    if (key.length > 10) {
        try {
            await fetch("/api/settings", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ gemini_api_key: key }),
            });
            showToast("Gemini API key salva!", "success");
            // A chave fica disponível para o modo automático, sem trocar a preferência do usuário.
            state.settings.gemini_api_key = key;
            updateAiConfigVisibility(document.getElementById("settingAiBackend").value);
        } catch (err) { /* silent */ }
    }
});

document.getElementById("settingAiBackend").addEventListener("change", (e) => {
    updateAiConfigVisibility(e.target.value);
});

document.getElementById("btnSaveSettings").addEventListener("click", async () => {
            const typedGeminiKey = document.getElementById("settingGeminiKey").value.trim();
        const settings = {

        whisper_model: document.getElementById("settingWhisperModel").value,
        cut_method: document.getElementById("settingCutMethod").value,
        cut_duration: parseInt(document.getElementById("settingCutDuration").value),
        render_preset: document.getElementById("settingRenderPreset").value,
        editorial_profile: document.getElementById("settingEditorialProfile").value,
        editorial_focus: document.getElementById("settingEditorialFocus").value,
        campaign_hub_account: document.getElementById("settingCampaignHubAccount").value,
        min_silence_duration: parseFloat(document.getElementById("settingSilenceDuration").value),
        padding: 0.25,
        language: document.getElementById("settingLanguage").value,
        transcription_source: document.getElementById("settingTranscriptionSource").value,
        ai_correction: document.getElementById("settingAiCorrection").dataset.active === "true",
        ai_backend: document.getElementById("settingAiBackend").value,
        ollama_model: document.getElementById("settingOllamaModel").value,
        gemini_model: document.getElementById("settingGeminiModel").value.trim(),
                    // Campo vazio preserva a chave local já configurada; nunca envia um placeholder mascarado.
            ...(typedGeminiKey ? { gemini_api_key: typedGeminiKey } : {}),

        claude_api_key: document.getElementById("settingClaudeKey").value,
        output_dir: state.outputDir,
        source_download_dir: state.sourceDownloadDir,
        source_max_height: state.sourceMaxHeight,
    };

    try {
        const res = await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(settings),
        });
        if (res.ok) {
            showToast("Configuracoes salvas!", "success");
            state.settings = { ...state.settings, ...settings, gemini_api_key_configured: Boolean(String(typedGeminiKey || "").trim()) || safeBooleanFlag(state.settings.gemini_api_key_configured) };
            applySettings();
        }
    } catch (e) {
        showToast("Erro ao salvar configuracoes", "error");
    }
});

// Range sliders
document.getElementById("settingSilenceDuration").addEventListener("input", (e) => {
    document.getElementById("silenceValue").textContent = e.target.value + "s";
});

// Toggle
document.getElementById("settingAiCorrection").addEventListener("click", (e) => {
    const toggle = e.currentTarget;
    const active = toggle.dataset.active === "true";
    toggle.dataset.active = !active;
});

// ─── Console Toggle ───

document.getElementById("consoleToggle").addEventListener("click", () => {
    const content = document.getElementById("consoleContent");
    const icon = document.querySelector(".toggle-icon");
    content.classList.toggle("collapsed");
    icon.style.transform = content.classList.contains("collapsed") ? "rotate(-90deg)" : "";
});

// ─── Help Modal ───

document.getElementById("btnHelp").addEventListener("click", () => {
    document.getElementById("helpModal").classList.add("active");
});

function closeHelpModal() {
    document.getElementById("helpModal").classList.remove("active");
}

// Close modals on overlay click
document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
        if (e.target === overlay) {
            overlay.classList.remove("active");
        }
    });
});

// ─── Toast Notifications ───

let toastContainer = null;

function showToast(message, type = "info") {
    if (!toastContainer) {
        toastContainer = document.createElement("div");
        toastContainer.className = "toast-container";
        document.body.appendChild(toastContainer);
    }

    const icons = {
        success: "check_circle",
        error: "error",
        warning: "warning",
        info: "info",
    };

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="material-icons-round" style="font-size:18px">${icons[type]}</span>
        <span>${message}</span>`;

    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(100px)";
        toast.style.transition = "all 0.3s";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ─── Export All ───

document.getElementById("btnExportAll").addEventListener("click", () => {
    if (state.clips.length === 0) {
        showToast("Nenhum clip para exportar", "warning");
        return;
    }
    state.clips.forEach((clip, i) => {
        setTimeout(() => downloadClip(i), i * 500);
    });
    showToast(`Exportando ${state.clips.length} clips...`, "info");
});

// ─── Context Chips ───

document.querySelectorAll(".context-chip").forEach(chip => {
    chip.addEventListener("click", () => {
        const input = document.getElementById("userContextInput");
        input.value = chip.dataset.context;
        // Highlight active chip
        document.querySelectorAll(".context-chip").forEach(c => c.classList.remove("active"));
        chip.classList.add("active");
    });
});

// ─── Transcript Search ───

const transcriptSearchInput = document.getElementById("transcriptSearchInput");
const btnClearSearch = document.getElementById("btnClearSearch");

if (transcriptSearchInput) {
    transcriptSearchInput.addEventListener("input", (e) => {
        const query = e.target.value.trim().toLowerCase();
        const countEl = document.getElementById("searchCount");
        const clearBtn = document.getElementById("btnClearSearch");

        if (!query) {
            if (countEl) countEl.textContent = "";
            if (clearBtn) clearBtn.style.display = "none";
            // Remove highlights
            document.querySelectorAll(".clip-transcript-content").forEach(el => {
                el.innerHTML = el.textContent;
            });
            return;
        }

        if (clearBtn) clearBtn.style.display = "inline-flex";

        let totalMatches = 0;
        document.querySelectorAll(".clip-transcript-content").forEach(el => {
            const text = el.textContent;
            const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
            const matches = text.match(regex);
            if (matches) {
                totalMatches += matches.length;
                el.innerHTML = text.replace(regex, '<span class="search-highlight">$1</span>');
                // Auto-expand transcript panels with matches
                const parent = el.closest(".clip-transcript");
                if (parent) parent.classList.add("expanded");
            } else {
                el.innerHTML = text;
            }
        });

        if (countEl) {
            countEl.textContent = totalMatches > 0 ? `${totalMatches} encontrados` : "Nenhum resultado";
        }
    });
}

if (btnClearSearch) {
    btnClearSearch.addEventListener("click", () => {
        if (transcriptSearchInput) {
            transcriptSearchInput.value = "";
            transcriptSearchInput.dispatchEvent(new Event("input"));
        }
    });
}

// ─── Keyboard Shortcuts ───

document.addEventListener("keydown", (e) => {
    // Don't capture if typing in input/textarea
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") {
        return;
    }

    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        const cutButton = document.getElementById("actionCut")?.querySelector(".btn-action");
        if (cutButton && !cutButton.disabled) cutButton.click();
        return;
    }

    switch (e.key) {
        case " ":
            // Space = play/pause current video
            e.preventDefault();
            const activeVideo = document.querySelector(".result-card video");
            if (activeVideo) {
                if (activeVideo.paused) activeVideo.play();
                else activeVideo.pause();
            }
            break;
        case "f":
        case "F":
            // F = focus search
            e.preventDefault();
            if (transcriptSearchInput) transcriptSearchInput.focus();
            break;
        case "Escape":
            if (state.activeJob && ["queued", "running", "cancel_requested"].includes(state.activeJob.state)) {
                requestCancelOperation();
                return;
            }
            // Close any open modal
            document.querySelectorAll(".modal-overlay.active").forEach(m => m.classList.remove("active"));
            break;
    }
});

// ─── Init ───

document.addEventListener("DOMContentLoaded", () => {
    loadSettings();
    startCampaignHubLocalStatusPolling();
    loadMediaFiles();
    loadTranscriptArchive();
    recoverActiveJobs();
    // Check Ollama status on load
    socket.emit("check_ollama");
});


// ─── Pesquisa editorial local do Campaign Hub (somente leitura) ───
function resetCampaignSearchPanel() {
    state.campaignSearchToken += 1;
    const input = document.getElementById("campaignSearchInput");
    const result = document.getElementById("campaignSearchResult");
    const status = document.getElementById("campaignSearchStatus");
    const dateFrom = document.getElementById("campaignSearchDateFrom");
    const dateTo = document.getElementById("campaignSearchDateTo");
    const platform = document.getElementById("campaignSearchPlatform");
    if (input) input.value = "";
    if (platform) platform.value = "";
    if (dateFrom) dateFrom.value = "";
    if (dateTo) dateTo.value = "";
    if (result) {
        result.hidden = true;
        result.innerHTML = "";
    }
    if (status) status.textContent = "Pesquise no cache local do Campaign Hub quando precisar de uma referência.";
}

function formatCampaignSearchDate(value) {
    const raw = String(value || "").trim();
    const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
    return match ? `${match[3]}/${match[2]}/${match[1]}` : (raw || "data não informada");
}

function formatCampaignSearchSeconds(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric) || numeric < 0) return "";
    const total = Math.floor(numeric);
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const seconds = total % 60;
    return hours ? `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}` : `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function campaignSearchCopyButton(text, label, icon = "content_copy") {
    const value = String(text || "").trim();
    if (!value) return "";
    return `<button class="btn btn-sm btn-secondary campaign-search-copy" type="button" data-campaign-copy="${encodeURIComponent(value)}"><span class="material-icons-round">${escapeHtml(icon)}</span>${escapeHtml(label)}</button>`;
}

function renderCampaignSearchMoments(moments) {
    if (!Array.isArray(moments) || !moments.length) return "";
    const rows = moments.slice(0, 6).map((moment, index) => {
        const start = formatCampaignSearchSeconds(moment.start_seconds);
        const end = formatCampaignSearchSeconds(moment.end_seconds);
        const time = start && end ? `${start}–${end}` : start || "momento sem timestamp";
        const label = String(moment.label || `Momento ${index + 1}`).trim();
        const reason = String(moment.reason || "").trim();
        const copyText = [label, time, reason].filter(Boolean).join(" · ");
        const momentUrl = safeExternalUrl(moment.preview_url);
        const momentAction = momentUrl ? `<a class="campaign-search-moment-open" href="${escapeHtml(momentUrl)}" target="_blank" rel="noopener noreferrer" title="Abrir momento no YouTube"><span class="material-icons-round">play_arrow</span>Abrir</a>` : "";
        return `<li class="campaign-search-moment"><button class="campaign-search-moment-time campaign-search-copy" type="button" data-campaign-copy="${encodeURIComponent(time)}" title="Copiar timestamp"><span class="material-icons-round">schedule</span>${escapeHtml(time)}</button><div><strong>${escapeHtml(label)}</strong>${reason ? `<p>${escapeHtml(reason)}</p>` : ""}</div><span class="campaign-search-moment-actions">${momentAction}${campaignSearchCopyButton(copyText, "Copiar", "content_copy")}</span></li>`;
    }).join("");
    return `<div class="campaign-search-moments"><strong><span class="material-icons-round">auto_awesome</span> Momentos fortes</strong><ul>${rows}</ul></div>`;
}

function renderCampaignSearchResult(payload) {
    const container = document.getElementById("campaignSearchResult");
    if (!container) return;
    if (!payload || !payload.success) {
        container.hidden = false;
        container.innerHTML = `<p class="context-empty-copy"><span class="material-icons-round">error_outline</span>${escapeHtml(payload?.error || "Nenhum resultado disponível.")}</p>`;
        return;
    }
    const counts = payload.counts || {};
    const results = Array.isArray(payload.results) ? payload.results : [];
    const countLine = `${Number(payload.total_cached_matches || 0)} resultado(s) no cache · ${Number(counts.with_timestamps || 0)} com timestamps · ${Number(counts.download_eligible || 0)} com URL + timestamps confirmados`;
    const cards = results.length ? results.map((item, index) => {
        const script = String(item.full_script || item.summary || item.caption || "").trim();
        const title = String(item.title || "Referência editorial sem título").trim();
        const summary = String(item.summary || script || "Transcrição não disponível no snapshot.").trim();
        const excerpt = summary.length > 420 ? `${summary.slice(0, 417)}…` : summary;
        const ratio = Number(item.performance_ratio || 0);
        const similarity = Math.round(Number(item.similarity || item.semantic_score || 0) * 100);
        const score = Number(item.editorial_score || 0).toFixed(1);
        const start = formatCampaignSearchSeconds(item.start_seconds);
        const end = formatCampaignSearchSeconds(item.end_seconds);
        const duration = formatCampaignSearchSeconds(item.duration_seconds);
        const timing = start && end ? `${start}–${end}` : start ? `a partir de ${start}` : "intervalo não informado";
        const topics = Array.isArray(item.topics) && item.topics.length ? item.topics : (Array.isArray(item.tags) ? item.tags : []);
        const badges = topics.slice(0, 5).map(tag => `<span>${escapeHtml(tag)}</span>`).join("");
        const category = item.category ? `<span class="campaign-search-category">${escapeHtml(item.category)}</span>` : "";
        const timestampLabel = item.has_timestamps ? "timestamps disponíveis" : "sem timestamps no cache";
        const downloadLabel = item.download_action_available ? "download disponível" : item.download_eligible ? "referência + timestamps; download local não habilitado" : "download não confirmado";
        const reviewLabels = [];
        if (item.needs_context) reviewLabels.push("contexto adicional recomendado");
        if (Array.isArray(item.risk_flags)) reviewLabels.push(...item.risk_flags);
        if (Array.isArray(item.gate_warnings)) reviewLabels.push(...item.gate_warnings);
        const reviewNote = reviewLabels.length ? `<span class="campaign-search-status review"><span class="material-icons-round">rule</span>${escapeHtml(reviewLabels.join(" · "))}</span>` : "";
        const sourceUrl = safeExternalUrl(item.source_url || item.url);
        const sourceAction = sourceUrl
            ? `<a class="btn btn-sm btn-secondary" href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer"><span class="material-icons-round">open_in_new</span> Abrir fonte</a>`
            : `<span class="campaign-search-status review">URL não autorizada para abrir</span>`;
        const previewUrl = safeExternalUrl(item.source_preview_url);
        const previewAction = previewUrl
            ? `<a class="btn btn-sm btn-primary" href="${escapeHtml(previewUrl)}" target="_blank" rel="noopener noreferrer"><span class="material-icons-round">play_arrow</span> Abrir trecho</a>`
            : "";
        const copyPauta = [title, item.summary, item.trigger_question ? `Pergunta-gatilho: ${item.trigger_question}` : "", `Intervalo: ${timing}`, item.source_title ? `Fonte: ${item.source_title}` : ""].filter(Boolean).join("\n");
        const copyInterval = start && end ? `${start}\t${end}` : start;
        const sourceMeta = [item.source_title, item.source_video_id ? `ID ${item.source_video_id}` : ""].filter(Boolean).join(" · ");
        return `<article class="campaign-search-card campaign-search-block-card"><div class="campaign-search-card-head"><strong>#${index + 1} · ${escapeHtml(item.channel || "conta não informada")}</strong><span>${escapeHtml(formatCampaignSearchDate(item.published_at))}</span></div><div class="campaign-search-card-title"><h4>${escapeHtml(title)}</h4>${category}</div>${sourceMeta ? `<p class="campaign-search-source"><span class="material-icons-round">movie</span>${escapeHtml(sourceMeta)}</p>` : ""}<div class="campaign-search-card-meta"><span>${escapeHtml(item.platform || item.source_platform || "fonte")}</span><span>bloco ${escapeHtml(timing)}</span>${duration ? `<span>duração ${escapeHtml(duration)}</span>` : ""}<span>relevância ${similarity}%</span><span>score ${escapeHtml(score)}</span>${ratio ? `<span>ratio ${ratio.toFixed(2)}x</span>` : ""}</div>${badges || item.trigger_question ? `<div class="campaign-search-tags">${badges}${item.trigger_question ? `<span class="campaign-search-question"><span class="material-icons-round">help_outline</span>${escapeHtml(item.trigger_question)}</span>` : ""}</div>` : ""}<p>${escapeHtml(excerpt)}</p>${item.primary_reason ? `<p class="campaign-search-reason"><span class="material-icons-round">lightbulb</span>${escapeHtml(item.primary_reason)}</p>` : ""}${renderCampaignSearchMoments(item.moments)}${reviewNote ? `<div class="campaign-search-review">${reviewNote}</div>` : ""}<div class="campaign-search-card-foot"><span class="campaign-search-status ${item.has_timestamps ? "ready" : "review"}">${escapeHtml(timestampLabel)} · ${escapeHtml(downloadLabel)}</span><div class="campaign-search-card-actions">${campaignSearchCopyButton(copyPauta, "Copiar pauta", "content_copy")}${campaignSearchCopyButton(script, "Copiar transcrição", "description")}${campaignSearchCopyButton(copyInterval, "Copiar intervalo", "schedule")}${previewAction}${sourceAction}</div></div></article>`;
    }).join("") : `<p class="context-empty-copy"><span class="material-icons-round">search_off</span>Nenhum resultado no cache local para esta consulta. Faça uma nova exportação somente leitura do Campaign Hub para ampliar a pesquisa.</p>`;
    container.hidden = false;
    container.innerHTML = `<div class="campaign-search-summary"><strong>${escapeHtml(countLine)}</strong><small>Fonte: snapshot local somente leitura · bloco editorial não é aprovação nem publicação</small></div><div class="campaign-search-list">${cards}</div>`;
    container.querySelectorAll("[data-campaign-copy]").forEach(button => {
        button.addEventListener("click", () => {
            try {
                copyToClipboard(decodeURIComponent(button.dataset.campaignCopy || ""));
            } catch (_error) {
                copyToClipboard(button.dataset.campaignCopy || "");
            }
        });
    });
}

async function searchCampaignHubEditorial() {
    const input = document.getElementById("campaignSearchInput");
    const account = document.getElementById("campaignSearchAccount");
    const platform = document.getElementById("campaignSearchPlatform");
    const dateFrom = document.getElementById("campaignSearchDateFrom");
    const dateTo = document.getElementById("campaignSearchDateTo");
    const status = document.getElementById("campaignSearchStatus");
    const button = document.getElementById("btnCampaignSearch");
    const query = input?.value.trim() || "";
    const searchToken = ++state.campaignSearchToken;
    if (!query) {
        if (status) status.textContent = "Informe um assunto para pesquisar.";
        showToast("Informe um assunto para pesquisar.", "warning");
        return;
    }
    if (button) { button.disabled = true; button.classList.add("loading"); }
    if (status) status.textContent = "Consultando o índice editorial local…";
    try {
        const response = await fetch("/api/editorial/search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                query,
                account: account?.value || "",
                platform: platform?.value || "",
                published_from: dateFrom?.value || "",
                published_to: dateTo?.value || "",
                limit: 25,
            }),
        });
        const payload = await parseJsonResponse(response, "Pesquisa editorial");
        if (searchToken !== state.campaignSearchToken) return;
        if (!response.ok || !payload.success) throw new Error(payload.error || "Pesquisa editorial indisponível");
        renderCampaignSearchResult(payload);
        if (status) {
            const dateNote = payload.published_from || payload.published_to
                ? ` no período ${payload.published_from || "início aberto"} a ${payload.published_to || "fim aberto"}`
                : "";
            status.textContent = `${Number(payload.returned || 0)} resultado(s) exibido(s)${dateNote}.`;
        }
    } catch (error) {
        if (searchToken !== state.campaignSearchToken) return;
        if (status) status.textContent = error.message;
        renderCampaignSearchResult({ success: false, error: error.message });
        showToast(error.message, "error");
    } finally {
        if (button) { button.disabled = false; button.classList.remove("loading"); }
    }
}

document.getElementById("btnCampaignSearch")?.addEventListener("click", searchCampaignHubEditorial);
document.getElementById("campaignSearchInput")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
        event.preventDefault();
        searchCampaignHubEditorial();
    }
});


// ─── Editorial workbench navigation ───
function setupWorkbenchNavigation() {
    const links = Array.from(document.querySelectorAll(".workbench-nav-link[href^='#']"));
    if (!links.length) return;
    const entries = links.map((link) => ({
        link,
        section: document.querySelector(link.getAttribute("href")),
    })).filter(({ section }) => section);
    if (!entries.length) return;

    const setActive = (activeLink) => {
        links.forEach((link) => link.classList.toggle("active", link === activeLink));
    };
    const refresh = () => {
        const visibleEntries = entries.filter(({ section }) => {
            const style = window.getComputedStyle(section);
            return style.display !== "none" && !section.hidden;
        });
        if (!visibleEntries.length) return;
        let current = visibleEntries[0];
        visibleEntries.forEach((entry) => {
            if (entry.section.getBoundingClientRect().top <= 190) current = entry;
        });
        setActive(current.link);
    };
    const scheduleRefresh = () => {
        if (window.__furiaWorkbenchNavFrame) return;
        window.__furiaWorkbenchNavFrame = window.requestAnimationFrame(() => {
            window.__furiaWorkbenchNavFrame = 0;
            refresh();
        });
    };

    links.forEach((link) => link.addEventListener("click", () => setActive(link)));
    window.addEventListener("scroll", scheduleRefresh, { passive: true });
    window.addEventListener("resize", scheduleRefresh);
    refresh();
}

document.addEventListener("DOMContentLoaded", setupWorkbenchNavigation);
