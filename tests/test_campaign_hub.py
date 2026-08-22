from modules.campaign_hub import (
    merge_acervo_seed_candidates,
    build_acervo_alignment,
    build_audience_fit,
    build_performance_prior,
    classify_hook,
    classify_hook_details,
    normalize_snapshot,
    snapshot_status,
)
from modules.editorial_context import detect_hook_candidates
from modules.editorial_ranker import EditorialRanker


def _snapshot():
    return normalize_snapshot({
        "version": "test",
        "default_account": "@renansantosmbl",
        "accounts": {
            "@renansantosmbl": {
                "platform": "instagram",
                "hook_observations": [
                    {"hook": "tese-provocativa", "ratio": 1.0},
                    {"hook": "tese-provocativa", "ratio": 1.2},
                    {"hook": "tese-provocativa", "ratio": 1.4},
                    {"hook": "news-peg", "ratio": 8.0},
                ],
            }
        },
    })


def test_snapshot_status_reports_bounded_local_metadata(tmp_path):
    snapshot_path = tmp_path / "profile.json"
    snapshot_path.write_text(
        '{"version":"test-v1","collected_at":"2026-08-15T12:00:00Z","default_account":"@renansantosmbl","accounts":{"@renansantosmbl":{"hook_observations":[{"hook":"news-peg","ratio":2.0}],"examples":[{}],"cohorts":[{}]}}}',
        encoding="utf-8",
    )

    status = snapshot_status(str(snapshot_path))

    assert status["available"] is True
    assert status["read_only"] is True
    assert status["auto_reload_on_next_analysis"] is True
    assert status["accounts"]["@renansantosmbl"] == {
        "hook_observations": 1,
        "examples": 1,
        "cohorts": 1,
        "acervo_blocks": 0,
        "pauta_candidates": 0,
        "audience_priors": 0,
        "entity_priors": 0,
    }


def test_acervo_block_aligns_only_same_source_and_overlapping_interval():
    snapshot = normalize_snapshot({
        "default_account": "@renansantosmbl",
        "accounts": {
            "@renansantosmbl": {
                "acervo_blocks": [{
                    "id": "block-1",
                    "contentClass": "fala",
                    "title": "Segurança pública precisa de resposta concreta",
                    "summary": "A proposta trata de segurança pública e combate ao crime organizado.",
                    "startS": 100,
                    "endS": 170,
                    "densityRank": 95,
                    "selfContainedRank": 90,
                    "trustTier": "owner",
                    "video": {"youtubeId": "AbCdEfGhI12", "title": "Fonte de teste"},
                    "highlights": [{"startS": 120, "endS": 132, "text": "A resposta precisa ser concreta.", "reason": "tese"}],
                }],
            },
        },
    })
    aligned = build_acervo_alignment(
        "A resposta para a segurança pública precisa ser concreta.",
        118,
        140,
        source_id="AbCdEfGhI12",
        account="@renansantosmbl",
        snapshot=snapshot,
    )
    assert aligned["available"] is True
    assert aligned["status"] == "aligned_same_source"
    assert aligned["block_id"] == "block-1"
    assert 50 < aligned["signal"] <= 58

    wrong_source = build_acervo_alignment(
        "A resposta para a segurança pública precisa ser concreta.",
        118,
        140,
        source_id="ZzYyXxWwVvU",
        account="@renansantosmbl",
        snapshot=snapshot,
    )
    assert wrong_source["available"] is False
    assert wrong_source["status"] == "source_has_no_overlapping_block"


def test_rich_snapshot_status_reports_blocks_without_hook_priors(tmp_path):
    snapshot_path = tmp_path / "rich.json"
    snapshot_path.write_text(
        '{"version":"rich-v1","accounts":{"@renansantosmbl":{"acervo_blocks":[{"id":"b","startS":1,"endS":4,"video":{"youtubeId":"AbCdEfGhI12"}}],"audience_priors":[{"segment":"BR","signal":54,"sampleCount":12}]}}}',
        encoding="utf-8",
    )
    status = snapshot_status(str(snapshot_path))
    assert status["available"] is True
    assert status["rich_context_available"] is True
    assert status["total_acervo_blocks"] == 1
    assert status["total_audience_priors"] == 1


