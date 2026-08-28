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
    assert prompt.count("[00:08:10.000] Não tenham medo.") == 1


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


def test_gemini_proxy_and_total_budgets_are_finite_and_proportional():
    assert GeminiVideoAnalyzer._proxy_timeout(5 * 60) >= GeminiVideoAnalyzer.PROXY_TIMEOUT_MIN_S
    assert GeminiVideoAnalyzer._proxy_timeout(2 * 60 * 60) <= GeminiVideoAnalyzer.PROXY_TIMEOUT_MAX_S
    assert GeminiVideoAnalyzer._multimodal_total_timeout(10 * 60) < GeminiVideoAnalyzer._multimodal_total_timeout(60 * 60)
    assert GeminiVideoAnalyzer._multimodal_total_timeout(8 * 60 * 60) == GeminiVideoAnalyzer.MULTIMODAL_TOTAL_MAX_S


def test_gemini_activation_timeout_is_bounded(monkeypatch):
    from types import SimpleNamespace
    import modules.gemini_video as gemini_module
    from modules.gemini_video import GeminiVideoError

    analyzer = GeminiVideoAnalyzer("configured")
    calls = []

    class FakeSession:
        def get(self, endpoint, timeout):
            calls.append((endpoint, timeout))
            return SimpleNamespace(status_code=200, json=lambda: {"state": "PROCESSING"})

    analyzer.session = FakeSession()
    clock = [100.0]
    monkeypatch.setattr(gemini_module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(gemini_module.time, "sleep", lambda seconds: clock.__setitem__(0, clock[0] + seconds))

    try:
        analyzer._wait_until_active("files/1", timeout_seconds=2)
    except GeminiVideoError as exc:
        assert "Tempo limite de 2s" in str(exc)
    else:
        raise AssertionError("a espera de ativação não respeitou o limite")

    assert calls and all(timeout <= 2 for _, timeout in calls)


def test_gemini_activation_propagates_cancel(monkeypatch):
    import modules.gemini_video as gemini_module
    from modules.cancellation import OperationCancelled

    analyzer = GeminiVideoAnalyzer("configured")
    monkeypatch.setattr(gemini_module.time, "monotonic", lambda: 100.0)

    def cancel():
        raise OperationCancelled()

    try:
        analyzer._wait_until_active("files/1", cancel_check=cancel, timeout_seconds=60)
    except OperationCancelled:
        pass
    else:
        raise AssertionError("o cancelamento foi engolido durante a ativação")


def test_gemini_generation_does_not_call_api_after_deadline(monkeypatch):
    import modules.gemini_video as gemini_module
    from modules.gemini_video import GeminiVideoError

    analyzer = GeminiVideoAnalyzer("configured")
    calls = []

    class FakeSession:
        def post(self, *args, **kwargs):
            calls.append(kwargs)
            raise AssertionError("API chamada depois do deadline")

    analyzer.session = FakeSession()
    monkeypatch.setattr(gemini_module.time, "monotonic", lambda: 100.0)

    try:
        analyzer._generate_content({}, deadline=99.0)
    except GeminiVideoError as exc:
        assert "limite total" in str(exc)
    else:
        raise AssertionError("o deadline expirado não foi reportado")
    assert calls == []


def test_gemini_proxy_does_not_start_ffmpeg_after_deadline(monkeypatch):
    from pathlib import Path
    import modules.gemini_video as gemini_module
    from modules.gemini_video import GeminiVideoError

    analyzer = GeminiVideoAnalyzer("configured")
    monkeypatch.setattr(gemini_module.time, "monotonic", lambda: 100.0)
    monkeypatch.setattr(gemini_module.GeminiVideoAnalyzer, "_check_budget", classmethod(lambda cls, deadline: (_ for _ in ()).throw(GeminiVideoError("limite total"))))

    def should_not_run(*args, **kwargs):
        raise AssertionError("FFmpeg iniciado após o deadline")

    monkeypatch.setattr("modules.video_cutter.VideoCutter._run_ffmpeg", should_not_run)
    try:
        analyzer._prepare_analysis_media(Path("source.mp4"), duration_seconds=60, deadline=99.0)
    except GeminiVideoError as exc:
        assert "limite total" in str(exc)
    else:
        raise AssertionError("o deadline ignorou o limite")


def test_gemini_recovers_only_complete_top_level_fields_from_truncated_json():
    text = '{"source_identity":{"status":"validated","confidence":0.9},"global_description":"entrevista","focus_windows":[{"start":"00:10"'
    parsed = GeminiVideoAnalyzer._parse_complete_top_level_fields(text)
    assert parsed == {
        "source_identity": {"status": "validated", "confidence": 0.9},
        "global_description": "entrevista",
    }


def test_gemini_does_not_recover_non_json_truncation():
    import json
    try:
        GeminiVideoAnalyzer._parse_complete_top_level_fields("resposta incompleta")
    except json.JSONDecodeError:
        pass
    else:
        raise AssertionError("texto sem propriedades JSON não deveria ser recuperado")
