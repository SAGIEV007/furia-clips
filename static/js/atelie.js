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

    /* ── tema ───────────────────────────────────────────────────────────────

       "nem sei onde altero para o tema branco". Não sabia porque não havia
       onde: o botão nunca existiu, e o claro também não — 34 lugares do estilo
       antigo pintavam com preto translúcido fixo, que no claro virava laje
       cinza por cima do texto.

       Escuro é o padrão e NÃO segue o sistema. Premiere, DaVinci e CapCut
       também não seguem: abrem escuros e ficam escuros até alguém mandar o
       contrário. Uma ferramenta de corte que fica branca porque o Windows
       mudou de humor está errada para quem a usa.                             */

    const botaoTema = document.getElementById("btnTema");

    function aplicarTema(tema) {
        const raiz = document.documentElement;
        if (tema === "claro" || tema === "escuro") raiz.dataset.tema = tema;
        else delete raiz.dataset.tema;

        // Escuro é o padrão e não segue o sistema, de propósito: ferramenta de
        // corte não pode ficar branca porque o Windows mudou de humor.
        const claroAgora = tema === "claro";
        if (botaoTema) {
            botaoTema.querySelector(".material-icons-round").textContent =
                claroAgora ? "light_mode" : "dark_mode";
            botaoTema.title = claroAgora
                ? "Tema claro — clique para escurecer"
                : "Tema escuro — clique para clarear";
        }
        // O canvas da onda e o mapa desenham com a cor lida do CSS: trocado o
        // tema, o que já está na tela ficou com a cor antiga.
        window.redesenharTalhos?.();
        window.desenharMapaDaFonte?.();
    }

    botaoTema?.addEventListener("click", () => {
        const atual = document.documentElement.dataset.tema;
        const proximo = atual === "claro" ? "escuro" : "claro";
        aplicarTema(proximo);
        guardar("furia.tema", proximo);
    });

    aplicarTema(lembrar("furia.tema") || "");

    /* ── seleção de corte ───────────────────────────────────────────────────

       O inspetor era permanente e passava o dia dizendo "Nada selecionado" —
       450 px de tela para uma frase. Agora ele entra quando há seleção. O mapa
       da fonte chama isto ao clicar num bloco.                                */

    window.selecionarCorte = function selecionarCorte(indice) {
        const inspetor = document.getElementById("inspetor");
        const cartao = document.querySelector(`#resultsGrid .clip-card:nth-of-type(${indice + 1})`);
        cartao?.scrollIntoView({ block: "nearest", behavior: "smooth" });
        document.querySelectorAll("#resultsGrid .clip-card.is-selected")
            .forEach((n) => n.classList.remove("is-selected"));
        cartao?.classList.add("is-selected");
        if (inspetor && inspetor.textContent.trim()) inspetor.classList.add("is-active");
    };

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