def test_audience_prior_requires_explicit_segment_and_sample():
    snapshot = normalize_snapshot({
        "accounts": {
            "@renansantosmbl": {
                "audience_priors": [{"segment": "BR", "category": "segurança pública", "signal": 55, "sampleCount": 12}],
            },
        },
    })
    absent = build_audience_fit("segurança pública", account="@renansantosmbl", snapshot=snapshot)
    assert absent["available"] is False
    assert absent["status"] == "segment_not_requested"
    available = build_audience_fit("segurança pública", account="@renansantosmbl", snapshot=snapshot, segment="BR")
    assert available["available"] is True
    assert available["review_required"] is True


def test_hook_candidates_expose_timestamped_payoff_and_selected_account_prior():
    snapshot = normalize_snapshot({
        "default_account": "@renansantosmbl",
        "accounts": {
            "@renansantosmbl": {
                "hook_observations": [
                    {"hook": "desafio-ao-espectador", "ratio": 1.0},
                    {"hook": "desafio-ao-espectador", "ratio": 1.1},
                    {"hook": "desafio-ao-espectador", "ratio": 1.2},
                ],
            },
            "@renansantosreserva": {
                "hook_observations": [
                    {"hook": "desafio-ao-espectador", "ratio": 3.0},
                    {"hook": "desafio-ao-espectador", "ratio": 3.1},
                    {"hook": "desafio-ao-espectador", "ratio": 3.2},
                ],
            },
        },
    })
    candidates = detect_hook_candidates([
        {"start": 4, "end": 7, "text": "Presta atenção: qual é o problema?"},
        {"start": 7, "end": 14, "text": "A resposta começa nos dados da cidade."},
        {"start": 14, "end": 22, "text": "Por isso, a solução precisa ser concreta."},
    ], snapshot=snapshot, account="@renansantosreserva", limit=3)

    assert candidates
    top = candidates[0]
    assert top["family"] == "desafio-ao-espectador"
    assert top["payoff_confirmed"] is True
    assert top["start"] <= 4
    assert top["end"] >= 22
    assert top["campaign_hub_prior"]["account"] == "@renansantosreserva"
    assert top["campaign_hub_prior"]["available"] is True


def test_hook_detector_rejects_setup_chatter_and_recovers_fragmented_question():
    setup_candidates = detect_hook_candidates([
        {"start": 0, "end": 3, "text": "Quem montou a câmera?"},
        {"start": 3, "end": 6, "text": "Diferente como púlpito?"},
        {"start": 6, "end": 12, "text": "Agora vamos falar da proposta concreta."},
    ], limit=3)

    assert setup_candidates
    assert all("câmera" not in item["hook_text"].lower() for item in setup_candidates[:2])

    boundary_candidates = detect_hook_candidates([
        {"start": 20, "end": 23, "text": "A discussão é de"},
        {"start": 23, "end": 28, "text": "qual é a proposta concreta?"},
        {"start": 28, "end": 36, "text": "Por isso, a resposta precisa ser objetiva."},
    ], limit=3)
    fragmented = next(item for item in boundary_candidates if "proposta concreta" in item["hook_text"].lower())
    assert fragmented["start"] == 18.5
    assert fragmented["payoff_confirmed"] is True


