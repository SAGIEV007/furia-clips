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


B354_BLOCK_ID = "b3545938-e3a5-4287-82b1-5f7dcdc218c3"
B354_MP4_DURATION_S = 549.449
B354_LIVE_DURATION_S = 11230.0


def _b354_snapshot():
    """Real shape of the b354 case, confirmed against the authorized Acervo.

    The block was cut out of a long live: the snapshot describes the whole
    `57nyfP9IDW4` source, while the editor works on the downloaded block MP4.
    """
    return {
        "version": "b354-alignment-v1",
        "default_account": "@renansantosmbl",
        "accounts": {"@renansantosmbl": {"platform": "youtube"}},
        "records": {
            "sources": [{
                "id": "57nyfP9IDW4",
                "youtubeId": "57nyfP9IDW4",
                "durationS": B354_LIVE_DURATION_S,
                "account": "@renansantosmbl",
            }],
            "blocks": [{
                "id": B354_BLOCK_ID,
                "videoId": "57nyfP9IDW4",
                "startS": 6142.56,
                "endS": 6692.0,
                "title": "Kim transforma a campanha de Renan em guerra e convoca 45 dias de mobilização",
                "triggerQuestion": "Como Kim apresenta a campanha de Renan e mobiliza os apoiadores?",
                # The block is about Renan, but Kim is the one speaking.
                "renanSpeaking": False,
                "riskFlags": ["juridico_sensivel", "linguagem_ofensiva", "ataque_pessoal"],
                "trustTier": "owner",
                "densityRank": 98,
                "selfContainedRank": 90,
                "highlights": [
                    {"sentenceIdx": 1350, "startS": 6289.36, "endS": 6293.36,
                     "text": "Nós somos um exército indestrutível."},
                    {"sentenceIdx": 1367, "startS": 6365.80, "endS": 6370.96,
                     "text": "Nós fundamos o nosso partido para representar as nossas próprias ideias."},
                    {"sentenceIdx": 1426, "startS": 6631.04, "endS": 6637.76,
                     "text": "Se a gente não se empenhar nesses 45 dias, a gente vai pagar pelos próximos 20 anos."},
                ],
            }],
        },
    }


def _b354_local_sentences():
    """Transcript of the downloaded block MP4: local timeline, starting at zero."""
    return [
        {"start": 140.0, "end": 146.8, "text": "Eu quero dizer uma coisa para vocês que estão aqui hoje.", "speaker_turn_valid": True},
        {"start": 146.8, "end": 152.4, "text": "Nós somos um exército indestrutível e ninguém vai nos parar.", "speaker_turn_valid": True},
        {"start": 218.0, "end": 223.24, "text": "Por que vocês fundaram um partido novo?", "speaker_turn_valid": True},
        {"start": 223.24, "end": 231.0, "text": "Nós fundamos o nosso partido para representar as nossas próprias ideias.", "speaker_turn_valid": True},
        {"start": 482.0, "end": 488.48, "text": "Agora eu preciso da atenção de todos vocês.", "speaker_turn_valid": True},
        {"start": 488.48, "end": 497.0, "text": "São 45 dias de esforço que vão definir os próximos 20 anos deste país.", "speaker_turn_valid": True},
    ]


def test_downloaded_block_media_maps_seeds_into_the_local_transcript():
    """The measured MP4 length is what tells the seeds which timeline they live on."""
    seeds = build_campaign_hub_guided_seeds(
        _b354_local_sentences(),
        _b354_snapshot(),
        account="@renansantosmbl",
        media_duration=B354_MP4_DURATION_S,
    )

    assert len(seeds) == 3
    assert [seed["timeline_mapping"] for seed in seeds] == ["downloaded_block_timeline"] * 3
    # The three reference highlights of the b354 baseline, on the local timeline.
    assert [seed["start"] for seed in seeds] == [146.8, 223.24, 488.48]
    assert [seed["end"] for seed in seeds] == [150.8, 228.4, 495.2]
    # The absolute coordinates stay recorded so the mapping remains auditable.
    assert seeds[0]["absolute_start"] == 6289.36
    assert seeds[0]["renan_speaking"] is False
    assert seeds[0]["speaker_gate"] == "review_required"


def test_declared_source_duration_alone_cannot_place_a_downloaded_block():
    """Without a measured duration the snapshot only knows the long source."""
    seeds = build_campaign_hub_guided_seeds(
        _b354_local_sentences(), _b354_snapshot(), account="@renansantosmbl"
    )

    assert [seed["timeline_mapping"] for seed in seeds] == ["source_timeline"] * 3
    assert seeds[0]["start"] == 6289.36


