"""Metade das ferramentas de legenda não pontua nada, e o estúdio exigia ponto.

O editor importou uma legenda de 111 linhas para gerar só a headline — o vídeo ele
tinha montado fora do Furia — e não aconteceu nada. A legenda não tem um único
ponto final. O construtor de frases nunca fechava uma sentença, então saíram sete
blocos de 41 a 128 palavras, e todos foram recusados por "sem fechamento de
frase". Zero citações, e a tela não disse o motivo.

Onde não há pontuação não há fronteira de frase para encontrar, e fingir que há
seria pior que admitir. A fronteira que existe é a pausa: o orador respirou ali.
Ela é real e não é fim de frase, então a citação sai marcada para ser conferida no
áudio antes de virar aspas.
"""

from modules.headline_quote import (
    transcript_is_punctuated,
    units_from_pauses,
)
from modules.headline_studio import FORMAT_SQUARE, generate_artwork_copy


# Verbatim da legenda que o editor importou, com os tempos do arquivo.
SEM_PONTUACAO = """1
00:00:00,000 --> 00:00:00,800
a compra de voto

2
00:00:00,900 --> 00:00:02,166
ela é a base da democracia brasileira

3
00:00:02,266 --> 00:00:03,366
existe compra de voto hoje

4
00:00:03,400 --> 00:00:04,500
pelo amor de Deus na verdade

5
00:00:05,200 --> 00:00:07,266
só existe compra de voto é

6
00:00:07,566 --> 00:00:09,366
quanto mais você desce na pirâmide social mais

7
00:00:09,600 --> 00:00:11,500
a compra de voto tá presente na vida das pessoas

8
00:00:11,966 --> 00:00:13,966
o Brasil provavelmente é a democracia no mundo que mais tem

9
00:00:14,300 --> 00:00:16,900
e você tem a compra de voto quando chega a época da eleição

10
00:00:17,400 --> 00:00:19,900
e uma família vai receber uma grana do cabo eleitoral
"""

COM_PONTUACAO = """1
00:00:00,000 --> 00:00:04,000
As criptos são uma nova lógica de reserva de valor.

2
00:00:04,000 --> 00:00:09,000
As pessoas sempre darão um jeito de transacionar entre elas.

3
00:00:09,000 --> 00:00:14,000
O Brasil escolheu o caminho arcaico para tratar essa tecnologia.
"""


def _linhas(texto):
    from modules.transcript_parser import parse_transcript_text

    return parse_transcript_text(texto)["segments"]


# ── reconhecer a fonte ─────────────────────────────────────────────────────

def test_a_pergunta_e_sobre_densidade_de_pontuacao_e_nao_sobre_cada_linha():
    """Uma legenda do YouTube põe o ponto no meio da linha o tempo todo.

    Perguntar linha a linha classificava uma fonte bem pontuada como sem
    pontuação e jogava fora as fronteiras de frase que ela de fato tinha — os
    cortes voltaram a abrir no meio da frase enquanto essa versão esteve de pé.
    """
    quebrada_no_meio = [
        {"start": 0.0, "end": 2.3, "text": "premiando por boas práticas. você cria"},
        {"start": 2.3, "end": 5.2, "text": "uma um um sentimento de irmandade no"},
        {"start": 5.2, "end": 6.5, "text": "continente que não existe. O Brasil é"},
        {"start": 6.5, "end": 9.0, "text": "muito isolado no continente sul-americano. A gente fala no"},
        {"start": 9.0, "end": 12.0, "text": "máximo assim os países da tríplice fronteira. Às vezes um Uruguai, mas tudo"},
        {"start": 12.0, "end": 15.0, "text": "muito pouco. A nossa relação é muito distante e isso inclui parte do sul."},
    ]
    assert transcript_is_punctuated(quebrada_no_meio), (
        "uma fonte com ponto no meio de cada linha continua sendo uma fonte "
        "pontuada; só nenhuma linha termina em ponto"
    )
    assert not transcript_is_punctuated(_linhas(SEM_PONTUACAO))


def test_fonte_curta_demais_nao_e_julgada():
    assert transcript_is_punctuated([{"text": "duas palavras só"}])


# ── a fronteira que sobra quando não há pontuação ──────────────────────────

def test_sem_pontuacao_a_fronteira_vem_da_pausa_e_sai_marcada():
    unidades = units_from_pauses(_linhas(SEM_PONTUACAO))
    assert unidades, "a pausa é a única fronteira que existe nesta fonte"
    assert all(item["boundary_source"] == "pausa" for item in unidades)
    assert all(item["end"] > item["start"] for item in unidades)
    # Nenhum bloco de cem palavras: isso não é citação de coisa nenhuma.
    assert max(len(item["text"].split()) for item in unidades) <= 30


def test_a_legenda_do_editor_volta_a_produzir_headline():
    result = generate_artwork_copy(
        SEM_PONTUACAO,
        mini_context="Renan falando sobre compra de votos",
        preferred_format=FORMAT_SQUARE,
        ai_backend=None,
    )
    sugestoes = result["formats"][FORMAT_SQUARE]["suggestions"]
    assert sugestoes, "a legenda sem pontuação voltou a devolver tela em branco"
    assert result["review_flags"]["no_quote_found"] is False
    assert result["review_flags"]["quote_boundary_from_pause"] is True
    for item in sugestoes:
        assert item["quote"]["boundary_source"] == "pausa"
        assert item["quote"]["text"].lower() in " ".join(
            linha["text"] for linha in _linhas(SEM_PONTUACAO)
        ).lower()


def test_fonte_pontuada_continua_usando_a_fronteira_de_frase():
    """O controle: a correção não pode custar a fonte que já funcionava."""
    result = generate_artwork_copy(
        COM_PONTUACAO, preferred_format=FORMAT_SQUARE, ai_backend=None
    )
    sugestoes = result["formats"][FORMAT_SQUARE]["suggestions"]
    assert sugestoes
    assert all(item["quote"]["boundary_source"] == "pontuacao" for item in sugestoes)
    assert result["review_flags"]["quote_boundary_from_pause"] is False


# ── o que continua sendo recusado mesmo sem pontuação ──────────────────────

def test_fala_encenada_na_voz_de_outra_pessoa_continua_recusada():
    """"ô quantos votos vou trazer aqui, pô" é o cabo eleitoral, não o candidato.

    O verbo de fala nem sempre está na frase anterior. O que denuncia a encenação
    é o vocativo de conversa de rua, e atribuir isso ao entrevistado seria a
    citação falsa mais cara que este módulo pode produzir.
    """
    from modules.headline_quote import _disqualify

    assert _disqualify(
        "ô quantos votos vou trazer aqui pô tem minha família toda", cased=False, punctuated=False
    ) == "fala encenada na voz de outra pessoa"


def test_repeticao_de_palavra_da_transcricao_continua_recusada():
    from modules.headline_quote import _disqualify

    assert _disqualify(
        "quantos votos votos vou trazer para a nossa família", cased=False, punctuated=False
    ) == "repetição de palavra na transcrição"


def test_terminar_em_palavra_funcional_e_fragmento_com_ou_sem_pontuacao():
    from modules.headline_quote import _disqualify

    for pontuada in (True, False):
        assert _disqualify(
            "só existe compra de voto é", cased=False, punctuated=pontuada
        ) in {"termina no meio de uma oração", "sem fechamento de frase"}
