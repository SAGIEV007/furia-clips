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

    /* ── as janelas ─────────────────────────────────────────────────────────
       Poolsuite: o que se abre é janela de verdade — arrasta, empilha, fecha.
       O motivo não é nostalgia: num notebook de 1366×768 painel fixo é largura
       perdida o dia inteiro, e janela é largura emprestada pelo tempo do uso. */

    let alturaDaPilha = 200;
    const abertas = {};

    function abrirJanela({ nome, largura, altura, corpo }) {
        if (abertas[nome]) { trazerParaFrente(abertas[nome]); return abertas[nome]; }

        const janela = document.createElement("section");
        janela.className = "f2-janela";
        janela.dataset.janela = nome;
        janela.style.width = `${largura}px`;
        janela.style.height = `${altura}px`;
        // Centrada na primeira vez, e presa dentro da tela: uma janela que
        // nasce metade fora é uma janela que ele arrasta antes de usar.
        janela.style.left = `${Math.max(8, Math.round((window.innerWidth - largura) / 2))}px`;
        janela.style.top = `${Math.max(48, Math.round((window.innerHeight - altura) / 2))}px`;
        janela.innerHTML = `
            <header class="f2-titulo">
                <button class="f2-fechar" type="button" title="Fechar">&times;</button>
                <span class="f2-nome-janela">${nome}</span>
            </header>`;
        // O corpo vem pronto de quem chamou e entra direto: embrulhá-lo numa
        // caixa a mais daria duas rolagens aninhadas na mesma janela.
        janela.appendChild(corpo);
        document.body.appendChild(janela);

        janela.querySelector(".f2-fechar").addEventListener("click", () => fecharJanela(nome));
        janela.addEventListener("mousedown", () => trazerParaFrente(janela));
        arrastar(janela, janela.querySelector(".f2-titulo"));

        abertas[nome] = janela;
        marcarDoca(nome, true);
        trazerParaFrente(janela);
        SONS.tique();
        return janela;
    }

    function fecharJanela(nome) {
        abertas[nome]?.remove();
        delete abertas[nome];
        marcarDoca(nome, false);
    }

    function marcarDoca(nome, aberta) {
        document.querySelector(`.f2-objeto[data-objeto="${nome}"]`)
            ?.setAttribute("aria-pressed", aberta ? "true" : "false");
    }

    function trazerParaFrente(janela) {
        document.querySelectorAll(".f2-janela").forEach((j) => j.classList.remove("f2-frente"));
        janela.classList.add("f2-frente");
        alturaDaPilha += 1;
        janela.style.zIndex = String(alturaDaPilha);
    }

    function arrastar(janela, puxador) {
        puxador.addEventListener("mousedown", (evento) => {
            if (evento.target.closest(".f2-fechar")) return;
            const caixa = janela.getBoundingClientRect();
            const dx = evento.clientX - caixa.left;
            const dy = evento.clientY - caixa.top;

            function mover(e) {
                // Presa na tela com uma folga: nunca some inteira, e o título
                // nunca vai parar embaixo da faixa de cima.
                const x = Math.min(window.innerWidth - 60, Math.max(60 - caixa.width, e.clientX - dx));
                const y = Math.min(window.innerHeight - 40, Math.max(41, e.clientY - dy));
                janela.style.left = `${Math.round(x)}px`;
                janela.style.top = `${Math.round(y)}px`;
            }
            function largar() {
                window.removeEventListener("mousemove", mover);
                window.removeEventListener("mouseup", largar);
            }
            window.addEventListener("mousemove", mover);
            window.addEventListener("mouseup", largar);
            evento.preventDefault();
        });
    }

    /* ── a janela da fonte ──────────────────────────────────────────────────

       Três formas de trazer material, na ordem em que ele usa: o que já está
       na máquina (quase sempre), um arquivo de outra pasta, e um link.

       A escolha é por FOTO, não por nome. Nome de arquivo baixado do YouTube
       tem cento e vinte caracteres e trinta deles começam igual; um quadro do
       vídeo ele reconhece em meio segundo. É a regra do Cipher fazendo
       trabalho: o mural fica cinza e só o que está sob o mouse ganha cor. */

    function tempoCurto(segundos) {
        const s = Math.round(segundos || 0);
        if (!s) return "--:--";
        const h = Math.floor(s / 3600);
        const m = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
        const r = String(s % 60).padStart(2, "0");
        return h ? `${h}:${m}:${r}` : `${m}:${r}`;
    }

    function horasDe(fontes) {
        const total = fontes.reduce((soma, f) => soma + (f.segundos || 0), 0);
        return total >= 3600
            ? `${(total / 3600).toFixed(1)} h de material`
            : `${Math.round(total / 60)} min de material`;
    }

    async function pedir(caminho, opcoes) {
        const resposta = await fetch(caminho, opcoes);
        const corpo = await resposta.json().catch(() => ({}));
        // Um erro do servidor NUNCA pode virar silêncio aqui: quem chama
        // sempre recebe alguma coisa com `ok` dentro para poder falar na tela.
        if (!resposta.ok) return { ok: false, erro: corpo.erro || `falhou (${resposta.status})` };
        return corpo;
    }

    function montarJanelaDaFonte() {
        const corpo = document.createElement("div");
        corpo.className = "f2-corpo";
        corpo.innerHTML = `
            <div class="f2-fonte-topo">
                <button class="f2-tecla" data-abrir type="button">abrir do computador</button>
                <input class="f2-campo" data-link type="text" spellcheck="false"
                       placeholder="ou cole o link de um vídeo">
                <button class="f2-tecla" data-ler type="button">ler</button>
            </div>
            <div class="f2-mural" data-mural></div>
            <div class="f2-rodape">
                <span data-conta>lendo a pasta de trabalho…</span>
                <span class="f2-recado" data-recado></span>
            </div>`;

        const mural = corpo.querySelector("[data-mural]");
        const conta = corpo.querySelector("[data-conta]");
        const recado = corpo.querySelector("[data-recado]");

        function dizer(texto, ruim) {
            recado.textContent = texto;
            recado.classList.toggle("f2-ruim", !!ruim);
            if (ruim) SONS.falha();
            window.clearTimeout(dizer.relogio);
            dizer.relogio = window.setTimeout(() => { recado.textContent = ""; }, 6000);
        }

        function pintar(fontes) {
            mural.textContent = "";
            if (!fontes.length) {
                conta.textContent = "nenhum vídeo na pasta de trabalho";
                return;
            }
            conta.textContent = `${fontes.length} ${fontes.length === 1 ? "vídeo" : "vídeos"} · ${horasDe(fontes)}`;
            for (const fonte of fontes) {
                const quadro = document.createElement("button");
                quadro.type = "button";
                quadro.className = "f2-quadro";
                quadro.title = fonte.nome;
                quadro.innerHTML = `
                    <span class="f2-quadro-tela">
                        <span class="f2-quadro-tempo">${tempoCurto(fonte.segundos)}</span>
                    </span>
                    <span class="f2-quadro-nome"></span>`;
                quadro.querySelector(".f2-quadro-nome").textContent = fonte.nome;

                const tela = quadro.querySelector(".f2-quadro-tela");
                const foto = new Image();
                foto.alt = "";
                foto.src = `/api/fonte/quadro?chave=${encodeURIComponent(fonte.chave)}`;
                // Vídeo que o ffmpeg não abre continua na lista, e sem foto —
                // porque um vídeo quebrado é exatamente o que ele precisa ver.
                foto.onerror = () => {
                    const aviso = document.createElement("span");
                    aviso.className = "f2-quadro-sem";
                    aviso.textContent = "sem quadro";
                    tela.insertBefore(aviso, tela.firstChild);
                };
                tela.insertBefore(foto, tela.firstChild);

                quadro.addEventListener("click", () => montarNaBancada(fonte));
                mural.appendChild(quadro);
            }
        }

        (async function carregar() {
            const dados = await pedir("/api/fonte/lista");
            if (dados.ok === false) { conta.textContent = "não deu para ler a pasta"; dizer(dados.erro, true); return; }
            pintar([...(dados.de_fora || []), ...(dados.fontes || [])]);
        })();

        corpo.querySelector("[data-abrir]").addEventListener("click", async (evento) => {
            const tecla = evento.currentTarget;
            tecla.disabled = true;
            const dados = await pedir("/api/fonte/escolher", { method: "POST" });
            tecla.disabled = false;
            if (dados.ok === false) { dizer(dados.erro, true); return; }
            if (dados.desistiu) return;
            montarNaBancada(dados.fonte);
        });

        async function lerOLink() {
            const campo = corpo.querySelector("[data-link]");
            const link = campo.value.trim();
            if (!link) { campo.focus(); return; }
            dizer("lendo o link…");
            const dados = await pedir("/api/fonte/ler-link", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ link }),
            });
            if (dados.ok === false) { dizer(dados.erro, true); return; }
            // Só a leitura do cabeçalho: baixar duas horas de entrevista para
            // descobrir que era o vídeo errado é meia hora perdida.
            const f = dados.fonte || {};
            dizer(`${f.title || "vídeo"} — ${tempoCurto(f.duration)} — baixar entra com o motor`);
        }
        corpo.querySelector("[data-ler]").addEventListener("click", lerOLink);
        corpo.querySelector("[data-link]").addEventListener("keydown", (e) => {
            if (e.key === "Enter") lerOLink();
        });

        return corpo;
    }

    MONTADO.fonte = function () {
        abrirJanela({ nome: "fonte", largura: 760, altura: 470, corpo: montarJanelaDaFonte() });
    };

    /* ── a fonte na bancada ─────────────────────────────────────────────────
       Escolhida a fonte, a parede deixa de estar vazia. Um quadro só, colorido,
       no meio do breu: é o único objeto da tela e é a coisa que ele vai
       cortar. Depois dos cortes prontos, este lugar vira a parede deles. */

    function montarNaBancada(fonte) {
        fecharJanela("fonte");
        document.body.classList.remove("f2-bancada-vazia");
        window.furiaEstado({ texto: "fonte na bancada" });

        const parede = document.getElementById("parede");
        parede.textContent = "";

        const montada = document.createElement("div");
        montada.className = "f2-montada";
        montada.innerHTML = `
            <div class="f2-montada-tela"></div>
            <div class="f2-montada-nome"></div>
            <div class="f2-montada-ficha">${tempoCurto(fonte.segundos)} de fonte</div>
            <button class="f2-tecla" data-moer type="button">moer a fonte</button>`;
        montada.querySelector(".f2-montada-nome").textContent = fonte.nome;

        const foto = new Image();
        foto.alt = "";
        foto.src = `/api/fonte/quadro?chave=${encodeURIComponent(fonte.chave)}`;
        montada.querySelector(".f2-montada-tela").appendChild(foto);

        fonteNaBancada = fonte;
        anotar(`fonte na bancada: ${fonte.nome} (${relogioCurto(fonte.segundos)})`);
        montada.querySelector("[data-moer]").addEventListener("click", moer);

        parede.appendChild(montada);
        SONS.feito();
    }

    /* ── a parede de cortes ─────────────────────────────────────────────────

       O coração do programa. A mecânica é a do Cipher, inteira: os cortes
       ficam cinzas no breu, o que está sob o mouse ganha cor, e a informação
       não mora embaixo de cada quadro — mora numa legenda única no pé da tela
       que troca conforme o mouse anda.

       Catorze quadros com quatro linhas embaixo de cada um são cinquenta e
       seis linhas competindo. Catorze quadros e uma linha só é uma coisa para
       ler por vez. */

    const parede = document.getElementById("parede");
    let cortesNaParede = [];
    let escolhido = null;

    function relogioCurto(segundos) {
        const s = Math.max(0, Math.round(segundos || 0));
        const h = Math.floor(s / 3600);
        const m = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
        const r = String(s % 60).padStart(2, "0");
        return h ? `${h}:${m}:${r}` : `${m}:${r}`;
    }

    async function abrirAParede() {
        const dados = await pedir("/api/cortes/lista");
        if (dados.ok === false || !dados.tem_rodada) {
            window.furiaEstado({ texto: "nenhuma rodada ainda" });
            return false;
        }
        pintarAParede(dados);
        return true;
    }
    window.furiaAbrirParede = abrirAParede;

    function porAFala(tela, corte) {
        const trecho = document.createElement("span");
        trecho.className = "f2-corte-fala";
        trecho.textContent = corte.fala || "sem transcrição neste corte";
        tela.insertBefore(trecho, tela.firstChild);
    }

    function pintarAParede(dados) {
        cortesNaParede = dados.cortes || [];
        document.body.classList.remove("f2-bancada-vazia");
        parede.textContent = "";

        const mural = document.createElement("div");
        mural.className = "f2-mural-cortes";

        const legenda = document.createElement("div");
        legenda.className = "f2-legenda";
        legenda.innerHTML = `
            <span class="f2-legenda-marca" data-marca></span>
            <span class="f2-legenda-fala f2-quieta" data-fala></span>
            <span class="f2-legenda-aviso" data-aviso></span>`;
        const marca = legenda.querySelector("[data-marca]");
        const fala = legenda.querySelector("[data-fala]");
        const aviso = legenda.querySelector("[data-aviso]");

        const resumo = dados.resumo || {};
        function emRepouso() {
            marca.textContent = "";
            aviso.textContent = "";
            fala.classList.add("f2-quieta");
            // Sem mouse em cima, a legenda conta a rodada inteira. É o número
            // que ele quer ver de longe: quantos saíram e quantos pedem o
            // olho dele.
            const partes = [`${resumo.entregues} cortes`];
            if (resumo.conferir) partes.push(`${resumo.conferir} pedem conferência`);
            if (resumo.descartados_por_sobreposicao) {
                partes.push(`${resumo.descartados_por_sobreposicao} descartados por sobreposição`);
            }
            if (resumo.recusados) partes.push(`${resumo.recusados} recusados`);
            if (!dados.fonte?.tem_imagem) {
                partes.push(dados.fonte?.tem_som
                    ? "fonte só em áudio nesta máquina"
                    : "vídeo da fonte não está nesta máquina");
            }
            fala.textContent = partes.join("  ·  ");
        }

        function contar(corte) {
            marca.innerHTML = "";
            marca.append(
                `${String(corte.n).padStart(2, "0")}/${String(cortesNaParede.length).padStart(2, "0")}   `,
            );
            const b = document.createElement("b");
            b.textContent = `${relogioCurto(corte.inicio)} → ${relogioCurto(corte.fim)}`;
            marca.append(b, `   ${relogioCurto(corte.duracao)}`);
            fala.classList.remove("f2-quieta");
            // Marcar o que ele mexeu: depois de ajustar seis bordas numa
            // rodada, "qual eu já mexi?" é a pergunta seguinte, e ela não pode
            // depender da memória dele.
            const marcado = corte.ajustado ? "borda sua · " : "";
            fala.textContent = marcado + (corte.fala || "sem transcrição neste corte");
            // O motivo vem inteiro, escrito pela máquina em português. Não é
            // um código para ele decifrar depois.
            aviso.textContent = corte.conferir ? (corte.motivos[0] || "conferir antes de publicar") : "";
        }

        /* O traço vermelho na base do quadro só aparece quando ele SEPARA.
           Nesta rodada os onze cortes pedem conferência, e marcar os onze
           deixou a parede listrada de vermelho — papel de parede, não aviso.
           Uma marca que está em tudo não aponta para nada, e queima a única
           cor que ele lê sem pensar. Quando é a rodada inteira, quem conta é
           a legenda do pé; quando são alguns, o traço mostra quais. */
        const marcarUmAUm = resumo.conferir > 0 && resumo.conferir < cortesNaParede.length;

        for (const corte of cortesNaParede) {
            const quadro = document.createElement("button");
            quadro.type = "button";
            quadro.className = "f2-corte";
            quadro.dataset.conferir = (corte.conferir && marcarUmAUm) ? "1" : "0";
            quadro.setAttribute("aria-current", "false");
            quadro.setAttribute(
                "aria-label",
                `corte ${corte.n}, de ${relogioCurto(corte.inicio)} a ${relogioCurto(corte.fim)}`,
            );
            quadro.innerHTML = `
                <span class="f2-corte-tela">
                    <span class="f2-corte-n">${String(corte.n).padStart(2, "0")}</span>
                    <span class="f2-corte-tempo">${relogioCurto(corte.duracao)}</span>
                </span>`;

            /* Com o vídeo na máquina, o quadro é a imagem. Sem ele, o quadro
               é a FALA — serifada, dentro do retângulo. Um mural de
               retângulos pretos vazios parece um programa quebrado; a mesma
               parede com o começo de cada fala continua sendo uma parede de
               cortes que dá para ler. E a fala é dado de verdade: veio da
               transcrição daquela rodada. */
            const tela = quadro.querySelector(".f2-corte-tela");
            if (dados.fonte?.tem_imagem) {
                const foto = new Image();
                foto.alt = "";
                foto.src = `/api/cortes/quadro?n=${corte.n}`;
                foto.onerror = () => { foto.remove(); porAFala(tela, corte); };
                tela.insertBefore(foto, tela.firstChild);
            } else {
                porAFala(tela, corte);
            }

            quadro.addEventListener("mouseenter", () => contar(corte));
            quadro.addEventListener("focus", () => contar(corte));
            quadro.addEventListener("click", () => {
                escolhido = corte;
                mural.querySelectorAll(".f2-corte").forEach((c) => c.setAttribute("aria-current", "false"));
                quadro.setAttribute("aria-current", "true");
                SONS.tique();
            });
            mural.appendChild(quadro);
        }

        mural.addEventListener("mouseleave", emRepouso);
        parede.append(mural, legenda);
        emRepouso();

        // A faixa de cima é estreita e o estado dela tem de caber numa
        // olhada. O aviso de vídeo ausente é assunto da legenda do pé, que é
        // onde ele já está olhando.
        window.furiaEstado({ texto: `${cortesNaParede.length} cortes na parede` });
    }

    window.furiaCorteEscolhido = () => escolhido;

    /* ── o talho ────────────────────────────────────────────────────────────

       A queixa do editor sobre o ajuste do Furia 1, nas palavras dele: "não
       sabia o que eu estava medindo, não sabia onde era o início que eu queria
       porque o próprio corte não permitia voltar, e eu sequer sabia se eram
       segundos". Eram dois campos de número em segundos absolutos da fonte.

       Som se edita olhando para o som. Aqui o número é consequência do
       arrasto, e a janela mostra de propósito um pedaço de FORA do corte —
       porque para escolher onde entrar é preciso ouvir a frase anterior. */

    function relogioFino(s) {
        const t = Math.max(0, s || 0);
        const m = String(Math.floor(t / 60)).padStart(2, "0");
        const r = (t % 60).toFixed(1).padStart(4, "0");
        return `${m}:${r}`;
    }

    function montarOTalho(trecho) {
        const corpo = document.createElement("div");
        corpo.className = "f2-corpo f2-talho";
        corpo.innerHTML = `
            <div class="f2-talho-topo">
                <span data-quem></span>
                <span data-bordas></span>
                <span class="f2-talho-mudou" data-mudou></span>
            </div>
            <div class="f2-onda">
                <canvas data-onda></canvas>
                <div class="f2-onda-fora" data-veu-esq></div>
                <div class="f2-onda-fora" data-veu-dir></div>
                <div class="f2-agulha" data-agulha></div>
                <div class="f2-alca" data-alca="inicio"></div>
                <div class="f2-alca" data-alca="fim"></div>
            </div>
            <div class="f2-frases" data-frases></div>
            <div class="f2-talho-pe">
                <button class="f2-tecla" data-ouvir="entrada" type="button">ouvir a entrada</button>
                <button class="f2-tecla" data-ouvir="saida" type="button">ouvir a saída</button>
                <button class="f2-tecla" data-voltar type="button">voltar ao proposto</button>
                <button class="f2-tecla" data-guardar type="button">guardar</button>
                <span class="f2-recado" data-recado></span>
            </div>`;

        const caixa = corpo.querySelector(".f2-onda");
        const tela = corpo.querySelector("[data-onda]");
        const veuEsq = corpo.querySelector("[data-veu-esq]");
        const veuDir = corpo.querySelector("[data-veu-dir]");
        const agulha = corpo.querySelector("[data-agulha]");
        const alcas = {
            inicio: corpo.querySelector('[data-alca="inicio"]'),
            fim: corpo.querySelector('[data-alca="fim"]'),
        };
        const oQuem = corpo.querySelector("[data-quem]");
        const asBordas = corpo.querySelector("[data-bordas]");
        const oMudou = corpo.querySelector("[data-mudou]");
        const asFrases = corpo.querySelector("[data-frases]");
        const oRecado = corpo.querySelector("[data-recado]");

        const janela = trecho.janela;
        const vao = Math.max(0.001, janela.fim - janela.inicio);
        let inicio = trecho.inicio;
        let fim = trecho.fim;
        let picos = null;

        const emFracao = (t) => (t - janela.inicio) / vao;
        const emTempo = (f) => janela.inicio + Math.min(1, Math.max(0, f)) * vao;

        function dizer(texto, ruim) {
            oRecado.textContent = texto;
            oRecado.classList.toggle("f2-ruim", !!ruim);
            if (ruim) SONS.falha();
            window.clearTimeout(dizer.relogio);
            dizer.relogio = window.setTimeout(() => { oRecado.textContent = ""; }, 6000);
        }

        /* ── o desenho ────────────────────────────────────────────────────── */

        function desenhar() {
            const largura = caixa.clientWidth;
            const altura = caixa.clientHeight;
            if (!largura || !altura) return;
            // A tela de desenho segue a densidade do monitor. Sem isto, num
            // notebook com escala de 125% a onda sai borrada — e onda borrada
            // é exatamente a que não deixa ver onde a frase começa.
            const escala = window.devicePixelRatio || 1;
            tela.width = Math.round(largura * escala);
            tela.height = Math.round(altura * escala);
            const ctx = tela.getContext("2d");
            ctx.setTransform(escala, 0, 0, escala, 0, 0);
            ctx.clearRect(0, 0, largura, altura);

            if (!picos) {
                ctx.fillStyle = getComputedStyle(document.documentElement)
                    .getPropertyValue("--f2-c4").trim();
                ctx.font = "10px monospace";
                ctx.fillText("lendo o som…", 12, altura / 2);
                return;
            }

            const raiz = getComputedStyle(document.documentElement);
            const meio = altura / 2;
            const passo = largura / picos.length;
            for (let i = 0; i < picos.length; i += 1) {
                const x = i * passo;
                const t = janela.inicio + (i / picos.length) * vao;
                const dentro = t >= inicio && t <= fim;
                ctx.fillStyle = raiz.getPropertyValue(dentro ? "--f2-folha" : "--f2-c4").trim();
                // Meio pixel de piso: uma fatia muda tem de continuar sendo uma
                // linha, senão o silêncio vira buraco e o desenho parece
                // quebrado no meio de uma pausa.
                const h = Math.max(0.5, picos[i] * (altura * 0.46));
                ctx.fillRect(x, meio - h, Math.max(1, passo - 0.4), h * 2);
            }
        }

        function pintarBordas() {
            const a = Math.min(1, Math.max(0, emFracao(inicio)));
            const b = Math.min(1, Math.max(0, emFracao(fim)));
            alcas.inicio.style.left = `${a * 100}%`;
            alcas.fim.style.left = `${b * 100}%`;
            veuEsq.style.left = "0";
            veuEsq.style.width = `${a * 100}%`;
            veuDir.style.left = `${b * 100}%`;
            veuDir.style.width = `${(1 - b) * 100}%`;

            asBordas.innerHTML = "";
            const forte = document.createElement("b");
            forte.textContent = `${relogioFino(inicio)} → ${relogioFino(fim)}`;
            // A duração no mesmo relógio das bordas. Ele pensa em minuto e
            // segundo, não em "143.1s".
            asBordas.append(forte, `   ${relogioFino(fim - inicio)}`);

            const mexeu = Math.abs(inicio - trecho.proposto.inicio) > 0.05
                || Math.abs(fim - trecho.proposto.fim) > 0.05;
            oMudou.textContent = mexeu
                ? `${(inicio - trecho.proposto.inicio >= 0 ? "+" : "")}${(inicio - trecho.proposto.inicio).toFixed(1)}s na entrada`
                  + `   ${(fim - trecho.proposto.fim >= 0 ? "+" : "")}${(fim - trecho.proposto.fim).toFixed(1)}s na saída`
                : "";
            desenhar();
            pintarFrases();
        }

        /* ── as frases ────────────────────────────────────────────────────── */

        let dentroAntes = new Set();
        function pintarFrases() {
            const agora = new Set();
            asFrases.querySelectorAll(".f2-frase").forEach((no, i) => {
                const f = trecho.frases[i];
                // Uma frase conta como dentro quando o miolo dela está dentro.
                // Pelo começo, uma frase que o corte pega pela metade apareceria
                // inteira; pelo fim, sumiria inteira. O miolo é o que decide se
                // aquela fala vai ao ar de forma inteligível.
                const centro = (f.t + f.fim) / 2;
                const dentro = centro >= inicio && centro <= fim;
                no.classList.toggle("f2-dentro", dentro);
                if (dentro) agora.add(i);
                if (dentro !== dentroAntes.has(i)) {
                    no.classList.add("f2-virou");
                    window.setTimeout(() => no.classList.remove("f2-virou"), 420);
                }
            });
            dentroAntes = agora;
        }

        for (const f of trecho.frases) {
            const linha = document.createElement("span");
            linha.className = "f2-frase";
            const hora = document.createElement("span");
            hora.className = "f2-frase-hora";
            hora.textContent = relogioFino(f.t).slice(0, 5);
            linha.append(hora, document.createTextNode(f.texto));
            asFrases.appendChild(linha);
        }

        /* ── arrastar ─────────────────────────────────────────────────────── */

        for (const [qual, alca] of Object.entries(alcas)) {
            alca.addEventListener("mousedown", (evento) => {
                evento.preventDefault();
                evento.stopPropagation();
                alca.classList.add("f2-pegando");
                const caixaOnda = caixa.getBoundingClientRect();

                function mover(e) {
                    const t = emTempo((e.clientX - caixaOnda.left) / caixaOnda.width);
                    // Um segundo de folga entre as alças: elas nunca se cruzam,
                    // e um corte de zero segundo não é um corte.
                    if (qual === "inicio") inicio = Math.min(t, fim - 1);
                    else fim = Math.max(t, inicio + 1);
                    pintarBordas();
                }
                function largar() {
                    alca.classList.remove("f2-pegando");
                    window.removeEventListener("mousemove", mover);
                    window.removeEventListener("mouseup", largar);
                    SONS.tique();
                }
                window.addEventListener("mousemove", mover);
                window.addEventListener("mouseup", largar);
            });
        }

        /* ── ouvir ────────────────────────────────────────────────────────── */

        let som = null;
        let pararEm = 0;
        function ouvir(de, ate) {
            if (!trecho.tem_som) { dizer("o som da fonte não está nesta máquina", true); return; }
            if (!som) {
                som = new Audio(`/api/talho/som?t=${Date.now()}`);
                som.addEventListener("timeupdate", () => {
                    agulha.style.left = `${Math.min(100, Math.max(0, emFracao(som.currentTime) * 100))}%`;
                    if (som.currentTime >= pararEm) { som.pause(); agulha.classList.remove("f2-tocando"); }
                });
                som.addEventListener("error", () => dizer("não deu para tocar o som da fonte", true));
            }
            pararEm = ate;
            som.currentTime = Math.max(0, de);
            agulha.classList.add("f2-tocando");
            som.play().catch(() => dizer("o navegador recusou tocar; clique de novo", true));
        }

        corpo.querySelector('[data-ouvir="entrada"]').addEventListener("click", () => {
            // Três segundos antes e quatro depois: é o gesto que ele repete
            // cem vezes por dia — a frase anterior morrendo e a nova nascendo.
            ouvir(inicio - 3, inicio + 4);
        });
        corpo.querySelector('[data-ouvir="saida"]').addEventListener("click", () => {
            ouvir(fim - 4, fim + 3);
        });

        corpo.querySelector("[data-voltar]").addEventListener("click", () => {
            inicio = trecho.proposto.inicio;
            fim = trecho.proposto.fim;
            pintarBordas();
            dizer("de volta ao que a máquina propôs");
        });

        corpo.querySelector("[data-guardar]").addEventListener("click", async (evento) => {
            const tecla = evento.currentTarget;
            tecla.disabled = true;
            const resposta = await pedir("/api/talho/guardar", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ n: trecho.n, inicio, fim }),
            });
            tecla.disabled = false;
            if (resposta.ok === false) { dizer(resposta.erro, true); return; }

            /* Quem manda no que apareceu na tela é o que VOLTOU do disco, não o
               que eu mandei. O defeito mais caro do Furia 1 foi um ajuste que
               respondia 200 e guardava o valor velho, e ninguém percebeu por
               duas versões porque a tela nunca conferiu. */
            inicio = resposta.inicio;
            fim = resposta.fim;
            trecho.proposto_guardado = true;
            pintarBordas();
            SONS.feito();
            anotar(`corte ${trecho.n}: borda guardada em ${relogioFino(inicio)} → ${relogioFino(fim)}`
                   + ` (a máquina propunha ${relogioFino(trecho.proposto.inicio)} → ${relogioFino(trecho.proposto.fim)})`,
                   "success");
            dizer(`guardado: ${relogioFino(inicio)} → ${relogioFino(fim)}`);
            abrirAParede();
        });

        /* ── a onda chega ─────────────────────────────────────────────────── */

        oQuem.textContent = `corte ${String(trecho.n).padStart(2, "0")} de ${trecho.de}`;
        pintarBordas();

        (async function buscarAOnda() {
            if (!trecho.tem_som) { picos = []; desenhar(); dizer("o som da fonte não está nesta máquina"); return; }
            const onda = await pedir(
                `/api/talho/onda?n=${trecho.n}&inicio=${janela.inicio}&fim=${janela.fim}`,
            );
            if (onda.ok === false) { picos = []; desenhar(); dizer(onda.erro, true); return; }
            picos = onda.picos;
            desenhar();
            if (onda.mudo) dizer("este trecho está mudo");
        })();

        // A janela pode ser arrastada e o navegador redimensionado; a onda é
        // desenhada em pixels e precisa ser refeita nos dois casos.
        new ResizeObserver(() => { pintarBordas(); }).observe(caixa);

        return corpo;
    }

    MONTADO.talho = async function () {
        const corte = escolhido || cortesNaParede[0];
        if (!corte) {
            window.furiaEstado({ texto: "escolha um corte na parede primeiro" });
            SONS.falha();
            return;
        }
        const trecho = await pedir(`/api/talho/trecho?n=${corte.n}`);
        if (trecho.ok === false) {
            window.furiaEstado({ texto: "não deu para abrir o talho" });
            SONS.falha();
            return;
        }
        // Fechar e reabrir: o talho é sempre do corte escolhido AGORA, e uma
        // janela velha aberta de outro corte é a receita da confusão que fez
        // o editor gravar o ajuste no corte errado.
        fecharJanela("talho");
        abrirJanela({ nome: "talho", largura: 880, altura: 480, corpo: montarOTalho(trecho) });
    };

    /* ── o mapa da fonte ────────────────────────────────────────────────────

       A parede responde "quais cortes saíram". Este mapa existe para a outra
       pergunta, a que nunca teve resposta: POR QUE aquele pedaço de quatro
       minutos não deu corte nenhum.

       O chão é a onda da fonte inteira — o material, não um desenho sobre o
       material. Em cima dela, o que virou corte fica aceso. Embaixo, os
       recusados: até agora eles só existiam como um número no fim do
       relatório, e é neles que mora a resposta. */

    function montarOMapa(mapa) {
        const corpo = document.createElement("div");
        corpo.className = "f2-corpo f2-mapa";
        corpo.innerHTML = `
            <div class="f2-mapa-topo">
                <span class="f2-mapa-fonte" data-fonte></span>
                <span class="f2-mapa-conta" data-conta></span>
            </div>
            <div class="f2-mapa-corpo">
                <div class="f2-regua-linha" data-regua></div>
                <div class="f2-mapa-onda" data-caixa><canvas data-onda></canvas></div>
                <div class="f2-faixa-recusados" data-recusados></div>
                <div class="f2-faixa-vaos" data-vaos></div>
            </div>
            <div class="f2-legenda">
                <span class="f2-legenda-marca" data-marca></span>
                <span class="f2-legenda-fala f2-quieta" data-fala></span>
                <span class="f2-legenda-aviso" data-aviso></span>
            </div>`;

        const dur = Math.max(1, mapa.fonte.segundos);
        const emPorCento = (t) => `${Math.min(100, Math.max(0, (t / dur) * 100))}%`;

        const caixa = corpo.querySelector("[data-caixa]");
        const tela = corpo.querySelector("[data-onda]");
        const marca = corpo.querySelector("[data-marca]");
        const fala = corpo.querySelector("[data-fala]");
        const aviso = corpo.querySelector("[data-aviso]");
        let picos = null;

        corpo.querySelector("[data-fonte]").textContent = mapa.fonte.nome;
        const conta = corpo.querySelector("[data-conta]");
        const parte = Math.round((mapa.aproveitado / dur) * 100);
        conta.innerHTML = "";
        const forte = document.createElement("b");
        forte.textContent = relogioCurto(mapa.aproveitado);
        // Não é enfeite de relatório: é a única linha da tela que responde
        // "aproveitei quanto desta entrevista?", que é a conta que ele faz de
        // cabeça toda vez e sempre erra.
        conta.append(`${relogioCurto(dur)} de fonte  ·  `, forte, ` viraram corte (${parte}%)`);

        /* ── a régua ──────────────────────────────────────────────────────── */

        const regua = corpo.querySelector("[data-regua]");
        // O passo acompanha a duração: numa entrevista de meia hora, marcar de
        // minuto em minuto dá trinta números grudados e ilegíveis.
        const passo = dur > 1500 ? 300 : dur > 600 ? 120 : 60;
        for (let t = 0; t <= dur; t += passo) {
            const m = document.createElement("span");
            m.className = "f2-marco";
            if (t === 0) m.classList.add("f2-primeiro");
            m.style.left = emPorCento(t);
            m.textContent = relogioCurto(t);
            regua.appendChild(m);
        }
        const fimDaRegua = document.createElement("span");
        fimDaRegua.className = "f2-marco f2-ultimo";
        fimDaRegua.style.left = "100%";
        fimDaRegua.textContent = relogioCurto(dur);
        regua.appendChild(fimDaRegua);

        /* ── a legenda ────────────────────────────────────────────────────── */

        function emRepouso() {
            marca.textContent = "";
            aviso.textContent = "";
            fala.classList.add("f2-quieta");
            const partes = [`${mapa.entregues.length} cortes`];
            if (mapa.vazios.length) partes.push(`${mapa.vazios.length} vãos sem corte`);
            if (mapa.recusados.length) partes.push(`${mapa.recusados.length} recusados`);
            if (mapa.adiados.length) partes.push(`${mapa.adiados.length} adiados`);
            fala.textContent = partes.join("  ·  ");
        }

        function contar({ de, ate, rotulo, texto, ruim }) {
            marca.innerHTML = "";
            const b = document.createElement("b");
            b.textContent = `${relogioCurto(de)} → ${relogioCurto(ate)}`;
            marca.append(b, `   ${relogioCurto(ate - de)}`, rotulo ? `   ${rotulo}` : "");
            fala.classList.toggle("f2-quieta", !texto);
            fala.textContent = texto || "";
            aviso.textContent = ruim || "";
        }

        /* ── os cortes entregues ──────────────────────────────────────────── */

        for (const c of mapa.entregues) {
            const alvo = document.createElement("button");
            alvo.type = "button";
            alvo.className = "f2-mapa-corte";
            alvo.style.left = emPorCento(c.inicio);
            alvo.style.width = emPorCento(c.fim - c.inicio);
            alvo.innerHTML = `<span class="f2-mapa-n">${String(c.n).padStart(2, "0")}</span>`;
            alvo.setAttribute("aria-label", `corte ${c.n}`);
            const dizer = () => contar({
                de: c.inicio, ate: c.fim,
                rotulo: `corte ${String(c.n).padStart(2, "0")}${c.ajustado ? " · borda sua" : ""}`,
                texto: c.fala,
            });
            alvo.addEventListener("mouseenter", dizer);
            alvo.addEventListener("focus", dizer);
            // Clicar no mapa leva ao talho daquele corte. É o caminho curto:
            // ele vê o buraco, entende que o corte vizinho comeu o trecho, e
            // abre o vizinho para mexer na borda sem passar pela parede.
            alvo.addEventListener("click", () => {
                escolhido = cortesNaParede.find((x) => x.n === c.n) || { n: c.n };
                MONTADO.talho();
            });
            caixa.appendChild(alvo);
        }

        /* ── os recusados e os adiados ────────────────────────────────────── */

        const faixa = corpo.querySelector("[data-recusados]");
        function porMarca(item, tipo) {
            const m = document.createElement("button");
            m.type = "button";
            m.className = "f2-recusado";
            m.dataset.tipo = tipo;
            // Aceso quando morreu dentro de um buraco: é esse que explica o
            // buraco. Apagado quando morreu num trecho que já deu corte, que
            // é rotina e não responde pergunta nenhuma.
            m.dataset.vao = item.num_vao ? "1" : "0";
            m.style.left = emPorCento(item.inicio);
            m.style.width = emPorCento(item.fim - item.inicio);
            m.setAttribute("aria-label", `${tipo} em ${relogioCurto(item.inicio)}`);
            const contra = item.perdeu_para
                ? `perdeu para o corte ${String(item.perdeu_para).padStart(2, "0")}`
                  + (item.por_quanto ? ` por ${item.por_quanto} pontos` : " por pouco")
                : "";
            const dizer = () => contar({
                de: item.inicio, ate: item.fim,
                rotulo: tipo === "adiado" ? "adiado" : "recusado",
                texto: item.trecho,
                ruim: [item.motivo, contra].filter(Boolean).join("  ·  "),
            });
            m.addEventListener("mouseenter", dizer);
            m.addEventListener("focus", dizer);
            faixa.appendChild(m);
        }
        for (const r of mapa.recusados) porMarca(r, "recusado");
        for (const a of mapa.adiados) porMarca(a, "adiado");

        /* ── os vãos ──────────────────────────────────────────────────────── */

        const faixaVaos = corpo.querySelector("[data-vaos]");
        for (const v of mapa.vazios) {
            const b = document.createElement("button");
            b.type = "button";
            b.className = "f2-vao";
            b.style.left = emPorCento(v.inicio);
            b.style.width = emPorCento(v.fim - v.inicio);
            b.textContent = relogioCurto(v.fim - v.inicio);
            b.setAttribute("aria-label", `vão de ${relogioCurto(v.fim - v.inicio)} sem corte`);
            // A diferença entre "aqui não tinha nada" e "aqui tinha três
            // coisas e todas caíram" é a resposta inteira desta tela.
            const houve = [];
            if (v.recusados) houve.push(`${v.recusados} recusado${v.recusados > 1 ? "s" : ""}`);
            if (v.adiados) houve.push(`${v.adiados} adiado${v.adiados > 1 ? "s" : ""}`);
            const dizer = () => contar({
                de: v.inicio, ate: v.fim,
                rotulo: "sem corte",
                texto: houve.length
                    ? `${houve.join(" e ")} aqui dentro — passe o mouse nas marcas abaixo`
                    : "a máquina não propôs nada neste trecho",
            });
            b.addEventListener("mouseenter", dizer);
            b.addEventListener("focus", dizer);
            faixaVaos.appendChild(b);
        }

        /* ── a onda ───────────────────────────────────────────────────────── */

        function desenhar() {
            const largura = caixa.clientWidth;
            const altura = caixa.clientHeight;
            if (!largura || !altura) return;
            const escala = window.devicePixelRatio || 1;
            tela.width = Math.round(largura * escala);
            tela.height = Math.round(altura * escala);
            const ctx = tela.getContext("2d");
            ctx.setTransform(escala, 0, 0, escala, 0, 0);
            ctx.clearRect(0, 0, largura, altura);
            if (!picos) return;

            const raiz = getComputedStyle(document.documentElement);
            const claro = raiz.getPropertyValue("--f2-folha").trim();
            const escuro = raiz.getPropertyValue("--f2-c4").trim();
            const meio = altura / 2;
            const passoPx = largura / picos.length;

            // Uma marca por fatia dizendo se aquele segundo virou corte. Fazer
            // essa conta dentro do laço de desenho seria onze comparações por
            // fatia — nove mil comparações a cada redesenho da janela.
            const dentro = new Uint8Array(picos.length);
            for (const c of mapa.entregues) {
                const de = Math.max(0, Math.floor((c.inicio / dur) * picos.length));
                const ate = Math.min(picos.length, Math.ceil((c.fim / dur) * picos.length));
                dentro.fill(1, de, ate);
            }

            for (let i = 0; i < picos.length; i += 1) {
                ctx.fillStyle = dentro[i] ? claro : escuro;
                const h = Math.max(0.5, picos[i] * (altura * 0.46));
                ctx.fillRect(i * passoPx, meio - h, Math.max(0.8, passoPx - 0.25), h * 2);
            }
        }

        (async function buscarAOnda() {
            if (!mapa.fonte.tem_som) return;
            const onda = await pedir("/api/mapa/onda?fatias=900");
            if (onda.ok === false) return;
            picos = onda.picos;
            desenhar();
        })();

        new ResizeObserver(desenhar).observe(caixa);
        corpo.addEventListener("mouseleave", emRepouso);
        emRepouso();
        return corpo;
    }

    MONTADO.mapa = async function () {
        const mapa = await pedir("/api/mapa");
        if (mapa.ok === false || !mapa.tem_rodada) {
            window.furiaEstado({ texto: "nenhuma rodada para mapear" });
            SONS.falha();
            return;
        }
        fecharJanela("mapa");
        abrirJanela({ nome: "mapa", largura: 1080, altura: 312, corpo: montarOMapa(mapa) });
    };

    /* ── moer: a bancada ligada no motor ────────────────────────────────────

       O motor é o do Furia 1 e continua onde sempre esteve. A bancada manda o
       vídeo pela mesma rota que a interface antiga sempre usou e escuta o
       mesmo canal — então não existe "o novo funciona e o velho quebrou": é o
       mesmo programa.

       Cada corte que fica pronto no disco chega aqui na hora, um a um, e sobe
       na parede. Ele não espera meia hora olhando uma barra para descobrir no
       fim se prestou: o terceiro corte já está lá para julgar enquanto o
       oitavo ainda está sendo cortado. */

    const CANAL = window.io ? window.io() : null;
    let fonteNaBancada = null;
    let moendo = false;

    /* Tudo que a máquina disse nesta sessão, para o registro poder devolver.
       Com teto: uma rodada de duas horas cospe milhares de linhas, e guardar
       todas na memória de uma aba aberta o dia inteiro é como o navegador
       engasga sem ninguém entender por quê. As mais recentes são as que
       importam para diagnosticar. */
    const REGISTRO = [];
    const TETO_DO_REGISTRO = 4000;

    function anotar(mensagem, nivel) {
        REGISTRO.push({
            hora: new Date().toLocaleTimeString("pt-BR"),
            diz: String(mensagem || ""),
            nivel: String(nivel || "info"),
        });
        if (REGISTRO.length > TETO_DO_REGISTRO) REGISTRO.splice(0, REGISTRO.length - TETO_DO_REGISTRO);
        window.furiaRegistroMudou?.();
    }

    function limparPrefixo(mensagem) {
        // O motor carimba "[Versão 2.0 · abc123] " em toda linha, o que serve
        // para o registro e não serve para a faixa de cima.
        return String(mensagem || "").replace(/^\[Versão[^\]]*\]\s*/, "");
    }

    function corteDaEntrega(bruto, indice) {
        const inicio = Number(bruto.start ?? 0);
        const fim = Number(bruto.end ?? 0);
        const bandeiras = bruto.review_flags || {};
        return {
            n: Number(bruto.rank ?? indice + 1),
            inicio, fim,
            duracao: Number(bruto.duration ?? Math.max(0, fim - inicio)),
            // Antes da folha existir, quem sabe se o corte pede conferência é o
            // próprio corte que acabou de chegar.
            conferir: Boolean(bruto.review_required || bandeiras.review_required
                || (bruto.review_reasons || []).length),
            motivos: (bruto.review_reasons || []).map(String).slice(0, 4),
            fala: String(bruto.title || bruto.text || "").trim(),
            origem: String(bruto.candidate_origin || ""),
            ajustado: false,
            aoVivo: true,
        };
    }

    function corteChegou(dados) {
        const corte = corteDaEntrega(dados.clip || {}, dados.index || 0);
        if (!cortesNaParede.some((c) => c.n === corte.n)) cortesNaParede.push(corte);
        cortesNaParede.sort((a, b) => a.n - b.n);
        pintarAParede({
            cortes: cortesNaParede,
            // Durante a rodada não existe folha ainda, então não existe quadro
            // para arrancar: o mural mostra a fala, que é o que já chegou.
            fonte: { tem_som: true, tem_imagem: false },
            resumo: {
                entregues: cortesNaParede.length,
                conferir: cortesNaParede.filter((c) => c.conferir).length,
            },
        });
        window.furiaEstado({
            texto: `moendo · corte ${dados.delivered || cortesNaParede.length} de ${dados.expected || "?"}`,
            trabalhando: true,
            // O contador de fita conta o material já moído: até onde da fonte a
            // máquina já chegou. É a mesma piada do relógio do Poolsuite, só
            // que aqui o número é verdade.
            fita: corte.fim,
        });
        SONS.tique();
    }

    if (CANAL) {
        CANAL.on("progress", (dados) => {
            // O registro anota SEMPRE, mesmo fora de uma rodada: é o que ele
            // me manda quando alguma coisa deu errado, e a linha que explica
            // costuma ser justamente a que veio antes de ele mandar moer.
            anotar(limparPrefixo(dados.message), dados.level);
            if (!moendo) return;
            const texto = limparPrefixo(dados.message).slice(0, 90);
            if (texto) window.furiaEstado({ texto, trabalhando: true });
        });

        CANAL.on("status", (evento) => {
            const qual = evento?.status;
            const dados = evento?.data || {};
            if (qual === "clip_ready") { corteChegou(dados); return; }
            if (qual === "complete_done") {
                moendo = false;
                anotar(`rodada terminada: ${dados.total_clips || 0} cortes`, "success");
                window.furiaEstado({ texto: `${dados.total_clips || 0} cortes prontos`, trabalhando: false });
                SONS.feito();
                // A folha de decisões só existe no fim. Agora que ela existe, a
                // parede troca o que chegou ao vivo pela versão de verdade —
                // com quadro, com motivo escrito e com o mapa alimentado.
                abrirAParede();
                return;
            }
            if (qual === "error") {
                moendo = false;
                const oQue = limparPrefixo(dados.error || "deu errado");
                anotar(oQue, "error");
                window.furiaEstado({ texto: oQue, trabalhando: false });
                SONS.falha();
                return;
            }
            if (qual === "cancelled") {
                moendo = false;
                window.furiaEstado({ texto: "cancelado", trabalhando: false });
            }
        });
    }

    async function moer() {
        if (moendo) { window.furiaEstado({ texto: "já está moendo" }); return; }
        if (!fonteNaBancada) return;
        // Caminho absoluto quando ele escolheu na janela do Windows; caminho de
        // dentro da pasta de trabalho no resto dos casos. Quem decide o que é
        // permitido é o motor, que já tinha essa regra.
        const alvo = fonteNaBancada.caminho || fonteNaBancada.chave;

        moendo = true;
        cortesNaParede = [];
        anotar(`moendo: ${fonteNaBancada.nome}`, "success");
        window.furiaEstado({ texto: "moendo", trabalhando: true, fita: 0 });
        SONS.armar();

        const resposta = await pedir("/api/process/complete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ video_path: alvo }),
        });
        if (resposta.ok === false || resposta.error) {
            moendo = false;
            window.furiaEstado({ texto: resposta.erro || resposta.error, trabalhando: false });
            SONS.falha();
        }
    }

    /* ── ajustes ────────────────────────────────────────────────────────────

       O programa velho tinha uma gaveta com quarenta e cinco campos, e ele
       reclamou dela com todas as letras. A gaveta não era feia — era grande.

       Aqui só entra o que MUDA UM CORTE, como fileira de opções em vez de
       campo para digitar. E antes dos controles vem o que ele mais precisa
       ver antes de mandar meia hora de entrevista para o moinho: se a máquina
       está inteira. O resto dos ajustes continua na interface antiga. */

    const ESCOLHAS = [
        {
            chave: "cut_duration", nome: "duração alvo",
            opcoes: [[30, "30 s"], [45, "45 s"], [60, "60 s"], [90, "90 s"], [120, "2 min"]],
        },
        {
            chave: "padding", nome: "folga na borda",
            opcoes: [[0, "colado"], [0.25, "0,25 s"], [0.5, "0,5 s"], [1, "1 s"]],
        },
        {
            chave: "transcription_source", nome: "quem transcreve",
            opcoes: [["auto", "automático"], ["whisper", "whisper aqui"], ["gemini", "gemini"]],
        },
        {
            chave: "whisper_model", nome: "modelo do whisper",
            opcoes: [["base", "base · rápido"], ["small", "small"], ["medium", "medium · lento"]],
        },
        {
            chave: "gemini_model", nome: "modelo do gemini",
            opcoes: [["gemini-2.5-flash", "2.5 flash"], ["gemini-2.5-pro", "2.5 pro"]],
        },
        {
            chave: "campaign_hub_account", nome: "conta do chub",
            opcoes: [["@renansantosmbl", "renansantosmbl"],
                     ["@renansantosreserva", "reserva"],
                     ["@partidomissao", "partido missão"]],
        },
    ];

    function mesmoValor(a, b) {
        // "0.25" e 0.25 são o mesmo ajuste. Comparar como texto puro deixaria
        // a opção certa apagada e ele clicaria de novo achando que não pegou.
        const na = Number(a);
        const nb = Number(b);
        if (Number.isFinite(na) && Number.isFinite(nb)) return na === nb;
        return String(a) === String(b);
    }

    function montarOsAjustes(ajustes, presets, estado) {
        const corpo = document.createElement("div");
        corpo.className = "f2-corpo f2-ajustes";
        corpo.innerHTML = `
            <div class="f2-secao">estado da máquina</div>
            <div class="f2-pecas" data-pecas></div>
            <div class="f2-secao">o que muda o corte</div>
            <div data-escolhas></div>
            <div class="f2-talho-pe">
                <button class="f2-tecla" data-antigo type="button">abrir os ajustes completos</button>
                <span class="f2-recado" data-recado></span>
            </div>`;

        const oRecado = corpo.querySelector("[data-recado]");
        function dizer(texto, ruim) {
            oRecado.textContent = texto;
            oRecado.classList.toggle("f2-ruim", !!ruim);
            if (ruim) SONS.falha();
            window.clearTimeout(dizer.relogio);
            dizer.relogio = window.setTimeout(() => { oRecado.textContent = ""; }, 6000);
        }

        /* ── o estado ─────────────────────────────────────────────────────── */

        const pecas = corpo.querySelector("[data-pecas]");
        for (const peca of estado) {
            const linha = document.createElement("div");
            linha.className = "f2-peca-linha";
            linha.innerHTML = `<span class="f2-led" data-viva="${peca.viva}"></span>
                <span class="f2-peca-nome"></span><span class="f2-peca-diz"></span>`;
            linha.querySelector(".f2-peca-nome").textContent = peca.nome;
            linha.querySelector(".f2-peca-diz").textContent = peca.diz;
            pecas.appendChild(linha);
        }

        /* ── as escolhas ──────────────────────────────────────────────────── */

        const onde = corpo.querySelector("[data-escolhas]");
        const todas = ESCOLHAS.concat([{
            chave: "render_preset", nome: "formato de saída",
            opcoes: (presets || []).map((p) => [p.id, p.name]),
        }]);

        for (const escolha of todas) {
            if (!escolha.opcoes.length) continue;
            const linha = document.createElement("div");
            linha.className = "f2-escolha";
            linha.innerHTML = `<span class="f2-escolha-nome"></span><div class="f2-opcoes"></div>`;
            linha.querySelector(".f2-escolha-nome").textContent = escolha.nome;
            const caixa = linha.querySelector(".f2-opcoes");

            for (const [valor, rotulo] of escolha.opcoes) {
                const botao = document.createElement("button");
                botao.type = "button";
                botao.className = "f2-opcao";
                botao.textContent = rotulo;
                botao.setAttribute("aria-pressed",
                    mesmoValor(ajustes[escolha.chave], valor) ? "true" : "false");
                botao.addEventListener("click", async () => {
                    const antes = caixa.querySelector('[aria-pressed="true"]');
                    caixa.querySelectorAll(".f2-opcao").forEach((b) => b.setAttribute("aria-pressed", "false"));
                    botao.setAttribute("aria-pressed", "true");

                    const resposta = await pedir("/api/settings", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ [escolha.chave]: valor }),
                    });
                    if (resposta.ok === false) {
                        // Desmarcar de volta. Deixar a opção nova acesa depois
                        // de uma gravação que falhou é a mesma mentira do
                        // ajuste do Furia 1 que respondia 200 e não guardava.
                        botao.setAttribute("aria-pressed", "false");
                        antes?.setAttribute("aria-pressed", "true");
                        dizer(resposta.erro || "não deu para guardar", true);
                        return;
                    }
                    ajustes[escolha.chave] = valor;
                    anotar(`ajuste: ${escolha.nome} passou para ${rotulo}`);
                    SONS.tique();
                    dizer(`${escolha.nome}: ${rotulo}`);
                });
                caixa.appendChild(botao);
            }
            onde.appendChild(linha);
        }

        corpo.querySelector("[data-antigo]").addEventListener("click", () => {
            // Os quarenta e cinco campos continuam existindo, na interface
            // antiga, para o dia raro em que ele precisar de um deles. Tirar
            // seria quebrar o que já funciona; trazer seria refazer a gaveta.
            window.open("/", "_blank", "noopener");
        });

        return corpo;
    }

    MONTADO.ajustes = async function () {
        const [ajustes, presets, chub, ollama] = await Promise.all([
            pedir("/api/settings"),
            pedir("/api/render-presets"),
            pedir("/api/campaign-hub/status"),
            pedir("/api/ollama/status"),
        ]);
        if (ajustes.ok === false) {
            window.furiaEstado({ texto: "não deu para ler os ajustes" });
            SONS.falha();
            return;
        }

        const conta = ajustes.campaign_hub_account || "@renansantosmbl";
        const daConta = (chub.accounts || {})[conta] || {};
        const estado = [
            {
                nome: "gemini",
                viva: ajustes.gemini_api_key_configured ? "1" : "ruim",
                diz: ajustes.gemini_api_key_configured
                    ? `chave posta · ${ajustes.gemini_model || ""}`
                    : "sem chave — a análise de vídeo não roda",
            },
            {
                nome: "chub",
                viva: chub.available ? "1" : "0",
                diz: chub.available
                    ? `de pé · ${daConta.hook_observations || 0} observações de gancho em ${conta}`
                    : "não respondeu",
            },
            {
                nome: "transcrição",
                viva: "1",
                diz: `${ajustes.transcription_source || "auto"} · whisper ${ajustes.whisper_model || ""} nesta máquina`,
            },
            {
                nome: "ollama",
                viva: ollama.connected ? "1" : "0",
                diz: ollama.connected ? `${ollama.model} de pé` : "desligado — não é obrigatório",
            },
            {
                nome: "versão",
                viva: "1",
                diz: `${ajustes.program_version || ""} · ${ajustes.program_revision || ""}`,
            },
        ];

        fecharJanela("ajustes");
        abrirJanela({
            nome: "ajustes", largura: 680, altura: 560,
            corpo: montarOsAjustes(ajustes, presets.presets || [], estado),
        });
    };

    /* ── registro ───────────────────────────────────────────────────────────

       Ele já precisou me mandar o registro três vezes, e as três vezes copiou
       da janela preta do lançador — porque era o único lugar de onde dava para
       levar texto embora. Mostrar não resolve: selecionar centenas de linhas
       com o mouse dentro de uma caixa com rolagem é tarefa que ninguém
       termina. Por isso esta janela tem menos leitura e mais SAÍDA. */

    function textoDoRegistro() {
        const cabeca = [
            `Furia — registro da sessão`,
            `gerado em ${new Date().toLocaleString("pt-BR")}`,
            `${REGISTRO.length} linhas`,
            "",
        ];
        return cabeca.concat(
            REGISTRO.map((l) => `[${l.hora}] ${l.nivel === "info" ? "" : l.nivel.toUpperCase() + " "}${l.diz}`),
        ).join("\n");
    }

    async function levarEmbora(texto) {
        try {
            await navigator.clipboard.writeText(texto);
            return true;
        } catch (erro) {
            // A área de transferência é negada fora de https em parte dos
            // navegadores. Sem plano B, copiar falharia calado — e falha
            // calada é o defeito mais caro deste programa.
            const caixa = document.createElement("textarea");
            caixa.value = texto;
            caixa.style.position = "fixed";
            caixa.style.opacity = "0";
            document.body.appendChild(caixa);
            caixa.select();
            let deu = false;
            try { deu = document.execCommand("copy"); } catch (e2) { deu = false; }
            caixa.remove();
            return deu;
        }
    }

    function montarORegistro() {
        const corpo = document.createElement("div");
        corpo.className = "f2-corpo f2-registro";
        corpo.innerHTML = `
            <div class="f2-linhas" data-linhas></div>
            <div class="f2-talho-pe">
                <button class="f2-tecla" data-copiar type="button">copiar tudo</button>
                <button class="f2-tecla" data-salvar type="button">salvar num arquivo</button>
                <button class="f2-tecla" data-pasta type="button">abrir a pasta</button>
                <button class="f2-tecla" data-diag type="button">abrir o diagnóstico</button>
                <span class="f2-recado" data-recado></span>
            </div>`;

        const linhas = corpo.querySelector("[data-linhas]");
        const oRecado = corpo.querySelector("[data-recado]");
        function dizer(texto, ruim) {
            oRecado.textContent = texto;
            oRecado.classList.toggle("f2-ruim", !!ruim);
            if (ruim) SONS.falha();
            window.clearTimeout(dizer.relogio);
            dizer.relogio = window.setTimeout(() => { oRecado.textContent = ""; }, 6000);
        }

        function pintar() {
            if (!REGISTRO.length) {
                linhas.innerHTML = `<div class="f2-registro-vazio">a máquina ainda não disse nada nesta sessão</div>`;
                return;
            }
            // Colado no fim continua colado no fim; rolado para cima fica onde
            // ele deixou. Puxar a rolagem de volta enquanto ele lê uma linha
            // de erro é o jeito mais rápido de tornar o registro inútil.
            const noFim = linhas.scrollTop + linhas.clientHeight >= linhas.scrollHeight - 24;
            linhas.textContent = "";
            for (const l of REGISTRO) {
                const linha = document.createElement("div");
                linha.className = "f2-linha-reg";
                linha.dataset.nivel = l.nivel;
                const hora = document.createElement("span");
                hora.className = "f2-linha-hora";
                hora.textContent = l.hora;
                const diz = document.createElement("span");
                diz.className = "f2-linha-diz";
                diz.textContent = l.diz;
                linha.append(hora, diz);
                linhas.appendChild(linha);
            }
            if (noFim) linhas.scrollTop = linhas.scrollHeight;
        }

        corpo.querySelector("[data-copiar]").addEventListener("click", async () => {
            if (!REGISTRO.length) { dizer("não há nada para copiar"); return; }
            const deu = await levarEmbora(textoDoRegistro());
            if (deu) { SONS.feito(); dizer(`${REGISTRO.length} linhas copiadas — é só colar na conversa`); }
            else dizer("o navegador não deixou copiar; use salvar num arquivo", true);
        });

        corpo.querySelector("[data-salvar]").addEventListener("click", () => {
            if (!REGISTRO.length) { dizer("não há nada para salvar"); return; }
            const bolha = new Blob([textoDoRegistro()], { type: "text/plain;charset=utf-8" });
            const link = document.createElement("a");
            link.href = URL.createObjectURL(bolha);
            const agora = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, "");
            link.download = `furia-registro-${agora}.txt`;
            link.click();
            window.setTimeout(() => URL.revokeObjectURL(link.href), 4000);
            SONS.feito();
            dizer("salvo na pasta de downloads");
        });

        corpo.querySelector("[data-pasta]").addEventListener("click", async () => {
            const r = await pedir("/api/open-logs", { method: "POST" });
            // Sem ambiente gráfico o comando falha, e aí dizer ONDE fica ainda
            // resolve: ele abre a pasta na mão.
            if (r.ok === false || r.error) dizer(r.pasta || r.erro || r.error, true);
            else dizer(r.pasta || "pasta aberta");
        });

        corpo.querySelector("[data-diag]").addEventListener("click", async () => {
            const r = await pedir("/api/open-diagnostics", { method: "POST" });
            const onde = r.pasta ? `${r.pasta} · ${r.arquivos || 0} arquivos` : "";
            if (r.ok === false || r.error) dizer(onde || r.erro || r.error, true);
            else dizer(onde || "pasta aberta");
        });

        pintar();
        window.furiaRegistroMudou = () => {
            if (abertas.registro) pintar();
        };
        return corpo;
    }

    MONTADO.registro = function () {
        abrirJanela({ nome: "registro", largura: 820, altura: 460, corpo: montarORegistro() });
    };

    /* ── o painel ───────────────────────────────────────────────────────────

       Magnífico, responsável, bonito e útil — as quatro palavras dele. A
       difícil é responsável, e ela manda em tudo aqui.

       Regra que não se negocia: um número que a ferramenta gera sobre o que a
       ferramenta fez não mede nada. Tudo nesta tela é medição de FORA —
       desempenho de post publicado, gancho rotulado por gente, tema
       controlado. Vinte e nove mil posts, não onze cortes.

       A segunda metade da responsabilidade é o tamanho da amostra: um gancho
       com mediana 1,19 em QUATRO posts não é um gancho bom, é um rumor. Daí a
       barra oca. */

    const EVIDENCIA_FINA = 10;    // abaixo disso o número é rumor, não medida

    function porCento(x) { return `${Math.max(0, Math.min(100, x * 100))}%`; }

    function numeroBonito(n) {
        return Number(n || 0).toLocaleString("pt-BR");
    }

    function razao(v) {
        return `${Number(v || 0).toFixed(2).replace(".", ",")}×`;
    }

    function montarOPainel(dados, aoContar) {
        const bloco = document.createElement("div");

        function fileira(itens, titulo, direita) {
            if (!itens.length) return;
            const cabeca = document.createElement("div");
            cabeca.className = "f2-painel-titulo";
            cabeca.innerHTML = `<span style="letter-spacing:0.2em;text-transform:uppercase">${titulo}</span>`;
            if (direita) {
                const nota = document.createElement("span");
                nota.textContent = direita;
                cabeca.appendChild(nota);
            }
            bloco.appendChild(cabeca);

            // O teto do eixo é comum a todas as barras da fileira: escalas
            // diferentes por linha fariam duas barras do mesmo tamanho
            // valerem números diferentes, que é a mentira mais fácil de contar
            // com um gráfico.
            //
            // E o eixo é medido pelas MEDIANAS, que é o que as barras
            // desenham. Esticá-lo até o p90 mais alto (3,18) empurrava todas
            // as barras para o primeiro terço da pista e deixava dois terços
            // de vazio: o eixo passava a servir o risquinho de contexto em vez
            // de servir o dado. Quem não couber no eixo perde o risco e conta
            // o seu número na legenda do pé.
            const maiorMediana = Math.max(...itens.map((i) => Number(i.mediana || 0)), 1.2);
            const teto = Math.ceil(maiorMediana * 1.25 * 10) / 10;
            const posicaoDoUm = 1 / teto;

            for (const item of itens) {
                const mediana = Number(item.mediana || 0);
                const n = Number(item.n || 0);
                const fina = n < EVIDENCIA_FINA;
                const acima = mediana >= 1;

                const linha = document.createElement("div");
                linha.className = "f2-barra-linha";
                linha.innerHTML = `
                    <span class="f2-barra-nome"></span>
                    <span class="f2-pista">
                        <span class="f2-um"></span>
                        <span class="f2-barra"></span>
                    </span>
                    <span class="f2-barra-valor"></span>`;
                linha.querySelector(".f2-barra-nome").textContent =
                    String(item.familia || item.slug || "").replace(/-/g, " ");
                linha.querySelector(".f2-barra-valor").textContent = razao(mediana);
                linha.querySelector(".f2-um").style.left = porCento(posicaoDoUm);

                const barra = linha.querySelector(".f2-barra");
                barra.dataset.lado = acima ? "acima" : "abaixo";
                barra.dataset.fina = fina ? "1" : "0";
                const de = Math.min(mediana, 1) / teto;
                const ate = Math.max(mediana, 1) / teto;
                barra.style.left = porCento(de);
                barra.style.width = porCento(ate - de);

                // O teto do gancho: até onde ele chega quando dá certo. Só
                // aparece quando é maior que a mediana e cabe no eixo.
                const p90 = Number(item.p90 || 0);
                if (p90 > mediana && p90 <= teto) {
                    const risco = document.createElement("span");
                    risco.className = "f2-teto";
                    risco.style.left = porCento(p90 / teto);
                    linha.querySelector(".f2-pista").appendChild(risco);
                }

                const nome = String(item.familia || item.slug || "");
                const conta = () => aoContar({
                    marca: `${razao(mediana)} · ${numeroBonito(n)} posts`,
                    texto: fina
                        ? `${nome} — evidência fina: ${n} posts só. O número existe, mas ainda não é medida.`
                        : `${nome} — ${p90 ? `chega a ${razao(p90)} quando dá certo. ` : ""}`
                          + `Medido em ${numeroBonito(n)} posts publicados.`,
                    ruim: fina ? "evidência fina" : "",
                });
                linha.addEventListener("mouseenter", conta);
                bloco.appendChild(linha);
            }
        }

        fileira(dados.ganchos || [], "o que puxa e o que afunda",
                "mediana contra a da própria conta · barra oca = evidência fina");

        // Os temas que puxam e os que afundam entram na MESMA fileira, e não
        // em duas. Duas fileiras são dois eixos, e dois eixos fazem uma barra
        // de 2,11 parecer do tamanho de uma de 0,71 — comparação errada com
        // cara de comparação certa.
        const temas = ((dados.temas || {}).melhores || [])
            .concat((dados.temas || {}).piores || [])
            .sort((a, b) => Number(b.mediana || 0) - Number(a.mediana || 0));
        fileira(temas, "tema", "os que mais puxam e os que mais afundam, no mesmo eixo");
        return bloco;
    }

    async function pintarOPainel(janela, conta, plataforma) {
        const corpo = janela.querySelector(".f2-painel");
        const onde = corpo.querySelector("[data-grafico]");
        const espelho = corpo.querySelector("[data-espelho]");
        const led = corpo.querySelector("[data-led]");
        const marca = corpo.querySelector("[data-marca]");
        const fala = corpo.querySelector("[data-fala]");
        const aviso = corpo.querySelector("[data-aviso]");

        onde.textContent = "";
        const dados = await pedir(
            `/api/painel?conta=${encodeURIComponent(conta)}&plataforma=${encodeURIComponent(plataforma)}`,
        );
        if (dados.ok === false) { espelho.textContent = "não deu para ler o espelho"; return; }

        const e = dados.espelho || {};
        led.dataset.viva = e.disponivel ? "1" : "ruim";
        espelho.innerHTML = "";
        if (e.disponivel) {
            const quando = String(e.gerado_em || "").slice(0, 10).split("-").reverse().join("/");
            const posts = document.createElement("b");
            posts.textContent = numeroBonito(e.posts_com_desempenho);
            const cortes = document.createElement("b");
            cortes.textContent = numeroBonito(e.cortes_publicados);
            espelho.append(
                "espelho do chub · ", posts, " posts medidos · ",
                cortes, " cortes publicados · ", quando ? `de ${quando}` : "",
            );
        } else {
            espelho.textContent = "o espelho do chub não está instalado — sem ele o painel não mede nada";
        }

        function aoContar({ marca: m, texto, ruim }) {
            marca.textContent = m || "";
            fala.classList.toggle("f2-quieta", !texto);
            fala.textContent = texto || "";
            aviso.textContent = ruim || "";
        }
        function emRepouso() {
            marca.textContent = "";
            aviso.textContent = "";
            fala.classList.add("f2-quieta");
            const ganchos = dados.ganchos || [];
            const melhor = ganchos[0];
            // A tela abre dizendo alguma coisa. Painel que abre mudo obriga o
            // sujeito a caçar o número que interessa, e ele não vai caçar.
            fala.textContent = melhor
                ? `nesta conta, o gancho que mais puxa é ${String(melhor.familia).replace(/-/g, " ")}`
                  + `, ${razao(melhor.mediana)} a mediana em ${numeroBonito(melhor.n)} posts`
                : "sem gancho medido nesta conta e plataforma";
        }

        onde.appendChild(montarOPainel(dados, aoContar));
        onde.addEventListener("mouseleave", emRepouso);
        emRepouso();
    }

    MONTADO.painel = async function () {
        const primeiro = await pedir("/api/painel");
        if (primeiro.ok === false) {
            window.furiaEstado({ texto: "não deu para abrir o painel" });
            SONS.falha();
            return;
        }
        let conta = primeiro.conta;
        let plataforma = primeiro.plataforma;

        const corpo = document.createElement("div");
        corpo.className = "f2-corpo f2-painel";
        corpo.innerHTML = `
            <div class="f2-painel-topo">
                <div class="f2-opcoes" data-contas></div>
                <div class="f2-opcoes" data-plataformas></div>
            </div>
            <div class="f2-espelho"><span class="f2-led" data-led></span><span data-espelho></span></div>
            <div class="f2-painel-corpo" data-grafico></div>
            <div class="f2-legenda">
                <span class="f2-legenda-marca" data-marca></span>
                <span class="f2-legenda-fala f2-quieta" data-fala></span>
                <span class="f2-legenda-aviso" data-aviso></span>
            </div>`;

        const janela = abrirJanela({ nome: "painel", largura: 1000, altura: 560, corpo });

        function fileiraDeOpcoes(caixa, valores, atual, aoEscolher) {
            caixa.textContent = "";
            for (const [valor, rotulo] of valores) {
                const b = document.createElement("button");
                b.type = "button";
                b.className = "f2-opcao";
                b.textContent = rotulo;
                b.setAttribute("aria-pressed", valor === atual ? "true" : "false");
                b.addEventListener("click", () => { aoEscolher(valor); SONS.tique(); });
                caixa.appendChild(b);
            }
        }

        function repintar() {
            fileiraDeOpcoes(
                corpo.querySelector("[data-contas]"),
                (primeiro.contas || [conta]).map((c) => [c, c.replace("@", "")]),
                conta,
                (v) => { conta = v; repintar(); },
            );
            fileiraDeOpcoes(
                corpo.querySelector("[data-plataformas]"),
                [["instagram", "instagram"], ["facebook", "facebook"], ["tiktok", "tiktok"]],
                plataforma,
                (v) => { plataforma = v; repintar(); },
            );
            pintarOPainel(janela, conta, plataforma);
        }
        repintar();
    };

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

    /* ── abrir na última rodada ─────────────────────────────────────────────
       Se existe uma folha de decisões, a bancada abre já com os cortes dela.
       O programa fechado ontem à noite reabre hoje no mesmo lugar — não numa
       tela vazia perguntando o que ele quer fazer, que é uma pergunta que ele
       já respondeu. */
    (async function retomar() {
        const respiro = document.createElement("div");
        respiro.className = "f2-respiro";
        parede.appendChild(respiro);
        const achou = await abrirAParede();
        if (!achou) respiro.remove();
    })();
})();
