/* ═══════════════════════════════════════════════════════════════════════════
   O ESTÚDIO

   A casa é a que ele mandou. O motor é o que já existia.

   O que veio no zip escolhia os cortes assim: pegava as oito primeiras faixas
   com som, dava a cada uma um título tirado de uma lista de oito frases
   prontas, e calculava a nota a partir da duração e da posição na fila. A tela
   ficava linda e não media nada. Isso saiu inteiro.

   No lugar entrou o que ele pediu de volta pelo nome: o console ao vivo, os
   blocos, o painel, o CHUB, o Gemini, a transcrição, a seleção, o corte e o
   render — tudo pelas mesmas rotas que o programa sempre teve. Nenhuma peça do
   motor foi copiada para cá.

   Três regras que ficam valendo em cada tela deste arquivo:

     1. Nada de número inventado. Se o motor não disse, a tela não escreve.
     2. Ele nunca abre pasta e nunca digita comando. Se precisa de arquivo,
        tem botão.
     3. Erro aparece. Falha calada custa a tarde dele.
   ═══════════════════════════════════════════════════════════════════════════ */

(() => {
  "use strict";

  const estado = {
    fontes: [],
    resumo: {},
    fonte: null,       // a fonte aberta agora {chave, nome, projeto, ...}
    rodada: null,      // a rodada dessa fonte {id, cortes[], trechos[]}
    corte: null,       // o id do corte aberto na revisão
    tela: "overview",
    aba: "analyze",
    ordem: "score",
    filtro: "all",
    moendo: false,
    trabalho: null,    // o id do job que está rodando
    blocos: null,
    ajustes: null,
  };

  try {
    estado.filtro = localStorage.getItem("furia-filtro") || estado.filtro;
    estado.ordem = localStorage.getItem("furia-ordem") || estado.ordem;
    estado.aba = localStorage.getItem("furia-aba") || estado.aba;
  } catch (_) {}

  const $ = (selector, escopo = document) => escopo.querySelector(selector);
  const $$ = (selector, escopo = document) => [...escopo.querySelectorAll(selector)];

  function escapar(valor) {
    return String(valor ?? "").replace(/[&<>'"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[c]));
  }
  const atributo = (valor) => escapar(valor).replace(/\n/g, " ");

  function relogio(segundos = 0) {
    const total = Math.max(0, Math.round(Number(segundos) || 0));
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    const dois = (n) => String(n).padStart(2, "0");
    return h ? `${h}:${dois(m)}:${dois(s)}` : `${m}:${dois(s)}`;
  }

  /* O ".mp4" no fim do título não informa nada — todas as fontes são vídeo — e
     rouba espaço num nome que já vem com sessenta caracteres do YouTube. */
  const semExtensao = (nome) => String(nome || "").replace(/\.[a-z0-9]{2,4}$/i, "");

  function tamanho(bytes = 0) {
    const giga = Number(bytes) / 1073741824;
    if (giga >= 1) return `${giga.toFixed(1)} GB`;
    return `${Math.max(1, Math.round(Number(bytes) / 1048576))} MB`;
  }

  async function pedir(url, opcoes = {}) {
    let resposta;
    try {
      resposta = await fetch(url, opcoes);
    } catch (_) {
      // O programa é local. Se o fetch morreu, o servidor caiu — e essa é uma
      // frase útil, ao contrário de "Failed to fetch".
      throw new Error("O programa parou de responder. Feche a janela preta e abra de novo.");
    }
    const corpo = await resposta.json().catch(() => ({}));
    if (!resposta.ok) throw new Error(corpo.error || corpo.erro || `Não deu certo (${resposta.status}).`);
    return corpo;
  }

  function aviso(mensagem, tipo = "default") {
    const alvo = $("#toast");
    if (!alvo) return;
    alvo.textContent = mensagem;
    alvo.className = `toast is-visible${tipo === "error" ? " is-error" : tipo === "success" ? " is-success" : ""}`;
    window.clearTimeout(aviso.timer);
    aviso.timer = window.setTimeout(() => { alvo.className = "toast"; }, 5200);
  }

  /* ═══ O CONSOLE ═════════════════════════════════════════════════════════
     Ele pediu pelo nome, e é a peça que mais paga a si mesma: é a única que
     responde "o que está acontecendo agora" sem ele abrir uma pasta.

     Cada linha vem do motor pelo mesmo canal que a interface antiga sempre
     usou. Nada é inventado aqui — o que a máquina não disser, não aparece. */

  const CONSOLE = { linhas: [], teto: 600 };

  function ligarOCanal() {
    if (typeof window.io !== "function") {
      // Sem o canal a tela continua de pé; só não narra. Rodar assim é o caso
      // de abrir o desenho sem o motor, e não é motivo para quebrar nada.
      escreverNoConsole("O canal do motor não abriu. As telas funcionam; o que a máquina fizer não vai aparecer aqui.", "warning");
      return;
    }
    const canal = window.io();
    canal.on("progress", (dado) => {
      escreverNoConsole(dado?.message || "", dado?.level || "info", dado?.time);
      pulsar(dado?.level);
    });
    canal.on("status", (dado) => {
      const tipo = dado?.status || "";
      const carga = dado?.data || {};
      if (tipo === "clip_ready") {
        // Corte a corte, ao vivo: com uma rodada de trinta minutos, ver o
        // primeiro corte nascer é a diferença entre esperar e desconfiar.
        marcarNoRelogio(`CORTE ${carga.delivered || "?"} DE ${carga.expected || "?"}`);
        if (estado.rodada && Number(carga.project_id) === Number(estado.rodada.id)) recarregarRodada();
      }
      if (tipo === "complete_done") {
        terminarDeMoer(true);
        if (carga.project_id) abrirRodada(carga.project_id);
        aviso(`Pronto: ${carga.total_clips || 0} cortes.`, "success");
      }
      if (tipo === "source_import_complete") {
        // A fonte chegou. Fecha a janela de importar, atualiza a mesa e abre a
        // fonte já baixada — o gesto dele é um só: colei o link, quero cortar.
        terminarDeMoer(true);
        fecharImportar();
        const campo = $("#linkFonte");
        if (campo) campo.value = "";
        aviso("Vídeo baixado e na mesa.", "success");
        abrirAFonteBaixada(carga.path || carga.absolute_path || "");
      }
      if (tipo === "cancelled") { terminarDeMoer(false); aviso("Trabalho parado.", "default"); }
      if (tipo === "error") {
        terminarDeMoer(false);
        // A mensagem de erro do motor vai INTEIRA para o console e resumida
        // para o aviso: o aviso some em cinco segundos, o console fica.
        escreverNoConsole(carga.message || "erro sem descrição", "error");
        aviso(String(carga.message || "Deu erro.").slice(0, 140), "error");
      }
    });
    canal.on("job_update", (trabalho) => {
      if (!trabalho || trabalho.id !== estado.trabalho) return;
      if (["succeeded", "failed", "cancelled"].includes(trabalho.state)) terminarDeMoer(trabalho.state === "succeeded");
    });
    canal.on("disconnect", () => escreverNoConsole("O canal do motor caiu.", "warning"));
    canal.on("connect", () => marcarNoRelogio(estado.moendo ? "MOENDO" : "PARADO"));
  }

  /* O console tem que ter MEMÓRIA.

     Um canal ao vivo só mostra o que passou enquanto a página estava aberta.
     Na prática isso quer dizer: ele recarrega a tela no meio de meia hora de
     trabalho e o console fica em branco, como se nada estivesse acontecendo —
     que é o pior momento possível para a tela parecer vazia.

     Então, ao abrir, o estúdio pergunta ao motor se tem trabalho rodando e
     puxa o que já foi dito. É a mesma informação que a interface antiga só
     tinha enquanto ninguém apertava F5. */
  async function recuperarOTrabalho() {
    let trabalhos;
    try {
      trabalhos = (await pedir("/api/jobs")).jobs || [];
    } catch (_) { return; }
    const rodando = trabalhos.find((t) => ["running", "queued"].includes(t.state));
    if (!rodando) return;
    estado.trabalho = rodando.id;
    estado.moendo = true;
    marcarNoRelogio("MOENDO");
    const parar = $("#btnCancelWork");
    if (parar) parar.hidden = false;
    try {
      const dados = await pedir(`/api/jobs/${rodando.id}/events?limit=300`);
      for (const evento of dados.events || []) {
        escreverNoConsole(evento.message || "", evento.level || "info",
          horaLocal(evento.created_at));
      }
      escreverNoConsole("— daqui para baixo é ao vivo —", "warning");
    } catch (_) { /* sem histórico o console segue ao vivo, só sem o começo */ }
    abrirOConsole(true);
  }

  /* A hora guardada é UTC; a hora dele é a do relógio dele.

     O motor grava `created_at` em UTC. Recortar os caracteres 11 a 19 dessa
     string dava a hora de Greenwich, enquanto as linhas ao vivo usavam o
     relógio da máquina. O console dele ficou assim:

         18:35:29  Processando 4 segmentos de fala...
         16:28:57  — daqui para baixo é ao vivo —

     Três horas para trás no meio da lista. Duas horas diferentes na mesma tela
     é pior do que nenhuma: ele não sabe mais qual das duas é a de agora. */
  function horaLocal(carimbo) {
    if (!carimbo) return "";
    const quando = new Date(carimbo);
    if (Number.isNaN(quando.getTime())) return String(carimbo).slice(11, 19);
    return quando.toTimeString().slice(0, 8);
  }

  function escreverNoConsole(texto, nivel = "info", hora = "") {
    if (!texto) return;
    CONSOLE.linhas.push({ texto: String(texto), nivel, hora: hora || new Date().toTimeString().slice(0, 8) });
    if (CONSOLE.linhas.length > CONSOLE.teto) CONSOLE.linhas.splice(0, CONSOLE.linhas.length - CONSOLE.teto);
    pintarOConsole();
  }

  function pintarOConsole() {
    const alvo = $("#consoleLines");
    if (!alvo) return;
    if (!CONSOLE.linhas.length) {
      alvo.innerHTML = `<p class="console-idle">A máquina está parada. Quando você mandar moer uma fonte, cada passo aparece aqui.</p>`;
    } else {
      alvo.innerHTML = CONSOLE.linhas
        .map((l) => `<p class="console-line is-${escapar(l.nivel)}"><time>${escapar(l.hora)}</time><span>${escapar(l.texto)}</span></p>`)
        .join("");
      if ($("#consoleFollow")?.checked) alvo.scrollTop = alvo.scrollHeight;
    }
    const conta = $("#consoleCount");
    if (conta) conta.textContent = `${CONSOLE.linhas.length} linha${CONSOLE.linhas.length === 1 ? "" : "s"}`;
  }

  function pulsar(nivel) {
    const luz = $("#consoleLight");
    if (!luz) return;
    luz.dataset.nivel = nivel === "error" ? "error" : nivel === "warning" ? "warning" : "ok";
    luz.classList.remove("is-pulse");
    void luz.offsetWidth;
    luz.classList.add("is-pulse");
  }

  function abrirOConsole(abrir) {
    const casa = $("#consoleShell");
    if (!casa) return;
    casa.hidden = abrir === undefined ? !casa.hidden : !abrir;
    if (!casa.hidden) pintarOConsole();
  }

  function marcarNoRelogio(texto) {
    const alvo = $("#systemClock");
    if (alvo) alvo.textContent = texto;
  }

  /* ═══ MOER ══════════════════════════════════════════════════════════════
     O botão que faz a máquina trabalhar. É a rota completa do motor: silêncio,
     transcrição, contexto, Gemini quando configurado, seleção, ranqueamento,
     corte, legenda, miniatura. Meia hora de trabalho, e por isso o console
     abre junto — tela parada durante meia hora é tela que parece travada. */

  async function moer() {
    if (estado.moendo) { abrirOConsole(true); return; }
    if (!estado.fonte?.chave) { aviso("Escolha uma fonte primeiro.", "error"); return; }
    const botao = $("#btnProjectAnalyze");
    if (botao) { botao.disabled = true; botao.textContent = "Começando…"; }
    try {
      const resposta = await pedir("/api/process/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_path: estado.fonte.chave,
          user_context: estado.ajustes?.channel_context || "",
        }),
      });
      estado.trabalho = resposta.job_id || null;
      estado.moendo = true;
      marcarNoRelogio("MOENDO");
      abrirOConsole(true);
      $("#btnCancelWork").hidden = false;
      escreverNoConsole(`Moendo ${estado.fonte.nome}.`, "info");
      pintarAFonte();
    } catch (erro) {
      aviso(erro.message, "error");
      escreverNoConsole(erro.message, "error");
      abrirOConsole(true);
    } finally {
      if (botao) { botao.disabled = false; botao.innerHTML = "Moer a fonte <span>→</span>"; }
    }
  }

  function terminarDeMoer(deuCerto) {
    estado.moendo = false;
    estado.trabalho = null;
    marcarNoRelogio(deuCerto ? "PRONTO" : "PARADO");
    const parar = $("#btnCancelWork");
    if (parar) parar.hidden = true;
    carregarAMesa();
    pintarAFonte();
  }

  /* Parar tem de dizer a verdade sobre o que aconteceu.

     No console dele apareceu cinco vezes seguidas "Pedido de parada enviado. O
     motor para no próximo passo." — e nada parou, porque não havia nada
     rodando: o trabalho era um fantasma de um uso anterior do programa.

     Prometer a mesma coisa cinco vezes é pior do que não fazer nada. Agora,
     antes de prometer, o programa confere o estado de verdade do trabalho: se
     ele já acabou, morreu ou nunca existiu, a tela diz isso e volta a ficar
     parada, em vez de continuar dizendo que vai parar. */
  async function pararOTrabalho() {
    if (!estado.trabalho) { terminarDeMoer(false); return; }

    let situacao = null;
    try {
      const resposta = await pedir(`/api/jobs/${estado.trabalho}`);
      situacao = (resposta.job || resposta).state || "";
    } catch (_) {
      // Sem resposta sobre o trabalho, seguimos e tentamos parar assim mesmo.
    }

    if (situacao && !["running", "queued", "cancel_requested"].includes(situacao)) {
      escreverNoConsole(
        "Não tinha nada rodando: este trabalho ficou de um uso anterior do programa.",
        "warning",
      );
      terminarDeMoer(false);
      return;
    }

    try {
      await pedir("/api/process/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: estado.trabalho }),
      });
      escreverNoConsole("Pedido de parada enviado. O motor para no próximo passo.", "warning");
      // O botão sai da tela: apertar de novo não adianta e repetir a mesma
      // frase só faz parecer que o programa não ouviu.
      const parar = $("#btnCancelWork");
      if (parar) parar.hidden = true;
    } catch (erro) { aviso(erro.message, "error"); }
  }

  /* ═══ AS JANELAS ════════════════════════════════════════════════════════
     O gerenciador de janelas veio dele e está intacto: arrastar pelo título,
     foco, empilhamento, minimizar, bandeja embaixo e posição lembrada. */

  let arrasto = null;
  const janelas = new Map();

  function bandeja() {
    let alvo = $("#windowTray");
    if (!alvo) {
      alvo = document.createElement("div");
      alvo.id = "windowTray";
      alvo.className = "window-tray";
      alvo.setAttribute("aria-label", "Janelas minimizadas");
      document.body.appendChild(alvo);
    }
    return alvo;
  }

  function lerPosicao(id) {
    try { return JSON.parse(localStorage.getItem(`furia-janela:${id}`) || "null"); } catch (_) { return null; }
  }
  function guardarPosicao(id, x, y) {
    try { localStorage.setItem(`furia-janela:${id}`, JSON.stringify({ x: Math.round(x), y: Math.round(y) })); } catch (_) {}
  }

  function focar(elemento) {
    const familia = elemento.closest(".screen") || document;
    $$(".window.wm-focused", familia).forEach((item) => item.classList.remove("wm-focused"));
    elemento.classList.add("wm-focused");
    $$(".window.wm-ready", familia).forEach((item, i) => item.style.setProperty("--wm-z", String(10 + i)));
    elemento.style.setProperty("--wm-z", "60");
  }

  /* A bandeja só mostra o que está GUARDADO.

     No zip ela listava todas as janelas, abertas inclusive — uma fileira de
     botões que não fazem nada, ocupando uma faixa da tela o tempo todo. Numa
     tela de 768px de altura essa faixa custa: ela cobria a linha de números da
     mesa. Bandeja de restaurar serve para restaurar; janela aberta não precisa
     de botão para ser aberta de novo. */
  function esconder(elemento, escondida) {
    elemento.classList.toggle("wm-hidden", escondida);
    const item = janelas.get(elemento.dataset.windowId);
    if (!item) return;
    if (escondida) bandeja().appendChild(item.aba);
    else item.aba.remove();
  }

  function registrarJanela(elemento, indice) {
    if (!elemento || elemento.dataset.wmReady) return;
    const tela = elemento.closest(".screen")?.id || "solta";
    const tipo = ["source-window", "signal-window", "queue-window", "editor-window", "review-stage", "review-inspector", "notes-window", "console-shell"]
      .find((nome) => elemento.classList.contains(nome)) || "window";
    const id = `${tela}:${tipo}:${indice}`;
    elemento.dataset.windowId = id;
    elemento.dataset.wmReady = "1";
    // A ordem de empilhamento que o DESENHO escolheu tem que sobreviver ao
    // gerenciador. `.wm-ready` põe um z-index só para todo mundo, e aí quem
    // fica na frente passa a ser quem vem depois no HTML — foi assim que o
    // quadro de sinal subiu por cima do título da mesa. Lendo o valor antes de
    // marcar a janela, cada uma continua onde o desenho a pôs até ele mesmo
    // clicar em alguma.
    const camada = Number.parseInt(getComputedStyle(elemento).zIndex, 10);
    if (Number.isFinite(camada)) elemento.style.setProperty("--wm-z", String(camada));
    elemento.classList.add("wm-ready");
    const guardada = lerPosicao(id);
    if (guardada && window.matchMedia("(min-width: 781px)").matches) {
      elemento.style.setProperty("--wm-x", `${guardada.x}px`);
      elemento.style.setProperty("--wm-y", `${guardada.y}px`);
    }
    const barra = $(".window-bar", elemento);
    if (!barra) return;
    barra.classList.add("wm-drag-handle");
    const controles = document.createElement("span");
    controles.className = "wm-controls";
    controles.innerHTML = `<button type="button" data-wm="minimize" title="Minimizar">−</button><button type="button" data-wm="close" title="Fechar">×</button>`;
    barra.appendChild(controles);
    const aba = document.createElement("button");
    aba.type = "button";
    aba.className = "window-tray-item";
    aba.textContent = barra.querySelector("span")?.textContent?.trim() || tipo;
    aba.addEventListener("click", () => { esconder(elemento, false); focar(elemento); });
    janelas.set(id, { elemento, aba });
    controles.addEventListener("click", (evento) => {
      if (!evento.target.closest("[data-wm]")) return;
      evento.stopPropagation();
      esconder(elemento, true);
    });
    barra.addEventListener("pointerdown", (evento) => {
      if (evento.target.closest("button")) return;
      if (!window.matchMedia("(min-width: 781px)").matches) return;
      focar(elemento);
      arrasto = {
        elemento, ponteiro: evento.pointerId, x0: evento.clientX, y0: evento.clientY,
        x: Number.parseFloat(getComputedStyle(elemento).getPropertyValue("--wm-x")) || 0,
        y: Number.parseFloat(getComputedStyle(elemento).getPropertyValue("--wm-y")) || 0,
      };
      elemento.classList.add("wm-dragging");
      barra.setPointerCapture?.(evento.pointerId);
    });
    elemento.addEventListener("pointerdown", () => focar(elemento));
    elemento.addEventListener("pointermove", (evento) => {
      if (!arrasto || arrasto.elemento !== elemento || arrasto.ponteiro !== evento.pointerId) return;
      elemento.style.setProperty("--wm-x", `${arrasto.x + evento.clientX - arrasto.x0}px`);
      elemento.style.setProperty("--wm-y", `${arrasto.y + evento.clientY - arrasto.y0}px`);
    });
    elemento.addEventListener("pointerup", () => {
      if (!arrasto || arrasto.elemento !== elemento) return;
      guardarPosicao(id,
        Number.parseFloat(elemento.style.getPropertyValue("--wm-x")) || 0,
        Number.parseFloat(elemento.style.getPropertyValue("--wm-y")) || 0);
      arrasto = null;
      elemento.classList.remove("wm-dragging");
    });
  }

  function montarJanelas(escopo = document) {
    for (const [id, item] of janelas.entries()) {
      const tela = item.elemento.closest(".screen");
      if (!document.contains(item.elemento) || (tela && !tela.classList.contains("is-visible"))) {
        item.aba.remove();
        item.elemento.querySelector(".wm-controls")?.remove();
        item.elemento.classList.remove("wm-ready", "wm-focused", "wm-hidden", "wm-dragging");
        item.elemento.removeAttribute("data-wm-ready");
        item.elemento.removeAttribute("data-window-id");
        janelas.delete(id);
      }
    }
    const raiz = escopo === document ? $(".screen.is-visible") || document : escopo;
    $$(".window", raiz)
      .filter((el) => {
        const tela = el.closest(".screen");
        return !el.closest("#importModal") && !el.closest("#consoleShell") && (!tela || tela.classList.contains("is-visible"));
      })
      .forEach(registrarJanela);
  }

  document.addEventListener("pointerup", () => {
    if (!arrasto) return;
    arrasto.elemento.classList.remove("wm-dragging");
    arrasto = null;
  });

  /* ═══ NAVEGAR ═══════════════════════════════════════════════════════════ */

  const TITULOS = {
    overview: ["Mesa", "Seu material de hoje"],
    projects: ["Biblioteca", "As fontes na pasta de trabalho"],
    project: ["Fonte", "—"],
    shortlist: ["Cortes", "O que a máquina separou"],
    review: ["Revisão", "Decidir com o material na frente"],
    painel: ["Painel", "O que já foi publicado rendeu"],
    settings: ["Ajustes", "Como a máquina trabalha"],
  };

  function navegar(tela) {
    estado.tela = tela;
    $$(".screen").forEach((item) => item.classList.toggle("is-visible", item.dataset.screen === tela));
    $$("[data-screen-link]").forEach((item) => item.classList.toggle("is-active", item.dataset.screenLink === tela));
    const titulo = TITULOS[tela] || TITULOS.overview;
    $("#topContext").textContent = titulo[0];
    $("#topSubcontext").textContent = tela === "project" ? semExtensao(estado.fonte?.nome) || "—" : titulo[1];
    window.scrollTo({ top: 0, behavior: "smooth" });
    if (tela === "overview") pintarAMesa();
    if (tela === "projects") pintarABiblioteca();
    if (tela === "shortlist") pintarOsCortes();
    if (tela === "review") pintarARevisao();
    if (tela === "painel") carregarOPainel();
    if (tela === "settings") carregarOsAjustes();
    montarJanelas();
  }

  /* ═══ A MESA E A BIBLIOTECA ═════════════════════════════════════════════
     A coisa que a tela lista é a FONTE — o vídeo no disco. No zip que ele
     mandou o objeto principal era um "projeto" vazio esperando um vídeo; no
     motor de verdade o projeto só nasce quando a máquina moe. Listar projetos
     vazios seria mostrar caixas que não existem. */

  const quadroDaFonte = (chave) => `/api/fonte/quadro?chave=${encodeURIComponent(chave)}`;

  async function carregarAMesa() {
    try {
      const dados = await pedir("/api/estudio/mesa");
      estado.fontes = dados.fontes || [];
      estado.resumo = dados.resumo || {};
      pintarAMesa();
      pintarABiblioteca();
    } catch (erro) { aviso(erro.message, "error"); }
  }

  function pintarNumeros() {
    const r = estado.resumo || {};
    $("#metricProjects").textContent = r.fontes || 0;
    $("#metricReview").textContent = r.para_rever || 0;
    $("#metricApproved").textContent = r.aprovados || 0;
    $("#metricExported").textContent = r.cortes || 0;
    $("#navProjectCount").textContent = r.fontes || 0;
    $("#navReviewCount").textContent = r.para_rever || 0;
  }

  function selo(fonte) {
    if (!fonte.projeto) return "AINDA NÃO MOÍDA";
    if (fonte.para_rever) return `${fonte.para_rever} PARA REVER`;
    if (fonte.aprovados) return `${fonte.aprovados} APROVADO${fonte.aprovados === 1 ? "" : "S"}`;
    return `${fonte.cortes} CORTE${fonte.cortes === 1 ? "" : "S"}`;
  }

  function cartaoDaFonte(fonte) {
    return `<button class="project-card" data-fonte="${atributo(fonte.chave)}">
      <div class="project-thumb"><img src="${quadroDaFonte(fonte.chave)}" alt="" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('div'),{className:'project-thumb-fallback',textContent:'SEM QUADRO'}))"><span class="project-card-badge">${escapar(selo(fonte))}</span></div>
      <div class="project-card-body">
        <div class="project-card-title">${escapar(semExtensao(fonte.nome))}</div>
        <div class="project-card-meta"><span>${escapar(tamanho(fonte.bytes))}</span><span>${fonte.projeto ? "já moída" : "na fila"}</span></div>
        <div class="project-card-status"><b>${fonte.cortes ? `${fonte.cortes} corte${fonte.cortes === 1 ? "" : "s"}` : "moer para achar os cortes"}</b><span>→</span></div>
      </div></button>`;
  }

  function pintarAMesa() {
    pintarNumeros();
    const recentes = $("#recentProjects");
    if (recentes) {
      recentes.innerHTML = estado.fontes.length
        ? estado.fontes.slice(0, 5).map((f) => `<button class="recent-row" data-fonte="${atributo(f.chave)}"><span class="recent-thumb"><img src="${quadroDaFonte(f.chave)}" alt="" loading="lazy" onerror="this.remove()"></span><span class="recent-copy"><strong>${escapar(semExtensao(f.nome))}</strong><small>${escapar(selo(f))}</small></span><span class="recent-arrow">→</span></button>`).join("")
        : `<div class="empty-state compact"><span class="empty-symbol">+</span><div><strong>Nenhuma fonte ainda.</strong><p>Traga um vídeo para a mesa e a máquina começa a trabalhar.</p></div></div>`;
      ligarOsBotoes(recentes);
    }
    pintarOSinal();
  }

  function pintarABiblioteca() {
    const alvo = $("#projectsGrid");
    if (!alvo) return;
    let lista = [...estado.fontes];
    if (estado.filtro === "processing") lista = lista.filter((f) => f.projeto && !f.cortes);
    if (estado.filtro === "ready_review") lista = lista.filter((f) => f.para_rever > 0);
    if (estado.filtro === "empty") lista = lista.filter((f) => !f.projeto);
    alvo.innerHTML = lista.length
      ? lista.map(cartaoDaFonte).join("")
      : `<div class="empty-state"><span class="empty-symbol">+</span><h3>${estado.fontes.length ? "Nenhuma fonte neste filtro." : "A primeira fonte começa aqui."}</h3><p>${estado.fontes.length ? "Escolha outro filtro." : "Traga um vídeo para a pasta de trabalho."}</p></div>`;
    ligarOsBotoes(alvo);
  }

  function pintarOSinal() {
    const alvo = $("#signalNodes");
    if (!alvo) return;
    const fontes = estado.fontes.slice(0, 6);
    $("#signalNodeCount").textContent = `${fontes.length} FONTE${fontes.length === 1 ? "" : "S"}`;
    if (!fontes.length) {
      alvo.innerHTML = ["FONTE", "RITMO", "CORTE", "EXPORT"].map((rotulo, i) => `<div class="signal-ghost signal-ghost-${i}" aria-hidden="true"><span></span><b>${rotulo}</b></div>`).join("");
      return;
    }
    alvo.innerHTML = fontes.map((f, i) => `<button class="signal-node" style="--float-delay:${i * -0.55}s" data-fonte="${atributo(f.chave)}" aria-label="Abrir ${atributo(f.nome)}"><img src="${quadroDaFonte(f.chave)}" alt="" loading="lazy" onerror="this.remove()"><span class="signal-node-label">${escapar(semExtensao(f.nome))}</span></button>`).join("");
    ligarOsBotoes(alvo);
    arrumarOSinal();
  }

  function arrumarOSinal() {
    const palco = $("#signalStage");
    const nos = $$(".signal-node", palco || document);
    if (!palco || !nos.length) return;
    const caixa = palco.getBoundingClientRect();
    const rx = Math.min(caixa.width * 0.34, 190);
    const ry = Math.min(caixa.height * 0.28, 118);
    const mx = Number(palco.style.getPropertyValue("--mouse-x")) || 0;
    const my = Number(palco.style.getPropertyValue("--mouse-y")) || 0;
    nos.forEach((no, i) => {
      const angulo = (i / nos.length) * Math.PI * 2 - Math.PI / 2;
      no.style.left = `${caixa.width / 2 + Math.cos(angulo) * rx - no.offsetWidth / 2}px`;
      no.style.top = `${caixa.height / 2 + Math.sin(angulo) * ry - no.offsetHeight / 2}px`;
      no.style.transform = `translate3d(${mx * (12 + i * 2)}px, ${my * (10 + i)}px, 0)`;
    });
  }

  /* ═══ ABRIR UMA FONTE ═══════════════════════════════════════════════════ */

  async function abrirFonte(chave) {
    const fonte = estado.fontes.find((f) => f.chave === chave);
    if (!fonte) return;
    estado.fonte = fonte;
    estado.rodada = null;
    estado.corte = null;
    estado.blocos = null;
    if (fonte.projeto) await carregarRodada(fonte.projeto);
    pintarAFonte();
    navegar("project");
  }

  /* Depois de baixar, abrir a fonte sozinho.

     O motor devolve o caminho onde salvou. A mesa lista por chave relativa à
     pasta de trabalho, então basta achar na lista recarregada a fonte cujo
     nome de arquivo bate. Se não achar — porque ele mandou salvar noutro lugar
     —, a mesa recarregada ainda mostra tudo e ele escolhe. Nunca fica sem
     saída. */
  async function abrirAFonteBaixada(caminho) {
    await carregarAMesa();
    const nome = String(caminho).replace(/\\/g, "/").split("/").pop();
    if (!nome) { navegar("projects"); return; }
    const achada = estado.fontes.find((f) => f.nome === nome);
    if (achada) await abrirFonte(achada.chave);
    else navegar("projects");
  }

  async function carregarRodada(id) {
    try {
      estado.rodada = await pedir(`/api/estudio/rodada/${id}`);
      estado.corte = estado.rodada.cortes?.[0]?.id ?? null;
    } catch (erro) { aviso(erro.message, "error"); }
  }

  async function abrirRodada(id) {
    await carregarAMesa();
    const fonte = estado.fontes.find((f) => Number(f.projeto) === Number(id));
    if (fonte) estado.fonte = fonte;
    await carregarRodada(id);
    estado.aba = "shortlist";
    pintarAFonte();
    navegar("project");
  }

  async function recarregarRodada() {
    if (!estado.rodada?.id) return;
    const antes = estado.corte;
    await carregarRodada(estado.rodada.id);
    if (antes && estado.rodada.cortes?.some((c) => c.id === antes)) estado.corte = antes;
    pintarAFonte();
    pintarOsCortes();
    pintarARevisao();
  }

  function pintarAFonte() {
    const fonte = estado.fonte;
    if (!fonte) return;
    const rodada = estado.rodada;
    $("#projectTitle").textContent = semExtensao(fonte.nome);
    $("#projectMeta").textContent = rodada
      ? `${relogio(rodada.segundos)} · ${tamanho(fonte.bytes)} · moída em ${(rodada.quando || "").slice(0, 16).replace("T", " ")}`
      : `${tamanho(fonte.bytes)} · ainda não moída`;
    const marca = $("#projectState");
    marca.textContent = estado.moendo ? "MOENDO" : rodada ? `${rodada.cortes.length} CORTE${rodada.cortes.length === 1 ? "" : "S"}` : "NA FILA";
    marca.className = `project-state ${estado.moendo ? "processing" : rodada ? "ready_review" : "ready"}`;
    $("#projectTabCount").textContent = rodada?.cortes?.length || 0;
    const botao = $("#btnProjectAnalyze");
    if (botao) botao.innerHTML = estado.moendo ? "Moendo… <span>·</span>" : rodada ? "Moer de novo <span>→</span>" : "Moer a fonte <span>→</span>";
    $$(".project-tab").forEach((aba) => aba.classList.toggle("is-active", aba.dataset.projectTab === estado.aba));
    // A tela sabe em que aba está: a revisão precisa de outro orçamento de
    // altura, e quem decide isso é o CSS, não mais JavaScript.
    $("#screen-project").dataset.aba = estado.aba;
    try { localStorage.setItem("furia-aba", estado.aba); } catch (_) {}
    const corpo = $("#projectBody");
    if (estado.aba === "analyze") corpo.innerHTML = desenharEntender();
    if (estado.aba === "shortlist") corpo.innerHTML = desenharOsCortesDaFonte();
    if (estado.aba === "review") corpo.innerHTML = desenharARevisao();
    if (estado.aba === "blocos") { corpo.innerHTML = desenharOsBlocos(); carregarOsBlocos(); }
    ligarOsBotoes(corpo);
  }

  /* O `#t=` no fim do endereço é o que garante que o corte abre no lugar certo.

     Mandar `currentTime` pelo JavaScript só funciona depois que o navegador
     leu a duração do arquivo, e essa leitura pode demorar — no teste ela ainda
     não tinha acontecido cinco segundos depois de abrir a tela. Enquanto isso,
     todo corte mostrava o segundo zero da mesma entrevista, que é exatamente a
     queixa: "mostra apenas o mesmo trecho do vídeo".

     O `#t=` é um pedaço do próprio endereço: o navegador já abre ali, sem
     esperar por código nenhum. O ajuste pelo JavaScript continua logo abaixo
     como reforço, para o caso de o corte mudar sem a página recarregar. */
  const videoDaFonte = (chave) => `/api/fonte/video?chave=${encodeURIComponent(chave)}`;

  function desenharEntender() {
    const fonte = estado.fonte;
    const rodada = estado.rodada;
    const trechos = rodada?.trechos || [];
    const cortes = rodada?.cortes || [];
    return `<div class="editor-grid">
      <section class="window editor-window"><div class="window-bar"><span>01 / A FONTE</span><span class="window-status">${estado.moendo ? "MOENDO" : "LOCAL"}</span></div>
        <div class="editor-window-body">
          <div class="window-subhead"><span class="subhead-label">VÍDEO / PRÉVIA</span><span class="status-chip">${escapar(fonte.chave)}</span></div>
          <div class="video-frame"><video controls preload="metadata" src="${videoDaFonte(fonte.chave)}"></video></div>
          <div class="editor-stats">
            <div class="editor-stat"><b>${rodada ? relogio(rodada.segundos) : "—"}</b><span>DURAÇÃO</span></div>
            <div class="editor-stat"><b>${trechos.length || "—"}</b><span>TRECHOS FALADOS</span></div>
            <div class="editor-stat"><b>${cortes.length}</b><span>CORTES</span></div>
          </div>
        </div></section>

      <section class="window editor-window"><div class="window-bar"><span>02 / O QUE A MÁQUINA FAZ</span><span class="window-status">MOTOR</span></div>
        <div class="editor-window-body">
          <p class="understanding-copy">Moer é o processo inteiro de uma vez: tirar o silêncio, transcrever, ler o contexto, escolher os trechos, ranquear, cortar, legendar e fazer a miniatura. Leva tempo — o console mostra cada passo.</p>
          <div class="signal-list">
            <div class="signal-row"><span>Transcrição</span><i style="--signal:${trechos.length ? "92%" : "5%"};--signal-color:var(--coral)"></i><b>${trechos.length ? `${trechos.length} trechos` : "sai ao moer"}</b></div>
            <div class="signal-row"><span>Seleção</span><i style="--signal:${cortes.length ? "86%" : "5%"};--signal-color:var(--cyan)"></i><b>${cortes.length ? `${cortes.length} cortes` : "sai ao moer"}</b></div>
            <div class="signal-row"><span>Revisão</span><i style="--signal:${cortes.length ? `${Math.round(cortes.filter((c) => c.status !== "suggested").length / cortes.length * 100)}%` : "5%"};--signal-color:var(--sun)"></i><b>${cortes.length ? `${cortes.filter((c) => c.status !== "suggested").length} de ${cortes.length}` : "depois dos cortes"}</b></div>
          </div>
          <div class="editor-actions">
            <button class="button" data-acao="console">Ver o console</button>
            <button class="button button-coral" data-acao="moer" ${estado.moendo ? "disabled" : ""}>${estado.moendo ? "Moendo…" : rodada ? "Moer de novo" : "Moer a fonte"} <span>→</span></button>
          </div>
        </div></section>

      <section class="window editor-window transcript-window"><div class="window-bar"><span>03 / A FALA</span><span class="window-status">${trechos.length ? `${trechos.length} TRECHOS` : "VAZIO"}</span></div>
        <div class="editor-window-body">${trechos.length
          ? `<div class="transcript-tools"><span class="tiny-label">PROCURAR NA FALA</span><input class="transcript-search" type="search" placeholder="uma palavra que ele disse…" aria-label="Procurar na fala"></div>
             <div class="transcript-snippet">${trechos.slice(0, 200).map((t) => `<div class="transcript-line" data-ir="${t.start}" tabindex="0" role="button"><time>${relogio(t.start)}</time><p>${escapar(t.text)}</p></div>`).join("")}</div>`
          : `<div class="transcript-empty"><span>⌁</span><div><strong>A fala aparece aqui depois de moer.</strong><p>É a transcrição da própria fonte, com o tempo de cada frase.</p></div></div>`}</div></section>
    </div>`;
  }

  /* ═══ OS CORTES ═════════════════════════════════════════════════════════ */

  const NOME_DO_ESTADO = { suggested: "SUGERIDO", reviewing: "AJUSTADO", approved: "APROVADO", rejected: "RECUSADO" };

  /* O quadro do cartão sai da FONTE, no segundo em que o corte começa.

     Antes ele só aparecia quando o render tinha deixado uma miniatura — e o
     render nem sempre deixa. Ele abriu uma rodada com mais de setenta cortes e
     disse: "no próprio programa não dá para ver os cortes". Era isso: setenta
     retângulos cinzas escritos SEM MINIATURA. Tirando da fonte, o quadro
     existe sempre, inclusive antes de qualquer render. */
  function quadroDoCorte(corte) {
    const chave = estado.rodada?.chave;
    if (!chave) return "";
    return `/api/estudio/quadro?chave=${encodeURIComponent(chave)}&em=${Math.max(0, corte.start || 0).toFixed(2)}`;
  }

  function emOrdem(cortes) {
    const lista = [...cortes];
    if (estado.ordem === "duration") return lista.sort((a, b) => b.duration - a.duration);
    if (estado.ordem === "status") return lista.sort((a, b) => a.status.localeCompare(b.status));
    return lista.sort((a, b) => b.score - a.score);
  }

  function cartaoDoCorte(corte) {
    const acesas = Math.max(1, Math.round(Number(corte.score || 0) / 20));
    return `<article class="clip-card${corte.status === "rejected" ? " is-rejected" : ""}" data-corte="${corte.id}">
      <div class="clip-thumb"><img src="${corte.thumbnail || quadroDoCorte(corte)}" alt="" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('div'),{className:'clip-fallback',textContent:'SEM QUADRO'}))"><span class="score-badge">${corte.score}</span></div>
      <div class="clip-content">
        <div class="clip-card-top"><span>${NOME_DO_ESTADO[corte.status] || "SUGERIDO"}</span><span>${relogio(corte.duration)}</span></div>
        <h3>${escapar(corte.title)}</h3>
        <div class="clip-time">${relogio(corte.start)} — ${relogio(corte.end)}</div>
        <div class="clip-signal" aria-label="Nota ${corte.score} de 100"><span>NOTA</span><b>${Array.from({ length: 5 }, (_, i) => `<i class="${i < acesas ? "is-on" : ""}"></i>`).join("")}</b></div>
        <div class="reason-list">${(corte.reasons || []).map((r) => `<span>${escapar(r)}</span>`).join("") || `<span>sem razão registrada</span>`}</div>
      </div>
      <div class="clip-actions">
        <button class="clip-open" data-acao="rever" data-corte="${corte.id}">Rever <span>→</span></button>
        <button class="small-decision approve" data-acao="decidir" data-decisao="approved" data-corte="${corte.id}" title="Aprovar">✓</button>
        <button class="small-decision reject" data-acao="decidir" data-decisao="rejected" data-corte="${corte.id}" title="Recusar">×</button>
      </div></article>`;
  }

  function desenharOsCortesDaFonte() {
    const cortes = estado.rodada?.cortes || [];
    if (!cortes.length) {
      return `<div class="project-shortlist-layout"><div class="empty-state"><span class="empty-symbol">✦</span><h3>Ainda não tem corte desta fonte.</h3><p>Moer é o passo que acha os cortes — e leva alguns minutos.</p><button class="button button-coral" data-acao="moer">Moer a fonte <span>→</span></button></div></div>`;
    }
    return `<div class="project-shortlist-layout"><div class="shortlist-grid">${emOrdem(cortes).map(cartaoDoCorte).join("")}</div></div>`;
  }

  function pintarOsCortes() {
    const alvo = $("#shortlistGrid");
    if (!alvo) return;
    const cortes = estado.rodada?.cortes || [];
    $("#shortlistCount").textContent = `${cortes.length} corte${cortes.length === 1 ? "" : "s"}`;
    alvo.innerHTML = cortes.length
      ? emOrdem(cortes).map(cartaoDoCorte).join("")
      : `<div class="empty-state"><span class="empty-symbol">✦</span><h3>Escolha uma fonte primeiro.</h3><p>Os cortes aparecem depois que a máquina moe um vídeo.</p><button class="button button-coral" data-acao="biblioteca">Abrir a Biblioteca <span>→</span></button></div>`;
    ligarOsBotoes(alvo);
    const lado = $("#shortlistChubContext");
    if (lado) { lado.innerHTML = desenharOCHUB(); ligarOsBotoes(lado); }
  }

  /* ═══ A REVISÃO ═════════════════════════════════════════════════════════
     A janela onde ele decide. Duas coisas mudaram do zip para cá, e as duas
     vieram de queixa dele sobre a versão antiga:

       · a alça se arrasta em cima da ONDA do som, não num campo de segundos.
         "não sabia o que eu estava medindo, não sabia onde era o início que eu
         queria porque o próprio corte não permitia voltar."

       · a janela da onda mostra margem FORA do corte de propósito: para
         escolher onde entrar é preciso ouvir a frase anterior. */

  function desenharARevisao() {
    const rodada = estado.rodada;
    const cortes = rodada?.cortes || [];
    const corte = cortes.find((c) => c.id === estado.corte) || cortes[0];
    if (!corte) return `<div class="empty-state"><span class="empty-symbol">◉</span><h3>Nenhum corte para rever.</h3><p>Moa uma fonte e os cortes aparecem aqui.</p></div>`;
    estado.corte = corte.id;

    const duracao = Math.max(1, Number(rodada.segundos) || corte.end);
    const trechos = (rodada.trechos || []).filter((t) => t.end > corte.start && t.start < corte.end);
    const legendas = trechos.length
      ? `<div class="review-caption-layer" aria-live="polite">${trechos.map((t) => `<span class="review-caption" data-start="${t.start}" data-end="${t.end}">${escapar(t.text)}</span>`).join("")}</div>`
      : "";

    return `<div class="review-grid">
      <section class="window review-stage"><div class="window-bar"><span>01 / O CORTE</span><span class="window-status">${NOME_DO_ESTADO[corte.status] || "SUGERIDO"}</span></div>
        <div class="review-stage-body">
          <div class="review-frame">
            <video class="review-video" controls preload="metadata" src="${videoDaFonte(rodada.chave)}#t=${Math.max(0, corte.start).toFixed(2)}" data-start="${corte.start}" data-end="${corte.end}"></video>
            ${legendas}<div class="review-safe-label">9:16 / ÁREA SEGURA</div>
          </div>
          <div class="review-controls">
            <!-- A onda é o controle. O número embaixo é consequência do
                 arrasto, nunca o contrário. -->
            <div class="onda" id="onda" data-corte="${corte.id}" data-duracao="${duracao}">
              <canvas id="ondaTela"></canvas>
              <div class="onda-selecao" id="ondaSelecao"></div>
              <button class="onda-alca onda-alca-in" id="alcaIn" aria-label="Início do corte"></button>
              <button class="onda-alca onda-alca-out" id="alcaOut" aria-label="Fim do corte"></button>
              <span class="onda-agulha" id="ondaAgulha" aria-hidden="true"></span>
            </div>
            <div class="review-range-readout"><b>ENTRA <span class="review-start-readout">${relogio(corte.start)}</span></b><b>SAI <span class="review-end-readout">${relogio(corte.end)}</span></b><span class="review-length-readout">${relogio(corte.duration)} de corte</span></div>
            <div class="review-preview-tools">
              <button class="button button-cyan" data-acao="tocar">Tocar o corte <span>▶</span></button>
              <label class="loop-toggle"><input type="checkbox" class="review-loop"><span>repetir</span></label>
              <button class="button" data-acao="guardar-bordas">Guardar as bordas</button>
            </div>
          </div>
          <div class="review-actions">
            <button class="reject-action" data-acao="decidir" data-decisao="rejected" data-corte="${corte.id}">Recusar</button>
            <button class="adjust-action" data-acao="cortes">Voltar aos cortes</button>
            <button class="approve-action" data-acao="decidir" data-decisao="approved" data-corte="${corte.id}">Aprovar <span>→</span></button>
            ${corte.exportUrl ? `<button class="export-action" data-acao="abrir-pasta">Abrir a pasta <span>↗</span></button>` : `<button class="export-action" disabled>Sem arquivo ainda</button>`}
          </div>
        </div></section>

      <aside class="window review-inspector"><div class="window-bar"><span>02 / POR QUE ESTE</span><span class="window-status">NOTA ${corte.score}</span></div>
        <div class="review-inspector-body">
          <h3>${escapar(corte.title)}</h3>
          <p class="review-muted" id="bordasDoCorte">${relogio(corte.start)} — ${relogio(corte.end)} · ${relogio(corte.duration)}${corte.ajustado ? " · bordas ajustadas por você" : ""}</p>
          <div class="review-signal-block"><span class="tiny-label">O QUE FEZ ELE ENTRAR</span>
            ${(corte.reasons || []).map((r, i) => `<div class="review-reason"><i class="reason-dot ${["pink", "cyan", "yellow"][i % 3]}"></i><span>${escapar(r)}</span></div>`).join("") || `<p class="review-muted">A máquina não registrou razão para este corte.</p>`}
            <!-- A nota é da máquina sobre o palpite dela mesma. Vai escrito
                 assim de propósito: número que a ferramenta dá para o que a
                 ferramenta escolheu não mede desempenho de nada. -->
            <p class="review-muted score-note">A nota é o palpite da máquina, não uma promessa. O que rendeu de verdade está no Painel.</p>
          </div>
          <div class="review-tools"><button class="button button-sun" data-acao="seo">Gerar título e descrição</button><span class="seo-preview" id="seoSaida">Sai daqui quando você mandar.</span></div>
          <div class="review-transcript">
            <div class="transcript-tools"><span class="tiny-label">A FALA DESTE CORTE</span><input class="transcript-search" type="search" placeholder="procurar…" aria-label="Procurar na fala"></div>
            ${trechos.length ? trechos.map((t) => `<p data-ir="${t.start}" tabindex="0" role="button"><time>${relogio(t.start)}</time>${escapar(t.text)}</p>`).join("") : `<p class="review-muted">${escapar(corte.transcript || "Sem transcrição para este trecho.")}</p>`}
          </div>
        </div></aside>
    </div>`;
  }

  function pintarARevisao() {
    const alvo = $("#reviewWorkspace");
    if (!alvo) return;
    const cortes = estado.rodada?.cortes || [];
    const decididos = cortes.filter((c) => c.status !== "suggested").length;
    $("#reviewProgressText").textContent = `${decididos} de ${cortes.length} decididos`;
    $("#reviewProgressBar").style.width = cortes.length ? `${Math.round(decididos / cortes.length * 100)}%` : "0%";
    alvo.innerHTML = cortes.length ? desenharARevisao() : `<div class="empty-state"><span class="empty-symbol">◉</span><h3>Escolha uma fonte moída.</h3><p>O vídeo, a fala e a decisão aparecem juntos aqui.</p></div>`;
    ligarOsBotoes(alvo);
  }

  /* ── a onda ─────────────────────────────────────────────────────────────
     Vem do motor: energia média do áudio em fatias iguais. Desenhada com o
     devicePixelRatio na conta, senão numa tela boa ela sai borrada. */

  const ONDA = { picos: [], inicio: 0, fim: 0, entra: 0, sai: 0, chave: "" };

  async function montarAOnda() {
    const caixa = $("#onda");
    if (!caixa || !estado.rodada) return;
    const cortes = estado.rodada.cortes || [];
    const corte = cortes.find((c) => c.id === Number(caixa.dataset.corte));
    if (!corte) return;

    // A margem de fora é o ponto: sem ouvir a frase anterior não dá para
    // escolher onde entrar. Um quinto do corte de cada lado, no mínimo cinco
    // segundos — corte curto sem piso ficaria sem margem nenhuma.
    const folga = Math.max(5, (corte.end - corte.start) * 0.2);
    const inicio = Math.max(0, corte.start - folga);
    const fim = Math.min(Number(estado.rodada.segundos) || corte.end + folga, corte.end + folga);
    ONDA.inicio = inicio; ONDA.fim = fim; ONDA.entra = corte.start; ONDA.sai = corte.end;

    desenharAOnda();
    posicionarAsAlcas();
    try {
      const dados = await pedir(`/api/waveform?video_path=${encodeURIComponent(estado.rodada.chave)}&start=${inicio}&end=${fim}&buckets=520`);
      ONDA.picos = dados.peaks || [];
      desenharAOnda();
    } catch (erro) {
      // Sem a onda as alças continuam funcionando — só que às cegas. Dizer
      // isso é melhor do que uma faixa cinza sem explicação.
      escreverNoConsole(`Não deu para desenhar a onda: ${erro.message}`, "warning");
    }
  }

  function desenharAOnda() {
    const tela = $("#ondaTela");
    const caixa = $("#onda");
    if (!tela || !caixa) return;
    const escala = window.devicePixelRatio || 1;
    const largura = Math.max(1, Math.round(caixa.clientWidth));
    const altura = Math.max(1, Math.round(caixa.clientHeight));
    tela.width = Math.round(largura * escala);
    tela.height = Math.round(altura * escala);
    const ctx = tela.getContext("2d");
    ctx.setTransform(escala, 0, 0, escala, 0, 0);
    ctx.clearRect(0, 0, largura, altura);
    if (!ONDA.picos.length) return;
    const passo = largura / ONDA.picos.length;
    const chao = altura - 2;
    ctx.fillStyle = "#111111";
    ONDA.picos.forEach((pico, i) => {
      const alto = Math.max(1, pico * (altura - 8));
      ctx.fillRect(i * passo, chao - alto, Math.max(1, passo - 0.4), alto);
    });
  }

  const paraFracao = (segundos) => (segundos - ONDA.inicio) / Math.max(0.001, ONDA.fim - ONDA.inicio);
  const paraSegundos = (fracao) => ONDA.inicio + fracao * (ONDA.fim - ONDA.inicio);

  function posicionarAsAlcas() {
    const caixa = $("#onda");
    if (!caixa) return;
    const a = Math.max(0, Math.min(1, paraFracao(ONDA.entra))) * 100;
    const b = Math.max(0, Math.min(1, paraFracao(ONDA.sai))) * 100;
    $("#alcaIn").style.left = `${a}%`;
    $("#alcaOut").style.left = `${b}%`;
    const selecao = $("#ondaSelecao");
    selecao.style.left = `${a}%`;
    selecao.style.width = `${Math.max(0, b - a)}%`;
    $(".review-start-readout").textContent = relogio(ONDA.entra);
    $(".review-end-readout").textContent = relogio(ONDA.sai);
    $(".review-length-readout").textContent = `${relogio(ONDA.sai - ONDA.entra)} de corte`;
    // O painel do lado mostra as mesmas bordas. Dois números da mesma coisa
    // discordando na tela é o jeito mais rápido de ele parar de acreditar nos
    // dois — então o de lá anda junto com o arrasto daqui.
    const espelho = $("#bordasDoCorte");
    if (espelho) {
      espelho.textContent = `${relogio(ONDA.entra)} — ${relogio(ONDA.sai)} · ${relogio(ONDA.sai - ONDA.entra)}`;
    }
  }

  /* O arrasto escuta na JANELA, não na alça, e o ouvinte é UM SÓ.

     A primeira versão prendia o ponteiro na alça e escutava o movimento nela.
     No teste de navegador o `pointerdown` chegava e nenhum `pointermove`
     chegava depois: a alça tem catorze pixels de largura, o cursor sai de
     cima dela no primeiro pixel de movimento, e quando a prisão do ponteiro
     não pega os eventos passam a ir para quem estiver embaixo do cursor.
     Resultado: a alça não saía do lugar.

     Escutando na janela, o arrasto continua enquanto o botão estiver apertado,
     mesmo com o cursor longe da alça — que é como todo controle de arrastar
     tem de se comportar. E os dois ouvintes ficam AQUI FORA de propósito: a
     revisão se redesenha a cada decisão, e pendurar um par novo a cada
     redesenho seria juntar ouvintes mortos a tarde inteira. */
  let arrastando = null;
  let arrastou = false;

  function moverAAlca(evento) {
    const caixa = $("#onda");
    if (!arrastando || !caixa) return;
    arrastou = true;
    const r = caixa.getBoundingClientRect();
    const fracao = Math.max(0, Math.min(1, (evento.clientX - r.left) / r.width));
    const segundos = paraSegundos(fracao);
    // Um segundo é o piso: abaixo disso não é corte, é engano de arrasto.
    if (arrastando === "in") ONDA.entra = Math.min(segundos, ONDA.sai - 1);
    else ONDA.sai = Math.max(segundos, ONDA.entra + 1);
    posicionarAsAlcas();
    const video = $(".review-video");
    if (video) video.currentTime = arrastando === "in" ? ONDA.entra : ONDA.sai;
  }

  window.addEventListener("pointermove", moverAAlca);
  window.addEventListener("pointerup", () => { arrastando = null; });

  function ligarAsAlcas(escopo) {
    const caixa = $("#onda", escopo);
    if (!caixa || caixa.dataset.ligado) return;
    caixa.dataset.ligado = "1";

    for (const [alca, qual] of [[$("#alcaIn"), "in"], [$("#alcaOut"), "out"]]) {
      alca.addEventListener("pointerdown", (evento) => {
        evento.preventDefault();
        arrastando = qual;
      });
      // Teclado: um décimo por seta, um segundo com Shift. Precisão de corte
      // não pode depender de firmeza de mão.
      alca.addEventListener("keydown", (evento) => {
        const passo = evento.shiftKey ? 1 : 0.1;
        if (evento.key === "ArrowLeft" || evento.key === "ArrowRight") {
          evento.preventDefault();
          const delta = evento.key === "ArrowLeft" ? -passo : passo;
          if (qual === "in") ONDA.entra = Math.max(ONDA.inicio, Math.min(ONDA.entra + delta, ONDA.sai - 1));
          else ONDA.sai = Math.min(ONDA.fim, Math.max(ONDA.sai + delta, ONDA.entra + 1));
          posicionarAsAlcas();
        }
      });
    }
    // Clicar na onda leva o vídeo até ali: é como ele procura a frase.
    // Soltar a alça em cima da onda também conta como clique para o navegador;
    // sem esta guarda, todo arrasto terminaria pulando o vídeo para outro
    // ponto — bem no instante em que ele acabou de escolher a borda.
    caixa.addEventListener("click", (evento) => {
      if (arrastou) { arrastou = false; return; }
      if (evento.target.closest(".onda-alca")) return;
      const r = caixa.getBoundingClientRect();
      const video = $(".review-video");
      if (video) { video.currentTime = paraSegundos((evento.clientX - r.left) / r.width); video.play().catch(() => {}); }
    });
  }

  async function guardarAsBordas() {
    if (!estado.corte) return;
    try {
      await pedir(`/api/clips/${estado.corte}/adjust`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          adjustment: { start: ONDA.entra, end: ONDA.sai },
          source_duration: estado.rodada?.segundos || 0,
          transcript_segments: estado.rodada?.trechos || [],
        }),
      });
      aviso("Bordas guardadas. O corte voltou para decidir.", "success");
      escreverNoConsole(`Bordas do corte ${estado.corte}: ${relogio(ONDA.entra)} → ${relogio(ONDA.sai)}.`, "success");
      await recarregarRodada();
    } catch (erro) { aviso(erro.message, "error"); }
  }

  async function decidir(corteId, decisao) {
    try {
      await pedir(`/api/clips/${corteId}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: decisao }),
      });
      aviso(decisao === "approved" ? "Aprovado." : "Recusado.", decisao === "approved" ? "success" : "default");
      await recarregarRodada();
      await carregarAMesa();
    } catch (erro) { aviso(erro.message, "error"); }
  }

  async function gerarSeo() {
    const corte = (estado.rodada?.cortes || []).find((c) => c.id === estado.corte);
    if (!corte) return;
    const saida = $("#seoSaida");
    if (saida) saida.textContent = "Pedindo à máquina…";
    try {
      await pedir("/api/process/seo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript: corte.transcript || corte.title, clip_id: corte.id }),
      });
      if (saida) saida.textContent = "A máquina está escrevendo. O resultado aparece no console e no corte.";
      abrirOConsole(true);
    } catch (erro) {
      if (saida) saida.textContent = erro.message;
      aviso(erro.message, "error");
    }
  }

  async function abrirOsRegistros() {
    try {
      const resposta = await pedir("/api/open-logs", { method: "POST" });
      // Sem ambiente gráfico o comando falha e a rota devolve ONDE fica. Dizer
      // o caminho ainda resolve; ficar calado, não.
      aviso(resposta.path ? `Registros em ${resposta.path}` : "A pasta dos registros abriu.", "success");
    } catch (erro) { aviso(erro.message, "error"); }
  }

  async function abrirAPasta() {
    try {
      await pedir("/api/open_folder", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) });
      aviso("A pasta dos cortes abriu no Windows.", "success");
    } catch (erro) { aviso(erro.message, "error"); }
  }

  /* ═══ OS BLOCOS ═════════════════════════════════════════════════════════
     Ele pediu de volta pelo nome. Bloco é um pedaço de material já revisado
     por gente — vem do acervo, não deste programa. É a diferença entre "a
     máquina acha que isso é bom" e "isso já foi separado por alguém". */

  function desenharOsBlocos() {
    return `<div class="blocos-layout">
      <section class="window editor-window"><div class="window-bar"><span>BLOCOS DESTA FONTE</span><span class="window-status" id="blocosEstado">LENDO…</span></div>
        <div class="editor-window-body">
          <div class="transcript-tools"><span class="tiny-label">PROCURAR NOS BLOCOS</span><input class="transcript-search" id="blocosBusca" type="search" placeholder="um tema, um nome…" aria-label="Procurar nos blocos"></div>
          <div id="blocosLista" class="blocos-lista"><p class="review-muted">Lendo o acervo…</p></div>
        </div></section>
      <aside class="window notes-window"><div class="window-bar"><span>O QUE É UM BLOCO</span><span class="window-status" id="blocosOrigem">—</span></div>
        <div class="notes-art" aria-hidden="true"></div>
        <h2>Pedaços inteiros da fonte.</h2>
        <!-- Bloco vem de dois lugares, e a diferença é grande demais para
             ficar implícita: um passou por gente, o outro é a leitura da
             máquina. Cada cartão diz de qual dos dois ele é. -->
        <p><b>Do acervo</b> — trecho que já passou por revisão humana. Vale como referência do que já foi cortado desta fonte.</p>
        <p><b>Leitura do Furia</b> — o programa achou onde uma pergunta começa e a resposta acaba. É palpite dele, e o cartão diz isso.</p>
        <p class="review-muted">Nenhum dos dois é corte. Bloco é onde procurar corte.</p>
      </aside></div>`;
  }

  async function carregarOsBlocos() {
    const lista = $("#blocosLista");
    const marca = $("#blocosEstado");
    if (!lista) return;
    try {
      const dados = await pedir("/api/editorial/blocks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_path: estado.fonte?.chave || "",
          duration_s: estado.rodada?.segundos || null,
          segments: estado.rodada?.trechos || [],
          q: $("#blocosBusca")?.value || "",
          limit: 60,
        }),
      });
      estado.blocos = dados;
      const blocos = dados.blocks || [];
      // "reviewed" quer dizer que alguém de carne e osso passou por esses
      // blocos. Isso muda o peso do que está na tela e por isso vai escrito.
      if (marca) {
        marca.textContent = blocos.length
          ? `${blocos.length} · ${dados.reviewed ? "REVISADO" : "LEITURA DO FURIA"}`
          : "NENHUM";
      }
      const origem = $("#blocosOrigem");
      if (origem) origem.textContent = blocos.length ? (dados.reviewed ? "ACERVO" : "FURIA") : "—";
      if (!blocos.length) {
        // A mensagem é do próprio motor e diz o que FAZER — "a transcrição não
        // rende trechos longos o bastante", "importe os blocos do Acervo deste
        // vídeo". Trocar isso por um texto genérico meu seria jogar fora a
        // única frase da tela que resolve o problema dele.
        lista.innerHTML = `<p class="review-muted">${escapar(dados.error || dados.message || "Nenhum bloco para esta fonte.")}</p>`;
        return;
      }
      lista.innerHTML = blocos.map((b) => {
        // Bloco não tem título porque ninguém escreveu um. O que ele tem é
        // posição, que é fato — então o cabeçalho é a posição, e o texto é a
        // fala literal, não um resumo inventado aqui.
        const onde = b.start != null ? `${relogio(b.start)} — ${relogio(b.end)}` : "";
        const marcas = [...(b.topics || [])].slice(0, 6);
        return `<article class="bloco">
          <div class="bloco-topo"><b>${escapar(b.label || "trecho")}</b><span>${escapar(onde)}</span></div>
          ${b.trigger_question ? `<p class="bloco-pergunta">${escapar(b.trigger_question)}</p>` : ""}
          ${b.summary ? `<p>${escapar(String(b.summary).slice(0, 340))}</p>` : ""}
          ${marcas.length ? `<div class="reason-list">${marcas.map((t) => `<span>${escapar(t)}</span>`).join("")}</div>` : ""}
          <div class="bloco-pe"><span>${escapar(b.trust_tier || b.source?.title || "")}</span>${b.duration ? `<span>${relogio(b.duration)}</span>` : ""}</div>
        </article>`;
      }).join("");
    } catch (erro) {
      if (marca) marca.textContent = "ERRO";
      lista.innerHTML = `<p class="review-muted">${escapar(erro.message)}</p>`;
    }
  }

  /* ═══ O PAINEL ══════════════════════════════════════════════════════════
     Tudo aqui é medido FORA: desempenho de post publicado. Nenhum número
     deste painel sai deste programa — um número que a ferramenta gera sobre o
     que a ferramenta fez não mede nada, e é por isso que a nota do corte NÃO
     entra aqui. */

  async function carregarOPainel() {
    const corpo = $("#painelCorpo");
    if (!corpo) return;
    const conta = $("#painelConta")?.value || "";
    const plataforma = $("#painelPlataforma")?.value || "instagram";
    corpo.innerHTML = `<div class="empty-state"><span class="empty-symbol">◒</span><h3>Lendo o espelho do CHUB…</h3></div>`;
    try {
      const dados = await pedir(`/api/painel?conta=${encodeURIComponent(conta)}&plataforma=${encodeURIComponent(plataforma)}`);
      const seletor = $("#painelConta");
      if (seletor && !seletor.options.length && (dados.contas || []).length) {
        seletor.innerHTML = dados.contas.map((c) => `<option value="${atributo(c)}"${c === dados.conta ? " selected" : ""}>${escapar(c)}</option>`).join("");
      }
      if (!dados.espelho?.disponivel) {
        corpo.innerHTML = `<div class="empty-state"><span class="empty-symbol">▤</span><h3>O espelho do CHUB não está aqui.</h3><p>O painel mostra desempenho de post publicado. Sem o espelho não há o que mostrar — e inventar número seria pior que a tela vazia.</p></div>`;
        return;
      }
      corpo.innerHTML = desenharOPainel(dados);
      ligarOsBotoes(corpo);
    } catch (erro) {
      corpo.innerHTML = `<div class="empty-state"><span class="empty-symbol">▤</span><h3>Não deu para ler o painel.</h3><p>${escapar(erro.message)}</p></div>`;
    }
  }

  /* A conta que importa é a razão contra a mediana da própria conta: 1,00 é o
     desempenho típico dela. O que interessa é a DISTÂNCIA até 1,00, e é isso
     que a barra desenha — o valor bruto não diz se foi bom. */
  function barra(mediana) {
    const valor = Number(mediana) || 0;
    const acima = valor >= 1;
    // A linha do meio é 1,00. Cada metade da faixa vale uma distância de 1,00 —
    // ou seja, a barra cheia à direita é 2,00× e a barra cheia à esquerda é
    // zero. Metade, e não a faixa inteira: com 100% a barra do tema mais forte
    // passava por cima da coluna do número e o valor sumia da tela.
    const largura = Math.min(50, Math.abs(valor - 1) * 50);
    const estourou = Math.abs(valor - 1) > 1 ? " estourou" : "";
    return `<i class="barra ${acima ? "acima" : "abaixo"}${estourou}" style="--largura:${largura.toFixed(1)}%"></i>`;
  }

  /* Os nomes vêm do espelho com o rótulo do banco: gancho é `familia`
     ("news-peg", "conflito"), tema é `slug` ("saude", "seguranca"). Traduzir
     aqui é o mínimo — hífen e minúscula de campo de banco não é como ele fala
     dessas coisas. */
  const humano = (bruto) => String(bruto || "")
    .replace(/[-_]+/g, " ")
    .replace(/^./, (c) => c.toUpperCase());

  function linhaDoPainel(item) {
    const valor = Number(item.mediana) || 0;
    const nome = humano(item.familia || item.slug || item.gancho || item.tema || item.nome);
    return `<div class="painel-linha"><span class="painel-nome" title="${atributo(nome)}">${escapar(nome || "sem nome")}</span><span class="painel-barra">${barra(valor)}</span><b class="painel-valor">${valor.toFixed(2)}×</b><small>${item.n || 0} posts</small></div>`;
  }

  function desenharOPainel(dados) {
    const ganchos = (dados.ganchos || []).slice(0, 8);
    const melhores = dados.temas?.melhores || [];
    const piores = dados.temas?.piores || [];
    return `<div class="painel-grade">
      <section class="window editor-window"><div class="window-bar"><span>GANCHOS QUE RENDERAM</span><span class="window-status">${escapar(dados.plataforma || "")}</span></div>
        <div class="editor-window-body">
          <p class="review-muted">1,00× é o desempenho típico desta conta. A barra mostra a distância até ele — para cima rendeu mais, para baixo rendeu menos.</p>
          <div class="painel-lista">${ganchos.map(linhaDoPainel).join("") || `<p class="review-muted">Sem gancho com amostra suficiente.</p>`}</div>
        </div></section>
      <section class="window editor-window"><div class="window-bar"><span>TEMAS</span><span class="window-status">${escapar(dados.conta || "")}</span></div>
        <div class="editor-window-body">
          <span class="tiny-label">OS QUE MAIS RENDERAM</span>
          <div class="painel-lista">${melhores.map(linhaDoPainel).join("") || `<p class="review-muted">Sem amostra.</p>`}</div>
          <span class="tiny-label">OS QUE MENOS RENDERAM</span>
          <div class="painel-lista">${piores.map(linhaDoPainel).join("") || `<p class="review-muted">Sem amostra.</p>`}</div>
        </div></section>
      <aside class="window notes-window"><div class="window-bar"><span>DE ONDE VÊM ESTES NÚMEROS</span><span class="window-status">CHUB</span></div>
        <h2>Nada aqui saiu deste programa.</h2>
        <p>São posts que foram publicados e medidos. A nota que a máquina dá a um corte é palpite sobre o que ainda não saiu; isto é resultado do que já saiu. Os dois nunca se somam.</p>
        <div class="signal-legend"><div><i class="legend-cyan"></i><span>Espelho</span><b>${escapar((dados.espelho?.gerado_em || "").slice(0, 10) || "sem data")}</b></div><div><i class="legend-sun"></i><span>Adversários</span><b>${dados.papeis?.adversarios || 0}</b></div><div><i class="legend-coral"></i><span>Aliados</span><b>${dados.papeis?.aliados || 0}</b></div></div>
      </aside></div>`;
  }

  function desenharOCHUB() {
    // O lado da tela de cortes. Curto de propósito: é lembrete, não painel.
    return `<section class="chub-memory"><div class="chub-memory-head"><span class="tiny-label">MEMÓRIA DA CAMPANHA</span><span class="chub-account" id="chubConta">—</span></div>
      <p class="chub-explainer">O que já foi publicado e rendeu. É referência do passado — não muda a nota deste corte e não prevê nada.</p>
      <button class="button button-cyan" data-acao="painel">Abrir o painel</button></section>`;
  }

  const CHUB = { ligado: false, conta: "" };

  async function lerOEstadoDoCHUB() {
    try {
      const dados = await pedir("/api/campaign-hub/status");
      CHUB.ligado = Boolean(dados.available || dados.memory_available);
      CHUB.conta = estado.ajustes?.campaign_hub_account || "";
    } catch (_) {
      // O CHUB é opcional de propósito: a máquina dele trabalha desligada, e
      // sem a memória da campanha o resto do programa continua inteiro.
      CHUB.ligado = false;
    }
    const alvo = $("#chubConta");
    if (alvo) alvo.textContent = CHUB.ligado ? (CHUB.conta || "ligado") : "sem memória";
  }

  /* ═══ OS AJUSTES ════════════════════════════════════════════════════════
     Ele não abre arquivo de configuração e não digita comando. Tudo que a
     máquina precisa saber tem que ter um campo aqui. */

  const CAMPOS = [
    { chave: "gemini_api_key", nome: "Chave do Gemini", tipo: "password", ajuda: "Sem ela a máquina trabalha só com o que roda nesta máquina. Fica guardada aqui e não sai daqui." },
    { chave: "gemini_model", nome: "Modelo do Gemini", tipo: "text", ajuda: "" },
    { chave: "ai_backend", nome: "Quem pensa", tipo: "escolha", opcoes: ["auto", "gemini", "ollama", "local"], ajuda: "\"auto\" usa o melhor que estiver disponível na hora." },
    { chave: "whisper_model", nome: "Ouvido (transcrição)", tipo: "escolha", opcoes: ["tiny", "base", "small", "medium", "large"], ajuda: "Maior ouve melhor e demora mais." },
    { chave: "language", nome: "Idioma", tipo: "text", ajuda: "" },
    { chave: "cut_duration", nome: "Tamanho do corte (segundos)", tipo: "number", ajuda: "" },
    { chave: "silence_threshold", nome: "O que conta como silêncio (dB)", tipo: "number", ajuda: "Mais negativo, mais sensível." },
    { chave: "min_silence_duration", nome: "Silêncio mínimo (segundos)", tipo: "number", ajuda: "" },
    { chave: "padding", nome: "Folga nas bordas (segundos)", tipo: "number", ajuda: "" },
    { chave: "render_preset", nome: "Formato de saída", tipo: "escolha", opcoes: ["shorts", "reels", "tiktok", "square", "wide"], ajuda: "" },
    { chave: "campaign_hub_account", nome: "Conta da campanha", tipo: "text", ajuda: "" },
    { chave: "channel_context", nome: "O que este canal é", tipo: "texto-longo", ajuda: "A máquina lê isto antes de escolher os cortes. Quanto mais claro, melhor a escolha." },
    { chave: "output_dir", nome: "Onde salvar os cortes", tipo: "pasta", ajuda: "Vazio salva na pasta do programa." },
  ];

  async function carregarOsAjustes() {
    const corpo = $("#settingsBody");
    if (!corpo) return;
    try {
      estado.ajustes = await pedir("/api/settings");
      corpo.innerHTML = `<div class="settings-grade">
        <section class="window editor-window"><div class="window-bar"><span>A MÁQUINA</span><span class="window-status">v${escapar(estado.ajustes.program_version || "")}</span></div>
          <div class="editor-window-body">${CAMPOS.map(desenharCampo).join("")}</div></section>
        <!-- Aqui NÃO tem link para a interface antiga.
             Ele já disse o que acha disso: "quando fui em ajustes e ajustes
             completos simplesmente abriu o furia antigo, PORQUE????". Um botão
             que devolve para o lugar de onde ele pediu para sair é o programa
             admitindo que não dá conta — e me deixa confortável em deixar
             buraco aqui. Se faltar alguma coisa, ela se constrói aqui dentro.
             O que entra no lugar é o que ele realmente não consegue fazer
             sozinho: chegar nos arquivos sem abrir pasta nenhuma. -->
        <aside class="window notes-window"><div class="window-bar"><span>ONDE AS COISAS FICAM</span><span class="window-status">DISCO</span></div>
          <h2>Nada aqui exige abrir pasta.</h2>
          <p>Os cortes prontos, o registro do que a máquina fez e as fontes ficam em pastas desta máquina. Os botões abrem a pasta certa no Windows.</p>
          <div class="settings-portas">
            <button type="button" data-acao="abrir-pasta">Abrir a pasta dos cortes ↗</button>
            <button type="button" data-acao="abrir-registros">Abrir a pasta dos registros ↗</button>
          </div>
          <p class="review-muted">Se der problema, o console tem um botão de copiar: o texto de lá é o que resolve mais rápido.</p>
        </aside></div>`;
      ligarOsBotoes(corpo);
    } catch (erro) {
      corpo.innerHTML = `<div class="empty-state"><span class="empty-symbol">⌘</span><h3>Não deu para ler os ajustes.</h3><p>${escapar(erro.message)}</p></div>`;
    }
  }

  function desenharCampo(campo) {
    const valor = estado.ajustes?.[campo.chave] ?? "";
    const guardada = estado.ajustes?.[`${campo.chave}_configured`];
    const ajuda = campo.ajuda ? `<small class="campo-ajuda">${escapar(campo.ajuda)}</small>` : "";
    let controle;
    if (campo.tipo === "escolha") {
      controle = `<select data-ajuste="${campo.chave}">${campo.opcoes.map((o) => `<option value="${atributo(o)}"${String(valor) === o ? " selected" : ""}>${escapar(o)}</option>`).join("")}</select>`;
    } else if (campo.tipo === "texto-longo") {
      controle = `<textarea data-ajuste="${campo.chave}" rows="4">${escapar(valor)}</textarea>`;
    } else if (campo.tipo === "pasta") {
      // Nunca digitar caminho: botão que abre a janela do Windows.
      controle = `<span class="campo-pasta"><input type="text" data-ajuste="${campo.chave}" value="${atributo(valor)}" readonly placeholder="pasta do programa"><button type="button" class="button" data-acao="escolher-pasta" data-alvo="${campo.chave}">Procurar</button></span>`;
    } else if (campo.tipo === "password") {
      controle = `<input type="password" data-ajuste="${campo.chave}" value="" placeholder="${guardada ? "já guardada — deixe em branco para manter" : "cole a chave aqui"}" autocomplete="off">`;
    } else {
      controle = `<input type="${campo.tipo}" data-ajuste="${campo.chave}" value="${atributo(valor)}">`;
    }
    return `<label class="campo"><span class="campo-nome">${escapar(campo.nome)}</span>${controle}${ajuda}</label>`;
  }

  async function guardarOsAjustes() {
    const carga = {};
    $$("[data-ajuste]").forEach((campo) => {
      const chave = campo.dataset.ajuste;
      let valor = campo.value;
      if (campo.type === "number") valor = Number(valor);
      // Chave em branco quer dizer "mantém a que está guardada" — mandar
      // string vazia apagaria a chave dele sem ele ter pedido.
      if (campo.type === "password" && !String(valor).trim()) return;
      carga[chave] = valor;
    });
    try {
      await pedir("/api/settings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(carga) });
      aviso("Ajustes guardados.", "success");
      await carregarOsAjustes();
    } catch (erro) { aviso(erro.message, "error"); }
  }

  async function escolherPasta(alvo) {
    try {
      const resposta = await pedir("/api/dialog/choose", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: "folder", title: "Onde salvar os cortes" }),
      });
      const caminho = resposta.path || resposta.caminho || "";
      if (caminho) {
        const campo = $(`[data-ajuste="${alvo}"]`);
        if (campo) campo.value = caminho;
      }
    } catch (erro) { aviso(erro.message, "error"); }
  }

  /* ═══ TRAZER UMA FONTE ══════════════════════════════════════════════════
     Dois caminhos, e o primeiro é a janela do Windows: o vídeo já está nesta
     máquina, então copiar de pasta para pasta é muito mais rápido do que
     mandar dois gigabytes pelo navegador e receber de volta.

     E ele é copiado PARA DENTRO da pasta de trabalho, sempre. Apontar para o
     arquivo dá o caminho, não a permissão — o motor só lê o que está dentro da
     pasta dele, e era exatamente isso que fazia "moer" falhar sem dizer por
     quê. A cópia conta o progresso no console. */

  /* BAIXAR POR LINK — a entrada de verdade do trabalho dele.

     O log que ele mandou começa assim: cola o endereço da coletiva, o programa
     baixa vídeo e áudio, junta num MP4 e importa. O motor já sabia fazer tudo
     isso; o estúdio é que nunca chamou a rota. Sem esta função ele não
     conseguia nem COMEÇAR — e é por isso que a versão que eu tinha chamado de
     mais estável era inutilizável para ele.

     A rota é a mesma que a interface antiga sempre usou, com o mesmo canal de
     progresso: o console mostra a porcentagem descendo enquanto baixa, e o
     botão de parar continua valendo. */
  async function baixarPorLink() {
    const campo = $("#linkFonte");
    const link = (campo?.value || "").trim();
    if (!link) { aviso("Cole o link do vídeo primeiro.", "error"); campo?.focus(); return; }
    if (estado.moendo) { aviso("A máquina já está ocupada. Espere ou pare o trabalho no console.", "error"); abrirOConsole(true); return; }

    const botao = $("#btnBaixarLink");
    if (botao) { botao.disabled = true; botao.textContent = "Baixando…"; }
    abrirOConsole(true);
    escreverNoConsole(`[Fonte] Pedindo o vídeo de ${link}`, "info");
    try {
      const resposta = await pedir("/api/source/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // Sem destino: o motor decide, e o padrão dele é a pasta de trabalho.
        // Mandar o texto do campo vazio já criou uma pasta chamada "A pasta
        // será escolhida ao importar" na máquina dele uma vez.
        body: JSON.stringify({ url: link }),
      });
      estado.trabalho = resposta.job_id || null;
      estado.moendo = true;
      marcarNoRelogio("BAIXANDO");
      $("#btnCancelWork").hidden = false;
    } catch (erro) {
      aviso(erro.message, "error");
      escreverNoConsole(erro.message, "error");
    } finally {
      if (botao) { botao.disabled = false; botao.innerHTML = "Baixar <span>↓</span>"; }
    }
  }

  async function escolherNoWindows() {
    const botao = $("#btnPickNative");
    if (botao) { botao.disabled = true; botao.textContent = "Abrindo a janela…"; }
    abrirOConsole(true);
    try {
      const resposta = await pedir("/api/fonte/escolher", { method: "POST" });
      if (resposta.desistiu) return;
      fecharImportar();
      await carregarAMesa();
      if (resposta.fonte?.chave) await abrirFonte(resposta.fonte.chave);
      aviso("Fonte na mesa.", "success");
    } catch (erro) {
      aviso(erro.message, "error");
      escreverNoConsole(erro.message, "error");
    } finally {
      if (botao) { botao.disabled = false; botao.innerHTML = "Procurar no computador <span>↗</span>"; }
    }
  }

  async function enviarPeloNavegador() {
    const arquivo = $("#videoInput").files?.[0];
    if (!arquivo) return;
    const botao = $("#btnConfirmImport");
    const barra = $("#importProgress");
    botao.disabled = true;
    botao.textContent = "Enviando…";
    if (barra) barra.hidden = false;
    try {
      const forma = new FormData();
      forma.append("file", arquivo);
      forma.append("path", "uploads");
      const resposta = await pedir("/api/files/upload", { method: "POST", body: forma });
      fecharImportar();
      await carregarAMesa();
      const chave = String(resposta.path || "").replace(/\\/g, "/");
      if (chave) await abrirFonte(chave);
      aviso("Fonte na mesa.", "success");
    } catch (erro) { aviso(erro.message, "error"); }
    finally {
      botao.disabled = false;
      botao.innerHTML = "Enviar pelo navegador <span>→</span>";
      if (barra) barra.hidden = true;
      $("#videoInput").value = "";
      $("#importFileName").textContent = "Nenhum arquivo escolhido";
    }
  }

  const abrirImportar = () => { $("#importModal").hidden = false; };
  const fecharImportar = () => { $("#importModal").hidden = true; };

  /* ═══ OS BOTÕES ═════════════════════════════════════════════════════════ */

  function ligarOsBotoes(escopo = document) {
    $$("[data-fonte]", escopo).forEach((el) => {
      if (el.dataset.ligado) return;
      el.dataset.ligado = "1";
      el.addEventListener("click", () => abrirFonte(el.dataset.fonte));
    });
    $$("[data-acao]", escopo).forEach((el) => {
      if (el.dataset.ligado) return;
      el.dataset.ligado = "1";
      el.addEventListener("click", () => executar(el.dataset.acao, el.dataset));
    });
    // Só CARTÃO de corte abre a revisão ao ser clicado.
    //
    // Antes isto valia para qualquer coisa com `data-corte` — e a onda tem
    // `data-corte`. O efeito: terminar de arrastar a alça disparava um clique
    // na onda, que redesenhava a tela inteira e devolvia as bordas antigas. O
    // arrasto funcionava e sumia no mesmo gesto, que é o pior tipo de defeito:
    // parece que o programa ignorou você.
    $$(".clip-card[data-corte]", escopo).forEach((el) => {
      if (el.dataset.ligado) return;
      el.dataset.ligado = "1";
      el.addEventListener("click", (evento) => {
        if (evento.target.closest("[data-acao]")) return;
        executar("rever", el.dataset);
      });
    });
    $$("[data-ir]", escopo).forEach((linha) => {
      if (linha.dataset.ligado) return;
      linha.dataset.ligado = "1";
      const ir = () => {
        const segundos = Number(linha.dataset.ir);
        const video = $(".review-video") || $(".video-frame video");
        if (video && Number.isFinite(segundos)) { video.currentTime = segundos; video.play().catch(() => {}); }
      };
      linha.addEventListener("click", ir);
      linha.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); ir(); } });
    });
    $$(".transcript-search", escopo).forEach((campo) => {
      if (campo.dataset.ligado) return;
      campo.dataset.ligado = "1";
      if (campo.id === "blocosBusca") {
        let espera = null;
        campo.addEventListener("input", () => { window.clearTimeout(espera); espera = window.setTimeout(carregarOsBlocos, 320); });
        return;
      }
      campo.addEventListener("input", () => {
        const busca = campo.value.trim().toLocaleLowerCase();
        const casa = campo.closest(".editor-window-body, .review-transcript");
        $$(".transcript-line, .review-transcript > p[data-ir]", casa).forEach((linha) => {
          linha.hidden = Boolean(busca) && !linha.textContent.toLocaleLowerCase().includes(busca);
        });
      });
    });
    ligarOVideo(escopo);
    ligarAsAlcas(escopo);
    if ($("#onda", escopo)) montarAOnda();
    montarJanelas(escopo);
  }

  function ligarOVideo(escopo) {
    const video = $(".review-video", escopo);
    if (!video || video.dataset.ligado) return;
    video.dataset.ligado = "1";
    const legendas = $$(".review-caption", escopo);
    const repetir = $(".review-loop", escopo);
    const agulha = $("#ondaAgulha");

    /* O vídeo abre NO COMEÇO DO CORTE, não no começo da fonte.

       Este era o defeito que ele descreveu assim: *"quando eu seleciono
       qualquer um dos cortes, mostra apenas o mesmo trecho do vídeo"*. E era
       exatamente isso: o player recebia a fonte inteira e ninguém mandava
       pular. Corte 1, corte 7, corte 40 — todos abriam no segundo zero da
       mesma entrevista, então os quarenta pareciam o mesmo corte.

       O quadro só pode ser posicionado depois que o navegador lê a duração do
       arquivo; antes disso, mexer em currentTime não faz nada. Por isso a
       ordem certa é esperar o `loadedmetadata`. E se os metadados já tiverem
       chegado antes deste código rodar, o evento não dispara mais — daí a
       segunda linha. */
    const irParaOComeco = () => {
      const comeco = Number(video.dataset.start) || 0;
      if (Number.isFinite(comeco) && Math.abs(video.currentTime - comeco) > 0.05) {
        try { video.currentTime = comeco; } catch (_) { /* fonte ainda sem duração */ }
      }
    };
    video.addEventListener("loadedmetadata", irParaOComeco);
    if (video.readyState >= 1) irParaOComeco();

    video.addEventListener("timeupdate", () => {
      const agora = video.currentTime;
      legendas.forEach((l) => l.classList.toggle("is-active", agora >= Number(l.dataset.start) && agora < Number(l.dataset.end)));
      if (agulha && ONDA.fim > ONDA.inicio) {
        const f = Math.max(0, Math.min(1, paraFracao(agora)));
        agulha.style.left = `${f * 100}%`;
        agulha.hidden = agora < ONDA.inicio || agora > ONDA.fim;
      }
      if (ONDA.sai > ONDA.entra && agora >= ONDA.sai) {
        if (repetir?.checked) { video.currentTime = ONDA.entra; video.play().catch(() => {}); }
        else video.pause();
      }
    });
  }

  function executar(acao, dados = {}) {
    if (acao === "moer") return moer();
    if (acao === "console") return abrirOConsole(true);
    if (acao === "biblioteca") return navegar("projects");
    if (acao === "painel") return navegar("painel");
    if (acao === "cortes") { estado.aba = "shortlist"; pintarAFonte(); return navegar("project"); }
    if (acao === "rever") { estado.corte = Number(dados.corte); estado.aba = "review"; pintarAFonte(); return navegar("project"); }
    if (acao === "decidir") return decidir(Number(dados.corte), dados.decisao);
    if (acao === "guardar-bordas") return guardarAsBordas();
    if (acao === "tocar") {
      const video = $(".review-video");
      if (video) { video.currentTime = ONDA.entra; video.play().catch(() => aviso("Clique no vídeo para começar.", "default")); }
      return undefined;
    }
    if (acao === "seo") return gerarSeo();
    if (acao === "abrir-pasta") return abrirAPasta();
    if (acao === "abrir-registros") return abrirOsRegistros();
    if (acao === "escolher-pasta") return escolherPasta(dados.alvo);
    return undefined;
  }

  /* ═══ A IGNIÇÃO ═════════════════════════════════════════════════════════ */

  function ligarABoot() {
    const tela = $("#bootScreen");
    if (!tela) return;
    let acabou = false;
    let andado = 0;
    let contador = null;
    const falas = ["abrindo a pasta de trabalho…", "procurando as fontes…", "ligando o motor…", "pronto para cortar."];
    const fim = () => {
      if (acabou) return;
      acabou = true;
      window.clearInterval(contador);
      tela.classList.add("is-done");
      tela.setAttribute("aria-hidden", "true");
      window.setTimeout(() => tela.remove(), 450);
      try { sessionStorage.setItem("furia-boot", "1"); } catch (_) {}
    };
    let visto = false;
    try { visto = sessionStorage.getItem("furia-boot") === "1"; } catch (_) {}
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches || visto) { fim(); return; }
    tela.setAttribute("aria-hidden", "false");
    contador = window.setInterval(() => {
      andado = Math.min(100, andado + 10 + Math.round(Math.random() * 9));
      $("#bootProgress").style.width = `${andado}%`;
      $("#bootCaption").textContent = falas[Math.min(falas.length - 1, Math.floor(andado / 28))];
      if (andado >= 100) window.setTimeout(fim, 160);
    }, 95);
    $("#bootSkip")?.addEventListener("click", fim);
    window.addEventListener("keydown", (e) => { if (e.key === "Enter" && !acabou) fim(); }, { once: true });
  }

  function ligarOSinal() {
    const palco = $("#signalStage");
    if (!palco) return;
    palco.addEventListener("pointermove", (evento) => {
      const r = palco.getBoundingClientRect();
      palco.style.setProperty("--mouse-x", ((evento.clientX - r.left) / r.width - 0.5).toFixed(3));
      palco.style.setProperty("--mouse-y", ((evento.clientY - r.top) / r.height - 0.5).toFixed(3));
      palco.classList.add("is-exploring");
      arrumarOSinal();
    });
    palco.addEventListener("pointerleave", () => {
      palco.style.setProperty("--mouse-x", "0");
      palco.style.setProperty("--mouse-y", "0");
      palco.classList.remove("is-exploring");
      arrumarOSinal();
    });
    window.addEventListener("resize", () => { arrumarOSinal(); desenharAOnda(); posicionarAsAlcas(); });
  }

  function comecar() {
    $$("[data-screen-link]").forEach((el) => el.addEventListener("click", () => navegar(el.dataset.screenLink)));
    $("#btnHeroImport")?.addEventListener("click", abrirImportar);
    $("#btnProjectsImport")?.addEventListener("click", abrirImportar);
    $("#btnQuickImport")?.addEventListener("click", abrirImportar);
    $("#btnCloseImport")?.addEventListener("click", fecharImportar);
    $("#btnPickNative")?.addEventListener("click", escolherNoWindows);
    $("#btnBaixarLink")?.addEventListener("click", baixarPorLink);
    $("#linkFonte")?.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); baixarPorLink(); } });
    $("#btnConfirmImport")?.addEventListener("click", enviarPeloNavegador);
    $("#btnProjectAnalyze")?.addEventListener("click", moer);
    $("#btnTopSettings")?.addEventListener("click", () => navegar("settings"));
    $("#btnSaveSettings")?.addEventListener("click", guardarOsAjustes);
    $("#btnConsole")?.addEventListener("click", () => abrirOConsole());
    // A pasta fica na barra de cima, sempre à mão. Os cortes saem em
    // ~/FuriaClipsData/exports, que é fora da pasta do programa — ele não tem
    // como adivinhar, e disse exatamente isso: "não sei sequer onde fica a
    // pasta de cortes".
    $("#btnPasta")?.addEventListener("click", abrirAPasta);
    $("#btnConsoleClose")?.addEventListener("click", () => abrirOConsole(false));
    $("#btnConsoleClear")?.addEventListener("click", () => { CONSOLE.linhas = []; pintarOConsole(); });
    $("#btnConsoleCopy")?.addEventListener("click", () => {
      // Copiar é para ele conseguir MANDAR o que deu errado. Sem isso a única
      // forma de contar um erro é digitar de novo olhando para a tela.
      const texto = CONSOLE.linhas.map((l) => `${l.hora} ${l.texto}`).join("\n");
      navigator.clipboard?.writeText(texto).then(() => aviso("Console copiado.", "success"), () => aviso("O navegador não deixou copiar.", "error"));
    });
    $("#btnCancelWork")?.addEventListener("click", pararOTrabalho);
    $("#videoInput")?.addEventListener("change", (e) => {
      const arquivo = e.target.files?.[0];
      $("#importFileName").textContent = arquivo?.name || "Nenhum arquivo escolhido";
      $("#btnConfirmImport").disabled = !arquivo;
    });
    $("#dropZone")?.addEventListener("dragover", (e) => { e.preventDefault(); $("#dropZone").classList.add("is-dragging"); });
    $("#dropZone")?.addEventListener("dragleave", () => $("#dropZone").classList.remove("is-dragging"));
    $("#dropZone")?.addEventListener("drop", (e) => {
      e.preventDefault();
      $("#dropZone").classList.remove("is-dragging");
      const arquivo = e.dataTransfer.files?.[0];
      if (!arquivo) return;
      const campo = $("#videoInput");
      const pacote = new DataTransfer();
      pacote.items.add(arquivo);
      campo.files = pacote.files;
      campo.dispatchEvent(new Event("change"));
    });
    $("#projectFilters")?.addEventListener("click", (e) => {
      const botao = e.target.closest("[data-filter]");
      if (!botao) return;
      estado.filtro = botao.dataset.filter;
      try { localStorage.setItem("furia-filtro", estado.filtro); } catch (_) {}
      $$(".filter-pill").forEach((p) => p.classList.toggle("is-active", p === botao));
      pintarABiblioteca();
    });
    $("#shortlistSort")?.addEventListener("change", (e) => {
      estado.ordem = e.target.value;
      try { localStorage.setItem("furia-ordem", estado.ordem); } catch (_) {}
      pintarOsCortes();
      pintarAFonte();
    });
    $(".project-tabs")?.addEventListener("click", (e) => {
      const aba = e.target.closest("[data-project-tab]");
      if (!aba) return;
      estado.aba = aba.dataset.projectTab;
      pintarAFonte();
    });
    $("#painelConta")?.addEventListener("change", carregarOPainel);
    $("#painelPlataforma")?.addEventListener("change", carregarOPainel);
    $("#importModal")?.addEventListener("click", (e) => { if (e.target.id === "importModal") fecharImportar(); });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") fecharImportar();
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "o") { e.preventDefault(); abrirImportar(); }
    });

    ligarABoot();
    ligarOSinal();
    ligarOCanal();
    montarJanelas(document);
    ligarOsBotoes(document);
    carregarAMesa();
    recuperarOTrabalho();
    lerOEstadoDoCHUB();
    // Os ajustes entram cedo porque o contexto do canal vai junto na hora de
    // moer, e ele pode moer antes de abrir a tela de ajustes uma única vez.
    pedir("/api/settings").then((a) => { estado.ajustes = a; }).catch(() => {});
  }

  comecar();
})();
