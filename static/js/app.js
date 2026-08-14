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
    outputFolder: "",
    activeJob: null,
    operationJobs: [],
    operationProjects: [],
    manualTranscript: null,
    manualTranscriptVideo: "",
    transcriptArchive: null,
    lastReviewAction: null,
    sourceUrl: "",
    sourceDownloadDir: "",
    sourceMaxHeight: 1080,
};

// ─── WebSocket Connection ───

const socket = io();

socket.on("connect", () => {
    state.connected = true;
    addConsoleLog("[Sistema] Conectado ao servidor.", "success");
});

socket.on("disconnect", () => {
    state.connected = false;
    addConsoleLog("[Sistema] Desconectado do servidor.", "error");
});

socket.on("connected", (data) => {
    addConsoleLog(`[Sistema] ${data.message}`, "success");
});

socket.on("progress", (data) => {
    addConsoleLog(`[${data.time}] ${data.message}`, data.level);
    showProgressBar();
});

socket.on("status", (data) => {
    handleStatusUpdate(data);
});

socket.on("job_update", (job) => {
    handleJobUpdate(job);
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
    state.selectionSource = data.source;
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
        dot.classList.add("offline");
        label.textContent = data.mode_label || "Gemini Offline";
        modeIndicator.classList.add("nlp-mode");
        modeIcon.textContent = "cloud_off";
        modeLabel.textContent = "Gemini Offline";
    } else if (data.connected) {
        dot.classList.add("connected");
        label.textContent = "Ollama Conectado";
        modeIndicator.classList.add("llm-mode");
        modeIcon.textContent = "psychology";
        modeLabel.textContent = "IA Inteligente";
        if (data.model_available) {
            label.textContent = `Ollama (${data.model})`;
        }
    } else {
        dot.classList.add("offline");
        label.textContent = "Ollama Offline";
        modeIndicator.classList.add("nlp-mode");
        modeIcon.textContent = "text_fields";
        modeLabel.textContent = "NLP Basico";
    }
}

// ─── Status Handlers ───

