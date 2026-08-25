/* ═══════════════════════════════════════════════════════════════════════════
   FURIA 2 — A BANCADA (comportamento)

   O que a folha de estilo não faz: a ignição, o som e o estado da máquina.

   ─── a ignição ─────────────────────────────────────────────────────────────

   É a mistura das duas referências em um gesto só. À esquerda, a marca se
   remonta de pó — que é a entrada do Cipher. À direita, a máquina se apresenta
   com versão, créditos e uma barra feita de tijolinhos que conta até 100% —
   que é o instalador do Poolsuite. Um segundo e meio, uma vez por sessão, e
   qualquer tecla pula: abertura que não se pula é abertura que se odeia na
   terceira vez.

   ─── som ───────────────────────────────────────────────────────────────────

   Sintetizado, nenhum arquivo: o programa abre sem internet numa máquina
   Windows, e um .mp3 a mais é um arquivo a mais para faltar. E som é SINAL,
   não enfeite — nenhum evento aqui é "você clicou num botão". Toca quando a
   MÁQUINA faz alguma coisa.
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
    "use strict";

    /* ── a marca, para o pó ─────────────────────────────────────────────────
       O mesmo desenho do cabeçalho. Vai virar imagem por dentro do próprio
       arquivo (sem rede, sem arquivo solto) só para que o canvas possa ler os
       pixels dela e saber onde cada grão tem que pousar. */

    const MARCA = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 68 26" width="150" height="57" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round"><path d="M4 23 V6.5 C4 3.8 5.6 2.5 8.2 2.5 H10"/><path d="M0.8 10 H10"/><path d="M17 10 V17.8 C17 21 19.2 23 22 23 C24.8 23 27 21 27 17.8 V10"/><path d="M27 10 V23"/><path d="M34 23 V10"/><path d="M34 14 C34 11.6 35.8 10 38.4 10 H41"/><path d="M48 23 V10"/><rect x="46" y="2.5" width="4" height="4" fill="#ffffff" stroke="none"/><path d="M66 16.5 C66 12.9 63.6 10 60.5 10 C57.4 10 55 12.9 55 16.5 C55 20.1 57.4 23 60.5 23 C63.6 23 66 20.1 66 16.5 Z"/><path d="M66 10 V23"/></svg>`;

    const FOLHA = "#f2efe6";
    const TIJOLOS = 26;
    const DURACAO_PO = 950;      // a marca levar quase um segundo para se juntar
    const DURACAO_BARRA = 1150;
    const ESPERA_FINAL = 320;    // o 100% aceso, parado, antes de apagar

    /* ── som ─────────────────────────────────────────────────────────────── */

    let audio = null;
    function contexto() {
        // Só depois do primeiro gesto: navegador nenhum deixa criar áudio antes,
        // e tentar mais cedo só enche o registro de aviso.
        if (!audio) {
            const Ctor = window.AudioContext || window.webkitAudioContext;
            if (!Ctor) return null;
            try { audio = new Ctor(); } catch (erro) { return null; }
        }
        if (audio.state === "suspended") audio.resume().catch(() => {});
        return audio;
    }

    /* Um tom com envelope. O filtro fechando é o que dá matéria ao som — sem
       ele vira bipe de micro-ondas. */
    function tom({ de, para = de, dur = 0.09, tipo = "sine", vol = 0.07, corpo = 2400 }) {
        const ctx = contexto();
        if (!ctx) return;
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

        // Ataque de 4 ms: percussivo sem estalar.
        ganho.gain.setValueAtTime(0.0001, agora);
        ganho.gain.exponentialRampToValueAtTime(vol, agora + 0.004);
        ganho.gain.exponentialRampToValueAtTime(0.0001, agora + dur);

        osc.connect(filtro).connect(ganho).connect(ctx.destination);
        osc.start(agora);
        osc.stop(agora + dur + 0.02);
    }

    const SONS = {
        // a máquina assumindo: varredura para cima
        armar: () => tom({ de: 150, para: 480, dur: 0.3, tipo: "triangle", vol: 0.07, corpo: 1700 }),
        // uma peça encaixando
        tique: () => tom({ de: 880, para: 1320, dur: 0.05, vol: 0.06, corpo: 3600 }),
        // terminou: duas notas, a segunda mais alta
        feito: () => {
            tom({ de: 660, dur: 0.08, vol: 0.06, corpo: 3000 });
            window.setTimeout(() => tom({ de: 990, dur: 0.14, vol: 0.06, corpo: 3000 }), 90);
        },
        // quebrou: desce, e é a única de onda quadrada
        falha: () => tom({ de: 320, para: 120, dur: 0.24, tipo: "square", vol: 0.05, corpo: 900 }),
    };
    window.furiaSom = (nome) => SONS[nome]?.();

    /* ── o estado da máquina ────────────────────────────────────────────────
       Um lugar só. A faixa de cima inteira — a palavra, o quadradinho da
       marca, o contador e o olho vermelho — obedece a esta função, para que
       nunca exista uma parte da tela dizendo que está rodando e outra dizendo
       que parou. */

    const oEstado = document.getElementById("estado");
    const oContador = document.getElementById("contador");

    function relogio(segundos) {
        const s = Math.max(0, Math.floor(segundos));
        const h = String(Math.floor(s / 3600)).padStart(2, "0");
        const m = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
        const r = String(s % 60).padStart(2, "0");
        return `${h}:${m}:${r}`;
    }

    window.furiaEstado = function furiaEstado({ texto, trabalhando, fita }) {
        if (texto !== undefined && oEstado) oEstado.textContent = texto;
        if (trabalhando !== undefined) {
            document.body.classList.toggle("f2-trabalhando", !!trabalhando);
        }
        if (fita !== undefined && oContador) oContador.textContent = relogio(fita);
    };

    /* ── a doca ─────────────────────────────────────────────────────────────
       Os objetos ainda não abrem: cada um é uma tela por vir, e a combinação
       foi montar uma de cada vez. Enquanto não abre, o botão DIZ que não abre.
       Botão que não faz nada e não fala é o defeito mais caro que este
       programa já teve — falha calada. */

    const MONTADO = {};   // vai enchendo tela a tela

    document.querySelectorAll(".f2-objeto").forEach((objeto) => {
        objeto.addEventListener("click", () => {
            const nome = objeto.dataset.objeto;
            if (MONTADO[nome]) { MONTADO[nome](objeto); return; }
            window.furiaEstado({ texto: `${nome} — ainda não montado` });
            SONS.falha();
            window.setTimeout(() => {
                window.furiaEstado({ texto: document.body.classList.contains("f2-trabalhando") ? "moendo" : "parada" });
            }, 1600);
        });
    });

    /* ── a ignição ────────────────────────────────────────────────────────── */

    function acender() {
        const tela = document.createElement("div");
        tela.className = "f2-ignicao";
        tela.setAttribute("aria-hidden", "true");
        tela.innerHTML = `
            <div class="f2-caixa">
                <div class="f2-caixa-po"><canvas id="po" width="200" height="148"></canvas></div>
                <div class="f2-caixa-ficha">
                    <!-- O nome NÃO se escreve aqui. Ele está se juntando do pó
                         ao lado, e essa é a marca. Escrever "FURIA" em fonte de
                         sistema logo ao lado do desenho da marca é assinar a
                         mesma coisa duas vezes, uma delas mal. Este lado é só o
                         que a máquina é. -->
                    <div class="f2-ficha-nome">Mesa de Corte</div>
                    <div class="f2-ficha-versao">versão 2.0 &mdash; 2026</div>
                    <div class="f2-ficha-creditos">
                        Corta entrevista longa em corte de rede social.<br>
                        Trabalha sem internet. Não manda nada para fora.
                    </div>
                    <div class="f2-ficha-tarefa">
                        <span id="tarefa">montando a bancada</span><span id="porcento">0%</span>
                    </div>
                    <div class="f2-barra" id="barra"></div>
                </div>
            </div>
            <div class="f2-pular">qualquer tecla pula</div>`;
        document.body.appendChild(tela);

        const barra = tela.querySelector("#barra");
        for (let i = 0; i < TIJOLOS; i += 1) {
            const t = document.createElement("i");
            t.className = "f2-tijolo";
            barra.appendChild(t);
        }
        const tijolos = [...barra.children];
        const porcento = tela.querySelector("#porcento");
        const tarefa = tela.querySelector("#tarefa");

        let encerrada = false;
        function apagar() {
            if (encerrada) return;
            encerrada = true;
            tela.classList.add("f2-saindo");
            window.setTimeout(() => tela.remove(), 360);
            window.removeEventListener("keydown", apagar);
            window.removeEventListener("mousedown", apagar);
        }
        window.addEventListener("keydown", apagar);
        window.addEventListener("mousedown", apagar);

        poDaMarca(tela.querySelector("#po"));

        // A barra: um tijolo de cada vez, com o número acompanhando.
        const inicio = performance.now();
        let cheios = 0;
        (function correr(agora) {
            if (encerrada) return;
            const t = Math.min(1, (agora - inicio) / DURACAO_BARRA);
            const alvo = Math.round(t * TIJOLOS);
            while (cheios < alvo) { tijolos[cheios].classList.add("f2-cheio"); cheios += 1; }
            porcento.textContent = `${Math.round(t * 100)}%`;
            if (t < 0.45) tarefa.textContent = "montando a bancada";
            else if (t < 0.85) tarefa.textContent = "conferindo as ferramentas";
            else tarefa.textContent = "pronta";
            if (t < 1) { requestAnimationFrame(correr); return; }
            SONS.feito();
            window.setTimeout(apagar, ESPERA_FINAL);
        })(inicio);

        // Se o navegador já tiver liberado áudio, a máquina assume com som. Na
        // primeira visita não terá, e é assim mesmo: som antes de qualquer
        // gesto é som que o navegador recusa e que ninguém pediu.
        window.setTimeout(() => SONS.armar(), 120);
    }

    /* A dissolução do Cipher: a marca virada pó, e o pó se juntando.
       O desenho é lido da própria marca — nada de fonte, nada de arquivo. */
    function poDaMarca(canvas) {
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        const L = canvas.width, A = canvas.height;

        const img = new Image();
        img.onload = function () {
            const x0 = Math.round((L - img.width) / 2);
            const y0 = Math.round((A - img.height) / 2);

            ctx.drawImage(img, x0, y0);
            let dados;
            try {
                dados = ctx.getImageData(0, 0, L, A).data;
            } catch (erro) {
                // Sem leitura de pixel não tem pó; a marca crua já está desenhada
                // e a ignição segue. Nunca vale travar a abertura por causa de um enfeite.
                return;
            }
            ctx.clearRect(0, 0, L, A);

            // Um grão a cada 2 px: denso o bastante para a palavra ser legível
            // enquanto se junta, leve o bastante para rodar em máquina fraca.
            const graos = [];
            for (let y = 0; y < A; y += 2) {
                for (let x = 0; x < L; x += 2) {
                    if (dados[(y * L + x) * 4 + 3] > 128) {
                        graos.push({
                            ax: x, ay: y,
                            dx: Math.random() * L,
                            dy: Math.random() * A,
                            atraso: Math.random() * 0.35,
                        });
                    }
                }
            }

            const inicio = performance.now();
            (function juntar(agora) {
                const t = Math.min(1, (agora - inicio) / DURACAO_PO);
                ctx.clearRect(0, 0, L, A);
                ctx.fillStyle = FOLHA;
                for (const g of graos) {
                    // Cada grão tem o seu próprio atraso: chegar todo mundo junto
                    // parece animação; chegar espalhado parece matéria assentando.
                    const p = Math.max(0, Math.min(1, (t - g.atraso) / (1 - g.atraso)));
                    const e = 1 - Math.pow(1 - p, 3);   // desacelera no fim
                    ctx.globalAlpha = 0.25 + 0.75 * e;
                    ctx.fillRect(g.dx + (g.ax - g.dx) * e, g.dy + (g.ay - g.dy) * e, 1.6, 1.6);
                }
                ctx.globalAlpha = 1;
                if (t < 1) { requestAnimationFrame(juntar); return; }
                // No fim, a marca de verdade por cima do pó: nítida, sem serrilha.
                ctx.clearRect(0, 0, L, A);
                ctx.drawImage(img, x0, y0);
            })(inicio);
        };
        img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(MARCA);
    }

    // Uma vez por sessão. `?ignicao=1` força — é como eu tiro a foto dela.
    const forcar = new URLSearchParams(location.search).has("ignicao");
    if (forcar || !sessionStorage.getItem("furia2.acesa")) {
        try { sessionStorage.setItem("furia2.acesa", "1"); } catch (e) { /* janela anônima */ }
        acender();
    }
})();