def test_hook_detector_recognizes_consequence_question_and_repeated_thesis_closure():
    consequence = detect_hook_candidates([
        {"start": 10, "end": 15, "text": "Eles querem transformar o debate numa guerra."},
        {"start": 15, "end": 22, "text": "Que tipo de sociedade a gente vai construir com isso?"},
        {"start": 22, "end": 29, "text": "Isso é bom só para quem ganha dinheiro com conflito."},
    ], limit=3)
    assert consequence
    assert consequence[0]["payoff_confirmed"] is True
    assert "pergunta de consequência" in consequence[0]["payoff_signals"]

    repeated = detect_hook_candidates([
        {"start": 30, "end": 36, "text": "Esse homem é um patrimônio brasileiro."},
        {"start": 36, "end": 43, "text": "Ele é um patrimônio brasileiro, esse cara."},
    ], limit=3)
    repeated_with_closure = next(item for item in repeated if "repetição deliberada da tese no fechamento" in item["payoff_signals"])
    assert repeated_with_closure["payoff_confirmed"] is True


def test_hook_detector_marks_visual_evidence_that_requires_video_review():
    candidates = detect_hook_candidates([
        {"start": 8, "end": 14, "text": "Olha esse gráfico do Google Trends, eu ultrapassei o candidato."},
        {"start": 14, "end": 22, "text": "Isso muda a leitura da eleição e mostra uma tendência concreta."},
    ], limit=2)

    assert candidates
    visual = candidates[0]
    assert visual["visual_evidence_required"] is True
    assert visual["needs_visual_review"] is True
    assert visual["visual_review_reason"]
    assert "evidência visual citada" in visual["evidence"]


def test_hook_detector_uses_existing_energy_profile_as_explainable_signal():
    candidates = detect_hook_candidates([
        {"start": 10, "end": 14, "text": "Vamos apresentar a proposta concreta."},
        {"start": 14, "end": 21, "text": "Por isso, a resposta começa agora."},
    ], energy_profile=[
        {"time": 0, "energy_normalized": 0.20},
        {"time": 10, "energy_normalized": 0.95},
        {"time": 11, "energy_normalized": 0.90},
        {"time": 14, "energy_normalized": 0.88},
    ], limit=2)

    assert candidates
    assert candidates[0]["audio_signal"]["available"] is True
    assert candidates[0]["audio_signal"]["peak"] >= 0.88
    assert "energia" in candidates[0]["reason"]


def test_hook_detector_suppresses_semantically_repeated_openings():
    candidates = detect_hook_candidates([
        {"start": 10, "end": 16, "text": "Vamos defender a proposta concreta para segurança pública."},
        {"start": 16, "end": 25, "text": "Por isso, a resposta precisa ser objetiva."},
        {"start": 100, "end": 106, "text": "Vamos defender a proposta concreta para segurança pública."},
        {"start": 106, "end": 115, "text": "Por isso, a resposta precisa ser objetiva."},
    ], limit=5)

    repeated = [item for item in candidates if "proposta concreta" in item["hook_text"].lower()]
    assert len(repeated) == 1


def test_qa_candidates_explain_speaker_boundary_and_review_need():
    from modules.editorial_context import analyze_transcript_context

    with_speaker_change = analyze_transcript_context({
        "segments": [
            {"start": 0, "end": 4, "end": 4, "text": "Qual é a proposta?", "speaker": "entrevistador"},
            {"start": 4, "end": 12, "text": "A proposta é reduzir o desperdício.", "speaker": "renan"},
        ]
    })
    assert with_speaker_change["qa_candidates"]
    assert with_speaker_change["qa_candidates"][0]["speaker_boundary"] is True
    assert with_speaker_change["qa_candidates"][0]["boundary_basis"] == "mudança_de_locutor"
    assert with_speaker_change["qa_candidates"][0]["needs_speaker_review"] is False

    without_speaker_change = analyze_transcript_context({
        "segments": [
            {"start": 0, "end": 4, "text": "Qual é a proposta?"},
            {"start": 4, "end": 12, "text": "A proposta é reduzir o desperdício."},
        ]
    })
    assert without_speaker_change["qa_candidates"]
    assert without_speaker_change["qa_candidates"][0]["needs_speaker_review"] is True
    assert without_speaker_change["speaker_detection"]["status"] == "not_available"


