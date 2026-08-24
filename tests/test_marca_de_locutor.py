"""A transcrição dizia onde o locutor troca, e o Furia apagava na entrada.

O editor mandou a transcrição do tactiq do vídeo de João Pessoa: 1h21, 1961
falas, e **153 marcas `>>`**. Cada uma é uma troca de locutor — é assim que o
YouTube e o tactiq anotam legenda de coletiva, e é a informação mais valiosa que
um arquivo desses carrega para quem precisa saber onde a pergunta começa.

O parser tinha esta linha:

    text = re.sub(r"(?:^|\\s)(?:>>|>)\\s*", " ", text)

Ou seja: apagava as marcas como se fossem sujeira de formatação. Toda a detecção
de turno do entrevistador — que é a base de onde o corte abre — era então
reconstruída por adivinhação de vocabulário ("candidato,", "o senhor"), tendo a
resposta escrita no próprio arquivo.

Medido na coletiva desse vídeo antes da correção: das 29 perguntas detectadas
saíam 8 cortes, e **quatro dos oito abriam no meio de uma frase** — inclusive o
que o editor apontou, que abria em "Eh, quais os compromissos" em vez de
"candidato", uma linha antes.

O texto continua limpo: a marca sai do texto e vira um campo. Ela é evidência
sobre a fala, não parte dela, e uma legenda com ">>" no meio iria parar na arte.
"""

import pytest

from modules.transcript_parser import parse_transcript_text

# Verbatim do arquivo do editor, do trecho que ele mesmo apontou.
COLETIVA = """# tactiq.io free youtube transcript
# RENAN SANTOS EM JOÃO PESSOA - IRL | 19/08/26
# https://www.youtube.com/watch/KpjvWf9SsWQ

00:17:34.960 >> Agora o
00:17:35.760 >> peraló tem os outros
00:17:37.640 >> candidato. Eh, quais os compromissos o
00:17:39.760 seu governo teria com a Paraíba? Caso
00:17:42.039 mesmo? São os mesmos compromissos que eu
00:17:43.919 tenho contra os estados brasileiros nos
"""


def test_a_marca_de_troca_de_locutor_sobrevive():
    segmentos = parse_transcript_text(COLETIVA)["segments"]
    assert segmentos, "nada foi lido"
    marcados = [s for s in segmentos if s.get("speaker_change")]
    assert len(marcados) == 3, (
        f"{len(marcados)} falas marcadas de 3 que o arquivo traz; as marcas '>>' "
        f"continuam sendo apagadas na entrada"
    )


def test_a_marca_nao_fica_no_texto():
    """Ela é evidência sobre a fala, não parte dela.

    Um ">>" que sobrevivesse no texto acabaria numa legenda queimada no vídeo ou
    dentro de aspas numa headline.
    """
    for segmento in parse_transcript_text(COLETIVA)["segments"]:
        assert ">>" not in segmento["text"]
        assert not segmento["text"].startswith(">")


def test_a_fala_que_continua_nao_e_marcada():
    """O controle: só a linha que traz a marca é troca de locutor."""
    segmentos = parse_transcript_text(COLETIVA)["segments"]
    continuacao = [s for s in segmentos if s["text"].startswith("seu governo teria")]
    assert continuacao, "o teste perdeu o que media"
    assert not continuacao[0].get("speaker_change")


def test_transcricao_sem_marca_nenhuma_nao_inventa_troca():
    """Metade dos arquivos não traz marca; ausência não pode virar sinal."""
    sem_marca = """1
00:00:00,000 --> 00:00:04,000
Primeira frase inteira da fala.

2
00:00:04,000 --> 00:00:09,000
Segunda frase da mesma pessoa.
"""
    segmentos = parse_transcript_text(sem_marca)["segments"]
    assert segmentos
    assert not any(s.get("speaker_change") for s in segmentos)


# ── a consequência: o corte abre onde o repórter fala ──────────────────────

def test_a_marca_vira_costura_de_conversa():
    """É para isso que ela serve: dizer onde o entrevistador toma a palavra.

    Sem ela, a costura era adivinhada por vocabulário — "candidato,", "o
    senhor" —, e uma pergunta que não usa nenhuma dessas formas passava batida.
    Com ela, a fronteira vem escrita no arquivo.
    """
    from modules.clip_selector import ClipSelector

    seletor = ClipSelector()
    frases = seletor._build_sentences(parse_transcript_text(COLETIVA)["segments"])
    costuras = seletor._conversation_seams(frases)
    assert costuras, "a marca não virou costura"
    # 00:17:34.960 = 1054,96 s — a primeira troca do trecho.
    assert any(abs(c - 1054.96) < 3.0 for c in costuras), costuras


