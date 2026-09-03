"""A nota não sabia a diferença entre o Renan e quem apresenta.

Medido na sabatina da Band — 382 frases, 32 minutos, material de verdade —
pelo caminho completo do programa: seletor, ranqueador e portão. Dos DOZE
melhores cortes que ele receberia, CINCO não abriam no entrevistado:

    81 (4º lugar)  "Renan, eu preciso chamar aqui o nosso intervalo"
    80             "O senhor manteria essas empresas estatais?"
    79             "Renan, por favor, de maneira cara, eu me sinto..."
    79             "A gente precisa finalizar... considerações finais"
    78             "Deixa eu colocar um outro assunto aqui na roda"

E uma saudação de chegada — "queria agradecer a Band" — tirava 79.

Eram dois defeitos empilhados.

O primeiro: o programa não reconhecia nada disso. "Eu preciso chamar aqui o
nosso intervalo" não era lido como intervalo, porque o vocabulário exigia
"vamos ao intervalo" ou "voltamos". O apresentador dizendo "Renan," — o sinal
mais forte e mais barato que existe numa entrevista, já que o entrevistado
nunca diz o próprio nome em vocativo — não era lido de jeito nenhum.

O segundo: o pouco que ele reconhecia só ia para revisão, sem tocar na nota.
Um corte que abre na chamada do intervalo aparecendo em quarto lugar não é um
corte para revisar; é um corte que não existe.
"""

import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]


# ── 1. o programa reconhece quem está falando ───────────────────────────────


@pytest.mark.parametrize("frase", [
    "Renan, eu preciso chamar aqui o nosso intervalo, mas só para complementar uma questão.",
    "Renan, por favor, de maneira clara, eu me sinto dadas as devidas proporções.",
    "E o que o senhor responde a isso, Renan?",
    # A forma que faltava, e que a âncora mais usa: o nome entre duas
    # vírgulas, no meio da frase. Sem ela, a entrega da palavra na sabatina da
    # Band era lida aos 671 s em vez de aos 17,8 s, e a peneira de entrevista
    # jogava fora TODO candidato dos primeiros onze minutos — treze de treze,
    # nos blocos que o Acervo diz que valem dezesseis cortes.
    "Também agradeço, Renan, por aceitar o nosso convite e tá aqui com a gente no programa.",
    "Antes do Mitre da Thaís, Renan, deixa eu também fazer uma pergunta.",
])
def test_chamar_pelo_nome_e_alguem_falando_com_ele(frase):
    """O entrevistado não diz o próprio nome em vocativo. Quem diz é quem
    apresenta, e ele diz o tempo todo."""
    from modules.interview_turns import addresses_the_guest

    assert addresses_the_guest(frase)


@pytest.mark.parametrize("frase", [
    # A armadilha da abertura da sabatina: o nome vem depois de vírgula e
    # termina em ponto, mas é aposto — a âncora apresentando ao público.
    "De acordo com o sorteio, o primeiro a detalhar suas propostas é o candidato do Missão, Renan Santos.",
    "O Renan Santos disse isso na semana passada.",
    "Estão aqui com a gente o Renan Santos e o Aldo Rebelo.",
    "Eu conversei com o Renan sobre isso ontem.",
])
def test_nomear_em_terceira_pessoa_nao_e_falar_com_ele(frase):
    """Contar o aposto punha a costura aos 31,6 s, dentro da leitura do
    estúdio — o mesmo defeito que já tinha tirado "candidato" da lista."""
    from modules.interview_turns import addresses_the_guest

    assert not addresses_the_guest(frase)


def test_o_nome_do_entrevistado_pode_ser_outro():
    """A regra é do formato, não da pessoa."""
    from modules.interview_turns import addresses_the_guest

    assert addresses_the_guest("Aldo, o senhor concorda com isso?", nomes=("aldo",))
    assert not addresses_the_guest("Aldo, o senhor concorda com isso?", nomes=("renan",))


def test_chamar_o_intervalo_e_um_intervalo():
    """O vocabulário exigia "vamos ao intervalo" ou "voltamos". Ninguém na TV
    brasileira fala assim: fala-se "chamar o intervalo"."""
    from modules.interview_turns import classify_broadcast_boundary

    assert classify_broadcast_boundary(
        "Renan, eu preciso chamar aqui o nosso intervalo, mas só para complementar uma questão."
    ) == "break_start"


