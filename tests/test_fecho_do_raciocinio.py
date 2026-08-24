"""O corte fechava onde o bloco fechava, não onde o raciocínio fechava.

A queixa mais teimosa do editor, sobre o clipe 1 de João Pessoa:

    "entra em um tema bacana mesmo começando no meio do contexto, mas ele parece
    não concluir o tema"

Medido contra as fronteiras humanas do Acervo (`scripts/medir_cortes.py`), o
podcast — a única das três fontes onde a conversa não tem costura detectável —
entrega cortes de 39 s onde o rotulador implica 94 s. Ali o corte é *um bloco*, e
o bloco fecha pelo relógio.

O módulo promete o contrário num comentário desde sempre: "the selector may still
join blocks when the context requires it". No caminho local isso nunca aconteceu.

Este arquivo guarda o passo que faltava, e ele é o espelho do recuo de abertura.
A abertura recua enquanto o texto não começa um pensamento; o fecho avança
enquanto o texto seguinte **não consegue começar um**. Um trecho que abre com "e",
"mas", "então", "aí" ou "porque" é, por construção gramatical, a continuação do
anterior — deixá-lo de fora garante um corte que para no meio do raciocínio, e
deixá-lo virar corte próprio garante um que abre no meio dele.

Não é heurística de tópico. Foi medido antes de ser escrito: coesão léxica entre
blocos vizinhos (TextTiling) aponta na direção certa mas separa fraco demais
(+0,04 a +0,09) e com três travessias de amostra — construir limiar ali seria
ajustar a ruído. Já a muleta de conversa, no podcast, aparece em 59% dos pares
dentro do mesmo território e em **nenhuma** das travessias.
"""

import pytest

from modules.clip_selector import ClipSelector


def _frases(linhas):
    return ClipSelector()._build_sentences(
        [{"start": a, "end": b, "text": t} for a, b, t in linhas]
    )


def _corte(inicio, fim, texto=""):
    return {"start": inicio, "end": fim, "text": texto, "duration": fim - inicio}


# Uma explicação que continua depois de onde o bloco fecharia.
EXPLICACAO = [
    (0.0, 9.0, "O Brasil tem um estado grande demais para o que ele entrega."),
    (9.4, 18.0, "A gente paga imposto de país rico e recebe serviço de país pobre."),
    (18.4, 27.0, "E isso não se resolve trocando quem manda, se resolve mudando o modelo."),
    (27.4, 36.0, "Então o que a gente propõe é cortar privilégio antes de falar em imposto."),
    (36.4, 45.0, "Aí sobra dinheiro para saúde, para educação e para segurança de verdade."),
    (45.4, 54.0, "É isso que a gente chama de estado que cabe no bolso do brasileiro."),
    (58.0, 67.0, "Mudando de assunto, quero falar da eleição do ano que vem."),
]


# ── o passo em si ──────────────────────────────────────────────────────────

def test_o_fecho_avanca_enquanto_a_frase_seguinte_nao_se_sustenta():
    seletor = ClipSelector(min_duration=8, max_duration=180, preferred_max_duration=30)
    frases = _frases(EXPLICACAO)
    # O corte fecha aos 18 s, onde o relógio fecharia o bloco — e a frase
    # seguinte abre com "E", que não se sustenta sozinha.
    clipes = seletor._close_where_the_thought_ends([_corte(0.0, 18.0)], frases)
    fim = float(clipes[0]["end"])
    assert fim > 18.0, "o corte parou onde o bloco parou, não onde o raciocínio parou"
    assert fim == pytest.approx(45.0), (
        f"fechou em {fim}s; devia seguir até 45,0s. A frase seguinte — 'É isso "
        f"que a gente chama...' — se sustenta sozinha, e é ali que o raciocínio "
        f"fecha"
    )


def test_o_fecho_para_na_primeira_frase_que_se_sustenta_sozinha():
    """Ele avança até o raciocínio fechar, não até o teto."""
    seletor = ClipSelector(min_duration=8, max_duration=180, preferred_max_duration=30)
    clipes = seletor._close_where_the_thought_ends([_corte(0.0, 18.0)], _frases(EXPLICACAO))
    assert "Mudando de assunto" not in clipes[0].get("text", ""), (
        "engoliu o começo do assunto seguinte"
    )


def test_corte_que_ja_fecha_bem_nao_e_tocado():
    """O controle: onde a frase seguinte se sustenta, não há o que estender."""
    seletor = ClipSelector(min_duration=8, max_duration=180, preferred_max_duration=30)
    clipes = seletor._close_where_the_thought_ends([_corte(0.0, 45.0)], _frases(EXPLICACAO))
    assert float(clipes[0]["end"]) == pytest.approx(45.0)


# ── os limites ─────────────────────────────────────────────────────────────