def test_qa_confidence_prefers_verified_speaker_transition_over_rhetorical_question():
    from modules.editorial_context import analyze_transcript_context

    verified = analyze_transcript_context({
        "segments": [
            {"start": 0, "end": 4, "text": "Qual é a proposta?", "speaker": "entrevistador"},
            {"start": 4, "end": 12, "text": "A proposta reduz o desperdício.", "speaker": "renan"},
        ]
    })
    rhetorical = analyze_transcript_context({
        "segments": [
            {"start": 0, "end": 4, "text": "Qual é a proposta?", "speaker": "renan"},
            {"start": 4, "end": 12, "text": "A proposta reduz o desperdício.", "speaker": "renan"},
        ]
    })
    assert verified["qa_candidates"][0]["confidence"] > rhetorical["qa_candidates"][0]["confidence"]
    assert rhetorical["qa_candidates"][0]["needs_speaker_review"] is True


def test_snapshot_rejects_unknown_accounts_and_keeps_supported_data():
    snapshot = normalize_snapshot({
        "accounts": {
            "@renansantosmbl": {"hook_observations": []},
            "@other": {"hook_observations": [{"hook": "x", "ratio": 99}]},
        }
    })
    assert list(snapshot["accounts"]) == ["@renansantosmbl"]


def test_hook_classification_is_explainable_and_prior_requires_sample():
    assert classify_hook("Qual é o maior problema do Brasil?") == "desafio-ao-espectador"
    prior = build_performance_prior(
        "Vamos mudar a gestão pública. A tese é clara.",
        account="@renansantosmbl",
        snapshot=_snapshot(),
    )
    assert prior["available"] is True
    assert prior["sample_count"] == 3
    assert 42 <= prior["observed_signal"] <= 58


def test_campaign_hub_prior_is_visible_but_bounded_in_ranker():
    ranker = EditorialRanker(
        campaign_hub_snapshot=_snapshot(),
        campaign_hub_account="@renansantosmbl",
    )
    result = ranker.score_clip({
        "start": 0,
        "end": 35,
        "duration": 35,
        "text": "Vamos mudar a gestão pública. A tese é clara e termina com uma solução.",
    })
    assert result["campaign_hub_prior"]["available"] is True
    assert result["review_flags"]["campaign_hub_prior_available"] is True
    assert result["review_flags"]["campaign_hub_sample_count"] == 3
    assert result["hook_family"] == "tese-provocativa"
    assert result["hook_evidence"]
    assert result["hook_classification_confidence"] >= 0.6
    assert result["review_flags"]["campaign_hub_hook_family"] == "tese-provocativa"
    assert "campaign_hub_prior" in result["factors"]


def test_hook_details_explain_explicit_thesis_before_generic_question():
    details = classify_hook_details("Vamos mudar a gestão pública. Que Brasil vamos construir?")
    assert details["family"] == "tese-provocativa"
    assert details["evidence"]
    assert details["basis"] == "regra_textual_explicita"


def test_aggregate_only_snapshot_is_normalized_without_post_ids():
    snapshot = normalize_snapshot({
        "schema_version": "editorial-priors-v1-aggregate-only",
        "default_account": "@renansantosmbl",
        "accounts": {
            "@renansantosmbl": {
                "platform": "instagram",
                "hook_priors": [
                    {"hook": "tese-provocativa", "observations": 4, "mean_ratio": 4.2, "max_ratio": 8.0},
                ],
            }
        },
    })
    assert snapshot["accounts"]["@renansantosmbl"]["hook_observations"]
    assert not snapshot["accounts"]["@renansantosmbl"]["examples"]
    prior = build_performance_prior(
        "Vamos mudar a gestão pública. A tese é clara.",
        snapshot=snapshot,
    )
    assert prior["available"] is True
    assert prior["sample_count"] == 4


