from modules.clip_selector import ClipSelector
from modules.interview_turns import (
    classify_broadcast_boundary,
    detect_interviewer_turns,
)


def _talk(rows):
    return [
        {"start": start, "end": end, "text": text}
        for start, end, text in rows
    ]


def test_broadcast_break_requires_a_call_or_a_return():
    assert classify_broadcast_boundary(
        "Candidato, nós vamos agora fazer um rápido intervalo e daqui a pouco voltamos."
    ) == "break_start_and_return"
    assert classify_broadcast_boundary("A gente volta já já.") == "return"
    assert classify_broadcast_boundary("O intervalo entre duas sessões foi longo.") is None


def test_break_and_return_are_hard_turns_and_do_not_absorb_next_question():
    sentences = _talk([
        (100.0, 106.0, "O raciocínio anterior termina aqui com uma conclusão clara."),
        (106.0, 126.0, "Candidato, nós vamos agora fazer um rápido intervalo e daqui a pouco voltamos."),
        (126.0, 128.0, "A gente volta já já."),
        (128.0, 132.0, "Estamos de volta com a entrevista."),
        (132.0, 140.0, "Candidato, qual é a próxima medida do seu plano?"),
        (140.0, 160.0, "A próxima medida é executar o plano com orçamento e fiscalização.") ,
    ])
    turns = detect_interviewer_turns(sentences)
    hard = [turn for turn in turns if turn["hard_boundary"]]
    assert len(hard) == 1
    assert hard[0]["broadcast_break"] is True
    assert hard[0]["broadcast_return"] is True
    assert hard[0]["start_s"] == 106.0
    assert hard[0]["end_s"] == 132.0
    assert any(turn["start_s"] == 132.0 and not turn["hard_boundary"] for turn in turns)


def test_candidate_starting_in_break_is_moved_to_first_editorial_sentence_after_return():
    selector = ClipSelector(min_duration=8, max_duration=180)
    sentences = _talk([
        (100.0, 106.0, "A resposta anterior fecha com clareza e termina aqui."),
        (106.0, 126.0, "Candidato, nós vamos agora fazer um rápido intervalo e daqui a pouco voltamos."),
        (126.0, 128.0, "A gente volta já já."),
        (128.0, 132.0, "Estamos de volta com a entrevista."),
        (132.0, 140.0, "Candidato, qual é a próxima medida do seu plano?"),
        (140.0, 168.0, "A próxima medida é executar o plano com orçamento, fiscalização e transparência."),
    ])
    selector._candidate_diagnostics = {"hard_negatives": [], "candidate_relationships": []}
    clips = selector._align_to_interview_turns(
        [{"start": 106.0, "end": 168.0, "text": "..."}], sentences
    )
    assert len(clips) == 1
    assert clips[0]["start"] == 132.0
    assert clips[0]["end"] == 168.0
    assert clips[0]["turn_aligned"]["crossed_broadcast_break"] is True


def test_question_with_only_short_answer_is_marked_for_defer_not_as_complete():
    selector = ClipSelector(min_duration=8, max_duration=180)
    sentences = _talk([
        (0.0, 12.0, "Candidato, qual é a sua proposta para o país?"),
        (12.0, 15.0, "É uma proposta muito importante."),
        (15.0, 18.0, "Vamos detalhar depois."),
        (50.0, 58.0, "Agora, outro tema: como será a execução?"),
        (58.0, 78.0, "A execução terá metas, orçamento, transparência e avaliação pública."),
    ])
    clips = [{
        "start": 0.0,
        "end": 18.0,
        "text": "Candidato, qual é a sua proposta para o país? É uma proposta muito importante. Vamos detalhar depois.",
        "context_complete": True,
        "payoff_complete": True,
        "review_required": False,
    }]
    selector._evaluate_interview_boundaries(clips, sentences)
    assert clips[0]["starts_with_interviewer_question"] is True
    assert clips[0]["answer_words_after_last_question"] < selector.MIN_SUBSTANTIAL_ANSWER_WORDS
    assert clips[0]["starts_with_question_only"] is True
    assert clips[0]["context_complete"] is False
    assert "starts_with_question_only" in clips[0]["review_reason_codes"]


