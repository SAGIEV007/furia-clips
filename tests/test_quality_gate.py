"""Tests for quality_gate tier classification in Fúria pipeline.

Professional calibration criteria:
- Reject: duration < 25s, viral_score < 50, weak hook
- Review: context incomplete, payoff incomplete, technical review needed
- Approve: strong score + complete context + complete payoff
"""

import pytest
from modules.clip_selector import ClipSelector


class TestQualityGate:
    """Quality gate auto-approval / review / reject tiers."""

    def setup_method(self):
        self.selector = ClipSelector()

    def test_high_score_auto_approves(self):
        tier, reason = self.selector.quality_gate({
            "viral_score": 95,
            "context_complete": True,
            "payoff_complete": True,
            "has_hook": True,
            "duration": 45.0,
        })
        assert tier == "approve"
        assert reason == "high_score_complete"

    def test_score_80_auto_approves(self):
        tier, reason = self.selector.quality_gate({
            "viral_score": 80,
            "context_complete": True,
            "payoff_complete": True,
            "has_hook": True,
            "duration": 45.0,
        })
        assert tier == "approve"
        assert reason == "high_score_complete"

    def test_mid_score_with_complete_context_approves(self):
        tier, reason = self.selector.quality_gate({
            "viral_score": 65,
            "context_complete": True,
            "payoff_complete": True,
            "has_hook": True,
            "duration": 45.0,
        })
        assert tier == "approve"
        assert reason == "solid_score_complete"

    def test_mid_score_with_incomplete_context_reviews(self):
        tier, reason = self.selector.quality_gate({
            "viral_score": 65,
            "context_complete": False,
            "payoff_complete": True,
            "has_hook": True,
            "duration": 45.0,
        })
        assert tier == "review"
        assert reason == "incomplete_context"

    def test_low_score_rejects(self):
        tier, reason = self.selector.quality_gate({
            "viral_score": 30,
            "context_complete": True,
            "payoff_complete": True,
            "has_hook": True,
            "duration": 45.0,
        })
        assert tier == "reject"
        assert reason == "low_viral_score"

    def test_zero_score_rejects(self):
        tier, reason = self.selector.quality_gate({
            "viral_score": 0,
            "context_complete": True,
            "payoff_complete": True,
            "has_hook": True,
            "duration": 45.0,
        })
        assert tier == "reject"
        assert reason == "low_viral_score"

    def test_too_short_rejects(self):
        tier, reason = self.selector.quality_gate({
            "viral_score": 75,
            "context_complete": True,
            "payoff_complete": True,
            "has_hook": True,
            "duration": 10.0,
        })
        assert tier == "reject"
        assert reason == "too_short"

    def test_weak_hook_rejects(self):
        tier, reason = self.selector.quality_gate({
            "viral_score": 75,
            "context_complete": True,
            "payoff_complete": True,
            "has_hook": False,
            "duration": 45.0,
        })
        assert tier == "reject"
        assert reason == "weak_hook"

    def test_incomplete_payoff_reviews(self):
        tier, reason = self.selector.quality_gate({
            "viral_score": 65,
            "context_complete": True,
            "payoff_complete": False,
            "has_hook": True,
            "duration": 45.0,
        })
        assert tier == "review"
        assert reason == "incomplete_payoff"

    def test_technical_review_reviews(self):
        tier, reason = self.selector.quality_gate({
            "viral_score": 65,
            "context_complete": True,
            "payoff_complete": True,
            "has_hook": True,
            "duration": 45.0,
            "technical_review_required": True,
        })
        assert tier == "review"
        assert reason == "technical_review_required"

    def test_missing_fields_defaults_safely(self):
        tier, reason = self.selector.quality_gate({})
        assert tier == "reject"
        assert reason == "too_short"
