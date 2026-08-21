from modules.clip_selector import ClipSelector
from modules.editorial_context import analyze_transcript_context
from modules.editorial_ranker import EditorialRanker


def test_context_pipeline_without_gemini_preserves_editorial_evidence():
    transcription = {
        "segments": [
            {"start": 0.0, "end": 3.0, "text": "Você acredita que essa operação foi justa?", "speaker": "Entrevistador"},
            {"start": 3.2, "end": 8.5, "text": "Não, porque expuseram dados sigilosos da minha família.", "speaker": "Renan", "speaker_confidence": 0.9},
            {"start": 8.7, "end": 13.0, "text": "Isso atingiu pessoas que não tinham nada a ver com o caso.", "speaker": "Renan", "speaker_confidence": 0.9},
            {"start": 13.2, "end": 17.0, "text": "Por isso essa operação precisa ser analisada com responsabilidade.", "speaker": "Renan", "speaker_confidence": 0.9},
        ],
        "coverage": {"status": "complete", "segment_count": 4, "semantic_identity_verified": True},
    }
    context = analyze_transcript_context(transcription, focus="generic", campaign_hub_snapshot={})
    assert context["qa_candidates"]

    selector = ClipSelector(target_duration=20, max_clips=5, min_duration=5, max_duration=30)
    clips = selector.select_clips(
        transcription,
        settings={"ai_backend": "auto", "gemini_api_key": "", "editorial_context": context},
    )
    assert clips
    assert any(clip.get("editorial_chapter_available") for clip in clips)

    ranked = EditorialRanker(campaign_hub_snapshot={}).rank_clips(clips)
    assert ranked
    assert all("editorial_potential_score" in clip for clip in ranked)
    assert any((clip.get("factors") or {}).get("qa_boundary") is not None for clip in ranked)
    assert any(clip.get("qa_boundary_basis") for clip in ranked)
    assert any((clip.get("review_flags") or {}).get("qa_boundary_basis") for clip in ranked)
