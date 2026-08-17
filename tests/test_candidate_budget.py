"""The candidate budget must follow the length of the source.

Measured against the Acervo benchmark on a 98-minute live: the old ceiling of 36
stopped the pipeline at less than a third of the material it was still willing to
produce, and gave a four-hour source practically the same allowance as a
one-hour one. Recall rose from 27/66 to 50/66 highlights when the budget followed
the duration, while precision stayed at 1.00 and no candidate landed outside a
labelled block.
"""

import app as app_module


def _budget(duration_s, monkeypatch):
    monkeypatch.setattr(app_module, "get_existing_clip_fingerprints", lambda *_: [])
    return app_module._selection_coverage_plan("fonte.mp4", duration_s)["adaptive_max_clips"]


def test_short_sources_keep_the_floor(monkeypatch):
    assert _budget(30, monkeypatch) == app_module.MIN_CANDIDATE_BUDGET
    assert _budget(119, monkeypatch) == app_module.MIN_CANDIDATE_BUDGET


def test_budget_grows_with_the_source(monkeypatch):
    one_hour = _budget(3600, monkeypatch)
    two_hours = _budget(7200, monkeypatch)
    four_hours = _budget(14400, monkeypatch)

    assert one_hour < two_hours < four_hours
    # The regression this replaces: 7200s and 14400s both used to return 36, so
    # doubling the source length examined no more of it.
    assert two_hours != four_hours


def test_long_source_is_not_capped_below_the_measured_supply(monkeypatch):
    # The benchmark video: the pipeline still produced new candidates up to 121.
    assert _budget(5905, monkeypatch) >= 121


def test_budget_stays_within_the_safety_valve(monkeypatch):
    assert _budget(360000, monkeypatch) == app_module.MAX_CANDIDATE_BUDGET


def test_invalid_duration_falls_back_to_the_floor(monkeypatch):
    assert _budget(None, monkeypatch) == app_module.MIN_CANDIDATE_BUDGET
    assert _budget("quatro horas", monkeypatch) == app_module.MIN_CANDIDATE_BUDGET
