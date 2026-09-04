"""Regression tests for viral_score grade calibration (A=80, B=25, C=0)."""
import pytest
from modules.viral_ranker import ViralRanker


def _score_from_grades(clip):
    return ViralRanker()._score_from_grades(clip)


def test_grade_mapping_locked():
    clip = {
        "breakdown": {"hook": "A", "flow": "B", "value": "C", "energy": "B"},
        "text": "test",
        "duration": 30,
    }
    result = _score_from_grades(clip)
    assert result["viral_score"] == 29  # 80*0.20 + 25*0.35 + 0*0.25 + 25*0.20 = 29.75 -> 29  # 80*0.20 + 25*0.35 + 0*0.25 + 25*0.20 = 35
    assert result["breakdown"] == clip["breakdown"]


def test_all_a_grades():
    clip = {
        "breakdown": {"hook": "A", "flow": "A", "value": "A", "energy": "A"},
        "text": "test",
        "duration": 30,
    }
    result = _score_from_grades(clip)
    assert result["viral_score"] == 80


def test_all_b_grades():
    clip = {
        "breakdown": {"hook": "B", "flow": "B", "value": "B", "energy": "B"},
        "text": "test",
        "duration": 30,
    }
    result = _score_from_grades(clip)
    assert result["viral_score"] == 25


def test_all_c_grades():
    clip = {
        "breakdown": {"hook": "C", "flow": "C", "value": "C", "energy": "C"},
        "text": "test",
        "duration": 30,
    }
    result = _score_from_grades(clip)
    assert result["viral_score"] == 0


def test_default_grade_is_b():
    clip = {
        "breakdown": {"hook": "X", "flow": "X", "value": "X", "energy": "X"},
        "text": "test",
        "duration": 30,
    }
    result = _score_from_grades(clip)
    assert result["viral_score"] == 25
