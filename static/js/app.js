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

// ─── Ollama Status ───

socket.on("ollama_status", (data) => {
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

    if (data.connected) {
        dot.classList.add("connected");
        label.textContent = "Ollama Conectado";
        modeIndicator.classList.add("llm-mode");
        modeIcon.textContent = "psychology";
        modeLabel.textContent = "IA Inteligente";
        if (data.model_available) {
            label.textContent = `Ollama Conectado (${data.model})`;
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
            showToast("Transcricao concluida!", "success");
            break;
        case "cut_complete":
            hideProgressBar();
            state.selectionSource = data.data.selection_source || "nlp";
            state.outputFolder = data.data.output_folder || "";
            showToast(`${data.data.clips.length} clips gerados e ranqueados!`, "success");
            displayResults(data.data.clips);
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
            state.outputFolder = data.data.output_dir || "";
            showToast(`Processo completo! ${data.data.total_clips} clips gerados e ranqueados.`, "success");
            displayResults(data.data.clips);
            updateOpenFolderButton(state.outputFolder);
            loadMediaFiles();
            break;
        case "error":
            hideProgressBar();
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

    // Keep max 200 lines
    while (console_el.children.length > 200) {
        console_el.removeChild(console_el.firstChild);
    }
}

function showProgressBar() {
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

function hideProgressBar() {
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
            selectVideo(file);
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

function selectVideo(item) {
    state.selectedVideo = item.path;
    state.selectedVideoName = item.name;

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
    event.currentTarget.classList.add("selected");

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
    source.src = `/workspace/${item.path}`;
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
    await fetch("/api/process/cut", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            video_path: state.selectedVideo,
            face_tracking: true,
            user_context: userContext,
            video_genre: videoGenre,
        }),
    });
});

document.getElementById("actionSeo").querySelector(".btn-action").addEventListener("click", async () => {
    showToast("Use o 'Processo Completo' ou gere SEO a partir de um clip nos resultados", "info");
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
    await fetch("/api/process/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            video_path: state.selectedVideo,
            output_dir: state.outputDir || "",
            user_context: userContext,
            video_genre: videoGenreComplete,
        }),
    });
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

