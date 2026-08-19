"""O corte tem de abrir onde alguém começa a dizer alguma coisa.

Medido na entrevista do Metrópoles com Renan Santos, sobre os cinco cortes que o
editor avaliou um a um. O fim estava certo nos cinco; a abertura estava errada em
quatro:

- o primeiro começava no meio da resposta anterior, tanto que o repórter ainda
  fazia a pergunta dentro do corte — reprovado;
- o segundo abria em "Veja, eu não tô olhando pra cota", uma frase que carrega o
  próprio assunto, e o editor o chamou de perfeito;
- o terceiro, o quarto e o quinto começavam no meio da fala, o quinto "sem
  contexto suficiente".

O alinhamento por turnos só conserta a borda que já cai perto de uma pergunta.
Nenhum desses quatro caía: eles abriam dezenas de segundos dentro de uma
resposta, longe de qualquer turno, e por isso nada os movia.
"""

from modules.clip_selector import ClipSelector, PREFERRED_MAX_DURATION


# ── 0. a causa raiz: o ponto final no meio da linha de legenda ─────────────

def test_ponto_final_no_meio_da_linha_fecha_a_sentenca_ali():
    """Uma legenda de YouTube quebra onde a linha encheu, não onde a frase fecha.

    Estas quatro linhas são as que a corrida do editor gravou no diagnóstico, com
    os tempos reais. O agrupador só fechava uma sentença quando a linha *inteira*
    terminava em ponto, então o ponto de "boas práticas." era invisível e a frase
    seguinte nascia com aquele rabo pendurado. Cinco dos oito cortes daquela
    corrida abriram exatamente assim.
    """
    seletor = ClipSelector()
    linhas = _sentencas([
        (1595.84, 1598.16, "premiando por boas práticas. você cria"),
        (1598.16, 1601.24, "uma um um um sentimento de irmandade no"),
        (1601.24, 1602.52, "continente que não existe. O Brasil é"),
        (1602.52, 1603.44, "muito isolado no continente sul-americano."),
    ])
    frases = seletor._build_sentences(linhas)
    textos = [f["text"] for f in frases]
    assert any(t.startswith("O Brasil é muito isolado") for t in textos), (
        f"nenhuma sentença abre em 'O Brasil é'; saíram {textos}. O ponto no "
        f"meio da linha tem de fechar a sentença ali, senão toda frase seguinte "
        f"herda o fim da anterior"
    )


def test_a_pergunta_do_reporter_nao_herda_o_fim_da_resposta_anterior():
    """Se herdar, o detector de turnos marca a costura segundos cedo demais.

    Foi o que produziu o pior efeito colateral da corrida: o alinhamento por
    turnos abria os cortes na costura errada, de propósito.
    """
    from modules.interview_turns import detect_interviewer_turns

    seletor = ClipSelector()
    linhas = _sentencas([
        (971.9, 974.6, "a gente tem que pensar no interesse nacional. Candidato,"),
        (974.6, 977.9, "para fechar esse pacote de economia, queria só entender"),
        (977.9, 981.2, "a fala do senhor sobre as emendas parlamentares hoje."),
    ])
    frases = seletor._build_sentences(linhas)
    turnos = detect_interviewer_turns(frases)
    assert turnos, "a pergunta do repórter tem de ser reconhecida como turno"
    assert turnos[0]["start_s"] > 971.9, (
        f"o turno começa em {turnos[0]['start_s']}s, no rabo da resposta "
        f"anterior; a costura fica cedo demais e o corte abre no meio da fala"
    )


def _sentencas(linhas):
    return [{"start": ini, "end": fim, "text": txt} for ini, fim, txt in linhas]


# A resposta sobre cotas e mérito, na ordem em que ela é dada, com a pergunta do
# repórter à frente. Os tempos são os da fonte, arredondados.
_PERGUNTA = (
    "Queria abordar a questão da educação, e eu queria entender como que o senhor "
    "pretende fazer essa bolsa de mérito e como fazer com que a educação brasileira "
    "diminua essa desigualdade que hoje existe."
)
_RESPOSTA = [
    "Olha, quando eu olho para a Ásia, que é um lugar que cresceu gerando capital "
    "humano de alta qualidade, eu olho um foco colossal no mérito.",
    "A escola técnica, o ensino médio técnico, é a base da recuperação da "
    "produtividade brasileira.",
    "E não necessariamente jogar esse aluno numa universidade porque sim, aí ele "
    "sai muito mal formado.",
    "Então, voltando, o que que nós vamos fazer, as cotas entram numa lógica que "
    "não tem nada a ver com o mérito.",
    "Veja, eu não tô olhando pra cota, eu tô olhando para aquele menino ou aquela "
    "menina que tá naquela escola pública no interior do Maranhão.",
    "Nós vamos pagar a mensalidade para ele e uma bolsa para vocês, porque a "
    "criança tem que ir ajeitada com roupa.",
    "A gente tem que resolver o problema do ensino básico, e é isso que a gente "
    "quer, redirecionar os recursos do estado para essa área.",
]


def _entrevista():
    """A pergunta e a resposta, uma frase de vinte segundos cada."""
    linhas = [(0.0, 20.0, _PERGUNTA)]
    t = 20.0
    for frase in _RESPOSTA:
        linhas.append((t, t + 20.0, frase))
        t += 20.0
    return _sentencas(linhas)


