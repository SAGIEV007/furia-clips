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
    assert all(clip["review_required"] is True for clip in clips)


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
    assert all(clip["review_required"] is True for clip in clips)



def _aligned_snapshot(*, trust_tier="owner", renan_speaking=True, block_start=0.0, block_end=18.0):
    return {
        "version": "test-snapshot",
        "default_account": "@renansantosmbl",
        "accounts": {"@renansantosmbl": {"platform": "youtube"}},
        "records": {
            "sources": [{"youtube_id": "test-source", "duration_s": block_end, "account": "@renansantosmbl"}],
            "blocks": [{
                "id": "block-1",
                "video_id": "test-source",
                "start_s": block_start,
                "end_s": block_end,
                "title": "Tese completa",
                "summary": TEXT,
                "renan_speaking": renan_speaking,
                "trust_tier": trust_tier,
                "risk_flags": [],
                "gate_warnings": [],
            }],
            "highlights": [{
                "id": "highlight-1",
                "block_id": "block-1",
                "video_id": "test-source",
                "start_s": block_start,
                "end_s": block_end,
            }],
        },
    }


def test_aligned_owner_campaign_hub_evidence_can_resolve_renan_identity():
    selector = ClipSelector(max_clips=3, min_duration=8, max_duration=60)
    clips = selector.select_clips(
        {"segments": [{"start": 0.0, "end": 18.0, "text": TEXT}]},
        settings={
            "ai_backend": "local",
            "editorial_focus": "renan_santos",
            "editorial_context": {"focus": "renan_santos"},
            "campaign_hub_account": "@renansantosmbl",
            "campaign_hub_snapshot": _aligned_snapshot(),
            "media_duration": 18.0,
        },
    )

    evidence_clips = [
        clip for clip in clips
        if (clip.get("campaign_hub_block") or {}).get("identity_evidence") == "campaign_hub_aligned_owner_or_allied"
    ]
    assert evidence_clips
    assert all(clip["speaker_identity_available"] is True for clip in evidence_clips)
    assert all(clip["speaker_identity_review_required"] is False for clip in evidence_clips)
    assert all(clip["speaker_identity_basis"] == "campaign_hub_aligned_owner_or_allied" for clip in evidence_clips)


def test_third_party_campaign_hub_evidence_does_not_resolve_renan_identity():
    selector = ClipSelector(max_clips=3, min_duration=8, max_duration=60)
    clips = selector.select_clips(
        {"segments": [{"start": 0.0, "end": 18.0, "text": TEXT}]},
        settings={
            "ai_backend": "local",
            "editorial_focus": "renan_santos",
            "editorial_context": {"focus": "renan_santos"},
            "campaign_hub_account": "@renansantosmbl",
            "campaign_hub_snapshot": _aligned_snapshot(trust_tier="third_party"),
            "media_duration": 18.0,
        },
    )

    evidence_clips = [clip for clip in clips if clip.get("campaign_hub_block")]
    assert evidence_clips
    assert all(clip["speaker_identity_available"] is False for clip in evidence_clips)
    assert all(clip["speaker_identity_review_required"] is True for clip in evidence_clips)


def test_snapshot_path_propagates_aligned_identity_evidence(tmp_path):
    import json

    snapshot_path = tmp_path / "campaign_hub.json"
    snapshot_path.write_text(json.dumps(_aligned_snapshot()), encoding="utf-8")
    selector = ClipSelector(max_clips=3, min_duration=8, max_duration=60)
    clips = selector.select_clips(
        {"segments": [{"start": 0.0, "end": 18.0, "text": TEXT}]},
        settings={
            "ai_backend": "local",
            "editorial_focus": "renan_santos",
            "editorial_context": {"focus": "renan_santos"},
            "campaign_hub_account": "@renansantosmbl",
            "campaign_hub_snapshot_path": str(snapshot_path),
            "media_duration": 18.0,
        },
    )

    evidence_clips = [
        clip for clip in clips
        if (clip.get("campaign_hub_block") or {}).get("identity_evidence") == "campaign_hub_aligned_owner_or_allied"
    ]
    assert evidence_clips
    assert all(clip["speaker_identity_available"] is True for clip in evidence_clips)
