/* ═══════════════════════════════════════════════════════════════════════════
   FURIA — A MESA (comportamento)

   O que a folha de estilo não consegue fazer: a ignição, o som, a marca em
   vetor, e as reações que fazem a mesa parecer um equipamento em vez de uma
   página.

   ─── som ───────────────────────────────────────────────────────────────────

   Tudo SINTETIZADO, nenhum arquivo. Não é preciosismo técnico: o Furia abre sem
   internet numa máquina Windows, e um .mp3 a mais é um arquivo a mais para
   faltar, para não caber no instalador, para tocar com atraso na primeira vez.
   Um oscilador e um envelope cabem em vinte linhas e tocam em zero milissegundo.

   O desenho do som segue a mesma regra do desenho da tela: som é SINAL, não
   enfeite. Quatro eventos, e nenhum deles é "você clicou num botão" — o editor
   clica trezentas vezes por hora e um clique sonoro em cada uma vira tortura.
   Toca quando o PROGRAMA faz algo que ele não mandou fazer agora:

       tique   um corte ficou pronto           (o que ele está esperando)
       armar   uma operação começou            (a mesa assumiu)
       feito   a operação terminou
       falha   alguma coisa quebrou

   Ligado por padrão, porque ele pediu impacto, e desligável em um clique que a
   mesa lembra. Um som que não se desliga é um som que se odeia na terceira hora.

   ─── ignição ───────────────────────────────────────────────────────────────

   Meio segundo, uma vez por sessão. Abrir uma página e ligar um equipamento são
   sensações diferentes, e a diferença inteira mora nesses 500 ms.
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
    "use strict";

    const guardar = (c, v) => { try { localStorage.setItem(c, v); } catch (e) { /* anônima */ } };
    const lembrar = (c) => { try { return localStorage.getItem(c); } catch (e) { return null; } };

    /* ── a marca ────────────────────────────────────────────────────────────
       Desenhada, não escrita. A única fonte que existe offline é a Inter, e
       palavra em Inter é palavra de qualquer produto. Traço reto, ângulo vivo,
       vazado — estêncil de painel de equipamento. */

    const MARCA = `
<svg viewBox="0 0 172 40" fill="none" aria-label="Furia" role="img"
     stroke="currentColor" stroke-width="5.5" stroke-linecap="square">
  <path d="M2.75 40 V2.75 H26 M2.75 19 H20"/>
  <path d="M35.75 2.75 V37.25 H59.25 V2.75"/>
  <path d="M68.75 40 V2.75 H92.25 V19 H68.75 M81 19 L92.25 40"/>
  <path d="M104.75 2.75 V40"/>
  <path d="M116.75 40 V2.75 H140.25 V40 M116.75 22 H140.25"/>
</svg>`;

    document.querySelectorAll("[data-marca-furia]").forEach((no) => {
        no.insertAdjacentHTML("afterbegin", MARCA);
    });

    /* ── som ────────────────────────────────────────────────────────────── */

    let audio = null;
    let ligado = lembrar("furia.som") !== "0";

    function contexto() {
        // Só depois do primeiro gesto: navegador nenhum deixa criar áudio antes,
        // e tentar mais cedo só enche o console de aviso.
        if (!audio) {
            const Ctor = window.AudioContext || window.webkitAudioContext;
            if (!Ctor) return null;
            try { audio = new Ctor(); } catch (erro) { return null; }
        }
        if (audio.state === "suspended") audio.resume().catch(() => {});
        return audio;
    }

    /* Um tom com envelope. `corpo` dá a diferença entre clique e nota: um
       filtro passa-baixa fechando é o que faz o som ter matéria em vez de
       parecer um bipe de micro-ondas. */
    function tom({ de, para = de, dur = 0.09, tipo = "sine", vol = 0.09, corpo = 2400 }) {
        const ctx = contexto();
        if (!ctx || !ligado) return;
        const agora = ctx.currentTime;
        const osc = ctx.createOscillator();
        const ganho = ctx.createGain();
        const filtro = ctx.createBiquadFilter();

        osc.type = tipo;
        osc.frequency.setValueAtTime(de, agora);
        if (para !== de) osc.frequency.exponentialRampToValueAtTime(para, agora + dur);

        filtro.type = "lowpass";
        filtro.frequency.setValueAtTime(corpo, agora);
        filtro.frequency.exponentialRampToValueAtTime(Math.max(220, corpo * 0.3), agora + dur);

        // Ataque de 4 ms: instantâneo o bastante para ser percussivo, longo o
        // bastante para não estalar.
        ganho.gain.setValueAtTime(0.0001, agora);
        ganho.gain.exponentialRampToValueAtTime(vol, agora + 0.004);
        ganho.gain.exponentialRampToValueAtTime(0.0001, agora + dur);

        osc.connect(filtro).connect(ganho).connect(ctx.destination);
        osc.start(agora);
        osc.stop(agora + dur + 0.02);
    }

    const SONS = {
        // Um corte ficou pronto. Curto e claro, como uma peça encaixando.
        tique: () => { tom({ de: 880, para: 1320, dur: 0.055, vol: 0.07, corpo: 3600 }); },
        // A mesa assumiu: varredura para cima, o equipamento acordando.
        armar: () => { tom({ de: 180, para: 520, dur: 0.26, tipo: "triangle", vol: 0.075, corpo: 1800 }); },
        // Terminou. Duas notas, a segunda mais alta: fecho.
        feito: () => {
            tom({ de: 660, dur: 0.08, vol: 0.07, corpo: 3000 });
            window.setTimeout(() => tom({ de: 990, dur: 0.14, vol: 0.07, corpo: 3000 }), 90);
        },
        // Quebrou. Desce, e é a única que usa onda quadrada.
        falha: () => { tom({ de: 320, para: 120, dur: 0.24, tipo: "square", vol: 0.055, corpo: 900 }); },
    };

    window.mesaSom = function mesaSom(nome) { SONS[nome]?.(); };

    const botaoSom = document.getElementById("btnSom");
    function pintarSom() {
        if (!botaoSom) return;
        botaoSom.classList.toggle("f-acesa", ligado);
        botaoSom.querySelector(".material-icons-round").textContent = ligado ? "volume_up" : "volume_off";
        botaoSom.title = ligado ? "Som ligado — clique para silenciar" : "Som silenciado";
        botaoSom.setAttribute("aria-pressed", ligado ? "true" : "false");
    }
    botaoSom?.addEventListener("click", () => {
        ligado = !ligado;
        guardar("furia.som", ligado ? "1" : "0");
        pintarSom();
        if (ligado) SONS.tique();
    });
    pintarSom();

    /* ── a trilha: por onde ele já passou ───────────────────────────────────
       O percurso (Fila → Cortar → Auditoria) mostra o caminho andado. Uma aba
       visitada fica em brasa; a atual, acesa. É o que transforma cinco abas
       iguais numa linha com direção. */

    function marcarPercorrida(slug) {
        const aba = document.querySelector(`.rail-tab[data-ambiente="${slug}"]`);
        aba?.classList.add("f-percorrida");
        const vistas = new Set((lembrar("furia.percorridas") || "").split(",").filter(Boolean));
        vistas.add(slug);
        guardar("furia.percorridas", [...vistas].join(","));
    }
    (lembrar("furia.percorridas") || "").split(",").filter(Boolean).forEach((slug) => {
        document.querySelector(`.rail-tab[data-ambiente="${slug}"]`)?.classList.add("f-percorrida");
    });
    document.querySelectorAll(".rail-tab").forEach((aba) => {
        aba.addEventListener("click", () => marcarPercorrida(aba.dataset.ambiente));
    });

    /* ── a leitura da fonte ─────────────────────────────────────────────────
       O app.js reescreve `#selectedVideoInfo` com o cartão antigo inteiro.
       Em vez de estilizar aquele HTML, leio o nome dele e escrevo no mostrador
       — é a diferença entre remendar a peça velha e ter uma peça nova. */

    const leitura = document.getElementById("furiaLeituraFonte");
    const originalDaFonte = document.getElementById("selectedVideoInfo");

    function atualizarLeitura() {
        if (!leitura) return;
        const nome = window.state?.selectedVideoName
            || String(window.state?.selectedVideo || "").split(/[\\/]/).pop()
            || "";
        leitura.textContent = nome || "sem fonte carregada";
        leitura.classList.toggle("vazio", !nome);
    }
    if (originalDaFonte) {
        new MutationObserver(atualizarLeitura).observe(originalDaFonte, {
            childList: true, subtree: true, characterData: true,
        });
    }
    atualizarLeitura();
    window.mesaAtualizarFonte = atualizarLeitura;

    /* ── o estado da estação reage à operação ───────────────────────────── */

    const estado = document.getElementById("workspaceState");
    const fita = document.getElementById("runBar");
    if (estado && fita) {
        new MutationObserver(() => {
            estado.classList.toggle("f-rodando", !fita.hidden);
        }).observe(fita, { attributes: true, attributeFilter: ["hidden"] });
    }

    /* ── a lâmina que chega anuncia ─────────────────────────────────────────
       `renderResultsGrid` reconstrói a grade inteira a cada corte entregue, e
       sem marcar o novo ele apareceria no meio dos outros sem nada dizer que
       chegou agora. */

    let vistosNaGrade = 0;
    window.mesaCorteChegou = function mesaCorteChegou() {
        const cartoes = document.querySelectorAll("#resultsGrid .result-card");
        if (cartoes.length > vistosNaGrade) {
            cartoes[cartoes.length - 1]?.classList.add("f-nova");
            SONS.tique();
        }
        vistosNaGrade = cartoes.length;
    };

    /* ── ignição ────────────────────────────────────────────────────────── */

    if (!sessionStorage.getItem("furia.ligada")) {
        try { sessionStorage.setItem("furia.ligada", "1"); } catch (e) { /* anônima */ }
        const tela = document.createElement("div");
        tela.className = "f-ignicao";
        tela.setAttribute("aria-hidden", "true");
        tela.innerHTML = `<div class="f-ig-marca">${MARCA}</div><div class="f-ig-linha"></div>`;
        document.body.appendChild(tela);
        window.setTimeout(() => tela.remove(), 1300);
        // A mesa assumindo. Só toca se o navegador já tiver permitido áudio —
        // na primeira visita não terá, e é assim mesmo: som antes de qualquer
        // gesto é som que o navegador recusa e que ninguém pediu.
        window.setTimeout(() => SONS.armar(), 180);
    }
})();
