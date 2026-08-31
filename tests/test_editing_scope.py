import inspect
from unittest.mock import patch

import app as app_module
import config


def test_editing_pipeline_disables_non_editing_metadata_by_default():
    assert config.DEFAULT_SETTINGS["generate_seo_metadata"] is False


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
    assert 'if use_face_tracking and tracker and video_layout not in {"debate", "fullscreen"}:' in source
    assert 'original_aspect_indices.update(range(len(top_clips)))' in source
    assert '"mode": "original"' in source


def test_short_cut_pipeline_passes_visual_composition_to_layout_planner():
    source = inspect.getsource(app_module.api_cut_shorts)

    assert 'visual_format=clip.get("visual_format")' in source
    assert 'text_panel=bool(clip.get("text_panel"))' in source
    assert 'fake_tweet=bool(clip.get("fake_tweet") or clip.get("social_post"))' in source
    assert 'external_evidence=bool(clip.get("external_evidence"))' in source


def test_framing_requires_confidence_without_review_flag_before_crop():
    source = inspect.getsource(app_module.api_cut_shorts)
    complete_source = inspect.getsource(app_module.api_process_complete)
    for pipeline in (source, complete_source):
        assert 'safe_reframe = bool(layout_plan.get("reframe_allowed")) and not bool(layout_plan.get("review_required"))' in pipeline
        assert 'if safe_reframe:' in pipeline
        assert 'original_aspect_indices.add(index)' in pipeline


def test_repository_status_endpoint_uses_read_only_mode_without_fetch():
    fake_status = {"branch": "main", "clean": True, "read_only": True}
    with patch.object(app_module, "get_repository_status", return_value=fake_status) as mock_status:
        response = app_module.app.test_client().get("/api/repository/status")
        assert response.status_code == 200
        mock_status.assert_called_once_with(fetch=False)
        assert response.get_json() == fake_status


def test_complete_pipeline_terminal_events_keep_job_identity():
    source = inspect.getsource(app_module.api_process_complete)
    assert 'emit_status("complete_done"' in source
    assert 'emit_status("cancelled", {}, job_id=ctx.job_id)' in source
    assert 'emit_status("error", {"message": str(e)}, job_id=ctx.job_id)' in source
    assert '}, job_id=ctx.job_id)' in source


def test_legacy_transcription_archives_manual_and_automatic_results():
    source = inspect.getsource(app_module.api_transcribe)
    assert "duration = _probe_video_duration_seconds(video_path)" in source
    assert "_transcription_from_request(data, duration=duration)" in source
    assert 'result["coverage"] = _transcription_coverage_report(result, duration)' in source
    assert "transcript_archive = archive_transcription(" in source
    assert 'result["archive"] = transcript_archive' in source
    assert 'result["quality"] = transcript_archive.get("quality", {})' in source


def test_complete_pipeline_reuses_shared_transcription_fallback_policy():
    source = inspect.getsource(app_module.api_process_complete)
    assert "_transcribe_video_automatically(" in source
    assert 'fallback_settings = {**settings, "transcription_source": "whisper"}' in source
    assert "cancel_check=ctx.check_cancel" in source


def test_editorial_context_archives_transcription_for_later_review():
    import inspect
    import app as app_module

    source = inspect.getsource(app_module.api_analyze_editorial_context)
    assert "transcript_archive = archive_transcription(" in source
    assert 'enriched["transcription_archive"]' in source
    assert '"relative_dir": transcript_archive.get("relative_dir", "")' in source


def test_prefetched_context_requires_matching_source_signature_when_present():
    cut_source = inspect.getsource(app_module.api_cut_shorts)
    complete_source = inspect.getsource(app_module.api_process_complete)

    for source in (cut_source, complete_source):
        assert "prefetched_context_signature" in source
        assert "current_source_signature = get_source_signature(video_path)" in source
        assert "prefetched_context_signature == current_source_signature" in source
        assert "prefetched_signature_matches" in source

    context_source = inspect.getsource(app_module.api_analyze_editorial_context)
    assert 'enriched["source_signature"] = source_signature' in context_source


def test_complete_pipeline_applies_context_gate_before_rendering():
    renderable, deferred = app_module._defer_context_incomplete_candidates([
        {
            "start": 0,
            "end": 20,
            "duration": 20,
            "context_complete": False,
            "starts_mid_sentence": False,
            "starts_with_context_reference": False,
            "overlap_suspected": False,
            "timing_ambiguous": False,
            "speaker_turn_valid": True,
        }
    ])
    assert deferred == []
    assert len(renderable) == 1
    assert renderable[0]["review_required"] is True
    assert renderable[0]["post_render_review_required"] is True


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


def test_project_transcript_reuse_requires_matching_source_identity(tmp_path):
    video_a = tmp_path / "video_a.mp4"
    video_b = tmp_path / "video_b.mp4"
    video_a.write_bytes(b"a")
    video_b.write_bytes(b"b")

    with patch.object(app_module, "get_project") as mock_get_project, \
            patch.object(app_module, "_resolve_media_input", side_effect=lambda p: p), \
            patch.object(app_module, "get_source_signature", return_value="sig-current"):
        # Same realpath as stored source_video -> matches regardless of signature.
        mock_get_project.return_value = {"source_video": str(video_a), "source_signature": ""}
        assert app_module._project_matches_video(1, str(video_a)) is True

        # Different path but matching stored signature -> matches.
        mock_get_project.return_value = {"source_video": str(video_b), "source_signature": "sig-current"}
        assert app_module._project_matches_video(1, str(video_a)) is True

        # Different path and mismatched signature -> does not match.
        mock_get_project.return_value = {"source_video": str(video_b), "source_signature": "sig-other"}
        assert app_module._project_matches_video(1, str(video_a)) is False

        # No project found -> does not match.
        mock_get_project.return_value = None
        assert app_module._project_matches_video(1, str(video_a)) is False

    # Missing project_id or video_path short-circuits without touching get_project.
    assert app_module._project_matches_video(None, str(video_a)) is False
    assert app_module._project_matches_video(1, "") is False


def test_smart_cut_preserves_all_canonical_transcript_sources():
    source = inspect.getsource(app_module.api_cut_shorts)
    assert 'transcription_source_name = str(transcription.get("source") or "").strip().lower()' in source
    assert 'transcription_source_name == "public_subtitles"' in source
    assert 'transcription_source_name == "whisper"' in source
    assert "Transcrição já disponível; o motor não será executado novamente." in source


def test_smart_cut_uses_job_context_for_whisper_cancellation_and_transcript_provenance():
    source = inspect.getsource(app_module.api_cut_shorts)
    assert "cancel_check=ctx.check_cancel" in source
    assert "transcription.get(\"source\") or selected_transcription_mode" in source
    assert 'settings.get("whisper_model", "small")' in source
    assert "_transcription_from_request(data, duration=video_duration)" in source
    assert "transcript_archive = archive_transcription(" in source
    assert 'transcription["archive"] = transcript_archive' in source