def test_chamar_para_o_debate_nao_e_intervalo():
    """O verbo sozinho não basta; ele exige o intervalo logo adiante."""
    from modules.interview_turns import classify_broadcast_boundary

    assert classify_broadcast_boundary("Chamar para o debate quem nunca governou é um erro.") is None


@pytest.mark.parametrize("frase,motivo", [
    ("A gente precisa finalizar um minuto, se puder também, na sequência, considerações finais.", "fala_de_mesa"),
    ("Deixa eu colocar um outro assunto aqui na roda que tá todo dia no noticiário.", "fala_de_mesa"),
    ("Renan, eu preciso chamar aqui o nosso intervalo.", "intervalo"),
    ("Bom, de fato é minha primeira vez aqui. Queria agradecer a Band, agradecer todo o time.", "cortesia"),
])
def test_a_abertura_que_nao_afirma_nada_tem_nome(frase, motivo):
    """Três coisas nunca são o começo de um corte, e as três estavam entre os
    doze melhores: o intervalo, o programa se administrando e a cortesia."""
    from modules.interview_turns import opens_without_a_claim

    assert opens_without_a_claim(frase) == motivo


@pytest.mark.parametrize("frase", [
    "Atualmente é um instrumento autoritário dos seus pares e ele precisa ser combatido.",
    "A nossa representação política no Brasil é inteiramente equivocada.",
    "O tempo do país acabou; precisamos de reformas antes que seja tarde.",
    "Um prefeito hoje ganha uma eleição fazendo um show do Wesley Safadão.",
])
def test_os_cortes_bons_continuam_passando(frase):
    """O vocabulário é estreito de propósito. "nosso tempo" não é "o tempo do
    país", e o desconto agora é caro demais para um falso positivo."""
    from modules.interview_turns import is_interviewer_sentence, opens_without_a_claim

    assert opens_without_a_claim(frase) is None
    assert not is_interviewer_sentence(frase)


def test_deputado_e_governador_em_terceira_pessoa_nao_sao_vocativo():
    """"a emenda do deputado aliado" — o Renan explicando como um prefeito
    ganha eleição — era lido como alguém CHAMANDO um deputado. Enquanto a
    marcação só ia para revisão isso passava; agora custaria nota num corte
    que presta."""
    from modules.interview_turns import is_interviewer_sentence

    assert not is_interviewer_sentence("Um prefeito ganha eleição com a emenda do deputado aliado.")
    assert not is_interviewer_sentence("O governador do Ceará já me processou duas vezes.")
    # A forma vocativa continua valendo.
    assert is_interviewer_sentence("Deputado, o senhor acha que isso resolve?")
    assert is_interviewer_sentence("Governador, qual a sua proposta?")


# ── 2. a nota desconta ──────────────────────────────────────────────────────


def _nota(clip):
    from modules.editorial_ranker import EditorialRanker

    base = {
        "text": "O Estado brasileiro gasta mal, gasta demais e entrega pouco, e isso não é opinião, é o que os números mostram todo ano.",
        "start": 0.0, "end": 60.0, "duration": 60.0,
        "context_complete": True, "payoff_complete": True, "evidence_present": True,
    }
    resultado = EditorialRanker().score_clip({**base, **clip})
    return int(resultado.get("editorial_potential_score", resultado.get("viral_score", 0)))


@pytest.mark.parametrize("motivo", ["intervalo", "fala_de_mesa", "cortesia"])
def test_abrir_sem_afirmar_nada_derruba_a_nota(motivo):
    """Um corte que abre na chamada do intervalo tirava 81 e ficava em quarto
    lugar."""
    limpo = _nota({})
    marcado = _nota({"opens_without_a_claim": motivo, "context_complete": False})
    assert marcado < limpo - 25, (
        f"abrir em {motivo} custou só {limpo - marcado} pontos; era para ser caro"
    )


def test_o_motivo_do_desconto_chega_na_tela():
    """Descontar sem dizer por quê é o programa mandando ele adivinhar."""
    from modules.editorial_ranker import EditorialRanker

    resultado = EditorialRanker().score_clip({
        "text": "Renan, eu preciso chamar aqui o nosso intervalo, mas só para complementar uma questão.",
        "start": 0.0, "end": 40.0, "duration": 40.0,
        "opens_without_a_claim": "intervalo", "context_complete": False,
    })
    motivos = json.dumps(resultado, ensure_ascii=False, default=str)
    assert "intervalo" in motivos