def test_qa_boundary_stops_before_following_question():
    from modules.editorial_context import analyze_transcript_context

    result = analyze_transcript_context({
        "segments": [
            {"start": 0, "end": 4, "text": "Qual é a proposta?", "speaker": "entrevistador"},
            {"start": 4, "end": 10, "text": "A proposta reduz o desperdício.", "speaker": "renan"},
            {"start": 10, "end": 15, "text": "Ela começa pela transparência.", "speaker": "renan"},
            {"start": 15, "end": 20, "text": "E qual é o prazo?", "speaker": "entrevistador"},
        ]
    })

    candidate = result["qa_candidates"][0]
    assert candidate["response_segments"] == [1, 2]
    assert candidate["end"] == 15.0


def test_qa_boundary_stops_at_second_reliable_speaker_change():
    from modules.editorial_context import analyze_transcript_context

    result = analyze_transcript_context({
        "segments": [
            {"start": 0, "end": 4, "text": "Qual é a proposta?", "speaker": "entrevistador"},
            {"start": 4, "end": 10, "text": "A proposta reduz o desperdício.", "speaker": "renan"},
            {"start": 10, "end": 14, "text": "Eu discordo dessa resposta.", "speaker": "convidado"},
        ]
    })

    candidate = result["qa_candidates"][0]
    assert candidate["response_segments"] == [1]
    assert candidate["boundary_basis"] == "segunda_troca_de_locutor"
    assert candidate["response_speaker"] == "renan"


def test_campaign_hub_prior_stays_neutral_with_insufficient_hook_sample():
    snapshot = normalize_snapshot({
        "accounts": {
            "@renansantosmbl": {
                "hook_observations": [
                    {"hook": "tese-provocativa", "ratio": 9.0},
                    {"hook": "tese-provocativa", "ratio": 9.5},
                ],
            }
        }
    })
    prior = build_performance_prior(
        "Vamos mudar a gestão pública. A tese é clara.",
        account="@renansantosmbl",
        snapshot=snapshot,
    )
    assert prior["available"] is False
    assert prior["observed_signal"] == 50.0
    assert prior["confidence"] == 0.0


def test_hook_detector_marks_unknown_speaker_for_review_even_without_question():
    candidates = detect_hook_candidates([
        {"start": 0.0, "end": 5.0, "text": "A verdade sobre este caso muda tudo.", "speaker": "unknown"},
        {"start": 5.2, "end": 12.0, "text": "Por isso, a consequência precisa ser explicada."},
    ], limit=3)

    assert candidates
    assert candidates[0]["needs_speaker_review"] is True
    assert "locutor" in candidates[0]["speaker_review_reason"]


def test_hook_detector_normalizes_string_and_non_finite_speaker_confidence():
    candidates = detect_hook_candidates([
        {"start": 0.0, "end": 5.0, "text": "A verdade sobre este caso muda tudo.", "speaker": "Renan", "speaker_confidence": "0.40"},
        {"start": 5.2, "end": 12.0, "text": "Por isso, a consequência precisa ser explicada."},
    ], limit=3)

    assert candidates
    assert candidates[0]["needs_speaker_review"] is True
    assert "locutor" in candidates[0]["speaker_review_reason"]

    nan_candidates = detect_hook_candidates([
        {"start": 0.0, "end": 5.0, "text": "A verdade sobre este caso muda tudo.", "speaker": "Renan", "speaker_confidence": "nan"},
    ], limit=3)
    assert nan_candidates[0]["needs_speaker_review"] is True



def test_snapshot_status_distinguishes_empty_file(tmp_path):
    snapshot_path = tmp_path / "empty.json"
    snapshot_path.write_text("  \n", encoding="utf-8")

    status = snapshot_status(str(snapshot_path))

    assert status["available"] is False
    assert status["status"] == "empty"
    assert status["path"] == str(snapshot_path)
    assert status["influences_ranking"] is False


