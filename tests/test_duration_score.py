import pytest
from modules.clip_selector import ClipSelector


class TestDurationScore:
    @pytest.fixture
    def selector(self):
        return ClipSelector()

    def test_under_min_returns_negative(self, selector):
        assert selector._duration_score(25.0) == -8

    def test_at_min_plus_small(self, selector):
        assert selector._duration_score(45.0) == 10

    def test_within_preferred_band(self, selector):
        assert selector._duration_score(60.0) == 10
        assert selector._duration_score(100.0) == 7

    def test_preferred_max(self, selector):
        assert selector._duration_score(150.0) == 2

    def test_technical_max(self, selector):
        assert selector._duration_score(180.0) == -1

    def test_over_technical_max(self, selector):
        assert selector._duration_score(181.0) == -5
