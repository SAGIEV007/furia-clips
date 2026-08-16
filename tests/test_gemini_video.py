from modules.gemini_video import GeminiVideoAnalyzer


def test_gemini_proxy_profile_gets_more_aggressive_for_long_sources():
    assert GeminiVideoAnalyzer._proxy_profile(5 * 60)["fps"] == "1"
    assert GeminiVideoAnalyzer._proxy_profile(30 * 60)["fps"] == "1/8"
    assert GeminiVideoAnalyzer._proxy_profile(60 * 60)["fps"] == "1/12"


def test_gemini_prompt_requests_timestamped_segments_and_audio_signals():
    prompt = GeminiVideoAnalyzer._build_prompt(
        {"description": "entrevista", "participant_confidence": 0.7},
        "priorize impostos",
    )
    assert "transcript_segments" in prompt
    assert "audio_visual_signals" in prompt
    assert "visual_observations" in prompt
    assert "fake_tweet" in prompt
    assert "visual_meme" in prompt
    assert "MM:SS" in prompt
    assert "priorize impostos" in prompt


def test_gemini_prompt_marks_editor_transcript_as_canonical():
    prompt = GeminiVideoAnalyzer._build_prompt(
        {"focus": "renan_santos", "transcript_reference": "[00:08:10.000] Não tenham medo."},
        "priorize o trecho sobre a ameaça",
    )
    assert "TRANSCRIÇÃO CANÔNICA FORNECIDA PELO EDITOR" in prompt
    assert "Não tenham medo" in prompt
    assert "não substitua a timeline" in prompt


def test_gemini_video_analyzer_extracts_non_thought_text():
    payload = {
        "candidates": [{
            "content": {"parts": [
                {"thought": True, "text": "internal"},
                {"text": '{"ok": true}'},
            ]}
        }]
    }
    assert GeminiVideoAnalyzer._extract_text(payload) == '{"ok": true}'


def test_gemini_video_analyzer_strips_json_fence():
    assert GeminiVideoAnalyzer._strip_fence("```json\n{\"ok\": true}\n```") == '{"ok": true}'


def test_gemini_generate_content_retries_transient_503(monkeypatch):
    from types import SimpleNamespace
    import modules.gemini_video as gemini_module

    responses = [
        SimpleNamespace(status_code=503, text="busy", json=lambda: {"error": {"message": "high demand"}}),
        SimpleNamespace(status_code=503, text="busy", json=lambda: {"error": {"message": "high demand"}}),
        SimpleNamespace(status_code=200, text="ok", json=lambda: {"ok": True}),
    ]
    calls = []

    class FakeSession:
        def post(self, endpoint, json, timeout):
            calls.append((endpoint, json, timeout))
            return responses.pop(0)

    analyzer = GeminiVideoAnalyzer("configured")
    analyzer.session = FakeSession()
    monkeypatch.setattr(gemini_module.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(gemini_module.random, "uniform", lambda left, right: 0.0)
    events = []
    response = analyzer._generate_content({"payload": True}, lambda message, level="info": events.append((message, level)))
    assert response.status_code == 200
    assert len(calls) == 3
    assert len(events) == 2
    assert all("503" in message for message, _ in events)


def test_gemini_prompt_does_not_assume_renan_for_generic_focus():
    prompt = GeminiVideoAnalyzer._build_prompt({"focus": "generic_political"}, "")
    assert "sem presumir a identidade" in prompt
    assert "critério editorial político genérico" in prompt


def test_gemini_prompt_keeps_renan_profile_when_focus_is_explicit():
    prompt = GeminiVideoAnalyzer._build_prompt({"focus": "renan_santos"}, "")
    assert "Renan Santos/MBL" in prompt
    assert "confirme a identidade no vídeo" in prompt