def test_snapshot_status_distinguishes_invalid_json(tmp_path):
    snapshot_path = tmp_path / "invalid.json"
    snapshot_path.write_text("{not-json", encoding="utf-8")

    status = snapshot_status(str(snapshot_path))

    assert status["available"] is False
    assert status["status"] == "invalid"
    assert "JSON inválido" in status["message"]
    assert status["influences_ranking"] is False


def test_snapshot_status_distinguishes_structurally_valid_but_empty_snapshot(tmp_path):
    snapshot_path = tmp_path / "no-observations.json"
    snapshot_path.write_text(
        '{"accounts":{"@renansantosmbl":{"hook_observations":[],"examples":[],"cohorts":[]}}}',
        encoding="utf-8",
    )

    status = snapshot_status(str(snapshot_path))

    assert status["available"] is False
    assert status["status"] == "empty"
    assert status["total_hook_observations"] == 0
    assert status["influences_ranking"] is False


def test_snapshot_status_exposes_bounded_ranking_influence(tmp_path):
    snapshot_path = tmp_path / "ready.json"
    snapshot_path.write_text(
        '{"version":"ready-v1","accounts":{"@renansantosmbl":{"hook_observations":['
        '{"hook":"tese-provocativa","ratio":1.0},'
        '{"hook":"tese-provocativa","ratio":1.1},'
        '{"hook":"tese-provocativa","ratio":1.2}]}}}',
        encoding="utf-8",
    )

    status = snapshot_status(str(snapshot_path))

    assert status["available"] is True
    assert status["status"] == "ready"
    assert status["total_hook_observations"] == 3
    assert status["influences_ranking"] is True
    assert "não cria cortes" in status["influence_scope"]


def test_snapshot_status_missing_explicit_file_is_read_only(tmp_path):
    status = snapshot_status(str(tmp_path / "does-not-exist.json"))

    assert status["available"] is False
    assert status["status"] == "missing"
    assert status["read_only"] is True
    assert status["influences_ranking"] is False



def test_ranker_exposes_acervo_alignment_without_removing_context_gate():
    snapshot = normalize_snapshot({
        "accounts": {
            "@renansantosmbl": {
                "acervo_blocks": [{
                    "id": "block-ranked",
                    "contentClass": "fala",
                    "title": "A proposta de segurança pública",
                    "summary": "A resposta precisa ser concreta e terminar com uma solução.",
                    "startS": 0,
                    "endS": 40,
                    "densityRank": 99,
                    "selfContainedRank": 99,
                    "trustTier": "owner",
                    "video": {"youtubeId": "AbCdEfGhI12"},
                }],
            },
        },
    })
    ranker = EditorialRanker(campaign_hub_snapshot=snapshot, campaign_hub_account="@renansantosmbl")
    result = ranker.score_clip({
        "source_id": "AbCdEfGhI12",
        "start": 0,
        "end": 35,
        "duration": 35,
        "text": "A proposta de segurança pública precisa ser concreta e termina com uma solução.",
        "context_complete": False,
        "question_detected": True,
        "question_answer_complete": False,
    })
    assert result["acervo_alignment"]["available"] is True
    assert result["review_flags"]["acervo_alignment_available"] is True
    assert result["quality_scorecard"]["status"] == "review_required"
    assert result["technical_gate"]["status"] in {"review", "weak"}



