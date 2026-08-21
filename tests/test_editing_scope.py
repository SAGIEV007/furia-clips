import inspect

import app as app_module
import config


def test_editing_pipeline_disables_non_editing_metadata_by_default():
    assert config.DEFAULT_SETTINGS["generate_seo_metadata"] is False
    source = inspect.getsource(app_module.api_process_complete)
    assert 'settings.get("generate_seo_metadata", False)' in source
    assert "Metadados de publicação desativados" in source


def test_complete_pipeline_passes_job_cancel_check_to_silence_removal():
    source = inspect.getsource(app_module.api_process_complete)
    assert "cancel_check=ctx.check_cancel" in source
    assert '_set_legacy_task("process_complete", active=True)' in source
    assert "with processing_lock:" in source
    assert '_set_legacy_task("", active=False)' in source


def test_optional_processing_endpoints_use_shared_legacy_state_guard():
    endpoints = (
        (app_module.api_generate_subtitles, '"subtitles"'),
        (app_module.api_generate_seo, '"seo"'),
        (app_module.api_generate_thumbnail, '"thumbnail"'),
    )
    for endpoint, operation in endpoints:
        source = inspect.getsource(endpoint)
        assert "with processing_lock:" in source
        assert f"_set_legacy_task({operation}, active=True" in source
        assert '_set_legacy_task("", active=False)' in source
        assert 'current_task["active"] = True' not in source


def test_optional_legacy_endpoints_return_and_emit_job_ids():
    subtitles_source = inspect.getsource(app_module.api_generate_subtitles)
    thumbnail_source = inspect.getsource(app_module.api_generate_thumbnail)

    for source, operation in ((subtitles_source, "subtitles"), (thumbnail_source, "thumbnail")):
        assert "job_id" in source
        assert f"job_id={operation}_job_id" in source
        assert '"state": "running"' in source
        assert f'"operation": "{operation}"' in source


def test_face_tracking_is_optional_and_guarded_before_detection():
    source = inspect.getsource(app_module.api_cut_shorts)
    assert 'use_face_tracking = _coerce_bool(data.get("face_tracking"), default=True)' in source
    assert 'if use_face_tracking and tracker and video_layout not in {"debate", "unknown", "fullscreen"}:' in source
    assert 'original_aspect_indices.update(range(len(top_clips)))' in source
    assert '"mode": "original"' in source


def test_framing_requires_confidence_without_review_flag_before_crop():
    source = inspect.getsource(app_module.api_cut_shorts)
    complete_source = inspect.getsource(app_module.api_process_complete)
    for pipeline in (source, complete_source):
        assert 'safe_reframe = bool(layout_plan.get("reframe_allowed")) and not bool(layout_plan.get("review_required"))' in pipeline
        assert 'if safe_reframe:' in pipeline
        assert 'original_aspect_indices.add(index)' in pipeline


def test_repository_status_endpoint_is_read_only_without_implicit_fetch():
    source = inspect.getsource(app_module.api_repository_status)
    assert "get_repository_status(fetch=False)" in source
    assert "request.args.get(\"fetch\"" not in source


def test_complete_pipeline_terminal_events_keep_job_identity():
    source = inspect.getsource(app_module.api_process_complete)
    assert 'emit_status("complete_done"' in source
    assert 'emit_status("cancelled", {}, job_id=ctx.job_id)' in source
    assert 'emit_status("error", {"message": str(e)}, job_id=ctx.job_id)' in source
    assert '}, job_id=ctx.job_id)' in source


def test_complete_pipeline_reuses_shared_transcription_fallback_policy():
    source = inspect.getsource(app_module.api_process_complete)
    assert "_transcribe_video_automatically(" in source
    assert 'fallback_settings = {**settings, "transcription_source": "whisper"}' in source
    assert "cancel_check=ctx.check_cancel" in source


def test_complete_pipeline_applies_context_gate_before_rendering():
    source = inspect.getsource(app_module.api_process_complete)
    assert "candidate_diagnostics = selector.get_candidate_diagnostics()" in source
    assert "top_clips, editorial_gate_rejections = _defer_context_incomplete_candidates(top_clips)" in source
    assert 'candidate_diagnostics["editorial_gate_deferred_count"] = len(editorial_gate_rejections)' in source
    assert 'candidate_diagnostics["rendered_count"] = len(results)' in source


def test_cut_job_distinguishes_render_failure_from_selection_shortage():
    source = inspect.getsource(app_module.api_cut_shorts)
    assert 'candidate_diagnostics["render_rejection_count"] = len(render_rejections)' in source
    assert 'candidate_diagnostics["rendered_count"] = len(results)' in source
    assert '"render_failed_after_selection"' in source
    assert '"partial_render_failure"' in source


def test_cut_completion_labels_selection_backend_without_collapsing_gemini_to_nlp():
    source = inspect.getsource(app_module.api_cut_shorts)
    assert '"gemini": "Gemini Flash"' in source
    assert '"llm": "Ollama"' in source
    assert '"nlp": "NLP local"' in source
    assert 'source_label = source_labels.get(selection_source, "NLP local")' in source


def test_cut_job_persists_safe_candidate_diagnostic_artifact():
    source = inspect.getsource(app_module.api_cut_shorts)
    assert '"type": "candidate_diagnostics"' in source
    assert '"reason": str(candidate_diagnostics.get("reason"' in source
    assert '"expected_count": int(candidate_diagnostics.get("expected_count"' in source
    assert '"editorial_gate_deferred_count": int(candidate_diagnostics.get("editorial_gate_deferred_count"' in source


def test_complete_pipeline_keeps_original_timeline_after_silence_artifact():
    source = inspect.getsource(app_module.api_process_complete)
    assert "working_video = video_path" in source
    assert "a seleção continuará usando a timeline original." in source
    assert "without an explicit TimelineMap conversion." in source


def test_smart_cut_uses_job_context_for_whisper_cancellation_and_transcript_provenance():
    source = inspect.getsource(app_module.api_cut_shorts)
    assert "cancel_check=ctx.check_cancel" in source
    assert "transcription.get(\"source\") or selected_transcription_mode" in source
    assert 'settings.get("whisper_model", "small")' in source
    assert "_transcription_from_request(data, duration=video_duration)" in source
    assert "transcript_archive = archive_transcription(" in source
    assert 'transcription["archive"] = transcript_archive' in source
