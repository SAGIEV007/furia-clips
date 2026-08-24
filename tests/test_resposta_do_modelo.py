"""O Gemini respondeu bem e o Furia jogou a resposta fora.

Na coletiva de João Pessoa o log registrou, em três linhas seguidas:

    [Gemini] Resposta recebida de gemini-2.5-flash (22836 chars). Parseando...
    [Gemini] JSON parseado mas 0 clips validos. Preview: ```json [ { "blocks": [ {
    "start": 219.0, "end": 223.0, "text": "Pera, tem os outros. ..." },
    [Gemini] Lote sem resposta. Ultimo erro: 0 clips parsed

Vinte e dois mil caracteres de análise, JSON bem formado, e a corrida inteira caiu
para o NLP básico. O modelo não errou: ele disse onde cortar pelo tempo, que é a
forma mais direta de dizer isso. O parser só sabia ler índice de bloco, e um dict
onde ele esperava um int vira `TypeError` dentro de um `except ... continue`.

Tempo é endereço melhor que índice — o índice depende de como nós agrupamos as
frases, o tempo não depende de nada. Resolver um intervalo para os blocos que ele
cobre é aritmética. Recusar a resposta por causa do formato era o Furia perdendo a
única análise cara que ele tinha na mão.

As regras editoriais não mudam com o formato: um conjunto de blocos com buraco
continua sendo recusado, curto demais continua sendo recusado. Só o endereçamento
passou a aceitar as duas formas.
"""

import pytest

from modules.clip_selector import ClipSelector


def _blocos(selector, spans):
    """Blocos editoriais como `_build_transcript_blocks` os entrega."""
    blocos = []
    for index, (start, end, text) in enumerate(spans):
        frases = [{
            "start": start, "end": end, "text": text,
            "speakers": [], "timing_confidence": 1.0,
        }]
        blocos.append(selector._make_editorial_block(index, start, end, text, frases))
    return blocos


# A coletiva, na granularidade em que o Furia a entregou ao modelo.
COLETIVA = [
    (200.0, 219.0, "Boa tarde a todos, obrigado pela presença de vocês aqui hoje."),
    (219.0, 232.0, "Pera, tem os outros. Quais os compromissos que o seu governo teria com a Paraíba?"),
    (232.0, 258.0, "Olha, o primeiro compromisso é com a segurança pública, que é o que mais aflige o paraibano hoje."),
    (258.0, 281.0, "E o segundo é gerar emprego de verdade, não emprego de programa social. Essa é a questão."),
    (281.0, 300.0, "Vamos para a próxima pergunta, por favor."),
]

# Verbatim da forma que o modelo devolveu e que o parser recusou.
RESPOSTA_POR_TEMPO = """```json
[
  {
    "blocks": [
      {
        "start": 219.0,
        "end": 223.0,
        "text": "Pera, tem os outros. Quais os compromissos que o seu governo teria com a Paraíba?"
      },
      {
        "start": 232.0,
        "end": 258.0,
        "text": "Olha, o primeiro compromisso é com a segurança pública."
      },
      {
        "start": 258.0,
        "end": 280.7,
        "text": "E o segundo é gerar emprego de verdade. Essa é a questão."
      }
    ],
    "title": "Renan responde sobre compromissos com a Paraíba",
    "speaker": "Renan Santos",
    "reason": "Pergunta da reporter e resposta completa",
    "editorial_family": "politico",
    "hook": "B",
    "flow": "A",
    "value": "B",
    "energy": "B"
  }
]
```"""

RESPOSTA_POR_INDICE = """[
  {
    "blocks": [1, 2, 3],
    "title": "Renan responde sobre compromissos com a Paraíba",
    "speaker": "Renan Santos",
    "reason": "Pergunta da reporter e resposta completa",
    "editorial_family": "politico",
    "hook": "B", "flow": "A", "value": "B", "energy": "B"
  }
]"""


@pytest.fixture
def selector():
    return ClipSelector(min_duration=15, max_duration=300)


# ── a resposta que foi jogada fora ─────────────────────────────────────────

def test_resposta_endereçada_por_tempo_vira_clip(selector):
    blocos = _blocos(selector, COLETIVA)
    clips = selector._parse_llm_response(RESPOSTA_POR_TEMPO, [], blocos, 0, source="gemini")

    assert clips, (
        "o modelo disse exatamente onde cortar e o Furia devolveu lista vazia; "
        "foi assim que a coletiva inteira caiu para o NLP básico"
    )
    clip = clips[0]
    assert clip["start"] == pytest.approx(219.0)
    assert clip["end"] == pytest.approx(281.0)
    assert clip["title"] == "Renan responde sobre compromissos com a Paraíba"


