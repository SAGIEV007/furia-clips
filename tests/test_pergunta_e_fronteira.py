"""A pergunta do repórter não era fronteira de bloco, e o editor viu isso sozinho.

Sobre os cortes de João Pessoa ele escreveu, do clipe 3:

    "o final do corte deveria ser 'essa é uma questão muito importante' e ele
    fala essa parte, aí o corte passa um pouco de onde deveria ser recortado e eu
    percebi claramente que esse 'a mais' que passou, é justamente o inicio em
    excesso do segundo corte"

E do clipe 2:

    "começa um pouco antes da pergunta, deveria começar literalmente em
    ''candidato''"

São a mesma falha vista dos dois lados. Reconstruída aqui, a coletiva produz um
bloco que começa no fim da resposta 1 ("Essa é uma questão muito importante") e
segue para dentro da pergunta 2 ("Renan, o senhor pretende manter..."). A fronteira
está no lugar errado, então o corte que termina a resposta 1 passa da conta e o
corte que abre a pergunta 2 começa cedo demais — pelo mesmo trecho.

A causa é `INTERJECTION_MAX_WORDS = 12`. Um turno de até doze palavras sem marca
explícita de mudança de assunto é lido como interrupção dentro da resposta, e
interrupção não abre bloco. Só que pergunta de coletiva é curta: "Candidato,
quais os compromissos que o seu governo teria com a Paraíba?" tem onze palavras.

O que o comentário do módulo chama de interrupção — "Senhor manter então para a
extrema pobreza até fazer a transição" — é um fragmento: não fecha em "?" nem
abre com palavra interrogativa. A contagem de palavras não separa os dois casos;
a gramática separa. Uma pergunta inteira nunca é interrupção, tenha o tamanho que
tiver.
"""

import pytest

from modules.clip_selector import ClipSelector
from modules.interview_turns import detect_interviewer_turns

# A coletiva, com os tempos que ela teria numa transcrição real.
COLETIVA = [
    ("Boa tarde a todos, obrigado pela presença de vocês aqui em João Pessoa.", 8),
    ("A gente vai abrir para as perguntas dos jornalistas agora.", 6),
    ("Candidato, quais os compromissos que o seu governo teria com a Paraíba?", 7),
    ("Olha, o primeiro compromisso é com a segurança pública.", 9),
    ("Hoje o paraibano tem medo de sair de casa depois das seis da tarde.", 10),
    ("A gente vai colocar polícia na rua e vai dar condição de trabalho para ela.", 11),
    ("O segundo compromisso é gerar emprego de verdade, não emprego de programa social.", 12),
    ("Essa é uma questão muito importante para o nosso estado.", 8),
    ("Renan, o senhor pretende manter o programa social que existe hoje?", 7),
    ("Pretendo rever inteiro, porque hoje ele não funciona.", 9),
    ("O programa mantém o pobre pobre em vez de dar oportunidade para ele crescer.", 11),
    ("Eu quero que o paraibano vire classe média, e isso se faz com trabalho.", 10),
    ("Uma última pergunta sobre a relação com o Congresso.", 6),
    ("O Congresso hoje é refém do centrão, e isso precisa acabar.", 9),
    ("Não adianta trocar o presidente e manter a mesma lógica de toma lá dá cá.", 11),
    ("Obrigado a todos, encerramos por aqui.", 6),
]


def _frases():
    segmentos = []
    tempo = 5.0
    for texto, duracao in COLETIVA:
        segmentos.append({"start": round(tempo, 2), "end": round(tempo + duracao, 2), "text": texto})
        tempo += duracao + 0.6
    return ClipSelector()._build_sentences(segmentos)


# ── a classificação do turno ───────────────────────────────────────────────

