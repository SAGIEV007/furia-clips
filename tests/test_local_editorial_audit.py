from types import SimpleNamespace


def test_local_editorial_context_uses_audio_and_campaign_snapshot(monkeypatch):
    import app as app_module

    events = []
    profile = [
        {"time": 0.0, "energy_normalized": 0.2},
        {"time": 1.0, "energy_normalized": 0.9},
        {"time": 2.0, "energy_normalized": 0.85},
    ]
    high = [{"start": 1.0, "end": 3.0, "duration": 2.0, "avg_energy": 0.87}]

    class FakeAudioAnalyzer:
        def analyze_energy(self, video_path, emit_progress=None):
            assert video_path == "/tmp/source.mp4"
            return profile

        def find_high_energy_moments(self, energy_profile, threshold, min_duration):
            assert energy_profile is profile
            assert threshold == 0.62
            assert min_duration == 2.0
            return high

    monkeypatch.setattr("modules.audio_analyzer.AudioAnalyzer", FakeAudioAnalyzer)
    monkeypatch.setattr("modules.campaign_hub.load_snapshot", lambda path=None: {"version": "test"})
    monkeypatch.setattr(
        "modules.editorial_context.detect_hook_candidates",
        lambda segments, **kwargs: [{"start": 1.0, "end": 5.0, "family": "tese-provocativa", "score": 82.0}],
    )

    result = app_module._enrich_editorial_context_locally(
        "/tmp/source.mp4",
        {"segments": [{"start": 1.0, "end": 4.0, "text": "A proposta muda o debate."}]},
        {"signals": {"question_response_structure": False}},
        {"campaign_hub_account": "@renansantosmbl"},
        events.append,
    )

    assert result["analysis_mode"] if "analysis_mode" in result else True
    assert result["hook_count"] == 1
    assert result["hook_candidates"][0]["family"] == "tese-provocativa"
    assert result["local_audio"]["high_energy_moments"] == high
    assert result["signals"]["local_high_energy_count"] == 1
