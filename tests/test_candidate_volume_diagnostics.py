import modules.clip_selector as clip_selector_module
from modules.clip_selector import ClipSelector


def _clip(start, end, text):
    return {
        "start": start,
        "end": end,
        "duration": end - start,
        "text": text,
        "viral_score": 80,
        "has_hook": True,
        "starts_mid_sentence": False,
        "starts_with_context_reference": False,
        "opening_dependent": False,
        "ending_fragmented": False,
        "question_detected": False,
        "qa_bridge": False,
        "qa_bridge_local": False,
        "context_complete": True,
        "payoff_complete": True,
        "overlap_suspected": False,
        "contains_broadcast_break": False,
    }


def test_long_transcript_uses_local_fallback_when_primary_pool_is_thin(monkeypatch):
    selector = ClipSelector(target_duration=30, max_clips=15, min_duration=8, max_duration=180)
    # Frases de oito palavras: o construtor só fecha uma sentença com cinco ou
    # mais, e com quatro os segmentos se acumulavam em blocos de trinta segundos.
    # O candidato dos 45 s caía então no meio de uma sentença, e a reparação de
    # abertura o recuava — legítimo, mas este teste é sobre a contagem do pool.
    transcription = {
        "segments": [
            {"start": index * 15.0, "end": (index + 1) * 15.0,
             "text": f"Ideia completa e bem formada de número {index}."}
            for index in range(20)
        ]
    }
    primary = [_clip(0, 30, "A fonte principal encontrou uma tese completa.")]
    primary[0]["source"] = "gemini"
    fallback = [_clip(45, 75, "A alternativa local encontrou outra tese completa.")]
    fallback[0]["source"] = "nlp"
    monkeypatch.setattr(selector, "_select_with_gemini", lambda *args, **kwargs: primary)
    monkeypatch.setattr(selector, "_select_with_nlp", lambda *args, **kwargs: fallback)
    monkeypatch.setattr(clip_selector_module, "annotate_clip_with_chapters", lambda clip, context: clip)

    clips = selector.select_clips(
        transcription,
        settings={"ai_backend": "gemini", "gemini_api_key": "configured"},
    )

    diagnostics = selector.get_candidate_diagnostics()
    assert len(clips) == 2
    assert diagnostics["expected_count"] >= 2
    assert diagnostics["primary_count"] == 1
    assert diagnostics["fallback_count"] == 1
    assert diagnostics["fallback_used"] is True
    assert diagnostics["final_count"] == 2
    origins = {clip["candidate_origin"] for clip in clips}
    assert origins == {"gemini_primary", "local_fallback"}


def test_short_transcript_does_not_create_artificial_candidate_quota(monkeypatch):
    selector = ClipSelector(target_duration=30, max_clips=15, min_duration=8, max_duration=180)
    monkeypatch.setattr(clip_selector_module, "annotate_clip_with_chapters", lambda clip, context: clip)
    clips = selector.select_clips(
        {
            "segments": [
                {"start": 0.0, "end": 15.0, "text": "Uma fala curta e completa."},
                {"start": 15.0, "end": 30.0, "text": "Outra fala curta e completa."},
            ]
        },
        settings={"ai_backend": "auto", "gemini_api_key": ""},
    )
    diagnostics = selector.get_candidate_diagnostics()
    assert diagnostics["expected_count"] == 0
    assert diagnostics["fallback_used"] is False
    assert diagnostics["reason"] == "short_source"
    # Short-source NLP clips may lack context_complete; quality gate filters them.
    # What matters here is that no artificial quota was created.
    assert not clips