def test_abrir_na_pergunta_sem_resposta_desconta():
    limpo = _nota({})
    marcado = _nota({"starts_with_question_only": True, "context_complete": False})
    assert marcado < limpo - 15


# ── 3. a pergunta longa é aparada, a curta fica ─────────────────────────────


def _entrevista(duracao_da_pergunta):
    fim = duracao_da_pergunta
    return [
        {"start": 0.0, "end": fim,
         "text": "Renan, eu queria te perguntar uma coisa que tem incomodado muita gente, e envolve o senhor, o partido e o eleitor que está em casa."},
        {"start": fim, "end": fim + 20,
         "text": "Olha, a resposta é simples e eu vou dar ela sem rodeio nenhum. O Estado brasileiro gasta mal, gasta demais e entrega pouco."},
        {"start": fim + 20, "end": fim + 44,
         "text": "Quando você olha o orçamento da União, a maior parte não chega na ponta: some em estrutura, em emenda, em coisa que ninguém audita."},
    ]


def _avaliar(frases):
    from modules.clip_selector import ClipSelector

    fim = float(frases[-1]["end"])
    corte = {"start": 0.0, "end": fim, "duration": fim,
             "text": " ".join(f["text"] for f in frases)}
    return ClipSelector(min_duration=15, max_duration=180)._evaluate_interview_boundaries(
        [corte], frases
    )[0]


def test_a_pergunta_longa_sai_e_o_corte_abre_na_resposta():
    """Escolha dele: "só quando a pergunta é curta". Passando do limite, o que
    ela faz é gastar a abertura do corte, que é onde se ganha ou se perde quem
    está assistindo."""
    corte = _avaliar(_entrevista(22.0))
    assert corte["question_trimmed_from_opening_s"] == pytest.approx(22.0, abs=0.1)
    assert corte["start"] == pytest.approx(22.0, abs=0.1)
    assert corte["original_start_before_question_trim"] == pytest.approx(0.0, abs=0.1)
    assert corte["duration"] == pytest.approx(44.0, abs=0.5), "o fim do corte não podia se mexer"


def test_a_pergunta_curta_fica_porque_da_contexto():
    """Numa entrevista, ouvir a pergunta ajuda a entender a resposta — mas só
    enquanto ela for uma frase, não um preâmbulo."""
    corte = _avaliar(_entrevista(6.0))
    assert "question_trimmed_from_opening_s" not in corte
    assert corte["start"] == pytest.approx(0.0, abs=0.1)


def test_aparar_nunca_deixa_o_corte_menor_que_o_minimo():
    """Um corte aparado até deixar de ser corte é pior que um corte que abre na
    pergunta."""
    frases = [
        {"start": 0.0, "end": 30.0, "text": "Renan, eu queria te perguntar uma coisa que envolve o senhor e o eleitor que está em casa agora."},
        {"start": 30.0, "end": 40.0, "text": "Olha, a resposta é simples: o Estado gasta mal e entrega pouco, e isso não é opinião nenhuma."},
    ]
    corte = _avaliar(frases)
    assert "question_trimmed_from_opening_s" not in corte, (
        "aparou e deixou 10s, abaixo do mínimo de 15"
    )


def test_a_resposta_nao_comeca_um_segundo_depois_da_pergunta():
    """Da sabatina, aos 671,3 s: "Renan, por favor," e, um segundo depois, "de
    maneira clara, eu me sinto, dadas as devidas proporções, como o Churchill
    pré-Segunda Guerra...". É a mesma pessoa seguindo a mesma frase; a
    diarização automática marcou troca de locutor onde não havia.

    Sem esta regra o programa lê uma pergunta de 1,0 s — que passa longe do
    teto de aparo — e o corte abre com onze segundos de jornalista.
    """
    frases = [
        {"start": 0.0, "end": 1.0, "text": "Renan, por favor,"},
        {"start": 1.0, "end": 12.0, "text": "de maneira clara, eu me sinto, dadas as devidas proporções, como o Churchill pré-Segunda Guerra, porque o mundo caminha para um conflito."},
        {"start": 12.0, "end": 40.0, "text": "O mundo está indo para um clima de guerra fria que fica cada vez mais quente a cada ano que passa."},
    ]
    corte = _avaliar(frases)
    assert corte.get("opens_without_a_claim"), (
        "o corte abre no entrevistador e passou como se a resposta já tivesse começado"
    )
    assert corte.get("answer_words_after_last_question") == 0


