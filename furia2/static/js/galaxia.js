/* ═══════════════════════════════════════════════════════════════════════════
   FURIA 2 — A GALÁXIA

   O editor pediu, sobre o Cipher: "eu queria a ideia de uma galáxia brilhando
   e girando no centro e que os itens nessa galáxia fossem os itens do menu".

   Eu tinha lido o Cipher errado. Peguei dele o preto e a regra da cor sob o
   mouse — que são verdadeiras e continuam valendo — e deixei de fora a coisa
   que ele estava apontando: a composição VIVA no meio da tela, que não é
   ilustração ao lado do menu, é o menu.

   Então aqui existe UM menu só, e ele tem dois estados:

       galáxia   a bancada em repouso. As seis ferramentas são estrelas numa
                 órbita que gira devagar em volta de um núcleo aceso, com pó
                 girando junto. É por onde ele começa.

       doca      assim que entra trabalho — uma fonte, uma parede de cortes —
                 as mesmas seis estrelas descem e se alinham na fileira de
                 baixo, e a órbita para. O centro passa a ser dos cortes, que
                 é a lei 2 do conceito.

   A mesma peça nos dois estados, não dois menus. E a órbita PARA quando ele
   está trabalhando: uma tela animando o dia inteiro num notebook é ventoinha
   ligada o dia inteiro, e isso é um custo que o desenho não tem direito de
   cobrar dele.
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
    "use strict";

    const menu = document.getElementById("menu");
    const tela = document.getElementById("poeira");
    if (!menu || !tela) return;

    const estrelas = [...menu.querySelectorAll(".f2-objeto")];
    const parado = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Uma volta a cada dois minutos e meio. Devagar o bastante para ser
    // respiração e não rodopio.
    const VOLTA = 150000;
    const GRAOS = 520;

    let modo = "galaxia";
    let quadro = null;
    let poeira = [];
    let largura = 0;
    let altura = 0;

    /* ── a galáxia para debaixo do mouse ────────────────────────────────────

       O primeiro teste de navegador recusou o clique com "element is not
       stable": o item do menu estava se movendo. Um menu que anda é um menu
       que se persegue, e isso é caro num programa de trabalho — bonito na
       primeira vez, insuportável na décima.

       Então a órbita PARA quando o mouse entra na galáxia e volta a andar
       quando ele sai. O giro fica sendo o estado de repouso, e no instante em
       que ele vai escolher alguma coisa a tela fica firme. É a mesma ideia do
       Cipher, onde encostar segura a composição.

       Por isso a fase é acumulada em vez de calculada do relógio: parar um
       relógio é impossível, mas parar de somar é trivial — e ao voltar ela
       continua de onde estava, sem o salto de quem recalculou. */
    let fase = 0;
    let ultimoQuadro = 0;
    let segurando = false;

    /* ── o pó ───────────────────────────────────────────────────────────────
       Cada grão tem o seu raio, o seu ângulo e a sua velocidade. Os de dentro
       giram mais rápido que os de fora, como giram os de verdade — e é isso
       que faz o conjunto parecer um corpo girando em vez de uma imagem
       rodando. */

    function semear() {
        poeira = [];
        for (let i = 0; i < GRAOS; i += 1) {
            // Raiz da sorte: sem ela os grãos se amontoam no meio, porque área
            // cresce com o quadrado do raio.
            const dentro = Math.sqrt(Math.random());
            poeira.push({
                raio: 0.08 + dentro * 0.92,
                angulo: Math.random() * Math.PI * 2,
                // Mais devagar quanto mais longe, e nunca igual: velocidade
                // igual em todo mundo desenha um disco rígido, não uma galáxia.
                giro: (0.45 + 0.55 * (1 - dentro)) * (Math.random() * 0.4 + 0.8),
                brilho: 0.12 + Math.random() * 0.5,
                grosso: Math.random() < 0.14 ? 1.7 : 1,
            });
        }
    }

    function medir() {
        const caixa = menu.getBoundingClientRect();
        largura = Math.max(1, Math.round(caixa.width));
        altura = Math.max(1, Math.round(caixa.height));
        const escala = window.devicePixelRatio || 1;
        tela.width = Math.round(largura * escala);
        tela.height = Math.round(altura * escala);
        tela.getContext("2d").setTransform(escala, 0, 0, escala, 0, 0);
    }

    /* O eixo da galáxia. A elipse é mais larga que alta porque a tela é mais
       larga que alta — uma órbita redonda numa tela 16:9 sobra dos lados e
       aperta em cima. */
    function orbita() {
        const cx = largura / 2;
        const cy = altura / 2 - 14;
        // Mais apertada do que a primeira versão: com a órbita larga demais as
        // estrelas encostavam nas bordas da tela e o conjunto deixava de ler
        // como UM corpo — virava seis ícones espalhados.
        const rx = Math.min(largura * 0.26, 340);
        const ry = Math.min(altura * 0.30, 178);
        return { cx, cy, rx, ry };
    }

    function pintarPoeira() {
        const ctx = tela.getContext("2d");
        ctx.clearRect(0, 0, largura, altura);
        const { cx, cy, rx, ry } = orbita();
        const maior = Math.max(rx, ry);

        /* O núcleo, em três camadas. Um borrão só fica cinza e parece sujeira
           na tela; o que faz brilhar é a soma de um halo largo e fraco, um
           miolo apertado e forte, e um ponto pequeno quase branco. */
        for (const [raio, forca] of [[maior * 0.78, 0.05], [maior * 0.30, 0.14], [maior * 0.08, 0.5]]) {
            const luz = ctx.createRadialGradient(cx, cy, 0, cx, cy, raio);
            luz.addColorStop(0, `rgba(242, 239, 230, ${forca})`);
            luz.addColorStop(1, "rgba(242, 239, 230, 0)");
            ctx.fillStyle = luz;
            ctx.fillRect(cx - raio, cy - raio, raio * 2, raio * 2);
        }

        for (const grao of poeira) {
            const a = grao.angulo + fase * grao.giro;
            const x = cx + Math.cos(a) * rx * grao.raio * 1.3;
            const y = cy + Math.sin(a) * ry * grao.raio * 1.3;
            // Mais perto do núcleo, mais aceso. Grão de brilho igual em todo
            // raio desenha uma peneira; a galáxia tem miolo.
            const perto = 1 - grao.raio;
            ctx.fillStyle = `rgba(242, 239, 230, ${grao.brilho * (0.25 + perto * 0.95)})`;
            ctx.fillRect(x, y, grao.grosso, grao.grosso);
        }
    }

    /* ── as estrelas ────────────────────────────────────────────────────── */

    function porNaOrbita() {
        const { cx, cy, rx, ry } = orbita();
        const volta = fase;
        estrelas.forEach((estrela, i) => {
            // Espalhadas por igual na órbita, e começando no alto: a primeira
            // ferramenta da fila é a fonte, e ela merece o lugar de cima.
            const a = volta + (i / estrelas.length) * Math.PI * 2 - Math.PI / 2;
            const x = cx + Math.cos(a) * rx;
            const y = cy + Math.sin(a) * ry;
            estrela.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px) translate(-50%, -50%)`;
            // Quem está do lado de baixo da elipse está "na frente": um pouco
            // maior e mais claro. É o único truque de profundidade aqui, e é o
            // que impede a órbita de parecer um relógio chato.
            const frente = (Math.sin(a) + 1) / 2;
            // Piso alto de propósito: uma estrela apagada demais do outro lado
            // da órbita é um item de menu que ele não lê.
            estrela.style.opacity = String(0.72 + frente * 0.28);
        });
    }

    function porNaDoca() {
        const largoDaEstrela = 88;
        const alto = 68;
        const folgaDeBaixo = 12;
        const total = estrelas.length * largoDaEstrela;
        const esquerda = (largura - total) / 2;
        const base = altura - folgaDeBaixo - alto / 2;
        estrelas.forEach((estrela, i) => {
            const x = esquerda + i * largoDaEstrela + largoDaEstrela / 2;
            estrela.style.transform = `translate(${Math.round(x)}px, ${Math.round(base)}px) translate(-50%, -50%)`;
            estrela.style.opacity = "1";
        });
        // A moldura da doca é desenhada pelo CSS, mas quem sabe onde a fileira
        // parou é aqui. Passar as medidas evita duas contas do mesmo número em
        // dois arquivos, que é como as duas acabam discordando.
        menu.style.setProperty("--doca-x", `${Math.round(esquerda)}px`);
        menu.style.setProperty("--doca-w", `${Math.round(total)}px`);
        menu.style.setProperty("--doca-b", `${folgaDeBaixo}px`);
        menu.style.setProperty("--doca-h", `${alto}px`);
    }

    function girar(agora) {
        const passou = ultimoQuadro ? Math.min(100, agora - ultimoQuadro) : 0;
        ultimoQuadro = agora;
        if (!segurando) fase += (passou / VOLTA) * Math.PI * 2;
        pintarPoeira();
        porNaOrbita();
        quadro = window.requestAnimationFrame(girar);
    }

    function parar() {
        if (quadro !== null) window.cancelAnimationFrame(quadro);
        quadro = null;
    }

    /* ── a troca de estado ──────────────────────────────────────────────── */

    function vestir(novo) {
        if (novo === modo) return;
        modo = novo;
        menu.dataset.modo = modo;
        parar();
        if (modo === "galaxia") {
            ultimoQuadro = 0;
            if (parado) { pintarPoeira(); porNaOrbita(); }
            else quadro = window.requestAnimationFrame(girar);
        } else {
            // A doca é parada de propósito: enquanto ele trabalha, a tela não
            // gasta um quadro por segundo com enfeite.
            tela.getContext("2d").clearRect(0, 0, largura, altura);
            porNaDoca();
        }
    }

    window.furiaMenu = vestir;

    function refazer() {
        medir();
        if (modo === "galaxia") {
            if (parado) { pintarPoeira(); porNaOrbita(); }
        } else {
            porNaDoca();
        }
    }

    /* CHEGAR PERTO segura a galáxia. Encostar não bastava.

       A primeira tentativa escutava o mouse na camada do menu, e a camada não
       recebe mouse — só as estrelas recebem. Resultado: a órbita só parava
       depois que o mouse JÁ estava em cima do item, que é tarde: o caminho até
       lá é justamente o pedaço em que o alvo não pode andar.

       Agora a conta é de distância. O mouse entrou no campo da órbita — ela
       mais um terço de folga —, a galáxia para. Saiu, volta a girar. Ele
       nunca persegue nada: no instante em que a mão vai naquela direção, a
       tela já está firme.

       E, fora do campo, ela continua girando: o giro é o repouso da bancada,
       não um efeito que morre no primeiro movimento do mouse. */
    const FOLGA = 1.34;
    window.addEventListener("pointermove", (evento) => {
        if (modo !== "galaxia") return;
        const caixa = menu.getBoundingClientRect();
        const { cx, cy, rx, ry } = orbita();
        const dx = (evento.clientX - caixa.left - cx) / (rx * FOLGA);
        const dy = (evento.clientY - caixa.top - cy) / (ry * FOLGA);
        segurando = dx * dx + dy * dy <= 1;
    });
    // Sair do navegador com o mouse pela borda não dispara movimento nenhum;
    // sem isto a galáxia ficaria parada para sempre.
    window.addEventListener("blur", () => { segurando = false; });
    document.addEventListener("pointerleave", () => { segurando = false; });

    medir();
    semear();
    menu.dataset.modo = "galaxia";
    if (parado) { pintarPoeira(); porNaOrbita(); }
    else quadro = window.requestAnimationFrame(girar);

    new ResizeObserver(refazer).observe(menu);

    // A aba escondida não precisa girar nada. Sem isto o navegador continua
    // chamando o desenho de fundo e a máquina esquenta com a tela apagada.
    document.addEventListener("visibilitychange", () => {
        if (document.hidden) parar();
        else if (modo === "galaxia" && !parado && quadro === null) {
            quadro = window.requestAnimationFrame(girar);
        }
    });
})();