document.getElementById("btnChangeOutputDir").addEventListener("click", () => {
    document.getElementById("outputDirInput").value = state.outputDir || "";
    document.getElementById("outputDirModal").classList.add("active");
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

function displayResults(clips) {
    const section = document.getElementById("resultsSection");
    const grid = document.getElementById("resultsGrid");
    const summary = document.getElementById("resultsSummary");
    const searchBar = document.getElementById("transcriptSearchBar");
    section.style.display = "block";
    grid.innerHTML = "";

    state.clips = clips;

    // Show search bar
    if (searchBar) searchBar.style.display = "flex";

    // Summary
    const avgScore = clips.reduce((a, c) => a + (c.viral_score || 0), 0) / clips.length;
    const highScoreCount = clips.filter(c => c.viral_score >= 70).length;
    const source = clips.length > 0 && clips[0].source === "llm" ? "IA" : "NLP";
    summary.textContent = `${clips.length} clips | Media: ${avgScore.toFixed(0)} | ${highScoreCount} com alto potencial | via ${source}`;

    // Sort by viral score (highest first)
    const sorted = [...clips].sort((a, b) => (b.viral_score || 0) - (a.viral_score || 0));

    sorted.forEach((clip, i) => {
        const originalIndex = clips.indexOf(clip);
        const rank = clip.rank || (i + 1);
        const scoreClass = clip.viral_score >= 70 ? "high" : clip.viral_score >= 40 ? "medium" : "low";
        const seo = clip.seo || {};
        const titles = seo.titles || [];
        const tags = seo.tags || [];
        const hashtags = seo.hashtags || [];
        const breakdown = clip.breakdown || {};
        const clipSource = clip.source || "nlp";
        const sourceLabel = clipSource === "llm" ? "IA" : "NLP";
        const sourceClass = clipSource === "llm" ? "source-llm" : "source-nlp";
        const transcriptId = `transcript-${originalIndex}`;

        // Grade color helper
        const gradeColor = (grade) => {
            if (grade === 'A') return '#22c55e';
            if (grade === 'B') return '#f59e0b';
            return '#ef4444';
        };

        const card = document.createElement("div");
        card.className = "result-card";
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
            </div>

            ${clip.title ? `<div class="result-title">${clip.title}</div>` : ''}

            <div class="result-video-preview">
                <video controls preload="metadata" poster="">
                    <source src="/workspace/${clip.subtitled_path || clip.path}" type="video/mp4">
                </video>
            </div>
            <div class="result-info">
                <div class="result-duration">
                    <span class="material-icons-round" style="font-size:14px">schedule</span>
                    ${formatTime(clip.start)} - ${formatTime(clip.end)} (${clip.duration.toFixed(1)}s)
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

                <div class="result-text-preview">${clip.text ? clip.text.substring(0, 150) + (clip.text.length > 150 ? '...' : '') : "Sem transcricao"}</div>

                ${clip.text ? `
                <button class="btn-show-transcript" onclick="toggleTranscript('${transcriptId}')">
                    <span class="material-icons-round" style="font-size:14px">description</span>
                    Ver Transcricao
                </button>
                <div class="clip-transcript" id="${transcriptId}">
                    <div class="clip-transcript-content">${clip.text}</div>
                </div>` : ''}

                ${titles.length > 0 ? `
                <div class="result-seo">
                    <h5><span class="material-icons-round" style="font-size:14px">title</span> Titulos Sugeridos</h5>
                    ${titles.slice(0, 3).map(t => `<div class="seo-title" onclick="copyToClipboard(this.textContent)">${t}</div>`).join('')}
                </div>` : ''}

                ${tags.length > 0 ? `
                <div class="seo-tags">
                    ${tags.slice(0, 10).map(t => `<span class="seo-tag" onclick="copyToClipboard('${t}')">${t}</span>`).join('')}
                </div>` : ''}

                ${hashtags.length > 0 ? `
                <div class="seo-hashtags">
                    ${hashtags.slice(0, 8).map(h => `<span class="seo-hashtag">${h}</span>`).join('')}
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
            </div>`;

        grid.appendChild(card);
    });

    section.scrollIntoView({ behavior: "smooth" });
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
    if (source === "llm") {
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
        a.href = `/workspace/${path}`;
        a.download = path.split("/").pop();
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
    if (s.min_silence_duration != null) {
        document.getElementById("settingSilenceDuration").value = s.min_silence_duration;
        document.getElementById("silenceValue").textContent = s.min_silence_duration + "s";
    }
    if (s.language) document.getElementById("settingLanguage").value = s.language;
    if (s.ai_correction != null) {
        document.getElementById("settingAiCorrection").dataset.active = s.ai_correction;
    }
    if (s.ai_backend) {
        document.getElementById("settingAiBackend").value = s.ai_backend;
        updateAiConfigVisibility(s.ai_backend);
    }
    if (s.ollama_model) document.getElementById("settingOllamaModel").value = s.ollama_model;
    if (s.gemini_api_key) document.getElementById("settingGeminiKey").value = s.gemini_api_key;
    if (s.claude_api_key) document.getElementById("settingClaudeKey").value = s.claude_api_key;
    if (s.output_dir) {
        state.outputDir = s.output_dir;
        document.getElementById("outputDirText").textContent = s.output_dir || "workspace/exports (padrao)";
    }
}

function updateAiConfigVisibility(backend) {
    document.getElementById("ollamaConfig").style.display = backend === "ollama" ? "block" : "none";
    document.getElementById("geminiConfig").style.display = backend === "gemini" ? "block" : "none";
    document.getElementById("claudeConfig").style.display = backend === "claude" ? "block" : "none";

    const status = document.getElementById("aiStatus");
    const labels = { ollama: "Ollama local selecionado", gemini: "Google Gemini selecionado", claude: "Claude API selecionado" };
    status.querySelector("span:last-child").textContent = labels[backend] || backend;
}

document.getElementById("settingAiBackend").addEventListener("change", (e) => {
    updateAiConfigVisibility(e.target.value);
});

document.getElementById("btnSaveSettings").addEventListener("click", async () => {
    const settings = {
        whisper_model: document.getElementById("settingWhisperModel").value,
        cut_method: document.getElementById("settingCutMethod").value,
        cut_duration: parseInt(document.getElementById("settingCutDuration").value),
        min_silence_duration: parseFloat(document.getElementById("settingSilenceDuration").value),
        padding: 0.25,
        language: document.getElementById("settingLanguage").value,
        ai_correction: document.getElementById("settingAiCorrection").dataset.active === "true",
        ai_backend: document.getElementById("settingAiBackend").value,
        ollama_model: document.getElementById("settingOllamaModel").value,
        gemini_api_key: document.getElementById("settingGeminiKey").value,
        claude_api_key: document.getElementById("settingClaudeKey").value,
        output_dir: state.outputDir,
    };

    try {
        const res = await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(settings),
        });
        if (res.ok) {
            showToast("Configuracoes salvas!", "success");
            state.settings = settings;
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
    // Check Ollama status on load
    socket.emit("check_ollama");
});
