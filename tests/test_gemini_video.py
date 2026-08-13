from modules.gemini_video import GeminiVideoAnalyzer


def test_gemini_prompt_requests_timestamped_segments_and_audio_signals():
    prompt = GeminiVideoAnalyzer._build_prompt(
        {"description": "entrevista", "participant_confidence": 0.7},
        "priorize impostos",
    )
    assert "transcript_segments" in prompt
    assert "audio_visual_signals" in prompt
    assert "MM:SS" in prompt
    assert "priorize impostos" in prompt


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