# ── 4. os portões medidos do CHUB ───────────────────────────────────────────


def test_o_espelho_entrega_os_portoes_que_ninguem_lia():
    """Estavam no arquivo desde que o espelho existe. A palavra `portoes` não
    aparecia em nenhum módulo do motor."""
    from modules.espelho_chub import portoes

    lidos = portoes()
    assert lidos.get("comeca_no_meio_da_frase") == pytest.approx(-28.0)
    assert lidos.get("termina_sem_fechar") == pytest.approx(-18.0)
    assert lidos.get("pergunta_e_resposta_completas") == pytest.approx(14.0)


def test_nenhum_portao_sozinho_decide_o_corte(tmp_path, monkeypatch):
    """Um peso que derruba ou salva um corte por conta própria deixa de ser
    desempate e vira a decisão inteira."""
    import modules.espelho_chub as espelho

    pacote = tmp_path / "espelho_chub.json"
    pacote.write_text(json.dumps({
        # `ganchos` é o que faz o carregador aceitar o arquivo como espelho.
        "ganchos": [{"conta": "@renansantosmbl", "familia": "tese-provocativa", "n": 9, "mediana": 1.0}],
        "portoes": {"comeca_no_meio_da_frase": -900, "pergunta_e_resposta_completas": 900},
    }), encoding="utf-8")
    monkeypatch.setenv("FURIA_CLIPS_DATA_DIR", str(tmp_path / "sem-espelho-do-editor"))
    monkeypatch.setattr(espelho, "PACOTE", pacote)
    espelho.recarregar()
    try:
        lidos = espelho.portoes()
        assert lidos["comeca_no_meio_da_frase"] == -30.0
        assert lidos["pergunta_e_resposta_completas"] == 30.0
    finally:
        espelho.recarregar()


def test_sem_espelho_o_programa_continua_ranqueando(tmp_path, monkeypatch):
    """Ele tem de funcionar sem internet e sem o espelho instalado."""
    import modules.espelho_chub as espelho

    monkeypatch.setattr(espelho, "PACOTE", tmp_path / "nao_existe.json")
    monkeypatch.setenv("FURIA_CLIPS_DATA_DIR", str(tmp_path / "sem-espelho-do-editor"))
    espelho.recarregar()
    try:
        assert espelho.portoes() == {}
    finally:
        espelho.recarregar()


def test_a_medicao_dele_substitui_o_meu_palpite():
    """O desconto por começar no meio da frase era 14, um número que eu
    escolhi. O espelho mede o mesmo defeito em 5.339 cortes publicados e dá
    28."""
    from modules.editorial_ranker import EditorialRanker

    EditorialRanker._PESOS_DO_ESPELHO = None
    assert EditorialRanker._peso("comeca_no_meio_da_frase", 14) == 28
    assert EditorialRanker._peso("termina_sem_fechar", 12) == 18
    assert EditorialRanker._peso("um_portao_que_nao_existe", 7) == 7


# ── 5. o material de verdade ────────────────────────────────────────────────


def test_na_sabatina_de_verdade_nenhum_corte_bom_abre_fora_do_entrevistado():
    """A prova final, no material real e pelo caminho completo do programa.

    Antes: cinco dos doze melhores não abriam no entrevistado, e o pior deles
    — o apresentador chamando o intervalo — estava em quarto lugar com 81.
    """
    import app as motor
    from modules.clip_selector import ClipSelector
    from modules.interview_turns import opens_without_a_claim
    from modules.viral_ranker import ViralRanker

    fixture = RAIZ / "tests" / "fixtures" / "acervo_sabatina_band.json"
    frases = json.loads(fixture.read_text(encoding="utf-8"))["sentencas"]
    transcricao = {
        "segments": [dict(f) for f in frases],
        "full_text": " ".join(f["text"] for f in frases),
    }

    candidatos = ClipSelector(min_duration=15, max_duration=180, max_clips=12).select_clips(
        transcricao, settings={"editorial_context": {}}, emit_progress=lambda *_a, **_k: None
    )
    ranqueados = ViralRanker(editorial_profile="renan_santos_politics").rank_clips(candidatos)
    entregues, _ = motor._defer_context_incomplete_candidates(ranqueados)
    assert entregues, "a sabatina parou de render corte nenhum"

    def abre_sem_afirmar(clip):
        primeira = str(clip.get("text") or "").strip().split(".")[0][:200]
        return opens_without_a_claim(primeira) is not None

    # Nos cinco melhores não pode sobrar nenhum. Mais abaixo, um corte marcado
    # e rebaixado é uma opção que ele pode olhar — não um defeito.
    ruins_no_topo = [c for c in entregues[:5] if abre_sem_afirmar(c)]
    assert not ruins_no_topo, (
        "voltou a entregar como melhor corte uma abertura que não afirma nada: "
        + " | ".join(str(c.get("text") or "")[:70] for c in ruins_no_topo)
    )

    # E se algum sobrou mais abaixo, ele tem de estar rebaixado de verdade.
    for clip in entregues:
        if abre_sem_afirmar(clip):
            assert int(clip.get("viral_score", 0)) <= 45, (
                "abertura sem afirmação nenhuma continua com nota alta: "
                f"{clip.get('viral_score')} — {str(clip.get('text') or '')[:70]}"
            )


