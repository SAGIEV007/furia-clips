from modules.campaign_hub import build_performance_prior, classify_hook, classify_hook_details, normalize_snapshot, snapshot_status
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
    assert status["accounts"]["@renansantosmbl"] == {"hook_observations": 1, "examples": 1, "cohorts": 1}


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
