// ═══════════════════════════════════════════════════
// FURIA CLIPS - Frontend Application v2.0
// ═══════════════════════════════════════════════════

// O talho e a paleta são arquivos separados e precisam ler o vídeo selecionado,
// os cortes e a transcrição. `const` em escopo de arquivo não é alcançável de
// fora, e sem esta linha o ajuste de corte não acha corte nenhum — descobri
// medindo no navegador, porque nada disso dá erro: `window.state?.clips` volta
// indefinido em silêncio.
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
    outputFolder: "",
    activeJob: null,
    operationJobs: [],
    operationProjects: [],
    manualTranscript: null,
    sourceReading: null,
    manualTranscriptVideo: "",
    transcriptArchive: null,
    lastReviewAction: null,
    sourceUrl: "",
    sourceDownloadDir: "",
    sourceMaxHeight: 1080,
    sourceImportActive: false,
    sourceTranscriptionActive: false,
    sourceTranscriptionJobId: null,
    operationDashboardLoading: false,
    lastJobConsoleKey: "",
    repositorySync: null,
    repositorySyncBusy: false,
    campaignHubSnapshotStatus: null,
    campaignHubStatusTimer: null,
    faceTracking: true,
    pendingProcessMode: "smart",
    processingStart: "",
    processingEnd: "",
    processingScopeLabel: "Fonte inteira",
    previewToken: 0,
    consoleHistory: [],
    consoleEvents: [],
    lastDiagnostic: null,
    diagnosticLoading: false,
};
window.state = state;


// Sistema de Toasts (Notificações UI)
function showToast(title, message, type = "info", duration = 4000) {
    let container = document.getElementById("toastContainer");
    if (!container) {
        container = document.createElement("div");
        container.id = "toastContainer";
        container.className = "toast-container";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    
    let icon = "info";
    if (type === "success") icon = "check_circle";
    if (type === "error") icon = "error";
    if (type === "warning") icon = "warning";

    toast.innerHTML = `
        <span class="material-icons-round toast-icon">${icon}</span>
        <div class="toast-content">
            ${title ? `<span class="toast-title">${title}</span>` : ""}
            <span class="toast-message">${message}</span>
        </div>
    `;

    container.appendChild(toast);
    
    // Força o reflow para ativar a transição CSS
    void toast.offsetWidth;
    toast.classList.add("show");

    setTimeout(() => {
        toast.classList.add("hiding");
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 400);
    }, duration);
}

// ─── WebSocket Connection ───

const socket = io({
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 10000,
    timeout: 20000,
});
let socketRecoveryNotice = false;

// ─── Barra de execução ───
//
// O editor descreveu o sintoma assim: apertar o botão de uma função enquanto
// outra está rodando. O servidor já recusa a segunda — mas até aqui a interface
// não contava nada: nem o que estava em andamento, nem há quanto tempo, nem por
// que o segundo clique não fez efeito. Um clique ignorado sem explicação ensina
// que o programa está travado.

const RUN_STAGE_ORDER = ["source", "transcript", "context", "ranking", "render"];
const RUN_STAGE_LABELS = {
    source: "Fonte",
    transcript: "Transcrição",
    context: "Contexto",
    ranking: "Ranking",
    render: "Cortes",
};
const run = { active: false, title: "", startedAt: 0, timer: null, progress: 0, stage: "source", scope: "Fonte inteira", lastSignal: 0 };

// Quanto tempo de silêncio do servidor antes de destrancar a interface sozinha.
//
// O trinco existe para o operador não disparar duas operações em cima da mesma
// fonte, e ele é uma conveniência — quem de fato serializa o trabalho é a fila
// no servidor. Só que ele era absoluto: `run.active` só voltava a ser falso
// quando chegava uma atualização de job dizendo que acabou. Se essa atualização
// não chegasse — processo interrompido, socket caído, servidor reiniciado — todo
// cartão de ação ficava com `pointer-events: none` para sempre, e o único que
// não ficava era justamente o que estava rodando e por isso também não responde.
//
// O editor descreveu exatamente isso: "apesar de o botão de fazer tudo ser o
// único que pareceu clicável, nem ele funcionou", depois de ter parado um
// processo. Um trinco sem chave por fora é um travamento, não uma proteção.
const RUN_STALL_MS = 90000;

function inferRunStage(detail = "") {
    const value = String(detail || "").toLowerCase();
    if (/transcri|gemini|whisper|legenda pública/.test(value)) return "transcript";
    if (/contexto|análise de vídeo|analise de video|\[layout\]|detec[cç][aã]o de cena/.test(value)) return "context";
    if (/sele[cç][aã]o|ranqueamento|ranking|\[nlp\]/.test(value)) return "ranking";
    if (/cortando|corte completo|renderizando|clip.*gerado/.test(value)) return "render";
    return "source";
}

function renderRunBarState(stage = run.stage, progress = run.progress, level = "active") {
    const normalizedStage = RUN_STAGE_ORDER.includes(stage) ? stage : "source";
    const normalizedProgress = Math.max(0, Math.min(100, Number(progress) || 0));
    run.stage = normalizedStage;
    run.progress = normalizedProgress;
    const stageEl = document.getElementById("runBarStage");
    const fill = document.getElementById("runBarProgressFill");
    const track = document.getElementById("runBarProgressTrack");
    const progressText = document.getElementById("runBarProgressText");
    if (stageEl) stageEl.textContent = RUN_STAGE_LABELS[normalizedStage];
    if (fill) fill.style.width = `${normalizedProgress}%`;
    if (progressText) progressText.textContent = `${Math.round(normalizedProgress)}%`;
    if (track) track.setAttribute("aria-valuenow", String(Math.round(normalizedProgress)));
    document.querySelectorAll("[data-run-step]").forEach((step) => {
        const index = RUN_STAGE_ORDER.indexOf(step.dataset.runStep);
        const currentIndex = RUN_STAGE_ORDER.indexOf(normalizedStage);
        step.classList.toggle("complete", index < currentIndex);
        step.classList.toggle("active", index === currentIndex && level !== "error");
        step.classList.toggle("error", index === currentIndex && level === "error");
    });
}

function setRunBarScope(scope) {
    run.scope = String(scope || "Fonte inteira");
    const element = document.getElementById("runBarScope");
    if (element) element.textContent = run.scope;
}

function paintRun() {
    const bar = document.getElementById("runBar");
    if (!bar) return;
    bar.hidden = !run.active;
    document.querySelectorAll(".action-card").forEach((card) => {
        card.classList.toggle("is-locked", run.active && card.dataset.action !== run.action);
        card.classList.toggle("is-running", run.active && card.dataset.action === run.action);
    });
    if (!run.active) return;
    // O servidor emudeceu: solta o trinco antes que ele vire travamento.
    if (run.lastSignal && Date.now() - run.lastSignal > RUN_STALL_MS) {
        const parado = run.title || "A operação";
        endRun();
        showToast(`${parado} parou de responder; as ações foram liberadas.`, "warning");
        addConsoleLog(
            `[Sistema] Sem notícia do servidor há ${Math.round(RUN_STALL_MS / 1000)}s. ` +
            "As ações foram destrancadas — se a operação ainda estiver rodando, ela aparece no painel de operação.",
            "warning",
        );
        return;
    }
    document.getElementById("runBarTitle").textContent = run.title || "Processando";
    setRunBarScope(run.scope);
    renderRunBarState(run.stage, run.progress);
    const seconds = Math.max(0, Math.round((Date.now() - run.startedAt) / 1000));
    document.getElementById("runBarClock").textContent =
        `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

function beginRun(title, action = "", detail = "Preparando…") {
    run.active = true;
    run.title = title;
    run.action = action;
    run.startedAt = Date.now();
    run.progress = 0;
    run.stage = inferRunStage(detail);
    run.lastSignal = Date.now();
    setRunBarScope(state.processingScopeLabel || "Fonte inteira");
    const line = document.getElementById("runBarDetail");
    if (line) line.textContent = detail;
    window.clearInterval(run.timer);
    run.timer = window.setInterval(paintRun, 1000);
    paintRun();
}

function describeRun(detail) {
    if (!run.active) return;
    run.lastSignal = Date.now();
    const line = document.getElementById("runBarDetail");
    // A mensagem de progresso já vem carimbada com versão e etapa; o que
    // interessa na barra é a última coisa dita, sem o carimbo.
    if (line && detail) line.textContent = String(detail).replace(/^\[[^\]]*\]\s*/, "").slice(0, 140);
    renderRunBarState(inferRunStage(detail), run.progress);
}

function endRun() {
    run.active = false;
    run.action = "";
    run.lastSignal = 0;
    window.clearInterval(run.timer);
    run.timer = null;
    // O botão de cancelar se desabilitava ao pedir a parada e nunca voltava.
    // Se o pedido não surtisse efeito, não havia como pedir de novo.
    const cancelar = document.getElementById("runBarCancel");
    if (cancelar) cancelar.disabled = false;
    paintRun();
}

document.getElementById("runBarCancel")?.addEventListener("click", async (event) => {
    const button = event.currentTarget;
    const id = state.activeJob?.id;
    if (button) button.disabled = true;
    describeRun("Solicitando parada segura…");
    try {
        const response = id
            ? await fetch(`/api/jobs/${id}/cancel`, { method: "POST" })
            : await fetch("/api/process/cancel", { method: "POST" });
        const data = await parseJsonResponse(response, "Cancelamento");
        if (!response.ok || data.error) {
            throw new Error(data.error || "Não foi possível solicitar o cancelamento");
        }
        describeRun("Cancelamento aceito; aguardando a etapa segura terminar…");
    } catch (error) {
        if (button) button.disabled = false;
        describeRun(`Falha ao solicitar cancelamento: ${error.message}`);
        showToast(error.message, "error");
        addConsoleLog(`[Erro] Falha ao solicitar cancelamento: ${error.message}`, "error");
    }
});

// ─── Voz de referência ───
//
// As rotas de cadastro existiam desde a 4.8 e não havia botão nenhum para
// alcançá-las — o mesmo padrão de módulo pronto e desligado que este projeto
// repete. O editor perguntou como cadastrar e a resposta honesta era "não dá".

async function carregarVoz() {
    const painel = document.getElementById("voiceStatus");
    if (!painel) return;
    try {
        const resposta = await fetch("/api/voz/status", { cache: "no-store" });
        const dados = await parseJsonResponse(resposta, "Voz de referência");
        const ponto = painel.querySelector(".status-dot");
        const texto = painel.querySelector("span:last-child");
        if (ponto) ponto.className = `status-dot ${dados.cadastrada ? "online" : "offline"}`;
        if (texto) {
            texto.textContent = dados.cadastrada
                ? `Voz cadastrada · ${dados.quadros} quadros de fala`
                : "Nenhuma voz cadastrada";
        }
    } catch {
        const texto = painel.querySelector("span:last-child");
        if (texto) texto.textContent = "Não foi possível ler o cadastro";
    }
}

document.getElementById("btnEnrollVoice")?.addEventListener("click", () => {
    document.getElementById("voiceFileInput")?.click();
});

document.getElementById("voiceFileInput")?.addEventListener("change", async (evento) => {
    const arquivo = evento.target.files?.[0];
    if (!arquivo) return;
    const botao = document.getElementById("btnEnrollVoice");
    trabalhando(botao, true);
    try {
        const corpo = new FormData();
        corpo.append("file", arquivo);
        const resposta = await fetch("/api/voz/cadastrar", { method: "POST", body: corpo });
        const dados = await parseJsonResponse(resposta, "Cadastro de voz");
        if (!resposta.ok || !dados.success) throw new Error(dados.error || "Não foi possível cadastrar a voz.");
        showToast(`Voz cadastrada: ${dados.frames} quadros de fala.`, "success");
        addConsoleLog(`[Voz] Amostra cadastrada com ${dados.frames} quadros; o Furia passa a checar o locutor de cada corte.`, "success");
        carregarVoz();
    } catch (erro) {
        showToast(erro.message, "error");
        addConsoleLog(`[Voz] Cadastro não concluído: ${erro.message}`, "warning");
    } finally {
        trabalhando(botao, false);
        evento.target.value = "";
    }
});

// ─── Aparência ───
//
// O som tinha função para tocar e nenhum jeito de ser ligado; o cursor apontava
// para classes que não existiam. Duas capacidades escritas e inalcançáveis, no
// mesmo commit. Agora as duas têm controle.

const CURSOR_CHAVE = "furia.cursor";

function aplicarCursor() {
    const modo = window.localStorage?.getItem(CURSOR_CHAVE) || "drag";
    document.body.classList.toggle("furia-cursor-always", modo === "always");
    document.body.classList.toggle("furia-cursor-off", modo === "off");
    const seletor = document.getElementById("settingCursor");
    if (seletor) seletor.value = modo;
}

document.getElementById("settingCursor")?.addEventListener("change", (evento) => {
    window.localStorage?.setItem(CURSOR_CHAVE, evento.target.value);
    aplicarCursor();
});

function aplicarSom() {
    const caixa = document.getElementById("settingSound");
    if (caixa) caixa.checked = somLigado();
}

document.getElementById("settingSound")?.addEventListener("change", (evento) => {
    window.localStorage?.setItem(SOM_CHAVE, evento.target.checked ? "1" : "0");
    if (evento.target.checked) tocarFim();
});

let toastContainer = null;

// ─── Acabamento de interação ───
//
// O cursor de onça é contextual de propósito: ligado o tempo todo ele atrasa em
// relação ao ponteiro do sistema, some sobre campo de texto e cansa numa jornada
// de horas. Ligado só enquanto o editor arrasta uma borda, vira assinatura.

// Só o que de fato existe e se arrasta hoje. As três classes anteriores —
// timeline-handle, clip-boundary-handle e companhia — não estavam em elemento
// nenhum: o cursor não tinha como aparecer nem uma vez.
const DRAG_HANDLES = ".reading-timeline, .reading-timeline-unit, .setting-range, .media-drop-zone";

document.addEventListener("pointerdown", (event) => {
    if (event.target.closest?.(DRAG_HANDLES)) document.body.classList.add("furia-dragging");
});
["pointerup", "pointercancel", "blur"].forEach((nome) => {
    window.addEventListener(nome, () => document.body.classList.remove("furia-dragging"));
});

// Um botão que disparou trabalho não pode continuar parecendo disponível. Isto
// cobre os 45 botões que não se desabilitavam sozinhos, sem ter de mexer em cada
// um deles.
function trabalhando(botao, ligado = true) {
    if (!botao) return;
    botao.classList.toggle("is-working", ligado);
    botao.disabled = ligado;
}

// A função 'avisar' foi substituída por showToast.

// Som desligado por padrão, um toque curto ao fim de processo longo, e um jeito
// de calar. Ferramenta que apita sem permissão é desinstalada.
const SOM_CHAVE = "furia.som";
function somLigado() { return window.localStorage?.getItem(SOM_CHAVE) === "1"; }
function tocarFim() {
    if (!somLigado()) return;
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const ganho = ctx.createGain();
        osc.frequency.setValueAtTime(660, ctx.currentTime);
        osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.12);
        ganho.gain.setValueAtTime(0.0001, ctx.currentTime);
        ganho.gain.exponentialRampToValueAtTime(0.06, ctx.currentTime + 0.02);
        ganho.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.3);
        osc.connect(ganho).connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.32);
        osc.onended = () => ctx.close();
    } catch { /* som é conforto, nunca requisito */ }
}

socket.on("connect", () => {
    const recovered = socketRecoveryNotice;
    state.connected = true;
    socketRecoveryNotice = false;
    addConsoleLog(
        recovered ? "[Sistema] Conexão restaurada; os jobs persistidos continuam disponíveis." : "[Sistema] Conectado ao servidor.",
        "success",
    );
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

socket.on("progress", (data) => {
    const time = data.time || new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    const version = data.program_version && !String(data.message || "").includes("[Versão")
        ? `[Versão ${data.program_version}${data.program_revision ? ` · ${data.program_revision}` : ""}] `
        : "";
    const displayMessage = `[${time}] ${version}${data.message || "Progresso recebido"}`;
    addConsoleLog(displayMessage, data.level, {
        ...data,
        event_name: data.event_name || "progress.message",
        message: displayMessage,
        details: data.details || {},
    });
    describeRun(data.message);
    showProgressBar();
});

socket.on("status", (data) => {
    handleStatusUpdate(data);
});

socket.on("job_update", (job) => {
    handleJobUpdate(job);
});

socket.on("source_transcription_complete", (data) => {
    handleSourceTranscriptionComplete(data);
});

socket.on("editorial_context_complete", (data) => {
    state.editorialContext = data?.context || null;
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

function setSourceTranscriptionButtons(active) {
    state.sourceTranscriptionActive = Boolean(active);
    [
        document.getElementById("btnDownloadSource"),
        document.getElementById("btnTranscribeSource"),
        document.getElementById("btnDownloadTranscribeSource"),
    ].filter(Boolean).forEach((button) => {
        button.disabled = Boolean(active);
        button.classList.toggle("loading", Boolean(active));
    });
}

function handleSourceTranscriptionComplete(data) {
    setSourceTranscriptionButtons(false);
    state.sourceTranscriptionJobId = null;
    hideProgressBar();
    const transcription = data?.transcription;
    if (transcription) {
        state.manualTranscript = transcription;
        state.manualTranscriptVideo = data?.source?.path || data?.source?.absolute_path || "";
        state.transcriptArchive = data?.transcription_archive || transcription.archive || null;
        hydrateTranscriptEditor(transcription, state.transcriptArchive);
    }
    const count = Number(transcription?.segment_count || transcription?.segments?.length || 0);
    const coverage = data?.coverage?.status || transcription?.coverage?.status || "não verificada";
    showSourceStatus(
        `Transcrição pronta sem cortes: ${count} segmentos · cobertura ${coverage}. Arquivo persistente salvo.`,
        coverage === "mismatch_suspected" ? "warning" : "success",
    );
    addConsoleLog(`[Transcrição por URL] ${count} segmentos prontos; nenhum corte foi gerado. Cobertura: ${coverage}.`, "success");
    showToast("Transcrição por URL concluída sem gerar cortes.", "success");
}

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
            showToast("Transcrição concluída.", "success");
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
        case "cut_complete": {
            hideProgressBar();
            const completedClips = Array.isArray(data.data.clips) ? data.data.clips : [];
            updateWorkspaceWorkflow("review", completedClips.length ? "Revisão pronta" : "Revisão requer atenção");
            state.selectionSource = data.data.selection_source || "nlp";
            state.candidateDiagnostics = data.data.candidate_diagnostics || state.candidateDiagnostics || {};
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

function rememberDiagnosticEvent(event = {}) {
    const normalized = {
        event_id: String(event.event_id || `ui-${Date.now()}-${Math.random().toString(16).slice(2)}`),
        job_id: event.job_id || state.activeJob?.id || null,
        event_name: String(event.event_name || "ui.console"),
        level: String(event.level || "info"),
        stage: event.stage || null,
        message: String(event.message ?? ""),
        details: event.details && typeof event.details === "object" ? event.details : {},
        created_at: event.created_at || event.recorded_at || new Date().toISOString(),
        sequence: Number.isFinite(Number(event.sequence)) ? Number(event.sequence) : null,
    };
    if (!state.consoleEvents.some((item) => item.event_id === normalized.event_id)) {
        state.consoleEvents.push(normalized);
        if (state.consoleEvents.length > 5000) {
            state.consoleEvents.splice(0, state.consoleEvents.length - 5000);
        }
    }
    return normalized;
}

function addConsoleLog(message, level = "info", event = null) {
    const console_el = document.getElementById("consoleOutput");
    const text = String(message ?? "");
    const recordedAt = new Date().toISOString();
    state.consoleHistory.push({ text, level, recorded_at: recordedAt });
    rememberDiagnosticEvent({
        ...(event || {}),
        level,
        message: text,
        recorded_at: recordedAt,
    });
    // A very early browser error can happen before the template mounts the
    // console. Keep the structured breadcrumb and avoid a second exception.
    if (!console_el) return;
    // Whether the reader was already at the bottom before this line arrived. If
    // they scrolled up to read something, yanking the panel back down loses their
    // place; if they were at the bottom, they want to keep following.
    const followingTail = console_el.scrollHeight - console_el.scrollTop - console_el.clientHeight < 40;

    const line = document.createElement("div");
    line.className = `console-line ${level}`;
    line.textContent = text;
    console_el.appendChild(line);
    updateProcessingJourney(text, level);

    // The visible panel stays bounded for performance; copying uses the full session history.
    while (console_el.children.length > 200) {
        console_el.removeChild(console_el.firstChild);
    }

    // Scrolling only after the trim, and on the next frame, so the height the
    // browser reports already accounts for the new line and for any wrapping it
    // caused. Doing it inline left the panel one line short of the bottom, which
    // is why the newest message was almost never the one on screen.
    if (followingTail) {
        requestAnimationFrame(() => {
            console_el.scrollTop = console_el.scrollHeight;
        });
    }
    if (state.consoleHistory.length > 5000) {
        state.consoleHistory.splice(0, state.consoleHistory.length - 5000);
    }
}

async function loadJobDiagnostic(jobId, { silent = false } = {}) {
    if (!jobId) return null;
    state.diagnosticLoading = true;
    try {
        const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/diagnostics?limit=1000`, { cache: "no-store" });
        const payload = await parseJsonResponse(response, "Diagnóstico do job");
        if (!response.ok || payload.error) throw new Error(payload.error || "Não foi possível carregar o diagnóstico");
        state.lastDiagnostic = payload;
        (payload.events || []).forEach((event) => rememberDiagnosticEvent(event));
        return payload;
    } catch (error) {
        if (!silent) addConsoleLog(`[Diagnóstico] Não foi possível carregar o histórico persistido: ${error.message}`, "warning", { event_name: "diagnostic.load_failed" });
        return null;
    } finally {
        state.diagnosticLoading = false;
    }
}

