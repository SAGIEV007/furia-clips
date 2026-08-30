"""Tests for quality_gate tier classification in Fúria pipeline."""

import pytest
from modules.clip_selector import ClipSelector


class TestQualityGate:
    """Quality gate auto-approval / review / reject tiers."""

    def setup_method(self):
        self.selector = ClipSelector()

    def test_high_score_auto_approves(self):
        tier, reason = self.selector.quality_gate({"viral_score": 95})
        assert tier == "approve"
        assert reason == "high_viral_score"

    def test_boundary_80_auto_approves(self):
        tier, reason = self.selector.quality_gate({"viral_score": 80})
        assert tier == "review"
        assert reason == "medium_viral_score"

    def test_mid_score_reviews(self):
        tier, reason = self.selector.quality_gate({"viral_score": 65})
        assert tier == "review"
        assert reason == "medium_viral_score"

    def test_low_score_rejects(self):
        tier, reason = self.selector.quality_gate({"viral_score": 30})
        assert tier == "reject"
        assert reason == "low_viral_score"

    def test_zero_score_rejects(self):
        tier, reason = self.selector.quality_gate({"viral_score": 0})
        assert tier == "reject"
        assert reason == "low_viral_score"

    def test_missing_score_defaults_to_reject(self):
        tier, reason = self.selector.quality_gate({})
        assert tier == "reject"
        assert reason == "low_viral_score"
