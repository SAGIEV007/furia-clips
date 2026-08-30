"""Tests for lightweight schema validators in modules/schemas.py."""

from __future__ import annotations

import math

import pytest

from modules.schemas import (
    ChubSnapshotValidationError,
    ClipCandidateValidationError,
    validate_chub_snapshot,
    validate_clip_candidate,
)


def test_validate_chub_snapshot_accepts_valid_payload():
    payload = {
        "default_account": "@renansantosmbl",
        "accounts": {
            "@renansantosmbl": {
                "hook_observations": [],
                "acervo_blocks": [],
                "acervo_pauta": [],
                "audience_priors": {},
                "performance": [],
            }
        },
        "meta": {"source": "test"},
    }
    assert validate_chub_snapshot(payload) is payload


def test_validate_chub_snapshot_rejects_missing_default_account():
    with pytest.raises(ChubSnapshotValidationError):
        validate_chub_snapshot({"accounts": {"@renansantosmbl": {}}})


def test_validate_chub_snapshot_rejects_missing_accounts():
    with pytest.raises(ChubSnapshotValidationError):
        validate_chub_snapshot({"default_account": "@renansantosmbl"})


def test_validate_chub_snapshot_rejects_non_dict_payload():
    with pytest.raises(ChubSnapshotValidationError):
        validate_chub_snapshot([])


def test_validate_chub_snapshot_rejects_accounts_not_dict():
    with pytest.raises(ChubSnapshotValidationError):
        validate_chub_snapshot({
            "default_account": "@renansantosmbl",
            "accounts": [],
        })


def test_validate_chub_snapshot_rejects_default_account_not_string():
    with pytest.raises(ChubSnapshotValidationError):
        validate_chub_snapshot({
            "default_account": 123,
            "accounts": {"@renansantosmbl": {}},
        })


def test_validate_clip_candidate_accepts_valid_clip():
    clip = {"start": 0.0, "end": 45.0, "duration": 45.0}
    assert validate_clip_candidate(clip) is clip
