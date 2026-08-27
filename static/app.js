(() => {
  "use strict";

  const state = { projects: [], activeProject: null, activeProjectId: null, activeClipId: null, activeJobId: null, screen: "overview", projectTab: "analyze", filter: "all", sort: "score", projectSort: "recent", busy: false, exporting: new Set(), currentJobId: null, cancelRequested: false, jobPollToken: 0, queuePollTimer: null, queuePollBusy: false, queuePollFailures: 0, projectsRequest: null, consoleLines: [], consoleSeen: new Set(), consoleOpen: false, consoleDismissed: false, consoleJobId: null, settings: {}, studioStatus: null };
  try {
    state.filter = localStorage.getItem("furia-filter") || state.filter;
    state.sort = localStorage.getItem("furia-sort") || state.sort;
    state.projectSort = localStorage.getItem("furia-project-sort") || state.projectSort;
    state.projectTab = localStorage.getItem("furia-project-tab") || state.projectTab;
    state.activeProjectId = localStorage.getItem("furia-active-project") || null;
    state.consoleOpen = localStorage.getItem("furia-console-open") === "1";
  } catch (_) {}
  function rememberActiveProject(projectId) {
    state.activeProjectId = projectId == null ? null : String(projectId);
    try {
      if (state.activeProjectId) localStorage.setItem("furia-active-project", state.activeProjectId);
      else localStorage.removeItem("furia-active-project");
    } catch (_) {}
  }
  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  let activeWindowDrag = null;
  const windowRegistry = new Map();

  function getWindowTray() {
    let tray = $("#windowTray");
    if (!tray) {
      tray = document.createElement("div");
      tray.id = "windowTray";
      tray.className = "window-tray";
      tray.setAttribute("aria-label", "Janelas minimizadas");
      document.body.appendChild(tray);
    }
    return tray;
  }

  function readWindowPosition(id) {
    try { return JSON.parse(localStorage.getItem(`furia-window:${id}`) || "null"); } catch (_) { return null; }
  }

  function saveWindowPosition(id, x, y) {
    try { localStorage.setItem(`furia-window:${id}`, JSON.stringify({ x: Math.round(x), y: Math.round(y) })); } catch (_) {}
  }

  function focusWindow(element) {
    const family = element.closest(".screen") || document;
    $$(".window.wm-focused", family).forEach((item) => item.classList.remove("wm-focused"));
    element.classList.add("wm-focused");
    const siblings = $$(".window.wm-ready", family);
    siblings.forEach((item, index) => { item.style.setProperty("--wm-z", String(10 + index)); });
    element.style.setProperty("--wm-z", "60");
  }

  function setWindowHidden(element, hidden) {
    element.classList.toggle("wm-hidden", hidden);
    const item = windowRegistry.get(element.dataset.windowId);
    if (item) item.trayButton.classList.toggle("is-open", !hidden);
  }

  function registerWindow(element, index) {
    if (!element || element.dataset.wmReady) return;
    const screen = element.closest(".screen")?.id || "dynamic";
    const type = ["source-window", "signal-window", "queue-window", "editor-window", "review-stage", "review-inspector", "notes-window"].find((name) => element.classList.contains(name)) || "window";
    const id = `${screen}:${type}:${index}`;
    element.dataset.windowId = id;
    element.dataset.wmReady = "1";
    element.classList.add("wm-ready");
    const saved = readWindowPosition(id);
    if (saved && window.matchMedia("(min-width: 781px)").matches) {
      element.style.setProperty("--wm-x", `${saved.x}px`);
      element.style.setProperty("--wm-y", `${saved.y}px`);
    }
    const bar = $(".window-bar", element);
    if (!bar) return;
    bar.classList.add("wm-drag-handle");
    const controls = document.createElement("span");
    controls.className = "wm-controls";
    controls.innerHTML = `<button type="button" data-wm="minimize" title="Minimizar">−</button><button type="button" data-wm="close" title="Fechar">×</button>`;
    bar.appendChild(controls);
    const trayButton = document.createElement("button");
    trayButton.type = "button";
    trayButton.className = "window-tray-item is-open";
    trayButton.textContent = bar.querySelector("span")?.textContent?.trim() || type;
    trayButton.addEventListener("click", () => { setWindowHidden(element, false); focusWindow(element); });
    getWindowTray().appendChild(trayButton);
    windowRegistry.set(id, { element, trayButton });
    controls.addEventListener("click", (event) => {
      const action = event.target.closest("[data-wm]")?.dataset.wm;
      if (!action) return;
      event.stopPropagation();
      setWindowHidden(element, true);
    });
    bar.addEventListener("pointerdown", (event) => {
      if (event.target.closest("button")) return;
      if (!window.matchMedia("(min-width: 781px)").matches) return;
      focusWindow(element);
      activeWindowDrag = { element, pointerId: event.pointerId, startX: event.clientX, startY: event.clientY, x: Number.parseFloat(getComputedStyle(element).getPropertyValue("--wm-x")) || 0, y: Number.parseFloat(getComputedStyle(element).getPropertyValue("--wm-y")) || 0 };
      element.classList.add("wm-dragging");
      bar.setPointerCapture?.(event.pointerId);
    });
    element.addEventListener("pointerdown", () => focusWindow(element));
    element.addEventListener("pointermove", (event) => {
      if (!activeWindowDrag || activeWindowDrag.element !== element || activeWindowDrag.pointerId !== event.pointerId) return;
      const x = activeWindowDrag.x + event.clientX - activeWindowDrag.startX;
      const y = activeWindowDrag.y + event.clientY - activeWindowDrag.startY;
      element.style.setProperty("--wm-x", `${x}px`);
      element.style.setProperty("--wm-y", `${y}px`);
    });
    element.addEventListener("pointerup", (event) => {
      if (!activeWindowDrag || activeWindowDrag.element !== element) return;
      const x = Number.parseFloat(element.style.getPropertyValue("--wm-x")) || 0;
      const y = Number.parseFloat(element.style.getPropertyValue("--wm-y")) || 0;
      saveWindowPosition(id, x, y);
      activeWindowDrag = null;
      element.classList.remove("wm-dragging");
    });
  }

  function unregisterWindow(id, item) {
    item.trayButton.remove();
    item.element.querySelector(".wm-controls")?.remove();
    item.element.classList.remove("wm-ready", "wm-focused", "wm-hidden", "wm-dragging");
    item.element.removeAttribute("data-wm-ready");
    item.element.removeAttribute("data-window-id");
    windowRegistry.delete(id);
  }

  function initWindowManager(scope = document) {
    for (const [id, item] of windowRegistry.entries()) {
      const screen = item.element.closest(".screen");
      if (!document.contains(item.element) || (screen && !screen.classList.contains("is-visible"))) unregisterWindow(id, item);
    }
    const root = scope === document ? $(".screen.is-visible") || document : scope;
    const windows = $$(".window", root).filter((element) => {
      const screen = element.closest(".screen");
      return !element.closest("#importModal") && (!screen || screen.classList.contains("is-visible"));
    });
    windows.forEach((element, index) => registerWindow(element, index));
  }

  document.addEventListener("pointerup", () => {
    if (!activeWindowDrag) return;
    activeWindowDrag.element.classList.remove("wm-dragging");
    activeWindowDrag = null;
  });

  async function api(url, options = {}) {
    const response = await fetch(url, options);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || `Não foi possível concluir a operação (${response.status}).`);
    return payload;
  }

  function toast(message, kind = "default") {
    const element = $("#toast");
    if (!element) return;
    element.textContent = message;
    element.className = `toast is-visible${kind === "error" ? " is-error" : kind === "success" ? " is-success" : ""}`;
    window.clearTimeout(toast.timer);
    toast.timer = window.setTimeout(() => { element.className = "toast"; }, 4200);
  }

  function formatDuration(seconds = 0) {
    const value = Number(seconds) || 0;
    return `${Math.floor(value / 60)}:${Math.floor(value % 60).toString().padStart(2, "0")}`;
  }

  function setConsoleOpen(open) {
    state.consoleOpen = Boolean(open);
    const drawer = $("#consoleDrawer");
    drawer?.classList.toggle("is-open", state.consoleOpen);
    $("#consoleIndicator")?.classList.toggle("is-active", state.consoleOpen);
    try { localStorage.setItem("furia-console-open", state.consoleOpen ? "1" : "0"); } catch (_) {}
    if (state.consoleOpen && !state.consoleLines.length && !state.consoleDismissed) hydrateConsoleFromLatestJob();
  }

  function renderConsole() {
    const target = $("#consoleLines");
    if (!target) return;
    target.innerHTML = state.consoleLines.length ? state.consoleLines.slice(-120).map((line) => `<div class="console-line console-${escapeHtml(line.level || "info")}"><time>${escapeHtml(line.time || "")}</time><b>${escapeHtml(line.stage || "LOCAL")}</b><span>${escapeHtml(line.message || "")}</span></div>`).join("") : `<div class="console-empty">Quando você iniciar uma ação, cada etapa ficará registrada aqui.</div>`;
    target.scrollTop = target.scrollHeight;
    const last = state.consoleLines[state.consoleLines.length - 1];
    if (last) $("#consoleSummary").textContent = last.message || "Execução local em andamento.";
    const cancelButton = $("#btnCancelJob");
    if (cancelButton) {
      cancelButton.disabled = !state.currentJobId || state.cancelRequested;
      cancelButton.textContent = state.cancelRequested ? "Cancelando…" : "Cancelar job";
    }
  }

  async function cancelCurrentJob() {
    const jobId = state.currentJobId;
    if (!jobId || state.cancelRequested) return;
    state.cancelRequested = true;
    renderConsole();
    appendConsole(`Solicitando cancelamento do job ${jobId}.`, "warning", "fila", `${jobId}:cancel-request`);
    try {
      await api(`/api/jobs/${jobId}/cancel`, { method: "POST" });
      toast("Cancelamento solicitado. O Console mostrará o encerramento.");
    } catch (error) {
      state.cancelRequested = false;
      appendConsole(`Não foi possível cancelar o job: ${error.message}`, "error", "fila", `${jobId}:cancel-error`);
      toast(error.message, "error");
      renderConsole();
    }
  }

  function appendConsole(message, level = "info", stage = "local", key = "") {
    const text = String(message || "").trim();
    if (!text) return;
    const identity = key || `${stage}:${level}:${text}`;
    if (state.consoleSeen.has(identity)) return;
    state.consoleSeen.add(identity);
    state.consoleDismissed = false;
    state.consoleLines.push({ message: text, level, stage: String(stage || "local").toUpperCase(), time: new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) });
    if (state.consoleLines.length > 160) state.consoleLines = state.consoleLines.slice(-160);
    setConsoleOpen(true);
    renderConsole();
  }

  function clearConsole() {
    state.consoleLines = [];
    state.consoleSeen = new Set();
    state.consoleDismissed = true;
    renderConsole();
    $("#consoleTitle").textContent = "Nenhuma tarefa selecionada";
    $("#consoleSummary").textContent = "As etapas do Whisper, Furia 1, captions e exportação aparecem aqui.";
  }

  function renderDependencyStatus(targetId, good, title, detail) {
    const target = $(`#${targetId}`);
    if (!target) return;
    target.classList.toggle("is-good", Boolean(good));
    target.classList.toggle("is-warn", !good);
    target.innerHTML = `<span class="status-dot"></span><div><strong>${escapeHtml(title)}</strong><small>${escapeHtml(detail)}</small></div>`;
  }

  async function refreshStudioStatus() {
    try {
      const status = await api("/api/studio/status");
      state.studioStatus = status;
      const whisper = status.whisper || {};
      const whisperEngines = [whisper.faster_whisper_installed ? "faster-whisper" : "", whisper.openai_whisper_installed ? "openai-whisper" : ""].filter(Boolean);
      renderDependencyStatus("whisperStatus", whisper.available, whisper.available ? "Whisper local disponível" : "Whisper local não instalado", whisper.available ? `${whisperEngines.join(" + ")} · modelo ${whisper.model} · dispositivo ${whisper.device}` : "Instale o Whisper no bootstrap do Windows ou use uma legenda pronta.");
      const ai = status.ai || {};
      const geminiReady = ai.mode === "gemini" && ai.connected;
      const geminiConfigured = Boolean(ai.gemini_configured);
      renderDependencyStatus("geminiStatus", geminiReady || geminiConfigured, geminiReady ? `Gemini conectado · ${ai.model || "modelo configurado"}` : geminiConfigured ? "Chave Gemini configurada; conexão não confirmada" : "Gemini opcional — nenhuma chave configurada", geminiReady ? "O Studio pode usar Gemini e mantém fallback local." : geminiConfigured ? "A chave está salva localmente; falha de rede não bloqueia o Furia 1." : "Sem chave, a análise segue com Ollama ou sinais locais.");
      return status;
    } catch (error) {
      appendConsole(`Não foi possível consultar o status das dependências: ${error.message}`, "warning", "status");
      return null;
    }
  }

  async function refreshStatusFromUi() {
    const button = $("#btnRefreshStatus");
    if (button) { button.disabled = true; button.textContent = "Atualizando…"; }
    try {
      const status = await refreshStudioStatus();
      if (status) toast("Diagnóstico local atualizado.", "success");
    } finally {
      if (button) { button.disabled = false; button.textContent = "Atualizar diagnóstico"; }
    }
  }

  function formatTime(seconds = 0) {
    const value = Number(seconds) || 0;
    return `${Math.floor(value / 60)}:${Math.floor(value % 60).toString().padStart(2, "0")}`;
  }

  function statusLabel(status) {
    return ({ empty: "SEM FONTE", pending: "AGUARDANDO", processing: "PROCESSANDO", ready_review: "CORTES PRONTOS", ready_no_results: "SEM CANDIDATOS", ready: "PRONTO", completed: "CONCLUÍDO", error: "ATENÇÃO" })[status] || "PROJETO";
  }

  function clipStatusLabel(status) {
    return ({ suggested: "SUGERIDO", reviewing: "REVISANDO", approved: "APROVADO", rejected: "REJEITADO", exported: "EXPORTADO" })[status] || "SUGERIDO";
  }

  function nextProjectAction(project) {
    if (!project?.filename) return { step: "01 / FONTE", title: "Importe um vídeo para começar.", detail: "A fonte será copiada para o workspace local antes de qualquer análise.", action: "import", label: "Importar vídeo" };
    if (state.busy || state.exporting.size || project.status === "processing") return { step: "EM ANDAMENTO", title: "O Studio está trabalhando.", detail: "Acompanhe a etapa atual no Console; não é necessário clicar novamente.", action: "console", label: "Abrir Console" };
    const hasTranscript = Boolean(project.transcriptCount || project.transcript?.length || project.transcription?.segment_count);
    if (!hasTranscript) return { step: "02 / TRANSCRIÇÃO", title: "Transforme a fala em texto.", detail: "Use um transcript pronto ou execute o Whisper local para liberar a leitura editorial.", action: "transcribe", label: "Executar Whisper local" };
    if (!Number(project.candidateCount || 0)) {
      if (project.status === "ready_no_results") return { step: "03 / LEITURA", title: "A análise terminou sem cortes prontos.", detail: "Revise o transcript, ajuste o contexto ou reanalise explicitamente; nenhum corte foi ocultado silenciosamente.", action: "analyze", label: "Reanalisar — Furia 1" , forceReanalysis: true };
      return { step: "03 / LEITURA", title: "Forme o pool de candidatos.", detail: "O Furia 1 vai procurar unidades editoriais e mostrar o resultado no Console.", action: "analyze", label: "Encontrar cortes — Furia 1", forceReanalysis: false };
    }
    if (Number(project.reviewCount || 0) > 0) return { step: "04 / REVISÃO", title: "Há momentos aguardando sua decisão.", detail: `${project.reviewCount} corte${Number(project.reviewCount) === 1 ? "" : "s"} ainda precisa${Number(project.reviewCount) === 1 ? "" : "m"} de aprovação ou rejeição.`, action: "open-shortlist", label: "Abrir Cortes" };
    if (Number(project.approvedCount || 0) > Number(project.exportedCount || 0)) return { step: "05 / SAÍDA", title: "Há cortes aprovados para exportar.", detail: "Abra a Revisão para conferir o range, a headline e gerar o arquivo vertical.", action: "open-review", label: "Abrir Revisão" };
    return { step: "CONCLUÍDO", title: "O projeto está pronto para consulta.", detail: "Você pode rever o resultado, alterar o intervalo ou abrir outro projeto.", action: "open-review", label: "Abrir Revisão" };
  }

  function renderProjectNextAction(project) {
    const next = nextProjectAction(project);
    const target = $("#projectNextAction");
    const button = $("#btnProjectAnalyze");
    if (target) target.innerHTML = `<div class="next-action-copy"><span class="tiny-label">PRÓXIMO PASSO</span><strong>${escapeHtml(next.step)} · ${escapeHtml(next.title)}</strong><small>${escapeHtml(next.detail)}</small></div>`;
    if (button) {
      button.dataset.action = next.action;
      button.textContent = next.label;
      button.dataset.forceReanalysis = next.forceReanalysis ? "true" : "false";
      button.appendChild(Object.assign(document.createElement("span"), { textContent: next.action === "console" ? "●" : "→" }));
      button.title = next.detail;
      button.disabled = Boolean((state.busy || state.exporting.size) && next.action !== "console");
    }
  }

  function formatRatio(value) {
    const number = Number(value);
    return Number.isFinite(number) ? `${number.toFixed(1)}x` : "sem amostra";
  }

  function renderEditorialBlock(block, compact = false) {
    if (!block || typeof block !== "object") return "";
    const thesis = block.thesis || block.context_summary || "Bloco editorial local";
    const reason = block.moment_reason || block.reason || "Momento selecionado por sinais do Furia 1.";
    const tags = Array.isArray(block.tags) ? block.tags.slice(0, compact ? 3 : 6) : [];
    const moments = Array.isArray(block.suggested_moments) ? block.suggested_moments.slice(0, compact ? 2 : 4) : [];
    return `<div class="editorial-block ${compact ? "is-compact" : ""}"><div class="editorial-block-head"><span class="tiny-label">BLOCO EDITORIAL</span><b>${escapeHtml(block.state || "REVISÃO")}</b></div><strong>${escapeHtml(thesis)}</strong><p>${escapeHtml(reason)}</p>${block.context_summary && !compact ? `<small>${escapeHtml(block.context_summary)}</small>` : ""}${tags.length ? `<div class="editorial-block-tags">${tags.map((tag) => `<span>${escapeHtml(String(tag))}</span>`).join("")}</div>` : ""}${moments.length ? `<div class="editorial-block-moments">${moments.map((moment) => `<button type="button" data-seek="${Number(moment.start ?? moment.at ?? 0)}">${escapeHtml(moment.label || moment.reason || "momento")} <time>${formatTime(moment.start ?? moment.at ?? 0)}</time></button>`).join("")}</div>` : ""}</div>`;
  }

  function renderChubMemory(chub, compact = false) {
    if (!chub?.available) {
      return `<section class="chub-memory is-empty"><div class="chub-memory-head"><span class="tiny-label">MEMÓRIA DE CAMPANHA</span><span class="chub-status">OPCIONAL</span></div><p>Conecte um arquivo JSON exportado do Campaign Hub para consultar referências históricas de hooks. Isso não é necessário para trabalhar e não altera o score local.</p><button class="button button-cyan" data-action="import-chub" title="Selecionar um JSON exportado do Campaign Hub">Conectar memória do Campaign Hub</button></section>`;
    }
    const topPosts = (chub.topPosts || []).slice(0, compact ? 2 : 3);
    const hooks = (chub.hooks || []).slice(0, compact ? 4 : 6);
    const platformLabel = (chub.platforms || []).join(" · ") || "escopo não informado";
    const examples = topPosts.map((post) => `<li><span>${escapeHtml(post.hook || post.tags?.[0] || "criativo histórico")}</span><b>${formatRatio(post.settledRatio ?? post.ratio)}</b></li>`).join("");
    const hookLabels = hooks.map((hook) => {
      const label = hook.label || hook.family || hook.hook || "família de hook";
      const ratio = hook.medianRatio ?? hook.median;
      const observations = hook.observations ?? hook.n;
      return `<span>${escapeHtml(label)}${ratio != null ? ` <b>${formatRatio(ratio)}</b>` : ""}${observations != null ? ` <small>n=${escapeHtml(observations)}</small>` : ""}</span>`;
    }).join("");
    const exampleSummary = examples || (hooks.length ? `<p class="chub-muted">${hooks.length} referências agregadas de hooks; use-as como contexto histórico, não como previsão.</p>` : `<p class="chub-muted">Snapshot conectado, sem exemplos resumidos.</p>`);
    return `<section class="chub-memory"><div class="chub-memory-head"><span class="tiny-label">MEMÓRIA DE CAMPANHA</span><span class="chub-head-actions"><span class="chub-account">${escapeHtml(chub.channel)}</span><button class="chub-clear" data-action="clear-chub" title="Desconectar snapshot">×</button></span></div><p class="chub-explainer">Referência histórica da conta. Não é previsão e não altera o score técnico deste corte.</p><div class="chub-memory-meta"><span>${escapeHtml(platformLabel)}</span><span>${chub.fetchedAt ? `atualizado ${escapeHtml(chub.fetchedAt.slice(0, 10))}` : "data não informada"}</span></div>${hookLabels ? `<div class="chub-hook-cloud">${hookLabels}</div>` : ""}${examples ? `<ul class="chub-example-list">${examples}</ul>` : exampleSummary}</section>`;
  }

  function navigate(screen) {
    if (screen === "settings") {
      openSettings();
      return;
    }
    state.screen = screen;
    document.body.classList.toggle("console-in-project", screen === "project");
    $$(".screen").forEach((item) => item.classList.toggle("is-visible", item.dataset.screen === screen));
    $$("[data-screen-link]").forEach((item) => item.classList.toggle("is-active", item.dataset.screenLink === screen));
    const labels = { overview: ["Mesa", "Seu material de hoje"], projects: ["Biblioteca", "Suas fontes locais"], project: ["Projeto", state.activeProject?.name || "Fonte"], shortlist: ["Cortes", "Momentos com oportunidade"], review: ["Revisão", "Decisões com contexto"] };
    const context = labels[screen] || labels.overview;
    $("#topContext").textContent = context[0];
    $("#topSubcontext").textContent = context[1];
    window.scrollTo({ top: 0, behavior: "smooth" });
    if (screen === "overview") refreshOverview();
    if (screen === "projects") { renderProjects(); loadProjects().then(() => { if (state.screen === "projects") renderProjects(); }); }
    if (screen === "shortlist") {
      renderGlobalShortlist();
      loadContextProject().then(() => { if (state.activeProject) renderGlobalShortlist(); });
    }
    if (screen === "review") {
      renderReviewScreen();
      loadContextProject().then(() => { if (state.activeProject) renderReviewScreen(); });
    }
    initWindowManager();
  }

  async function loadContextProject() {
    if (state.activeProject) return state.activeProject;
    const remembered = state.activeProjectId && state.projects.find((project) => String(project.id) === String(state.activeProjectId));
    const candidate = remembered || state.projects.find((project) => Number(project.candidateCount) > 0) || state.projects[0];
    if (!candidate) return null;
    try {
      state.activeProject = await api(`/api/projects/${candidate.id}`);
      rememberActiveProject(state.activeProject.id);
      state.activeClipId = state.activeProject.clips?.[0]?.id || null;
      return state.activeProject;
    } catch (error) { toast(error.message, "error"); return null; }
  }

  function renderMetrics(metrics = {}) {
    $("#metricProjects").textContent = metrics.projects || 0;
    $("#metricReview").textContent = metrics.review || 0;
    $("#metricApproved").textContent = metrics.approved || 0;
    $("#metricExported").textContent = metrics.exported || 0;
    $("#navProjectCount").textContent = metrics.projects || 0;
    $("#navReviewCount").textContent = metrics.review || 0;
  }

  function projectCard(project) {
    const thumb = project.thumbnail || "";
    return `<button class="project-card" data-project-id="${project.id}"><div class="project-thumb">${thumb ? `<img loading="lazy" decoding="async" src="${thumb}" alt="">` : "<div class=project-thumb-fallback>LOCAL / SOURCE</div>"}<span class="project-card-badge">${statusLabel(project.status)}</span></div><div class="project-card-body"><div class="project-card-title">${escapeHtml(project.name)}</div><div class="project-card-meta"><span>${formatDuration(project.duration)}</span><span>${project.width && project.height ? `${project.width}×${project.height}` : "aguardando fonte"}</span></div><div class="project-card-status"><b>${project.candidateCount ? `${project.candidateCount} cortes` : project.stage}</b><span>→</span></div></div></button>`;
  }

  function renderRecent() {
    const target = $("#recentProjects");
    if (!state.projects.length) {
      target.innerHTML = `<div class="empty-state compact"><span class="empty-symbol">+</span><div><strong>Nenhuma fonte ainda.</strong><p>Importe um vídeo para começar a montar sua mesa.</p></div></div>`;
      return;
    }
    target.innerHTML = state.projects.slice(0, 5).map((project) => `<button class="recent-row" data-project-id="${project.id}"><span class="recent-thumb">${project.thumbnail ? `<img loading="lazy" decoding="async" src="${project.thumbnail}" alt="">` : "◒"}</span><span class="recent-copy"><strong>${escapeHtml(project.name)}</strong><small>${statusLabel(project.status)} · ${project.candidateCount || 0} cortes</small></span><span class="recent-arrow">→</span></button>`).join("");
    attachDynamicActions(target);
  }

  function renderProjects() {
    const target = $("#projectsGrid");
    let projects = [...state.projects];
    if (state.filter !== "all") projects = projects.filter((project) => project.status === state.filter);
    if (state.projectSort === "name") projects.sort((a, b) => String(a.name || "").localeCompare(String(b.name || ""), "pt-BR"));
    else if (state.projectSort === "status") projects.sort((a, b) => String(a.status || "").localeCompare(String(b.status || "")) || String(b.updatedAt || "").localeCompare(String(a.updatedAt || "")));
    else projects.sort((a, b) => String(b.updatedAt || b.createdAt || "").localeCompare(String(a.updatedAt || a.createdAt || "")));
    target.innerHTML = projects.length ? projects.map(projectCard).join("") : `<div class="empty-state"><span class="empty-symbol">+</span><h3>${state.projects.length ? "Nenhuma fonte neste filtro." : "Sua primeira fonte começa aqui."}</h3><p>${state.projects.length ? "Escolha outro estado para continuar." : "Importe um vídeo para abrir um projeto local."}</p></div>`;
    attachDynamicActions(target);
  }

  function renderSourceDesk() {
    const target = $("#sourceDeskContent");
    if (!target) return;
    const project = state.activeProject;
    if (!project?.filename) {
      target.className = "source-empty";
      target.innerHTML = `<div class="source-art" aria-hidden="true"><img src="/static/assets/studio-object-sheet.png" alt=""></div><div class="source-copy"><span class="tiny-label">LOCAL FILE / VIDEO</span><h1>Traga uma fonte<br><em>para a mesa.</em></h1><p>O vídeo fica no seu workspace.<br>Nada sai desta máquina.</p><button class="button button-coral" id="btnHeroImport">Importar vídeo <span>↗</span></button></div>`;
      $("#btnHeroImport")?.addEventListener("click", openImport);
      return;
    }
    target.className = "source-active";
    const transcriptLabel = project.transcriptCount ? `${project.transcriptCount} blocos` : "transcrição pendente";
    const cutLabel = project.candidateCount ? `${project.candidateCount} cortes` : "nenhum corte ainda";
    target.innerHTML = `<div class="source-active-preview">${project.videoUrl ? `<video controls preload="metadata" src="${project.videoUrl}" aria-label="Prévia de ${escapeAttribute(project.name)}"></video>` : `<div class="video-placeholder"><span>◉</span>Prévia indisponível</div>`}</div><div class="source-active-copy"><span class="tiny-label">FONTE ATIVA / LOCAL</span><h1>${escapeHtml(project.name)}</h1><p>${escapeHtml(project.filename)}<br>${formatDuration(project.duration)} · ${escapeHtml(transcriptLabel)} · ${escapeHtml(cutLabel)}</p><div class="source-active-actions"><button class="button button-coral" data-action="open-project">Abrir projeto <span>→</span></button><button class="button" data-action="open-project-analyze">${project.candidateCount ? "Revisar cortes" : "Continuar preparação"}</button></div></div>`;
    attachDynamicActions(target);
  }

  function refreshOverview() {
    renderRecent();
    renderProjects();
    renderMetrics(state.metrics || {});
    renderSignal();
    renderSourceDesk();
    refreshQueue();
  }

  function nextQueuePollDelay() {
    const active = Boolean(state.currentJobId || state.busy || state.exporting.size);
    const base = active ? 1800 : 8000;
    const backoff = Math.min(4, Math.max(0, state.queuePollFailures || 0));
    const delay = Math.min(30000, base * (2 ** backoff));
    return document.hidden ? Math.max(15000, delay) : delay;
  }

  function scheduleQueuePoll(delay = null) {
    window.clearTimeout(state.queuePollTimer);
    state.queuePollTimer = window.setTimeout(() => {
      state.queuePollTimer = null;
      refreshQueue();
    }, delay == null ? nextQueuePollDelay() : Math.max(0, delay));
  }

  async function refreshQueue() {
    const target = $("#queueContent");
    if (!target || state.queuePollBusy) return;
    state.queuePollBusy = true;
    window.clearTimeout(state.queuePollTimer);
    state.queuePollTimer = null;
    try {
      const payload = await api("/api/jobs?limit=6");
      const jobs = payload.jobs || [];
      state.queuePollFailures = 0;
      target.innerHTML = jobs.length ? jobs.map((job, index) => `<div class="queue-line"><b>${String(index + 1).padStart(2, "0")}</b><span>${escapeHtml(job.type || "job local")}</span><small>${escapeHtml(job.message || job.stage || job.state || "aguardando")}</small><i>${job.state === "completed" ? "✓" : job.state === "failed" ? "!" : job.state === "cancelled" ? "×" : `${Number(job.progress || 0)}%`}</i></div>`).join("") : `<div class="queue-empty"><span>◒</span><p>Nenhuma tarefa em andamento.<br>A mesa está pronta para a próxima fonte.</p></div>`;
      if (state.consoleOpen && !state.consoleLines.length && !state.consoleDismissed) hydrateConsoleFromLatestJob(jobs[0]);
    } catch (_) {
      state.queuePollFailures = Math.min(4, (state.queuePollFailures || 0) + 1);
      target.innerHTML = `<div class="queue-empty"><span>…</span><p>Fila local indisponível no momento.<br>O Studio tentará novamente automaticamente.</p></div>`;
    } finally {
      state.queuePollBusy = false;
      scheduleQueuePoll();
    }
  }

  async function hydrateConsoleFromLatestJob(latest = null) {
    if (state.consoleLines.length || state.consoleDismissed) return;
    try {
      if (!latest) latest = (await api("/api/jobs?limit=1")).jobs?.[0];
      if (!latest || state.consoleJobId === latest.id) return;
      state.consoleJobId = latest.id;
      const activeState = ["queued", "running", "cancel_requested"].includes(String(latest.state || ""));
      state.currentJobId = activeState ? latest.id : null;
      state.cancelRequested = false;
      $("#consoleTitle").textContent = `${latest.type || "Tarefa local"} · ${latest.state || "fila"}`;
      const eventPayload = await api(`/api/jobs/${latest.id}/events?limit=120`).catch(() => ({ events: [] }));
      const events = eventPayload.events || [];
      events.forEach((event) => appendConsole(event.message, event.level || "info", event.stage || latest.stage || "job", `${latest.id}:${event.sequence}`));
      if (latest.error && !events.some((event) => event.message === latest.error)) appendConsole(latest.error, "error", latest.stage || "job", `${latest.id}:error`);
      if (latest.state === "completed" && !events.some((event) => /job concluído|tarefa concluída/i.test(String(event.message || "")))) appendConsole(latest.message || "Tarefa concluída.", "success", latest.stage || "job", `${latest.id}:completed`);
    } catch (_) {}
  }

  function loadProjects() {
    if (state.projectsRequest) return state.projectsRequest;
    state.projectsRequest = (async () => {
      try {
        const payload = await api("/api/projects");
        state.projects = Array.isArray(payload) ? payload : (payload.projects || []);
        if (state.activeProjectId && !state.projects.some((project) => String(project.id) === String(state.activeProjectId))) {
          rememberActiveProject(null);
          state.activeProject = null;
        }
        if (state.activeProject && !state.projects.some((project) => String(project.id) === String(state.activeProject.id))) {
          state.activeProject = null;
        }
        const approved = state.projects.reduce((total, project) => total + Number(project.approvedCount || 0), 0);
        const exported = state.projects.reduce((total, project) => total + Number(project.exportedCount || 0), 0);
        const review = state.projects.reduce((total, project) => total + Number(project.reviewCount ?? Math.max(0, Number(project.candidateCount || 0) - Number(project.approvedCount || 0))), 0);
        state.metrics = payload.metrics || {
          projects: state.projects.length,
          processing: state.projects.filter((project) => ["processing", "pending"].includes(project.status)).length,
          review: Math.max(0, review),
          approved,
          exported,
        };
        refreshOverview();
        if (state.activeProject) {
          state.activeProject = await api(`/api/projects/${state.activeProject.id}`);
          rememberActiveProject(state.activeProject.id);
          renderProjectScreen();
        } else if (state.projects.length) {
          await loadContextProject();
          refreshOverview();
        }
      } catch (error) { toast(error.message, "error"); }
      finally { state.projectsRequest = null; }
    })();
    return state.projectsRequest;
  }

  async function openProject(id) {
    try {
      state.activeProject = await api(`/api/projects/${id}`);
      rememberActiveProject(state.activeProject.id);
      const preferredTab = ["analyze", "shortlist", "review"].includes(state.projectTab) ? state.projectTab : "analyze";
      state.projectTab = preferredTab === "review" && state.activeProject.clips?.length ? "review" : preferredTab === "shortlist" && state.activeProject.clips?.length ? "shortlist" : "analyze";
      state.activeClipId = state.activeProject.clips?.find((clip) => clip.id === state.activeClipId)?.id || state.activeProject.clips?.[0]?.id || null;
      renderProjectScreen();
      navigate("project");
    } catch (error) { toast(error.message, "error"); }
  }

  function renderProjectScreen() {
    const project = state.activeProject;
    if (!project) return;
    $("#projectTitle").textContent = project.name;
    $("#projectMeta").textContent = `${formatDuration(project.duration)} · ${project.width || "—"}×${project.height || "—"} · ${project.stage}`;
    $("#projectState").textContent = statusLabel(project.status);
    $("#projectState").className = `project-state ${project.status}`;
    $("#projectTabCount").textContent = project.clips?.length || 0;
    $$(".project-tab").forEach((tab) => tab.classList.toggle("is-active", tab.dataset.projectTab === state.projectTab));
    try { localStorage.setItem("furia-project-tab", state.projectTab); } catch (_) {}
    renderProjectNextAction(project);
    const target = $("#projectBody");
    if (target) target.setAttribute("aria-busy", state.busy ? "true" : "false");
    document.body.classList.toggle("studio-busy", Boolean(state.busy || state.exporting.size));
    if (state.projectTab === "analyze") target.innerHTML = renderAnalyze(project);
    if (state.projectTab === "shortlist") target.innerHTML = renderShortlist(project.clips || []);
    if (state.projectTab === "review") target.innerHTML = renderReview(project);
    attachDynamicActions(target);
  }

  function renderAnalyze(project) {
    const analysis = project.analysis || {};
    const transcript = project.transcript || [];
    const transcription = project.transcription || {};
    const analyzing = project.status === "processing" || state.busy;
    const transcriptSource = transcription.source || (transcript.length ? "arquivo local" : "aguardando");
    const transcriptLabel = transcript.length ? `${transcript.length} blocos · ${transcriptSource}` : "Ainda não gerada";
    return `<div class="editor-grid"><section class="window editor-window"><div class="window-bar"><span>01 / VÍDEO DE ORIGEM</span><span class="window-status">${statusLabel(project.status)}</span></div><div class="editor-window-body"><div class="window-subhead"><span class="subhead-label">FONTE LOCAL / PRÉVIA</span><span class="status-chip">${project.filename ? "ARQUIVO COPIADO" : "SEM FONTE"}</span></div><div class="video-frame">${project.videoUrl ? `<video controls preload="metadata" src="${project.videoUrl}" aria-label="Prévia de ${escapeAttribute(project.name)}"></video>` : `<div class="video-placeholder"><span>+</span>Importe uma fonte para ver a prévia.</div>`}</div><div class="editor-stats"><div class="editor-stat"><b>${formatDuration(project.duration)}</b><span>DURAÇÃO</span></div><div class="editor-stat"><b>${analysis.active_ranges || "—"}</b><span>SINAIS LOCAIS</span></div><div class="editor-stat"><b>${project.candidateCount || 0}</b><span>CORTES</span></div></div></div></section><section class="window editor-window"><div class="window-bar"><span>02 / PREPARAR E ENCONTRAR</span><span class="window-status">FURIA 1</span></div><div class="editor-window-body"><p class="understanding-copy"><strong>Fluxo recomendado:</strong> primeiro transforme a fala em uma transcrição, depois deixe o Furia 1 formar o pool de candidatos. Cada ação mostra o progresso no Console.</p><div class="workflow-steps"><div class="workflow-step"><b>1</b><span>Transcrição</span><small>${escapeHtml(transcriptLabel)}</small></div><div class="workflow-step"><b>2</b><span>Leitura editorial</span><small>${project.candidateCount ? "pool pronto" : "após a transcrição"}</small></div><div class="workflow-step"><b>3</b><span>Revisão humana</span><small>${project.candidateCount ? "abrir Cortes" : "aguardando"}</small></div></div><div class="signal-list"><div class="signal-row"><span>Ritmo</span><i style="--signal:${analysis.active_ranges ? "72%" : "8%"};--signal-color:var(--cyan)"></i><b>${analysis.active_ranges ? "mapeado" : "aguardando"}</b></div><div class="signal-row"><span>Transcript</span><i style="--signal:${transcript.length ? "92%" : "5%"};--signal-color:var(--coral)"></i><b>${transcript.length ? "pronto" : "pendente"}</b></div><div class="signal-row"><span>Cortes</span><i style="--signal:${project.candidateCount ? "86%" : "5%"};--signal-color:var(--sun)"></i><b>${project.candidateCount ? "prontos" : "pendentes"}</b></div></div>${renderChubMemory(project.chub, true)}      <div class="editor-actions"><button class="button" data-action="attach-transcript" title="Use um arquivo SRT, VTT ou TXT já existente">Usar transcript pronto</button><button class="button button-cyan" data-action="transcribe" ${analyzing ? "disabled" : ""} title="Transcrever a fonte com Whisper local">${analyzing ? "Whisper em execução…" : "Executar Whisper local"}</button><button class="button button-coral" data-action="analyze" data-force-reanalysis="${project.candidateCount ? "true" : "false"}" ${analyzing ? "disabled" : ""} title="${project.candidateCount ? "Recalcular os candidatos explicitamente" : "Formar e ranquear candidatos com o motor Furia 1"}">${analyzing ? "Análise em execução…" : project.candidateCount ? "Reanalisar — Furia 1" : "Encontrar cortes — Furia 1"} <span>→</span></button></div></div></section><section class="window editor-window transcript-window"><div class="window-bar"><span>03 / TEXTO COM TIMESTAMPS</span><button class="window-bar-link" data-action="attach-transcript">IMPORTAR SRT / VTT / TXT</button></div><div class="editor-window-body">${transcript.length ? `<div class="transcript-tools"><span class="tiny-label">BUSCAR E IR PARA O VÍDEO</span><input class="transcript-search" type="search" placeholder="Buscar na fala…" aria-label="Buscar na transcrição"></div><div class="transcript-snippet">${transcript.slice(0, 24).map((segment) => `<div class="transcript-line" data-seek="${segment.start}" tabindex="0" role="button"><time>${formatTime(segment.start)}</time><p>${escapeHtml(segment.text)}</p></div>`).join("")}</div>` : `<div class="transcript-empty"><span>⌁</span><div><strong>Nenhum texto carregado ainda.</strong><p>Escolha “Executar Whisper local” ou use um arquivo SRT, VTT ou TXT. O botão não fica silencioso: cada etapa aparece no Console.</p></div></div>`}</div></section></div>`;
  }

  function renderShortlist(clips) {
    if (!clips.length) {
      const completedWithoutResults = state.activeProject?.status === "ready_no_results";
      const emptyTitle = completedWithoutResults ? "A análise terminou sem cortes prontos." : "Os cortes aparecem depois da leitura da fonte.";
      const emptyCopy = completedWithoutResults ? "Confira a transcrição e reanalise explicitamente se quiser tentar outra leitura local." : "O Furia 1 primeiro forma um pool amplo de candidatos; depois você revisa, ajusta e aprova os momentos.";
      const actionLabel = completedWithoutResults ? "Reanalisar — Furia 1" : "Encontrar cortes — Furia 1";
      return `<div class="project-shortlist-layout"><div class="empty-state"><span class="empty-symbol">✦</span><h3>${emptyTitle}</h3><p>${emptyCopy}</p><button class="button button-coral" data-action="analyze" data-force-reanalysis="${completedWithoutResults ? "true" : "false"}" title="${completedWithoutResults ? "Recalcular explicitamente os candidatos" : "Formar e ranquear candidatos com o motor Furia 1"}">${actionLabel} <span>→</span></button></div>${renderChubMemory(state.activeProject?.chub, true)}</div>`;
    }
    return `<div class="project-shortlist-layout"><div class="shortlist-grid">${sortedClips(clips).map(clipCard).join("")}</div>${renderChubMemory(state.activeProject?.chub, true)}</div>`;
  }

  function renderGlobalShortlist() {
    const target = $("#shortlistGrid");
    if (!state.activeProject) {
      target.innerHTML = `<div class="empty-state"><span class="empty-symbol">✦</span><h3>Escolha uma fonte primeiro.</h3><p>Os cortes aparecem depois da análise de um projeto local.</p><button class="button button-coral" data-action="go-projects">Abrir Biblioteca <span>→</span></button></div>`;
      $("#shortlistCount").textContent = "0 momentos";
      attachDynamicActions(target);
      return;
    }
    const clips = sortedClips(state.activeProject.clips || []);
    $("#shortlistCount").textContent = `${clips.length} momentos`;
    target.innerHTML = clips.length ? clips.map(clipCard).join("") : `<div class="empty-state"><span class="empty-symbol">✦</span><h3>A shortlist ainda está vazia.</h3><p>Execute a análise de ${escapeHtml(state.activeProject.name)} para encontrar cortes.</p></div>`;
    attachDynamicActions(target);
    const chubTarget = $("#shortlistChubContext");
    if (chubTarget) { chubTarget.innerHTML = renderChubMemory(state.activeProject.chub); attachDynamicActions(chubTarget); }
  }

  function sortedClips(clips) {
    const result = [...clips];
    if (state.sort === "duration") return result.sort((a, b) => b.duration - a.duration);
    if (state.sort === "status") return result.sort((a, b) => a.status.localeCompare(b.status));
    return result.sort((a, b) => b.score - a.score);
  }

  function clipCard(clip) {
    return `<article class="clip-card" data-clip-id="${clip.id}"><div class="clip-thumb">${clip.thumbnail ? `<img loading="lazy" decoding="async" src="${clip.thumbnail}" alt="">` : "<div class=clip-fallback>LOCAL / CUT</div>"}<span class="score-badge">${clip.score}</span></div><div class="clip-content"><div class="clip-card-top"><span>${clipStatusLabel(clip.status)}</span><span>${formatDuration(clip.duration)}</span></div><h3>${escapeHtml(clip.title)}</h3><div class="clip-time">${formatTime(clip.start)} — ${formatTime(clip.end)}</div><div class="clip-signal" aria-label="Sinal local ${clip.score} de 100"><span>SINAL</span><b>${Array.from({ length: 5 }, (_, index) => `<i class="${index < Math.max(1, Math.round(Number(clip.score || 0) / 20)) ? "is-on" : ""}"></i>`).join("")}</b></div><div class="reason-list">${(clip.reasons || []).map((reason) => `<span>${escapeHtml(reason)}</span>`).join("")}</div>${renderEditorialBlock(clip.editorialBlock, true)}</div><div class="clip-actions"><button class="clip-open" data-action="open-review" data-clip-id="${clip.id}">Revisar <span>→</span></button><button class="small-decision approve" data-action="decision" data-decision="approved" data-clip-id="${clip.id}" title="Aprovar">✓</button><button class="small-decision reject" data-action="decision" data-decision="rejected" data-clip-id="${clip.id}" title="Rejeitar">×</button></div></article>`;
  }

  function renderReview(project) {
    const clip = project.clips?.find((item) => item.id === state.activeClipId) || project.clips?.[0];
    if (!clip) return `<div class="empty-state"><span class="empty-symbol">◉</span><h3>Escolha um momento nos Cortes.</h3><p>Analise uma fonte para abrir a bancada de Revisão.</p></div>`;
    state.activeClipId = clip.id;
    const duration = Math.max(1, Number(project.duration) || clip.end || 1);
    const clipIndex = (project.clips || []).findIndex((item) => item.id === clip.id);
    const previousClip = clipIndex > 0 ? project.clips[clipIndex - 1] : null;
    const nextClip = clipIndex >= 0 && clipIndex < project.clips.length - 1 ? project.clips[clipIndex + 1] : null;
    const transcript = (project.transcript || []).filter((segment) => segment.end > clip.start && segment.start < clip.end);
    const video = project.videoUrl ? `<video class="review-video" controls preload="metadata" src="${project.videoUrl}" data-start="${clip.start}" data-end="${clip.end}"></video>` : `<div class="video-placeholder"><span>◉</span>Prévia indisponível</div>`;
    const captions = transcript.length ? `<div class="review-caption-layer" aria-live="polite">${transcript.map((segment) => `<span class="review-caption" data-start="${segment.start}" data-end="${segment.end}">${escapeHtml(segment.text)}</span>`).join("")}</div>` : "";
    const isExporting = state.exporting.has(clip.id);
    const canExport = clip.status === "approved" && !isExporting;
    const exportLabel = isExporting ? "Renderizando…" : clip.status === "exported" ? "Exportado" : canExport ? "Exportar 9:16" : "Aprovar primeiro";
    const startPercent = Math.max(0, Math.min(100, clip.start / duration * 100));
    const endPercent = Math.max(startPercent, Math.min(100, clip.end / duration * 100));
    return `<div class="review-grid"><section class="window review-stage"><div class="window-bar"><span>01 / REVISÃO DO CORTE · ${clipIndex + 1}/${project.clips.length}</span><div class="review-nav"><button type="button" data-action="open-review" data-clip-id="${previousClip?.id || ""}" ${previousClip ? "" : "disabled"} aria-label="Corte anterior">←</button><button type="button" data-action="open-review" data-clip-id="${nextClip?.id || ""}" ${nextClip ? "" : "disabled"} aria-label="Próximo corte">→</button><span class="window-status">${clipStatusLabel(clip.status)}</span></div></div><div class="review-stage-body"><div class="review-frame">${video}${captions}<div class="review-safe-label">9:16 / ÁREA SEGURA</div></div><div class="review-controls"><div class="review-timeline" data-duration="${duration}" style="--range-start:${startPercent}%;--range-end:${endPercent}%"><i class="review-range-fill"></i><input class="range-handle range-start" type="range" min="0" max="${duration}" step="0.01" value="${clip.start}" data-clip-id="${clip.id}" aria-label="Início do clip"><input class="range-handle range-end" type="range" min="0" max="${duration}" step="0.01" value="${clip.end}" data-clip-id="${clip.id}" aria-label="Fim do clip"></div><div class="review-range-readout"><b>IN <span class="review-start-readout">${formatTime(clip.start)}</span></b><b>OUT <span class="review-end-readout">${formatTime(clip.end)}</span></b><span>${formatDuration(clip.duration)} selecionados</span></div><div class="review-preview-tools"><button class="button button-cyan" data-action="play-clip" data-clip-id="${clip.id}">Reproduzir corte <span>▶</span></button><label class="loop-toggle"><input type="checkbox" class="review-loop" data-clip-id="${clip.id}"><span>loop da seleção</span></label><label class="loop-toggle"><input type="checkbox" class="review-snap" data-clip-id="${clip.id}"><span>alinhar às bordas da fala</span></label><small>Arraste os marcadores para ajustar o intervalo.</small></div></div><div class="review-feedback-row"><label for="reviewFeedbackReason">Se rejeitar, registre o motivo<select class="review-feedback-reason" id="reviewFeedbackReason"><option value="">Selecionar motivo opcional</option><option value="sem_contexto">Contexto incompleto</option><option value="sem_payoff">Sem conclusão</option><option value="audio_ruim">Áudio ou fala ruim</option><option value="duplicado">Duplicado de outro momento</option><option value="fora_do_foco">Fora do foco editorial</option><option value="corte_fraco">Potencial insuficiente</option><option value="outro">Outro</option></select></label><small>O motivo ajuda a calibrar o ranking depois de reunir decisões suficientes.</small></div><div class="review-actions"><button class="reject-action" data-action="decision" data-decision="rejected" data-clip-id="${clip.id}">Rejeitar</button><button class="adjust-action" data-action="open-shortlist">Voltar aos Cortes</button><button class="approve-action" data-action="decision" data-decision="approved" data-clip-id="${clip.id}">Aprovar <span>→</span></button><button class="export-action" data-action="export" data-clip-id="${clip.id}" ${canExport ? "" : "disabled"}>${exportLabel} <span>↗</span></button></div></div></section><aside class="window review-inspector"><div class="window-bar"><span>02 / NOTA DE DECISÃO</span><span class="window-status">SCORE ${clip.score}</span></div><div class="review-inspector-body"><h3>${escapeHtml(clip.title)}</h3><p class="review-muted">${formatTime(clip.start)} — ${formatTime(clip.end)} · ${formatDuration(clip.duration)}</p>${renderChubMemory(project.chub, true)}${renderEditorialBlock(clip.editorialBlock)}<div class="review-tools"><button class="button button-sun" data-action="seo" data-clip-id="${clip.id}">Gerar SEO local</button><div class="seo-preview" id="seo-${clip.id}"><span class="seo-empty">Título, descrição e hashtags entram aqui.</span></div></div><label class="field-label" for="reviewTitle">Headline sugerida</label><input class="review-title-input" id="reviewTitle" data-clip-id="${clip.id}" value="${escapeAttribute(clip.title)}"><div class="review-signal-block"><span class="tiny-label">POR QUE ENTROU</span>${(clip.reasons || []).map((reason, index) => `<div class="review-reason"><i class="reason-dot ${["pink", "cyan", "yellow"][index % 3]}"></i><span>${escapeHtml(reason)}</span><b>${index === 0 ? "forte" : "presente"}</b></div>`).join("")}</div><div class="review-transcript"><div class="transcript-tools"><span class="tiny-label">TEXTO / BUSCAR E IR</span><input class="transcript-search" type="search" placeholder="Buscar na fala…" aria-label="Buscar na fala"></div>${transcript.length ? transcript.map((segment) => `<p data-seek="${segment.start}" tabindex="0" role="button"><time>${formatTime(segment.start)}</time>${escapeHtml(segment.text)}</p>`).join("") : `<p class="review-muted">Anexe uma transcrição para revisar o texto em sincronia.</p>`}</div></div></aside></div>`;
  }

  function bindReviewControls(scope) {
    const timeline = $(".review-timeline", scope);
    const startInput = $(".range-start", scope);
    const endInput = $(".range-end", scope);
    const snapInput = $(".review-snap", scope);
    if (timeline && startInput && endInput && !timeline.dataset.bound) {
      timeline.dataset.bound = "1";
      const syncRange = () => {
        const maximum = Number(timeline.dataset.duration) || 1;
        let start = Number(startInput.value) || 0;
        let end = Number(endInput.value) || maximum;
        if (end - start < 1) {
          if (document.activeElement === startInput) start = Math.max(0, end - 1);
          else end = Math.min(maximum, start + 1);
          startInput.value = start;
          endInput.value = end;
        }
        timeline.style.setProperty("--range-start", `${start / maximum * 100}%`);
        timeline.style.setProperty("--range-end", `${end / maximum * 100}%`);
        $(".review-start-readout", scope).textContent = formatTime(start);
        $(".review-end-readout", scope).textContent = formatTime(end);
        $(".review-range-readout > span", scope).textContent = `${formatDuration(end - start)} selecionados`;
      };
      [startInput, endInput].forEach((input) => {
        input.addEventListener("input", syncRange);
        input.addEventListener("change", () => persistClipRange(input.dataset.clipId, Number(startInput.value), Number(endInput.value), Boolean(snapInput?.checked)));
      });
      syncRange();
    }
    const video = $(".review-video", scope);
    if (video && !video.dataset.bound) {
      video.dataset.bound = "1";
      const start = Number(video.dataset.start) || 0;
      const end = Number(video.dataset.end) || 0;
      const captions = $$(".review-caption", scope);
      const loop = $(".review-loop", scope);
      const syncPlayback = () => {
        const time = video.currentTime;
        captions.forEach((item) => item.classList.toggle("is-active", time >= Number(item.dataset.start) && time < Number(item.dataset.end)));
        if (end > start && time >= end) {
          if (loop?.checked) { video.currentTime = start; video.play().catch(() => {}); }
          else video.pause();
        }
      };
      video.addEventListener("play", () => { if (video.currentTime < start || video.currentTime >= end) video.currentTime = start; });
      video.addEventListener("timeupdate", syncPlayback);
      loop?.addEventListener("change", () => { video.loop = loop.checked; });
    }
  }

  async function persistClipRange(clipId, start, end, snapToTranscript = false) {
    if (end - start < 1) { toast("O clip precisa ter pelo menos 1 segundo.", "error"); return; }
    try {
      const clip = await api(`/api/clips/${clipId}/range`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ start, end, snap_to_transcript: snapToTranscript }) });
      const local = state.activeProject?.clips?.find((item) => item.id === clipId);
      if (local) Object.assign(local, clip);
      state.activeClipId = clipId;
      toast("Intervalo salvo. O clip voltou para revisão.", "success");
      renderProjectScreen();
      renderReviewScreen();
      await loadProjects();
    } catch (error) { toast(error.message, "error"); }
  }

  function playClip(clipId) {
    const video = $(".review-video");
    const clip = state.activeProject?.clips?.find((item) => item.id === clipId);
    if (!video || !clip) return;
    video.currentTime = clip.start;
    video.play().catch(() => toast("O navegador bloqueou a reprodução automática. Clique no player para iniciar.", "default"));
  }

  function renderReviewScreen() {
    const project = state.activeProject;
    const target = $("#reviewWorkspace");
    const clips = project?.clips || [];
    const reviewed = clips.filter((clip) => ["approved", "rejected", "exported"].includes(clip.status)).length;
    $("#reviewProgressText").textContent = `${reviewed} de ${clips.length} revisados`;
    $("#reviewProgressBar").style.width = clips.length ? `${Math.round(reviewed / clips.length * 100)}%` : "0%";
    target.innerHTML = project ? renderReview(project) : `<div class="empty-state"><span class="empty-symbol">◉</span><h3>Escolha um projeto nos Cortes.</h3><p>O vídeo, o transcript e a decisão aparecem juntos aqui.</p></div>`;
    attachDynamicActions(target);
  }

  function attachDynamicActions(scope = document) {
    $$(`[data-project-id]`, scope).forEach((element) => element.addEventListener("click", () => openProject(element.dataset.projectId)));
    $$(`[data-action]`, scope).forEach((element) => element.addEventListener("click", () => performAction(element.dataset.action, element.dataset)));
    const titleInput = $("#reviewTitle", scope);
    if (titleInput && !titleInput.dataset.bound) {
      titleInput.dataset.bound = "1";
      titleInput.addEventListener("change", () => updateClipTitle(titleInput.dataset.clipId, titleInput.value));
    }
    $$('[data-seek]', scope).forEach((line) => {
      if (line.dataset.seekBound) return;
      line.dataset.seekBound = "1";
      const seek = () => { const seconds = Number(line.dataset.seek); const video = $('.review-video', document) || $('.video-frame video', document); if (video && Number.isFinite(seconds)) { video.currentTime = seconds; video.focus({ preventScroll: true }); } };
      line.addEventListener('click', seek);
      line.addEventListener('keydown', (event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); seek(); } });
    });
    $$('.transcript-search', scope).forEach((input) => {
      if (input.dataset.searchBound) return;
      input.dataset.searchBound = "1";
      input.addEventListener('input', () => { const query = input.value.trim().toLocaleLowerCase(); const host = input.closest('.editor-window-body, .review-transcript'); $$('.transcript-line, .review-transcript > p[data-seek]', host).forEach((line) => { line.hidden = Boolean(query) && !line.textContent.toLocaleLowerCase().includes(query); }); });
    });
    bindReviewControls(scope);
    initWindowManager(scope);
  }

  async function updateClipTitle(clipId, title) {
    try {
      await api(`/api/clips/${clipId}/title`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title }) });
      if (state.activeProject) state.activeProject = await api(`/api/projects/${state.activeProject.id}`);
      toast("Headline salva no projeto local.", "success");
    } catch (error) { toast(error.message, "error"); }
  }

  async function performAction(action, data = {}) {
    if (action === "import") return openImport();
    if (action === "console") return setConsoleOpen(true);
    if (action === "analyze") return analyzeActiveProject(String(data.forceReanalysis || "").toLowerCase() === "true");
    if (action === "transcribe") return transcribeActiveProject();
    if (action === "attach-transcript") return $("#transcriptInput").click();
    if (action === "import-chub") { if (!state.activeProject) await loadContextProject(); if (!state.activeProject) { toast("Importe uma fonte antes de anexar a memória do Chub.", "error"); return; } return $("#chubInput").click(); }
    if (action === "clear-chub") return clearChubContext();
    if (action === "go-projects") return navigate("projects");
    if (action === "open-project") { if (state.activeProject) { state.projectTab = "analyze"; renderProjectScreen(); navigate("project"); } else navigate("projects"); return; }
    if (action === "open-project-analyze") { if (state.activeProject) { state.projectTab = state.activeProject.candidateCount ? "shortlist" : "analyze"; renderProjectScreen(); navigate("project"); } else navigate("projects"); return; }
    if (action === "open-review") { state.activeClipId = data.clipId; state.projectTab = "review"; renderProjectScreen(); navigate("project"); return; }
    if (action === "open-shortlist") { state.projectTab = "shortlist"; renderProjectScreen(); navigate("project"); return; }
    if (action === "decision") {
      const reason = data.reasonCode || $(".review-feedback-reason")?.value || "";
      return decideClip(data.clipId, data.decision, reason);
    }
    if (action === "export") return exportClip(data.clipId);
    if (action === "play-clip") return playClip(data.clipId);
    if (action === "seo") return generateSeo(data.clipId);
    if (action === "use-headline") return applyHeadline(data.clipId, data.headline);
  }

  async function pollJob(jobId, interval = 600) {
    const token = ++state.jobPollToken;
    while (token === state.jobPollToken) {
      await sleep(interval);
      const progress = await api(`/api/jobs/${jobId}`);
      const status = progress.status || progress.state || "queued";
      if (state.activeProject && $("#projectState")) $("#projectState").textContent = status === "running" ? `${progress.progress || 0}%` : (progress.message || progress.stage || status);
      try {
        const eventPayload = await api(`/api/jobs/${jobId}/events?limit=120`);
        (eventPayload.events || []).forEach((event) => appendConsole(event.message, event.level || "info", event.stage || progress.stage || "job", `${jobId}:${event.sequence}`));
      } catch (_) {}
      if (["completed", "done"].includes(status)) { state.currentJobId = null; state.cancelRequested = false; appendConsole(progress.message || "Tarefa concluída.", "success", progress.stage || "job", `${jobId}:completed`); renderConsole(); scheduleQueuePoll(0); return progress; }
      if (["failed", "error", "cancelled"].includes(status)) { state.currentJobId = null; state.cancelRequested = false; appendConsole(progress.error || progress.message || "A operação local falhou.", status === "cancelled" ? "warning" : "error", progress.stage || "job", `${jobId}:failed`); renderConsole(); scheduleQueuePoll(0); const failure = new Error(progress.error || progress.message || "A operação local falhou."); failure.consoleLogged = true; throw failure; }
    }
    throw new Error("O acompanhamento da tarefa foi interrompido; abra o Console para verificar o estado.");
  }

  async function analyzeActiveProject(forceReanalysis = false) {
    if (!state.activeProject?.filename) { toast("Importe um vídeo antes de analisar.", "error"); appendConsole("Análise não iniciada: nenhuma fonte foi importada.", "warning", "análise"); return; }
    if (state.activeProject.clips?.length && !forceReanalysis) {
      state.projectTab = "shortlist";
      renderProjectScreen();
      toast("Este projeto já tem cortes. Revise a shortlist ou escolha Reanalisar explicitamente.");
      appendConsole("Análise não repetida: este projeto já possui candidatos persistidos. Use Reanalisar quando quiser recalcular.", "info", "análise", `analysis-skip:${state.activeProject.id}:${Date.now()}`);
      return;
    }
    if (state.busy) { toast("Já existe uma tarefa em andamento. Acompanhe pelo Console."); setConsoleOpen(true); return; }
    state.busy = true;
    state.currentJobId = null;
    setConsoleOpen(true);
    $("#consoleTitle").textContent = `Análise: ${state.activeProject.name}`;
    renderProjectScreen();
    appendConsole(`Iniciando análise editorial da fonte ${state.activeProject.name}.`, "info", "análise", `analysis-start:${state.activeProject.id}:${Date.now()}`);
    try {
      const job = await api("/api/process/cut", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ project_id: state.activeProject.id, video_path: state.activeProject.sourceVideo, face_tracking: false, audit_mode: "standard", preferred_format: "vertical_916", force_reanalysis: Boolean(forceReanalysis) }) });
      const jobId = job.jobId || job.job_id;
      if (!jobId) throw new Error("O servidor não retornou o identificador da análise.");
      state.currentJobId = jobId;
      state.cancelRequested = false;
      renderConsole();
      appendConsole("Job criado. O Furia 1 vai transcrever, formar o pool e ranquear os candidatos.", "info", "fila", `${jobId}:created`);
      toast("O Studio está lendo a fonte…");
      await pollJob(jobId);
      state.activeProject = await api(`/api/projects/${state.activeProject.id}`);
      const clipCount = state.activeProject.clips?.length || 0;
      state.activeClipId = state.activeProject.clips?.[0]?.id || null;
      state.projectTab = clipCount ? "shortlist" : "analyze";
      if (clipCount) {
        toast(`${clipCount} cortes encontrados.`, "success");
        appendConsole(`${clipCount} cortes disponíveis para revisão humana.`, "success", "análise", `${jobId}:result`);
      } else {
        toast("A análise terminou sem encontrar cortes prontos.", "default");
        appendConsole("Nenhum corte pronto nesta execução. Confira a transcrição, a duração da fonte e tente ajustar o contexto editorial.", "warning", "análise", `${jobId}:no-cuts`);
      }
      renderProjectScreen();
      await loadProjects();
    } catch (error) { if (!error.consoleLogged) appendConsole(error.message, "error", "análise", `analysis-error:${state.currentJobId || Date.now()}`); toast(error.message, "error"); }
    finally { state.busy = false; renderProjectScreen(); renderConsole(); scheduleQueuePoll(0); }
  }

  async function transcribeActiveProject() {
    if (!state.activeProject?.filename) { toast("Importe um vídeo antes de transcrever.", "error"); appendConsole("Whisper não iniciado: nenhuma fonte foi importada.", "warning", "whisper"); return; }
    if (state.busy) { toast("Já existe uma tarefa em andamento. Acompanhe pelo Console."); setConsoleOpen(true); return; }
    state.busy = true;
    setConsoleOpen(true);
    $("#consoleTitle").textContent = `Whisper: ${state.activeProject.name}`;
    renderProjectScreen();
    appendConsole("Whisper local solicitado manualmente. O vídeo permanece no workspace.", "info", "whisper", `whisper-start:${state.activeProject.id}:${Date.now()}`);
    try {
      const job = await api(`/api/projects/${state.activeProject.id}/transcribe`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ force_whisper: true }) });
      const jobId = job.jobId || job.job_id;
      if (!jobId) throw new Error("O servidor não retornou o identificador da transcrição.");
      state.currentJobId = jobId;
      state.cancelRequested = false;
      renderConsole();
      appendConsole("Job criado. Acompanhe abaixo o engine efetivamente usado e o progresso por chunks.", "info", "fila", `${jobId}:created`);
      toast("Whisper local está preparando a transcrição…");
      await pollJob(jobId, 900);
      state.activeProject = await api(`/api/projects/${state.activeProject.id}`);
      toast("Transcrição do Whisper pronta para revisão.", "success");
      renderProjectScreen();
      refreshOverview();
    } catch (error) { if (!error.consoleLogged) appendConsole(error.message, "error", "whisper", `whisper-error:${state.currentJobId || Date.now()}`); toast(error.message, "error"); }
    finally { state.busy = false; renderProjectScreen(); renderConsole(); scheduleQueuePoll(0); }
  }

  async function decideClip(clipId, decision, reasonCode = "") {
    try {
      await api(`/api/clips/${clipId}/decision`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ decision, reason_code: reasonCode || "" }) });
      state.activeProject = await api(`/api/projects/${state.activeProject.id}`);
      state.activeClipId = clipId;
      toast(decision === "approved" ? "Momento aprovado e pronto para exportar." : decision === "rejected" ? "Momento rejeitado e retirado da fila." : "Estado atualizado.", decision === "approved" ? "success" : "default");
      renderProjectScreen();
      renderGlobalShortlist();
      renderReviewScreen();
      await loadProjects();
    } catch (error) { toast(error.message, "error"); }
  }

  async function exportClip(clipId) {
    if (state.exporting.has(clipId)) return;
    state.exporting.add(clipId);
    renderReviewScreen();
    $("#consoleTitle").textContent = `Exportação: corte ${clipId}`;
    appendConsole(`Iniciando exportação vertical do corte ${clipId}.`, "info", "export", `export-start:${clipId}:${Date.now()}`);
    try {
      const job = await api(`/api/clips/${clipId}/export`, { method: "POST" });
      const jobId = job.jobId || job.job_id;
      if (!jobId) throw new Error("O servidor não retornou o identificador da exportação.");
      state.currentJobId = jobId;
      state.cancelRequested = false;
      renderConsole();
      toast("Renderizando corte vertical…");
      await pollJob(jobId, 800);
      state.activeProject = await api(`/api/projects/${state.activeProject.id}`);
      toast("Export pronto na pasta local.", "success");
      renderProjectScreen();
      renderReviewScreen();
      await loadProjects();
    } catch (error) { if (!error.consoleLogged) appendConsole(error.message, "error", "export", `export-error:${clipId}:${Date.now()}`); toast(error.message, "error"); }
    finally { state.exporting.delete(clipId); renderProjectScreen(); renderReviewScreen(); renderConsole(); scheduleQueuePoll(0); }
  }

  function renderSeoPreview(seo, clipId) {
    const clip = (state.activeProject?.clips || []).find((item) => String(item.id) === String(clipId));
    const titles = (seo.titles || [seo.title]).filter(Boolean).slice(0, 3);
    const quote = String(clip?.transcript || "").replace(/\s+/g, " ").trim().slice(0, 220);
    const description = String(seo.description || "Headline local baseada na legenda timestampada.").trim().slice(0, 260);
    return `<div class="seo-proof"><span class="tiny-label">HEADLINE / BASE NA LEGENDA</span><p class="seo-proof-quote">${quote ? `“${escapeHtml(quote)}${quote.length >= 220 ? "…" : "”"}` : "A legenda deste corte é a fonte da sugestão."}</p><small>${formatTime(clip?.start || 0)} — ${formatTime(clip?.end || 0)} · sem promessa de viralidade</small></div><div class="seo-alternatives">${titles.map((title, index) => `<button class="seo-option ${index === 0 ? "is-primary" : ""}" data-action="use-headline" data-clip-id="${clipId}" data-headline="${escapeAttribute(title)}"><span>${index + 1}. ${escapeHtml(title)}</span><b>usar</b></button>`).join("")}</div><p class="seo-description">${escapeHtml(description)}</p><span class="seo-hashtags">${escapeHtml((seo.hashtags || []).join(" "))}</span>`;
  }

  async function applyHeadline(clipId, headline) {
    if (!headline) return;
    await updateClipTitle(clipId, headline);
    state.projectTab = "review";
    renderProjectScreen();
  }

  async function generateSeo(clipId) {
    try {
      const seo = await api(`/api/projects/${state.activeProject.id}/seo`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ clip_id: clipId }) });
      const target = $(`#seo-${clipId}`);
      if (target) { target.innerHTML = renderSeoPreview(seo, clipId); attachDynamicActions(target); }
      toast("Três headlines locais geradas a partir das captions.", "success");
    } catch (error) { toast(error.message, "error"); }
  }

  async function confirmImport() {
    const file = $("#videoInput").files?.[0];
    if (!file) return;
    const button = $("#btnConfirmImport");
    button.disabled = true;
    button.textContent = "Adicionando…";
    try {
      const project = await api("/api/projects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: file.name.replace(/\.[^.]+$/, "") }) });
      const form = new FormData();
      form.append("video", file);
      state.activeProject = await api(`/api/projects/${project.id}/import`, { method: "POST", body: form });
      state.activeClipId = null;
      $("#importModal").hidden = true;
      $("#videoInput").value = "";
      $("#importFileName").textContent = "Nenhum arquivo escolhido";
      toast("Fonte importada. A mesa está pronta para analisar.", "success");
      await loadProjects();
      renderProjectScreen();
      navigate("project");
    } catch (error) { toast(error.message, "error"); }
    finally { button.disabled = false; button.innerHTML = "Adicionar fonte <span>→</span>"; }
  }

  async function attachTranscript(file) {
    if (!file || !state.activeProject) return;
    const form = new FormData();
    form.append("transcript", file);
    try {
      state.activeProject = await api(`/api/projects/${state.activeProject.id}/transcript`, { method: "POST", body: form });
      toast("Transcript anexado ao projeto.", "success");
      renderProjectScreen();
    } catch (error) { toast(error.message, "error"); }
  }

  async function attachChub(file) {
    if (!file) return;
    if (!state.activeProject) await loadContextProject();
    if (!state.activeProject) { toast("Importe uma fonte antes de anexar a memória do Chub.", "error"); return; }
    try {
      const payload = JSON.parse(await file.text());
      state.activeProject = await api(`/api/projects/${state.activeProject.id}/chub-context`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      rememberActiveProject(state.activeProject.id);
      $("#settingsChubStatus").textContent = `Snapshot conectado: ${state.activeProject.chub.channel}.`;
      appendConsole(`Memória opcional do Campaign Hub conectada ao projeto ${state.activeProject.name}.`, "success", "chub", `chub:${state.activeProject.id}:${Date.now()}`);
      toast(`Memória chub conectada à conta ${state.activeProject.chub.channel}.`, "success");
      renderProjectScreen();
      renderGlobalShortlist();
      renderReviewScreen();
      await loadProjects();
    } catch (error) { toast(error.message || "O snapshot chub não pôde ser importado.", "error"); }
  }

  async function clearChubContext() {
    if (!state.activeProject) return;
    try {
      state.activeProject = await api(`/api/projects/${state.activeProject.id}/chub-context`, { method: "DELETE" });
      $("#settingsChubStatus").textContent = "Nenhum snapshot selecionado neste projeto.";
      appendConsole("Memória do Campaign Hub desconectada; o projeto continua funcionando offline.", "success", "chub", `chub-clear:${state.activeProject.id}:${Date.now()}`);
      toast("Memória chub desconectada deste projeto.", "success");
      renderProjectScreen();
      renderGlobalShortlist();
      renderReviewScreen();
      await loadProjects();
    } catch (error) { toast(error.message, "error"); }
  }

  function openImport() { $("#importModal").hidden = false; $("#dropZone")?.focus(); }
  function closeImport() { $("#importModal").hidden = true; }
  async function openSettings() {
    const modal = $("#settingsModal");
    if (!modal) return;
    modal.hidden = false;
    try {
      const settings = await api("/api/settings");
      state.settings = settings;
      $("#settingTranscriptionSource").value = settings.transcription_source || "auto";
      $("#settingAiBackend").value = settings.ai_backend || "auto";
      $("#settingGeminiModel").value = settings.gemini_model || "gemini-2.5-flash";
      $("#settingGeminiApiKey").value = "";
      $("#settingGeminiApiKey").placeholder = settings.gemini_api_key_configured ? "Chave já configurada — deixe vazio para manter" : "Cole sua chave aqui (fica fora do código)";
      $("#settingCutDuration").value = settings.cut_duration || 45;
      $("#settingSubtitleStyle").value = settings.subtitle_style || "word_by_word";
      $("#settingChannelContext").value = settings.channel_context || "";
      $("#settingsChubStatus").textContent = state.activeProject?.chub?.available ? `Snapshot conectado: ${state.activeProject.chub.channel}.` : "Nenhum snapshot selecionado neste projeto.";
      await refreshStudioStatus();
    } catch (error) { toast(error.message, "error"); }
  }
  function closeSettings() { $("#settingsModal").hidden = true; }
  async function saveSettings() {
    try {
      const payload = { transcription_source: $("#settingTranscriptionSource").value, ai_backend: $("#settingAiBackend").value, gemini_model: $("#settingGeminiModel").value.trim() || "gemini-2.5-flash", cut_duration: Number($("#settingCutDuration").value) || 45, subtitle_style: $("#settingSubtitleStyle").value, channel_context: $("#settingChannelContext").value };
      const geminiKey = $("#settingGeminiApiKey").value.trim();
      if (geminiKey) payload.gemini_api_key = geminiKey;
      await api("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      state.settings = { ...state.settings, ...payload, gemini_api_key_configured: Boolean(geminiKey || state.settings.gemini_api_key_configured) };
      closeSettings();
      appendConsole(`Ajustes aplicados: transcrição ${payload.transcription_source}; análise ${payload.ai_backend}.`, "success", "settings", `settings:${Date.now()}`);
      toast("Ajustes salvos na base local do Studio.", "success");
    } catch (error) { appendConsole(error.message, "error", "settings", `settings-error:${Date.now()}`); toast(error.message, "error"); }
  }
  function escapeHtml(value) { return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char])); }
  function escapeAttribute(value) { return escapeHtml(value).replace(/\n/g, " "); }

  function initBoot() {
    const screen = $("#bootScreen");
    if (!screen) return;
    const skip = $("#bootSkip");
    let finished = false;
    let progress = 0;
    let timer = null;
    const captions = ["abrindo o workspace local…", "lendo a mesa…", "organizando suas fontes…", "pronto para cortar."];
    const finish = () => {
      if (finished) return;
      finished = true;
      window.clearInterval(timer);
      screen.classList.add("is-done");
      screen.setAttribute("aria-hidden", "true");
      window.setTimeout(() => screen.remove(), 450);
      try { sessionStorage.setItem("furia-studio-boot-seen", "1"); } catch (_) {}
    };
    let seen = false;
    try { seen = sessionStorage.getItem("furia-studio-boot-seen") === "1"; } catch (_) {}
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches || seen) { finish(); return; }
    screen.setAttribute("aria-hidden", "false");
    timer = window.setInterval(() => {
      progress = Math.min(100, progress + 10 + Math.round(Math.random() * 9));
      $("#bootProgress").style.width = `${progress}%`;
      $("#bootCaption").textContent = captions[Math.min(captions.length - 1, Math.floor(progress / 28))];
      if (progress >= 100) window.setTimeout(finish, 160);
    }, 95);
    skip?.addEventListener("click", finish);
    window.addEventListener("keydown", (event) => { if (event.key === "Enter" && !finished) finish(); }, { once: true });
  }

  function initSignal() {
    const stage = $("#signalStage");
    if (!stage) return;
    stage.addEventListener("pointermove", (event) => {
      const rect = stage.getBoundingClientRect();
      stage.style.setProperty("--mouse-x", ((event.clientX - rect.left) / rect.width - .5).toFixed(3));
      stage.style.setProperty("--mouse-y", ((event.clientY - rect.top) / rect.height - .5).toFixed(3));
      stage.classList.add("is-exploring");
      layoutSignal();
    });
    stage.addEventListener("pointerleave", () => { stage.style.setProperty("--mouse-x", "0"); stage.style.setProperty("--mouse-y", "0"); stage.classList.remove("is-exploring"); layoutSignal(); });
    window.addEventListener("resize", layoutSignal);
  }

  function renderSignal() {
    const target = $("#signalNodes");
    if (!target) return;
    const projects = state.projects.slice(0, 6);
    $("#signalNodeCount").textContent = `${projects.length} SOURCE${projects.length === 1 ? "" : "S"}`;
    if (!projects.length) {
      target.innerHTML = ["SOURCE", "RHYTHM", "CUT", "EXPORT"].map((label, index) => `<div class="signal-ghost signal-ghost-${index}" aria-hidden="true"><span></span><b>${label}</b></div>`).join("");
      return;
    }
    target.innerHTML = projects.map((project, index) => `<button class="signal-node" style="--float-delay:${index * -0.55}s" data-project-id="${project.id}" aria-label="Abrir ${escapeAttribute(project.name)}">${project.thumbnail ? `<img src="${project.thumbnail}" alt="">` : "<span class=signal-node-color></span>"}<span class="signal-node-label">${escapeHtml(project.name)} · ${statusLabel(project.status)}</span></button>`).join("");
    attachDynamicActions(target);
    layoutSignal();
  }

  function layoutSignal() {
    const stage = $("#signalStage");
    const nodes = $$(".signal-node", stage || document);
    if (!stage || !nodes.length) return;
    const rect = stage.getBoundingClientRect();
    const radiusX = Math.min(rect.width * .34, 190);
    const radiusY = Math.min(rect.height * .28, 118);
    const mx = Number(stage.style.getPropertyValue("--mouse-x")) || 0;
    const my = Number(stage.style.getPropertyValue("--mouse-y")) || 0;
    nodes.forEach((node, index) => {
      const angle = (index / nodes.length) * Math.PI * 2 - Math.PI / 2;
      node.style.left = `${rect.width / 2 + Math.cos(angle) * radiusX - node.offsetWidth / 2}px`;
      node.style.top = `${rect.height / 2 + Math.sin(angle) * radiusY - node.offsetHeight / 2}px`;
      node.style.transform = `translate3d(${mx * (12 + index * 2)}px, ${my * (10 + index)}px, 0)`;
    });
  }

  function init() {
    $$("[data-screen-link]").forEach((element) => element.addEventListener("click", () => navigate(element.dataset.screenLink)));
    $("#btnHeroImport")?.addEventListener("click", openImport);
    $("#btnProjectsImport")?.addEventListener("click", openImport);
    $("#btnQuickImport")?.addEventListener("click", openImport);
    $("#btnCloseImport")?.addEventListener("click", closeImport);
    $("#btnConfirmImport")?.addEventListener("click", confirmImport);
    $("#btnProjectAnalyze")?.addEventListener("click", (event) => performAction(event.currentTarget.dataset.action || "analyze", event.currentTarget.dataset));
    $("#videoInput")?.addEventListener("change", (event) => { const file = event.target.files?.[0]; $("#importFileName").textContent = file?.name || "Nenhum arquivo escolhido"; $("#btnConfirmImport").disabled = !file; });
    $("#transcriptInput")?.addEventListener("change", (event) => { attachTranscript(event.target.files?.[0]); event.target.value = ""; });
    $("#chubInput")?.addEventListener("change", (event) => { attachChub(event.target.files?.[0]); event.target.value = ""; });
    $("#btnTopSettings")?.addEventListener("click", openSettings);
    $("#btnToggleConsole")?.addEventListener("click", () => setConsoleOpen(!state.consoleOpen));
    $("#btnCloseConsole")?.addEventListener("click", () => setConsoleOpen(false));
    $("#btnClearConsole")?.addEventListener("click", clearConsole);
    $("#btnCancelJob")?.addEventListener("click", cancelCurrentJob);
    $("#btnRefreshStatus")?.addEventListener("click", refreshStatusFromUi);
    $("#btnCloseSettings")?.addEventListener("click", closeSettings);
    $("#btnCloseSettingsSecondary")?.addEventListener("click", closeSettings);
    $("#btnSaveSettings")?.addEventListener("click", saveSettings);
    $("#settingsModal")?.addEventListener("click", (event) => { if (event.target.id === "settingsModal") closeSettings(); });
    $("#dropZone")?.addEventListener("dragover", (event) => { event.preventDefault(); $("#dropZone").classList.add("is-dragging"); });
    $("#dropZone")?.addEventListener("dragleave", () => $("#dropZone").classList.remove("is-dragging"));
    $("#dropZone")?.addEventListener("drop", (event) => { event.preventDefault(); $("#dropZone").classList.remove("is-dragging"); const file = event.dataTransfer.files?.[0]; if (file) { const input = $("#videoInput"); const transfer = new DataTransfer(); transfer.items.add(file); input.files = transfer.files; input.dispatchEvent(new Event("change")); } });
    $("#projectFilters")?.addEventListener("click", (event) => { const button = event.target.closest("[data-filter]"); if (!button) return; state.filter = button.dataset.filter; try { localStorage.setItem("furia-filter", state.filter); } catch (_) {}; $$(".filter-pill").forEach((item) => item.classList.toggle("is-active", item === button)); renderProjects(); });
    $("#shortlistSort")?.addEventListener("change", (event) => { state.sort = event.target.value; try { localStorage.setItem("furia-sort", state.sort); } catch (_) {}; renderGlobalShortlist(); });
    $("#btnSortProjects")?.addEventListener("click", (event) => { const modes = ["recent", "name", "status"]; state.projectSort = modes[(modes.indexOf(state.projectSort) + 1) % modes.length]; const labels = { recent: "Recentes ↓", name: "Nome A–Z", status: "Estado" }; event.currentTarget.textContent = labels[state.projectSort]; try { localStorage.setItem("furia-project-sort", state.projectSort); } catch (_) {}; renderProjects(); });
    $(".project-tabs")?.addEventListener("click", (event) => { const tab = event.target.closest("[data-project-tab]"); if (!tab) return; state.projectTab = tab.dataset.projectTab; renderProjectScreen(); });
    $("#importModal")?.addEventListener("click", (event) => { if (event.target.id === "importModal") closeImport(); });
    document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeImport(); if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "o") { event.preventDefault(); openImport(); } });
    initBoot();
    initSignal();
    initWindowManager(document);
    setConsoleOpen(state.consoleOpen);
    renderConsole();
    loadProjects();
    refreshStudioStatus();
    document.addEventListener("visibilitychange", () => scheduleQueuePoll(0));
    scheduleQueuePoll(0);
  }

  init();
})();
