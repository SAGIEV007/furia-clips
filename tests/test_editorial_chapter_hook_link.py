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
    assert result["hook_distance_seconds"] == 0.0
    assert result["hook_review_required"] is True


def test_clip_without_context_keeps_legacy_defaults():
    result = annotate_clip_with_chapters({"start": 0, "end": 10}, None)

    assert result["contextual_hook"] is None
    assert result["hook_review_required"] is False
