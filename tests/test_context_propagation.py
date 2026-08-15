import modules.clip_selector as clip_selector_module
from modules.clip_selector import ClipSelector


def test_selector_passes_contextual_hooks_to_final_clip_annotation(monkeypatch):
    selector = ClipSelector(target_duration=30, max_clips=5, min_duration=8, max_duration=180)
    captured = {}

    monkeypatch.setattr(
        selector,
        "_select_with_nlp",
        lambda *args, **kwargs: [{
            "start": 0.0,
            "end": 24.0,
            "duration": 24.0,
            "text": "A proposta concreta muda o debate e termina com uma resposta.",
            "source": "nlp",
        }],
    )

    def annotate(clip, context):
        captured["context"] = context
        return clip

    monkeypatch.setattr(clip_selector_module, "annotate_clip_with_chapters", annotate)

    clips = selector.select_clips(
        {"segments": [{"start": 0.0, "end": 24.0, "text": "A proposta concreta muda o debate e termina com uma resposta."}]},
        settings={
            "ai_backend": "auto",
            "gemini_api_key": "",
            "editorial_context": {
                "hook_candidates": [{"family": "tese-provocativa", "hook_text": "A proposta concreta muda o debate."}],
                "editorial_chapters": [],
            },
        },
    )

    assert clips
    assert captured["context"]["hook_candidates"][0]["family"] == "tese-provocativa"


def test_partial_transcript_context_reaches_clip_review_contract(monkeypatch):
    selector = ClipSelector(target_duration=30, max_clips=5, min_duration=8, max_duration=180)
    monkeypatch.setattr(
        selector,
        "_select_with_nlp",
        lambda *args, **kwargs: [{
            "start": 10.0,
            "end": 34.0,
            "duration": 24.0,
            "text": "A proposta concreta muda o debate e termina com uma resposta.",
            "source": "nlp",
        }],
    )
    clips = selector.select_clips(
        {"segments": [{"start": 10.0, "end": 34.0, "text": "A proposta concreta muda o debate e termina com uma resposta."}]},
        settings={
            "ai_backend": "auto",
            "gemini_api_key": "",
            "editorial_context": {
                "hook_candidates": [],
                "editorial_chapters": [],
                "transcription_quality": {"status": "partial", "review_required": True},
            },
        },
    )
    assert clips[0]["transcription_review_required"] is True
    assert clips[0]["transcription_coverage_status"] == "partial"
    assert "cobertura parcial" in clips[0]["transcription_review_reason"]
