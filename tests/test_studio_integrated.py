from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
BAT = (ROOT / "run.bat").read_text(encoding="utf-8")
CUTTER = (ROOT / "modules" / "video_cutter.py").read_text(encoding="utf-8")


def test_poolsuite_surface_is_the_single_frontend():
    assert 'title>Furia Studio' in HTML
    assert '/static/app.css' in HTML
    assert '/static/app.js' in HTML
    assert 'id="settingsModal"' in HTML
    assert 'id="queueContent"' in HTML
    assert 'id="reviewWorkspace"' in HTML
    assert 'Publicação' not in HTML
    assert 'Insights' not in HTML
    assert 'furia2' not in HTML.lower()


def test_studio_interactions_have_real_targets():
    for fragment in (
        'data-action="open-review"',
        'data-action="decision"',
        'data-action="export"',
        'class="range-handle range-start"',
        'class="range-handle range-end"',
        'class="transcript-search"',
        'function renderEditorialBlock',
        'function refreshQueue',
        'function openSettings',
        'function renderSeoPreview',
        'data-action="use-headline"',
                    'HEADLINE / BASE NA LEGENDA',

        'activeProjectId',
        'furia-active-project',
        'renderSourceDesk',
        'console-drawer',
        'refreshStudioStatus',
        'force_whisper',
        'Conectar memória do Campaign Hub',
        'class="review-snap"',
        'snap_to_transcript',
        'reviewCount',
        'A análise terminou sem encontrar cortes prontos.',
        'Nenhum corte pronto nesta execução.',
        'function nextProjectAction',
        'id="projectNextAction"',
        'function scheduleQueuePoll',
        'queuePollBusy',
                    'MEMÓRIA DE CAMPANHA',
            'btnCancelJob',
            'cancelCurrentJob',
            'review-feedback-reason',
            'reason_code',
            'projectsRequest',
            'loading="lazy"',
            'Corte anterior',
            'ready_no_results',
            'btnRefreshStatus',
            'data-force-reanalysis',
            'cancel_check',

    ):
        assert fragment in HTML or fragment in JS or fragment in CUTTER


def test_launcher_uses_one_configurable_port_and_url():
    assert 'set "FURIA_URL=http://127.0.0.1:%FURIA_PORT%"' in BAT
    assert "-LocalPort %FURIA_PORT%" in BAT
    assert '-Url "%FURIA_URL%"' in BAT
    assert "3001" not in BAT.replace('set "FURIA_PORT=3001"', "")


def test_adapter_routes_are_registered_once():
    app_module = pytest.importorskip("app")
    rules = {(rule.rule, rule.endpoint, tuple(sorted(rule.methods - {"HEAD", "OPTIONS"}))) for rule in app_module.app.url_map.iter_rules()}
    assert ("/api/projects", "studio_create_project", ("POST",)) in rules
    assert ("/api/projects/<int:project_id>/import", "studio_import_local", ("POST",)) in rules
    assert ("/api/projects/<int:project_id>/chub-context", "studio_chub_attach", ("POST",)) in rules
    assert ("/api/projects/<int:project_id>/chub-context", "studio_chub_clear", ("DELETE",)) in rules
    assert ("/api/clips/<int:clip_id>/range", "studio_range", ("POST",)) in rules
    assert ("/api/clips/<int:clip_id>/decision", "studio_decision", ("POST",)) in rules
    assert ("/api/clips/<int:clip_id>/title", "studio_title", ("POST",)) in rules
    assert ("/api/projects/<int:project_id>/seo", "studio_seo", ("POST",)) in rules
    assert ("/api/clips/<int:clip_id>/export", "studio_export", ("POST",)) in rules
    assert ("/api/studio/status", "studio_status", ("GET",)) in rules


def test_adapter_does_not_load_furia2_namespace():
    source = (ROOT / "studio_adapter.py").read_text(encoding="utf-8").lower()
    assert "furia2" not in source
    assert not (ROOT / "furia2").exists()