def test_full_length_media_keeps_the_absolute_timeline():
    """Cutting the whole live keeps candidates and seeds on the same absolute axis."""
    seeds = build_campaign_hub_guided_seeds(
        [], _b354_snapshot(), account="@renansantosmbl", media_duration=B354_LIVE_DURATION_S
    )

    assert [seed["timeline_mapping"] for seed in seeds] == ["source_timeline"] * 3
    assert seeds[0]["start"] == 6289.36


def test_seed_far_outside_the_transcript_produces_no_proposal():
    """An unmapped seed must not be snapped onto an unrelated sentence.

    Anchoring it would publish the wrong window carrying Campaign Hub
    provenance, and every distant seed would collapse onto the same edge
    sentence, turning three different highlights into one repeated proposal.
    """
    selector = ClipSelector(min_duration=8, max_duration=180, max_clips=5)
    proposals = selector._select_with_campaign_hub_guidance(
        _b354_local_sentences(),
        {"campaign_hub_snapshot": _b354_snapshot(), "campaign_hub_account": "@renansantosmbl"},
    )

    assert proposals == []


def test_guided_proposals_recover_the_three_b354_highlights():
    """End to end: measured media in settings turns the seeds into real proposals."""
    selector = ClipSelector(min_duration=8, max_duration=180, max_clips=5)
    proposals = selector._select_with_campaign_hub_guidance(
        _b354_local_sentences(),
        {
            "campaign_hub_snapshot": _b354_snapshot(),
            "campaign_hub_account": "@renansantosmbl",
            "media_duration": B354_MP4_DURATION_S,
        },
    )

    assert len(proposals) == 3
    # Each proposal covers its highlight and opens earlier, because the expansion
    # recovers the antecedent instead of starting in the middle of the answer.
    for highlight_start, highlight_end in ((146.8, 150.8), (223.24, 228.4), (488.48, 495.2)):
        covering = [
            proposal for proposal in proposals
            if proposal["start"] <= highlight_start and proposal["end"] >= highlight_end
        ]
        assert len(covering) == 1, f"destaque {highlight_start}-{highlight_end} sem proposta única"
        assert covering[0]["start"] < highlight_start
    # Kim speaks in this block, so no proposal may be released without review.
    assert all(proposal["review_required"] is True for proposal in proposals)
    assert all(proposal["source"] == "campaign_hub_guided" for proposal in proposals)
    assert {proposal["campaign_hub"]["provenance"]["block_id"] for proposal in proposals} == {B354_BLOCK_ID}


def _snapshot_with_ignored_region():
    snapshot = _b354_snapshot()
    snapshot["records"]["ignored_regions"] = [{
        "video_id": "57nyfP9IDW4",
        "start_s": 300.0,
        "end_s": 400.0,
        "reason": "Transcrição ininteligível e isolada.",
        "provenance": "model_labelled",
    }]
    return snapshot


def test_candidates_over_labelled_non_content_are_dropped():
    """A stretch the Acervo labelled as unusable must not consume a candidate slot."""
    selector = ClipSelector()
    settings = {"campaign_hub_snapshot": _snapshot_with_ignored_region()}
    clips = [
        {"start": 310.0, "end": 350.0, "text": "dentro da região ignorada"},
        {"start": 100.0, "end": 140.0, "text": "conteúdo normal"},
        # Touching the edge is not enough: an idea may start right after the
        # unusable stretch, so only a dominant overlap disqualifies a candidate.
        {"start": 380.0, "end": 460.0, "text": "começa na borda e segue para conteúdo"},
    ]

    kept = selector._drop_labelled_non_content(clips, settings)

    assert [clip["start"] for clip in kept] == [100.0, 380.0]
    assert selector.get_candidate_diagnostics()["labelled_non_content_dropped"] == 1


def test_non_content_filter_is_inert_without_a_snapshot():
    """Offline-first: no authorized snapshot means nothing is filtered."""
    selector = ClipSelector()
    clips = [{"start": 310.0, "end": 350.0, "text": "sem snapshot"}]

    assert selector._drop_labelled_non_content(clips, {}) == clips
    assert selector._drop_labelled_non_content(clips, {"campaign_hub_snapshot": {}}) == clips


def test_media_duration_is_read_from_the_probed_job_settings():
    selector = ClipSelector()

    assert selector._media_duration({"media_duration": 549.449}) == 549.449
    assert selector._media_duration({"video_duration": 549.449}) == 549.449
    assert selector._media_duration({"media_duration": 0}) is None
    assert selector._media_duration({"media_duration": "indefinido"}) is None
    assert selector._media_duration({}) is None
    assert selector._media_duration(None) is None


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