function handleStatusUpdate(data) {
    switch (data.status) {
        case "silence_complete":
            hideProgressBar();
            showToast("Silencio removido com sucesso!", "success");
            loadMediaFiles();
            break;
        case "transcribe_complete":
            hideProgressBar();
            if (data.data) {
                state.manualTranscript = data.data;
                state.manualTranscriptVideo = state.selectedVideo || "";
                hydrateTranscriptEditor(data.data, data.data.archive_metadata || data.data.archive);
            }
            showToast("Transcricao concluida!", "success");
            break;
        case "source_import_complete":
            hideProgressBar();
            state.sourceDownloadDir = data.data.destination_dir || state.sourceDownloadDir;
            state.transcriptArchive = data.data.transcription_archive || data.data.transcription_files?.archive || null;
            if (data.data.transcription) {
                state.manualTranscript = data.data.transcription;
                state.manualTranscriptVideo = data.data.path || data.data.absolute_path || "";
                hydrateTranscriptEditor(data.data.transcription, state.transcriptArchive);
                const transcriptCount = data.data.transcription.segment_count || data.data.transcription.segments?.length || 0;
                const transcriptFile = data.data.transcription_archive?.text || data.data.transcription_files?.archive?.text || data.data.transcription_files?.text;
                const transcriptLabel = transcriptFile ? ` Arquivo persistente: ${transcriptFile}` : "";
                showSourceStatus(`Fonte importada e transcrição automática pronta: ${transcriptCount} segmentos.${transcriptLabel}`, "success");
            } else {
                showSourceStatus("Fonte importada; a transcrição automática não ficou disponível. Você pode clicar em Gerar do vídeo.", "warning");
            }
            const externalImported = {
                path: data.data.path || data.data.absolute_path,
                name: data.data.title || (data.data.path || "Vídeo importado").split(/[\\/]/).pop(),
                size_human: "Fonte pública",
            };
            loadMediaFiles().then(() => {
                const imported = state.mediaFiles.find(item => item.path === data.data.path);
                selectVideo(imported || externalImported, null);
            });
            showToast(data.data.transcription ? "Vídeo e transcrição importados!" : "Vídeo do link importado!", "success");
            break;
        case "cut_complete":
            hideProgressBar();
            updateWorkspaceWorkflow("review", "Revisão pronta");
            state.selectionSource = data.data.selection_source || "nlp";
            state.outputFolder = data.data.output_folder || "";
            showToast(`${data.data.clips.length} clips gerados e ranqueados!`, "success");
            displayResults(data.data.clips, data.data.video_layout || null);
            updateResultsModeBadge(state.selectionSource);
            updateOpenFolderButton(state.outputFolder);
            break;
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
            showToast(`Processo completo! ${data.data.total_clips} clips gerados e ranqueados.`, "success");
            displayResults(data.data.clips, data.data.video_layout || null);
            updateOpenFolderButton(state.outputFolder);
            loadMediaFiles();
            break;
        case "cancelled":
            hideProgressBar();
            updateWorkspaceWorkflow("source", "Operação pausada");
            showToast(data.data?.message || "Operação cancelada.", "warning");
            addConsoleLog("[Sistema] Operação cancelada com segurança.", "warning");
            break;
        case "error":
            hideProgressBar();
            updateWorkspaceWorkflow("source", "Atenção necessária");
            showToast(data.data.message || "Erro no processamento", "error");
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

function showProcessingControls(label = "Processamento em andamento.") {
    const controls = document.getElementById("processingControls");
    const status = document.getElementById("processingOperationStatus");
    const button = document.getElementById("btnCancelOperation");
    const journey = document.getElementById("processingJourney");
    if (controls) controls.style.display = "flex";
    if (status) status.textContent = label;
    if (button) button.disabled = false;
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

function showProgressBar() {
    showProcessingControls();
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

function renderOperationDashboard(jobs = state.operationJobs || []) {
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
        const message = escapeHtml(job.error || job.message || job.stage || "Aguardando execução");
        const stateLabel = escapeHtml(String(job.state || "queued").replaceAll("_", " "));
        return `<article class="operation-job ${escapeHtml(job.state || "queued")}">
            <div class="operation-job-head">
                <div class="operation-job-type"><span class="material-icons-round">${job.type === "cut_shorts" ? "content_cut" : "auto_awesome"}</span>${escapeHtml(formatOperationJobType(job.type))}</div>
                <span class="operation-job-state">${stateLabel}</span>
            </div>
            <p class="operation-job-message">${message}</p>
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
    if (!panel || !title || !text || !badge) return;
    const sample = Number(calibration.sample_size || 0);
    const minimum = Number(calibration.minimum_sample_size || 12);
    panel.classList.toggle("is-active", Boolean(calibration.eligible));
    if (calibration.eligible) {
        title.textContent = "Calibração editorial ativa";
        text.textContent = `${sample} decisões finais já ajudam a ajustar o ranking de forma limitada e explicável.`;
        badge.textContent = "ATIVA";
    } else {
        const remaining = Math.max(0, minimum - sample);
        title.textContent = "Aprendizado editorial em coleta";
        text.textContent = `${sample} decisão(ões) final(is) registradas. Faltam ${remaining} para avaliar uma calibração conservadora.`;
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
    const reached = Boolean(progress.target_reached);
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
            <div class="transcript-archive-meta"><strong>${escapeHtml(item.source_video || item.relative_dir || "Transcrição")}</strong><small>${source} · ${project} · ${Number(item.valid_segment_count || 0)} segmentos válidos</small></div>
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
        const summary = document.getElementById("transcriptArchiveSummary");
        if (summary) summary.textContent = `Arquivo de transcrições indisponível: ${error.message}`;
    }
}

async function requestEditorialBackup() {
    const button = document.getElementById("btnEditorialBackup");
    if (button) button.disabled = true;
    try {
        const response = await fetch("/api/editorial/backup", { method: "POST" });
        const payload = await parseJsonResponse(response, "Backup editorial");
        if (!response.ok || !payload.success) throw new Error(payload.error || "Não foi possível criar o backup");
        window.location.assign(`/api/editorial/backup/${encodeURIComponent(payload.filename)}`);
        showToast(`Backup criado (${formatDataSize(payload.size_bytes)}). Guarde o arquivo fora da pasta do programa.`, "success");
        renderEditorialData(payload.summary || {});
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
    } catch (error) {
        showToast(error.message || "Não foi possível restaurar o backup", "error");
    } finally {
        input.value = "";
        if (button) button.disabled = false;
    }
}

async function loadOperationDashboard() {
    try {
        const response = await fetch("/api/jobs?limit=12");
        const payload = await parseJsonResponse(response, "Histórico de operações");
        if (!response.ok) throw new Error(payload.error || "Não foi possível carregar os jobs");
        state.operationJobs = Array.isArray(payload.jobs) ? payload.jobs : [];
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
    }
}

function handleJobUpdate(job, options = {}) {
    state.activeJob = job;
    const existingIndex = (state.operationJobs || []).findIndex((item) => item.id === job.id);
    if (existingIndex >= 0) state.operationJobs[existingIndex] = job;
    else state.operationJobs = [job, ...(state.operationJobs || [])];
    renderOperationDashboard();
    if (options.refreshDashboard !== false) window.clearTimeout(state.operationRefreshTimer);
    if (options.refreshDashboard !== false) {
        state.operationRefreshTimer = window.setTimeout(loadOperationDashboard, 700);
    }
    const container = document.getElementById("progressBarContainer");
    const bar = document.getElementById("progressBar");
    if (container && bar && ["queued", "running", "cancel_requested"].includes(job.state)) {
        container.style.display = "block";
        bar.dataset.animating = "false";
        bar.style.width = `${Math.max(2, Math.min(100, job.progress || 0))}%`;
        addConsoleLog(`[Job ${job.id.slice(0, 8)}] ${job.message || job.stage || job.state}`, "info");
    }
    if (["queued", "running", "cancel_requested"].includes(job.state)) {
        showProcessingControls(`[Job ${job.id.slice(0, 8)}] ${job.message || job.stage || "Processando"}`);
    }
    if (job.state === "completed") {
        if (bar) bar.style.width = "100%";
        setTimeout(hideProgressBar, 250);
    } else if (job.state === "failed") {
        hideProgressBar();
        showToast(job.error || "O job falhou", "error");
    } else if (job.state === "cancelled") {
        hideProgressBar();
        hideProcessingControls();
        showToast("Processamento cancelado", "warning");
    }
}

async function recoverActiveJobs() {
    await loadOperationDashboard();
}

function hideProgressBar() {
    hideProcessingControls();
    const container = document.getElementById("progressBarContainer");
    const bar = document.getElementById("progressBar");
    bar.style.width = "100%";
    if (bar.dataset.interval) {
        clearInterval(parseInt(bar.dataset.interval));
        bar.dataset.animating = "";
    }
    setTimeout(() => {
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
    const changedVideo = state.selectedVideo && state.selectedVideo !== item.path;
    state.selectedVideo = item.path;
    state.selectedVideoName = item.name;
    if (changedVideo && state.manualTranscriptVideo !== item.path) {
        state.manualTranscript = null;
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
            <button class="btn btn-sm btn-deselect" onclick="deselectVideo()" title="Remover selecao">
                <span class="material-icons-round" style="font-size:14px">close</span>
            </button>
        </div>`;

    // Update media grid selection
    document.querySelectorAll(".media-card").forEach(el => el.classList.remove("selected"));
    if (sourceElement?.classList) sourceElement.classList.add("selected");

    // Show video preview
    showVideoPreview(item);

    addConsoleLog(`[Sistema] Video selecionado: ${item.name}`, "info");
    showToast(`Video selecionado: ${truncateName(item.name, 30)}`, "success");
}

function showVideoPreview(item) {
    const section = document.getElementById("videoPreviewSection");
    const video = document.getElementById("videoPreview");
    const source = document.getElementById("videoPreviewSource");
    const nameEl = document.getElementById("previewVideoName");

    section.style.display = "block";
    nameEl.textContent = item.name;
    source.src = mediaUrlForPath(item.path);
    video.load();

    video.addEventListener("loadedmetadata", () => {
        const dur = formatTime(video.duration);
        const res = `${video.videoWidth}x${video.videoHeight}`;
        document.getElementById("videoDuration").textContent = `Duracao: ${dur}`;
        document.getElementById("videoResolution").textContent = `Resolucao: ${res}`;
    }, { once: true });
}

function deselectVideo() {
    state.selectedVideo = null;
    state.selectedVideoName = "";
    document.querySelectorAll(".media-card").forEach(el => el.classList.remove("selected"));

    const info = document.getElementById("selectedVideoInfo");
    info.className = "selected-video";
    info.innerHTML = `
        <div class="no-video">
            <span class="material-icons-round">videocam_off</span>
            <p>Nenhum video selecionado</p>
        </div>`;

    // Hide preview
    document.getElementById("videoPreviewSection").style.display = "none";
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

// Drag and drop on media library
const mediaDropZone = document.getElementById("mediaDropZone");
const mediaSection = document.getElementById("mediaLibrarySection");

[mediaDropZone, mediaSection].forEach(el => {
    el.addEventListener("dragover", (e) => {
        e.preventDefault();
        mediaDropZone.classList.add("drag-over");
    });
    el.addEventListener("dragleave", () => {
        mediaDropZone.classList.remove("drag-over");
    });
    el.addEventListener("drop", async (e) => {
        e.preventDefault();
        mediaDropZone.classList.remove("drag-over");
        const files = e.dataTransfer.files;
        for (const file of files) {
            await uploadFile(file);
        }
        await loadMediaFiles();
        // Auto-select
        setTimeout(() => {
            const cards = document.querySelectorAll(".media-card");
            if (cards.length > 0 && !state.selectedVideo) {
                cards[cards.length - 1].click();
            }
        }, 100);
    });
});

// ─── Close Preview ───

document.getElementById("btnClosePreview").addEventListener("click", () => {
    document.getElementById("videoPreviewSection").style.display = "none";
});

// ─── Actions ───

function requireVideo() {
    if (!state.selectedVideo) {
        showToast("Selecione um video primeiro na biblioteca!", "warning");
        return false;
    }
    return true;
}

document.getElementById("actionSilence").querySelector(".btn-action").addEventListener("click", async () => {
    if (!requireVideo()) return;
    addConsoleLog("[Acao] Iniciando remocao de silencio...", "info");
    await fetch("/api/process/silence", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_path: state.selectedVideo }),
    });
});

document.getElementById("actionCut").querySelector(".btn-action").addEventListener("click", async () => {
    if (!requireVideo()) return;
    const userContext = document.getElementById("userContextInput").value.trim();
    addConsoleLog("[Acao] Iniciando corte inteligente de shorts...", "info");
    if (userContext) addConsoleLog(`[Contexto] "${userContext}"`, "info");
    const videoGenre = document.getElementById("settingVideoGenre").value;

    // Auto-save Gemini key before processing (in case user pasted but didn't click Save)
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
            face_tracking: true,
            user_context: userContext,
            video_genre: videoGenre,
            transcription_source: document.getElementById("settingTranscriptionSource")?.value || "auto",
            ...(state.manualTranscript ? {
                transcript_segments: state.manualTranscript.segments,
                transcript_language: state.manualTranscript.language || "pt",
            } : {}),
        }),
    });
    const started = await parseJsonResponse(response, "Corte inteligente");
    if (!response.ok || started.error) throw new Error(started.error || "Não foi possível iniciar o corte");
    if (started.job_id) {
        state.activeJob = { id: started.job_id, state: started.state || "queued" };
        showProcessingControls("Corte adicionado à fila persistente.");
    }
});

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
    addConsoleLog("[Acao] Iniciando processo completo...", "info");
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
            ...(state.manualTranscript ? {
                transcript_segments: state.manualTranscript.segments,
                transcript_language: state.manualTranscript.language || "pt",
            } : {}),
        }),
    });
    const started = await parseJsonResponse(response, "Processo completo");
    if (!response.ok || started.error) throw new Error(started.error || "Não foi possível iniciar o processo completo");
    if (started.job_id) {
        state.activeJob = { id: started.job_id, state: started.state || "queued" };
        showProcessingControls("Processo completo adicionado à fila persistente.");
    }
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
    await fetch("/api/process/subtitles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            video_path: state.selectedVideo,
            subtitle_settings: subtitleSettings,
        }),
    });
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
    await fetch("/api/process/thumbnail", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            video_path: state.selectedVideo,
            text, style, time,
        }),
    });
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

