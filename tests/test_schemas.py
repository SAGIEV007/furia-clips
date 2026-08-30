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
    payload = {"account": "@renansantosmbl", "posts": [{"id": "1"}]}
    assert validate_chub_snapshot(payload) is payload


def test_validate_chub_snapshot_rejects_missing_account():
    with pytest.raises(ChubSnapshotValidationError):
        validate_chub_snapshot({"posts": []})


def test_validate_chub_snapshot_rejects_missing_posts():
    with pytest.raises(ChubSnapshotValidationError):
        validate_chub_snapshot({"account": "@renansantosmbl"})


def test_validate_chub_snapshot_rejects_non_dict_payload():
    with pytest.raises(ChubSnapshotValidationError):
        validate_chub_snapshot([])


def test_validate_clip_candidate_accepts_valid_clip():
    clip = {"start": 0.0, "end": 45.0, "duration": 45.0}
    assert validate_clip_candidate(clip) is clip


def test_validate_clip_candidate_rejects_non_numeric_field():
    with pytest.raises(ClipCandidateValidationError):
        validate_clip_candidate({"start": "abc", "end": 10.0, "duration": 10.0})


def test_validate_clip_candidate_rejects_non_finite_field():
    with pytest.raises(ClipCandidateValidationError):
        validate_clip_candidate({"start": math.inf, "end": 10.0, "duration": 10.0})


def test_validate_clip_candidate_rejects_non_dict():
    with pytest.raises(ClipCandidateValidationError):
        validate_clip_candidate("not-a-dict")