def test_as_duas_formas_de_endereço_dão_o_mesmo_corte(selector):
    """Índice e tempo apontam o mesmo trecho; o corte não pode depender do formato."""
    blocos = _blocos(selector, COLETIVA)
    por_tempo = selector._parse_llm_response(RESPOSTA_POR_TEMPO, [], blocos, 0)
    por_indice = selector._parse_llm_response(RESPOSTA_POR_INDICE, [], blocos, 0)

    assert por_tempo and por_indice
    assert por_tempo[0]["start"] == por_indice[0]["start"]
    assert por_tempo[0]["end"] == por_indice[0]["end"]
    assert por_tempo[0]["text"] == por_indice[0]["text"]


def test_o_texto_do_clip_vem_da_transcrição_e_não_do_modelo(selector):
    """O modelo reescreveu a fala ao citá-la; o clip carrega o que foi dito.

    Na resposta acima o modelo encurtou "não emprego de programa social" fora da
    citação. Quem legenda e quem gera headline lê este campo, então ele tem de vir
    do bloco, nunca do resumo do modelo.
    """
    blocos = _blocos(selector, COLETIVA)
    clip = selector._parse_llm_response(RESPOSTA_POR_TEMPO, [], blocos, 0)[0]
    assert "não emprego de programa social" in clip["text"]


def test_intervalo_no_nível_do_clip_também_é_lido(selector):
    """Sem a chave `blocks`, com start/end no próprio objeto — mesma intenção."""
    resposta = """[
      {"start": 219.0, "end": 280.7, "title": "Compromissos com a Paraíba",
       "hook": "B", "flow": "A", "value": "B", "energy": "B"}
    ]"""
    blocos = _blocos(selector, COLETIVA)
    clips = selector._parse_llm_response(resposta, [], blocos, 0)
    assert clips
    assert clips[0]["start"] == pytest.approx(219.0)
    assert clips[0]["end"] == pytest.approx(281.0)


# ── o que continua sendo recusado ──────────────────────────────────────────

def test_buraco_no_meio_continua_recusado_quando_o_endereço_é_tempo(selector):
    """Pular um bloco é pular contexto, e isso não muda porque veio em segundos."""
    resposta = """[
      {"blocks": [
        {"start": 219.0, "end": 232.0, "text": "a pergunta"},
        {"start": 258.0, "end": 280.0, "text": "o fim da resposta"}
      ], "title": "t", "hook": "B", "flow": "B", "value": "B", "energy": "B"}
    ]"""
    blocos = _blocos(selector, COLETIVA)
    assert selector._parse_llm_response(resposta, [], blocos, 0) == []


def test_intervalo_fora_do_vídeo_é_recusado(selector):
    resposta = """[
      {"blocks": [{"start": 4200.0, "end": 4260.0, "text": "nada aqui"}],
       "title": "t", "hook": "B", "flow": "B", "value": "B", "energy": "B"}
    ]"""
    blocos = _blocos(selector, COLETIVA)
    assert selector._parse_llm_response(resposta, [], blocos, 0) == []


def test_curto_demais_continua_recusado(selector):
    resposta = """[
      {"blocks": [{"start": 281.5, "end": 283.0, "text": "próxima pergunta"}],
       "title": "t", "hook": "B", "flow": "B", "value": "B", "energy": "B"}
    ]"""
    blocos = _blocos(selector, COLETIVA)
    curto = ClipSelector(min_duration=30, max_duration=300)
    assert curto._parse_llm_response(resposta, [], blocos, 0) == []


def test_índice_de_bloco_não_é_confundido_com_segundo(selector):
    """`[1, 2, 3]` são blocos. Ler como segundos daria um corte no início do vídeo."""
    blocos = _blocos(selector, COLETIVA)
    clip = selector._parse_llm_response(RESPOSTA_POR_INDICE, [], blocos, 0)[0]
    assert clip["start"] == pytest.approx(219.0), "índice virou segundo"


# ── o silêncio, que foi o que custou caro ──────────────────────────────────

def test_recusa_de_resposta_é_dita_em_voz_alta(selector):
    """"0 clips parsed" não dizia por quê, e a corrida caiu sem ninguém saber.

    Vinte e dois mil caracteres de análise foram descartados com uma linha de log
    que não nomeava o motivo. Quando o parser recusa tudo, o motivo da primeira
    recusa vai para o progresso — é a diferença entre um bug de duas semanas e um
    de dez minutos.
    """
    avisos = []
    resposta = """[
      {"blocks": [{"start": 4200.0, "end": 4260.0, "text": "nada aqui"}],
       "title": "t", "hook": "B", "flow": "B", "value": "B", "energy": "B"}
    ]"""
    blocos = _blocos(selector, COLETIVA)
    assert selector._parse_llm_response(
        resposta, [], blocos, 0, emit_progress=lambda msg, nivel="info": avisos.append(msg)
    ) == []
    assert avisos, "a recusa saiu calada"
    assert any("nenhum bloco" in msg.lower() for msg in avisos), avisos