// ─── Results Display ───

function mediaUrlForPath(path) {
    if (!path) return "";
    const value = String(path).replaceAll("\\", "/");
    if (value.startsWith("/workspace/")) return value;
    if (value.startsWith("workspace/")) return `/${value}`;
    if (/^[A-Za-z]:\//.test(value) || value.startsWith("/")) {
        return `/api/output_file?path=${encodeURIComponent(path)}`;
    }
    return `/workspace/${value.replace(/^\\+/, "")}`;
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

function mediaUrlForClip(clip) {
    return mediaUrlForPath(clip.subtitled_path || clip.path);
}

function displayResults(clips, videoLayout = null) {
    state.clips = Array.isArray(clips) ? clips : [];
    state.reviewFilter = "all";
    state.reviewSort = "score";
    state.videoLayout = videoLayout || "unknown";

    renderReviewCommandCenter();
    renderResultsGrid();
    document.getElementById("resultsSection").scrollIntoView({ behavior: "smooth" });
}

function reviewStatusOf(clip) {
    return clip.review_status || "pending";
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
    if (framing.mode === "reframe_9_16") {
        return { icon: "center_focus_strong", label: "Reframe 9:16 seguro", hint: framing.reason || "locutor estável detectado" };
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

    const avgScore = allClips.length ? allClips.reduce((a, c) => a + (c.viral_score || 0), 0) / allClips.length : 0;
    const highScoreCount = allClips.filter(c => c.viral_score >= 70).length;
    const sourceMap = { "gemini": "Gemini", "llm": "Ollama", "nlp": "NLP" };
    const source = allClips.length > 0 ? (sourceMap[allClips[0].source] || "NLP") : "NLP";
    summary.textContent = `${clips.length} de ${allClips.length} visíveis | Média: ${avgScore.toFixed(0)} | ${highScoreCount} com alto potencial | via ${source}`;

    const sorted = clips;

    sorted.forEach((clip, i) => {
        const originalIndex = state.clips.indexOf(clip);
        const rank = clip.rank || (i + 1);
        const scoreClass = clip.viral_score >= 70 ? "high" : clip.viral_score >= 40 ? "medium" : "low";
        const seo = clip.seo || {};
        const titles = seo.titles || [];
        const tags = seo.tags || [];
        const hashtags = seo.hashtags || [];
        const breakdown = clip.breakdown || {};
        const factors = clip.factors || {};
        const politicalType = clip.political_editorial_type || "";
        const topicSignature = String(clip.topic_signature || "");
        const diversityPenalty = Math.round(Number(clip.diversity_penalty || 0));
        const closureType = String(clip.closure_type || "");
        const closureLabels = { conclusion: "conclusão", closed_statement: "frase fechada", cliffhanger: "continuidade", open: "fecho a revisar" };
        const speakerLabel = String(clip.speaker || clip.speaker_role || "").trim();
        const speakerConfidence = Number(clip.speaker_confidence);
        const overlapSuspected = Boolean(clip.overlap_suspected || clip.speaker_overlap);
        const reviewFlags = clip.review_flags || {};
        const needsFactReview = Boolean(reviewFlags.needs_fact_review || reviewFlags.needsFactReview);
        const needsLegalReview = Boolean(reviewFlags.needs_legal_review || reviewFlags.needsLegalReview);
        const reviewStatus = reviewStatusOf(clip);
        const confidence = Math.round((clip.confidence || 0) * 100);
        const clipSource = clip.source || "nlp";
        const sourceLabels = { "gemini": "Gemini", "llm": "Ollama", "nlp": "NLP" };
        const sourceLabel = sourceLabels[clipSource] || "NLP";
        const sourceClass = clipSource === "gemini" ? "source-gemini" : (clipSource === "llm" ? "source-llm" : "source-nlp");
        const transcriptId = `transcript-${originalIndex}`;
        const layoutMeta = layoutMetaForClip(clip);
        const editorialBlock = clip.editorial_block || {};
        const blockTags = Array.isArray(editorialBlock.tags) ? editorialBlock.tags : [];
        const latestAdjustment = clip.latest_adjustment || {};
        const adjustmentState = clip.adjustment_state || (latestAdjustment.start != null ? "saved" : "");

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
                    <span class="score-value">${clip.viral_score || 0}</span>
                    <span class="score-label">/100</span>
                </div>
                ${clip.has_hook ? '<span class="hook-badge"><span class="material-icons-round" style="font-size:12px">flash_on</span> Gancho</span>' : ''}
                <span class="clip-source-badge ${sourceClass}">${sourceLabel}</span>
                ${politicalType ? `<span class="clip-source-badge source-editorial">${escapeHtml(politicalType)}</span>` : ''}
                <span class="review-state-chip ${reviewStatus}">${reviewStatus === "needs_review" ? "revisar contexto" : reviewStatus === "pending" ? "na fila" : reviewStatus}</span>
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
                ${(needsFactReview || needsLegalReview) ? `<div class="clip-review-risk ${needsLegalReview ? 'legal' : ''}"><span class="material-icons-round">${needsLegalReview ? 'gavel' : 'fact_check'}</span> ${needsLegalReview ? 'Revisão factual e jurídica' : 'Revisão factual recomendada'}</div>` : ''}
                ${topicSignature ? `<div class="clip-topic-chip" title="Sinal lexical usado somente para diversificar o portfólio">Tema: ${escapeHtml(topicSignature.replace(':', ' · ').replaceAll('-', ', '))}</div>` : ''}
                ${closureType ? `<div class="clip-closure-chip ${escapeHtml(closureType)}"><span class="material-icons-round">${closureType === 'conclusion' ? 'task_alt' : closureType === 'cliffhanger' ? 'hourglass_top' : 'subtitles'}</span> ${escapeHtml(closureLabels[closureType] || closureType)}</div>` : ''}
                ${(speakerLabel || overlapSuspected || Number.isFinite(speakerConfidence)) ? `<div class="clip-speaker-note ${overlapSuspected ? 'warning' : ''}"><span class="material-icons-round">${overlapSuspected ? 'record_voice_over' : 'person'}</span> ${speakerLabel ? `Locutor: ${escapeHtml(speakerLabel)}` : 'Locutor não identificado'}${Number.isFinite(speakerConfidence) ? ` · ${Math.round(Math.max(0, Math.min(1, speakerConfidence)) * 100)}%` : ''}${overlapSuspected ? ' · possível sobreposição' : ''}</div>` : ''}
                ${diversityPenalty >= 20 ? `<div class="clip-diversity-note"><span class="material-icons-round">filter_list</span> Similaridade com outro corte: ${diversityPenalty}%</div>` : ''}
                <div class="result-duration">
                    <span class="material-icons-round" style="font-size:14px">schedule</span>
                    ${formatTime(clip.start)} - ${formatTime(clip.end)} (${Number(clip.duration || 0).toFixed(1)}s)
                </div>
                ${(editorialBlock.thesis || editorialBlock.context_summary || blockTags.length) ? `<div class="editorial-block-dossier">
                    <div class="editorial-block-kicker"><span class="material-icons-round">inventory_2</span> Dossiê do bloco · ${escapeHtml(editorialBlock.state || "candidato")}</div>
                    ${editorialBlock.thesis ? `<strong>${escapeHtml(editorialBlock.thesis)}</strong>` : ''}
                    ${editorialBlock.context_summary ? `<p>${escapeHtml(editorialBlock.context_summary)}</p>` : ''}
                    ${editorialBlock.moment_reason ? `<small><b>Momento:</b> ${escapeHtml(editorialBlock.moment_reason)}</small>` : ''}
                    ${blockTags.length ? `<div class="editorial-block-tags">${blockTags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join('')}</div>` : ''}
                </div>` : ''}
                <button class="btn btn-sm btn-boundary-toggle" onclick="toggleBoundaryEditor(${originalIndex})"><span class="material-icons-round">tune</span> Ajustar entrada/saída</button>
                <div class="clip-boundary-editor" id="boundary-editor-${originalIndex}" hidden>
                    <div class="clip-boundary-fields">
                        <label>Entrada <input type="number" min="0" step="0.1" data-boundary-start="${originalIndex}" value="${Number(clip.start || 0).toFixed(1)}"></label>
                        <label>Saída <input type="number" min="0" step="0.1" data-boundary-end="${originalIndex}" value="${Number(clip.end || 0).toFixed(1)}"></label>
                        <button class="btn btn-sm btn-primary" onclick="previewClipBoundary(${originalIndex})"><span class="material-icons-round">preview</span> Pré-visualizar</button>
                        <button class="btn btn-sm btn-success" onclick="persistClipBoundary(${originalIndex})" ${clip.clip_id ? "" : "disabled"}><span class="material-icons-round">save</span> Salvar ajuste</button>
                    </div>
                    <small>Pré-visualizar só altera este card. Salvar ajuste registra a decisão fora do arquivo original; ainda não gera um novo MP4.</small>
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

                ${titles.length > 0 ? `
                <div class="result-seo">
                    <h5><span class="material-icons-round" style="font-size:14px">title</span> Titulos Sugeridos</h5>
                    ${titles.slice(0, 3).map(t => `<div class="seo-title" onclick="copyToClipboard(this.textContent)">${escapeHtml(t)}</div>`).join('')}
                </div>` : ''}

                ${tags.length > 0 ? `
                <div class="seo-tags">
                    ${tags.slice(0, 10).map(t => `<span class="seo-tag" onclick="copyToClipboard(this.textContent)">${escapeHtml(t)}</span>`).join('')}
                </div>` : ''}

                ${hashtags.length > 0 ? `
                <div class="seo-hashtags">
                    ${hashtags.slice(0, 8).map(h => `<span class="seo-hashtag">${escapeHtml(h)}</span>`).join('')}
                </div>` : ''}

                <div class="result-actions">
                    <button class="btn btn-sm btn-primary" onclick="downloadClip(${originalIndex})">
                        <span class="material-icons-round">download</span> Baixar
                    </button>
                    <button class="btn btn-sm" onclick="generateClipSeo(${originalIndex})">
                        <span class="material-icons-round">auto_awesome</span> SEO
                    </button>
                    <button class="btn btn-sm" onclick="generateClipThumb(${originalIndex})">
                        <span class="material-icons-round">image</span> Capa
                    </button>
                </div>
                <div class="review-actions">
                    <button class="btn btn-sm btn-success" onclick="setClipReview(${originalIndex}, 'approved')"><span class="material-icons-round">check_circle</span>Aprovar</button>
                    <button class="btn btn-sm btn-review-context" title="Não aprova nem rejeita; abre a transcrição completa e coloca o clip na fila de revisão." onclick="openContextReview(${originalIndex})"><span class="material-icons-round">visibility</span>Revisar contexto</button>
                    <button class="btn btn-sm btn-danger" onclick="setClipReview(${originalIndex}, 'rejected')"><span class="material-icons-round">close</span>Rejeitar</button>
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
    if (feedback) feedback.textContent = "Calculando limites seguros...";
    try {
        const response = await fetch("/api/clips/adjust", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                clip,
                start,
                end,
                duration: clip.source_duration || clip.video_duration || null,
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
        showToast("Limites atualizados na prévia do candidato.", "success");
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
    const adjustment = clip.latest_adjustment || {
        start: Number(clip.start),
        end: Number(clip.end),
        duration: Number(clip.duration),
        boundary_adjustment: { source: "manual" },
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
                note: "Ajuste temporal salvo na revisão do editor.",
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
        showToast("Ajuste salvo no histórico editorial; o MP4 original foi preservado.", "success");
    } catch (error) {
        if (feedback) feedback.textContent = error.message;
        showToast(error.message, "error");
    }
}

function transcriptSegmentsForClip(clip) {
    const allSegments = Array.isArray(state.manualTranscript?.segments) ? state.manualTranscript.segments : [];
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
    meta.textContent = `${clip.text || "Trecho sem transcrição"} · ${Number(clip.start || 0).toFixed(1)}s–${Number(clip.end || 0).toFixed(1)}s`;
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
    if (!clip) return;
    const previousStatus = reviewStatusOf(clip);
    clip.review_status = action;
    renderReviewCommandCenter();
    renderResultsGrid();
    try {
        if (clip.clip_id) {
            const response = await fetch(`/api/clips/${clip.clip_id}/feedback`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action }),
            });
            if (!response.ok) throw new Error("feedback rejected");
        }
        const messages = {
            approved: "Clip aprovado",
            rejected: "Clip rejeitado",
            needs_review: "Clip marcado para revisão de contexto",
        };
        state.lastReviewAction = { action, clip_id: clip.clip_id || null, at: new Date().toISOString() };
        renderReviewCommandCenter();
        renderResultsGrid();
        showToast(messages[action] || "Feedback salvo", action === "approved" ? "success" : "warning");
        loadEditorialLearning();
    } catch (error) {
        clip.review_status = previousStatus;
        renderReviewCommandCenter();
        renderResultsGrid();
        showToast("Não foi possível salvar o feedback", "error");
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
        badge.textContent = "IA Inteligente";
    } else {
        badge.classList.add("mode-nlp");
        badge.textContent = "NLP Basico";
    }
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
    try {
        const res = await fetch("/api/open_folder", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: folderPath }),
        });
        const data = await res.json();
        if (data.success) {
            showToast("Pasta aberta!", "success");
        } else {
            showToast(data.error || "Nao foi possivel abrir a pasta", "warning");
        }
    } catch (e) {
        showToast("Erro ao abrir pasta", "error");
    }
}

