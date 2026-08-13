from modules.clip_selector import ClipSelector


def test_manual_long_segment_generates_clip_without_context():
    transcription = {
        "segments": [{
            "start": 0.0,
            "end": 40.0,
            "text": "O candidato explica a proposta, apresenta os dados e conclui o raciocínio com clareza.",
        }],
    }
    selector = ClipSelector(target_duration=30, max_clips=15, min_duration=20, max_duration=180)
    clips = selector.select_clips(
        transcription,
        energy_profile=[],
        user_context="",
        settings={"ai_backend": "ollama", "ollama_url": "http://127.0.0.1:9"},
    )
    assert clips
    assert clips[0]["duration"] >= 20
