"""A bancada dentro do programa de verdade.

A decisão do conceito era "sobrevive o motor e as três peças de interface que
já funcionavam; o resto da interface morre". Juntar por Blueprint, e não por
uma segunda porta, é o que faz "o resto morre" não significar "o resto para de
funcionar": transcrição, Gemini, CHUB, blocos, corte e render continuam onde
sempre estiveram, e a bancada fala com eles pelas mesmas rotas que a interface
antiga sempre usou.

    /     a interface antiga, intacta
    /2    a bancada

Os testes daqui são o contrato dessa junção, mais as três telas que fecham o
programa: ajustes, registro e painel.
"""

from pathlib import Path

import pytest

import app as programa

RAIZ = Path(__file__).resolve().parents[1]
CSS = RAIZ / "furia2" / "static" / "css" / "furia2.css"
JS = RAIZ / "furia2" / "static" / "js" / "bancada.js"
BANCADA = RAIZ / "furia2" / "templates" / "bancada.html"


@pytest.fixture()
def cliente():
    return programa.app.test_client()


# ── a junção ────────────────────────────────────────────────────────────────


def test_as_duas_interfaces_moram_no_mesmo_programa(cliente):
    """Duas portas separadas seriam dois programas, e dois programas é o
    caminho mais curto para um deles ficar para trás."""
    assert cliente.get("/").status_code == 200, "a interface antiga saiu do ar"
    assert cliente.get("/2").status_code == 200, "a bancada não subiu"


def test_a_bancada_enxerga_o_motor_inteiro(cliente):
    """O que ele nomeou quando pediu para fechar: CHUB, vínculo com o Gemini,
    sistema de blocos e o painel. Tudo respondendo do mesmo programa."""
    for rota in (
        "/api/settings",              # a chave do Gemini e o resto dos ajustes
        "/api/campaign-hub/status",   # o CHUB
        "/api/editorial/blocks",      # o sistema de blocos
        "/api/painel",                # o painel
        "/api/render-presets",
        "/api/ollama/status",
    ):
        assert cliente.get(rota).status_code == 200, f"{rota} parou de responder"


def test_a_rota_que_mo_e_a_mesma_da_interface_antiga():
    """A bancada não ganhou um caminho próprio para moer. Um segundo caminho
    seria um segundo lugar para consertar quando o corte saísse errado."""
    codigo = JS.read_text(encoding="utf-8")
    assert '"/api/process/complete"' in codigo
    origem = (RAIZ / "app.py").read_text(encoding="utf-8")
    assert origem.count('@app.route("/api/process/complete"') == 1


def test_as_rotas_da_bancada_nao_pisam_nas_do_motor():
    """Duas rotas com o mesmo endereço E o mesmo método fazem o Flask servir
    uma e engolir a outra, calado — e a que fica é a que foi registrada
    primeiro.

    A conta é por endereço MAIS método. A primeira versão deste teste contava
    só o endereço e reprovou em `/api/settings`, que existe duas vezes de
    propósito: uma para ler e outra para gravar. Contar errado transformaria
    um par legítimo num defeito imaginário.
    """
    pares = [
        (str(regra.rule), metodo)
        for regra in programa.app.url_map.iter_rules()
        for metodo in (regra.methods or set()) - {"HEAD", "OPTIONS"}
    ]
    repetidos = {par for par in pares if pares.count(par) > 1}
    assert not repetidos, f"endereço e método repetidos no programa: {sorted(repetidos)}"


def test_a_estatica_da_bancada_nao_se_mistura_com_a_antiga(cliente):
    """Dois programas servindo `style.css` do mesmo endereço é o tipo de
    confusão que só aparece na máquina dele, três dias depois."""
    assert cliente.get("/furia2/css/furia2.css").status_code == 200
    assert cliente.get("/static/css/mesa.css").status_code == 200


def test_a_bancada_sobe_sozinha_para_trabalhar_no_desenho():
    """Sem o motor, para mexer numa tela sem esperar o programa inteiro."""
    from furia2.app import criar_app

    sozinho = criar_app().test_client()
    assert sozinho.get("/2").status_code == 200
    assert sozinho.get("/api/cortes/lista").status_code == 200


# ── moer ────────────────────────────────────────────────────────────────────


