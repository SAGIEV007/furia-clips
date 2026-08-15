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
    }


def test_long_transcript_uses_local_fallback_when_primary_pool_is_thin(monkeypatch):
    selector = ClipSelector(target_duration=30, max_clips=15, min_duration=8, max_duration=180)
    transcription = {
        "segments": [
            {"start": index * 15.0, "end": (index + 1) * 15.0, "text": f"Ideia completa número {index}."}
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
    assert clips