def test_pergunta_inteira_nao_e_interrupcao_por_ser_curta():
    turnos = detect_interviewer_turns(_frases())
    perguntas = [t for t in turnos if "?" in t["text"]]
    assert perguntas, "as perguntas do repórter sumiram da detecção de turnos"
    for turno in perguntas:
        assert not turno["interjection"], (
            f"pergunta completa de {turno['words']} palavras tratada como "
            f"interrupção dentro da resposta: {turno['text']!r}"
        )


def test_fragmento_no_meio_da_resposta_continua_sendo_interrupcao():
    """O controle. Este é o caso que a regra das doze palavras existe para pegar.

    Não fecha em "?", não abre com palavra interrogativa: o entrevistado retoma o
    mesmo argumento logo depois, e um corte pode passar por cima.
    """
    frases = ClipSelector()._build_sentences([
        {"start": 0.0, "end": 9.0, "text": "A gente precisa de uma transição responsável no programa."},
        {"start": 9.6, "end": 13.0, "text": "Senhor manter então para a extrema pobreza até fazer a transição."},
        {"start": 13.6, "end": 22.0, "text": "Exatamente, para a extrema pobreza a gente mantém enquanto faz a transição."},
    ])
    turnos = detect_interviewer_turns(frases)
    assert turnos, "o aparte deixou de ser detectado"
    assert all(t["interjection"] for t in turnos), (
        "um fragmento no meio da resposta virou fronteira de bloco"
    )


# ── a consequência: onde o bloco abre e onde ele fecha ─────────────────────

def _blocos():
    seletor = ClipSelector(max_clips=6, min_duration=15, max_duration=180)
    return seletor._build_transcript_blocks(_frases())


def test_a_pergunta_abre_um_bloco_em_vez_de_ficar_colada_na_anterior():
    blocos = _blocos()
    aberturas = [b["text"].strip() for b in blocos]
    assert any(t.startswith("Candidato, quais os compromissos") for t in aberturas), (
        "nenhum bloco começa na pergunta; ela continua engolida no bloco de "
        f"abertura. Blocos: {[t[:45] for t in aberturas]}"
    )
    assert any(t.startswith("Renan, o senhor pretende manter") for t in aberturas), (
        f"a segunda pergunta não abre bloco. Blocos: {[t[:45] for t in aberturas]}"
    )


def test_o_fim_da_resposta_nao_vaza_para_dentro_da_pergunta_seguinte():
    """O defeito que o editor identificou, medido.

    Nenhum bloco pode conter o fecho da resposta 1 e a pergunta 2 ao mesmo tempo:
    é esse bloco que faz o corte anterior passar da conta e o seguinte começar
    cedo demais, pelo mesmo trecho.
    """
    for bloco in _blocos():
        texto = bloco["text"]
        junta_os_dois = (
            "Essa é uma questão muito importante" in texto
            and "Renan, o senhor pretende manter" in texto
        )
        assert not junta_os_dois, (
            "o fim da resposta 1 e a pergunta 2 estão no mesmo bloco "
            f"({bloco['start']:.1f}-{bloco['end']:.1f}s): {texto[:120]!r}"
        )


def test_cada_pergunta_e_sua_resposta_viram_uma_unidade_selecionavel():
    """A cobertura: a coletiva tem três perguntas, não uma."""
    blocos = _blocos()
    com_pergunta = [b for b in blocos if "?" in b["text"]]
    assert len(com_pergunta) >= 2, (
        f"só {len(com_pergunta)} bloco(s) carregam uma pergunta, de {len(blocos)} blocos"
    )


@pytest.mark.parametrize("texto,esperado", [
    ("Candidato, quais os compromissos do seu governo com a Paraíba?", True),
    ("Renan, o senhor pretende manter o programa social?", True),
    ("Deputado, por que o senhor votou assim?", True),
    # Sem pontuação, só a pergunta que abre com palavra interrogativa é
    # reconhecível; a de sim/não fica indistinguível de uma afirmação.
    ("Candidato quais os compromissos do seu governo com a Paraíba", True),
    ("Senhor manter então para a extrema pobreza até fazer a transição.", False),
    ("Candidato, obrigado pela presença.", False),
    ("O senhor pretende manter o programa", False),
])
def test_a_gramatica_decide_e_nao_o_tamanho(texto, esperado):
    from modules.interview_turns import is_a_whole_question

    assert is_a_whole_question(texto) is esperado, texto