def _snapshot_for_evidence():
    snapshot = _b354_snapshot()
    snapshot["records"]["blocks"][0].update({
        "start_s": 0.0,
        "end_s": 600.0,
        "speakers_note": "Todas as linhas atribuídas à (fala 1), sem identificação nominal.",
        "summary": "Kim convoca 45 dias de mobilização.",
    })
    return snapshot


def test_every_candidate_inherits_the_block_context_it_sits_in():
    """A candidate must never reach the reviewer without saying who is speaking."""
    selector = ClipSelector()
    clips = [{"start": 100.0, "end": 160.0, "text": "trecho dentro do bloco"}]

    selector._attach_block_evidence(clips, {"campaign_hub_snapshot": _snapshot_for_evidence()})

    block = clips[0]["campaign_hub_block"]
    assert block["block_id"] == B354_BLOCK_ID
    assert block["trigger_question"]
    assert block["density_rank"] == 98
    assert block["speakers_note"]
    # Kim speaks in this block, so the candidate is explicitly not Renan.
    assert block["renan_speaking"] is False
    assert block["speaker_status"] == "terceiro_ou_indeterminado"
    # Evidence only: the block never approves the clip on its own.
    assert block["evidence_only"] is True
    assert clips[0]["review_required"] is True
    assert any("locutor" in reason for reason in clips[0]["review_reasons"])
    assert any("riscos" in reason for reason in clips[0]["review_reasons"])


def test_confirmed_renan_block_does_not_add_a_speaker_review_reason():
    selector = ClipSelector()
    snapshot = _snapshot_for_evidence()
    snapshot["records"]["blocks"][0]["renan_speaking"] = True
    snapshot["records"]["blocks"][0]["risk_flags"] = []
    clips = [{"start": 100.0, "end": 160.0, "text": "Renan fala"}]

    selector._attach_block_evidence(clips, {"campaign_hub_snapshot": snapshot})

    assert clips[0]["campaign_hub_block"]["speaker_status"] == "renan_confirmado"
    assert "review_reasons" not in clips[0]


def test_candidate_outside_every_block_receives_no_invented_context():
    selector = ClipSelector()
    clips = [{"start": 2000.0, "end": 2060.0, "text": "fora de qualquer bloco"}]

    selector._attach_block_evidence(clips, {"campaign_hub_snapshot": _snapshot_for_evidence()})

    assert "campaign_hub_block" not in clips[0]


def test_block_evidence_is_inert_without_a_snapshot():
    selector = ClipSelector()
    clips = [{"start": 100.0, "end": 160.0, "text": "sem snapshot"}]

    assert selector._attach_block_evidence(clips, {}) == clips
    assert "campaign_hub_block" not in clips[0]


def test_selection_diagnostics_expose_stage_counts_without_changing_output():
    selector = ClipSelector(min_duration=8, max_duration=180, max_clips=5)
    clips = selector.select_clips(
        {"segments": _sentences()},
        settings={
            "campaign_hub_snapshot": _snapshot(),
            "campaign_hub_account": "@renansantosmbl",
            "editorial_context": {},
        },
    )

    diagnostics = selector.get_candidate_diagnostics()
    stages = diagnostics["stage_counts"]
    assert {"primary_pool", "post_fallback", "after_non_content_filter", "after_context_enrichment", "pre_overlap", "post_overlap", "final"} <= set(stages)
    assert stages["final"]["count"] == len(clips)
    assert stages["post_overlap"]["count"] >= stages["final"]["count"]
    assert stages["final"]["campaign_hub_guided"] + stages["final"]["campaign_hub_block_evidence"] >= 1


def test_renan_first_excludes_guided_proposals_without_positive_speaker_evidence():
    snapshot = _snapshot()
    snapshot["records"]["blocks"][0]["renan_speaking"] = False
    selector = ClipSelector(min_duration=8, max_duration=180, max_clips=5)
    clips = selector.select_clips(
        {"segments": _sentences()},
        settings={
            "campaign_hub_snapshot": snapshot,
            "campaign_hub_account": "@renansantosmbl",
            "editorial_focus": "renan_santos_politics",
            "editorial_profile": "renan_santos_politics",
            "channel_context": "Renan Santos / MBL",
            "editorial_context": {"focus": "renan_santos_politics"},
        },
    )

    diagnostics = selector.get_candidate_diagnostics()
    assert not any(clip.get("source") == "campaign_hub_guided" for clip in clips)
    assert diagnostics["campaign_hub_guided_filtered_by_speaker"] >= 1