def test_primary_candidate_wins_overlapping_local_fallback(monkeypatch):
    selector = ClipSelector(target_duration=30, max_clips=15, min_duration=8, max_duration=180)
    transcription = {
        "segments": [
            {"start": index * 15.0, "end": (index + 1) * 15.0, "text": f"Ideia completa número {index}."}
            for index in range(20)
        ]
    }
    primary = [_clip(0, 30, "A seleção primária preserva a tese completa.")]
    primary[0]["source"] = "gemini"
    fallback = [_clip(10, 40, "A alternativa local repete parte da tese completa.")]
    fallback[0]["source"] = "nlp"
    monkeypatch.setattr(selector, "_select_with_gemini", lambda *args, **kwargs: primary)
    monkeypatch.setattr(selector, "_select_with_nlp", lambda *args, **kwargs: fallback)
    monkeypatch.setattr(clip_selector_module, "annotate_clip_with_chapters", lambda clip, context: clip)

    clips = selector.select_clips(
        transcription,
        settings={"ai_backend": "gemini", "gemini_api_key": "configured"},
    )

    diagnostics = selector.get_candidate_diagnostics()
    assert len(clips) == 1
    assert clips[0]["candidate_origin"] == "gemini_primary"
    assert diagnostics["fallback_discarded_count"] == 1
    assert diagnostics["fallback_discarded_overlap"] == 1


def test_previous_fingerprints_discard_overlap_and_preserve_new_moment():
    selector = ClipSelector(target_duration=30, max_clips=15, min_duration=8, max_duration=180)
    selector._previous_clip_fingerprints = [
        {"start": 100.0, "end": 140.0, "duration": 40.0, "text": "Tese já aprovada", "review_status": "approved"},
        {"start": 240.0, "end": 270.0, "duration": 30.0, "text": "Trecho rejeitado", "review_status": "rejected"},
    ]
    selector._candidate_diagnostics = {
        "previous_discarded_count": 0,
        "previous_discarded_approved": 0,
        "previous_discarded_rejected": 0,
    }

    kept = selector._remove_previous_fingerprints([
        _clip(105.0, 138.0, "A tese já aprovada"),
        _clip(300.0, 332.0, "Uma tese nova e completa"),
    ])

    assert len(kept) == 1
    assert kept[0]["start"] == 300.0
    assert selector._candidate_diagnostics["previous_discarded_count"] == 1
    assert selector._candidate_diagnostics["previous_discarded_approved"] == 1
    assert selector._candidate_diagnostics["previous_discarded_rejected"] == 0


def test_hard_negative_ledger_records_duplicate_reason_and_winner():
    selector = ClipSelector(max_clips=15)
    winner = _clip(0.0, 30.0, "A tese primária completa e independente.")
    loser = _clip(10.0, 40.0, "A tese primária completa e independente com repetição.")
    winner["editorial_potential_score"] = 90
    loser["editorial_potential_score"] = 70
    winner["candidate_origin"] = "local_primary"
    loser["candidate_origin"] = "local_fallback"

    kept = selector._remove_overlaps([winner, loser])
    diagnostics = selector.get_candidate_diagnostics()

    assert kept == [winner]
    assert diagnostics["hard_negative_count"] == 1
    assert len(diagnostics["hard_negatives"]) == 1
    item = diagnostics["hard_negatives"][0]
    assert item["reason"] == "duplicate_overlap"
    assert item["start"] == 10.0
    assert item["winner"]["start"] == 0.0
    assert len(item["text_preview"]) <= 280


def test_hard_negative_ledger_is_bounded():
    selector = ClipSelector()
    selector._candidate_diagnostics = {"hard_negatives": [], "hard_negative_count": 0}

    for index in range(100):
        selector._record_hard_negative(
            _clip(float(index), float(index + 10), f"Candidato quase válido {index}"),
            "teste_limite",
        )

    diagnostics = selector.get_candidate_diagnostics()
    assert len(diagnostics["hard_negatives"]) == 80
    assert diagnostics["hard_negative_count"] == 100


def test_expected_candidate_count_scales_with_long_source_but_stays_bounded():
    selector = ClipSelector(max_clips=36)
    short = [{"start": index * 15.0, "end": (index + 1) * 15.0, "text": "fala"} for index in range(7)]
    long = [{"start": index * 30.0, "end": (index + 1) * 30.0, "text": "fala completa."} for index in range(80)]

    assert selector._expected_candidate_count(short) == 0
    count = selector._expected_candidate_count(long)
    assert 6 <= count <= 36
    assert count > selector._expected_candidate_count(long[:20])


