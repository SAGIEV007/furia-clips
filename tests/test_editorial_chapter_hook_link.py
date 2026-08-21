from modules.editorial_chapters import annotate_clip_with_chapters


def test_clip_receives_nearest_hook_without_changing_timestamps():
    clip = {"start": 20.0, "end": 48.0, "duration": 28.0, "text": "Uma fala completa."}
    context = {
        "editorial_chapters": [],
        "hook_candidates": [
            {
                "start": 18.0,
                "end": 35.0,
                "family": "tese-provocativa",
                "hook_text": "A proposta muda o debate.",
                "score": 82,
                "payoff_confirmed": True,
                "payoff_signals": ["pergunta de consequência"],
                "visual_evidence_required": True,
                "visual_review_reason": "confirmar gráfico, pesquisa ou imagem mencionada",
                "needs_speaker_review": True,
                "audio_signal": {"available": True, "peak": 0.8},
            },
            {
                "start": 90.0,
                "end": 110.0,
                "family": "outro",
                "hook_text": "Outro trecho.",
                "score": 99,
                "payoff_confirmed": False,
            },
        ],
    }

    result = annotate_clip_with_chapters(clip, context)

    assert result["start"] == 20.0
    assert result["end"] == 48.0
    assert result["contextual_hook"]["family"] == "tese-provocativa"
    assert result["contextual_hook"]["hook_text"] == "A proposta muda o debate."
    assert result["contextual_hook"]["payoff_signals"] == ["pergunta de consequência"]
    assert result["contextual_hook"]["visual_evidence_required"] is True
    assert result["contextual_hook"]["visual_review_reason"] == "confirmar gráfico, pesquisa ou imagem mencionada"
    assert result["hook_distance_seconds"] == 0.0
    assert result["hook_review_required"] is True


def test_clip_without_context_keeps_legacy_defaults():
    result = annotate_clip_with_chapters({"start": 0, "end": 10}, None)

    assert result["contextual_hook"] is None
    assert result["hook_review_required"] is False


def test_clip_exposes_qa_boundary_basis_for_review():
    context = {
        "editorial_chapters": [{"id": "chapter-1", "index": 0, "start": 0.0, "end": 60.0, "end": 60.0, "label": "pergunta e resposta"}],
        "hook_candidates": [],
        "qa_candidates": [{
            "start": 10.0,
            "end": 40.0,
            "boundary_basis": "segunda_troca_de_locutor",
            "needs_speaker_review": True,
            "overlap_suspected": False,
        }],
    }
    result = annotate_clip_with_chapters({"start": 9.0, "end": 41.0}, context)

    assert result["qa_bridge"] is True
    assert result["qa_boundary_basis"] == "segunda_troca_de_locutor"
    assert result["qa_boundary_review_required"] is True
