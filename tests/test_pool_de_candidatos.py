"""Três defeitos que esvaziavam a lista de candidatos numa fonte real.

Medidos na sabatina do SBT News com Renan Santos (31 minutos, 602 segmentos de
legenda, 382 sentenças). O caminho local produzia 5 cortes finais. A v3.6, na
mesma fonte, produzia 33. A regressão não estava no ranqueamento — estava em
três passes que descartavam material bom por motivos que pareciam certos quando
foram escritos:

1. o contexto escrito pelo editor virava lista de nomes obrigatórios, e todo
   candidato que não citasse "Sabatina", "SBT", "News", "Renan" ou "Santos" era
   apagado — 12 de 19. Numa sabatina o entrevistado não diz o próprio nome nem
   o do canal;
2. a expansão para achar um desfecho completo só respeitava o teto técnico de
   600 s, então um bloco de 176 s virava candidato de 471 s;
3. dois candidatos que se encostam eram tratados como a mesma resposta servida
   duas vezes. No caminho local os blocos particionam a fonte inteira, então
   encostar é o normal: o passe apagava 9 de 18, cada um respondendo a uma
   pergunta diferente.
"""

from modules.clip_selector import ClipSelector, PREFERRED_MAX_DURATION


def _sentencas(linhas):
    return [{"start": ini, "end": fim, "text": txt} for ini, fim, txt in linhas]


# ── 1. o nome no contexto é preferência, não portão ────────────────────────

def test_contexto_com_nome_nao_apaga_quem_nao_o_cita():
    """Quem não cita o nome continua na lista; quem cita apenas sobe."""
    seletor = ClipSelector(target_duration=45, max_clips=20, min_duration=8)

    blocos = []
    for i in range(8):
        base = i * 60.0
        # só os dois primeiros citam o nome
        fala = ("Renan Santos falou sobre isso na semana passada."
                if i < 2 else
                "O problema da segurança pública é estrutural e ninguém enfrenta.")
        blocos.append({
            "start": base, "end": base + 40.0, "duration": 40.0,
            "text": f"{fala} " * 4,
            "sentences": _sentencas([(base + j * 10.0, base + j * 10.0 + 9.0, fala) for j in range(4)]),
            "speakers": [], "speaker": "", "index": i,
        })

    contexto = seletor._prepare_context_matching("Sabatina do SBT News com Renan Santos")
    assert "renan" in contexto["names"], "o teste depende do nome ser reconhecido"

    marcados = [(b, 60.0) for b in blocos]
    clipes = seletor._build_clips_from_scored_blocks(marcados, contexto)
    assert clipes, "o construtor precisa devolver candidatos para o teste valer"

    citam = [c for c in clipes if "renan" in c["text"].lower()]
    nao_citam = [c for c in clipes if "renan" not in c["text"].lower()]
    assert citam and nao_citam, "a fixture precisa dos dois casos"

    resultado = seletor._select_with_nlp(
        [s for b in blocos for s in b["sentences"]],
        None,
        "Sabatina do SBT News com Renan Santos",
        None,
    )
    sobreviventes_sem_nome = [c for c in resultado if "renan" not in c["text"].lower()]
    assert sobreviventes_sem_nome, (
        "candidato que não cita o nome do contexto foi apagado; o nome é "
        "preferência de ranqueamento, nunca portão"
    )


# ── 2. a expansão respeita o teto preferido, não o técnico ─────────────────

def test_expansao_nao_ultrapassa_o_teto_preferido():
    """Nenhum candidato sai com cinco minutos porque procurava um desfecho."""
    seletor = ClipSelector(target_duration=45, max_clips=20, min_duration=8)

    # oito blocos contíguos de 60 s cujo texto nunca fecha um argumento, que é
    # o caso em que a expansão seguia adiante procurando o desfecho.
    blocos = []
    for i in range(8):
        base = i * 60.0
        fala = "e aí a gente continua falando sem concluir o raciocínio e"
        blocos.append({
            "start": base, "end": base + 60.0, "duration": 60.0,
            "text": f"{fala} " * 6,
            "sentences": _sentencas([(base + j * 10.0, base + j * 10.0 + 10.0, fala) for j in range(6)]),
            "speakers": [], "speaker": "", "index": i,
        })

    clipes = seletor._build_clips_from_scored_blocks([(b, 60.0) for b in blocos], None)
    assert clipes
    for clipe in clipes:
        duracao = float(clipe["end"]) - float(clipe["start"])
        assert duracao <= PREFERRED_MAX_DURATION + 0.5, (
            f"candidato de {duracao:.1f}s; um trecho de vários minutos não é "
            f"corte, é pedaço do programa"
        )


