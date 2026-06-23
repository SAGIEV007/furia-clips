// ═══════════════════════════════════════════════════
// FURIA CLIPS - Frontend Application
// ═══════════════════════════════════════════════════

const state = {
    selectedVideo: null,
    currentPath: "",
    settings: {},
    clips: [],
    connected: false,
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

// ─── Status Handlers ───

function handleStatusUpdate(data) {
    switch (data.status) {
        case "silence_complete":
            hideProgressBar();
            showToast("Silencio removido com sucesso!", "success");
            loadFiles(state.currentPath);
            break;
        case "transcribe_complete":
            hideProgressBar();
            showToast("Transcricao concluida!", "success");
            break;
        case "cut_complete":
            hideProgressBar();
            showToast(`${data.data.clips.length} clips gerados!`, "success");
            displayResults(data.data.clips);
            break;
        case "subtitles_complete":
            hideProgressBar();
            showToast("Legendas geradas com sucesso!", "success");
            loadFiles(state.currentPath);
            break;
        case "seo_complete":
            hideProgressBar();
            showToast("Conteudo SEO gerado!", "success");
            break;
        case "thumbnail_complete":
            hideProgressBar();
            showToast("Thumbnail gerada!", "success");
            loadFiles(state.currentPath);
            break;
        case "complete_done":
            hideProgressBar();
            showToast(`Processo completo! ${data.data.total_clips} clips gerados.`, "success");
            displayResults(data.data.clips);
            loadFiles(state.currentPath);
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
}

function showProgressBar() {
    const container = document.getElementById("progressBarContainer");
    const bar = document.getElementById("progressBar");
    container.style.display = "block";
    // Animate progress bar continuously
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

// ─── File Manager ───

async function loadFiles(path = "") {
    try {
        const res = await fetch(`/api/files?path=${encodeURIComponent(path)}`);
        const data = await res.json();
        state.currentPath = data.current_path;
        renderFiles(data.items);
        renderBreadcrumb(data.current_path);
    } catch (e) {
        addConsoleLog(`[Erro] Falha ao carregar arquivos: ${e.message}`, "error");
    }
}

function renderFiles(items) {
    const grid = document.getElementById("fileGrid");
    grid.innerHTML = "";

    if (items.length === 0) {
        grid.innerHTML = `
            <div class="file-grid-empty">
                <span class="material-icons-round">cloud_upload</span>
                <p>Nenhum arquivo encontrado. Importe um video para comecar!</p>
            </div>`;
        return;
    }

    items.forEach(item => {
        const el = document.createElement("div");
        el.className = "file-item" + (state.selectedVideo === item.path ? " selected" : "");

        if (item.is_dir) {
            el.innerHTML = `
                <div class="file-icon folder">
                    <span class="material-icons-round">folder</span>
                </div>
                <span class="file-name">${item.name}</span>`;
            el.addEventListener("click", () => loadFiles(item.path));
        } else {
            const icon = item.is_video ? "movie" : "description";
            const iconClass = item.is_video ? "video" : "folder";
            el.innerHTML = `
                <div class="file-icon ${iconClass}">
                    <span class="material-icons-round">${icon}</span>
                </div>
                <span class="file-name">${item.name}</span>
                <span class="file-size">${item.size_human}</span>
                ${item.is_video ? '<span class="file-badge">MP4</span>' : ''}`;

            if (item.is_video) {
                el.addEventListener("click", () => selectVideo(item));
            }
        }

        grid.appendChild(el);
    });
}

function renderBreadcrumb(path) {
    const bc = document.getElementById("breadcrumb");
    let html = `<span class="material-icons-round">home</span>
                <span class="breadcrumb-item${!path ? ' active' : ''}" data-path="" onclick="loadFiles('')">Workspace</span>`;

    if (path) {
        const parts = path.split("/");
        let accumulated = "";
        parts.forEach((part, i) => {
            accumulated += (accumulated ? "/" : "") + part;
            const isLast = i === parts.length - 1;
            html += `<span class="breadcrumb-separator">/</span>
                     <span class="breadcrumb-item${isLast ? ' active' : ''}"
                           data-path="${accumulated}"
                           onclick="loadFiles('${accumulated}')">${part}</span>`;
        });
    }

    bc.innerHTML = html;
}

function selectVideo(item) {
    state.selectedVideo = item.path;
    document.querySelectorAll(".file-item").forEach(el => el.classList.remove("selected"));
    event.currentTarget.classList.add("selected");

    const info = document.getElementById("selectedVideoInfo");
    info.className = "selected-video has-video";
    info.innerHTML = `
        <div class="video-info-selected">
            <span class="video-name">${item.name}</span>
            <span class="video-meta">${item.size_human}</span>
            <button class="btn btn-sm btn-deselect" onclick="deselectVideo()">
                <span class="material-icons-round" style="font-size:14px">close</span> Remover selecao
            </button>
        </div>`;

    addConsoleLog(`[Sistema] Video selecionado: ${item.name}`, "info");
}

function deselectVideo() {
    state.selectedVideo = null;
    document.querySelectorAll(".file-item").forEach(el => el.classList.remove("selected"));
    const info = document.getElementById("selectedVideoInfo");
    info.className = "selected-video";
    info.innerHTML = `
        <div class="no-video">
            <span class="material-icons-round">videocam_off</span>
            <p>Nenhum video selecionado</p>
        </div>`;
}

// ─── File Upload ───

document.getElementById("btnImport").addEventListener("click", () => {
    document.getElementById("fileInput").click();
});

document.getElementById("fileInput").addEventListener("change", async (e) => {
    const files = e.target.files;
    if (!files.length) return;

    for (const file of files) {
        await uploadFile(file);
    }
    loadFiles(state.currentPath);
    e.target.value = "";
});

async function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("path", state.currentPath || "uploads");

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

// Drag and drop
const fileExplorer = document.getElementById("fileExplorerSection");
fileExplorer.addEventListener("dragover", (e) => {
    e.preventDefault();
    fileExplorer.classList.add("drag-over");
});
fileExplorer.addEventListener("dragleave", () => {
    fileExplorer.classList.remove("drag-over");
});
fileExplorer.addEventListener("drop", async (e) => {
    e.preventDefault();
    fileExplorer.classList.remove("drag-over");
    const files = e.dataTransfer.files;
    for (const file of files) {
        await uploadFile(file);
    }
    loadFiles(state.currentPath);
});

// ─── New Folder ───

document.getElementById("btnNewFolder").addEventListener("click", async () => {
    const name = prompt("Nome da nova pasta:");
    if (!name) return;

    try {
        const res = await fetch("/api/files/mkdir", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, parent: state.currentPath }),
        });
        const data = await res.json();
        if (data.success) {
            loadFiles(state.currentPath);
            showToast("Pasta criada!", "success");
        }
    } catch (e) {
        showToast("Erro ao criar pasta", "error");
    }
});

