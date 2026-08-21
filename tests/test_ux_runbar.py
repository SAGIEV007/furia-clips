from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
SCRIPT = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
STYLES = (ROOT / "static" / "css" / "style.css").read_text(encoding="utf-8")


def test_run_bar_exposes_progress_scope_and_pipeline_steps():
    required_markup = (
        'id="runBarStage"',
        'id="runBarProgressTrack"',
        'id="runBarProgressFill"',
        'id="runBarProgressText"',
        'id="runBarScope"',
        'data-run-step="source"',
        'data-run-step="transcript"',
        'data-run-step="context"',
        'data-run-step="ranking"',
        'data-run-step="render"',
    )
    assert all(fragment in TEMPLATE for fragment in required_markup)


def test_run_bar_progress_is_accessible_and_driven_by_existing_job_progress():
    assert 'role="progressbar"' in TEMPLATE
    assert 'aria-valuenow' in TEMPLATE
    assert "renderRunBarState(inferRunStage(jobDetail), Number(job.progress || 0))" in SCRIPT
    assert "runBarProgressFill" in SCRIPT
    assert "runBarScope" in SCRIPT


def test_run_bar_has_semantic_visual_states_and_reduced_motion_support():
    assert ".run-bar-step.complete" in STYLES
    assert ".run-bar-step.active" in STYLES
    assert ".run-bar-step.error" in STYLES
    assert "prefers-reduced-motion" in STYLES
    assert "@media (max-width: 620px)" in STYLES
