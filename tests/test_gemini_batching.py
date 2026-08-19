"""Sending a long source to Gemini in pieces, and surviving a piece that fails.

The whole transcript went in one request — the function's own docstring said so.
On the press conference of 18/08/2026 that was 28 blocks in a single prompt; it
timed out at 180 seconds, the run fell to keyword selection, and every clip that
came out of it was a fixed-length tile. The editor called the result random.

Two properties matter here and neither existed. Work is split, so no single
request has to carry a two-hour video. And a lot that fails costs only its own
share: partial evidence beats no evidence.
"""

from modules.clip_selector import ClipSelector


def _transcription(blocks=20):
    return {"segments": [
        {"start": index * 30.0, "end": index * 30.0 + 29.0,
         "text": f"Frase completa número {index} com assunto próprio e conclusão."}
        for index in range(blocks * 3)
    ]}


def _selector():
    return ClipSelector(target_duration=45, max_clips=20, min_duration=20, max_duration=600)


def test_the_transcript_is_split_into_lots(monkeypatch):
    selector = _selector()
    seen = []

    def fake_lot(blocks, *args, **kwargs):
        seen.append(len(blocks))
        return []

    monkeypatch.setattr(selector, "_gemini_lot", fake_lot)
    selector._select_with_gemini(
        _transcription()["segments"], None, "", {"gemini_api_key": "x"}, None
    )

    assert len(seen) > 1, "a transcrição inteira voltou a ir numa requisição só"
    assert max(seen) <= ClipSelector.GEMINI_BLOCKS_PER_REQUEST


def test_a_failed_lot_does_not_discard_the_others(monkeypatch):
    """The behaviour that turned one timeout into a whole bad run."""
    selector = _selector()
    calls = {"n": 0}

    def fake_lot(blocks, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return None  # este lote falhou
        return [{"start": 10.0, "end": 40.0, "text": "trecho", "viral_score": 70}]

    monkeypatch.setattr(selector, "_gemini_lot", fake_lot)
    found = selector._select_with_gemini(
        _transcription()["segments"], None, "", {"gemini_api_key": "x"}, None
    )

    assert found, "um lote perdido apagou todos os outros"
    assert calls["n"] > 1


def test_candidates_come_back_ranked(monkeypatch):
    selector = _selector()
    scores = iter([40, 90, 65, 80, 55, 70, 30, 85])

    def fake_lot(blocks, *args, **kwargs):
        return [{"start": 0.0, "end": 30.0, "text": "t", "viral_score": next(scores, 10)}]

    monkeypatch.setattr(selector, "_gemini_lot", fake_lot)
    found = selector._select_with_gemini(
        _transcription()["segments"], None, "", {"gemini_api_key": "x"}, None
    )

    assert [item["viral_score"] for item in found] == sorted(
        (item["viral_score"] for item in found), reverse=True
    )


def test_no_api_key_is_not_an_error(monkeypatch):
    assert _selector()._select_with_gemini([], None, "", {}, None) == []
