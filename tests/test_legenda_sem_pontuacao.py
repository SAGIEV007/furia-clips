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

import pytest

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

4
00:00:14,000 --> 00:00:19,000
O caminho arcaico das criptos afasta as novas gerações.
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
    assert result["review_flags"]["source_not_punctuated"] is True
    # Numa fonte sem pontuação não há frase fechada para citar ao pé da letra,
    # então o modo `citacao` — que promete literalidade palavra por palavra — não
    # sai daqui. Saem a leitura em terceira pessoa e a forma atribuída, cujas
    # aspas carregam a afirmação passada para o registro escrito.
    assert all(item["mode"] in {"resumo", "atribuicao"} for item in sugestoes)
    for item in sugestoes:
        assert item["eyebrow"].strip(), "toda headline sai com gancho"
    resumos = [item for item in sugestoes if item["mode"] == "resumo"]
    assert resumos
    for item in resumos:
        assert '"' not in item["headline"] and "“" not in item["headline"]


def test_fonte_pontuada_continua_usando_a_fronteira_de_frase():
    """O controle: a correção não pode custar a fonte que já funcionava."""
    result = generate_artwork_copy(
        COM_PONTUACAO, preferred_format=FORMAT_SQUARE, ai_backend=None
    )
    sugestoes = result["formats"][FORMAT_SQUARE]["suggestions"]
    assert sugestoes
    assert result["review_flags"]["source_not_punctuated"] is False
    # Onde a fonte pontua, a citação literal volta a ser uma opção possível.
    assert any(item["mode"] == "citacao" for item in sugestoes)


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


# ── quando nem pausa existe ────────────────────────────────────────────────

SEM_PAUSA = """1
00:00:00,000 --> 00:00:03,500
o STF está uma porcaria

2
00:00:03,600 --> 00:00:08,000
ministros que ninguém elegeu decidindo o futuro do país

3
00:00:08,100 --> 00:00:12,500
legislando no lugar do Congresso e censurando rede social

4
00:00:12,600 --> 00:00:16,000
isso é absurdo isso é vergonhoso
"""


def test_legenda_com_cues_coladas_ainda_produz_unidades():
    """Uma folga de 0,1 s entre cues não é pausa, e a legenda virava um bloco só.

    Metade dos arquivos de legenda tem cue contígua — a linha seguinte começa um
    décimo de segundo depois da anterior. Sem pausa acima de 0,3 s, tudo virava
    uma unidade de 29 palavras, acima do teto de 24, e a tela devolvia zero
    headlines. Foi assim que o editor viu "não aparece nada".
    """
    unidades = units_from_pauses(_linhas(SEM_PAUSA))
    assert len(unidades) > 1, (
        f"a legenda inteira virou {len(unidades)} unidade(s) de "
        f"{[len(u['text'].split()) for u in unidades]} palavras"
    )
    assert all(len(u["text"].split()) <= 24 for u in unidades)


def test_a_fronteira_de_linha_sai_marcada_como_mais_fraca_que_a_pausa():
    """Quem corta ali precisa saber que não foi o orador que parou.

    A pausa é evidência de que ele respirou. A quebra de linha é evidência de que
    alguém que legendou achou que a linha tinha enchido — é fronteira real, mas
    de outra natureza, e uma citação tirada dali precisa de conferência maior.
    """
    unidades = units_from_pauses(_linhas(SEM_PAUSA))
    fontes = {u["boundary_source"] for u in unidades}
    assert "linha de legenda" in fontes, fontes


def test_onde_ha_pausa_ela_continua_mandando():
    """O controle: a pausa não perde para a contagem de palavras."""
    unidades = units_from_pauses(_linhas(SEM_PONTUACAO))
    assert all(u["boundary_source"] == "pausa" for u in unidades), (
        f"a pausa deixou de ser a fronteira: {[u['boundary_source'] for u in unidades]}"
    )


def test_a_legenda_de_cues_coladas_volta_a_produzir_headline():
    """Esteve marcado como `xfail` estrito por meia hora, e ele se anunciou.

    O defeito medido era "mais material produz menos headline": com duas linhas
    esta fonte devolvia uma sugestão e com quatro, nenhuma. A causa não era o
    score relativo, como eu tinha suposto ao marcar — era `key_term` exigindo que
    o assunto se repetisse. Numa legenda de quatro linhas "STF" aparece uma vez,
    e sem assunto morrem de uma vez as famílias resumo, atribuição e afirmação.
    O termo passou a poder vir do minicontexto, que é onde o editor já escreve o
    assunto, e o teste virou verde sozinho — que é para isso que `strict=True`
    serve.
    """
    result = generate_artwork_copy(
        SEM_PAUSA, mini_context="Renan Santos sobre o STF",
        preferred_format=FORMAT_SQUARE, ai_backend=None,
    )
    sugestoes = result["formats"][FORMAT_SQUARE]["suggestions"]
    assert sugestoes, "a legenda de cues coladas continua devolvendo tela em branco"
    for item in sugestoes:
        assert item["eyebrow"].strip()