/* ── levar o registro para fora ──────────────────────────────────────────── */
//
// "não tem nem console para eu copiar os logs e te mandar exceto o .bat". A
// gaveta já mostrava tudo, mas mostrar não resolve: selecionar centenas de
// linhas com o mouse dentro de uma caixa com rolagem é uma tarefa que ninguém
// termina. O registro precisa sair inteiro, num clique.
(function () {
    "use strict";
    const aviso = document.getElementById("gavetaAviso");
    const dizer = (texto, erro) => {
        if (!aviso) return;
        aviso.textContent = texto;
        aviso.style.color = erro ? "var(--at-ruim)" : "var(--at-bom)";
        window.setTimeout(() => { aviso.textContent = ""; }, 6000);
    };

    function registro() {
        const linhas = [...document.querySelectorAll("#consoleOutput .console-line")]
            .map((l) => l.textContent.replace(/\s+/g, " ").trim());
        const versao = document.getElementById("runtimeVersion")?.textContent?.trim() || "";
        return [
            `Furia Clips ${versao}`,
            `registro copiado em ${new Date().toLocaleString("pt-BR")}`,
            `${linhas.length} linhas`,
            "",
            ...linhas,
        ].join("\n");
    }

    /* Copiar, com plano B. A área de transferência moderna é negada fora de
       conexão segura em parte dos navegadores, e o Furia roda local, sem
       certificado — sem o caminho antigo, copiar falharia calado justamente na
       máquina dele.

       (O endereço local não aparece escrito aqui de propósito: um teste proíbe
       "http" nestes arquivos para garantir que nada busque rede, e ele é uma
       verificação burra que não deve ser afrouxada por causa de um comentário.) */
    async function copiar(texto) {
        try {
            await navigator.clipboard.writeText(texto);
            return true;
        } catch (erro) {
            const caixa = document.createElement("textarea");
            caixa.value = texto;
            caixa.style.position = "fixed";
            caixa.style.opacity = "0";
            document.body.appendChild(caixa);
            caixa.select();
            const deu = document.execCommand("copy");
            caixa.remove();
            return deu;
        }
    }

    document.getElementById("btnCopiarRegistro")?.addEventListener("click", async () => {
        const texto = registro();
        const deu = await copiar(texto);
        dizer(
            deu ? `copiado — ${texto.split("\n").length - 4} linhas`
                : "não deu para copiar; use Salvar em arquivo",
            !deu,
        );
    });

    document.getElementById("btnSalvarRegistro")?.addEventListener("click", () => {
        const agora = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
        const link = document.createElement("a");
        link.href = URL.createObjectURL(new Blob([registro()], { type: "text/plain;charset=utf-8" }));
        link.download = `furia-registro-${agora}.txt`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(() => URL.revokeObjectURL(link.href), 4000);
        dizer("salvo na pasta de downloads");
    });

    /* ── mandar a rodada para análise ───────────────────────────────────────

       "onde eu acho essas informações para te passar? no console mesmo?"

       O relatório completo sempre existiu, mas mora em
       C:\\Users\\<ele>\\FuriaClipsData\\diagnostics, e chegar lá exige navegar no
       explorador. Dois caminhos agora:

       - abrir a pasta, para arrastar o arquivo inteiro quando o assunto for a
         seleção toda;
       - copiar um RESUMO, que é o que resolve a pergunta que eu faço mais: qual
         corte abriu ou fechou errado. Para isso não preciso de 500 KB de JSON,
         preciso da primeira e da última frase de cada corte. Isso cabe numa
         mensagem, e ele pode marcar os ruins direto no texto colado.          */

    document.getElementById("btnAbrirPastaDiagnostico")?.addEventListener("click", async () => {
        try {
            const resposta = await fetch("/api/open-diagnostics", { method: "POST" });
            const corpo = await resposta.json();
            if (!resposta.ok) { dizer(corpo.error || "não deu", true); return; }
            dizer(
                corpo.arquivos
                    ? `pasta aberta · ${corpo.arquivos} relatório(s) · o mais novo é ${corpo.mais_recente}`
                    : "pasta aberta — ainda sem relatório; rode um vídeo primeiro",
            );
        } catch (erro) {
            dizer(String(erro.message).slice(0, 80), true);
        }
    });

    document.getElementById("btnCopiarResumoDaRodada")?.addEventListener("click", async () => {
        const cortes = window.state?.clips || [];
        if (!cortes.length) {
            dizer("nenhum corte nesta sessão ainda", true);
            return;
        }
        const relogio = (s) => {
            const t = Math.max(0, Math.round(Number(s) || 0));
            return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
        };
        const limpo = (texto) => String(texto || "").replace(/\s+/g, " ").trim();
        const descartados =
            window.state?.diagnostics?.descartados_por_sobreposicao
            || window.state?.selectionDiagnostics?.descartados_por_sobreposicao
            || [];

        const linhas = [
            `FURIA ${document.getElementById("runtimeVersion")?.textContent?.trim() || ""}`
            + ` · ${new Date().toLocaleString("pt-BR")}`,
            // O nome vem do estado, não do elemento: ler o textContent trazia
            // junto o ícone e a dica escondida ("cloud_upload Nenhum vídeo
            // carregado Importe ou cole o link…"), e a primeira linha do
            // resumo saía impossível de ler.
            `fonte: ${limpo(window.state?.selectedVideoName)
                || limpo(String(window.state?.selectedVideo || "").split(/[\\/]/).pop())
                || "não identificada"}`,
            `${cortes.length} corte(s) entregues`
            + (descartados.length ? ` · ${descartados.length} candidato(s) descartados pela peneira` : ""),
            "",
            "Marque abaixo o que abriu ou fechou errado:",
            "",
        ];
        cortes.forEach((corte, i) => {
            // Primeira e última frase são exatamente o que decide se a borda
            // ficou certa. O miolo não ajuda a responder isso e só faria o
            // texto não caber numa mensagem.
            const texto = limpo(corte.text);
            const frases = texto.split(/(?<=[.!?])\s+/).filter(Boolean);
            const abre = frases[0] || texto.slice(0, 120) || "(sem transcrição)";
            // A última "frase" só vale como fecho se ela FECHAR. Um trecho que
            // termina no meio da palavra não é o fim do corte — é sinal de que
            // a transcrição chegou cortada, e mostrá-lo faria eu julgar um
            // fecho que não existe.
            const ultima = frases.length > 1 ? frases[frases.length - 1] : "";
            const fecha = /[.!?]\s*$/.test(ultima)
                ? ultima
                : (ultima ? `${ultima} …(transcrição incompleta aqui)` : "");
            linhas.push(
                `#${corte.rank || i + 1}  ${relogio(corte.start)}–${relogio(corte.end)}`
                + `  (${Math.round(Number(corte.duration) || 0)}s, nota ${corte.viral_score ?? "—"})`
                + `${corte.review_status && corte.review_status !== "needs_review" ? ` · ${corte.review_status}` : ""}`,
            );
            linhas.push(`    abre:  ${abre.slice(0, 160)}`);
            if (fecha) linhas.push(`    fecha: ${fecha.slice(0, 160)}`);
            linhas.push("");
        });

        const soltos = descartados.filter((d) => !d.dentro_do_vencedor);
        if (soltos.length) {
            linhas.push(`Descartados que traziam material próprio (${soltos.length}):`);
            soltos.slice(0, 10).forEach((d) => {
                linhas.push(
                    `  ${relogio(d.inicio)}–${relogio(d.fim)} (${Math.round(d.duracao)}s`
                    + `${d.inedito_s != null ? `, ${Math.round(d.inedito_s)}s inéditos` : ""})`
                    + `  “${limpo(d.trecho).slice(0, 90)}”`,
                );
            });
        }

        const texto = linhas.join("\n");
        const deu = await copiar(texto);
        dizer(
            deu
                ? `resumo copiado — ${cortes.length} corte(s), ${texto.split("\n").length} linhas. Cole na conversa.`
                : "não deu para copiar; use Salvar em arquivo",
            !deu,
        );
    });

    document.getElementById("btnAbrirPastaLogs")?.addEventListener("click", async () => {
        try {
            const resposta = await fetch("/api/open-logs", { method: "POST" });
            const corpo = await resposta.json();
            dizer(resposta.ok ? (corpo.pasta || "pasta aberta") : (corpo.error || "não deu"), !resposta.ok);
        } catch (erro) {
            dizer(String(erro.message).slice(0, 80), true);
        }
    });
})();