def test_previous_fingerprint_text_similarity_discards_nearby_duplicate():
    selector = ClipSelector(max_clips=15)
    selector._previous_clip_fingerprints = [
        {"start": 500.0, "end": 530.0, "duration": 30.0, "text": "A conclusão é clara e o Brasil precisa mudar", "review_status": "rejected"},
    ]
    selector._candidate_diagnostics = {
        "previous_discarded_count": 0,
        "previous_discarded_approved": 0,
        "previous_discarded_rejected": 0,
    }

    kept = selector._remove_previous_fingerprints([
        _clip(520.0, 550.0, "A conclusão é clara e o Brasil precisa mudar agora"),
    ])

    assert kept == []
    assert selector._candidate_diagnostics["previous_discarded_rejected"] == 1

def test_previous_fingerprint_does_not_discard_distant_same_text():
    selector = ClipSelector(max_clips=15)
    selector._previous_clip_fingerprints = [
        {"start": 500.0, "end": 530.0, "duration": 30.0, "text": "A conclusão é clara e o Brasil precisa mudar", "review_status": "approved"},
    ]
    selector._candidate_diagnostics = {
        "previous_discarded_count": 0,
        "previous_discarded_approved": 0,
        "previous_discarded_rejected": 0,
    }

    kept = selector._remove_previous_fingerprints([
        _clip(800.0, 830.0, "A conclusão é clara e o Brasil precisa mudar"),
    ])

    assert len(kept) == 1
    assert selector._candidate_diagnostics["previous_discarded_count"] == 0


def test_previous_fingerprints_are_reset_for_each_selection_run(monkeypatch):
    selector = ClipSelector(target_duration=30, max_clips=15, min_duration=8, max_duration=180)
    monkeypatch.setattr(selector, "_select_with_nlp", lambda *args, **kwargs: [_clip(0, 30, "Uma tese completa e independente.")])
    monkeypatch.setattr(clip_selector_module, "annotate_clip_with_chapters", lambda clip, context: clip)
    transcription = {"segments": [{"start": i * 15.0, "end": (i + 1) * 15.0, "text": f"Ideia {i}."} for i in range(20)]}

    selector.select_clips(transcription, settings={"previous_clip_fingerprints": [{"start": 0, "end": 30, "text": "Uma tese completa e independente."}]})
    assert selector.get_candidate_diagnostics()["previous_discarded_count"] == 1

    selector.select_clips(transcription, settings={"previous_clip_fingerprints": []})
    assert selector.get_candidate_diagnostics()["previous_discarded_count"] == 0
    assert selector.get_candidate_diagnostics()["final_count"] == 1


def test_candidate_origin_labels_remain_visible_after_deduplication(monkeypatch):
    selector = ClipSelector(target_duration=30, max_clips=15, min_duration=8, max_duration=180)
    primary = _clip(0, 30, "Tese primária completa.")
    primary["source"] = "gemini"
    monkeypatch.setattr(selector, "_select_with_gemini", lambda *args, **kwargs: [primary])
    monkeypatch.setattr(selector, "_select_with_nlp", lambda *args, **kwargs: [])
    monkeypatch.setattr(clip_selector_module, "annotate_clip_with_chapters", lambda clip, context: clip)
    transcription = {"segments": [{"start": i * 15.0, "end": (i + 1) * 15.0, "text": f"Ideia {i}."} for i in range(20)]}

    clips = selector.select_clips(transcription, settings={"ai_backend": "gemini", "gemini_api_key": "configured"})

    assert clips[0]["candidate_origin"] == "gemini_primary"
    assert clips[0]["candidate_origin_label"] == "Gemini — seleção primária"


def test_adaptive_expected_count_never_exceeds_selector_maximum():
    selector = ClipSelector(max_clips=9)
    sentences = [{"start": index * 60.0, "end": (index + 1) * 60.0, "text": "fala completa."} for index in range(200)]
    assert selector._expected_candidate_count(sentences) == 9