def test_o_botao_moer_manda_o_caminho_que_o_motor_entende():
    """Caminho absoluto quando ele escolheu na janela do Windows; caminho de
    dentro da pasta de trabalho no resto. Quem decide o que é permitido é o
    motor, que já tinha essa regra."""
    codigo = JS.read_text(encoding="utf-8")
    assert "fonteNaBancada.caminho || fonteNaBancada.chave" in codigo


def test_moer_duas_vezes_nao_dispara_duas_rodadas():
    """Clicar duas vezes num botão que demora meia hora é o gesto mais natural
    do mundo, e disparar duas moagens do mesmo vídeo é como o computador dele
    trava."""
    codigo = JS.read_text(encoding="utf-8")
    trecho = codigo[codigo.find("async function moer()"):]
    assert 'if (moendo) {' in trecho[:200]


def test_o_carimbo_de_versao_nao_vai_para_a_faixa_de_cima():
    """O motor carimba "[Versão 6.61 · abc123] " em toda linha. Serve para o
    registro; na faixa de cima come o espaço da mensagem."""
    codigo = JS.read_text(encoding="utf-8")
    assert "limparPrefixo" in codigo
    assert "replace(/^\\[Versão[^\\]]*\\]\\s*/" in codigo


def test_o_corte_sobe_na_parede_assim_que_fica_pronto():
    """Ele não espera meia hora olhando uma barra para descobrir no fim se
    prestou: o terceiro corte já está lá para julgar enquanto o oitavo ainda
    está sendo cortado."""
    codigo = JS.read_text(encoding="utf-8")
    assert '"clip_ready"' in codigo
    assert "corteChegou" in codigo


def test_no_fim_a_parede_troca_o_ao_vivo_pela_folha():
    """A folha de decisões só existe no fim. Ficar com a versão ao vivo
    deixaria a parede sem quadro, sem motivo escrito e sem mapa."""
    codigo = JS.read_text(encoding="utf-8")
    trecho = codigo[codigo.find('if (qual === "complete_done")'):]
    assert "abrirAParede()" in trecho[:600]


# ── ajustes ─────────────────────────────────────────────────────────────────


def test_os_ajustes_mostram_se_a_maquina_esta_inteira():
    """Antes de mandar meia hora de entrevista para o moinho, ele precisa ver
    numa olhada se o Gemini tem chave e se o CHUB está de pé."""
    codigo = JS.read_text(encoding="utf-8")
    trecho = codigo[codigo.find("MONTADO.ajustes"):]
    for peca in ("gemini", "chub", "transcrição", "ollama", "versão"):
        assert f'nome: "{peca}"' in trecho, f"o estado de {peca} sumiu dos ajustes"


def test_o_gemini_sem_chave_acende_vermelho():
    """Sem chave a análise de vídeo não roda, e descobrir isso depois de meia
    hora de moagem é meia hora perdida."""
    codigo = JS.read_text(encoding="utf-8")
    assert 'ajustes.gemini_api_key_configured ? "1" : "ruim"' in codigo


def test_o_ollama_desligado_nao_acende_vermelho():
    """Ele não é obrigatório. Vermelho num item opcional ensina a ignorar
    vermelho, e aí o vermelho que importa também é ignorado."""
    codigo = JS.read_text(encoding="utf-8")
    assert 'ollama.connected ? "1" : "0"' in codigo


def test_os_ajustes_so_trazem_o_que_muda_o_corte():
    """A gaveta velha tinha quarenta e cinco campos e ele reclamou dela com
    todas as letras. Quarenta e cinco campos numa tela são quarenta e cinco
    decisões que ninguém tomou."""
    codigo = JS.read_text(encoding="utf-8")
    trecho = codigo[codigo.find("const ESCOLHAS = ["):codigo.find("function mesmoValor")]
    assert trecho.count("chave:") <= 8, "os ajustes voltaram a virar uma gaveta"
    # E o resto continua alcançável, em vez de sumir.
    assert "abrir os ajustes completos" in codigo


def test_um_ajuste_que_nao_gravou_nao_fica_aceso():
    """Deixar a opção nova acesa depois de uma gravação que falhou é a mesma
    mentira do ajuste do Furia 1 que respondia 200 e não guardava."""
    codigo = JS.read_text(encoding="utf-8")
    trecho = codigo[codigo.find("const resposta = await pedir(\"/api/settings\""):]
    assert 'botao.setAttribute("aria-pressed", "false")' in trecho[:900]
    assert 'antes?.setAttribute("aria-pressed", "true")' in trecho[:900]


