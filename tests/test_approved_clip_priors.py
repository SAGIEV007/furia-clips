from modules.approved_clip_priors import build_feature_prior, load_feature_records, normalize_feature_record


def _record(decision, duration, format_id="square_alfinetei", headline="A VERDADE SOBRE A PROPOSTA"):
    return {
        "decision": decision,
        "duration": duration,
        "format_id": format_id,
        "hook_family": "tese-provocativa",
        "topic": "seguranca",
        "headline": headline,
        "transcript": "texto privado que não deve ir para o prior",
        "factors": {"context_quality": 84, "hook": 76},
    }


def test_normalize_feature_record_strips_raw_fields_and_bounds_values():
    item = normalize_feature_record({
        **_record("approved", 42),
        "factors": {"hook": 110, "bad": float("nan")},
    })
    assert item["decision"] == "approved"
    assert item["duration"] == 42
    assert item["factors"]["hook"] == 100
    assert "transcript" not in item
    assert item["headline_shape"]["word_count"] > 0


def test_build_feature_prior_requires_approved_and_rejected_volume():
    records = [_record("approved", 30 + index) for index in range(4)] + [_record("rejected", 70 + index) for index in range(4)]
    prior = build_feature_prior(records, min_samples=4)
    assert prior["eligible"] is True
    assert prior["approved_count"] == 4
    assert prior["rejected_count"] == 4
    assert prior["approved_mean_duration"] < prior["rejected_mean_duration"]
    assert prior["influence_scope"].startswith("aggregate-only")
    assert "transcript" not in str(prior)


def test_load_feature_records_accepts_jsonl_and_skips_invalid_rows(tmp_path):
    path = tmp_path / "approved.jsonl"
    path.write_text("\n".join([
        '{"decision":"approved","duration":22,"format_id":"vertical_916","headline":"ALERTA SOBRE A SEGURANÇA"}',
        '{not-json}',
        '{"decision":"pending","duration":22}',
    ]), encoding="utf-8")
    rows = load_feature_records(path)
    assert len(rows) == 1
    assert rows[0]["format_id"] == "vertical_916"
