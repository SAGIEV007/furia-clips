/* ═══════════════════════════════════════════════════════════════════════════
   FURIA CLIPS — ATELIÊ
   Ambientes, paleta de comandos, gaveta do registro e o ajuste de corte novo.

   Nada aqui substitui o app.js. Ele continua dono das ações; este arquivo cuida
   de onde as coisas ficam e de como o editor chega até elas.
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
    "use strict";

    const guardar = (chave, valor) => { try { localStorage.setItem(chave, valor); } catch (e) { /* aba anônima */ } };
    const lembrar = (chave) => { try { return localStorage.getItem(chave); } catch (e) { return null; } };

    /* ── ambientes ──────────────────────────────────────────────────────── */

    function irPara(slug) {
        const abas = document.querySelectorAll(".rail-tab");
        let achou = false;
        abas.forEach((aba) => {
            const alvo = aba.dataset.ambiente === slug;
            achou = achou || alvo;
            aba.classList.toggle("is-active", alvo);
            aba.setAttribute("aria-selected", alvo ? "true" : "false");
        });
        if (!achou) return false;
        document.querySelectorAll(".ambiente").forEach((amb) => {
            const alvo = amb.id === `amb-${slug}`;
            amb.hidden = !alvo;
            amb.classList.toggle("is-active", alvo);
        });
        guardar("furia.ambiente", slug);
        window.scrollTo({ top: 0, behavior: "instant" });
        return true;
    }
    window.irParaAmbiente = irPara;

    document.querySelectorAll(".rail-tab").forEach((aba) => {
        aba.addEventListener("click", () => irPara(aba.dataset.ambiente));
    });
    irPara(lembrar("furia.ambiente") || "fila");

    /* ── gaveta do registro técnico ─────────────────────────────────────── */

    const gaveta = document.getElementById("gavetaConsole");
    const puxador = document.getElementById("btnGaveta");
    const corpoGaveta = document.getElementById("gavetaCorpo");

    function abrirGaveta(abrir) {
        if (!gaveta) return;
        gaveta.dataset.aberta = abrir ? "true" : "false";
        corpoGaveta.hidden = !abrir;
        puxador.setAttribute("aria-expanded", abrir ? "true" : "false");
        guardar("furia.gaveta", abrir ? "1" : "0");
        if (abrir) marcarLidas();
    }
    puxador?.addEventListener("click", () => abrirGaveta(gaveta.dataset.aberta !== "true"));
    if (lembrar("furia.gaveta") === "1") abrirGaveta(true);

    // Quantas linhas novas desde a última vez que ele olhou, e se alguma é erro.
    // Assim o registro pode ficar fechado sem esconder que algo quebrou.
    let jaLidas = 0;
    const contagem = document.getElementById("gavetaContagem");
    function marcarLidas() {
        const linhas = document.querySelectorAll("#consoleOutput .console-line");
        jaLidas = linhas.length;
        if (contagem) { contagem.textContent = ""; contagem.removeAttribute("data-erro"); }
    }
    function conferirRegistro() {
        const linhas = document.querySelectorAll("#consoleOutput .console-line");
        if (gaveta?.dataset.aberta === "true") { jaLidas = linhas.length; return; }
        const novas = linhas.length - jaLidas;
        if (!contagem) return;
        if (novas <= 0) { contagem.textContent = ""; contagem.removeAttribute("data-erro"); return; }
        const temErro = Array.from(linhas).slice(jaLidas).some((l) => l.classList.contains("error"));
        contagem.textContent = novas > 99 ? "99+" : String(novas);
        if (temErro) contagem.setAttribute("data-erro", "true");
        else contagem.removeAttribute("data-erro");
    }
    const saida = document.getElementById("consoleOutput");
    if (saida) new MutationObserver(conferirRegistro).observe(saida, { childList: true });
    marcarLidas();

    /* ── paleta de comandos ─────────────────────────────────────────────── */

    // Com setenta e tantos botões espalhados, digitar o nome é mais rápido que
    // lembrar onde está. Os comandos são descobertos da própria página, então
    // um botão novo entra na paleta sem ninguém precisar cadastrá-lo.
    function reunirComandos() {
        const lista = [
            { nome: "Ir para a Fila", icone: "playlist_add", onde: "Ambiente", fazer: () => irPara("fila") },
            { nome: "Ir para Cortar", icone: "content_cut", onde: "Ambiente", fazer: () => irPara("cortar") },
            { nome: "Ir para Auditoria", icone: "fact_check", onde: "Ambiente", fazer: () => irPara("auditoria") },
            { nome: "Ir para o Acervo", icone: "inventory_2", onde: "Ambiente", fazer: () => irPara("acervo") },
            { nome: "Abrir o registro técnico", icone: "terminal", onde: "Janela", fazer: () => abrirGaveta(true) },
            { nome: "Alternar densidade (compacta ou confortável)", icone: "density_medium", onde: "Aparência", fazer: alternarDensidade },
        ];
        document.querySelectorAll(".ambiente button, .sidebar button").forEach((botao) => {
            if (botao.closest(".paleta") || botao.disabled) return;
            const texto = (botao.textContent || "").replace(/\s+/g, " ").trim();
            const rotulo = texto || botao.getAttribute("title") || botao.getAttribute("aria-label") || "";
            if (!rotulo || rotulo.length > 60) return;
            const ambiente = botao.closest(".ambiente");
            const aba = ambiente && document.querySelector(`.rail-tab[data-ambiente="${ambiente.id.replace("amb-", "")}"]`);
            lista.push({
                nome: rotulo,
                icone: botao.querySelector(".material-icons-round")?.textContent?.trim() || "bolt",
                onde: aba?.querySelector(".rail-tab-label")?.textContent || "Barra lateral",
                fazer: () => {
                    if (ambiente) irPara(ambiente.id.replace("amb-", ""));
                    botao.click();
                },
            });
        });
        const vistos = new Set();
        return lista.filter((item) => {
            const chave = item.nome.toLowerCase();
            if (vistos.has(chave)) return false;
            vistos.add(chave);
            return true;
        });
    }

    const fundoPaleta = document.createElement("div");
    fundoPaleta.className = "paleta-fundo";
    fundoPaleta.hidden = true;
    fundoPaleta.innerHTML = `
        <div class="paleta" role="dialog" aria-modal="true" aria-label="Buscar ação">
            <input id="paletaBusca" type="text" placeholder="Digite o que você quer fazer…" autocomplete="off" spellcheck="false">
            <div class="paleta-lista" id="paletaLista" role="listbox"></div>
        </div>`;
    document.body.appendChild(fundoPaleta);

    const buscaPaleta = fundoPaleta.querySelector("#paletaBusca");
    const listaPaleta = fundoPaleta.querySelector("#paletaLista");
    let comandos = [];
    let marcado = 0;

    function semAcento(texto) {
        return String(texto || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
    }

    function pintarPaleta() {
        const alvo = semAcento(buscaPaleta.value);
        const achados = comandos.filter((c) => semAcento(c.nome).includes(alvo)).slice(0, 40);
        marcado = Math.min(marcado, Math.max(0, achados.length - 1));
        if (!achados.length) {
            listaPaleta.innerHTML = `<div class="paleta-vazio">Nada com esse nome. Tente outra palavra.</div>`;
            return;
        }
        listaPaleta.innerHTML = achados.map((c, i) => `
            <button class="paleta-item${i === marcado ? " marcado" : ""}" data-i="${i}" role="option" aria-selected="${i === marcado}">
                <span class="material-icons-round">${c.icone}</span>
                <span>${c.nome.replace(/[<>&]/g, "")}</span>
                <small>${c.onde}</small>
            </button>`).join("");
        listaPaleta.querySelectorAll(".paleta-item").forEach((botao) => {
            botao.addEventListener("click", () => { fecharPaleta(); achados[Number(botao.dataset.i)].fazer(); });
        });
        listaPaleta.querySelector(".marcado")?.scrollIntoView({ block: "nearest" });
    }

    function abrirPaleta() {
        comandos = reunirComandos();
        buscaPaleta.value = "";
        marcado = 0;
        fundoPaleta.hidden = false;
        pintarPaleta();
        buscaPaleta.focus();
    }
    function fecharPaleta() { fundoPaleta.hidden = true; }

    document.getElementById("btnPaleta")?.addEventListener("click", abrirPaleta);
    fundoPaleta.addEventListener("mousedown", (e) => { if (e.target === fundoPaleta) fecharPaleta(); });
    buscaPaleta.addEventListener("input", () => { marcado = 0; pintarPaleta(); });
    buscaPaleta.addEventListener("keydown", (e) => {
        const total = listaPaleta.querySelectorAll(".paleta-item").length;
        if (e.key === "Escape") { fecharPaleta(); }
        else if (e.key === "ArrowDown") { e.preventDefault(); marcado = (marcado + 1) % Math.max(1, total); pintarPaleta(); }
        else if (e.key === "ArrowUp") { e.preventDefault(); marcado = (marcado - 1 + total) % Math.max(1, total); pintarPaleta(); }
        else if (e.key === "Enter") { e.preventDefault(); listaPaleta.querySelector(".marcado")?.click(); }
    });

    /* ── densidade ──────────────────────────────────────────────────────── */

    function alternarDensidade() {
        const agora = document.body.dataset.densidade === "compacta" ? "confortavel" : "compacta";
        document.body.dataset.densidade = agora;
        guardar("furia.densidade", agora);
        window.showToast?.(agora === "compacta" ? "Densidade compacta" : "Densidade confortável", "info");
    }
    document.body.dataset.densidade = lembrar("furia.densidade") || "confortavel";

    /* ── atalhos globais ────────────────────────────────────────────────── */

    document.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); abrirPaleta(); return; }
        if (e.key === "Escape" && !fundoPaleta.hidden) { fecharPaleta(); return; }
        const digitando = /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName) || e.target.isContentEditable;
        if (digitando || e.ctrlKey || e.metaKey || e.altKey) return;
        const atalhos = { "1": "fila", "2": "cortar", "3": "auditoria", "4": "acervo" };
        if (atalhos[e.key]) { e.preventDefault(); irPara(atalhos[e.key]); }
    });
})();

/* ── a gaveta de ajustes ────────────────────────────────────────────────── */
(function () {
    "use strict";
    const fundo = document.getElementById("ajustesFundo");
    if (!fundo) return;
    const abrir = (sim) => { fundo.hidden = !sim; if (sim) fundo.querySelector("select, input, button")?.focus(); };
    document.getElementById("btnAjustes")?.addEventListener("click", () => abrir(true));
    document.getElementById("btnFecharAjustes")?.addEventListener("click", () => abrir(false));
    fundo.addEventListener("mousedown", (e) => { if (e.target === fundo) abrir(false); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !fundo.hidden) abrir(false); });
})();