def test_meio_ponto_e_o_mesmo_ajuste_escrito_como_texto():
    """"0.25" e 0,25 são o mesmo ajuste. Comparar como texto puro deixaria a
    opção certa apagada e ele clicaria de novo achando que não pegou."""
    codigo = JS.read_text(encoding="utf-8")
    assert "function mesmoValor" in codigo
    assert "Number.isFinite(na) && Number.isFinite(nb)" in codigo


# ── registro ────────────────────────────────────────────────────────────────


def test_o_registro_tem_os_tres_caminhos_para_levar_o_texto_embora():
    """Ele já precisou me mandar o registro três vezes, e as três copiou da
    janela preta do lançador porque era o único lugar de onde dava para levar
    texto embora."""
    codigo = JS.read_text(encoding="utf-8")
    for saida in ("[data-copiar]", "[data-salvar]", "[data-pasta]", "[data-diag]"):
        assert saida in codigo, f"sumiu {saida} do registro"


def test_copiar_tem_plano_b():
    """A área de transferência é negada fora de https em parte dos
    navegadores. Sem plano B, copiar falharia calado."""
    codigo = JS.read_text(encoding="utf-8")
    assert "execCommand" in codigo


def test_o_texto_copiado_carrega_versao_e_hora():
    """Registro sem hora e sem contagem não serve para diagnosticar nada."""
    codigo = JS.read_text(encoding="utf-8")
    trecho = codigo[codigo.find("function textoDoRegistro"):]
    assert "toLocaleString" in trecho[:600]
    assert "linhas" in trecho[:600]


def test_o_registro_nao_cresce_para_sempre():
    """Uma rodada de duas horas cospe milhares de linhas, e guardar todas na
    memória de uma aba aberta o dia inteiro é como o navegador engasga sem
    ninguém entender por quê."""
    codigo = JS.read_text(encoding="utf-8")
    assert "TETO_DO_REGISTRO" in codigo
    assert "REGISTRO.splice(0, REGISTRO.length - TETO_DO_REGISTRO)" in codigo


def test_o_registro_anota_tambem_o_que_ele_mesmo_faz():
    """Sem isso o registro só existe durante uma moagem, e a maior parte das
    perguntas dele acontece fora de uma moagem."""
    codigo = JS.read_text(encoding="utf-8")
    assert "fonte na bancada:" in codigo
    assert "borda guardada em" in codigo
    assert "ajuste:" in codigo


def test_a_rolagem_do_registro_nao_e_puxada_debaixo_do_dedo():
    """Puxar a rolagem de volta enquanto ele lê uma linha de erro é o jeito
    mais rápido de tornar o registro inútil."""
    codigo = JS.read_text(encoding="utf-8")
    assert "const noFim = linhas.scrollTop + linhas.clientHeight >= linhas.scrollHeight - 24;" in codigo


# ── painel ──────────────────────────────────────────────────────────────────


def test_o_painel_so_mede_coisa_de_fora(cliente):
    """A regra que não se negocia: um número que a ferramenta gera sobre o que
    a ferramenta fez não mede nada. Tudo aqui é desempenho de post publicado,
    gancho rotulado por gente e tema controlado."""
    corpo = cliente.get("/api/painel").get_json()
    assert corpo["espelho"]["disponivel"] is True
    assert corpo["espelho"]["posts_com_desempenho"] > 1000
    codigo = JS.read_text(encoding="utf-8")
    trecho = codigo[codigo.find("MONTADO.painel"):]
    assert "/api/cortes/lista" not in trecho, (
        "o painel começou a medir a própria rodada — é exatamente o que ele não pode fazer"
    )


def test_a_evidencia_fina_e_desenhada_como_evidencia_fina():
    """Um gancho com mediana 1,19 em QUATRO posts não é um gancho bom: é um
    rumor. A barra oca tem o mesmo comprimento — não mente sobre o valor — e
    não deixa confiar nele."""
    codigo = JS.read_text(encoding="utf-8")
    assert "const EVIDENCIA_FINA = 10;" in codigo
    assert "const fina = n < EVIDENCIA_FINA;" in codigo
    folha = CSS.read_text(encoding="utf-8")
    bloco = folha[folha.find('.f2-barra[data-fina="1"] {'):]
    bloco = bloco[:bloco.find("}")]
    assert "background: transparent" in bloco
    assert "inset 0 0 0 1px" in bloco