async function copyFullConsoleLog() {
    const jobId = state.activeJob?.id || state.lastDiagnostic?.job?.id || null;
    let diagnostic = state.lastDiagnostic?.job?.id === jobId ? state.lastDiagnostic : null;
    if (jobId && !diagnostic) diagnostic = await loadJobDiagnostic(jobId, { silent: true });
    const lines = state.consoleHistory.map(entry => entry.text).filter(Boolean);
    if (!lines.length && !diagnostic) {
        showToast("Ainda não há linhas para copiar.", "warning");
        return;
    }
    const report = {
        schema_version: "ui-diagnostic-v1",
        generated_at: new Date().toISOString(),
        program_version: state.settings?.program_version || null,
        program_revision: state.settings?.program_revision || null,
        active_job_id: jobId,
        console_line_count: lines.length,
        console_lines: lines,
        structured_events: state.consoleEvents.slice(-5000),
        persisted_job_diagnostic: diagnostic || null,
        privacy_note: "Este resumo não inclui chaves, cookies, transcrição integral ou mídia.",
    };
    const value = JSON.stringify(report, null, 2);
    try {
        if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(value);
        } else {
            const helper = document.createElement("textarea");
            helper.value = value;
            helper.setAttribute("readonly", "true");
            helper.style.position = "fixed";
            helper.style.opacity = "0";
            document.body.appendChild(helper);
            helper.select();
            document.execCommand("copy");
            helper.remove();
        }
        const eventCount = (diagnostic?.events || []).length || state.consoleEvents.length;
        addConsoleLog(`[Sistema] Diagnóstico completo copiado (${lines.length} linhas, ${eventCount} eventos).`, "success", { event_name: "diagnostic.copied", details: { line_count: lines.length, event_count: eventCount } });
        showToast(`Diagnóstico copiado (${lines.length} linhas, ${eventCount} eventos).`, "success");
    } catch (error) {
        showToast(`Não foi possível copiar o diagnóstico: ${error.message}`, "error");
    }
}

document.getElementById("btnCopyConsoleLog")?.addEventListener("click", copyFullConsoleLog);

window.addEventListener("error", (event) => {
    const message = event?.error?.message || event?.message || "Erro JavaScript não identificado";
    addConsoleLog(`[Frontend] ${message} (${event?.filename || "script"}:${event?.lineno || "?"})`, "error", {
        event_name: "frontend.error",
        details: { filename: event?.filename || null, line: event?.lineno || null, column: event?.colno || null },
    });
});
window.addEventListener("unhandledrejection", (event) => {
    const reason = event?.reason?.message || String(event?.reason || "Promise rejeitada sem motivo");
    addConsoleLog(`[Frontend] Promise rejeitada: ${reason}`, "error", { event_name: "frontend.unhandled_rejection" });
});

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

// ─── Etapas da tela ───
//
// Eram doze seções empilhadas numa página só: para chegar nos resultados o
// editor rolava por biblioteca, fonte, leitura, blocos, prévia, refinamento,
// estúdio, métricas e ações. A barra de etapas do topo já existia e era
// enfeite — indicava progresso e não levava a lugar nenhum.
//
// Agora ela navega. As mesmas seções, agrupadas pelo momento em que servem.

const STAGE_SECTIONS = {
    source: ["mediaLibrarySection", "sourceSection"],
    analysis: ["sourceReadingSection", "editorialBlocksSection", "contextSection", "actionsSection"],
    review: ["resultsSection", "headlineStudioSection"],
    learning: ["operationDashboard", "performanceMetricsSection"],
};
// O console fica fora do agrupamento: é o registro do que está acontecendo e
// precisa estar alcançável de qualquer etapa.
const STAGE_ORDER = ["source", "analysis", "review", "learning"];

let currentStage = "source";
let stageChosenAt = 0;

function showStage(stage, { manual = false } = {}) {
    if (!STAGE_SECTIONS[stage]) return;
    currentStage = stage;
    if (manual) stageChosenAt = Date.now();

    // A barra de ambientes assumiu a navegação, e duas navegações na mesma tela
    // brigam: esta escondia `resultsSection` enquanto a outra mostrava o
    // ambiente Auditoria, e o cartão do corte nascia com zero pixel — sem erro
    // nenhum, como sempre acontece quando o culpado é `display:none`.
    //
    // A função continua existindo porque várias partes do código a chamam para
    // dizer em que momento estamos; ela só não mexe mais em visibilidade.
    document.querySelectorAll(".stage-off").forEach((secao) => secao.classList.remove("stage-off"));

    document.querySelectorAll(".workflow-step").forEach((passo, indice) => {
        const nome = STAGE_ORDER[indice];
        passo.classList.toggle("current", nome === stage);
        passo.classList.toggle("active", nome === stage);
        passo.setAttribute("aria-current", nome === stage ? "step" : "false");
    });
}

document.querySelectorAll(".workflow-step").forEach((passo, indice) => {
    passo.setAttribute("role", "button");
    passo.setAttribute("tabindex", "0");
    const abrir = () => showStage(STAGE_ORDER[indice], { manual: true });
    passo.addEventListener("click", abrir);
    passo.addEventListener("keydown", (evento) => {
        if (evento.key === "Enter" || evento.key === " ") { evento.preventDefault(); abrir(); }
    });
});

// O pipeline avança sozinho, mas não arranca o editor da tela que ele acabou de
// escolher. Puxar alguém para outra aba no meio de uma leitura é pior que
// deixá-lo trocar de aba sozinho.
function avancarEtapa(stage) {
    if (Date.now() - stageChosenAt < 45000 && stage !== currentStage) {
        const passo = document.querySelectorAll(".workflow-step")[STAGE_ORDER.indexOf(stage)];
        passo?.classList.add("has-news");
        return;
    }
    showStage(stage);
}

