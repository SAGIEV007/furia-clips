import pytest

from modules.editorial_block import build_editorial_block


def test_build_editorial_block_maps_existing_candidate_fields():
    block = build_editorial_block(
        {
            "start": 12.25,
            "end": 47.5,
            "duration": 35.25,
            "title": "Reforma fiscal precisa de proposta concreta",
            "reason": "Tese completa com consequência explícita.",
            "editorial_family": "politico",
            "review_status": "pending",
            "confidence": 0.87,
        }
    )

    assert block["state"] == "candidate"
    assert block["thesis"] == "Reforma fiscal precisa de proposta concreta"
    assert block["context_summary"] == "Tese completa com consequência explícita."
    assert block["source_family"] == "politico"
    assert block["suggested_moments"][0]["kind"] == "primary"
    assert block["suggested_moments"][0]["start"] == 12.25
    assert block["confidence"] == 0.87


def test_build_editorial_block_does_not_invent_missing_summary():
    block = build_editorial_block({"start": 0, "end": 5})

    assert block["thesis"] == ""
    assert block["context_summary"] == ""
    assert block["moment_reason"] == ""
    assert block["source_family"] == "unknown"


def test_build_editorial_block_normalizes_alternatives_and_state():
    block = build_editorial_block(
        {
            "start": 30,
            "end": 50,
            "suggested_moments": [
                {"kind": "alternative", "start": 31.2, "end": 44.8, "reason": "fecho mais curto"},
                {"kind": "invalid", "start": 9, "end": 9},
            ],
            "review_state": "needs_review",
        }
    )

    assert block["state"] == "needs_review"
    assert len(block["suggested_moments"]) == 1
    assert block["suggested_moments"][0]["kind"] == "alternative"


def test_build_editorial_block_rejects_invalid_interval():
    with pytest.raises(ValueError, match="duração positiva"):
        build_editorial_block({"start": 12, "end": 12})