def test_acervo_mention_without_renan_speaking_is_review_only():
    snapshot = normalize_snapshot({
        "accounts": {
            "@renansantosmbl": {
                "acervo_blocks": [{
                    "id": "mention-1",
                    "contentClass": "mencao",
                    "renanSpeaking": False,
                    "title": "Menção lateral a Renan",
                    "startS": 10,
                    "endS": 30,
                    "densityRank": 99,
                    "selfContainedRank": 99,
                    "trustTier": "owner",
                    "video": {"youtubeId": "AbCdEfGhI12"},
                }],
            },
        },
    })
    result = build_acervo_alignment(
        "Menção lateral a Renan em contexto de segurança pública.",
        12,
        20,
        source_id="AbCdEfGhI12",
        account="@renansantosmbl",
        snapshot=snapshot,
    )
    assert result["available"] is True
    assert result["persona_match"] is False
    assert result["review_required"] is True
    assert result["signal"] <= 50



def test_merge_acervo_seed_candidates_adds_review_only_same_source_seed():
    snapshot = normalize_snapshot({
        "default_account": "@renansantosmbl",
        "accounts": {
            "@renansantosmbl": {
                "acervo_blocks": [{
                    "id": "block-seed-1",
                    "contentClass": "fala",
                    "renanSpeaking": True,
                    "densityRank": 92,
                    "selfContainedRank": 88,
                    "trustTier": "owner",
                    "startS": 10,
                    "endS": 34,
                    "title": "Resposta sobre segurança pública",
                    "summary": "Resposta com tese, consequência e contexto.",
                    "video": {"youtubeId": "AbCdEfGhI12"},
                    "highlights": [{"startS": 12, "endS": 30, "text": "A resposta apresenta os dados."}],
                }],
            },
        },
    })
    merged = merge_acervo_seed_candidates(
        [{"start": 60, "end": 80, "duration": 20, "source_id": "AbCdEfGhI12", "text": "Outro candidato."}],
        snapshot,
        account="@renansantosmbl",
        source_id="AbCdEfGhI12",
    )

    assert len(merged) == 2
    seed = merged[-1]
    assert seed["candidate_origin"] == "campaign_hub_acervo_seed"
    assert seed["context_seed_only"] is True
    assert seed["transcription_review_required"] is True
    assert seed["acervo_alignment"]["status"] == "aligned_same_source"


def test_merge_acervo_seed_candidates_does_not_cross_source_or_duplicate_interval():
    snapshot = normalize_snapshot({
        "default_account": "@renansantosmbl",
        "accounts": {
            "@renansantosmbl": {
                "acervo_blocks": [{
                    "id": "block-seed-2",
                    "contentClass": "fala",
                    "renanSpeaking": True,
                    "startS": 10,
                    "endS": 34,
                    "title": "Seed",
                    "summary": "Resumo",
                    "video": {"youtubeId": "AbCdEfGhI12"},
                }],
            },
        },
    })
    existing = [{"start": 10, "end": 34, "duration": 24, "source_id": "AbCdEfGhI12", "text": "Já existe."}]
    merged = merge_acervo_seed_candidates(existing, snapshot, account="@renansantosmbl", source_id="OutroVideo99")
    assert merged == existing
    merged_same = merge_acervo_seed_candidates(existing, snapshot, account="@renansantosmbl", source_id="AbCdEfGhI12")
    assert merged_same == existing


def test_merge_acervo_seed_candidates_treats_missing_local_source_as_current_source():
    snapshot = normalize_snapshot({
        "default_account": "@renansantosmbl",
        "accounts": {
            "@renansantosmbl": {
                "acervo_blocks": [{
                    "id": "block-seed-local-payload",
                    "contentClass": "fala",
                    "renanSpeaking": True,
                    "startS": 10,
                    "endS": 34,
                    "title": "Seed repetido",
                    "summary": "Resumo do mesmo intervalo para revisão.",
                    "video": {"youtubeId": "AbCdEfGhI12"},
                }],
            },
        },
    })
    local_candidate = [{
        "start": 10,
        "end": 34,
        "duration": 24,
        "text": "Candidato local sem identidade explícita.",
    }]

    merged = merge_acervo_seed_candidates(
        local_candidate,
        snapshot,
        account="@renansantosmbl",
        source_id="AbCdEfGhI12",
    )

    assert merged == local_candidate