function updateWorkspaceWorkflow(stage = "source", stateLabel = "") {
    const order = ["source", "analysis", "review", "learning"];
    const index = Math.max(0, order.indexOf(stage));
    document.querySelectorAll(".workflow-step").forEach((step, stepIndex) => {
        // `active` pertence à navegação; aqui só o progresso.
        step.classList.toggle("complete", stepIndex < index);
        if (stepIndex === index) step.classList.remove("has-news");
    });
    avancarEtapa(order[index] || "source");
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
document.getElementById("btnImportCampaignHubMemory")?.addEventListener("click", () => document.getElementById("campaignHubMemoryFileInput")?.click());
document.getElementById("campaignHubMemoryFileInput")?.addEventListener("change", (event) => importCampaignHubMemory(event.target.files?.[0]));
document.getElementById("btnRefreshTranscriptArchive")?.addEventListener("click", loadTranscriptArchive);
document.getElementById("btnEditorialRestore")?.addEventListener("click", () => document.getElementById("editorialRestoreInput")?.click());
document.getElementById("editorialRestoreInput")?.addEventListener("change", restoreEditorialBackup);
document.getElementById("btnRepositoryPushFeedback")?.addEventListener("click", () => runRepositorySync("push_feedback"));
document.getElementById("btnRepositoryRestoreFeedback")?.addEventListener("click", () => runRepositorySync("restore_feedback"));

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
            const usable = Boolean(item.usable);
            return `<span class="editorial-learning-coverage-chip ${usable ? "usable" : "insufficient"}" title="${usable ? "Amostra suficiente para este sinal" : "Ainda sem amostra suficiente para calibrar"}"><b>${escapeHtml(label)}</b> ${total} ${usable ? "utilizável" : "insuficiente"}</span>`;
        });
        coverageTarget.innerHTML = `<span class="editorial-learning-coverage-label">Cobertura dos motivos:</span>${coverageEntries.join("")}`;
    }
    panel.classList.toggle("is-active", Boolean(calibration.eligible));
    if (calibration.eligible) {
        title.textContent = "Calibração editorial ativa";
        const durationNote = durationSignal.usable && Math.abs(durationGap) >= 0.1
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
    const memoryCard = document.getElementById("campaignHubMemoryCard");
    const memoryText = document.getElementById("campaignHubMemoryText");
    const memoryMeta = document.getElementById("campaignHubMemoryMeta");
    const memoryBadge = document.getElementById("campaignHubMemoryBadge");
    if (!element && !memoryCard) return;
    const dot = element?.querySelector(".status-dot");
    const label = element?.querySelector("span:last-child");
    const previous = state.campaignHubSnapshotStatus;
    state.campaignHubSnapshotStatus = payload || null;
    const memory = payload?.memory || payload || {};
    const available = Boolean(memory.available || payload?.memory_available);
    const status = String(memory.status || payload?.status || "missing");
    const accounts = memory.accounts || payload?.accounts || {};
    const accountCount = Object.keys(accounts).length;
    const recordCounts = memory.record_counts || payload?.record_counts || {};
    const blockCount = Number(recordCounts.blocks || 0);
    const highlightCount = Number(recordCounts.highlights || 0);
    const changed = Boolean(previous?.modified_at && payload?.modified_at && previous.modified_at !== payload.modified_at);
    const level = !available ? (status === "invalid" ? "warning" : "offline") : (changed ? "warning" : "online");
    if (dot) dot.className = `status-dot ${level}`;
    if (label) {
        label.textContent = !available
            ? (memory.message || payload?.message || "Sem memória editorial local")
            : changed
                ? `Nova memória detectada · ${accountCount} perfil(is) · será usada no próximo corte`
                : `Memória local pronta · ${accountCount} perfil(is) · somente leitura`;
    }
    if (element) element.title = available
        ? `${memory.version || payload?.version || "Memória local"}${memory.last_sync_at ? ` · sincronizada em ${new Date(memory.last_sync_at).toLocaleString("pt-BR")}` : ""}.`
        : "O Furia continua funcionando offline, mas não recebeu memória editorial válida.";
    if (memoryCard) {
        memoryCard.dataset.level = level;
        if (!available) {
            if (memoryText) memoryText.textContent = memory.message || payload?.message || "Nenhum export autorizado instalado. O Furia continua funcionando com sinais locais básicos.";
            if (memoryBadge) memoryBadge.textContent = status === "invalid" ? "REVISAR" : "OFFLINE";
            if (memoryMeta) memoryMeta.textContent = "Atualize a memória quando tiver um export autorizado do Campaign Hub.";
        } else {
            if (memoryText) memoryText.textContent = changed
                ? "Há uma versão nova da memória local; ela será usada no próximo processamento."
                : "O próximo job usa esta memória offline para contexto, benchmark e prior fraco.";
            if (memoryBadge) memoryBadge.textContent = "PRONTA";
            if (memoryMeta) memoryMeta.textContent = `${accountCount} perfil(is) · ${blockCount} bloco(s) · ${highlightCount} destaque(s)${memory.last_sync_at ? ` · ${new Date(memory.last_sync_at).toLocaleDateString("pt-BR")}` : ""}`;
        }
    }
}

async function importCampaignHubMemory(file) {
    if (!file) return;
    const button = document.getElementById("btnImportCampaignHubMemory");
    if (button) button.disabled = true;
    const formData = new FormData();
    formData.append("snapshot", file);
    formData.append("merge", "true");
    try {
        const response = await fetch("/api/campaign-hub/memory/import", { method: "POST", body: formData });
        const payload = await parseJsonResponse(response, "Memória do Campaign Hub");
        if (!response.ok || !payload.success) throw new Error(payload.error || "Não foi possível atualizar a memória local.");
        showToast(`Memória atualizada: ${Number(payload.record_counts?.blocks || 0)} bloco(s) local(is).`, "success");
        addConsoleLog(`[Campaign Hub] Memória local mesclada; ${Number(payload.merge_stats?.records_added || 0)} registro(s) novo(s).`, "info");
        await loadCampaignHubLocalStatus();
    } catch (error) {
        showToast(error.message || "Não foi possível atualizar a memória local.", "error");
        addConsoleLog(`[Campaign Hub] Atualização não concluída: ${error.message}`, "warning");
    } finally {
        if (button) button.disabled = false;
        const input = document.getElementById("campaignHubMemoryFileInput");
        if (input) input.value = "";
    }
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

// De onde vieram os blocos. Só o Acervo passou por revisão humana; a leitura do
// Furia é uma aproximação honesta e o painel diz isso em voz alta, porque muda
// o quanto o editor deve confiar nas bordas.
const BLOCK_ORIGINS = {
    acervo: "blocos revisados do Acervo",
    campaign_hub: "blocos da memória do Campaign Hub",
    furia_entrevista: "leitura do Furia · turnos da entrevista",
    furia_temas: "leitura do Furia · blocos temáticos",
};

function renderEditorialBlocks(payload) {
    const list = document.getElementById("editorialBlocksList");
    const status = document.getElementById("editorialBlocksStatus");
    if (!list) return;
    const blocks = Array.isArray(payload?.blocks) ? payload.blocks : [];
    const reviewed = payload?.reviewed === true;
    if (status) {
        const dot = status.querySelector(".status-dot");
        if (dot) dot.className = `status-dot ${payload?.available ? (reviewed ? "online" : "warn") : "offline"}`;
        const originLabel = BLOCK_ORIGINS[payload?.origin] || "";
        status.lastChild.textContent = payload?.available
            ? ` ${payload.total || 0} bloco(s)${originLabel ? ` · ${originLabel}` : ""}`
            : " Nenhum bloco para esta fonte";
    }
    if (!payload?.available) {
        list.innerHTML = `<div class="editorial-blocks-empty"><span class="material-icons-round">cloud_off</span><br>${escapeHtml(payload?.message || "Insira um link do YouTube ou carregue um vídeo local para listar os blocos.")}</div>`;
        return;
    }
    if (!blocks.length) {
        list.innerHTML = `<div class="editorial-blocks-empty"><span class="material-icons-round">search_off</span><br>Nenhum bloco corresponde à busca atual.</div>`;
        return;
    }
    list.innerHTML = blocks.map((block) => {
        const riskCount = (block.risk_flags || []).length + (block.gate_warnings || []).length;
        const renanLabel = block.renan_speaking === true ? "fala do Renan" : block.renan_speaking === false ? "fala de terceiro" : "locutor não confirmado";
        const renanClass = block.renan_speaking === true ? "good" : block.renan_speaking === false ? "warn" : "";
        const sourceTitle = reviewed && block.source?.title ? ` · ${escapeHtml(block.source.title)}` : "";
        const highlights = Array.isArray(block.highlights) ? block.highlights.slice(0, 6) : [];
        const highlightsMarkup = highlights.length ? `<div class="editorial-block-highlights"><div class="editorial-block-highlights-title"><span class="material-icons-round">auto_awesome</span> Destaques de referência</div>${highlights.map((highlight) => `<div class="editorial-block-highlight"><div><b>${escapeHtml(formatTime(Number(highlight.start_s || 0)))}–${escapeHtml(formatTime(Number(highlight.end_s || 0)))}</b><span>${escapeHtml(highlight.text || "Destaque sem transcrição")}</span></div><button class="btn btn-sm btn-outline editorial-block-highlight-export" type="button" data-highlight-export="${escapeHtml(block.id)}" data-highlight-id="${escapeHtml(highlight.id)}" title="Exporta somente este destaque da fonte local"><span class="material-icons-round">download</span></button></div>`).join("")}</div>` : "";
        return `<article class="editorial-block-card" data-block-id="${escapeHtml(block.id)}" data-block-start="${Number(block.start || 0)}">
            <div class="editorial-block-time"><strong>${formatTime(Number(block.start || 0))}</strong>${formatTime(Number(block.end || 0))}<span>${Number(block.duration || 0).toFixed(0)}s</span></div>
            <div class="editorial-block-content">
                <h4>${escapeHtml(block.title || block.label || "Bloco editorial")}</h4>
                <p class="${block.summary_is_verbatim ? "editorial-block-verbatim" : ""}">${block.summary_is_verbatim ? "<b>Trecho falado:</b> " : ""}${escapeHtml(block.summary || "Resumo não disponível.")}</p>
                ${block.trigger_question ? `<div class="editorial-block-question"><b>Pergunta:</b> ${escapeHtml(block.trigger_question)}</div>` : ""}
                <div class="editorial-block-meta">
                    <span class="editorial-block-chip ${renanClass}">${escapeHtml(renanLabel)}</span>
                    <span class="editorial-block-chip">${Number(block.highlight_count || 0)} destaque(s)</span>
                    ${block.self_contained_rank ? `<span class="editorial-block-chip good">contexto ${escapeHtml(block.self_contained_rank)}º percentil</span>` : ""}
                    ${riskCount ? `<span class="editorial-block-chip warn">${riskCount} risco(s)</span>` : ""}
                    <span class="editorial-block-chip">${escapeHtml(block.trust_tier || "tier não informado")}${sourceTitle}</span>
                </div>
                ${highlightsMarkup}
            </div>
            <div class="editorial-block-action-stack">
                <button class="btn btn-sm btn-outline editorial-block-action" type="button" data-block-select="${escapeHtml(block.id)}"><span class="material-icons-round">playlist_add</span> Selecionar</button>
                <button class="btn btn-sm btn-outline editorial-block-action" type="button" data-block-export="${escapeHtml(block.id)}" title="Usa a fonte local selecionada; confirme que ela corresponde a este vídeo"><span class="material-icons-round">download</span> Exportar intervalo</button>
            </div>
        </article>`;
    }).join("");
    // O card inteiro agora é clicável, seleciona o bloco e pula o preview
    list.querySelectorAll(".editorial-block-card").forEach((card) => {
        card.addEventListener("click", (e) => {
            // Ignora se o clique foi num botão de ação (eles têm handlers próprios)
            if (e.target.closest('button')) return;
            
            const blockId = card.dataset.blockId;
            const startS = Number(card.dataset.blockStart);
            const block = blocks.find((item) => String(item.id) === blockId);
            
            state.selectedEditorialBlock = block || null;
            list.querySelectorAll(".editorial-block-card").forEach((c) => c.classList.toggle("selected", c.dataset.blockId === blockId));
            
            // Abre o player dock e pula para o tempo
            const video = document.getElementById("videoPreview");
            const dock = document.getElementById("playerDock");
            if (video && dock && Number.isFinite(startS)) {
                if (!dock.classList.contains("is-open") && state.selectedVideo) {
                    showVideoPreview(state.selectedVideo);
                }
                // Aguarda o vídeo carregar se acabou de ser aberto
                if (video.readyState >= 1) {
                    video.currentTime = startS;
                    video.play().catch(() => {});
                } else {
                    video.addEventListener('loadedmetadata', () => {
                        video.currentTime = startS;
                        video.play().catch(() => {});
                    }, { once: true });
                }
            }
        });
    });

    list.querySelectorAll("[data-block-select]").forEach((button) => {
        button.addEventListener("click", (e) => {
            e.stopPropagation();
            const block = blocks.find((item) => String(item.id) === String(button.dataset.blockSelect));
            state.selectedEditorialBlock = block || null;
            list.querySelectorAll(".editorial-block-card").forEach((card) => card.classList.toggle("selected", card.dataset.blockId === String(button.dataset.blockSelect)));
            const source = block?.source?.title || "fonte local correspondente";
            showToast(`Bloco selecionado: ${block?.title || "intervalo editorial"}. Verifique a fonte (${source}) antes de baixar.`, "info");
            addConsoleLog(`[Blocos] Intervalo selecionado ${formatTime(Number(block?.start || 0))}–${formatTime(Number(block?.end || 0))}; confirme a fonte local antes de exportar.`, "info");
        });
    });
    list.querySelectorAll("[data-block-export]").forEach((button) => {
        button.addEventListener("click", async () => {
            const block = blocks.find((item) => String(item.id) === String(button.dataset.blockExport));
            const videoPath = selectedVideoPathForRequest();
            const sourceUrl = state.sourceUrl || "";
            
            if (!block || (!videoPath && !sourceUrl)) {
                showToast("É necessário um vídeo local ou uma URL de origem para exportar o bloco.", "warning");
                return;
            }
            
            const sourceLabel = block.source?.title || block.source?.url || "o vídeo carregado";
            const msgConfirm = videoPath 
                ? `Confirme que o vídeo local selecionado corresponde a “${sourceLabel}”. Exportar ${formatTime(Number(block.start || 0))}–${formatTime(Number(block.end || 0))} no aspecto original?`
                : `Baixar o intervalo ${formatTime(Number(block.start || 0))}–${formatTime(Number(block.end || 0))} remotamente do YouTube na melhor qualidade? (Isso pode demorar alguns instantes)`;
                
            if (!confirm(msgConfirm)) return;
            button.disabled = true;
            
            // Ícone visual de loading no botão
            const icone = button.querySelector(".material-icons-round");
            const iconeOriginal = icone ? icone.textContent : "download";
            if (icone) icone.textContent = "hourglass_empty";
            
            try {
                const response = await fetch("/api/editorial/blocks/export", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ video_path: videoPath, source_url: sourceUrl, block_id: block.id, start: block.start, end: block.end }),
                });
                const payload = await parseJsonResponse(response, "Exportação do bloco");
                if (!response.ok || !payload.success) throw new Error(payload.error || "Não foi possível exportar o intervalo.");
                showToast("Intervalo exportado no aspecto original.", "success");
                addConsoleLog(`[Blocos] Intervalo ${formatTime(Number(payload.start))}–${formatTime(Number(payload.end))} exportado.`, "success");
                window.open(payload.download_url, "_blank", "noopener");
            } catch (error) {
                showToast(error.message, "error");
                addConsoleLog(`[Blocos] Exportação não concluída: ${error.message}`, "warning");
            } finally {
                button.disabled = false;
                if (icone) icone.textContent = iconeOriginal;
            }
        });
    });
    list.querySelectorAll("[data-highlight-export]").forEach((button) => {
        button.addEventListener("click", async () => {
            const videoPath = selectedVideoPathForRequest();
            const sourceUrl = state.sourceUrl || "";
            if (!videoPath && !sourceUrl) {
                showToast("É necessário um vídeo local ou uma URL de origem para exportar o destaque.", "warning");
                return;
            }
            
            const msgConfirm = videoPath 
                ? "Exportar este destaque da fonte local atual?"
                : "Baixar este destaque remotamente do YouTube na melhor qualidade? (Isso pode demorar alguns instantes)";
                
            if (!confirm(msgConfirm)) return;
            
            button.disabled = true;
            const icone = button.querySelector(".material-icons-round");
            const iconeOriginal = icone ? icone.textContent : "download";
            if (icone) icone.textContent = "hourglass_empty";
            
            try {
                const response = await fetch("/api/editorial/blocks/highlights/export", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ video_path: videoPath, source_url: sourceUrl, block_id: button.dataset.highlightExport, highlight_id: button.dataset.highlightId }),
                });
                const payload = await parseJsonResponse(response, "Exportação do destaque");
                if (!response.ok || !payload.success) throw new Error(payload.error || "Não foi possível exportar o destaque.");
                showToast("Destaque exportado no aspecto original.", "success");
                addConsoleLog(`[Blocos] Destaque ${formatTime(Number(payload.start))}–${formatTime(Number(payload.end))} exportado.`, "success");
                window.open(payload.download_url, "_blank", "noopener");
            } catch (error) {
                showToast(error.message, "error");
                addConsoleLog(`[Blocos] Exportação do destaque não concluída: ${error.message}`, "warning");
            } finally {
                button.disabled = false;
                if (icone) icone.textContent = iconeOriginal;
            }
        });
    });
}