def test_todas_as_barras_de_uma_fileira_dividem_o_mesmo_eixo():
    """Escalas diferentes por linha fariam duas barras do mesmo tamanho valerem
    números diferentes — a mentira mais fácil de contar com um gráfico."""
    codigo = JS.read_text(encoding="utf-8")
    assert "const teto = Math.ceil(maiorMediana * 1.25 * 10) / 10;" in codigo


def test_o_eixo_e_medido_pelo_que_as_barras_desenham():
    """Esticar o eixo até o p90 mais alto empurrava todas as barras para o
    primeiro terço da pista: o eixo passava a servir o risquinho de contexto
    em vez de servir o dado."""
    codigo = JS.read_text(encoding="utf-8")
    assert "const maiorMediana = Math.max(...itens.map((i) => Number(i.mediana || 0)), 1.2);" in codigo


def test_tema_que_puxa_e_tema_que_afunda_ficam_no_mesmo_eixo():
    """Duas fileiras são dois eixos, e dois eixos fazem uma barra de 2,11
    parecer do tamanho de uma de 0,71."""
    codigo = JS.read_text(encoding="utf-8")
    trecho = codigo[codigo.find("const temas = ((dados.temas"):]
    assert ".concat((dados.temas || {}).piores" in trecho[:400]
    assert trecho[:600].count("fileira(temas") == 1


def test_o_painel_nao_gasta_uma_terceira_cor():
    """A polaridade — acima ou abaixo da mediana — é dita pelo LADO da linha de
    1,00 e pelo número, que são canais mais fortes que cor e funcionam para
    quem não distingue cor nenhuma."""
    folha = CSS.read_text(encoding="utf-8")
    # O único ponto colorido da tela é o LED do espelho, e ele é a MESMA peça
    # que acende nos ajustes — a máquina dizendo de onde vêm os números. Ter
    # uma segunda peça igual só para o painel seria duas coisas para manter
    # dizendo a mesma coisa.
    assert '.f2-led[data-viva="1"]' in folha
    assert '<span class="f2-led" data-led>' in JS.read_text(encoding="utf-8")

    # E a seção do painel não gasta cor nenhuma por conta própria.
    trecho = folha[folha.find("   O PAINEL"):]
    corpo = trecho[trecho.find(".f2-painel {"):]
    assert "--f2-sangue" not in corpo
    assert "--f2-fosforo" not in corpo


def test_o_painel_abre_dizendo_alguma_coisa():
    """Painel que abre mudo obriga o sujeito a caçar o número que interessa, e
    ele não vai caçar."""
    codigo = JS.read_text(encoding="utf-8")
    assert "o gancho que mais puxa é" in codigo


def test_o_painel_usa_a_mesma_legenda_da_parede_e_do_mapa():
    """Três telas com o mesmo gesto e o mesmo lugar de resposta. Inventar um
    terceiro jeito de mostrar detalhe seria pedir para ele aprender de novo."""
    codigo = JS.read_text(encoding="utf-8")
    trecho = codigo[codigo.find("MONTADO.painel"):]
    assert 'class="f2-legenda"' in trecho
    assert ".f2-painel .f2-legenda" in CSS.read_text(encoding="utf-8")


# ── a doca inteira ──────────────────────────────────────────────────────────


def test_todos_os_seis_objetos_da_doca_abrem():
    """Nenhum objeto pode continuar dizendo "ainda não montado": era um recado
    honesto enquanto as telas nasciam, e vira defeito depois que nascem."""
    codigo = JS.read_text(encoding="utf-8")
    for objeto in ("fonte", "talho", "mapa", "painel", "ajustes", "registro"):
        assert f"MONTADO.{objeto} =" in codigo, f"o objeto {objeto} não abre"


def test_o_canal_do_motor_e_o_mesmo_arquivo_da_interface_antiga():
    """Duas cópias da mesma biblioteca é uma para esquecer de atualizar. E ele
    vem do próprio programa: nada de rede."""
    pagina = BANCADA.read_text(encoding="utf-8")
    assert '<script src="/static/vendor/socket.io.min.js"></script>' in pagina
    assert (RAIZ / "static" / "vendor" / "socket.io.min.js").is_file()


def test_sem_o_motor_a_bancada_continua_de_pe():
    """Rodando o lançador solto, para trabalhar no desenho, o canal não existe
    — e uma tela que quebra sem ele seria uma tela impossível de desenhar."""
    codigo = JS.read_text(encoding="utf-8")
    assert "const CANAL = window.io ? window.io() : null;" in codigo
    assert "if (CANAL) {" in codigo
