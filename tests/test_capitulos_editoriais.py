"""O último capítulo saía duplicado em todo vídeo, e isso custava pontos ao corte.

`build_editorial_chapters` fecha o grupo corrente quando acaba a transcrição e,
logo depois, fecha de novo o que sobrou — sem nunca esvaziar o grupo entre as duas
coisas. O resultado é um capítulo final repetido, sempre.

Não é cosmético. `annotate_clip_with_chapters` mede coerência pelo número de
capítulos que o clip toca: um capítulo dá 100, dois dão 84. Um corte que cabe
inteiro dentro do último capítulo tocava os dois clones e levava a penalidade de
quem atravessa fronteira. Num vídeo curto, com um capítulo só, isso atingia todos
os cortes. E o mapa de capítulos vai no prompt do Gemini como "blocos editoriais
contíguos" a respeitar — com um trecho listado duas vezes.
"""

from modules.editorial_chapters import annotate_clip_with_chapters, build_editorial_chapters


def _fala(start, end, texto, pergunta=False):
    return {"start": start, "end": end, "text": texto, "is_question": pergunta}


COLETIVA = [
    _fala(0.0, 9.0, "Boa tarde a todos, obrigado pela presença de vocês aqui hoje."),
    _fala(9.0, 16.0, "Candidato, quais os compromissos do seu governo com a Paraíba?", pergunta=True),
    _fala(16.0, 27.0, "O primeiro compromisso é com a segurança pública, que aflige o paraibano."),
    _fala(27.0, 40.0, "E o segundo é gerar emprego de verdade, não emprego de programa social."),
    _fala(52.0, 58.0, "Renan, o senhor pretende manter o programa atual?", pergunta=True),
    _fala(58.0, 70.0, "Pretendo rever inteiro, porque hoje ele simplesmente não funciona."),
    _fala(70.0, 79.0, "Essa é uma questão muito importante para a Paraíba."),
]


def test_nenhum_capitulo_sai_repetido():
    capitulos = build_editorial_chapters(COLETIVA)
    assert capitulos
    intervalos = [(c["start"], c["end"]) for c in capitulos]
    assert len(intervalos) == len(set(intervalos)), (
        f"o mapa de capítulos repete um trecho: {intervalos}"
    )


def test_os_capitulos_cobrem_a_transcricao_uma_vez_so():
    capitulos = build_editorial_chapters(COLETIVA)
    assert capitulos[0]["start"] == COLETIVA[0]["start"]
    assert capitulos[-1]["end"] == COLETIVA[-1]["end"]
    somado = sum(c["segment_count"] for c in capitulos)
    assert somado == len(COLETIVA), (
        f"{somado} segmentos em capítulos para {len(COLETIVA)} segmentos de transcrição"
    )
    assert [c["index"] for c in capitulos] == list(range(len(capitulos)))


def test_corte_dentro_de_um_capitulo_nao_leva_penalidade_de_fronteira():
    """Cem pontos é o que vale um corte que não atravessa nada."""
    contexto = {"editorial_chapters": build_editorial_chapters(COLETIVA), "qa_candidates": []}
    capitulo = contexto["editorial_chapters"][-1]
    clip = {"start": capitulo["start"] + 1.0, "end": capitulo["end"] - 1.0}
    anotado = annotate_clip_with_chapters(clip, contexto)
    assert anotado["chapter_count"] == 1, anotado["editorial_chapter_ids"]
    assert anotado["chapter_coherence_score"] == 100.0


def test_capitulo_longo_ainda_e_dividido():
    """O controle: parar de duplicar não pode virar parar de dividir."""
    longa = []
    tempo = 0.0
    for numero in range(60):
        longa.append(_fala(tempo, tempo + 9.0, f"Frase número {numero} da explicação."))
        tempo += 9.0
    capitulos = build_editorial_chapters(longa)
    assert len(capitulos) > 1, "540 segundos viraram um capítulo só"
    assert sum(c["segment_count"] for c in capitulos) == len(longa)
