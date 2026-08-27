from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
APP_CSS = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
INDEX_HTML = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")


def test_api_requests_have_abortable_timeout_and_safe_job_guidance():
    assert 'const { timeoutMs = 30000, signal: externalSignal' in APP_JS
    assert "new AbortController()" in APP_JS
    assert "window.clearTimeout(timer)" in APP_JS
    assert "O Studio não recebeu resposta" in APP_JS
    assert "O job pode continuar no servidor" in APP_JS


def test_job_polling_retries_then_keeps_job_attached_for_recovery():
    assert "networkFailures >= 6" in APP_JS
    assert "state.jobDetached = true" in APP_JS
    assert "Retomar acompanhamento" in APP_JS
    assert "async function resumeDetachedJob()" in APP_JS
    assert "state.currentJobId !== null" in APP_JS
    assert "state.busy || state.jobDetached" in APP_JS


def test_dynamic_actions_are_idempotent_and_layout_is_frame_coalesced():
    assert "element.dataset.actionBound" in APP_JS
    assert "input.dataset.searchBound" in APP_JS
    assert "window.requestAnimationFrame" in APP_JS
    assert "signalLayoutFrame = 0" in APP_JS


def test_hidden_upload_controls_and_dialogs_have_accessible_names():
    assert 'id="transcriptInput"' in INDEX_HTML
    assert 'id="chubInput"' in INDEX_HTML
    assert 'aria-label="Importar transcript SRT, VTT, TXT ou JSON"' in INDEX_HTML
    assert 'aria-label="Importar snapshot opcional do Chub"' in INDEX_HTML
    assert 'role="dialog" aria-modal="true"' in INDEX_HTML


def test_responsive_and_console_recovery_styles_are_present():
    assert "min-width: 320px" in APP_CSS
    assert "@media (max-width: 780px)" in APP_CSS
    assert "@media (max-width: 440px)" in APP_CSS
    assert ".console-resume:not([hidden])" in APP_CSS
    assert "overflow-x: hidden" in APP_CSS
