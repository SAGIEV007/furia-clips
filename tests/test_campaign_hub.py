from modules.campaign_hub import build_performance_prior, classify_hook, normalize_snapshot
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
    assert "campaign_hub_prior" in result["factors"]