def test_interrupted_answer_is_not_declared_payoff_complete():
    selector = ClipSelector(min_duration=8, max_duration=180)
    sentences = _talk([
        (0.0, 8.0, "Candidato, qual é a sua proposta?"),
        (8.0, 28.0, "A proposta reduz o desperdício e amplia o atendimento para quem precisa."),
        (28.0, 32.0, "Mas o senhor consegue fazer isso?"),
        (32.0, 42.0, "Sim, porque o orçamento será reorganizado e a execução começa no primeiro ano."),
    ])
    clips = [{
        "start": 0.0,
        "end": 30.0,
        "text": "Candidato, qual é a sua proposta? A proposta reduz o desperdício e amplia o atendimento para quem precisa. Mas o senhor consegue fazer isso?",
        "context_complete": True,
        "payoff_complete": True,
        "review_required": False,
    }]
    selector._evaluate_interview_boundaries(clips, sentences)
    assert clips[0]["ending_interruption"] is True
    assert clips[0]["payoff_complete"] is False
    assert "ending_interruption" in clips[0]["review_reason_codes"]


def test_touching_answers_with_a_question_between_remain_two_opportunities_and_other_touching_parts_link():
    selector = ClipSelector(min_duration=8, max_duration=180)
    question_and_answer = _talk([
        (0.0, 8.0, "Candidato, qual é a primeira medida?"),
        (8.0, 28.0, "A primeira medida é executar a proposta com orçamento e controle público."),
        (28.0, 36.0, "Senhor, qual é a segunda medida?"),
        (36.0, 58.0, "A segunda medida é garantir fiscalização, metas e transparência."),
    ])
    kept = selector._drop_touching_siblings([
        {"start": 0.0, "end": 28.0, "viral_score": 70, "text": "primeira resposta"},
        {"start": 28.0, "end": 58.0, "viral_score": 68, "text": "segunda resposta"},
    ], sentences=question_and_answer)
    assert len(kept) == 2

    no_question = _talk([
        (0.0, 20.0, "A resposta continua desenvolvendo o mesmo argumento."),
        (20.0, 40.0, "E depois apresenta a consequência do mesmo argumento."),
    ])
    kept = selector._drop_touching_siblings([
        {"start": 0.0, "end": 20.0, "viral_score": 70, "text": "continuação"},
        {"start": 20.0, "end": 40.0, "viral_score": 72, "text": "mesma continuação"},
    ], sentences=no_question)
    assert len(kept) == 1
    assert any(
        item["relation"] == "continuation_of"
        for item in selector._candidate_diagnostics["candidate_relationships"]
    )


def test_same_opening_is_explained_as_alternative_not_a_second_opportunity():
    selector = ClipSelector(min_duration=8, max_duration=180)
    selector._candidate_diagnostics = {"hard_negatives": [], "candidate_relationships": []}
    kept = selector._remove_overlaps([
        {"start": 10.0, "end": 50.0, "viral_score": 80, "text": "A proposta melhora a segurança e entrega resultados claros."},
        {"start": 10.0, "end": 70.0, "viral_score": 60, "text": "A proposta melhora a segurança e entrega resultados claros com execução detalhada."},
    ])
    assert len(kept) == 1
    assert any(
        item["relation"] == "alternative_of"
        for item in selector._candidate_diagnostics["candidate_relationships"]
    )