def test_a_sabatina_nao_entrega_o_mesmo_trecho_duas_vezes():
    """Antes eram quatro sobreposições em 23 candidatos, uma delas de 34
    segundos — metade de um corte repetida no outro.

    Um encontro curto entre dois cortes de assuntos diferentes é a emenda
    entre eles, não repetição: o limite é sobre quanto do corte se repete.
    """
    import app as motor
    from modules.clip_selector import ClipSelector
    from modules.viral_ranker import ViralRanker

    fixture = RAIZ / "tests" / "fixtures" / "acervo_sabatina_band.json"
    frases = json.loads(fixture.read_text(encoding="utf-8"))["sentencas"]
    transcricao = {
        "segments": [dict(f) for f in frases],
        "full_text": " ".join(f["text"] for f in frases),
    }
    candidatos = ClipSelector(min_duration=15, max_duration=180, max_clips=12).select_clips(
        transcricao, settings={"editorial_context": {}}, emit_progress=lambda *_a, **_k: None
    )
    entregues, _ = motor._defer_context_incomplete_candidates(
        ViralRanker(editorial_profile="renan_santos_politics").rank_clips(candidatos)
    )
    ordenados = sorted(entregues, key=lambda c: float(c.get("start", 0) or 0))
    for antes, depois in zip(ordenados, ordenados[1:]):
        comum = float(antes.get("end", 0)) - float(depois.get("start", 0))
        if comum <= 0:
            continue
        duracao = max(1.0, float(depois.get("end", 0)) - float(depois.get("start", 0)))
        assert comum / duracao <= 0.30, (
            f"{comum:.0f}s repetidos, {comum / duracao * 100:.0f}% do corte de "
            f"{depois.get('start'):.0f}s"
        )


def test_a_entrega_da_palavra_na_sabatina_nao_pode_cair_no_meio_do_programa():
    """A guarda que este teste protege é a mais cara que já apareceu aqui.

    `_align_to_interview_turns` descarta todo candidato anterior à entrega da
    palavra, porque antes dela o programa está se apresentando e o convidado
    ainda não falou. Quando a entrega é lida tarde demais, esse descarte deixa
    de ser proteção e vira uma tesoura cega: na sabatina da Band ela caía aos
    671 s — 35% do programa — e levava junto treze candidatos bons.

    O sintoma era invisível pelo lado de dentro: nenhum erro, nenhum aviso, só
    metade do vídeo que não rendia corte. Por isso o teste mede o número, e não
    a ausência de exceção.
    """
    import json

    from modules.interview_turns import first_address_to_guest

    fixture = RAIZ / "tests" / "fixtures" / "acervo_sabatina_band.json"
    frases = json.loads(fixture.read_text(encoding="utf-8"))["sentencas"]
    entrega = first_address_to_guest(frases)

    assert entrega is not None, "a entrega da palavra sumiu; tudo vira estúdio"
    assert entrega < 60.0, (
        f"a entrega da palavra foi lida aos {entrega:.1f}s. Acima de um minuto "
        f"num programa de 32 minutos ela não é entrega — é uma forma de vocativo "
        f"que o reconhecedor deixou passar, e todo candidato antes dela será "
        f"descartado sem aviso"
    )
