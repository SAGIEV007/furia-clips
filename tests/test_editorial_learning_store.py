from modules.editorial_learning_store import (
    save_clip_decision,
    save_context_bundle,
    save_headline_decision,
    save_headline_generation,
    save_transcription_bundle,
    session_dir,
    write_session_manifest,
)


def test_editorial_session_store_keeps_transcript_context_headlines_and_decisions(tmp_path, monkeypatch):
    monkeypatch.setenv("FURIA_EDITORIAL_SESSIONS_DIR", str(tmp_path))
    transcription = {
        "source": "manual",
        "full_text": "Uma tese completa.",
        "segments": [{"start": 1.0, "end": 3.0, "text": "Uma tese completa."}],
        "segment_count": 1,
        "language": "pt",
    }
    selection = {**transcription, "selection_scope": "live_content"}
    files = save_transcription_bundle(
        transcription,
        project_id=7,
        source_video="/tmp/renan-live.mp4",
        selection_transcription=selection,
    )
    context_file = save_context_bundle(
        {"analysis_mode": "transcript_plus_local_audio"},
        transcription_provenance={"source": "manual", "confirmed_by_editor": True},
        project_id=7,
        source_video="/tmp/renan-live.mp4",
    )
    headline_file = save_headline_generation(
        {"transcript": transcription["full_text"], "preferred_format": "vertical_916"},
        {"topic": "segurança"},
        project_id=7,
        clip_id=3,
        source_video="/tmp/renan-live.mp4",
    )
    headline_decision = save_headline_decision(
        {"format_id": "vertical_916", "artwork_text": "NÃO TENHA MEDO", "action": "selected"},
        project_id=7,
        clip_id=3,
        source_video="/tmp/renan-live.mp4",
    )
    clip_decision = save_clip_decision(
        {"action": "approved", "reason_code": "context_complete"},
        project_id=7,
        clip_id=3,
        source_video="/tmp/renan-live.mp4",
    )
    manifest = write_session_manifest(
        project_id=7,
        source_video="/tmp/renan-live.mp4",
        transcription_provenance={"source": "manual"},
        context_status={"analysis_mode": "transcript_plus_local_audio"},
    )

    folder = session_dir(7, source_video="/tmp/renan-live.mp4")
    # The test uses the same environment variable as the local application.
    assert files["transcription_text"].endswith("transcription.txt")
    assert context_file.endswith("context_latest.json")
    assert headline_file.endswith("headline_generations.jsonl")
    assert headline_decision.endswith("headline_decisions.jsonl")
    assert clip_decision.endswith("clip_decisions.jsonl")
    assert manifest.endswith("manifest.json")
    assert "Uma tese completa." in __import__("pathlib").Path(files["transcription_text"]).read_text(encoding="utf-8")
    assert folder.exists()