def test_a_marca_nao_dispensa_os_portoes_editoriais():
    """Saber onde o locutor troca não autoriza abrir um corte em qualquer troca.

    Numa coletiva há troca a cada aparte — "obrigado", "próxima" — e transformar
    cada uma em fronteira devolveria o defeito das fatias de cronômetro por outro
    caminho.
    """
    from modules.clip_selector import ClipSelector

    aparte = """00:00:00.000 >> Obrigado.
00:00:01.500 >> De nada, e como eu dizia, a economia da
00:00:04.000 região precisa de investimento de verdade
"""
    seletor = ClipSelector()
    frases = seletor._build_sentences(parse_transcript_text(aparte)["segments"])
    for clip in seletor._close_where_the_thought_ends(
        [{"start": 1.5, "end": 4.0, "text": "", "duration": 2.5}], frases
    ):
        assert clip["end"] >= 4.0


# ── a pergunta é o setup, e o corte abria na resposta ──────────────────────

def test_o_corte_recua_ate_a_pergunta_marcada_logo_antes():
    """Abrir na resposta com a pergunta seis segundos atrás é perder o contexto.

    Na coletiva de João Pessoa isso aconteceu duas vezes. Em 22:00 o arquivo
    marca `>> como vai desenvolver sua campanha frente` — a pergunta — e o corte
    abria em 22:06, em `>> Falando a verdade, eu não vou abrir concessão`, que é
    a resposta.

    O recuo de abertura não tocava nisso porque a resposta *se sustenta sozinha*:
    "Falando a verdade..." é uma frase inteira, então nada indicava que faltava
    algo. O que indica é a marca: quem fala mudou seis segundos antes, e o que
    veio antes é a pergunta que este corte responde.
    """
    from modules.clip_selector import ClipSelector

    bruto = """00:22:00.919 >> como vai desenvolver sua campanha frente
00:22:03.500 aos outros candidatos do estado?
00:22:06.880 >> Falando a verdade, eu não vou abrir
00:22:09.400 concessão, não vou mudar um A do que eu
00:22:12.000 venho dizendo desde o primeiro dia disso.
00:22:15.200 A campanha vai ser feita na rua, com as
00:22:18.100 pessoas, e não em gabinete fechado com
00:22:21.000 quem sempre mandou nesse estado aqui.
"""
    seletor = ClipSelector(min_duration=8, max_duration=180, preferred_max_duration=60)
    frases = seletor._build_sentences(parse_transcript_text(bruto)["segments"])
    clipes = seletor._open_where_the_thought_begins(
        [{"start": 1326.88, "end": 1344.0, "text": "", "duration": 17.12}], frases
    )
    inicio = float(clipes[0]["start"])
    assert inicio < 1326.0, (
        f"abriu em {inicio:.1f}s, na resposta; a pergunta marcada está em 1320,9s"
    )
    assert abs(inicio - 1320.919) < 0.5, f"não parou na pergunta: {inicio:.1f}s"


def test_o_recuo_nao_atravessa_duas_trocas_de_locutor():
    """Uma pergunta é setup; duas trocas atrás já é outra conversa."""
    from modules.clip_selector import ClipSelector

    bruto = """00:00:00.000 >> Obrigado pela presença de todos.
00:00:03.000 >> E qual a proposta para a segurança?
00:00:06.000 >> A proposta é colocar polícia na rua com
00:00:09.000 condição de trabalho e salário decente.
00:00:12.000 Sem isso o resto é conversa para inglês
00:00:15.000 ver, e o senhor sabe disso tão bem quanto
00:00:18.000 eu, porque já viu esse filme antes.
"""
    seletor = ClipSelector(min_duration=8, max_duration=180, preferred_max_duration=60)
    frases = seletor._build_sentences(parse_transcript_text(bruto)["segments"])
    clipes = seletor._open_where_the_thought_begins(
        [{"start": 6.0, "end": 21.0, "text": "", "duration": 15.0}], frases
    )
    inicio = float(clipes[0]["start"])
    assert inicio >= 3.0, f"recuou até {inicio:.1f}s, atravessando a saudação"
    assert abs(inicio - 3.0) < 0.5, f"não parou na pergunta: {inicio:.1f}s"