// Refresh
document.getElementById("btnRefresh").addEventListener("click", () => {
    loadFiles(state.currentPath);
});

// ─── Actions ───

function requireVideo() {
    if (!state.selectedVideo) {
        showToast("Selecione um video primeiro!", "warning");
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
    addConsoleLog("[Acao] Iniciando corte de shorts...", "info");
    await fetch("/api/process/cut", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_path: state.selectedVideo, face_tracking: true }),
    });
});

document.getElementById("actionSeo").querySelector(".btn-action").addEventListener("click", async () => {
    showToast("Selecione um clip nos resultados para gerar SEO", "info");
});

document.getElementById("actionThumbnail").querySelector(".btn-action").addEventListener("click", () => {
    if (!requireVideo()) return;
    openThumbnailModal();
});

document.getElementById("actionComplete").querySelector(".btn-action").addEventListener("click", async () => {
    if (!requireVideo()) return;
    if (!confirm("Executar o pipeline completo? Isso pode demorar alguns minutos dependendo do tamanho do video.")) return;
    addConsoleLog("[Acao] Iniciando processo completo...", "info");
    await fetch("/api/process/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_path: state.selectedVideo }),
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
                    justify-content:center; padding:16px; background:#111;">
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

// ─── Results Display ───

function displayResults(clips) {
    const section = document.getElementById("resultsSection");
    const grid = document.getElementById("resultsGrid");
    section.style.display = "block";
    grid.innerHTML = "";

    state.clips = clips;

    clips.forEach((clip, i) => {
        const scoreClass = clip.viral_score >= 70 ? "high" : clip.viral_score >= 40 ? "medium" : "low";
        const seo = clip.seo || {};
        const titles = seo.titles || [];
        const tags = seo.tags || [];
        const hashtags = seo.hashtags || [];

        const card = document.createElement("div");
        card.className = "result-card";
        card.innerHTML = `
            <div class="result-video-preview">
                <video controls preload="metadata">
                    <source src="/workspace/${clip.subtitled_path || clip.path}" type="video/mp4">
                </video>
            </div>
            <div class="result-info">
                <div class="result-header">
                    <span class="result-clip-number">Clip #${i + 1}</span>
                    <div style="display:flex; align-items:center; gap:8px;">
                        ${clip.has_hook ? '<span class="hook-badge"><span class="material-icons-round" style="font-size:12px">flash_on</span> Gancho</span>' : ''}
                        <span class="viral-score ${scoreClass}">
                            <span class="material-icons-round">trending_up</span>
                            ${clip.viral_score}
                        </span>
                    </div>
                </div>
                <div class="result-duration">
                    ${formatTime(clip.start)} - ${formatTime(clip.end)} (${clip.duration.toFixed(1)}s)
                </div>
                <div class="result-text">${clip.text || "Sem transcricao"}</div>

                ${titles.length > 0 ? `
                <div class="result-seo">
                    <h5>Titulos Sugeridos</h5>
                    ${titles.slice(0, 3).map(t => `<div class="seo-title" onclick="copyToClipboard('${escapeHtml(t)}')">${t}</div>`).join('')}
                </div>` : ''}

                ${tags.length > 0 ? `
                <div class="seo-tags">
                    ${tags.slice(0, 8).map(t => `<span class="seo-tag">${t}</span>`).join('')}
                </div>` : ''}

                <div class="result-actions">
                    <button class="btn btn-sm btn-primary" onclick="downloadClip(${i})">
                        <span class="material-icons-round">download</span> Exportar
                    </button>
                    <button class="btn btn-sm" onclick="generateClipSeo(${i})">
                        <span class="material-icons-round">auto_awesome</span> SEO
                    </button>
                    <button class="btn btn-sm" onclick="generateClipThumb(${i})">
                        <span class="material-icons-round">image</span> Capa
                    </button>
                </div>
            </div>`;

        grid.appendChild(card);
    });

    section.scrollIntoView({ behavior: "smooth" });
}

function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

function escapeHtml(str) {
    return str.replace(/'/g, "\\'").replace(/"/g, "&quot;");
}

function downloadClip(index) {
    const clip = state.clips[index];
    if (clip) {
        const path = clip.subtitled_path || clip.path;
        window.open(`/workspace/${path}`, "_blank");
    }
}

async function generateClipSeo(index) {
    const clip = state.clips[index];
    if (!clip || !clip.text) {
        showToast("Clip sem transcricao para gerar SEO", "warning");
        return;
    }
    addConsoleLog(`[SEO] Gerando conteudo para Clip #${index + 1}...`, "info");
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

    addConsoleLog(`[Thumbnail] Gerando capa para Clip #${index + 1}...`, "info");
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
        showToast("Copiado para a area de transferencia!", "success");
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
    if (s.padding != null) {
        document.getElementById("settingPadding").value = s.padding;
        document.getElementById("paddingValue").textContent = s.padding + "s";
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
        padding: parseFloat(document.getElementById("settingPadding").value),
        language: document.getElementById("settingLanguage").value,
        ai_correction: document.getElementById("settingAiCorrection").dataset.active === "true",
        ai_backend: document.getElementById("settingAiBackend").value,
        ollama_model: document.getElementById("settingOllamaModel").value,
        gemini_api_key: document.getElementById("settingGeminiKey").value,
        claude_api_key: document.getElementById("settingClaudeKey").value,
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
document.getElementById("settingPadding").addEventListener("input", (e) => {
    document.getElementById("paddingValue").textContent = e.target.value + "s";
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
        <span class="material-icons-round" style="font-size:18px; color:var(--${type})">${icons[type]}</span>
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
});

// ─── Init ───

document.addEventListener("DOMContentLoaded", () => {
    loadSettings();
    loadFiles();
});
