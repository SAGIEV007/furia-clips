from modules.campaign_hub_guidance import build_campaign_hub_guided_seeds
from modules.clip_selector import ClipSelector


def _snapshot():
    return {
        "version": "guidance-test-v1",
        "default_account": "@renansantosmbl",
        "records": {
            "sources": [{"id": "source-1", "youtube_id": "video-1", "duration_s": 100}],
            "blocks": [{
                "id": "block-1",
                "video_id": "source-1",
                "title": "Força coletiva",
                "summary": "A origem da mobilização do partido.",
                "trigger_question": "Por que vocês continuam juntos?",
                "topics": ["partido", "mobilização"],
                "start_s": 0,
                "end_s": 100,
                "renan_speaking": True,
                "trust_tier": "qa_gated",
            }],
            "highlights": [{
                "id": "highlight-1",
                "block_id": "block-1",
                "start_s": 20,
                "end_s": 24,
                "text": "Nós somos um exército indestrutível.",
                "reason": "força coletiva",
            }],
        },
    }


def _sentences():
    return [
        {"start": 18, "end": 20, "text": "Por que vocês continuam juntos?", "speaker_turn_valid": True},
        {
            "start": 20,
            "end": 35,
            "text": "Nós somos um exército indestrutível e seguimos unidos em qualquer cenário político.",
            "speaker_turn_valid": True,
        },
    ]


def test_guided_seed_maps_downloaded_block_timeline_and_preserves_provenance():
    seeds = build_campaign_hub_guided_seeds(_sentences(), _snapshot(), account="@renansantosmbl")

    assert len(seeds) == 1
    seed = seeds[0]
    assert seed["seed_id"] == "highlight-1"
    assert seed["start"] == 20.0
    assert seed["end"] == 24.0
    assert seed["timeline_mapping"] == "downloaded_block_timeline"
    assert seed["renan_speaking"] is True
    assert seed["provenance"]["block_id"] == "block-1"


def test_guided_proposal_expands_seed_to_question_and_payoff():
    selector = ClipSelector(min_duration=8, max_duration=180, max_clips=5)
    proposals = selector._select_with_campaign_hub_guidance(
        _sentences(),
        {"campaign_hub_snapshot": _snapshot(), "campaign_hub_account": "@renansantosmbl"},
    )

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal["source"] == "campaign_hub_guided"
    assert proposal["start"] == 18.0
    assert proposal["end"] == 35.0
    assert proposal["campaign_hub"]["highlight_id"] == "highlight-1"
    assert proposal["campaign_hub"]["gates"]["context_complete"] is True
    assert proposal["campaign_hub"]["gates"]["speaker_gate"] == "pass"
    assert proposal["review_required"] is False


def test_missing_snapshot_keeps_legacy_path_available():
    selector = ClipSelector(max_clips=5)
    assert selector._select_with_campaign_hub_guidance(_sentences(), {}) == []


def test_public_selector_marks_guided_origin_and_keeps_provenance():
    selector = ClipSelector(min_duration=8, max_duration=180, max_clips=5)
    clips = selector.select_clips(
        {"segments": _sentences()},
        settings={
            "campaign_hub_snapshot": _snapshot(),
            "campaign_hub_account": "@renansantosmbl",
            "editorial_context": {},
        },
    )

    guided = [clip for clip in clips if clip.get("source") == "campaign_hub_guided"]
    assert guided
    assert guided[0]["candidate_origin"] == "campaign_hub_guided"
    assert guided[0]["campaign_hub"]["provenance"]["highlight_id"] == "highlight-1"


def test_real_campaign_hub_block_shape_becomes_auditable_seeds():
    snapshot = {
        "version": "chub-real-shape-v1",
        "default_account": "@renansantosmbl",
        "accounts": {"@renansantosmbl": {"platform": "youtube"}},
        "records": {
            "sources": [{
                "id": "video-internal",
                "youtubeId": "gVrW6a5e6Tc",
                "durationS": 3193,
                "account": "@renansantosmbl",
            }],
            "blocks": [{
                "id": "70358a7d-7848-48d1-8d3d-5ef7c61c149d",
                "videoId": "gVrW6a5e6Tc",
                "startS": 279.96,
                "endS": 578.16,
                "title": "Missão propõe leis penais duras e retomada de territórios contra facções",
                "summary": "Renan propõe endurecer as leis penais e retomar territórios.",
                "triggerQuestion": "Como o Missão pretende combater o crime organizado no Brasil?",
                "topics": ["Crime organizado", "Segurança Pública"],
                "densityRank": 98,
                "selfContainedRank": 71,
                "renanSpeaking": True,
                "riskFlags": [],
                "gateWarnings": ["start_continuation"],
                "trustTier": "third_party",
                "highlights": [{
                    "sentenceIdx": 128,
                    "startS": 434.76,
                    "endS": 437.56,
                    "text": "Tem partes inteiras do Rio de Janeiro que foram tomados pelo crime organizado.",
                }],
            }],
        },
    }

    seeds = build_campaign_hub_guided_seeds([], snapshot, account="@renansantosmbl")

    assert len(seeds) == 1
    seed = seeds[0]
    assert seed["seed_id"] == "70358a7d-7848-48d1-8d3d-5ef7c61c149d-sentence-128"
    assert seed["start"] == 434.76
    assert seed["end"] == 437.56
    assert seed["timeline_mapping"] == "source_timeline"
    assert seed["highlight_id"] == "sentence-128"
    assert seed["renan_speaking"] is True
    assert seed["speaker_gate"] == "pass"
    assert seed["gate_warnings"] == ["start_continuation"]
    assert seed["provenance"]["sentence_idx"] == 128
    assert seed["provenance"]["source_ref"] == "gVrW6a5e6Tc"


def test_third_party_campaign_hub_seed_remains_review_required():
    selector = ClipSelector(min_duration=8, max_duration=180, max_clips=5)
    proposal = selector._build_campaign_hub_proposal(
        [
            {
                "start": 430.0,
                "end": 434.76,
                "text": "Como o Missão pretende combater o crime organizado no Brasil?",
                "speaker_turn_valid": True,
            },
            {
                "start": 434.76,
                "end": 452.0,
                "text": "Tem partes inteiras do Rio de Janeiro que foram tomadas pelo crime organizado e precisam ser retomadas pelo Estado.",
                "speaker_turn_valid": True,
            },
        ],
        {
            "seed_id": "real-block-sentence-128",
            "source_kind": "highlight",
            "start": 434.76,
            "end": 437.56,
            "confidence": 0.82,
            "density_rank": 98,
            "self_contained_rank": 71,
            "renan_speaking": True,
            "trust_tier": "third_party",
            "gate_warnings": ["start_continuation"],
            "risk_flags": [],
        },
    )

    assert proposal is not None
    assert proposal["campaign_hub"]["gates"]["provenance_gate"] == "review_required"
    assert proposal["campaign_hub"]["gates"]["warning_gate"] == "review_required"
    assert proposal["review_required"] is True
