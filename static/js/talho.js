/* ═══════════════════════════════════════════════════════════════════════════
   O TALHO — onde o corte ganha suas bordas.

   O que existia: dois campos de número em segundos absolutos da fonte, "300.0"
   e "800.0". O editor descreveu exatamente o que isso é de usar: "não sabia o
   que eu estava medindo, não sabia onde era o início que eu queria porque o
   próprio corte não permitia voltar, e eu sequer sabia se eram segundos".

   As três queixas são a mesma: som não se edita olhando para um número.

   Aqui a onda é o controle. As alças passam por cima dela, a margem de fora
   aparece apagada — para poder voltar — e a fala do instante fica escrita
   embaixo. O número continua existindo, escondido, porque é dele que as funções
   de salvar já dependiam; ele virou consequência do arrasto.
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
    "use strict";

    // Quanto de fora do corte entra na tela de cada lado. A queixa central era
    // não conseguir voltar: para escolher onde entrar é preciso ver e ouvir a
    // frase anterior.
    const MARGEM_S = 5;
    // Perto disso de uma borda de frase, a alça gruda. O editor corta fala; a
    // unidade dele é a frase, não o décimo de segundo.
    const IMA_S = 0.35;

    const talhos = new Map();

    const relogio = (s) => {
        const t = Math.max(0, Number(s) || 0);
        const h = Math.floor(t / 3600);
        const m = Math.floor((t % 3600) / 60);
        const seg = (t % 60).toFixed(1).padStart(4, "0");
        return h ? `${h}:${String(m).padStart(2, "0")}:${seg}` : `${m}:${seg}`;
    };
    const escapar = (t) => String(t ?? "").replace(/[&<>"']/g, (c) =>
        ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

    function segmentos() {
        const t = window.state?.manualTranscript;
        return Array.isArray(t?.segments) ? t.segments : [];
    }

    function bordasDeFrase(de, ate) {
        const bordas = [];
        for (const seg of segmentos()) {
            const ini = Number(seg.start), fim = Number(seg.end);
            if (Number.isFinite(ini) && ini >= de && ini <= ate) bordas.push(ini);
            if (Number.isFinite(fim) && fim >= de && fim <= ate) bordas.push(fim);
        }
        return bordas;
    }

    function falaEm(instante) {
        for (const seg of segmentos()) {
            if (Number(seg.start) <= instante && instante < Number(seg.end)) {
                return String(seg.text || "").trim();
            }
        }
        return "";
    }

    function grudar(valor, bordas, ligado) {
        if (!ligado || !bordas.length) return valor;
        let melhor = valor, dist = IMA_S;
        for (const borda of bordas) {
            const d = Math.abs(borda - valor);
            if (d < dist) { dist = d; melhor = borda; }
        }
        return melhor;
    }

    function desenhar(t) {
        const tela = t.canvas;
        const escala = window.devicePixelRatio || 1;
        const largura = tela.clientWidth, altura = tela.clientHeight;
        if (!largura || !altura) return;
        tela.width = Math.round(largura * escala);
        tela.height = Math.round(altura * escala);
        const ctx = tela.getContext("2d");
        ctx.setTransform(escala, 0, 0, escala, 0, 0);
        ctx.clearRect(0, 0, largura, altura);

        const estilo = getComputedStyle(document.body);
        const ouro = estilo.getPropertyValue("--at-ouro").trim() || "#f0a91e";
        const apagado = estilo.getPropertyValue("--at-linha-forte").trim() || "#343a41";

        if (!t.picos.length) {
            ctx.fillStyle = apagado;
            ctx.font = "12px Inter, sans-serif";
            ctx.fillText(t.erro || "lendo o áudio…", 10, altura / 2);
            return;
        }

        const meio = altura / 2;
        const passo = largura / t.picos.length;
        for (let i = 0; i < t.picos.length; i++) {
            const instante = t.de + (i / t.picos.length) * (t.ate - t.de);
            const dentro = instante >= t.inicio && instante <= t.fim;
            ctx.fillStyle = dentro ? ouro : apagado;
            const h = Math.max(1, t.picos[i] * (altura - 8));
            ctx.fillRect(i * passo, meio - h / 2, Math.max(1, passo - 0.6), h);
        }

        // as bordas de frase, para o ímã ter onde grudar à vista
        const bordas = bordasDeFrase(t.de, t.ate);
        if (bordas.length && bordas.length < 400) {
            ctx.fillStyle = apagado;
            for (const borda of bordas) {
                const x = ((borda - t.de) / (t.ate - t.de)) * largura;
                ctx.fillRect(x, altura - 4, 1, 4);
            }
        }
    }

    function posicionar(t) {
        const largura = t.tela.clientWidth || 1;
        const emX = (s) => ((s - t.de) / (t.ate - t.de)) * largura;
        t.foraEsq.style.left = "0px";
        t.foraEsq.style.width = `${Math.max(0, emX(t.inicio))}px`;
        t.foraDir.style.left = `${emX(t.fim)}px`;
        t.foraDir.style.width = `${Math.max(0, largura - emX(t.fim))}px`;
        t.alcaIni.style.left = `${emX(t.inicio)}px`;
        t.alcaFim.style.left = `${emX(t.fim)}px`;

        t.raiz.querySelector("[data-relogio=entrada] b").textContent = relogio(t.inicio);
        t.raiz.querySelector("[data-relogio=saida] b").textContent = relogio(t.fim);
        t.raiz.querySelector("[data-relogio=duracao] b").textContent =
            `${(t.fim - t.inicio).toFixed(1)}s`;

        if (t.campoIni) t.campoIni.value = t.inicio.toFixed(1);
        if (t.campoFim) t.campoFim.value = t.fim.toFixed(1);

        t.alcaIni.setAttribute("aria-valuetext", `entrada em ${relogio(t.inicio)}`);
        t.alcaFim.setAttribute("aria-valuetext", `saída em ${relogio(t.fim)}`);
    }

    function mostrarFala(t, instante, dentro) {
        const texto = falaEm(instante);
        t.fala.classList.toggle("no-corte", !!dentro);
        t.fala.innerHTML = texto
            ? escapar(texto)
            : `<em>${segmentos().length ? "silêncio ou pausa neste ponto" : "sem transcrição carregada — a fala não pode ser mostrada"}</em>`;
    }

    async function carregarOnda(t) {
        if (!t.caminho) { t.erro = "vídeo de origem não identificado"; desenhar(t); return; }
        try {
            const url = `/api/waveform?video_path=${encodeURIComponent(t.caminho)}`
                + `&start=${t.de.toFixed(2)}&end=${t.ate.toFixed(2)}&buckets=520`;
            const resposta = await fetch(url);
            const dados = await resposta.json();
            if (!resposta.ok) throw new Error(dados.error || `HTTP ${resposta.status}`);
            t.picos = Array.isArray(dados.peaks) ? dados.peaks : [];
            t.erro = dados.silent ? "trecho sem áudio audível" : "";
        } catch (erro) {
            t.picos = [];
            t.erro = `não deu para desenhar o áudio: ${String(erro.message).slice(0, 70)}`;
        }
        desenhar(t);
    }

    function arrastar(t, alca, qual) {
        const mover = (evento) => {
            const caixa = t.tela.getBoundingClientRect();
            const x = Math.min(caixa.right, Math.max(caixa.left, evento.clientX)) - caixa.left;
            let instante = t.de + (x / caixa.width) * (t.ate - t.de);
            instante = grudar(instante, bordasDeFrase(t.de, t.ate), t.ima.checked);
            if (qual === "inicio") t.inicio = Math.min(instante, t.fim - 0.5);
            else t.fim = Math.max(instante, t.inicio + 0.5);
            posicionar(t);
            desenhar(t);
            mostrarFala(t, instante, true);
        };
        const soltar = () => {
            alca.classList.remove("arrastando");
            window.removeEventListener("pointermove", mover);
            window.removeEventListener("pointerup", soltar);
        };
        alca.addEventListener("pointerdown", (evento) => {
            evento.preventDefault();
            alca.classList.add("arrastando");
            alca.focus();
            window.addEventListener("pointermove", mover);
            window.addEventListener("pointerup", soltar);
        });
        // Teclado: as setas andam de décimo em décimo, com Shift de segundo em
        // segundo. Quem não consegue mirar com o mouse ainda consegue ajustar.
        alca.addEventListener("keydown", (evento) => {
            const passo = evento.shiftKey ? 1 : 0.1;
            let delta = 0;
            if (evento.key === "ArrowLeft") delta = -passo;
            else if (evento.key === "ArrowRight") delta = passo;
            else return;
            evento.preventDefault();
            if (qual === "inicio") t.inicio = Math.max(t.de, Math.min(t.inicio + delta, t.fim - 0.5));
            else t.fim = Math.min(t.ate, Math.max(t.fim + delta, t.inicio + 0.5));
            posicionar(t);
            desenhar(t);
            mostrarFala(t, qual === "inicio" ? t.inicio : t.fim, true);
        });
    }

    function ligarTeclas(t) {
        t.raiz.addEventListener("keydown", (evento) => {
            if (/^(INPUT|TEXTAREA|SELECT)$/.test(evento.target.tagName)) return;
            const video = t.video;
            const tecla = evento.key.toLowerCase();
            // J K L, I e O: a memória muscular que todo editor já tem.
            if (tecla === "j") { evento.preventDefault(); if (video) video.currentTime = Math.max(0, video.currentTime - 2); }
            else if (tecla === "k" || evento.key === " ") {
                evento.preventDefault();
                if (video) video.paused ? video.play() : video.pause();
            }
            else if (tecla === "l") { evento.preventDefault(); if (video) video.currentTime += 2; }
            else if (tecla === "i") {
                evento.preventDefault();
                if (video) { t.inicio = Math.max(t.de, Math.min(video.currentTime, t.fim - 0.5)); posicionar(t); desenhar(t); }
            }
            else if (tecla === "o") {
                evento.preventDefault();
                if (video) { t.fim = Math.min(t.ate, Math.max(video.currentTime, t.inicio + 0.5)); posicionar(t); desenhar(t); }
            }
        });
    }

    /* Monta o talho dentro do editor de bordas de um corte. */
    window.montarTalho = function montarTalho(indice) {
        const caixa = document.getElementById(`boundary-editor-${indice}`);
        if (!caixa) return;
        // Salvar e pré-visualizar chamam `renderResultsGrid`, que reconstrói o
        // cartão inteiro a partir do HTML: campos novos, rótulos visíveis, e o
        // talho anterior fora do documento. O mapa continuava guardando aquele
        // nó morto, então reabrir devolvia cedo e o editor via de volta os
        // campos de número antigos — "REAPARECE O SISTEMA DE BOTÕES E NUMEROS
        // ANTIGOS". Um nó que saiu do documento não vale como talho montado.
        const anterior = talhos.get(indice);
        if (anterior && anterior.raiz.isConnected) { desenhar(anterior); return; }
        talhos.delete(indice);

        const clip = window.state?.clips?.[indice];
        if (!clip) return;
        const inicio = Number(clip.start) || 0;
        const fim = Number(clip.end) || inicio + 1;
        const de = Math.max(0, inicio - MARGEM_S);
        const ate = fim + MARGEM_S;

        const raiz = document.createElement("div");
        raiz.className = "talho";
        raiz.tabIndex = 0;
        raiz.innerHTML = `
            <div class="talho-relogios">
                <span class="talho-relogio" data-relogio="entrada"><i>entra em</i><b>—</b></span>
                <span class="talho-relogio" data-relogio="saida"><i>sai em</i><b>—</b></span>
                <span class="talho-relogio duracao" data-relogio="duracao"><i>dura</i><b>—</b></span>
            </div>
            <div class="talho-tela">
                <canvas></canvas>
                <div class="talho-fora" data-fora="esq"></div>
                <div class="talho-fora" data-fora="dir"></div>
                <div class="talho-alca" data-alca="inicio" tabindex="0" role="slider"
                     aria-label="Início do corte" aria-valuemin="0"></div>
                <div class="talho-alca" data-alca="fim" tabindex="0" role="slider"
                     aria-label="Fim do corte" aria-valuemin="0"></div>
            </div>
            <div class="talho-fala"><em>passe o mouse sobre a onda para ver a fala</em></div>
            <div class="talho-acoes">
                <label class="talho-encaixe"><input type="checkbox" checked> encaixar na frase</label>
                <span class="talho-dica"><kbd>J</kbd><kbd>K</kbd><kbd>L</kbd> navegar · <kbd>I</kbd><kbd>O</kbd> marcar entrada e saída</span>
            </div>`;

        const campos = caixa.querySelector(".clip-boundary-fields");
        campos && caixa.insertBefore(raiz, campos);

        const t = {
            raiz, de, ate, inicio, fim, picos: [], erro: "",
            caminho: window.state?.selectedVideo || clip.source_video || "",
            video: document.querySelector("#playerDock video, #videoPreview video"),
            tela: raiz.querySelector(".talho-tela"),
            canvas: raiz.querySelector("canvas"),
            foraEsq: raiz.querySelector('[data-fora="esq"]'),
            foraDir: raiz.querySelector('[data-fora="dir"]'),
            alcaIni: raiz.querySelector('[data-alca="inicio"]'),
            alcaFim: raiz.querySelector('[data-alca="fim"]'),
            fala: raiz.querySelector(".talho-fala"),
            ima: raiz.querySelector('.talho-encaixe input'),
            campoIni: caixa.querySelector(`[data-boundary-start="${indice}"]`),
            campoFim: caixa.querySelector(`[data-boundary-end="${indice}"]`),
        };
        talhos.set(indice, t);

        // Os campos de número continuam existindo — as funções de salvar já
        // liam deles — mas saem da frente. Eles deixam de ser o controle.
        [t.campoIni, t.campoFim].forEach((campo) => {
            if (!campo) return;
            campo.type = "hidden";
            campo.closest("label")?.setAttribute("hidden", "");
        });

        arrastar(t, t.alcaIni, "inicio");
        arrastar(t, t.alcaFim, "fim");
        ligarTeclas(t);

        t.tela.addEventListener("pointermove", (evento) => {
            if (evento.target.closest(".talho-alca")) return;
            const caixaTela = t.tela.getBoundingClientRect();
            const instante = t.de + ((evento.clientX - caixaTela.left) / caixaTela.width) * (t.ate - t.de);
            mostrarFala(t, instante, instante >= t.inicio && instante <= t.fim);
        });
        t.tela.addEventListener("click", (evento) => {
            if (evento.target.closest(".talho-alca") || !t.video) return;
            const caixaTela = t.tela.getBoundingClientRect();
            t.video.currentTime = t.de + ((evento.clientX - caixaTela.left) / caixaTela.width) * (t.ate - t.de);
        });

        posicionar(t);
        carregarOnda(t);
        new ResizeObserver(() => { posicionar(t); desenhar(t); }).observe(t.tela);
    };

    window.redesenharTalhos = () => talhos.forEach(desenhar);
    window.esquecerTalhos = () => talhos.clear();
})();