def test_o_recuo_passa_por_cima_de_um_sim_sim():
    """Entre a pergunta e a resposta cabe um aceite de palavra, e ele não é turno.

    Em 12:35 da coletiva o repórter pergunta — "A pergunta é, o senhor foi com a
    parada de segurança para" —, o Renan responde "Sim, sim." e só então começa a
    resposta de verdade. O arquivo marca troca nos três. Parar no "Sim, sim."
    devolveria o mesmo defeito: o corte abre na resposta e a pergunta fica de
    fora, agora com um "sim" pendurado na frente.

    Ignorar um aceite não é atravessar dois turnos — é ignorar um turno que não
    diz nada. Qualquer coisa maior que isso continua sendo fronteira.
    """
    from modules.clip_selector import ClipSelector

    bruto = """00:12:35.920 >> A pergunta é, o senhor foi com a parada
00:12:37.360 de segurança para
00:12:38.880 >> Sim, sim.
00:12:39.660 >> Eu ando com o apoio da Polícia Federal
00:12:43.920 por conta das regras eleitorais, e essa
00:12:47.920 ação foi uma ação tomada pelo nosso time
00:12:51.320 com a central de denúncias que a gente
00:12:54.399 recebe do Brasil inteiro todo dia.
"""
    seletor = ClipSelector(min_duration=8, max_duration=180, preferred_max_duration=60)
    frases = seletor._build_sentences(parse_transcript_text(bruto)["segments"])
    clipes = seletor._open_where_the_thought_begins(
        [{"start": 759.66, "end": 778.0, "text": "", "duration": 18.34}], frases
    )
    inicio = float(clipes[0]["start"])
    assert abs(inicio - 755.92) < 0.5, (
        f"abriu em {inicio:.1f}s; a pergunta marcada está em 755,9s e entre as duas "
        f"só há um 'Sim, sim.'"
    )


def test_uma_resposta_inteira_no_meio_nao_e_aceite():
    """O controle do teste acima: só o aceite curto é ignorado.

    Se entre a pergunta e este corte houver uma resposta de verdade, ela é a
    conversa, e recuar por cima dela abriria o corte num assunto que já foi
    respondido.
    """
    from modules.clip_selector import ClipSelector

    bruto = """00:00:00.000 >> O senhor pretende manter o programa?
00:00:03.000 >> Pretendo manter e ampliar o alcance
00:00:06.000 dele para o interior do estado inteiro.
00:00:09.000 >> Mas o custo disso vai sair de onde, do
00:00:12.000 orçamento da saúde ou de imposto novo?
00:00:15.000 >> Sai de corte de cargo comissionado, que
00:00:18.000 é o que sobra de gordura nessa máquina.
"""
    seletor = ClipSelector(min_duration=8, max_duration=180, preferred_max_duration=60)
    frases = seletor._build_sentences(parse_transcript_text(bruto)["segments"])
    clipes = seletor._open_where_the_thought_begins(
        [{"start": 15.0, "end": 27.0, "text": "", "duration": 12.0}], frases
    )
    inicio = float(clipes[0]["start"])
    assert inicio >= 9.0, f"recuou até {inicio:.1f}s, por cima de uma resposta inteira"


def test_porque_de_explicacao_nao_e_pergunta():
    """"É porque" explica; "por que" pergunta. A lista confundia as duas.

    Na coletiva o Renan diz "Quando eles aceitam? isso, é porque naturalmente
    eles concordam com o jogo de cartas marcadas." A limpeza de vocativo cortava
    "isso," e sobrava "é porque", que a lista de aberturas aceitava como
    pergunta. O resultado foi uma fronteira de bloco no meio de uma frase dele.
    """
    from modules.interview_turns import is_a_whole_question

    assert not is_a_whole_question("isso, é porque naturalmente eles concordam")
    assert not is_a_whole_question("Não vou, porque não acredito nisso.")
    # A forma interrogativa continua valendo, com e sem ponto.
    assert is_a_whole_question("Candidato, por que o senhor não foi ao debate")
    assert is_a_whole_question("Por que isso não saiu do papel?")


def test_a_ultima_palavra_do_locutor_anterior_nao_entra_no_corte():
    """A legenda quebra na marca, e sobra um resto de centésimos antes da borda.

    "O processo todo tá acontecendo. E" — esse "E" é a última palavra de quem
    falava antes, e o tactiq lhe dá 8 centésimos colados na troca de locutor.
    Ele não está no áudio do corte que abre na pergunta, e não pode estar na
    legenda dele: o corte de 22:00 começava escrito "E como vai desenvolver sua
    campanha", com um "E" que ninguém fala.
    """
    from modules.clip_selector import ClipSelector

    frases = [
        {"start": 1318.76, "end": 1320.85, "text": "O processo todo tá acontecendo."},
        {"start": 1320.85, "end": 1320.92, "text": "E"},
        {"start": 1320.92, "end": 1325.39, "text": "como vai desenvolver sua campanha?"},
    ]
    texto = ClipSelector._text_between(frases, 1320.919, 1326.0)
    assert texto.startswith("como vai"), texto
    assert not texto.startswith("E "), texto
