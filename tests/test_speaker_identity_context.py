from modules.clip_selector import ClipSelector


TEXT = (
    "A proposta revela o problema com clareza, apresenta a consequência concreta "
    "e termina com uma resposta completa para o público."
)


def _run_selector(*, focus="renan_santos", speaker=None):
    segment = {"start": 0.0, "end": 18.0, "text": TEXT}
    if speaker is not None:
        segment["speaker"] = speaker
        segment["speaker_confidence"] = 0.92
    selector = ClipSelector(max_clips=3, min_duration=8, max_duration=60)
    clips = selector.select_clips(
        {"segments": [segment]},
        settings={
            "ai_backend": "local",
            "editorial_focus": focus,
            "editorial_context": {"focus": focus} if focus else {},
        },
    )
    return clips


def test_renan_first_without_speaker_identity_requires_review():
    clips = _run_selector(focus="renan_santos")

    assert clips
    assert all(clip["speaker_identity_required"] is True for clip in clips)
    assert all(clip["speaker_identity_available"] is False for clip in clips)
    assert all(clip["speaker_identity_review_required"] is True for clip in clips)
    assert all(clip["context_complete"] is False for clip in clips)
    assert all(clip["qa_bridge"] is False for clip in clips)


def test_renan_first_with_labeled_speaker_can_pass_identity_gate():
    clips = _run_selector(focus="renan_santos", speaker="Renan")

    assert clips
    assert all(clip["speaker_identity_required"] is True for clip in clips)
    assert all(clip["speaker_identity_available"] is True for clip in clips)
    assert all(clip["speaker_identity_review_required"] is False for clip in clips)
    assert all(clip["context_complete"] is True for clip in clips)


def test_generic_mode_does_not_require_speaker_identity():
    clips = _run_selector(focus="generic_political")

    assert clips
    assert all(clip["speaker_identity_required"] is False for clip in clips)
    assert all(clip["speaker_identity_review_required"] is False for clip in clips)
    assert all(clip["context_complete"] is True for clip in clips)


def test_auto_focus_with_renan_profile_requires_identity_gate():
    selector = ClipSelector(max_clips=3, min_duration=8, max_duration=60)
    clips = selector.select_clips(
        {"segments": [{"start": 0.0, "end": 18.0, "text": TEXT}]},
        settings={
            "ai_backend": "local",
            "editorial_focus": "auto",
            "editorial_profile": "renan_santos_politics",
            "editorial_context": {"focus": "generic_political"},
        },
    )

    assert clips
    assert all(clip["speaker_identity_required"] is True for clip in clips)
    assert all(clip["speaker_identity_review_required"] is True for clip in clips)
    assert all(clip["context_complete"] is False for clip in clips)