# ── por que o modelo respondeu naquela forma ───────────────────────────────

def test_a_pre_analise_nao_ensina_a_forma_errada(selector):
    """A pré-análise ia no prompt como `repr` de dicionário do Python.

    Listas de `{'start': ..., 'end': ...}` logo acima do pedido de
    `"blocks": [3, 4, 5]` — e foi nessa forma que o modelo respondeu. Num vídeo
    curto esse bloco ocupava 65% do prompt, a maior parte em escrituração interna
    (`boundary_basis`, `needs_speaker_review`, índices de segmento) que o modelo
    não tem como usar.
    """
    contexto = {
        "description": "Pré-análise: coletiva com 6 perguntas detectadas.",
        "participant_confidence": 0.5,
        "interview_windows": [{"start": 10.0, "end": 180.0, "evidence": 8}],
        "qa_candidates": [{
            "start": 219.0, "end": 280.7, "question_segment": 1,
            "boundary_basis": "sem_diarização", "needs_speaker_review": True,
            "confidence": 0.54,
        }],
        "editorial_chapters": [{
            "id": "chapter-001", "index": 0, "start": 0.0, "end": 201.0,
            "label": "segurança / emprego / paraíba", "qa_candidate_ids": [0],
            "segment_start": 0, "segment_end": 20,
        }],
    }
    texto = selector._render_editorial_context(contexto)

    assert "{" not in texto and "[" not in texto, (
        "a pré-análise ainda mostra a forma de objeto que o modelo copiou"
    )
    # O relógio da pré-análise é o mesmo dos blocos da transcrição.
    assert "03:39–04:40" in texto
    assert "segurança / emprego / paraíba" in texto
    # Escrituração interna não vai para o prompt.
    for interno in ("boundary_basis", "needs_speaker_review", "segment_start",
                    "qa_candidate_ids", "chapter-001", "confidence"):
        assert interno not in texto, interno


def test_sem_pre_analise_o_prompt_nao_ganha_secao_vazia(selector):
    assert selector._render_editorial_context(None) == ""
    assert selector._render_editorial_context({}) == ""


# ── o modelo devolve o relógio que nós ensinamos a ele ─────────────────────

RESPOSTA_EM_RELOGIO = """```json
[
  {
    "blocks": [
      {"start": "03:39", "end": "03:52", "text": "a pergunta da reporter"},
      {"start": "03:52", "end": "04:41", "text": "a resposta inteira"}
    ],
    "title": "Compromissos com a Paraíba",
    "hook": "B", "flow": "A", "value": "B", "energy": "B"
  }
]
```"""


def test_endereço_em_mm_ss_é_lido(selector):
    """`"start": "00:55"` é o formato que o prompt ensina, e ele era recusado.

    A transcrição vai para o modelo com cada bloco rotulado `[MM:SS - MM:SS]`, e
    desde a 6.12 a pré-análise também. Medindo o caminho do Gemini na conta real,
    o primeiro lote da sabatina voltou exatamente assim — e `float("00:55")`
    levanta `ValueError` dentro do mesmo `except` que já tinha custado a coletiva
    de João Pessoa. Ensinar um formato e recusar a resposta nele é o defeito
    inteiro, de novo, uma camada acima.
    """
    blocos = _blocos(selector, COLETIVA)
    clips = selector._parse_llm_response(RESPOSTA_EM_RELOGIO, [], blocos, 0, source="gemini")
    assert clips, "o modelo respondeu no relógio que nós ensinamos e foi recusado"
    assert clips[0]["start"] == pytest.approx(219.0)
    assert clips[0]["end"] == pytest.approx(281.0)


def test_relógio_com_hora_também_é_lido(selector):
    """Fonte de 1h21 fala em HH:MM:SS, e é a duração real das fontes do editor."""
    resposta = """[
      {"blocks": [{"start": "00:03:39", "end": "00:04:41", "text": "x"}],
       "title": "t", "hook": "B", "flow": "A", "value": "B", "energy": "B"}
    ]"""
    blocos = _blocos(selector, COLETIVA)
    clips = selector._parse_llm_response(resposta, [], blocos, 0)
    assert clips
    assert clips[0]["start"] == pytest.approx(219.0)


def test_texto_que_não_é_relógio_continua_recusado(selector):
    resposta = """[
      {"blocks": [{"start": "logo depois", "end": "mais tarde", "text": "x"}],
       "title": "t", "hook": "B", "flow": "B", "value": "B", "energy": "B"}
    ]"""
    blocos = _blocos(selector, COLETIVA)
    assert selector._parse_llm_response(resposta, [], blocos, 0) == []