def _corte(inicio, fim):
    return {"start": inicio, "end": fim, "viral_score": 70, "text": ""}


# ── 1. abrir no meio da frase ──────────────────────────────────────────────

def test_corte_que_abre_no_meio_da_frase_recua_ate_o_comeco_dela():
    seletor = ClipSelector(target_duration=45, max_clips=20, min_duration=8)
    sentencas = _entrevista()

    # começa oito segundos dentro da frase que abre em 100 s
    clipes = seletor._open_where_the_thought_begins([_corte(108.0, 160.0)], sentencas)
    assert abs(float(clipes[0]["start"]) - 100.0) < 0.01, (
        f"abriu em {clipes[0]['start']}s, no meio da frase; o espectador entra "
        f"numa oração já começada"
    )


def test_a_frase_recuperada_entra_no_texto_do_corte():
    seletor = ClipSelector(target_duration=45, max_clips=20, min_duration=8)
    clipes = seletor._open_where_the_thought_begins([_corte(108.0, 160.0)], _entrevista())
    assert "Veja, eu não tô olhando" in clipes[0]["text"], (
        "a borda andou mas o texto continuou o antigo; o corte e a sua "
        "transcrição têm de dizer a mesma coisa"
    )


# ── 2. o corte que o editor aprovou não se mexe ────────────────────────────

def test_abertura_que_carrega_o_proprio_assunto_fica_onde_esta():
    """"Veja, eu não tô olhando pra cota" abre um raciocínio e é um começo."""
    seletor = ClipSelector(target_duration=45, max_clips=20, min_duration=8)
    clipes = seletor._open_where_the_thought_begins([_corte(100.0, 160.0)], _entrevista())
    assert abs(float(clipes[0]["start"]) - 100.0) < 0.01, (
        "o corte que o editor chamou de perfeito foi movido; uma frase que "
        "apresenta o próprio assunto é uma abertura legítima"
    )


# ── 3. quem abre continuando recua até quem começa ─────────────────────────

def test_abertura_em_conjuncao_recua_ate_a_frase_que_comeca_o_raciocinio():
    """"E não necessariamente..." continua a frase anterior, não abre nada."""
    seletor = ClipSelector(target_duration=45, max_clips=20, min_duration=8)
    clipes = seletor._open_where_the_thought_begins([_corte(60.0, 140.0)], _entrevista())
    assert abs(float(clipes[0]["start"]) - 40.0) < 0.01, (
        f"abriu em {clipes[0]['start']}s, num 'E' que se apoia na frase anterior; "
        f"devia recuar até a frase que sustenta o argumento sozinha"
    )


# ── 4. o recuo para na pergunta, nunca dentro dela ─────────────────────────

def test_o_recuo_abre_na_pergunta_inteira_nunca_no_meio_dela():
    """Chegar à pergunta é chegar em chão firme, e a borda para lá.

    Abrir na pergunta foi a forma do corte que o editor aprovou — "pega a
    resposta do Renan e a apresentação dele completa". O que ele reprovou foi
    outra coisa: abrir no meio de uma resposta e ter a pergunta pendurada no meio
    do corte. Então o recuo pode alcançar a pergunta, e tem de parar no começo
    dela, nunca dentro.
    """
    seletor = ClipSelector(target_duration=45, max_clips=20, min_duration=8)
    # abre num "E" logo no início da resposta: recuar leva à pergunta
    linhas = [(0.0, 20.0, _PERGUNTA),
              (20.0, 40.0, "E é exatamente por isso que a gente vai fazer diferente.")]
    linhas += [(40.0 + i * 20.0, 60.0 + i * 20.0, frase) for i, frase in enumerate(_RESPOSTA[1:])]
    clipes = seletor._open_where_the_thought_begins([_corte(20.0, 90.0)], _sentencas(linhas))
    inicio = float(clipes[0]["start"])
    assert abs(inicio - 0.0) < 0.01, (
        f"abriu em {inicio}s, num 'E' pendurado; havia a pergunta inteira a "
        f"vinte segundos e ela cabia no corte"
    )
    assert clipes[0]["text"].startswith("Queria abordar"), (
        "a borda parou no meio da pergunta em vez do começo dela"
    )


# ── 5. quando recuar não cabe, o corte avança em vez de abrir quebrado ─────

def test_sem_espaco_para_recuar_a_abertura_avanca_para_a_proxima_frase():
    """O teto de duração não é desculpa para abrir no meio de uma oração."""
    seletor = ClipSelector(target_duration=45, max_clips=20, min_duration=8)
    sentencas = _entrevista()
    # o corte já vai até o fim do teto: recuar 8 s estouraria o limite
    fim = 108.0 + PREFERRED_MAX_DURATION
    sentencas.append({"start": 160.0, "end": fim, "text": "Segue a resposta até o fim."})
    clipes = seletor._open_where_the_thought_begins([_corte(108.0, fim)], sentencas)
    inicio = float(clipes[0]["start"])
    assert inicio >= 108.0, "recuou apesar de o teto não permitir"
    assert abs(inicio - 120.0) < 0.01, (
        f"abriu em {inicio}s, ainda no meio da frase; sem espaço para recuar a "
        f"borda tem de avançar até a próxima frase inteira"
    )