function displaySeoResult(seo) {
    // Update the last clip that was generating SEO
    addConsoleLog(`[SEO] Titulos: ${(seo.titles || []).join(' | ')}`, "success");
    addConsoleLog(`[SEO] Tags: ${(seo.tags || []).slice(0, 5).join(', ')}...`, "info");
}

function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
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
    const quality = transcription?.quality?.quality || transcription?.archive_metadata?.quality?.quality || "não validada semanticamente";
    const qualityScore = transcription?.quality?.score || transcription?.archive_metadata?.quality?.score;
    const suffix = Number.isFinite(Number(qualityScore)) ? ` Qualidade estrutural: ${qualityScore}/100 (${quality}).` : ` Qualidade: ${quality}.`;
    const status = document.getElementById("transcriptStatus");
    if (status) {
        status.textContent = `Transcrição carregada na aba: ${count} segmentos.${suffix}`;
        status.className = `source-status ${quality === "structurally_ok" ? "success" : "warning"}`;
    }
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
                duration: state.selectedVideo?.duration || state.selectedVideo?.duration_seconds || null,
                video_path: state.selectedVideo?.path || null,
            }),
        });
        const data = await parseJsonResponse(res, "Transcrição");
        if (!res.ok || !data.success) throw new Error(data.error || "Transcrição inválida");
        state.manualTranscript = data.transcription;
        showSourceStatus(`Transcrição ${data.transcription.format} pronta: ${data.transcription.segment_count} segmentos. Ela será usada no próximo corte sem Whisper.`, "success");
        showToast("Transcrição manual aplicada.", "success");
    } catch (error) {
        state.manualTranscript = null;
        showSourceStatus(error.message, "error");
        showToast("Não foi possível interpretar a transcrição.", "error");
    }
});