def test_corte_que_bate_no_teto_fecha_na_pausa_e_nao_no_cronometro():
    """Havendo fronteira real dentro da janela, é nela que o corte fecha.

    Numa fixture sem pausa, sem entrevistador e sem conclusão não existe
    fronteira melhor que o teto, e fechar em 180,0 seria a resposta certa. O
    defeito que o editor viu era outro: fechar no cronômetro *tendo* onde
    fechar. Aqui existe um silêncio de quatro segundos aos 140 s, e é ele que
    tem de ganhar.
    """
    # O teto vai explícito: este teste mede *onde* o corte fecha dentro da
    # janela, não qual deve ser o tamanho da janela. Esse valor é medido por
    # `scripts/medir_cortes.py` contra as fronteiras humanas do Acervo, e
    # amarrar a fixture ao padrão faria este teste quebrar toda vez que a régua
    # mover o teto — sem que o mecanismo aqui tivesse mudado.
    seletor = ClipSelector(
        target_duration=45, max_clips=20, min_duration=8, preferred_max_duration=180.0
    )
    fala = "e aí a gente continua falando sem concluir o raciocínio e"

    # Blocos de 20 s: granularidade fina o bastante para o fim do corte poder
    # cair na pausa em vez de numa fronteira de bloco.
    linhas = []
    t = 0.0
    for i in range(30):
        linhas.append((t, t + 10.0, fala))
        t += 10.0
        if abs(t - 140.0) < 0.01:   # a única pausa da fonte
            t += 4.0

    blocos = []
    for i in range(0, len(linhas), 2):
        pedaco = linhas[i:i + 2]
        blocos.append({
            "start": pedaco[0][0], "end": pedaco[-1][1],
            "duration": pedaco[-1][1] - pedaco[0][0],
            "text": f"{fala} " * len(pedaco),
            "sentences": _sentencas(pedaco),
            "speakers": [], "speaker": "", "index": len(blocos),
        })

    clipes = seletor._build_clips_from_scored_blocks([(b, 60.0) for b in blocos], None)
    assert clipes
    primeiro = min(clipes, key=lambda c: float(c["start"]))
    fim = float(primeiro["end"])
    assert abs(fim - 140.0) < 0.01, (
        f"o corte fechou em {fim:.1f}s em vez dos 140,0s da pausa; fechar no "
        f"cronômetro tendo onde fechar é o defeito dos candidatos de 180,0 s"
    )


# ── 3. encostar só é irmandade quando ninguém pergunta no meio ─────────────

# Perguntas de verdade passam de doze palavras; abaixo disso o detector as
# classifica como aparte, e um aparte não separa irmãos porque o entrevistado
# fala por cima dele.
_PERGUNTAS = [
    "Candidato, o senhor pode detalhar para o telespectador qual é exatamente a "
    "sua proposta para a reforma administrativa do Estado brasileiro?",
    "Candidato, mudando de assunto, e sobre segurança pública, o que o senhor "
    "pretende fazer já nos primeiros meses de um eventual governo seu?",
    "Candidato, o senhor falou em privatização há pouco. Como exatamente isso "
    "funcionaria no caso das empresas que dão prejuízo hoje?",
    "Candidato, para encerrar o nosso bloco, qual é a mensagem que o senhor "
    "deixa para o eleitor que ainda está indeciso neste momento?",
]


def _sabatina():
    """Quatro perguntas em quatro minutos — o mínimo que o detector reconhece."""
    linhas = []
    t = 0.0
    for pergunta in _PERGUNTAS:
        linhas.append((t, t + 8.0, pergunta))
        t += 8.0
        for _ in range(3):
            linhas.append((t, t + 17.0, "A resposta segue por um trecho inteiro sem interrupção nenhuma."))
            t += 17.0
    return _sentencas(linhas)


def test_vizinhos_com_pergunta_no_meio_sobrevivem_os_dois():
    seletor = ClipSelector()
    sentencas = _sabatina()
    # o primeiro candidato termina onde a segunda pergunta começa
    inicio_segunda = sentencas[4]["start"]
    colados = [
        {"start": 0.0, "end": inicio_segunda, "viral_score": 70, "text": "Primeira resposta."},
        {"start": inicio_segunda, "end": inicio_segunda + 60.0, "viral_score": 70, "text": "Segunda resposta."},
    ]
    mantidos = seletor._drop_touching_siblings(colados, None, sentencas)
    assert len(mantidos) == 2, (
        "o entrevistador toma a palavra entre os dois: são respostas a "
        "perguntas diferentes, não a mesma resposta servida duas vezes"
    )


def test_vizinhos_sem_pergunta_no_meio_continuam_virando_um_so():
    """A regra original continua valendo onde ela nasceu."""
    seletor = ClipSelector()
    sentencas = _sabatina()
    # os dois candidatos ficam inteiros dentro da mesma resposta
    dentro = sentencas[1]["start"]
    colados = [
        {"start": dentro, "end": dentro + 19.0, "viral_score": 70, "text": "Começo da resposta."},
        {"start": dentro + 19.0, "end": dentro + 38.0, "viral_score": 70, "text": "Continuação da mesma resposta."},
    ]
    mantidos = seletor._drop_touching_siblings(colados, None, sentencas)
    assert len(mantidos) == 1, (
        "sem troca de locutor na junta, dois candidatos colados são a mesma "
        "resposta partida em dois"
    )