async function loadEditorialBlocks() {
    // O painel lia só um snapshot global que ninguém nunca preencheu, e por isso
    // vivia vazio. Agora ele manda o vídeo e a transcrição abertos: o servidor
    // usa os blocos revisados do Acervo quando existem e, quando não existem,
    // a leitura que o próprio Furia faz da fonte.
    const query = document.getElementById("editorialBlocksSearch")?.value.trim() || "";
    const prioritizeRenan = document.getElementById("editorialBlocksRenanOnly")?.checked;
    try {
        const response = await fetch("/api/editorial/blocks", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            cache: "no-store",
            body: JSON.stringify({
                video_path: state.selectedVideo || "",
                source_url: state.sourceUrl || "",
                segments: state.manualTranscript?.segments || [],
                q: query,
                prioritize_renan: Boolean(prioritizeRenan),
                limit: 80,
            }),
        });
        const payload = await parseJsonResponse(response, "Blocos editoriais");
        renderEditorialBlocks(payload);
    } catch (error) {
        renderEditorialBlocks({ available: false, message: error.message });
    }
}

function startCampaignHubLocalStatusPolling() {
    loadCampaignHubLocalStatus();
    loadEditorialBlocks();
    if (state.campaignHubStatusTimer) window.clearInterval(state.campaignHubStatusTimer);
    state.campaignHubStatusTimer = window.setInterval(() => {
        loadCampaignHubLocalStatus();
        loadEditorialBlocks();
    }, 60000);
}

document.getElementById("btnRefreshEditorialBlocks")?.addEventListener("click", loadEditorialBlocks);
document.getElementById("editorialBlocksRenanOnly")?.addEventListener("change", loadEditorialBlocks);
let editorialBlocksSearchTimer;
document.getElementById("editorialBlocksSearch")?.addEventListener("input", () => {
    window.clearTimeout(editorialBlocksSearchTimer);
    editorialBlocksSearchTimer = window.setTimeout(loadEditorialBlocks, 250);
});

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
    const available = Boolean(payload.feedback_snapshot_present && payload.feedback_snapshot_valid);
    button.disabled = !available;
    button.title = available
        ? "Reconciliar no banco local as decisões finais existentes no snapshot deste checkout"
        : (payload.feedback_snapshot_present
            ? "O snapshot local não passou na validação; envie um snapshot válido antes de restaurar"
            : "Nenhum snapshot válido neste checkout; use “Enviar feedback ao GitHub” em outro notebook primeiro");
}

