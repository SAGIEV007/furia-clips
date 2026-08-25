/* ═══════════════════════════════════════════════════════════════════════════
   O MAPA DA FONTE

   O editor pergunta a mesma coisa toda rodada: "estou perdendo cortes?". A
   resposta sempre existiu, dentro de um JSON de diagnóstico que ele precisa
   abrir, achar a chave certa e comparar números à mão.

   Aqui ela é a primeira coisa na tela. A fonte inteira vira uma régua. Cada
   corte entregue ocupa o pedaço exato de onde saiu. Embaixo, na pista dos
   descartados, ficam os candidatos que a peneira derrubou. O que não tem bloco
   em cima nem embaixo é material que ninguém aproveitou — e um vão grande fica
   marcado com a própria duração, porque é ali que ele decide se roda de novo.

   Medido na corrida real dele (PENÉLOPE, 29 min): 11 cortes entregues, 21
   descartados por sobreposição, dos quais 12 estavam INTEIROS dentro de um
   corte entregue. Esses doze não são perda — o corte longo contém aquela fala.
   Por isso eles vão hachurados e apagados, e os outros nove vão sólidos: a
   diferença entre "conteúdo que eu já tenho" e "fala que morreu" é a única
   pergunta que o mapa precisa responder.

   Clicar num bloco leva o player da fonte para aquele ponto — o pedido dele,
   nas palavras dele: "ao clicar nos blocos deve transportar a pessoa para o
   player original no lugar do bloco".
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
    "use strict";

    // Abaixo disto um vão não é notícia: é a respiração entre dois cortes.
    const VAO_MINIMO_S = 60;

    function relogio(segundos) {
        const total = Math.max(0, Math.round(Number(segundos) || 0));
        return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
    }

    function duracaoPorExtenso(segundos) {
        const total = Math.round(Number(segundos) || 0);
        if (total < 60) return `${total}s`;
        const minutos = Math.floor(total / 60);
        const resto = total % 60;
        return resto ? `${minutos}min${resto}` : `${minutos}min`;
    }

    /* A duração da fonte. Sem ela não há régua, e adivinhar seria pior do que
       não desenhar: um mapa com a escala errada mente com confiança. */
    function duracaoDaFonte(cortes) {
        const candidatos = [
            Number(window.state?.sourceDuration),
            Number(window.state?.videoDuration),
            ...(cortes || []).map((c) => Number(c.source_duration)),
        ].filter((valor) => Number.isFinite(valor) && valor > 0);
        if (candidatos.length) return Math.max(...candidatos);
        // Último recurso: o fim do corte mais tardio, com uma folga honesta.
        const fim = Math.max(0, ...(cortes || []).map((c) => Number(c.end) || 0));
        return fim > 0 ? fim * 1.05 : 0;
    }

    function descartados() {
        const bruto = window.state?.diagnostics?.descartados_por_sobreposicao
            || window.state?.selectionDiagnostics?.descartados_por_sobreposicao
            || [];
        return Array.isArray(bruto) ? bruto : [];
    }

    /* Os pedaços da fonte que nenhum corte entregue cobre. */
    function vaos(cortes, duracao) {
        const faixas = (cortes || [])
            .map((c) => [Number(c.start) || 0, Number(c.end) || 0])
            .filter(([de, ate]) => ate > de)
            .sort((a, b) => a[0] - b[0]);
        const buracos = [];
        let cursor = 0;
        for (const [de, ate] of faixas) {
            if (de - cursor >= VAO_MINIMO_S) buracos.push([cursor, de]);
            cursor = Math.max(cursor, ate);
        }
        if (duracao - cursor >= VAO_MINIMO_S) buracos.push([cursor, duracao]);
        return buracos;
    }

    function cobertura(cortes) {
        const faixas = (cortes || [])
            .map((c) => [Number(c.start) || 0, Number(c.end) || 0])
            .filter(([de, ate]) => ate > de)
            .sort((a, b) => a[0] - b[0]);
        let total = 0;
        let cursor = -1;
        for (const [de, ate] of faixas) {
            const inicio = Math.max(de, cursor);
            if (ate > inicio) total += ate - inicio;
            cursor = Math.max(cursor, ate);
        }
        return total;
    }

    function escapar(texto) {
        const caixa = document.createElement("div");
        caixa.textContent = String(texto ?? "");
        return caixa.innerHTML;
    }

    /* ── a dica que segue o mouse ───────────────────────────────────────── */

    let dica = null;
    function garantirDica() {
        if (dica && dica.isConnected) return dica;
        dica = document.createElement("div");
        dica.className = "mapa-dica";
        dica.setAttribute("role", "tooltip");
        document.body.appendChild(dica);
        return dica;
    }

    function mostrarDica(evento, titulo, corpo) {
        const alvo = garantirDica();
        alvo.innerHTML = `<b>${escapar(titulo)}</b><span>${escapar(corpo)}</span>`;
        alvo.classList.add("is-active");
        const caixa = alvo.getBoundingClientRect();
        const x = Math.min(Math.max(8, evento.clientX - caixa.width / 2), window.innerWidth - caixa.width - 8);
        const y = evento.clientY - caixa.height - 12;
        alvo.style.left = `${x}px`;
        alvo.style.top = `${y < 8 ? evento.clientY + 16 : y}px`;
    }

    function esconderDica() {
        if (dica) dica.classList.remove("is-active");
    }

    /* ── o desenho ──────────────────────────────────────────────────────── */

    function bloco(de, ate, duracao, extras) {
        const elemento = document.createElement("button");
        elemento.type = "button";
        elemento.className = "mapa-bloco";
        elemento.style.setProperty("--de", (de / duracao).toFixed(5));
        elemento.style.setProperty("--ate", (ate / duracao).toFixed(5));
        Object.assign(elemento.dataset, extras || {});
        return elemento;
    }

    function irPara(segundos) {
        const video = document.querySelector("#playerDock video, #videoPreview video, video");
        if (!video) return false;
        try {
            video.currentTime = Math.max(0, Number(segundos) || 0);
            video.scrollIntoView({ block: "nearest", behavior: "smooth" });
            return true;
        } catch (erro) {
            return false;
        }
    }

    window.desenharMapaDaFonte = function desenharMapaDaFonte() {
        const alvo = document.getElementById("mapaFonte");
        if (!alvo) return;

        const cortes = (window.state?.clips || []).filter(
            (c) => Number.isFinite(Number(c.start)) && Number(c.end) > Number(c.start)
        );
        const duracao = duracaoDaFonte(cortes);

        // Sem cortes ou sem escala não há mapa. Uma régua vazia não informa
        // nada e ocupa 120 px — melhor não existir.
        if (!cortes.length || !(duracao > 0)) {
            alvo.hidden = true;
            alvo.innerHTML = "";
            return;
        }
        alvo.hidden = false;

        const perdidos = descartados();
        const buracos = vaos(cortes, duracao);
        const coberto = cobertura(cortes);
        const soltos = perdidos.filter((d) => !d.dentro_do_vencedor).length;

        alvo.innerHTML = "";

        // ── cabeçalho: a leitura em uma frase ───────────────────────────
        const topo = document.createElement("figcaption");
        topo.className = "mapa-topo";
        const resumo = [
            `<b>${cortes.length}</b> corte${cortes.length === 1 ? "" : "s"} cobrindo `
            + `<b>${duracaoPorExtenso(coberto)}</b> dos ${duracaoPorExtenso(duracao)} da fonte`,
        ];
        if (buracos.length) {
            resumo.push(`<b>${buracos.length}</b> vão${buracos.length === 1 ? "" : "s"} acima de ${VAO_MINIMO_S}s sem corte nenhum`);
        }
        if (soltos) {
            resumo.push(`<b>${soltos}</b> candidato${soltos === 1 ? "" : "s"} descartado${soltos === 1 ? "" : "s"} por encostar noutro`);
        }
        topo.innerHTML = `<h4>Onde cada corte nasceu</h4>`
            + `<p class="mapa-resumo">${resumo.join(" · ")}</p>`;
        alvo.appendChild(topo);

        // ── pista dos entregues ─────────────────────────────────────────
        const pista = document.createElement("div");
        pista.className = "mapa-pista";
        pista.dataset.pista = "entregues";
        pista.innerHTML = `<span class="mapa-rotulo">entregues</span>`;
        const trilho = document.createElement("div");
        trilho.className = "mapa-trilho";

        // Os vãos primeiro, para os blocos ficarem por cima deles.
        for (const [de, ate] of buracos) {
            const vao = document.createElement("div");
            vao.className = "mapa-vao";
            vao.style.setProperty("--de", (de / duracao).toFixed(5));
            vao.style.setProperty("--ate", (ate / duracao).toFixed(5));
            // Só rotula o vão que tem largura para a palavra caber.
            if ((ate - de) / duracao > 0.06) vao.textContent = duracaoPorExtenso(ate - de);
            trilho.appendChild(vao);
        }

        cortes.forEach((corte) => {
            const indice = window.state.clips.indexOf(corte);
            const de = Number(corte.start);
            const ate = Number(corte.end);
            const numero = corte.rank || indice + 1;
            const peca = bloco(de, ate, duracao, { corte: String(indice) });
            peca.textContent = (ate - de) / duracao > 0.025 ? numero : "";
            const abertura = String(corte.text || "").replace(/\s+/g, " ").trim().slice(0, 150);
            peca.setAttribute(
                "aria-label",
                `Corte ${numero}, de ${relogio(de)} a ${relogio(ate)}, ${duracaoPorExtenso(ate - de)}`
            );
            peca.addEventListener("mousemove", (evento) =>
                mostrarDica(
                    evento,
                    `Corte ${numero} · ${relogio(de)}–${relogio(ate)} · ${duracaoPorExtenso(ate - de)}`,
                    abertura || "sem transcrição carregada"
                )
            );
            peca.addEventListener("mouseleave", esconderDica);
            peca.addEventListener("click", () => {
                esconderDica();
                trilho.querySelectorAll(".mapa-bloco.is-active").forEach((n) => n.classList.remove("is-active"));
                peca.classList.add("is-active");
                irPara(de);
                window.selecionarCorte?.(indice);
            });
            trilho.appendChild(peca);
        });
        pista.appendChild(trilho);
        alvo.appendChild(pista);

        // ── pista dos descartados ───────────────────────────────────────
        if (perdidos.length) {
            const pistaB = document.createElement("div");
            pistaB.className = "mapa-pista";
            pistaB.dataset.pista = "descartados";
            pistaB.innerHTML = `<span class="mapa-rotulo">descartados</span>`;
            const trilhoB = document.createElement("div");
            trilhoB.className = "mapa-trilho";
            perdidos.forEach((item) => {
                const de = Number(item.inicio) || 0;
                const ate = Number(item.fim) || 0;
                if (!(ate > de)) return;
                const dentro = Boolean(item.dentro_do_vencedor);
                const peca = bloco(de, ate, duracao, { dentro: dentro ? "sim" : "nao" });
                peca.setAttribute(
                    "aria-label",
                    dentro
                        ? `Descartado por estar inteiro dentro de um corte entregue, ${relogio(de)} a ${relogio(ate)}`
                        : `Descartado por encostar noutro corte, ${relogio(de)} a ${relogio(ate)}`
                );
                peca.addEventListener("mousemove", (evento) =>
                    mostrarDica(
                        evento,
                        `${relogio(de)}–${relogio(ate)} · ${duracaoPorExtenso(ate - de)}`,
                        dentro
                            ? "Estava inteiro dentro de um corte que você recebeu — esse conteúdo você já tem."
                            : `Encostava no corte de ${relogio(item.vencedor_inicio)}–${relogio(item.vencedor_fim)}. `
                              + (String(item.trecho || "").trim() || "sem trecho registrado")
                    )
                );
                peca.addEventListener("mouseleave", esconderDica);
                peca.addEventListener("click", () => { esconderDica(); irPara(de); });
                trilhoB.appendChild(peca);
            });
            pistaB.appendChild(trilhoB);
            alvo.appendChild(pistaB);
        }

        // ── a régua ─────────────────────────────────────────────────────
        const regua = document.createElement("div");
        regua.className = "mapa-regua";
        const marcas = 6;
        for (let i = 0; i <= marcas; i += 1) {
            const marca = document.createElement("span");
            marca.className = "mapa-marca";
            marca.style.setProperty("--em", (i / marcas).toFixed(4));
            marca.textContent = relogio((duracao * i) / marcas);
            regua.appendChild(marca);
        }
        alvo.appendChild(regua);
    };
})();
