from modules.campaign_hub_memory import install_snapshot
from modules.editorial_block_memory import get_block, list_blocks


def _payload():
    return {
        "version": "blocks-test",
        "default_account": "@renansantosmbl",
        "accounts": {"@renansantosmbl": {"platform": "youtube", "hook_observations": []}},
        "records": {
            "sources": [{"id": "video-1", "title": "Evento", "duration_s": 600}],
            "blocks": [
                {
                    "id": "block-a",
                    "video_id": "video-1",
                    "title": "Renan convoca o evento",
                    "summary": "Convocação com contexto.",
                    "topics": ["campanha", "evento"],
                    "start_s": 100,
                    "end_s": 140,
                    "renan_speaking": True,
                    "trigger_question": "Qual é o próximo ato?",
                    "possible_cuts": 2,
                },
                {
                    "id": "block-b",
                    "video_id": "video-1",
                    "title": "Outra fala",
                    "summary": "Outro contexto.",
                    "start_s": 200,
                    "end_s": 250,
                    "renan_speaking": False,
                },
            ],
            "highlights": [{"id": "highlight-a", "block_id": "block-a", "start_s": 110, "end_s": 120, "text": "Vamos ao evento.", "reason": "convocação"}],
            "sentences": [{"id": "sentence-a", "block_id": "block-a", "start_s": 100, "end_s": 110, "text": "Vamos ao evento."}],
        },
    }


def test_list_blocks_filters_and_keeps_highlights(tmp_path):
    path = tmp_path / "profile.json"
    install_snapshot(_payload(), destination=path)

    result = list_blocks(str(path), query="convoca", renan_speaking=True)

    assert result["available"] is True
    assert result["total"] == 1
    assert result["blocks"][0]["id"] == "block-a"
    assert result["blocks"][0]["highlight_count"] == 1
    assert result["blocks"][0]["source"]["title"] == "Evento"


def test_get_block_includes_bounded_sentences(tmp_path):
    path = tmp_path / "profile.json"
    install_snapshot(_payload(), destination=path)

    block = get_block("block-a", str(path))

    assert block["trigger_question"] == "Qual é o próximo ato?"
    assert block["sentences"][0]["text"] == "Vamos ao evento."


def test_prioritize_renan_keeps_other_speakers_visible(tmp_path):
    path = tmp_path / "profile.json"
    install_snapshot(_payload(), destination=path)

    result = list_blocks(str(path), prioritize_renan=True)

    assert result["total"] == 2
    assert [item["id"] for item in result["blocks"]] == ["block-a", "block-b"]


def test_source_ref_filters_to_the_matching_video(tmp_path):
    payload = _payload()
    payload["records"]["sources"][0]["youtube_id"] = "abc12345678"
    path = tmp_path / "profile.json"
    install_snapshot(payload, destination=path)

    result = list_blocks(str(path), source_ref="abc12345678")

    assert result["total"] == 2
    assert all(item["source"]["youtube_id"] == "abc12345678" for item in result["blocks"])