function setRepositorySyncButtonsDisabled(disabled) {
    ["btnRepositoryPushFeedback", "btnRepositoryRestoreFeedback"].forEach((id) => {
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
    const snapshotPresent = Boolean(payload.feedback_snapshot_present);
    const snapshotValid = Boolean(payload.feedback_snapshot_valid);
    const snapshotRecords = Number(payload.feedback_snapshot_records || 0);
    const snapshotLabel = snapshotPresent
        ? (snapshotValid ? `${snapshotRecords} decisão(ões) no snapshot` : "snapshot inválido; revisão necessária")
        : "snapshot ainda não criado";
    syncRepositoryRestoreAvailability();
    if (payload.feedback_snapshot_dirty) {
        setRepositorySyncStatus(`Feedback local pendente de envio. Use “Enviar feedback ao GitHub”. · ${snapshotLabel}`, "info");
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
        if (action === "push_feedback") {
            setRepositorySyncStatus("Preparando somente o snapshot sanitizado de feedback...", "info");
        } else if (action === "restore_feedback") {
            setRepositorySyncStatus("Validando o snapshot e reconciliando decisões neste notebook...", "info");
        }
        const response = await fetchRepositoryJson("/api/repository/sync", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action }),
        }, 30000);
        const payload = await parseJsonResponse(response, "Sincronização do programa");
        if (!response.ok || payload.success === false) throw new Error(payload.error || "A sincronização não foi concluída");
        state.repositorySync = payload;
        // Keep the detailed state rendered above: it distinguishes code freshness,
        // local code changes, and feedback pending instead of hiding it behind a
        // generic success message. Restore refreshes the local status below because
        // its response is a reconciliation summary, not a repository-status payload.
        if (action !== "restore_feedback") renderRepositorySyncState(payload);
        if (action === "push_feedback") {
            showToast(payload.published ? "Feedback sanitizado sincronizado no GitHub." : "Feedback já estava sincronizado.", "success");
            addConsoleLog("[Sincronização] Nenhum vídeo, transcrição ou chave foi enviado; somente decisões editoriais agregadas.", "info");
        } else if (action === "restore_feedback") {
            const imported = Number(payload.imported || 0);
            const current = Number(payload.already_current || 0);
            const unmatched = Number(payload.unmatched || 0);
            const stale = Number(payload.skipped_older || 0);
            const invalid = Number(payload.invalid || 0);
            const restoreLevel = invalid ? "warning" : "success";
            showToast(`Feedback reconciliado: ${imported} importado(s), ${current} já atual(is)${invalid ? `, ${invalid} inválido(s) ignorado(s)` : ""}.`, restoreLevel);
            addConsoleLog(`[Sincronização] Snapshot sanitizado reconciliado: ${imported} importado(s), ${current} já atual(is), ${stale} antigo(s), ${unmatched} sem correspondência, ${invalid} inválido(s) ignorado(s).`, invalid ? "warning" : "info");
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

async function loadOperationDashboard() {
    if (state.operationDashboardLoading) return;
    state.operationDashboardLoading = true;
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
    } finally {
        state.operationDashboardLoading = false;
    }
}

checkRepositorySync(false);

const RUN_TITLES = {
    complete_process: "Processo completo",
    clip_generation: "Cortando shorts",
    source_import: "Importando fonte",
    source_transcription: "Transcrevendo",
    silence_removal: "Removendo silêncio",
    subtitles: "Gerando legendas",
    thumbnail: "Gerando thumbnail",
};

function handleJobUpdate(job, options = {}) {
    state.activeJob = job;
    if (job.last_event_id) {
        rememberDiagnosticEvent({
            event_id: job.last_event_id,
            job_id: job.id,
            event_name: job.event_name || "job.update",
            level: job.state === "failed" ? "error" : job.state === "cancelled" ? "warning" : "info",
            stage: job.stage,
            message: job.message || job.state,
            details: { state: job.state, progress: job.progress, error: job.error || null },
            sequence: job.event_sequence,
            created_at: job.updated_at,
        });
    }
    // Um job em andamento é a definição de "ocupado"; o resto da interface
    // passa a se comportar de acordo em vez de aceitar cliques e descartá-los.
    if (["queued", "running", "cancel_requested"].includes(job.state)) {
        if (!run.active) beginRun(RUN_TITLES[job.type] || "Processando", job.type, job.message || job.stage || "Preparando…");
        const jobDetail = job.message || job.stage || "Preparando…";
        const jobScope = job.processing_interval?.label || (job.processing_interval?.active ? "faixa selecionada" : state.processingScopeLabel || "Fonte inteira");
        setRunBarScope(jobScope);
        renderRunBarState(inferRunStage(jobDetail), Number(job.progress || 0));
        describeRun(jobDetail);
    } else {
        if (run.active && job.state === "completed") tocarFim();
        endRun();
    }
    const existingIndex = (state.operationJobs || []).findIndex((item) => item.id === job.id);
    if (existingIndex >= 0) state.operationJobs[existingIndex] = job;
    else state.operationJobs = [job, ...(state.operationJobs || [])];
    renderOperationDashboard();
    if (options.refreshDashboard !== false) window.clearTimeout(state.operationRefreshTimer);
    if (options.refreshDashboard !== false) {
        state.operationRefreshTimer = window.setTimeout(loadOperationDashboard, 1200);
    }
    if (job.type === "source_transcription") {
        const active = ["queued", "running", "cancel_requested"].includes(job.state);
        setSourceTranscriptionButtons(active);
        if (active) {
            state.sourceTranscriptionJobId = job.id;
            showSourceStatus(`[Transcrição por URL] ${job.message || job.stage || "Processando"}`, "");
        } else if (job.state === "failed") {
            state.sourceTranscriptionJobId = null;
            showSourceStatus(`[Transcrição por URL] Falha: ${job.error || "consulte o console"}`, "error");
        } else if (job.state === "cancelled") {
            state.sourceTranscriptionJobId = null;
            showSourceStatus("Transcrição por URL cancelada.", "warning");
        }
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
        showProcessingControls(`[Job ${job.id.slice(0, 8)}] ${job.message || job.stage || "Processando"}`);
    }
    if (job.state === "completed") {
        if (bar) bar.style.width = "100%";
        setTimeout(hideProgressBar, 250);
        loadJobDiagnostic(job.id, { silent: true });
    } else if (job.state === "failed") {
        hideProgressBar();
        showToast(job.error || "O job falhou", "error");
        loadJobDiagnostic(job.id, { silent: true });
    } else if (job.state === "cancelled") {
        hideProgressBar();
        hideProcessingControls();
        showToast("Processamento cancelado", "warning");
        loadJobDiagnostic(job.id, { silent: true });
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
    if (!item || !item.path) {
        showToast("Não foi possível selecionar este vídeo: caminho inválido.", "error");
        return;
    }
    const changedVideo = state.selectedVideo && state.selectedVideo !== item.path;
    // Uma transcrição sem dono é desta fonte, não lixo.
    //
    // O sentinela "pending-source" existe justamente para a transcrição que
    // chegou antes de haver vídeo escolhido. Só que `manualTranscriptVideo`
    // também fica em branco em três caminhos — quando o servidor devolve a
    // transcrição sem o caminho da fonte, quando a transcrição local termina
    // antes de haver seleção, e quando o editor cola o texto à mão. Nesses
    // casos ela não era "pending-source" nem igual ao caminho do item, então
    // caía no descarte alguma linha abaixo, sem aviso nenhum.
    //
    // O editor viu o resultado disso e não a causa: "apesar de eu ter colado a
    // transcrição previamente, o programa aparentemente tentou fazer uma
    // transcrição também". Tinha mesmo: a colada já não existia mais.
    const transcriptUnclaimed = !state.manualTranscriptVideo || state.manualTranscriptVideo === "pending-source";
    const transcriptBelongsToItem = state.manualTranscript && (
        state.manualTranscriptVideo === item.path || transcriptUnclaimed
    );
    state.selectedVideo = item.path;
    state.selectedVideoName = item.name;
    // E ela ganha dono agora. Sobreviver sem dono seria pior que ser
    // descartada: na próxima troca de fonte ela continuaria "sem dono" e
    // colaria no vídeo errado — o corte sairia com a transcrição de outro
    // vídeo, que é um defeito silencioso e muito mais caro de perceber.
    if (transcriptBelongsToItem && transcriptUnclaimed) {
        state.manualTranscriptVideo = item.path;
    }
    if (changedVideo) {
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
    if (state.manualTranscript && !transcriptBelongsToItem) {
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
        addConsoleLog("[Sistema] A nova seleção foi liberada; a tarefa anterior continua na fila persistente.", "info");
    }
    addConsoleLog(`[Sistema] Vídeo selecionado: ${item.name}`, "info");
    showToast(`Vídeo selecionado: ${truncateName(item.name, 30)}`, "success");
    if (typeof loadEditorialBlocks === "function") loadEditorialBlocks();
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
    const section = document.getElementById("playerDock");
    const video = document.getElementById("videoPreview");
    const source = document.getElementById("videoPreviewSource");
    const nameEl = document.getElementById("previewVideoName");
    const status = document.getElementById("videoPreviewStatus");
    const mainContent = document.querySelector(".main-content");

    // `state.selectedVideo` guarda o *caminho*, não o item — e dois lugares
    // chamavam esta função com ele: o clique num bloco editorial e o clique
    // numa unidade de leitura, que são justamente os dois lugares de onde o
    // editor abriria o player para conferir um corte. Uma string não tem
    // `.path`, então a guarda abaixo devolvia na hora e o player simplesmente
    // não aparecia. Nenhum erro no console, nenhuma mensagem: o clique não
    // fazia nada. Foi assim que "o player simplesmente SUMIU".
    if (typeof item === "string") {
        item = { path: item, name: state.selectedVideoName || "" };
    }
    if (!section || !video || !source || !item?.path) return;
    const token = ++state.previewToken;
    
    section.classList.add("is-open");
    if (mainContent) mainContent.classList.add("dock-open");
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

function deselectVideo() {
    state.selectedVideo = null;
    state.selectedVideoName = "";
    document.querySelectorAll(".media-card").forEach(el => el.classList.remove("selected"));

    const info = document.getElementById("selectedVideoInfo");
    info.className = "selected-video";
    info.innerHTML = `
        <div class="no-video">
            <span class="material-icons-round">videocam_off</span>
            <p>Nenhum vídeo selecionado</p>
        </div>`;

    // Hide preview
    const previewSection = document.getElementById("videoPreviewSection");
    if (previewSection) previewSection.style.display = "none";
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
    const previewSection = document.getElementById("videoPreviewSection");
    if (previewSection) previewSection.style.display = "none";
});

// ─── Actions ───

function requireVideo() {
    if (!state.selectedVideo) {
        showToast("Selecione um vídeo primeiro na biblioteca!", "warning");
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

function openCutOptionsModal(mode = "smart") {
    if (!requireVideo()) return;
    const modal = document.getElementById("cutOptionsModal");
    if (!modal) return;
    state.pendingProcessMode = mode === "complete" ? "complete" : "smart";
    const name = document.getElementById("cutOptionsVideoName");
    if (name) name.textContent = state.selectedVideoName || "vídeo selecionado";
    const enabled = document.getElementById("faceTrackingEnabled");
    if (enabled) enabled.checked = state.faceTracking !== false;
    const title = document.getElementById("cutOptionsTitle");
    if (title) title.innerHTML = `<span class="material-icons-round">${state.pendingProcessMode === "complete" ? "rocket_launch" : "center_focus_strong"}</span> ${state.pendingProcessMode === "complete" ? "Opções do processo completo" : "Opções do corte"}`;
    const buttonIcon = document.getElementById("btnStartSmartCutIcon");
    const buttonLabel = document.getElementById("btnStartSmartCutLabel");
    if (buttonIcon) buttonIcon.textContent = state.pendingProcessMode === "complete" ? "rocket_launch" : "auto_awesome";
    if (buttonLabel) buttonLabel.textContent = state.pendingProcessMode === "complete" ? "Executar processo completo" : "Gerar e ranquear cortes";
    const startInput = document.getElementById("processingStartInput");
    const endInput = document.getElementById("processingEndInput");
    if (startInput) startInput.value = state.processingStart || "";
    if (endInput) endInput.value = state.processingEnd || "";
    updateProcessingIntervalHint();
    modal.classList.add("active");
}
function closeCutOptionsModal() {
    document.getElementById("cutOptionsModal")?.classList.remove("active");
}
function parseProcessingTime(value) {
    const text = String(value || "").trim().replace(",", ".");
    if (!text) return null;
    if (/^\d+(?:\.\d+)?$/.test(text)) return Number(text);
    const parts = text.split(":").map(Number);
    if (parts.some((part) => !Number.isFinite(part)) || ![2, 3].includes(parts.length)) return NaN;
    if (parts.slice(1).some((part) => part < 0 || part >= 60)) return NaN;
    return parts.length === 2 ? parts[0] * 60 + parts[1] : parts[0] * 3600 + parts[1] * 60 + parts[2];
}
function formatProcessingTime(seconds) {
    if (!Number.isFinite(seconds)) return "tempo inválido";
    const total = Math.max(0, Math.round(seconds));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const rest = total % 60;
    return hours ? `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}` : `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}
function readProcessingInterval() {
    const start = document.getElementById("processingStartInput")?.value.trim() || "";
    const end = document.getElementById("processingEndInput")?.value.trim() || "";
    const startSeconds = parseProcessingTime(start);
    const endSeconds = parseProcessingTime(end);
    if (!start && !end) return { valid: true, start: null, end: null, label: "fonte inteira" };
    if ((start && !Number.isFinite(startSeconds)) || (end && !Number.isFinite(endSeconds))) {
        return { valid: false, error: "Use segundos, mm:ss ou hh:mm:ss no início e no fim." };
    }
    
    // Tratamento mais tolerante e guiado para durações parciais (ex: deixou o fim em branco)
    const finalStart = Number.isFinite(startSeconds) ? startSeconds : 0;
    const finalEnd = Number.isFinite(endSeconds) ? endSeconds : Infinity;
    
    if (finalStart < 0) {
        return { valid: false, error: "O início do intervalo não pode ser negativo." };
    }
    if (finalEnd <= finalStart) {
        return { valid: false, error: "O fim do intervalo precisa ser maior que o início." };
    }
    
    return {
        valid: true,
        start: start || null,
        end: end || null,
        label: `${start ? formatProcessingTime(finalStart) : "início da fonte"}–${end ? formatProcessingTime(finalEnd) : "fim da fonte"}`,
    };
}
function updateProcessingIntervalHint() {
    const hint = document.getElementById("processingIntervalHint");
    const chip = document.getElementById("processingIntervalChip");
    const interval = readProcessingInterval();
    if (chip) chip.textContent = interval.valid ? (interval.label || "Fonte inteira") : "Verificar faixa";
    if (!hint) return;
    hint.textContent = interval.valid
        ? (interval.start || interval.end ? `Esta execução usará somente ${interval.label}. A mídia original não será alterada.` : "Deixe os dois campos vazios para usar a fonte inteira. Aceita segundos, mm:ss ou hh:mm:ss.")
        : interval.error;
    hint.classList.toggle("interval-error", !interval.valid);
}
async function startSmartCut() {
    const interval = readProcessingInterval();
    if (!interval.valid) {
        updateProcessingIntervalHint();
        showToast(interval.error, "warning");
        return;
    }
    state.processingStart = interval.start || "";
    state.processingEnd = interval.end || "";
    state.processingScopeLabel = interval.label || "fonte inteira";
    closeCutOptionsModal();
    if (!requireVideo()) return;
    state.faceTracking = Boolean(document.getElementById("faceTrackingEnabled")?.checked);
    const mode = state.pendingProcessMode === "complete" ? "complete" : "smart";
    const userContext = document.getElementById("userContextInput").value.trim();
    const videoGenre = document.getElementById("settingVideoGenre").value;
    const geminiKey = document.getElementById("settingGeminiKey").value.trim();
    const aiBackend = document.getElementById("settingAiBackend").value;
    const modeLabel = mode === "complete" ? "processo completo" : "corte inteligente de shorts";
    addConsoleLog(`[Acao] Iniciando ${modeLabel}...`, "info");
    addConsoleLog(`[Intervalo] ${interval.label}; a fonte original não será alterada.`, "info");
    if (mode === "smart") addConsoleLog(`[Enquadramento] Facetracking ${state.faceTracking ? "ativado" : "desativado"}; o fallback mantém a proporção original quando necessário.`, "info");
    if (userContext) addConsoleLog(`[Contexto] "${userContext}"`, "info");
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
    const endpoint = mode === "complete" ? "/api/process/complete" : "/api/process/cut";
    const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            video_path: state.selectedVideo,
            output_dir: state.outputDir || "",
            face_tracking: state.faceTracking,
            user_context: userContext,
            video_genre: videoGenre,
            transcription_source: document.getElementById("settingTranscriptionSource")?.value || "auto",
            audit_mode: document.getElementById("settingAuditMode")?.value || "standard",
            preferred_format: document.getElementById("settingPreferredFormat")?.value || "auto",
            processing_start: interval.start,
            processing_end: interval.end,
            ...(state.manualTranscript ? {
                transcript_segments: state.manualTranscript.segments,
                transcript_language: state.manualTranscript.language || "pt",
            } : {}),
        }),
    });
    const started = await parseJsonResponse(response, mode === "complete" ? "Processo completo" : "Corte inteligente");
    if (!response.ok || started.error) throw new Error(started.error || `Não foi possível iniciar o ${modeLabel}`);
    if (started.job_id) {
        state.activeJob = { id: started.job_id, state: started.state || "queued" };
        showProcessingControls(`${mode === "complete" ? "Processo completo" : "Corte"} adicionado à fila persistente.`);
    }
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

document.getElementById("actionComplete").querySelector(".btn-action").addEventListener("click", () => {
    openCutOptionsModal("complete");
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

function selectedVideoPathForRequest() {
    return typeof state.selectedVideo === "string" ? state.selectedVideo : (state.selectedVideo?.path || "");
}

async function openConfiguredDownloadsFolder() {
    try {
        const response = await fetch("/api/open_folder", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: state.outputDir || "" }),
        });
        const data = await parseJsonResponse(response, "Pasta de downloads");
        if (!response.ok || data.error) throw new Error(data.error || "Não foi possível abrir a pasta de downloads");
        showToast("Pasta de downloads aberta.", "success");
    } catch (error) {
        showToast(error.message, "error");
    }
}

document.getElementById("btnOpenDownloadsDir")?.addEventListener("click", openConfiguredDownloadsFolder);

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
    const multimodalStatus = String(multimodal.source_identity_status || "").toLowerCase();
    const provenance = context.transcription_provenance || {};
    const campaignHub = context.campaign_hub || {};
    const analysisInput = multimodal.analysis_input || {};
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
            if (hook.needs_visual_review) reviewReasons.push("revisar sobreposição visual/áudio");
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
    const transcriptMarkup = provenance.confirmed_by_editor || provenance.manual_supplied
        ? `<span class="context-source-status validated" title="O texto colado/importado foi usado como timeline canônica; não houve retranscrição silenciosa">transcrição manual confirmada · ${Number(provenance.segment_count || 0)} segmentos</span>`
        : `<span class="context-source-status review" title="A fonte temporal veio do pipeline automático; confirme antes de publicar">transcrição automática · confirmar</span>`;
    const proxyMarkup = analysisInput.used_proxy
        ? `<span class="context-source-status validated" title="O Gemini recebeu uma cópia visual menor; o vídeo original não foi alterado">vídeo compactado para Gemini</span>`
        : "";
    const hubMarkup = campaignHub.used
        ? `<span class="context-source-status validated" title="Priors agregados e limitados foram usados apenas como desempate editorial">Campaign Hub · prior fraco aplicado</span>`
        : `<span class="context-source-status review" title="Nenhum snapshot do Campaign Hub foi carregado nesta análise">Campaign Hub · sem snapshot</span>`;
    result.hidden = false;
    const participantConfidence = Number(context.participant_confidence);
    const participantMarkup = Number.isFinite(participantConfidence)
        ? `<span title="Referência textual e sinais de locutor; não é identificação visual">participante ${Math.round(Math.max(0, Math.min(1, participantConfidence)) * 100)}%</span>`
        : "";
    result.innerHTML = `<div class="context-result-summary"><strong>${escapeHtml(context.description || "Contexto editorial analisado.")}</strong><div class="context-result-facts"><span>${escapeHtml(mode)}</span><span>${qa} pergunta(s)–resposta</span><span>${chapters} capítulo(s)</span><span>${windows} janela(s) de entrevista</span><span>${Number(quality.segment_count || 0)} segmentos · ${escapeHtml(quality.status || "qualidade não validada")}</span>${participantMarkup}${speakerMarkup}${transcriptMarkup}${proxyMarkup}${hubMarkup}${multimodalMarkup}</div></div>${localAudioMarkup}${hookMarkup}`;
}

async function pollEditorialContextJob(jobId, button, status) {
    const started = Date.now();
    // Aumentar o timeout de 20 para 60 minutos, já que o Gemini com fallback local em lives de 2h pode demorar
    while (Date.now() - started < 60 * 60 * 1000) {
        await new Promise(resolve => setTimeout(resolve, 1200));
        const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`);
        const job = await parseJsonResponse(response, "Status da análise de contexto");
        if (!response.ok) throw new Error(job.error || "Não foi possível consultar a análise");
        if (job.message && status) status.textContent = job.message;
        if (job.state === "completed") {
            const artifact = Array.isArray(job.artifacts) ? job.artifacts.find(item => item?.type === "editorial_context") : null;
            state.editorialContext = artifact?.context || null;
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
    const transcript = state.manualTranscript ? formatTranscriptForEditor(state.manualTranscript) : (document.getElementById("manualTranscriptInput")?.value.trim() || "");
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
        });
        const data = await parseJsonResponse(response, "Análise de contexto");
        if (!response.ok || !data.success) throw new Error(data.error || "Não foi possível iniciar a análise de contexto");
        await pollEditorialContextJob(data.job_id, button, status);
        addConsoleLog("[Contexto] Dossiê integral concluído e exibido no painel.", "success");
        showToast("Contexto analisado antes do corte.", "success");
    } catch (error) {
        if (status) status.textContent = error.message;
        addConsoleLog(`[Contexto] ${error.message}`, "error");
        showToast(error.message, "error");
    } finally {
        button.disabled = false;
        button.classList.remove("loading");
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

const editorialFormatLabels = {
    vertical_916: "9:16 — headline central",
    square_alfinetei: "1:1 — Alfinetei",
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
        const diversityReason = String(clip.diversity_reason || "").trim();
        const reviewFlags = clip.review_flags || {};
        const contextReferenceFlag = Boolean(clip.starts_with_context_reference || reviewFlags.starts_with_context_reference);
        const weakPayoffFlag = Boolean(clip.payoff_weak_ending || reviewFlags.payoff_weak_ending);
        const closureType = String(clip.closure_type || "");
        const closureLabels = { conclusion: "conclusão", closed_statement: "frase fechada", cliffhanger: "continuidade", open: "fecho a revisar" };
        const speakerLabel = String(clip.speaker || clip.speaker_role || "").trim();
        const speakerConfidence = Number(clip.speaker_confidence);
        const overlapSuspected = Boolean(clip.overlap_suspected || clip.speaker_overlap);
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
            visual_meme: "meme / arte composta",
            desconhecido: "formato a revisar",
        };
        const preserveComposition = Boolean(clip.preserve_composition || reviewFlags.preserve_composition || clip.reframe_policy === "preservar_composicao");
        const needsFactReview = Boolean(reviewFlags.needs_fact_review || reviewFlags.needsFactReview);
        const needsLegalReview = Boolean(reviewFlags.needs_legal_review || reviewFlags.needsLegalReview);
        const chapterCount = Number(clip.chapter_count || reviewFlags.chapter_count || 0);
        const chapterScore = Number(clip.chapter_coherence_score ?? reviewFlags.chapter_coherence_score);
        const chapterBridge = Boolean(clip.qa_bridge || reviewFlags.qa_bridge);
        const qaBoundaryBasis = String(clip.qa_boundary_basis || reviewFlags.qa_boundary_basis || "").trim();
        const qaBoundaryReviewRequired = Boolean(clip.qa_boundary_review_required || reviewFlags.qa_boundary_review_required);
        const qaBoundaryLabels = {
            mudanca_de_locutor: "mudança de locutor",
            marcador_de_locutor: "marcador de locutor",
            segunda_troca_de_locutor: "segunda troca de locutor",
            sem_diarizacao: "sem diarização confiável",
        };
        const qaBoundaryLabel = qaBoundaryLabels[qaBoundaryBasis] || qaBoundaryBasis.replaceAll("_", " ");
        const durationSeconds = Number(clip.duration || ((clip.end || 0) - (clip.start || 0)) || 0);
        const durationFit = Number(clip.duration_fit ?? factors.duration_fit);
        const durationPreference = clip.duration_preference || {};
        const durationStatus = String(durationPreference.status || reviewFlags.duration_preference || (
            durationSeconds <= 180 ? "curto_preferencial" : "longo_para_revisao"
        ));
        const durationException = Boolean(durationPreference.exception || reviewFlags.duration_exception || durationStatus === "excecao_contextual");
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
        const contextualHookAvailable = Boolean(contextualHook.hook_text || contextualHook.family);
        const contextualHookReview = Boolean(clip.hook_review_required || reviewFlags.hook_review_required);
        const contextualHookReviewReasons = [];
        if (contextualHookReview) {
            if (reviewFlags.speaker_review_required || clip.speaker_turn_valid == null) contextualHookReviewReasons.push("locutor não diarizado");
            if (contextualHook.audio_signal && contextualHook.audio_signal.available === false) contextualHookReviewReasons.push("áudio sem sinal contextual");
            if (clip.overlap_suspected || reviewFlags.overlap_suspected) contextualHookReviewReasons.push("possível sobreposição");
        }
        const contextualHookReviewHint = contextualHookReviewReasons.join(" · ") || "confirmar no vídeo";
        const transcriptionReviewRequired = Boolean(clip.transcription_review_required || reviewFlags.transcription_review_required);
        const transcriptionCoverageStatus = String(clip.transcription_coverage_status || reviewFlags.transcription_coverage_status || "").trim();
        const transcriptionReviewReason = String(clip.transcription_review_reason || reviewFlags.transcription_review_reason || (
            transcriptionCoverageStatus === "partial" ? "cobertura parcial da transcrição; confirme o trecho no vídeo" : "identidade temporal da transcrição não validada; confirme o trecho no vídeo"
        )).trim();
        const campaignPriorAvailable = Boolean(campaignPrior.available || reviewFlags.campaign_hub_prior_available);
        const campaignHookFamily = String(campaignPrior.hook_family || reviewFlags.campaign_hub_hook_family || "").trim();
        const campaignSampleCount = Number(campaignPrior.sample_count || reviewFlags.campaign_hub_sample_count || 0);
        const feedbackCalibration = clip.feedback_calibration || {};
        const feedbackDurationSignal = feedbackCalibration.duration_signal || {};
        const feedbackCalibrationAvailable = Boolean(feedbackCalibration.eligible || reviewFlags.feedback_calibration_eligible);
        const feedbackSampleSize = Number(feedbackCalibration.sample_size || reviewFlags.feedback_sample_size || 0);
        const feedbackDurationGap = Number(feedbackDurationSignal.gap_seconds ?? reviewFlags.feedback_duration_gap_seconds ?? 0);
        const reviewStatus = reviewStatusOf(clip);
        const reviewMeta = reviewStatusMeta(reviewStatus);
        const confidence = Math.round((clip.confidence || 0) * 100);
        const clipSource = clip.source || "nlp";
        const sourceLabels = { "gemini": "Gemini", "llm": "Ollama", "nlp": "NLP" };
        const sourceLabel = sourceLabels[clipSource] || "NLP";
        const sourceClass = clipSource === "gemini" ? "source-gemini" : (clipSource === "llm" ? "source-llm" : "source-nlp");
        const candidateOrigin = String(clip.candidate_origin || "local_primary");
        const candidateOriginLabel = String(clip.candidate_origin_label || "Origem local registrada");
        const candidateOriginNote = String(clip.candidate_origin_note || "Origem registrada para transparência da revisão.");
        const originClass = candidateOrigin === "local_fallback" ? "candidate-origin-fallback" : "candidate-origin-primary";
        const transcriptId = `transcript-${originalIndex}`;
        const layoutMeta = layoutMetaForClip(clip);
        const editorialBlock = clip.editorial_block || {};
        const blockTags = Array.isArray(editorialBlock.tags) ? editorialBlock.tags : [];
        const latestAdjustment = clip.latest_adjustment || {};
        const adjustmentState = clip.adjustment_state || (latestAdjustment.start != null ? "saved" : "");
        const clipTranscriptText = String(clip.text || clip.transcript || "");
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
                    <span class="score-value">${clip.viral_score || 0}</span>
                    <span class="score-label">/100</span>
                </div>
                <!-- Onde na fonte, e por quanto tempo. É a primeira pergunta de
                     quem edita vídeo, e não estava em lugar nenhum do cartão. -->
                <span class="result-tempo" title="Posição na fonte e duração do corte">
                    <b>${formatTime(clip.start || 0)}</b><i>→</i><b>${formatTime(clip.end || 0)}</b>
                    <em>${Math.round(durationSeconds)}s</em>
                </span>
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
                ${contextualHookAvailable ? `<div class="clip-hook-provenance ${contextualHookReview ? 'review' : ''}"><span class="material-icons-round">bolt</span><span><b>Hook contextual:</b> ${escapeHtml(String(contextualHook.family || 'não classificado'))} · ${Number(contextualHook.score || 0).toFixed(1)}/100${contextualHook.payoff_confirmed ? ' · payoff próximo' : ' · payoff a confirmar'}${contextualHookReview ? ` · ${escapeHtml(contextualHookReviewHint)}` : ''}<br><q>${escapeHtml(String(contextualHook.hook_text || ''))}</q></span></div>` : ''}
                ${feedbackCalibrationAvailable ? `<div class="clip-feedback-prior"><span class="material-icons-round">tune</span><span><b>Feedback editorial aplicado:</b> ${Math.max(0, feedbackSampleSize)} decisões finais${Math.abs(feedbackDurationGap) >= 0.1 ? ` · aprovados ${feedbackDurationGap > 0 ? 'tendem a ser mais curtos' : 'tiveram duração média maior'} em ${Math.abs(feedbackDurationGap).toFixed(1)}s` : ''} · influência limitada</span></div>` : ''}
                ${(needsFactReview || needsLegalReview) ? `<div class="clip-review-risk ${needsLegalReview ? 'legal' : ''}"><span class="material-icons-round">${needsLegalReview ? 'gavel' : 'fact_check'}</span> ${needsLegalReview ? 'Revisão factual e jurídica' : 'Revisão factual recomendada'}</div>` : ''}
                ${topicSignature ? `<div class="clip-topic-chip" title="Sinal lexical usado somente para diversificar o portfólio">Tema: ${escapeHtml(topicSignature.replace(':', ' · ').replaceAll('-', ', '))}</div>` : ''}
                ${durationStatus ? `<div class="clip-duration-policy ${durationMeta.className}" title="${escapeHtml(String(durationPreference.reason || durationMeta.hint))}"><span class="material-icons-round">${durationMeta.icon}</span><span><b>${escapeHtml(durationMeta.label)}</b>${Number.isFinite(durationFit) ? ` · brevidade ${Math.round(Math.max(0, Math.min(100, durationFit)))}%` : ''}${durationException ? ' · contexto excepcional preservado' : ''}</span></div>` : ''}
                ${closureType ? `<div class="clip-closure-chip ${escapeHtml(closureType)}"><span class="material-icons-round">${closureType === 'conclusion' ? 'task_alt' : closureType === 'cliffhanger' ? 'hourglass_top' : 'subtitles'}</span> ${escapeHtml(closureLabels[closureType] || closureType)}</div>` : ''}
                ${contextReferenceFlag ? `<div class="clip-review-risk"><span class="material-icons-round">link_off</span><span><b>Abertura dependente:</b> o trecho começa com uma referência sem antecedente claro.</span></div>` : ''}
                ${weakPayoffFlag ? `<div class="clip-review-risk"><span class="material-icons-round">pending</span><span><b>Payoff a revisar:</b> o final pode continuar o raciocínio em vez de concluí-lo.</span></div>` : ''}
                ${(speakerLabel || overlapSuspected || Number.isFinite(speakerConfidence)) ? `<div class="clip-speaker-note ${overlapSuspected ? 'warning' : ''}"><span class="material-icons-round">${overlapSuspected ? 'record_voice_over' : 'person'}</span> ${speakerLabel ? `Locutor: ${escapeHtml(speakerLabel)}` : 'Locutor não identificado'}${Number.isFinite(speakerConfidence) ? ` · ${Math.round(Math.max(0, Math.min(1, speakerConfidence)) * 100)}%` : ''}${overlapSuspected ? ' · possível sobreposição' : ''}</div>` : ''}
                ${diversityPenalty >= 20 ? `<div class="clip-diversity-note"><span class="material-icons-round">filter_list</span> Similaridade com outro corte: ${diversityPenalty}%${diversityReason ? ` · ${escapeHtml(diversityReason)}` : ''}</div>` : ''}
                <!-- O tempo do corte subiu para a faixa do topo, onde é a
                     primeira coisa que se lê. Repetir aqui era ruído. -->
                ${(editorialBlock.thesis || editorialBlock.context_summary || blockTags.length) ? `<div class="editorial-block-dossier">
                    <div class="editorial-block-kicker"><span class="material-icons-round">inventory_2</span> Dossiê do bloco · ${escapeHtml(editorialBlock.state || "candidato")}</div>
                    ${editorialBlock.thesis ? `<strong>${escapeHtml(editorialBlock.thesis)}</strong>` : ''}
                    ${editorialBlock.context_summary ? `<p>${escapeHtml(editorialBlock.context_summary)}</p>` : ''}
                    ${editorialBlock.moment_reason ? `<small><b>Momento:</b> ${escapeHtml(editorialBlock.moment_reason)}</small>` : ''}
                    ${blockTags.length ? `<div class="editorial-block-tags">${blockTags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join('')}</div>` : ''}
                </div>` : ''}
                <button class="btn btn-sm btn-boundary-toggle" onclick="toggleBoundaryEditor(${originalIndex})" title="Remover falas desnecessárias antes ou depois do trecho"><span class="material-icons-round">graphic_eq</span> Ajustar entrada e saída</button>
                <div class="clip-boundary-editor" id="boundary-editor-${originalIndex}" hidden>
                    <div class="clip-boundary-fields">
                        <label>Entrada <input type="number" min="0" step="0.1" data-boundary-start="${originalIndex}" value="${Number(clip.start || 0).toFixed(1)}"></label>
                        <label>Saída <input type="number" min="0" step="0.1" data-boundary-end="${originalIndex}" value="${Number(clip.end || 0).toFixed(1)}"></label>
                        <button class="btn btn-sm btn-primary" onclick="previewClipBoundary(${originalIndex})"><span class="material-icons-round">preview</span> Pré-visualizar</button>
                        <button class="btn btn-sm btn-success" onclick="persistClipBoundary(${originalIndex})" ${clip.clip_id ? "" : "disabled"}><span class="material-icons-round">save</span> Salvar ajuste</button>
                    </div>
                    <small><b>Como usar:</b> Arraste as alças douradas sobre a onda. O trecho aceso é o corte; o cinza dos lados é a margem, para você poder voltar. “Pré-visualizar” atualiza somente este card e mantém o arquivo original. “Salvar ajuste” registra a decisão para o próximo render; não cria um MP4 novo nesta etapa.</small>
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
                    <button class="btn btn-sm btn-success ${reviewStatus === 'approved' ? 'is-current' : ''}" aria-pressed="${reviewStatus === 'approved'}" onclick="setClipReview(${originalIndex}, 'approved')"><span class="material-icons-round">check_circle</span>${reviewStatus === 'approved' ? 'Aprovado' : 'Aprovar'}</button>
                    <button class="btn btn-sm btn-review-context ${reviewStatus === 'needs_review' ? 'is-current' : ''}" aria-pressed="${reviewStatus === 'needs_review'}" title="Não aprova nem rejeita; abre a transcrição completa e coloca o clip na fila de revisão." onclick="openContextReview(${originalIndex})"><span class="material-icons-round">visibility</span>${reviewStatus === 'needs_review' ? 'Contexto aberto' : 'Revisar contexto'}</button>
                    <button class="btn btn-sm btn-danger ${reviewStatus === 'rejected' ? 'is-current' : ''}" aria-pressed="${reviewStatus === 'rejected'}" onclick="setClipReview(${originalIndex}, 'rejected')"><span class="material-icons-round">close</span>${reviewStatus === 'rejected' ? 'Rejeitado' : 'Rejeitar'}</button>
                </div>
            </div>`;

        grid.appendChild(card);
    });

    if (clips.length === 0) {
        grid.innerHTML = `<div class="review-empty-state"><span class="material-icons-round">filter_alt_off</span><strong>Nenhum corte nesta fila</strong><p>Altere o filtro para revisar os outros candidatos.</p></div>`;
    }

    // O mapa da fonte lê `state.clips` inteiro, não a fila filtrada: ele existe
    // para mostrar a cobertura da fonte, e um filtro de revisão não muda de
    // onde os cortes saíram.
    window.desenharMapaDaFonte?.();
}

function toggleBoundaryEditor(index) {
    const editor = document.getElementById(`boundary-editor-${index}`);
    if (!editor) return;
    editor.hidden = !editor.hidden;
    // A onda só pode ser desenhada depois que o painel tem tamanho: filho de um
    // elemento escondido mede zero pixel, e um canvas de zero pixel não desenha
    // nada nem reclama. Foi assim que o player sumiu duas vezes.
    if (!editor.hidden) window.montarTalho?.(index);
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
    const sourceDuration = Number(clip.source_duration ?? clip.video_duration ?? clip.duration);
    if (Number.isFinite(sourceDuration) && sourceDuration > 0 && (start < 0 || end > sourceDuration)) {
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
        const removedBefore = Math.max(0, Number(data.clip.start || 0) - Number(originalBounds.start || 0));
        const removedAfter = Math.max(0, Number(originalBounds.end || 0) - Number(data.clip.end || 0));
        const removalSummary = `Removeu ${removedBefore.toFixed(1)}s antes e ${removedAfter.toFixed(1)}s depois`;
        if (feedback) feedback.textContent = `Prévia aplicada: ${formatTime(data.clip.start)}–${formatTime(data.clip.end)}. ${removalSummary}. Nada foi salvo ainda; revise o vídeo e clique em “Salvar ajuste” somente se estiver limpo.`;
        showToast(`Prévia limpa aplicada. ${removalSummary}.`, "success");
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
    // As alças escrevem nos campos escondidos; o "Pré-visualizar" lia deles, o
    // "Salvar" não. Quem arrastasse e salvasse direto gravava clip.start e
    // clip.end — os valores ORIGINAIS — e o corte voltava igual, sem erro e sem
    // registro. Era exatamente o que o editor descreveu: "confirmei que era para
    // calibrar o corte, o video se manteve o mesmo, não gerou logs".
    const campoInicio = document.querySelector(`[data-boundary-start="${index}"]`);
    const campoFim = document.querySelector(`[data-boundary-end="${index}"]`);
    const arrastado = {
        start: Number(campoInicio?.value),
        end: Number(campoFim?.value),
    };
    const usarArrasto = Number.isFinite(arrastado.start) && Number.isFinite(arrastado.end)
        && arrastado.end > arrastado.start;
    const adjustment = usarArrasto
        ? {
            start: arrastado.start,
            end: arrastado.end,
            duration: Number((arrastado.end - arrastado.start).toFixed(2)),
            boundary_adjustment: { source: "manual" },
        }
        : clip.latest_adjustment || {
            start: Number(clip.start),
            end: Number(clip.end),
            duration: Number(clip.duration),
            boundary_adjustment: { source: "manual" },
        };
    if (usarArrasto) {
        addConsoleLog(
            `[Ajuste] Corte ${index + 1}: ${Number(clip.start).toFixed(1)}s→${Number(clip.end).toFixed(1)}s `
            + `passa a ${adjustment.start.toFixed(1)}s→${adjustment.end.toFixed(1)}s `
            + `(${adjustment.duration.toFixed(1)}s).`,
            "info",
        );
    }
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
                confidence: Number(clip.confidence || 0),
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
        if (feedbackData?.calibration) renderEditorialLearning(feedbackData.calibration);
        renderReviewCommandCenter();
        renderResultsGrid();
        showToast(messages[action] || "Feedback salvo", action === "approved" ? "success" : "warning");
        loadEditorialLearning();
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

function renderCandidateVolumeNotice(diagnostics = {}) {
    const notice = document.getElementById("candidateVolumeNotice");
    if (!notice) return;
    const expected = Number(diagnostics.expected_count || 0);
    const primary = Number(diagnostics.primary_count || 0);
    const fallback = Number(diagnostics.fallback_count || 0);
    const discarded = Number(diagnostics.fallback_discarded_count || 0);
    const discardedOverlap = Number(diagnostics.fallback_discarded_overlap || 0);
    const discardedSimilarity = Number(diagnostics.fallback_discarded_similarity || 0);
    const finalCount = Number(diagnostics.final_count || 0);
    const chubDiscovery = Number(diagnostics.campaign_hub_discovery_count || 0);
    const chubPublishable = Number(diagnostics.campaign_hub_publishable_guided_count || 0);
    const chubFiltered = Number(diagnostics.campaign_hub_guided_filtered_by_speaker || 0);
    const chubNote = chubDiscovery > 0
        ? ` Campaign Hub encontrou ${chubDiscovery} trecho(s); ${chubPublishable} entraram na fila publicável${chubFiltered > 0 ? ` e ${chubFiltered} ficaram para revisão de locutor` : ""}.`
        : "";
    if (!expected && !primary && !finalCount && !chubDiscovery) {
        notice.hidden = true;
        notice.textContent = "";
        return;
    }
    notice.hidden = false;
    notice.className = "candidate-volume-notice";
    if (fallback > 0) {
        notice.classList.add("fallback");
        const discardedNote = discarded > 0
            ? ` ${discarded} alternativa(s) foram descartadas por redundância${discardedOverlap > 0 ? ` (${discardedOverlap} por sobreposição` : " ("}${discardedSimilarity > 0 ? `${discardedOverlap > 0 ? ", " : ""}${discardedSimilarity} por repetição textual` : ""}).`
            : " Nenhuma alternativa foi descartada por redundância.";
        notice.innerHTML = `<span class="material-icons-round">alt_route</span><span>Pool ampliado com segurança: ${primary} candidato(s) da fonte principal + ${fallback} alternativa(s) locais.${discardedNote} Os gates de contexto permaneceram ativos.${chubNote}</span>`;
        return;
    }
    if (expected && finalCount < expected) {
        notice.classList.add("warning");
        notice.innerHTML = `<span class="material-icons-round">info</span><span>${finalCount} candidato(s) chegaram à revisão; a referência estrutural era ${expected}. O vídeo pode ter pouco material autossuficiente ou gates editoriais rigorosos.${chubNote}</span>`;
        return;
    }
    notice.innerHTML = `<span class="material-icons-round">check_circle</span><span>Pool editorial adequado: ${finalCount} candidato(s) distintos chegaram à revisão.${chubNote}</span>`;
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

// O 409 diz "cancele na barra do topo"; o editor respondeu "não mostra barra no
// topo só para constar", e estava certo. Depois de recarregar a página, a aba
// não guarda nenhuma lembrança do processamento — quem sabe dele é o servidor.
// Então a barra é trazida de volta a partir do que o servidor informa, com o
// botão de cancelar vivo, em vez de mandar o editor procurar um botão que não
// existe. Ela se solta sozinha pelo mesmo destravamento de 90 s do resto.
function adotarProcessamentoDoServidor(payload) {
    const nomes = {
        source_import: "Baixando a fonte",
        transcription: "Transcrevendo",
        cut: "Cortando",
        analysis: "Analisando o vídeo",
    };
    const decorridoServidor = Number(payload?.elapsed_seconds);
    // Já existe barra: ela é a mesma operação. Reiniciá-la zeraria o relógio que
    // o editor está lendo.
    if (run.active) return decorridoServidor;
    const titulo = nomes[payload?.operation] || "Processamento em andamento";
    if (payload?.job_id) state.activeJob = { ...(state.activeJob || {}), id: payload.job_id };
    beginRun(titulo, "", "Retomado a partir do servidor — use Cancelar se ele estiver travado.");
    const decorrido = Number(payload?.elapsed_seconds);
    if (Number.isFinite(decorrido) && decorrido > 0) {
        run.startedAt = Date.now() - decorrido * 1000;
        paintRun();
    }
    return decorrido;
}

async function parseJsonResponse(response, context = "servidor") {
    // 409 é a recusa deliberada do servidor quando já existe trabalho em
    // andamento. Tratada como erro genérico, ela chegava ao editor como uma
    // falha inexplicável — quando na verdade é a guarda funcionando.
    if (response.status === 409) {
        let payload = null;
        try {
            payload = JSON.parse(await response.text());
        } catch (erro) {
            payload = null;
        }
        const decorrido = adotarProcessamentoDoServidor(payload);
        const ha = Number.isFinite(decorrido) && decorrido > 0
            ? ` Está rodando há ${Math.floor(decorrido / 60)}min${String(decorrido % 60).padStart(2, "0")}s.`
            : "";
        throw new Error(
            `Já existe um processamento em andamento.${ha} A barra do topo voltou a aparecer: ` +
            "espere terminar, ou clique em Cancelar nela.",
        );
    }
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
    // A leitura da fonte só é possível com transcrição; assim que ela chega, o
    // painel deixa de estar vazio sem o editor precisar pedir.
    if (state.selectedVideo && transcription?.segments?.length) {
        window.setTimeout(() => refreshSourceReading(), 0);
        // Os blocos saem da mesma leitura. Esperar o ciclo de 60s para eles
        // aparecerem fazia o painel parecer quebrado.
        window.setTimeout(() => loadEditorialBlocks(), 0);
    }
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
        const label = quality.score !== undefined ? `${Number(quality.score).toFixed(0)}/100 · ${quality.quality || "revisar"}` : "qualidade não validada";
        const source = String(item.source || "automatic").replace(/_/g, " ");
        return `<article class="transcript-archive-item"><div><strong>${escapeHtml(sourceVideo)}</strong><small>${escapeHtml(source)} · ${escapeHtml(label)} · ${Number(item.quality?.segment_count || 0)} segmentos</small></div><div class="transcript-archive-links"><a class="btn btn-sm btn-outline" href="${escapeHtml(item.download_text || "#")}" target="_blank" rel="noopener">TXT</a><a class="btn btn-sm btn-outline" href="${escapeHtml(item.download_json || "#")}" target="_blank" rel="noopener">JSON</a></div></article>`;
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
        state.manualTranscriptVideo = state.selectedVideo || "pending-source";
        showSourceStatus(`Transcrição ${data.transcription.format} pronta: ${data.transcription.segment_count} segmentos. Ela será usada no próximo corte sem Whisper e poderá ser anexada ao próximo download.`, "success");
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

function artworkHeadlineHtml(headline, emphasis) {
    // O trecho em destaque vai dentro da frase, com fundo vermelho, e não numa
    // linha "Destaque sugerido:" embaixo dela. Na arte que o editor produz o
    // destaque é parte da leitura, não uma anotação sobre ela.
    const texto = escapeHtml(headline || "");
    const alvo = escapeHtml(emphasis || "");
    if (!alvo) return texto;
    const posicao = texto.toLowerCase().indexOf(alvo.toLowerCase());
    if (posicao < 0) return texto;
    return texto.slice(0, posicao)
        + `<mark class="artwork-mark">${texto.slice(posicao, posicao + alvo.length)}</mark>`
        + texto.slice(posicao + alvo.length);
}

function renderArtworkHeadline(suggestion, format, clipIndex = null) {
    const gancho = escapeHtml(suggestion.eyebrow || "");
    const alternativas = Array.isArray(suggestion.eyebrow_alternatives) ? suggestion.eyebrow_alternatives : [];
    const headline = String(suggestion.headline || "");
    const destaque = String(suggestion.emphasis || "");
    const corpo = artworkHeadlineHtml(headline, destaque);
    const modo = suggestion.mode === "citacao" ? "citação literal" : "leitura do trecho";
    const inicio = suggestion.source_interval && suggestion.source_interval.start_s;
    const marca = Number.isFinite(inicio) ? formatTimecode(inicio) : "";
    const fora = suggestion.within_preferred_limit === false;

    const trocas = alternativas.length > 1
        ? `<div class="artwork-hook-swap">${alternativas.map(item => `
            <button type="button" class="artwork-hook-option ${escapeHtml(item) === gancho ? "active" : ""}"
                data-hook="${encodeURIComponent(item)}">${escapeHtml(item)}</button>`).join("")}</div>`
        : "";

    return `<article class="artwork-suggestion-card ${format}" data-headline="${encodeURIComponent(headline)}" data-emphasis="${encodeURIComponent(destaque)}">
        <div class="artwork-canvas">
            <div class="artwork-band">
                ${gancho ? `<div class="artwork-eyebrow">${gancho}</div>` : ""}
                <div class="artwork-headline">${corpo}</div>
            </div>
            <div class="artwork-frame"><span class="material-icons-round">movie</span></div>
        </div>
        ${trocas}
        <div class="artwork-suggestion-footer">
            <span class="artwork-meta">
                <span class="artwork-mode ${suggestion.mode === "citacao" ? "literal" : ""}">${modo}</span>
                <span>${Number(suggestion.character_count || headline.length)} car${fora ? " · acima do ideal" : ""}</span>
                ${marca ? `<span>${marca}</span>` : ""}
            </span>
            <div>${artworkCopyButton(headline, "Copiar headline")}${artworkFeedbackButton(format, headline, clipIndex)}</div>
        </div>
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
    const aiRefinement = studio.ai_refinement || {};
    const aiStatus = String(aiRefinement.status || "");
    const aiProvider = String(aiRefinement.provider || "").trim();
    const aiReviewChip = aiRefinement.requested
        ? `<span class="artwork-review-chip ${aiStatus === "accepted" ? "safe" : "warning"}"><span class="material-icons-round">${aiStatus === "accepted" ? "auto_awesome" : "info"}</span>${escapeHtml(aiRefinement.message || (aiProvider ? `IA configurada · ${aiProvider}` : "IA solicitada"))}</span>`
        : "";
    const reviewChips = [
        aiReviewChip,
        flags.transcript_ends_incomplete ? '<span class="artwork-review-chip warning"><span class="material-icons-round">pending</span>final da transcrição incompleto</span>' : "",
        flags.needs_fact_review ? '<span class="artwork-review-chip"><span class="material-icons-round">fact_check</span>revisar afirmação factual</span>' : "",
        flags.needs_legal_review ? '<span class="artwork-review-chip legal"><span class="material-icons-round">gavel</span>revisar formulação jurídica</span>' : "",
        flags.source_not_punctuated ? '<span class="artwork-review-chip warning"><span class="material-icons-round">graphic_eq</span>a legenda não pontua: a leitura saiu das pausas, confira no áudio</span>' : "",
        flags.speaker_unconfirmed ? '<span class="artwork-review-chip warning"><span class="material-icons-round">person_off</span>ninguém confirmou quem fala: a arte sai sem atribuição</span>' : "",
    ].filter(Boolean).join("");
    const selectedFormat = studio.generated_format || recommended;
    const availableFormats = [selectedFormat].filter(format => ["vertical_916", "square_alfinetei"].includes(format));
    const formatCards = availableFormats.map(format => {
        const config = formats[format] || {};
        const suggestions = Array.isArray(config.suggestions) ? config.suggestions : [];
        return `<section class="artwork-format-result ${format === recommended ? "recommended" : ""}">
            <div class="artwork-format-result-head"><div><span class="artwork-format-kicker">${format === recommended ? "FORMATO RECOMENDADO" : "ALTERNATIVA"}</span><h4>${escapeHtml(config.label || artworkFormatLabels[format])}</h4></div><span class="artwork-limit">${escapeHtml(config.description || "")}</span></div>
            <div class="artwork-suggestion-grid">${suggestions.map(item => renderArtworkHeadline(item, format, clipIndex)).join("") || `<p class="artwork-empty">${escapeHtml(studio.recommendation_reason || "Sem alternativa disponível.")}</p>`}</div>
        </section>`;
    }).join("");
    // Esta atribuição foi apagada junto com o cartão do formato descartado na
    // 6.7: o script que removeu aquele bloco cortava linhas até achar uma que
    // terminasse em crase-ponto-e-vírgula, e essa linha era exatamente esta. O
    // resultado passou dois ciclos montando o HTML e jogando fora, com a tela em
    // branco e a mensagem verde de sucesso — e `node --check` passando, porque o
    // código continuava válido. Só não fazia nada.
    container.innerHTML = `<div class="headline-studio-result-summary">
<div><span class="artwork-format-kicker">LEITURA EDITORIAL</span><h4>${escapeHtml(artworkFormatLabels[recommended] || recommended)}</h4><p>${escapeHtml(studio.recommendation_reason || "")}</p></div><div class="artwork-analysis-metrics"><span>Tema: <strong>${escapeHtml(studio.topic || "geral")}</strong></span><span>Contexto: <strong>${Math.round(Number(studio.analysis?.context_completeness || 0))}/100</strong></span><span>Fonte: <strong>${studio.generation_source === "ai_refined" ? "IA + regras" : "regras editoriais"}</strong>${aiProvider ? ` · ${escapeHtml(aiProvider)}` : ""}</span><span>Preferência: <strong>${escapeHtml(learningLabel)}</strong></span></div></div><div class="artwork-review-chips">${reviewChips || '<span class="artwork-review-chip safe"><span class="material-icons-round">verified</span>sem alerta lexical automático</span>'}</div><div class="artwork-format-results">${formatCards}</div>`;
    container.style.display = "block";
    container.querySelectorAll(".artwork-copy-button").forEach(button => {
        button.addEventListener("click", () => copyToClipboard(decodeURIComponent(button.dataset.artworkCopy || "")));
    });
    container.querySelectorAll(".artwork-feedback-button").forEach(button => {
        button.addEventListener("click", () => saveArtworkFeedback(button));
    });
    // Trocar o gancho sem reescrever a headline. As alternativas já vêm do
    // gerador, e sem isto elas eram só um dado no objeto de resposta.
    container.querySelectorAll(".artwork-hook-option").forEach(button => {
        button.addEventListener("click", () => {
            const card = button.closest(".artwork-suggestion-card");
            if (!card) return;
            const gancho = decodeURIComponent(button.dataset.hook || "");
            const alvo = card.querySelector(".artwork-eyebrow");
            if (alvo) alvo.textContent = gancho;
            card.querySelectorAll(".artwork-hook-option").forEach(item => item.classList.remove("active"));
            button.classList.add("active");
            const headline = decodeURIComponent(card.dataset.headline || "");
            card.querySelectorAll(".artwork-copy-button").forEach(item => {
                item.dataset.artworkCopy = encodeURIComponent(`${gancho}\n${headline}`);
            });
        });
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
                project_id: state.selectedProjectId || state.currentProjectId || null,
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
            body: JSON.stringify({ url, ...getSourceDownloadAuthPayload() }),
        });
        const data = await parseJsonResponse(res, "Verificação da fonte");
        if (!res.ok || !data.success) throw new Error(data.error || "Fonte indisponível");
        state.sourceUrl = url;
        
        // Se conseguimos validar a URL remota, já podemos puxar os blocos do Acervo
        loadEditorialBlocks();
        
        const duration = data.source.duration ? ` — ${formatTime(data.source.duration)}` : "";
        showSourceStatus(`${data.source.title || "Fonte válida"}${duration}. Blocos analisados remotamente.`, "success");
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

function getSourceDownloadAuthPayload() {
    return {
        cookie_browser: document.getElementById("sourceCookieBrowser")?.value || "",
        user_agent: document.getElementById("sourceUserAgent")?.value?.trim() || "",
    };
}

async function transcribeSourceOnly() {
    if (state.sourceTranscriptionActive || state.sourceImportActive) return;
    const input = document.getElementById("sourceUrlInput");
    const url = normalizePublicUrlInput(input?.value);
    if (input && url) input.value = url;
    if (!url) {
        showSourceStatus("Informe uma URL pública.", "error");
        return;
    }
    const destination = await ensureSourceDirectory();
    if (!destination) {
        showSourceStatus("Transcrição cancelada: escolha uma pasta para salvar a fonte.", "warning");
        return;
    }
    const maxHeight = parseInt(document.getElementById("sourceMaxHeight")?.value || state.sourceMaxHeight || 1080, 10);
    setSourceTranscriptionButtons(true);
    showProgressBar();
    showSourceStatus("Download de áudio e transcrição iniciados; nenhum corte será gerado.", "");
    try {
        const res = await fetch("/api/source/transcribe", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                url,
                destination_dir: destination,
                max_height: maxHeight,
                media_type: "audio",
                transcription_source: document.getElementById("settingTranscriptionSource")?.value || "auto",
                ...getSourceDownloadAuthPayload(),
            }),
        });
        const data = await parseJsonResponse(res, "Transcrição por URL");
        if (!res.ok || !data.success) throw new Error(data.error || "Não foi possível iniciar a transcrição");
        state.sourceUrl = url;
        state.sourceTranscriptionJobId = data.job_id || null;
        state.activeJob = data.job_id ? { id: data.job_id, type: "source_transcription", state: data.state || "queued" } : null;
        showProcessingControls("Transcrição por URL (áudio) adicionada à fila persistente; nenhum corte será gerado.");
        addConsoleLog(`[Transcrição por URL] Job ${String(data.job_id || "").slice(0, 8)} iniciado com áudio, sem renderização.`, "info");
    } catch (error) {
        setSourceTranscriptionButtons(false);
        hideProgressBar();
        showSourceStatus(error.message, "error");
        showToast(error.message, "error");
    }
}

async function importSource(autoTranscribe = false) {
    if (state.sourceImportActive || state.sourceTranscriptionActive) return;
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
    const confirmedTranscript = autoTranscribe && state.manualTranscript?.segments?.length
        ? {
            segments: state.manualTranscript.segments,
            language: state.manualTranscript.language || "pt",
        }
        : null;
    const buttons = [
        document.getElementById("btnDownloadSource"),
        document.getElementById("btnDownloadTranscribeSource"),
    ].filter(Boolean);
    state.sourceImportActive = true;
    state.sourceMaxHeight = maxHeight;
    buttons.forEach(button => { button.disabled = true; button.classList.add("loading"); });
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
                ...getSourceDownloadAuthPayload(),
            }),
        });
        const data = await parseJsonResponse(res, "Importação da fonte");
        if (!res.ok || !data.success) throw new Error(data.error || "Não foi possível iniciar a importação");
        state.sourceUrl = url;
        addConsoleLog(`[Fonte] Download iniciado em ${destination}, limite de qualidade ${maxHeight}p.`, "info");
        if (confirmedTranscript) addConsoleLog("[Transcrição manual] Será reutilizada após o download; Gemini e Whisper serão ignorados.", "success");
        else if (autoTranscribe) addConsoleLog("[Fonte] A transcrição será gerada após o download, apenas se não houver fonte manual confirmada.", "info");
    } catch (error) {
        hideProgressBar();
        showSourceStatus(error.message, "error");
        showToast(error.message, "error");
    } finally {
        state.sourceImportActive = false;
        buttons.forEach(button => { button.disabled = false; button.classList.remove("loading"); });
    }
}

document.getElementById("btnDownloadSource")?.addEventListener("click", () => importSource(false));
document.getElementById("btnTranscribeSource")?.addEventListener("click", transcribeSourceOnly);
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
    if (s.render_preset) document.getElementById("settingRenderPreset").value = s.render_preset;
    if (s.editorial_profile) document.getElementById("settingEditorialProfile").value = s.editorial_profile;
    if (s.editorial_focus) document.getElementById("settingEditorialFocus").value = s.editorial_focus;
    if (s.min_silence_duration != null) {
        document.getElementById("settingSilenceDuration").value = s.min_silence_duration;
        document.getElementById("silenceValue").textContent = s.min_silence_duration + "s";
    }
    if (s.language) document.getElementById("settingLanguage").value = s.language;
    if (s.transcription_source) document.getElementById("settingTranscriptionSource").value = s.transcription_source;
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
    const sourceCookieBrowser = document.getElementById("sourceCookieBrowser");
    if (sourceCookieBrowser && typeof s.source_cookie_browser === "string") {
        sourceCookieBrowser.value = s.source_cookie_browser || "";
    }
    const sourceUserAgent = document.getElementById("sourceUserAgent");
    if (sourceUserAgent && typeof s.source_user_agent === "string") {
        sourceUserAgent.value = s.source_user_agent || "";
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
        render_preset: document.getElementById("settingRenderPreset").value,
        editorial_profile: document.getElementById("settingEditorialProfile").value,
        editorial_focus: document.getElementById("settingEditorialFocus").value,
        min_silence_duration: parseFloat(document.getElementById("settingSilenceDuration").value),
        padding: 0.25,
        language: document.getElementById("settingLanguage").value,
        transcription_source: document.getElementById("settingTranscriptionSource").value,
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
    showStage("source");
    aplicarCursor();
    aplicarSom();
    carregarVoz();
    startCampaignHubLocalStatusPolling();
    loadMediaFiles();
    loadTranscriptArchive();
    recoverActiveJobs();
    // Check Ollama status on load
    socket.emit("check_ollama");
});

// ─── Leitura da fonte ───
//
// O programa entendia o vídeo internamente — turnos do entrevistador, blocos
// temáticos, pontes pergunta-resposta — e não mostrava nada disso. O editor
// descobria o que ele tinha pensado abrindo um JSON depois do corte. Este painel
// existe para que a leitura venha antes, e para deixar explícito de onde ela vem:
// blocos revisados por uma pessoa e uma aproximação do Furia não merecem a mesma
// confiança.

function formatTimecode(seconds) {
    const total = Math.max(0, Math.round(Number(seconds) || 0));
    const minutes = Math.floor(total / 60);
    return `${String(minutes).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

const READING_ORIGINS = {
    acervo: { label: "Blocos revisados do Acervo", className: "reviewed" },
    furia_entrevista: { label: "Leitura do Furia · turnos da entrevista", className: "derived" },
    furia_temas: { label: "Leitura do Furia · blocos temáticos", className: "derived" },
    nenhuma: { label: "Sem leitura", className: "" },
};

function renderSourceReading(reading) {
    const empty = document.getElementById("readingEmpty");
    const summary = document.getElementById("readingSummary");
    const timeline = document.getElementById("readingTimeline");
    const list = document.getElementById("readingList");
    const origin = document.getElementById("readingOrigin");
    if (!list) return;

    state.sourceReading = reading || null;
    const units = Array.isArray(reading?.units) ? reading.units : [];
    list.innerHTML = "";
    timeline.innerHTML = "";

    if (!units.length) {
        empty.hidden = false;
        empty.textContent = reading
            ? "Nenhum trecho reconhecido. Carregue a transcrição desta fonte e leia de novo."
            : "Carregue um vídeo e uma transcrição para ver a leitura.";
        summary.hidden = true;
        timeline.hidden = true;
        origin.hidden = true;
        return;
    }

    empty.hidden = true;
    summary.hidden = false;
    timeline.hidden = false;

    const descriptor = READING_ORIGINS[reading.origin] || READING_ORIGINS.nenhuma;
    origin.hidden = false;
    origin.textContent = descriptor.label;
    origin.className = `reading-origin ${descriptor.className}`;

    document.getElementById("readingUnitCount").textContent = String(reading.unit_count || units.length);
    document.getElementById("readingCoverage").textContent = `${Math.round((reading.coverage_ratio || 0) * 100)}%`;
    document.getElementById("readingHighlights").textContent = String(reading.highlight_count || 0);

    const span = Number(reading.duration_s) || units[units.length - 1].end_s || 1;
    units.forEach((unit, index) => {
        const slice = document.createElement("div");
        slice.className = `reading-timeline-unit${(unit.highlights || []).length ? " has-highlight" : ""}`;
        slice.style.flexGrow = String(Math.max(0.001, (unit.duration_s || 0) / span));
        slice.dataset.index = String(index);
        slice.title = `${formatTimecode(unit.start_s)} – ${formatTimecode(unit.end_s)}`;
        slice.addEventListener("click", () => focusReadingUnit(index));
        timeline.appendChild(slice);

        list.appendChild(buildReadingUnit(unit, index));
    });
}

function buildReadingUnit(unit, index) {
    const item = document.createElement("li");
    item.className = "reading-unit";
    item.dataset.index = String(index);
    item.addEventListener("click", () => focusReadingUnit(index));

    const time = document.createElement("div");
    time.className = "reading-unit-time";
    time.innerHTML = `${formatTimecode(unit.start_s)}<small>dura ${formatTimecode(unit.duration_s)}</small>`;
    item.appendChild(time);

    const body = document.createElement("div");

    // O título só existe quando alguém escreveu um. Termos frequentes entram
    // como termos, nunca promovidos a título.
    if (unit.title) {
        const title = document.createElement("div");
        title.className = "reading-unit-title";
        title.textContent = unit.title;
        body.appendChild(title);
    }
    if (unit.question) {
        const question = document.createElement("p");
        question.className = "reading-unit-question";
        question.textContent = unit.question;
        body.appendChild(question);
    }
    if ((unit.subject_terms || []).length) {
        const terms = document.createElement("div");
        terms.className = "reading-unit-terms";
        unit.subject_terms.forEach((term) => {
            const chip = document.createElement("span");
            chip.textContent = term;
            terms.appendChild(chip);
        });
        body.appendChild(terms);
    }
    if ((unit.highlights || []).length) {
        const highlights = document.createElement("ul");
        highlights.className = "reading-unit-highlights";
        unit.highlights.slice(0, 4).forEach((highlight) => {
            const line = document.createElement("li");
            line.innerHTML = `<b>${formatTimecode(highlight.start_s)}</b>`;
            line.appendChild(document.createTextNode(highlight.text || ""));
            highlights.appendChild(line);
        });
        body.appendChild(highlights);
    }

    const flags = document.createElement("div");
    flags.className = "reading-unit-flags";
    if (unit.renan_speaking === false) {
        const flag = document.createElement("em");
        flag.className = "warn";
        flag.textContent = "Renan não é quem fala aqui";
        flags.appendChild(flag);
    }
    if (unit.needs_context) {
        const flag = document.createElement("em");
        flag.className = "warn";
        flag.textContent = "precisa de contexto";
        flags.appendChild(flag);
    }
    (unit.risk_flags || []).forEach((risk) => {
        const flag = document.createElement("em");
        flag.textContent = risk;
        flags.appendChild(flag);
    });
    if (Number(unit.possible_cuts) > 0) {
        const flag = document.createElement("em");
        flag.textContent = `${unit.possible_cuts} corte(s) possível(is)`;
        flags.appendChild(flag);
    }
    if (flags.children.length) body.appendChild(flags);

    item.appendChild(body);
    return item;
}

function focusReadingUnit(index) {
    const unit = state.sourceReading?.units?.[index];
    if (!unit) return;
    document.querySelectorAll(".reading-unit, .reading-timeline-unit").forEach((node) => {
        node.classList.toggle("active", node.dataset.index === String(index));
    });
    
    const video = document.getElementById("videoPreview");
    const dock = document.getElementById("playerDock");
    if (video && dock && Number.isFinite(Number(unit.start_s))) {
        if (!dock.classList.contains("is-open") && state.selectedVideo) {
            showVideoPreview(state.selectedVideo);
        }
        if (video.readyState >= 1) {
            video.currentTime = Number(unit.start_s);
            video.play().catch(() => {});
        } else {
            video.addEventListener('loadedmetadata', () => {
                video.currentTime = Number(unit.start_s);
                video.play().catch(() => {});
            }, { once: true });
        }
    }
}

async function refreshSourceReading() {
    if (!state.selectedVideo) {
        showToast("Selecione um vídeo antes de ler a fonte.", "warning");
        return;
    }
    const button = document.getElementById("btnRefreshReading");
    if (button) button.disabled = true;
    try {
        const response = await fetch("/api/source/reading", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                video_path: state.selectedVideo,
                segments: state.manualTranscript?.segments || [],
            }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "Não foi possível ler a fonte.");
        renderSourceReading(payload);
    } catch (error) {
        showToast(error.message || "Não foi possível ler a fonte.", "error");
    } finally {
        if (button) button.disabled = false;
    }
}

async function importAcervoBlocks(file) {
    if (!file) return;
    if (!state.selectedVideo) {
        showToast("Selecione o vídeo correspondente antes de importar os blocos.", "warning");
        return;
    }
    try {
        const blocks = JSON.parse(await file.text());
        const response = await fetch("/api/acervo/import", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ video_path: state.selectedVideo, blocks }),
        });
        const payload = await response.json();
        if (!response.ok || payload.success === false) throw new Error(payload.error || "Importação recusada.");
        showToast(`${payload.blocks} bloco(s) do Acervo vinculados a este vídeo.`, "success");
        addConsoleLog(`[Acervo] ${payload.blocks} blocos revisados importados para esta fonte; as fronteiras passam a vir deles.`, "success");
        await refreshSourceReading();
    } catch (error) {
        showToast(error.message || "Não foi possível importar os blocos.", "error");
    }
}

document.getElementById("btnRefreshReading")?.addEventListener("click", refreshSourceReading);
document.getElementById("btnImportAcervo")?.addEventListener("click", () => document.getElementById("acervoImportInput")?.click());
document.getElementById("acervoImportInput")?.addEventListener("change", (event) => {
    importAcervoBlocks(event.target.files?.[0]);
    event.target.value = "";
});
