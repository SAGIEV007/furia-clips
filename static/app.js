(() => {
  "use strict";

  const state = { projects: [], activeProject: null, activeClipId: null, screen: "overview", projectTab: "analyze", filter: "all", sort: "score", busy: false, exporting: new Set() };
  try {
    state.filter = localStorage.getItem("furia-filter") || state.filter;
    state.sort = localStorage.getItem("furia-sort") || state.sort;
    state.projectTab = localStorage.getItem("furia-project-tab") || state.projectTab;
  } catch (_) {}
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

  function formatTime(seconds = 0) {
    const value = Number(seconds) || 0;
    return `${Math.floor(value / 60)}:${Math.floor(value % 60).toString().padStart(2, "0")}`;
  }

  function statusLabel(status) {
    return ({ empty: "SEM FONTE", pending: "AGUARDANDO", processing: "PROCESSANDO", ready_review: "CORTES PRONTOS", ready: "PRONTO", completed: "CONCLUÍDO", error: "ATENÇÃO" })[status] || "PROJETO";
  }

  function clipStatusLabel(status) {
    return ({ suggested: "SUGERIDO", reviewing: "REVISANDO", approved: "APROVADO", rejected: "REJEITADO", exported: "EXPORTADO" })[status] || "SUGERIDO";
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
    return `<div class="editorial-block ${compact ? "is-compact" : ""}"><div class="editorial-block-head"><span class="tiny-label">EDITORIAL BLOCK</span><b>${escapeHtml(block.state || "REVISÃO")}</b></div><strong>${escapeHtml(thesis)}</strong><p>${escapeHtml(reason)}</p>${block.context_summary && !compact ? `<small>${escapeHtml(block.context_summary)}</small>` : ""}${tags.length ? `<div class="editorial-block-tags">${tags.map((tag) => `<span>${escapeHtml(String(tag))}</span>`).join("")}</div>` : ""}${moments.length ? `<div class="editorial-block-moments">${moments.map((moment) => `<button type="button" data-seek="${Number(moment.start ?? moment.at ?? 0)}">${escapeHtml(moment.label || moment.reason || "momento")} <time>${formatTime(moment.start ?? moment.at ?? 0)}</time></button>`).join("")}</div>` : ""}</div>`;
  }

  function renderChubMemory(chub, compact = false) {
    if (!chub?.available) {
      return `<section class="chub-memory is-empty"><div class="chub-memory-head"><span class="tiny-label">CAMPAIGN MEMORY</span><span class="chub-status">OPCIONAL</span></div><p>Use um snapshot do chub para lembrar hooks e referências de desempenho sem alterar o score local.</p><button class="button button-cyan" data-action="import-chub">Importar snapshot</button></section>`;
    }
    const topPosts = (chub.topPosts || []).slice(0, compact ? 2 : 3);
    const hooks = (chub.hooks || []).slice(0, compact ? 4 : 6);
    const platformLabel = (chub.platforms || []).join(" · ") || "escopo não informado";
    const examples = topPosts.map((post) => `<li><span>${escapeHtml(post.hook || post.tags?.[0] || "criativo histórico")}</span><b>${formatRatio(post.settledRatio ?? post.ratio)}</b></li>`).join("");
    const hookLabels = hooks.map((hook) => `<span>${escapeHtml(hook.label || "hook")}${hook.medianRatio != null ? ` <b>${formatRatio(hook.medianRatio)}</b>` : ""}</span>`).join("");
    return `<section class="chub-memory"><div class="chub-memory-head"><span class="tiny-label">CAMPAIGN MEMORY</span><span class="chub-head-actions"><span class="chub-account">${escapeHtml(chub.channel)}</span><button class="chub-clear" data-action="clear-chub" title="Desconectar snapshot">×</button></span></div><p class="chub-explainer">Referência histórica da conta. Não é previsão e não altera o score técnico deste corte.</p><div class="chub-memory-meta"><span>${escapeHtml(platformLabel)}</span><span>${chub.fetchedAt ? `atualizado ${escapeHtml(chub.fetchedAt.slice(0, 10))}` : "data não informada"}</span></div>${hookLabels ? `<div class="chub-hook-cloud">${hookLabels}</div>` : ""}${examples ? `<ul class="chub-example-list">${examples}</ul>` : `<p class="chub-muted">Snapshot conectado, mas sem exemplos resumidos.</p>`}</section>`;
  }

  function navigate(screen) {
    if (screen === "settings") {
      openSettings();
      return;
    }
    state.screen = screen;
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
    const candidate = state.projects.find((project) => Number(project.candidateCount) > 0);
    if (!candidate) return null;
    try {
      state.activeProject = await api(`/api/projects/${candidate.id}`);
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
    return `<button class="project-card" data-project-id="${project.id}"><div class="project-thumb">${thumb ? `<img src="${thumb}" alt="">` : "<div class=project-thumb-fallback>LOCAL / SOURCE</div>"}<span class="project-card-badge">${statusLabel(project.status)}</span></div><div class="project-card-body"><div class="project-card-title">${escapeHtml(project.name)}</div><div class="project-card-meta"><span>${formatDuration(project.duration)}</span><span>${project.width && project.height ? `${project.width}×${project.height}` : "aguardando fonte"}</span></div><div class="project-card-status"><b>${project.candidateCount ? `${project.candidateCount} cortes` : project.stage}</b><span>→</span></div></div></button>`;
  }

  function renderRecent() {
    const target = $("#recentProjects");
    if (!state.projects.length) {
      target.innerHTML = `<div class="empty-state compact"><span class="empty-symbol">+</span><div><strong>Nenhuma fonte ainda.</strong><p>Importe um vídeo para começar a montar sua mesa.</p></div></div>`;
      return;
    }
    target.innerHTML = state.projects.slice(0, 5).map((project) => `<button class="recent-row" data-project-id="${project.id}"><span class="recent-thumb">${project.thumbnail ? `<img src="${project.thumbnail}" alt="">` : "◒"}</span><span class="recent-copy"><strong>${escapeHtml(project.name)}</strong><small>${statusLabel(project.status)} · ${project.candidateCount || 0} cortes</small></span><span class="recent-arrow">→</span></button>`).join("");
    attachDynamicActions(target);
  }

  function renderProjects() {
    const target = $("#projectsGrid");
    let projects = [...state.projects];
    if (state.filter !== "all") projects = projects.filter((project) => project.status === state.filter);
    target.innerHTML = projects.length ? projects.map(projectCard).join("") : `<div class="empty-state"><span class="empty-symbol">+</span><h3>${state.projects.length ? "Nenhuma fonte neste filtro." : "Sua primeira fonte começa aqui."}</h3><p>${state.projects.length ? "Escolha outro estado para continuar." : "Importe um vídeo para abrir um projeto local."}</p></div>`;
    attachDynamicActions(target);
  }

  function refreshOverview() {
    renderRecent();
    renderProjects();
    renderMetrics(state.metrics || {});
    renderSignal();
    refreshQueue();
  }

  async function refreshQueue() {
    const target = $("#queueContent");
    if (!target) return;
    try {
      const payload = await api("/api/jobs?limit=6");
      const jobs = payload.jobs || [];
      target.innerHTML = jobs.length ? jobs.map((job, index) => `<div class="queue-line"><b>${String(index + 1).padStart(2, "0")}</b><span>${escapeHtml(job.type || "job local")}</span><small>${escapeHtml(job.message || job.stage || job.state || "aguardando")}</small><i>${job.state === "completed" ? "✓" : job.state === "failed" ? "!" : `${Number(job.progress || 0)}%`}</i></div>`).join("") : `<div class="queue-empty"><span>◒</span><p>Nenhuma tarefa em andamento.<br>A mesa está pronta para a próxima fonte.</p></div>`;
    } catch (_) {
      target.innerHTML = `<div class="queue-empty"><span>…</span><p>Fila local indisponível no momento.</p></div>`;
    }
  }

  async function loadProjects() {
    try {
      const payload = await api("/api/projects");
      state.projects = Array.isArray(payload) ? payload : (payload.projects || []);
      const clips = state.projects.reduce((total, project) => total + Number(project.candidateCount || 0), 0);
      const approved = state.projects.reduce((total, project) => total + Number(project.approvedCount || 0), 0);
      const exported = state.projects.reduce((total, project) => total + Number(project.exportedCount || 0), 0);
      state.metrics = payload.metrics || {
        projects: state.projects.length,
        processing: state.projects.filter((project) => ["processing", "pending"].includes(project.status)).length,
        review: clips - approved - exported,
        approved,
        exported,
      };
      refreshOverview();
      if (state.activeProject) {
        state.activeProject = await api(`/api/projects/${state.activeProject.id}`);
        renderProjectScreen();
      }
    } catch (error) { toast(error.message, "error"); }
  }

  async function openProject(id) {
    try {
      state.activeProject = await api(`/api/projects/${id}`);
      state.projectTab = "analyze";
      state.activeClipId = state.activeProject.clips?.[0]?.id || null;
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
    const target = $("#projectBody");
    if (state.projectTab === "analyze") target.innerHTML = renderAnalyze(project);
    if (state.projectTab === "shortlist") target.innerHTML = renderShortlist(project.clips || []);
    if (state.projectTab === "review") target.innerHTML = renderReview(project);
    attachDynamicActions(target);
  }

  function renderAnalyze(project) {
    const analysis = project.analysis || {};
    const transcript = project.transcript || [];
    const analyzing = project.status === "processing";
    return `<div class="editor-grid"><section class="window editor-window"><div class="window-bar"><span>01 / SOURCE PLAYER</span><span class="window-status">${statusLabel(project.status)}</span></div><div class="editor-window-body"><div class="window-subhead"><span class="subhead-label">SOURCE / PREVIEW</span><span class="status-chip">${project.filename ? "LOCAL FILE" : "EMPTY"}</span></div><div class="video-frame">${project.videoUrl ? `<video controls preload="metadata" src="${project.videoUrl}"></video>` : `<div class="video-placeholder"><span>+</span>Importe uma fonte para ver a prévia.</div>`}</div><div class="editor-stats"><div class="editor-stat"><b>${formatDuration(project.duration)}</b><span>DURAÇÃO</span></div><div class="editor-stat"><b>${analysis.active_ranges || "—"}</b><span>ZONAS ATIVAS</span></div><div class="editor-stat"><b>${project.candidateCount || 0}</b><span>CORTES</span></div></div></div></section><section class="window editor-window"><div class="window-bar"><span>02 / UNDERSTAND</span><span class="window-status">LOCAL</span></div><div class="editor-window-body"><p class="understanding-copy">A fonte é lida por ritmo e continuidade antes de qualquer corte. O transcript pode ser anexado ou gerado localmente quando o Whisper estiver instalado.</p><div class="signal-list"><div class="signal-row"><span>Ritmo</span><i style="--signal:${analysis.active_ranges ? "72%" : "8%"};--signal-color:var(--cyan)"></i><b>${analysis.active_ranges ? "mapeado" : "aguardando"}</b></div><div class="signal-row"><span>Transcript</span><i style="--signal:${transcript.length ? "92%" : "5%"};--signal-color:var(--coral)"></i><b>${transcript.length ? `${transcript.length} blocos` : "opcional"}</b></div><div class="signal-row"><span>Cortes</span><i style="--signal:${project.candidateCount ? "86%" : "5%"};--signal-color:var(--sun)"></i><b>${project.candidateCount ? "prontos" : "vazios"}</b></div></div>${renderChubMemory(project.chub, true)}<div class="editor-actions"><button class="button" data-action="attach-transcript">Adicionar transcript</button><button class="button" data-action="transcribe" ${analyzing ? "disabled" : ""}>Whisper local</button><button class="button button-coral" data-action="analyze" ${analyzing ? "disabled" : ""}>${analyzing ? "Analisando…" : "Analisar fonte"} <span>→</span></button></div></div></section><section class="window editor-window transcript-window"><div class="window-bar"><span>03 / TRANSCRIPT</span><button class="window-bar-link" data-action="attach-transcript">IMPORTAR SRT / VTT / TXT</button></div><div class="editor-window-body">${transcript.length ? `<div class="transcript-tools"><span class="tiny-label">WORDS / SEARCH & SEEK</span><input class="transcript-search" type="search" placeholder="Buscar na fala…" aria-label="Buscar na transcrição"></div><div class="transcript-snippet">${transcript.slice(0, 24).map((segment) => `<div class="transcript-line" data-seek="${segment.start}" tabindex="0" role="button"><time>${formatTime(segment.start)}</time><p>${escapeHtml(segment.text)}</p></div>`).join("")}</div>` : `<div class="transcript-empty"><span>⌁</span><div><strong>Uma superfície de leitura, não uma caixa preta.</strong><p>Anexe uma transcrição para revisar as palavras junto do vídeo.</p></div></div>`}</div></section></div>`;
  }

  function renderShortlist(clips) {
    if (!clips.length) return `<div class="project-shortlist-layout"><div class="empty-state"><span class="empty-symbol">✦</span><h3>Os cortes aparecem depois da análise.</h3><p>Execute a análise para encontrar momentos com oportunidade.</p><button class="button button-coral" data-action="analyze">Analisar fonte <span>→</span></button></div>${renderChubMemory(state.activeProject?.chub, true)}</div>`;
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
    return `<article class="clip-card" data-clip-id="${clip.id}"><div class="clip-thumb">${clip.thumbnail ? `<img src="${clip.thumbnail}" alt="">` : "<div class=clip-fallback>LOCAL / CUT</div>"}<span class="score-badge">${clip.score}</span></div><div class="clip-content"><div class="clip-card-top"><span>${clipStatusLabel(clip.status)}</span><span>${formatDuration(clip.duration)}</span></div><h3>${escapeHtml(clip.title)}</h3><div class="clip-time">${formatTime(clip.start)} — ${formatTime(clip.end)}</div><div class="clip-signal" aria-label="Sinal local ${clip.score} de 100"><span>SINAL</span><b>${Array.from({ length: 5 }, (_, index) => `<i class="${index < Math.max(1, Math.round(Number(clip.score || 0) / 20)) ? "is-on" : ""}"></i>`).join("")}</b></div><div class="reason-list">${(clip.reasons || []).map((reason) => `<span>${escapeHtml(reason)}</span>`).join("")}</div>${renderEditorialBlock(clip.editorialBlock, true)}</div><div class="clip-actions"><button class="clip-open" data-action="open-review" data-clip-id="${clip.id}">Revisar <span>→</span></button><button class="small-decision approve" data-action="decision" data-decision="approved" data-clip-id="${clip.id}" title="Aprovar">✓</button><button class="small-decision reject" data-action="decision" data-decision="rejected" data-clip-id="${clip.id}" title="Rejeitar">×</button></div></article>`;
  }

  function renderReview(project) {
    const clip = project.clips?.find((item) => item.id === state.activeClipId) || project.clips?.[0];
    if (!clip) return `<div class="empty-state"><span class="empty-symbol">◉</span><h3>Escolha um momento nos Cortes.</h3><p>Analise uma fonte para abrir a bancada de Revisão.</p></div>`;
    state.activeClipId = clip.id;
    const duration = Math.max(1, Number(project.duration) || clip.end || 1);
    const transcript = (project.transcript || []).filter((segment) => segment.end > clip.start && segment.start < clip.end);
    const video = project.videoUrl ? `<video class="review-video" controls preload="metadata" src="${project.videoUrl}" data-start="${clip.start}" data-end="${clip.end}"></video>` : `<div class="video-placeholder"><span>◉</span>Prévia indisponível</div>`;
    const captions = transcript.length ? `<div class="review-caption-layer" aria-live="polite">${transcript.map((segment) => `<span class="review-caption" data-start="${segment.start}" data-end="${segment.end}">${escapeHtml(segment.text)}</span>`).join("")}</div>` : "";
    const isExporting = state.exporting.has(clip.id);
    const canExport = clip.status === "approved" && !isExporting;
    const exportLabel = isExporting ? "Renderizando…" : clip.status === "exported" ? "Exportado" : canExport ? "Exportar 9:16" : "Aprovar primeiro";
    const startPercent = Math.max(0, Math.min(100, clip.start / duration * 100));
    const endPercent = Math.max(startPercent, Math.min(100, clip.end / duration * 100));
    return `<div class="review-grid"><section class="window review-stage"><div class="window-bar"><span>01 / CLIP REVIEW</span><span class="window-status">${clipStatusLabel(clip.status)}</span></div><div class="review-stage-body"><div class="review-frame">${video}${captions}<div class="review-safe-label">9:16 / SAFE AREA</div></div><div class="review-controls"><div class="review-timeline" data-duration="${duration}" style="--range-start:${startPercent}%;--range-end:${endPercent}%"><i class="review-range-fill"></i><input class="range-handle range-start" type="range" min="0" max="${duration}" step="0.01" value="${clip.start}" data-clip-id="${clip.id}" aria-label="Início do clip"><input class="range-handle range-end" type="range" min="0" max="${duration}" step="0.01" value="${clip.end}" data-clip-id="${clip.id}" aria-label="Fim do clip"></div><div class="review-range-readout"><b>IN <span class="review-start-readout">${formatTime(clip.start)}</span></b><b>OUT <span class="review-end-readout">${formatTime(clip.end)}</span></b><span>${formatDuration(clip.duration)} selecionados</span></div><div class="review-preview-tools"><button class="button button-cyan" data-action="play-clip" data-clip-id="${clip.id}">Reproduzir corte <span>▶</span></button><label class="loop-toggle"><input type="checkbox" class="review-loop" data-clip-id="${clip.id}"><span>loop da seleção</span></label><small>Arraste os marcadores para ajustar o intervalo.</small></div></div><div class="review-actions"><button class="reject-action" data-action="decision" data-decision="rejected" data-clip-id="${clip.id}">Rejeitar</button><button class="adjust-action" data-action="open-shortlist">Voltar aos Cortes</button><button class="approve-action" data-action="decision" data-decision="approved" data-clip-id="${clip.id}">Aprovar <span>→</span></button><button class="export-action" data-action="export" data-clip-id="${clip.id}" ${canExport ? "" : "disabled"}>${exportLabel} <span>↗</span></button></div></div></section><aside class="window review-inspector"><div class="window-bar"><span>02 / DECISION NOTE</span><span class="window-status">SCORE ${clip.score}</span></div><div class="review-inspector-body"><h3>${escapeHtml(clip.title)}</h3><p class="review-muted">${formatTime(clip.start)} — ${formatTime(clip.end)} · ${formatDuration(clip.duration)}</p>${renderChubMemory(project.chub, true)}${renderEditorialBlock(clip.editorialBlock)}<div class="review-tools"><button class="button button-sun" data-action="seo" data-clip-id="${clip.id}">Gerar SEO local</button><span class="seo-preview" id="seo-${clip.id}">Título, descrição e hashtags entram aqui.</span></div><label class="field-label" for="reviewTitle">Headline sugerida</label><input class="review-title-input" id="reviewTitle" data-clip-id="${clip.id}" value="${escapeAttribute(clip.title)}"><div class="review-signal-block"><span class="tiny-label">WHY IT MADE THE CUT</span>${(clip.reasons || []).map((reason, index) => `<div class="review-reason"><i class="reason-dot ${["pink", "cyan", "yellow"][index % 3]}"></i><span>${escapeHtml(reason)}</span><b>${index === 0 ? "forte" : "presente"}</b></div>`).join("")}</div><div class="review-transcript"><div class="transcript-tools"><span class="tiny-label">WORDS / SEARCH & SEEK</span><input class="transcript-search" type="search" placeholder="Buscar na fala…" aria-label="Buscar na fala"></div>${transcript.length ? transcript.map((segment) => `<p data-seek="${segment.start}" tabindex="0" role="button"><time>${formatTime(segment.start)}</time>${escapeHtml(segment.text)}</p>`).join("") : `<p class="review-muted">Anexe uma transcrição para revisar o texto em sincronia.</p>`}</div></div></aside></div>`;
  }

  function bindReviewControls(scope) {
    const timeline = $(".review-timeline", scope);
    const startInput = $(".range-start", scope);
    const endInput = $(".range-end", scope);
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
        input.addEventListener("change", () => persistClipRange(input.dataset.clipId, Number(startInput.value), Number(endInput.value)));
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

  async function persistClipRange(clipId, start, end) {
    if (end - start < 1) { toast("O clip precisa ter pelo menos 1 segundo.", "error"); return; }
    try {
      const clip = await api(`/api/clips/${clipId}/range`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ start, end }) });
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
    if (action === "analyze") return analyzeActiveProject();
    if (action === "transcribe") return transcribeActiveProject();
    if (action === "attach-transcript") return $("#transcriptInput").click();
    if (action === "import-chub") return $("#chubInput").click();
    if (action === "clear-chub") return clearChubContext();
    if (action === "go-projects") return navigate("projects");
    if (action === "open-review") { state.activeClipId = data.clipId; state.projectTab = "review"; renderProjectScreen(); navigate("project"); return; }
    if (action === "open-shortlist") { state.projectTab = "shortlist"; renderProjectScreen(); navigate("project"); return; }
    if (action === "decision") return decideClip(data.clipId, data.decision);
    if (action === "export") return exportClip(data.clipId);
    if (action === "play-clip") return playClip(data.clipId);
    if (action === "seo") return generateSeo(data.clipId);
  }

  async function pollJob(jobId, interval = 600) {
    while (true) {
      await sleep(interval);
      const progress = await api(`/api/jobs/${jobId}`);
      const status = progress.status || progress.state || "queued";
      if (state.activeProject && $("#projectState")) $("#projectState").textContent = status === "running" ? `${progress.progress || 0}%` : (progress.message || progress.stage || status);
      if (["completed", "done"].includes(status)) return progress;
      if (["failed", "error", "cancelled"].includes(status)) throw new Error(progress.error || progress.message || "A operação local falhou.");
    }
  }

  async function analyzeActiveProject() {
    if (!state.activeProject?.filename) { toast("Importe um vídeo antes de analisar.", "error"); return; }
    if (state.busy) return;
    state.busy = true;
    try {
      const job = await api("/api/process/cut", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ project_id: state.activeProject.id, video_path: state.activeProject.sourceVideo, face_tracking: false, audit_mode: "standard", preferred_format: "vertical_916" }) });
      toast("O Studio está lendo a fonte…");
      await pollJob(job.jobId);
      state.activeProject = await api(`/api/projects/${state.activeProject.id}`);
      state.activeClipId = state.activeProject.clips?.[0]?.id || null;
      state.projectTab = "shortlist";
      toast(`${state.activeProject.clips.length} cortes encontrados.`, "success");
      renderProjectScreen();
      await loadProjects();
    } catch (error) { toast(error.message, "error"); }
    finally { state.busy = false; }
  }

  async function transcribeActiveProject() {
    if (!state.activeProject?.filename) { toast("Importe um vídeo antes de transcrever.", "error"); return; }
    if (state.busy) return;
    state.busy = true;
    try {
      const job = await api(`/api/projects/${state.activeProject.id}/transcribe`, { method: "POST" });
      toast("Whisper local está preparando o transcript…");
      await pollJob(job.jobId, 900);
      state.activeProject = await api(`/api/projects/${state.activeProject.id}`);
      toast("Transcript pronto para revisão.", "success");
      renderProjectScreen();
    } catch (error) { toast(error.message, "error"); }
    finally { state.busy = false; }
  }

  async function decideClip(clipId, decision) {
    try {
      await api(`/api/clips/${clipId}/decision`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ decision }) });
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
    try {
      const job = await api(`/api/clips/${clipId}/export`, { method: "POST" });
      toast("Renderizando clip vertical…");
      await pollJob(job.jobId, 800);
      state.activeProject = await api(`/api/projects/${state.activeProject.id}`);
      toast("Export pronto na pasta local.", "success");
      renderProjectScreen();
      renderReviewScreen();
      await loadProjects();
    } catch (error) { toast(error.message, "error"); }
    finally { state.exporting.delete(clipId); renderReviewScreen(); }
  }

  async function generateSeo(clipId) {
    try {
      const seo = await api(`/api/projects/${state.activeProject.id}/seo`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ clip_id: clipId }) });
      const target = $(`#seo-${clipId}`);
      if (target) target.innerHTML = `<strong>${escapeHtml(seo.title)}</strong><span>${escapeHtml(seo.hashtags.join(" "))}</span>`;
      toast("Título, descrição e hashtags gerados localmente.", "success");
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
    if (!file || !state.activeProject) return;
    try {
      const payload = JSON.parse(await file.text());
      state.activeProject = await api(`/api/projects/${state.activeProject.id}/chub-context`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
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
      $("#settingTranscriptionSource").value = settings.transcription_source || "auto";
      $("#settingCutDuration").value = settings.cut_duration || 45;
      $("#settingSubtitleStyle").value = settings.subtitle_style || "word_by_word";
      $("#settingChannelContext").value = settings.channel_context || "";
    } catch (error) { toast(error.message, "error"); }
  }
  function closeSettings() { $("#settingsModal").hidden = true; }
  async function saveSettings() {
    try {
      await api("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ transcription_source: $("#settingTranscriptionSource").value, cut_duration: Number($("#settingCutDuration").value) || 45, subtitle_style: $("#settingSubtitleStyle").value, channel_context: $("#settingChannelContext").value }) });
      closeSettings();
      toast("Ajustes salvos na base local do Studio.", "success");
    } catch (error) { toast(error.message, "error"); }
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
    $("#btnProjectAnalyze")?.addEventListener("click", () => performAction("analyze"));
    $("#videoInput")?.addEventListener("change", (event) => { const file = event.target.files?.[0]; $("#importFileName").textContent = file?.name || "Nenhum arquivo escolhido"; $("#btnConfirmImport").disabled = !file; });
    $("#transcriptInput")?.addEventListener("change", (event) => { attachTranscript(event.target.files?.[0]); event.target.value = ""; });
    $("#chubInput")?.addEventListener("change", (event) => { attachChub(event.target.files?.[0]); event.target.value = ""; });
    $("#btnTopSettings")?.addEventListener("click", openSettings);
    $("#btnCloseSettings")?.addEventListener("click", closeSettings);
    $("#btnCloseSettingsSecondary")?.addEventListener("click", closeSettings);
    $("#btnSaveSettings")?.addEventListener("click", saveSettings);
    $("#settingsModal")?.addEventListener("click", (event) => { if (event.target.id === "settingsModal") closeSettings(); });
    $("#dropZone")?.addEventListener("dragover", (event) => { event.preventDefault(); $("#dropZone").classList.add("is-dragging"); });
    $("#dropZone")?.addEventListener("dragleave", () => $("#dropZone").classList.remove("is-dragging"));
    $("#dropZone")?.addEventListener("drop", (event) => { event.preventDefault(); $("#dropZone").classList.remove("is-dragging"); const file = event.dataTransfer.files?.[0]; if (file) { const input = $("#videoInput"); const transfer = new DataTransfer(); transfer.items.add(file); input.files = transfer.files; input.dispatchEvent(new Event("change")); } });
    $("#projectFilters")?.addEventListener("click", (event) => { const button = event.target.closest("[data-filter]"); if (!button) return; state.filter = button.dataset.filter; try { localStorage.setItem("furia-filter", state.filter); } catch (_) {}; $$(".filter-pill").forEach((item) => item.classList.toggle("is-active", item === button)); renderProjects(); });
    $("#shortlistSort")?.addEventListener("change", (event) => { state.sort = event.target.value; try { localStorage.setItem("furia-sort", state.sort); } catch (_) {}; renderGlobalShortlist(); });
    $(".project-tabs")?.addEventListener("click", (event) => { const tab = event.target.closest("[data-project-tab]"); if (!tab) return; state.projectTab = tab.dataset.projectTab; renderProjectScreen(); });
    $("#importModal")?.addEventListener("click", (event) => { if (event.target.id === "importModal") closeImport(); });
    document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeImport(); if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "o") { event.preventDefault(); openImport(); } });
    initBoot();
    initSignal();
    initWindowManager(document);
    loadProjects();
    refreshQueue();
    window.setInterval(refreshQueue, 2500);
  }

  init();
})();