def test_repeated_interruption_markers_choose_later_stable_response_opener():
    selector = ClipSelector(min_duration=8, max_duration=180)
    sentences = _talk([
        (100.0, 104.0, "Declarações do senhor e senhoras."),
        (104.0, 108.0, "Por exemplo? Lista. Eu vou dar um exemplo, a ideia é responder por partes."),
        (108.0, 116.0, "O primeiro ponto é retomar as áreas com investigação e prova."),
        (116.0, 120.0, "Vou dar um exemplo, vou de um a um, denúncia anônima."),
        (120.0, 144.0, "Hoje, se existe investigação e outras provas, isso é um procedimento normal e verificável."),
    ])
    assert selector._stabilized_response_start(
        sentences, 108.0, 144.0, minimum_start_s=90.0
    ) == 116.0


def test_question_only_candidate_is_deferred_by_the_backend_gate():
    from app import _defer_context_incomplete_candidates

    renderable, deferred = _defer_context_incomplete_candidates([{
        "start": 0.0,
        "end": 18.0,
        "duration": 18.0,
        "context_complete": False,
        "starts_with_question_only": True,
        "review_required": True,
    }])
    assert renderable == []
    assert deferred[0]["start"] == 0.0
    assert "pergunta de jornalista sem resposta substancial" in deferred[0]["reason"]


def test_interrupted_answer_remains_renderable_for_human_review_when_context_is_complete():
    from app import _defer_context_incomplete_candidates

    candidate = {
        "start": 0.0,
        "end": 30.0,
        "duration": 30.0,
        "context_complete": True,
        "ending_interruption": True,
        "review_required": True,
    }
    renderable, deferred = _defer_context_incomplete_candidates([candidate])
    assert deferred == []
    assert renderable == [candidate]
    assert candidate["review_required"] is True


def test_fragmented_follow_up_question_is_not_left_at_the_end_of_a_clip():
    """A new interviewer question must not enter the tail of the previous answer."""
    selector = ClipSelector(min_duration=15, max_duration=180)
    sentences = _talk([
        (2096.78, 2098.78, "Candidato, eu gostaria de falar sobre direito ao voto."),
        (2098.78, 2100.78, "Você não teria direito, por exemplo, ao voto?"),
        (2100.78, 2104.78, "Se eu concorda com essa ideia, se eleito, o senhor promoveria alguma medida"),
        (2104.78, 2108.78, "para restringir o direito ao voto do cidadão?"),
        (2108.78, 2110.78, "Não, é sua opinião dele."),
        (2110.78, 2115.18, "Eu nem sabia da opinião, mas se ele falou isso, é a opinião dele."),
        (2115.18, 2117.18, "E por que Orlando Lima tem uma participação?"),
        (2117.18, 2119.85, "tão destacada no seu programa de governo?"),
        (2119.85, 2121.85, "Porque ele é um grande pesquisador."),
        (2204.55, 2208.55, "O senhor respondeu à pergunta. Agora vamos falar de economia."),
        (2208.55, 2212.55, "A dívida pública está hoje em 32% do PIB."),
        (2212.55, 2220.55, "Para que percentual do PIB o senhor se compromete a trazer essa dívida?"),
        (2220.55, 2230.55, "Nós vamos adotar medidas responsáveis e reduzir a trajetória da dívida."),
        (2230.55, 2236.55, "Candidato, agora vamos falar sobre saúde pública."),
        (2236.55, 2248.55, "Nós vamos ampliar o atendimento e melhorar a gestão."),
        (2255.55, 2261.55, "Candidato, qual é a sua prioridade para educação?"),
        (2261.55, 2274.55, "A prioridade é investir na base e acompanhar os resultados."),
        (2280.55, 2286.55, "Candidato, para terminar, qual mensagem o senhor deixa?"),
        (2286.55, 2298.55, "A mensagem é que o Brasil pode recuperar sua capacidade de planejamento."),
    ])
    clips = selector._align_to_interview_turns(
        [{"start": 2096.78, "end": 2117.18, "text": "..."}], sentences
    )
    assert len(clips) == 1
    assert clips[0]["end"] <= 2115.18
    assert clips[0]["end"] - clips[0]["start"] >= selector.min_duration
    assert clips[0]["turn_aligned"]["end_shift_s"] < 0