document.getElementById("btnGenerateTranscript")?.addEventListener("click", async () => {
    if (!requireVideo()) return;
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
        showSourceStatus("Transcrição iniciada; acompanhe o console abaixo.", "");
    } catch (error) {
        hideProgressBar();
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

function artworkFeedbackButton(format, value) {
    return `<button class="btn btn-sm artwork-feedback-button" type="button" data-artwork-format="${escapeHtml(format)}" data-artwork-feedback="${encodeURIComponent(value)}"><span class="material-icons-round">bookmark_add</span>Escolher</button>`;
}

function renderArtworkHeadline(suggestion, format) {
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
        <div class="artwork-suggestion-footer"><span>${Number(suggestion.character_count || headline.length)} caracteres · ${Number(suggestion.word_count || String(suggestion.headline || "").trim().split(/\s+/).filter(Boolean).length)} palavras</span><div>${artworkCopyButton(suggestion.headline || "", "Copiar headline")}${artworkFeedbackButton(format, suggestion.headline || "")}</div></div>
        ${suggestion.layout_hint ? `<p class="artwork-layout-hint"><span class="material-icons-round">grid_view</span>${escapeHtml(suggestion.layout_hint)}</p>` : ""}
    </article>`;
}

function renderHeadlineStudioResults(studio) {
    const container = document.getElementById("headlineStudioResults");
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
    const formatCards = ["vertical_916", "square_alfinetei"].map(format => {
        const config = formats[format] || {};
        const suggestions = Array.isArray(config.suggestions) ? config.suggestions : [];
        return `<section class="artwork-format-result ${format === recommended ? "recommended" : ""}">
            <div class="artwork-format-result-head"><div><span class="artwork-format-kicker">${format === recommended ? "FORMATO RECOMENDADO" : "ALTERNATIVA"}</span><h4>${escapeHtml(config.label || artworkFormatLabels[format])}</h4></div><span class="artwork-limit">${escapeHtml(config.description || "")}</span></div>
            <div class="artwork-suggestion-grid">${suggestions.map(item => renderArtworkHeadline(item, format)).join("") || '<p class="artwork-empty">Sem alternativa disponível.</p>'}</div>
        </section>`;
    }).join("");
    const tweets = Array.isArray(formats.fake_tweet?.suggestions) ? formats.fake_tweet.suggestions : [];
    const tweetCard = `<section class="artwork-format-result fake-tweet ${recommended === "fake_tweet" ? "recommended" : ""}">
        <div class="artwork-format-result-head"><div><span class="artwork-format-kicker">${recommended === "fake_tweet" ? "FORMATO RECOMENDADO" : "ALTERNATIVA"}</span><h4>Fake tweet — rascunho de publicação</h4></div><span class="artwork-limit">Revisar antes de atribuir ao perfil</span></div>
        <div class="fake-tweet-options">${tweets.map(item => `<article class="fake-tweet-card"><p>${escapeHtml(item.post_text || "")}</p><footer><span>${Number(item.character_count || 0)} caracteres</span><div>${artworkCopyButton(item.post_text || "", "Copiar texto")}${artworkFeedbackButton("fake_tweet", item.post_text || "")}</div></footer></article>`).join("") || '<p class="artwork-empty">Sem alternativa disponível.</p>'}</div>
    </section>`;
    container.innerHTML = `<div class="headline-studio-result-summary"><div><span class="artwork-format-kicker">LEITURA EDITORIAL</span><h4>${escapeHtml(artworkFormatLabels[recommended] || recommended)}</h4><p>${escapeHtml(studio.recommendation_reason || "")}</p></div><div class="artwork-analysis-metrics"><span>Tema: <strong>${escapeHtml(studio.topic || "geral")}</strong></span><span>Contexto: <strong>${Math.round(Number(studio.analysis?.context_completeness || 0))}/100</strong></span><span>Fonte: <strong>${studio.generation_source === "ai_refined" ? "IA + regras" : "regras editoriais"}</strong></span><span>Preferência: <strong>${escapeHtml(learningLabel)}</strong></span></div></div><div class="artwork-review-chips">${reviewChips || '<span class="artwork-review-chip safe"><span class="material-icons-round">verified</span>sem alerta lexical automático</span>'}</div><div class="artwork-format-results">${formatCards}${tweetCard}</div>`;
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
    if (!artworkText || !formatId) return;
    button.disabled = true;
    try {
        const studio = state.headlineStudio || {};
        const response = await fetch("/api/headline-studio/feedback", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                format_id: formatId,
                artwork_text: artworkText,
                action: "selected",
                topic: studio.topic || "",
                transcript_excerpt: studio.transcript?.excerpt || "",
                mini_context: studio.mini_context || "",
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

document.getElementById("btnSavePerformanceMetrics")?.addEventListener("click", savePerformanceMetrics);
document.getElementById("btnRefreshPerformanceMetrics")?.addEventListener("click", loadPerformanceMetrics);
["performanceMetricPlatform", "performanceMetricFormat", "performanceMetricWindow", "performanceMetricRegion"].forEach((id) => {
    document.getElementById(id)?.addEventListener("change", loadPerformanceMetrics);
});
loadPerformanceMetrics();

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

async function ensureSourceDirectory() {
    const existing = String(state.sourceDownloadDir || "").trim();
    if (existing) {
        const label = document.getElementById("sourceDestinationText");
        if (label) label.textContent = existing;
        return existing;
    }

    // Recover a path already rendered by settings or a previous selection so
    // importing a source never opens the native picker twice in one workflow.
    const label = document.getElementById("sourceDestinationText");
    const rendered = String(label?.textContent || "").trim();
    const placeholder = /^(escolha|selecion(e|ar)|pasta padrão|workspace\/uploads)/i;
    if (rendered && !placeholder.test(rendered)) {
        state.sourceDownloadDir = rendered;
        return rendered;
    }
    return chooseSourceDirectory();
}

document.getElementById("btnImportSource")?.addEventListener("click", async () => {
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
    const autoTranscribe = document.getElementById("sourceAutoTranscribe")?.checked !== false;
    state.sourceMaxHeight = maxHeight;
    showProgressBar();
    showSourceStatus("Download e transcrição iniciados; acompanhe o console abaixo.", "");
    try {
        const res = await fetch("/api/source/import", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                url,
                destination_dir: destination,
                max_height: maxHeight,
                auto_transcribe: autoTranscribe,
                transcription_source: document.getElementById("settingTranscriptionSource")?.value || "auto",
            }),
        });
        const data = await parseJsonResponse(res, "Importação da fonte");
        if (!res.ok || !data.success) throw new Error(data.error || "Não foi possível iniciar a importação");
        state.sourceUrl = url;
        addConsoleLog(`[Fonte] Download iniciado em ${destination}, limite de qualidade ${maxHeight}p.`, "info");
        if (autoTranscribe) addConsoleLog("[Fonte] A transcrição timestampada será gerada automaticamente após o download.", "info");
    } catch (error) {
        hideProgressBar();
        showSourceStatus(error.message, "error");
        showToast(error.message, "error");
    }
});

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
    if (s.whisper_model) document.getElementById("settingWhisperModel").value = s.whisper_model;
    if (s.cut_method) document.getElementById("settingCutMethod").value = s.cut_method;
    if (s.cut_duration) document.getElementById("settingCutDuration").value = s.cut_duration;
    if (s.render_preset) document.getElementById("settingRenderPreset").value = s.render_preset;
    if (s.editorial_profile) document.getElementById("settingEditorialProfile").value = s.editorial_profile;
    if (s.editorial_focus) document.getElementById("settingEditorialFocus").value = s.editorial_focus;
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
    if (geminiStatus) {
        const configured = Boolean(s.gemini_api_key_configured || s.gemini_api_key);
        geminiStatus.textContent = configured ? "Gemini configurado nesta instalação; o valor permanece oculto." : "Gemini sem chave nesta instalação; o app usará legenda pública ou fallback local.";
        geminiStatus.className = `ai-key-status ${configured ? "configured" : "missing"}`;
    }
    if (s.gemini_api_key) document.getElementById("settingGeminiKey").value = s.gemini_api_key;
    if (s.gemini_model) document.getElementById("settingGeminiModel").value = s.gemini_model;
    if (s.claude_api_key) document.getElementById("settingClaudeKey").value = s.claude_api_key;
    if (s.output_dir) {
        state.outputDir = s.output_dir;
        document.getElementById("outputDirText").textContent = s.output_dir || "workspace/exports (padrao)";
    }
    if (s.source_download_dir) {
        state.sourceDownloadDir = s.source_download_dir;
        const sourceLabel = document.getElementById("sourceDestinationText");
        if (sourceLabel) sourceLabel.textContent = s.source_download_dir;
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
            state.settings = { ...state.settings, ...settings, gemini_api_key_configured: Boolean(typedGeminiKey || state.settings.gemini_api_key_configured) };
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
            // Close any open modal
            document.querySelectorAll(".modal-overlay.active").forEach(m => m.classList.remove("active"));
            break;
    }
});

// ─── Init ───

document.addEventListener("DOMContentLoaded", () => {
    loadSettings();
    loadMediaFiles();
    loadTranscriptArchive();
    recoverActiveJobs();
    // Check Ollama status on load
    socket.emit("check_ollama");
});