def test_o_avanco_e_limitado_e_nao_engole_o_video_inteiro():
    """Uma fala que emenda muleta atrás de muleta não vira um corte de dez minutos."""
    linhas = [(0.0, 9.0, "Primeira ideia inteira que abre o assunto.")]
    tempo = 9.4
    for i in range(40):
        linhas.append((tempo, tempo + 9.0, f"E aí a coisa continua na parte {i} sem fechar."))
        tempo += 9.4
    seletor = ClipSelector(min_duration=8, max_duration=180, preferred_max_duration=30)
    clipes = seletor._close_where_the_thought_ends([_corte(0.0, 18.0)], _frases(linhas))
    duracao = float(clipes[0]["end"]) - float(clipes[0]["start"])
    assert duracao <= seletor.max_duration, f"corte de {duracao:.0f}s estourou o limite duro"
    assert duracao <= 18.0 + seletor.preferred_max_duration + 9.5, (
        f"avançou {duracao - 18.0:.0f}s; o orçamento é um teto preferencial "
        f"({seletor.preferred_max_duration:.0f}s) mais a frase que o cruza"
    )


def test_a_palavra_do_entrevistador_fecha_o_raciocinio():
    """Quem responde terminou quando quem pergunta retoma a palavra."""
    linhas = [
        (0.0, 9.0, "A segurança pública é o que mais aflige o paraibano hoje."),
        (9.4, 18.0, "E a gente vai colocar polícia na rua com condição de trabalho."),
        (18.4, 27.0, "Candidato, e sobre a economia, qual é a proposta?"),
        (27.4, 36.0, "E aí na economia a gente parte do corte de privilégio."),
    ]
    seletor = ClipSelector(min_duration=8, max_duration=180, preferred_max_duration=30)
    clipes = seletor._close_where_the_thought_ends([_corte(0.0, 9.0)], _frases(linhas))
    fim = float(clipes[0]["end"])
    assert fim == pytest.approx(18.0), (
        f"fechou em {fim}s; a pergunta do repórter aos 18,4s é o fim do raciocínio "
        f"e o corte não pode atravessá-la"
    )


def test_o_limite_duro_manda_no_avanco():
    seletor = ClipSelector(min_duration=8, max_duration=25, preferred_max_duration=25)
    clipes = seletor._close_where_the_thought_ends([_corte(0.0, 18.0)], _frases(EXPLICACAO))
    assert float(clipes[0]["end"]) - 0.0 <= 25.0


def test_sem_frases_o_passo_devolve_o_que_recebeu():
    seletor = ClipSelector()
    entrada = [_corte(0.0, 18.0)]
    assert seletor._close_where_the_thought_ends(entrada, []) == entrada


# ── a medida que motivou tudo ──────────────────────────────────────────────

def test_o_podcast_do_acervo_deixa_de_cortar_a_um_terco_do_alvo():
    """A régua externa: `scripts/medir_cortes.py` contra as fronteiras humanas.

    O podcast entregava 0,41 do tamanho que o rotulador implica. Este é o número
    que o passo existe para mover, e ele é medido na fonte real, não numa fixture
    escrita para agradar ao seletor.
    """
    import json
    import pathlib
    import statistics

    caminho = pathlib.Path(__file__).parent / "fixtures" / "acervo_inteligencia_1607.json"
    if not caminho.exists():
        pytest.skip("fixture do Acervo ausente")
    fixture = json.loads(caminho.read_text(encoding="utf-8"))
    segmentos = [
        {"start": s["start"], "end": s["end"], "text": s["text"]}
        for s in fixture["sentencas"]
    ]
    territorios = [(r["start"], r["end"], r["cortes"]) for r in fixture["blocos_de_referencia"]]

    import inspect

    from modules.editorial_context import analyze_transcript_context

    seletor = ClipSelector(max_clips=12, min_duration=20, max_duration=480)
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
    assert clips

    duracao = statistics.median(c["end"] - c["start"] for c in clips)
    alvo = statistics.median((t[1] - t[0]) / max(1, t[2]) for t in territorios)
    razao = duracao / alvo
    assert razao >= 0.60, (
        f"razão de duração em {razao:.2f} (mediana {duracao:.0f}s contra alvo "
        f"{alvo:.0f}s); o corte continua sendo um bloco em vez de um raciocínio"
    )

    # E o que já estava certo continua certo: nenhum corte pode passar a
    # atravessar território de assunto por causa da extensão.
    def toca(clip):
        return [
            t for t in territorios
            if min(t[1], clip["end"]) - max(t[0], clip["start"]) > 1.0
        ]

    atravessam = [c for c in clips if len(toca(c)) > 1]
    assert len(atravessam) / len(clips) <= 0.20, (
        f"{len(atravessam)}/{len(clips)} cortes atravessam fronteira de assunto; "
        f"estender o fecho não pode ser comprado com contexto errado"
    )
