from modules.instagram_editorial_priors import (
    _aggregate_records,
    build_editorial_pattern_prior,
    load_editorial_priors,
)


def test_aggregate_records_keeps_only_family_and_layout_statistics():
    aggregate = _aggregate_records([
        {
            "content_key": "private-or-public-id-that-must-not-propagate",
            "family": "reaction_external_evidence",
            "views": 1200000,
            "layout": "vertical_split_screen",
            "layout_policy": "preserve_split_screen",
            "confidence": 0.9,
        },
        {
            "content_key": "another-id",
            "family": "reaction_external_evidence",
            "views": 500000,
            "layout": "vertical_split_screen",
            "layout_policy": "preserve_split_screen",
            "confidence": 0.8,
        },
    ])
    assert aggregate["record_count"] == 2
    assert aggregate["family_priors"][0]["family"] == "reaction_external_evidence"
    assert aggregate["family_priors"][0]["preserve_composition_rate"] == 1.0
    assert "content_key" not in aggregate["family_priors"][0]


def test_local_dataset_produces_bounded_family_prior():
    payload = load_editorial_priors()
    assert payload["source"] in {"local_detailed_dataset", "packaged_aggregate_priors", "none"}
    prior = build_editorial_pattern_prior(
        "Qual é a resposta? A prova está nos registros. Por isso, a conclusão é clara.",
        {"split_screen": True},
    )
    assert 42.0 <= prior["signal"] <= 58.0
    assert prior["sample_count"] >= 0