def test_uma_coletiva_esparsa_ainda_ganha_costura_na_pergunta():
    """Duas perguntas em 154s não passam no portão de densidade — e não precisam.

    O portão exige um turno a cada cinco minutos antes de honrar qualquer
    costura. Um discurso de uma hora seguido de dez minutos de coletiva nunca
    alcança isso, e era ali que os blocos voltavam a ser fatias de cronômetro.
    """
    from modules.interview_turns import detect_interviewer_turns, looks_like_an_interview

    frases = _frases()
    turnos = detect_interviewer_turns(frases)
    assert not looks_like_an_interview(turnos, 154.0), (
        "esta fonte deixou de ser esparsa; o teste perdeu o que media"
    )
    costuras = ClipSelector()._conversation_seams(frases)
    assert costuras, "nenhuma costura numa fonte com duas perguntas inteiras"
    assert 20.2 in costuras, f"a costura não caiu no 'Candidato': {costuras}"


def test_monologo_continua_sem_costura():
    """O controle: onde não há pergunta, nada muda."""
    frases = ClipSelector()._build_sentences([
        {"start": 0.0, "end": 9.0, "text": "O Brasil tem um estado grande demais para o que entrega."},
        {"start": 9.6, "end": 19.0, "text": "A gente paga imposto de país rico e recebe serviço de país pobre."},
        {"start": 19.6, "end": 29.0, "text": "Isso não se resolve trocando quem manda, se resolve mudando o modelo."},
    ])
    assert ClipSelector()._conversation_seams(frases) == []


# ── a cobertura: dois pares Q&A viram dois cortes ──────────────────────────

def test_perguntas_vizinhas_nao_se_anulam():
    """Furia entregou 3 cortes onde o CapCut achou 5 capítulos e o site da
    Missão, 31 blocos. Uma das causas é este passe.

    A regra de vizinhança apaga um candidato que encosta no outro, porque em
    blocos de cronômetro dois candidatos colados eram mesmo a mesma resposta
    servida duas vezes. Numa coletiva, encostar é o estado normal: uma pergunta
    termina e a próxima começa. A válvula certa já existia — se o entrevistador
    toma a palavra na junta, os dois cortes vivem —, mas ela redecidia a costura
    por conta própria, com as mesmas duas travas que este arquivo corrige, e uma
    coletiva de perguntas curtas caía nas duas.
    """
    import inspect

    from modules.editorial_context import analyze_transcript_context

    segmentos = []
    tempo = 5.0
    for texto, duracao in COLETIVA:
        segmentos.append({"start": round(tempo, 2), "end": round(tempo + duracao, 2), "text": texto})
        tempo += duracao + 0.6

    seletor = ClipSelector(max_clips=6, min_duration=15, max_duration=180)
    contexto = analyze_transcript_context({"segments": segmentos})
    aceitos = inspect.signature(seletor.select_clips).parameters
    argumentos = {
        nome: valor for nome, valor in [
            ("transcription", {"segments": segmentos}), ("energy_profile", []),
            ("user_context", ""), ("settings", {}), ("emit_progress", None),
            ("editorial_context", contexto),
        ] if nome in aceitos
    }
    clips = seletor.select_clips(**argumentos)

    assert len(clips) >= 2, (
        f"a coletiva tem duas perguntas respondidas por inteiro e saiu {len(clips)} corte(s): "
        f"{[(round(c['start'], 1), round(c['end'], 1)) for c in clips]}"
    )
    aberturas = [c["text"].strip() for c in clips]
    assert any(t.startswith("Candidato, quais os compromissos") for t in aberturas), aberturas
    assert any(t.startswith("Renan, o senhor pretende manter") for t in aberturas), aberturas
