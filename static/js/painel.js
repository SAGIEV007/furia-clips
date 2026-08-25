/* ═══════════════════════════════════════════════════════════════════════════
   O PAINEL — o que o Furia sabe, desenhado.

   O editor tem 29.596 posts medidos guardados num arquivo e nunca viu nenhum
   deles. Saber que `news-peg` rende 1,40 contra 0,98 da `tese-provocativa` muda
   o que ele grava e o que ele corta — e isso estava escrito só num JSON.

   Três decisões que o desenho segue:

   A conta é sempre contra a mediana da própria conta. 1,00 é o desempenho
   típico daquela conta naquela plataforma, então o que importa é a distância
   até 1,00 — não o valor bruto, que não significaria nada sozinho. Por isso as
   barras saem de uma linha central: é uma escala divergente, e o meio é cinza
   de propósito, porque o meio quer dizer "nada demais".

   O tamanho da amostra viaja com o número, sempre. `contraste-regional` marca
   1,19 com quatro exemplos e `tese-provocativa` marca 0,98 com quatrocentos e
   oitenta e dois; mostrar as duas barras sem dizer isso seria mentir com a
   verdade.

   E nada aqui é medição do próprio Furia. São posts que foram ao ar e blocos
   que uma pessoa revisou. Número que a ferramenta produz sobre o que a
   ferramenta fez não mede coisa nenhuma.
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
    "use strict";

    const escapar = (t) => String(t ?? "").replace(/[&<>"']/g, (c) =>
        ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

    const numero = (valor) => Number(valor || 0).toLocaleString("pt-BR");
    const razao = (valor) => Number(valor || 0).toFixed(2).replace(".", ",");

    // "uf-pa" virava "Pa". Uma sigla de estado cortada pela metade não é um
    // rótulo — é um enigma no meio de um gráfico.
    const ESTADOS = {
        ac: "Acre", al: "Alagoas", am: "Amazonas", ap: "Amapá", ba: "Bahia",
        ce: "Ceará", df: "Distrito Federal", es: "Espírito Santo", go: "Goiás",
        ma: "Maranhão", mg: "Minas Gerais", ms: "Mato Grosso do Sul",
        mt: "Mato Grosso", pa: "Pará", pb: "Paraíba", pe: "Pernambuco",
        pi: "Piauí", pr: "Paraná", rj: "Rio de Janeiro",
        rn: "Rio Grande do Norte", ro: "Rondônia", rr: "Roraima",
        rs: "Rio Grande do Sul", sc: "Santa Catarina", se: "Sergipe",
        sp: "São Paulo", to: "Tocantins",
    };
    const ACENTOS = {
        saude: "Saúde", "saude-e-educacao": "Saúde e educação",
        educacao: "Educação", corrupcao: "Corrupção",
        "corrupcao-e-escandalos": "Corrupção e escândalos",
        "gasto-publico": "Gasto público", "contas-publicas": "Contas públicas",
        "seguranca-publica": "Segurança pública", seguranca: "Segurança",
        "crime-organizado": "Crime organizado", "crime-e-faccoes": "Crime e facções",
        "faccoes-criminosas": "Facções criminosas", "eleicao-candidatura": "Eleição e candidatura",
        "campanha-e-eleicoes": "Campanha e eleições", "debate-cultural": "Debate cultural",
        "guerra-cultural": "Guerra cultural", "jogo-politico": "Jogo político",
        "justica-e-instituicoes": "Justiça e instituições", "decisao-judicial": "Decisão judicial",
        "escandalo-investigacao": "Escândalo e investigação",
        "comportamento-e-familia": "Comportamento e família",
        "municipios-e-federalismo": "Municípios e federalismo",
        "economia-e-trabalho": "Economia e trabalho", "emprego-renda": "Emprego e renda",
        "propriedade-invasoes": "Propriedade e invasões",
        "saneamento-moradia": "Saneamento e moradia", "cidades-e-moradia": "Cidades e moradia",
        "mundo-e-historia": "Mundo e história", "valores-liberdade": "Valores e liberdade",
        "liberdade-expressao": "Liberdade de expressão", "censura-digital": "Censura digital",
        "celebridades-influencers": "Celebridades e influenciadores",
        "midia-imprensa": "Mídia e imprensa", "congresso-centrao": "Congresso e centrão",
        "bolsonaro-direita": "Bolsonaro e a direita", "lula-pt": "Lula e o PT",
        "stf-moraes": "STF e Moraes", "prefeitura-gestao-local": "Prefeituras",
        "agro-e-ambiente": "Agro e ambiente", "meio-ambiente": "Meio ambiente",
        "energia-tecnologia-e-infra": "Energia, tecnologia e infra",
        "pauta-trans": "Pauta trans", missao: "Missão", periferia: "Periferia",
        juventude: "Juventude", nordeste: "Nordeste", exterior: "Exterior",
    };
    const nomeBonito = (slug) => {
        const chave = String(slug || "");
        if (ACENTOS[chave]) return ACENTOS[chave];
        const estado = chave.match(/^uf-([a-z]{2})$/);
        if (estado) return ESTADOS[estado[1]] || estado[1].toUpperCase();
        return chave.replace(/-e-/g, " e ").replace(/-/g, " ").replace(/^\w/, (c) => c.toUpperCase());
    };

    let dados = null;

    /* Uma faixa divergente: a barra sai do meio, para a direita quando rende
       acima do típico e para a esquerda quando rende abaixo. */
    function faixa(rotulo, valor, amostra, maximo) {
        const desvio = valor - 1;
        const largura = Math.min(48, (Math.abs(desvio) / maximo) * 48);
        const acima = desvio >= 0;
        const magro = amostra < 10;
        return `
        <div class="faixa${magro ? " amostra-magra" : ""}" tabindex="0"
             aria-label="${escapar(rotulo)}: ${razao(valor)} vezes a mediana da conta, ${amostra} exemplos">
            <span class="faixa-nome">${escapar(rotulo)}</span>
            <span class="faixa-trilho">
                <span class="faixa-meio" aria-hidden="true"></span>
                <span class="faixa-barra ${acima ? "acima" : "abaixo"}"
                      style="${acima ? "left:50%" : `right:50%`};width:${largura}%"></span>
            </span>
            <span class="faixa-valor">${razao(valor)}</span>
            <span class="faixa-n" title="${amostra} exemplos sustentam este número">${amostra}</span>
        </div>`;
    }

    function bloco(titulo, explicacao, linhas) {
        return `
        <section class="cartao">
            <header class="cartao-topo">
                <h3>${escapar(titulo)}</h3>
                <p>${explicacao}</p>
            </header>
            <div class="faixas">
                <div class="faixas-regua" aria-hidden="true">
                    <span class="regua-eixos">
                        <span>rende menos</span><span class="regua-meio">1,00</span><span>rende mais</span>
                    </span>
                </div>
                ${linhas}
            </div>
        </section>`;
    }

    function pintar() {
        const alvo = document.getElementById("painelCorpo");
        if (!alvo || !dados) return;
        const e = dados.espelho || {};

        if (!e.disponivel) {
            alvo.innerHTML = `
                <div class="painel-vazio">
                    <span class="material-icons-round">insights</span>
                    <strong>Sem o espelho do CHUB, não há o que mostrar aqui.</strong>
                    <p>O painel desenha desempenho de material publicado. Rode <code>chub.bat --espelho</code> e volte.</p>
                </div>`;
            return;
        }

        const ganchos = dados.ganchos || [];
        const melhores = dados.temas?.melhores || [];
        const piores = dados.temas?.piores || [];
        const maiorDesvio = Math.max(0.25, ...[...ganchos, ...melhores, ...piores]
            .map((i) => Math.abs(Number(i.mediana) - 1)));

        const topo = ganchos[0];
        const papeis = dados.papeis || {};

        alvo.innerHTML = `
        <div class="marcos">
            <div class="marco destaque">
                <span class="marco-rotulo">O gancho que mais rende</span>
                <strong class="marco-valor">${topo ? escapar(topo.familia) : "—"}</strong>
                <span class="marco-nota">${topo ? `${razao(topo.mediana)}× a mediana da conta · ${topo.n} exemplos` : ""}</span>
            </div>
            <div class="marco">
                <span class="marco-rotulo">Posts medidos</span>
                <strong class="marco-valor">${numero(e.posts_com_desempenho)}</strong>
                <span class="marco-nota">com desempenho real</span>
            </div>
            <div class="marco">
                <span class="marco-rotulo">Cortes publicados</span>
                <strong class="marco-valor">${numero(e.cortes_publicados)}</strong>
                <span class="marco-nota">${numero(e.cortes_com_transcricao)} com transcrição</span>
            </div>
            <div class="marco">
                <span class="marco-rotulo">Blocos revisados</span>
                <strong class="marco-valor">${numero(e.blocos_do_acervo)}</strong>
                <span class="marco-nota">marcados por gente</span>
            </div>
        </div>

        ${bloco("Ganchos", `Como cada forma de abrir o corte se saiu no <b>${escapar(dados.conta)}</b>, no ${escapar(dados.plataforma)}. O número da direita é quantos exemplos sustentam a linha.`,
            ganchos.map((g) => faixa(g.familia, g.mediana, g.n, maiorDesvio)).join(""))}

        <div class="dupla">
            ${bloco("Temas que rendem", "Assuntos acima do desempenho típico da conta.",
                melhores.map((t) => faixa(nomeBonito(t.slug), t.mediana, t.n, maiorDesvio)).join(""))}
            ${bloco("Temas que não rendem", "Mesmo material, mesmo esforço, menos alcance.",
                piores.map((t) => faixa(nomeBonito(t.slug), t.mediana, t.n, maiorDesvio)).join(""))}
        </div>

        <section class="cartao">
            <header class="cartao-topo">
                <h3>Quem é quem</h3>
                <p>Mapa de nomes do CHUB. Um trecho em que um adversário se enrola vale tanto quanto uma boa fala do Renan.</p>
            </header>
            <div class="mapa">
                <div class="mapa-contagem">
                    <span><b>${papeis.adversarios || 0}</b> adversários</span>
                    <span><b>${papeis.aliados || 0}</b> aliados</span>
                    <span><b>${(papeis.indefinidos || []).length}</b> sem lado definido</span>
                </div>
                <ul class="mapa-lista">
                    ${(papeis.principais || []).map((p) => `
                        <li>
                            <span class="mapa-nome">${escapar(p.nome)}</span>
                            <span class="mapa-barra" aria-hidden="true">
                                <i style="width:${Math.round(p.confianca * 100)}%"></i>
                            </span>
                            <span class="mapa-n">${p.contra} contra · ${p.a_favor} a favor</span>
                        </li>`).join("")}
                </ul>
                ${(papeis.indefinidos || []).length ? `
                <p class="mapa-duvida">
                    <span class="material-icons-round">help_outline</span>
                    <span><b>Sem lado definido:</b> ${(papeis.indefinidos || []).map(escapar).join(", ")}.
                    Aparecem quase tanto de um lado quanto do outro, então o Furia não os trata como adversário.</span>
                </p>` : ""}
            </div>
        </section>

        <p class="painel-rodape">
            Espelho gerado em ${escapar(String(e.gerado_em).slice(0, 10).split("-").reverse().join("/"))} ·
            ${escapar(e.origem)} · tudo aqui é desempenho de material que foi ao ar, não medição do próprio Furia.
        </p>`;
    }

    async function carregar(conta) {
        const alvo = document.getElementById("painelCorpo");
        if (alvo) alvo.setAttribute("aria-busy", "true");
        try {
            const resposta = await fetch(`/api/painel${conta ? `?conta=${encodeURIComponent(conta)}` : ""}`);
            dados = await resposta.json();
            pintar();
            const seletor = document.getElementById("painelConta");
            if (seletor && !seletor.dataset.pronto) {
                seletor.innerHTML = (dados.contas || []).map((c) =>
                    `<option value="${escapar(c)}"${c === dados.conta ? " selected" : ""}>${escapar(c)}</option>`).join("");
                seletor.dataset.pronto = "1";
                seletor.addEventListener("change", () => carregar(seletor.value));
            }
        } catch (erro) {
            if (alvo) alvo.innerHTML = `<div class="painel-vazio"><span class="material-icons-round">error_outline</span>
                <strong>Não deu para ler o painel.</strong><p>${escapar(erro.message)}</p></div>`;
        } finally {
            if (alvo) alvo.removeAttribute("aria-busy");
        }
    }

    window.carregarPainel = carregar;
    document.addEventListener("DOMContentLoaded", () => carregar());
})();
