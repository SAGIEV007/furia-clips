"""The blocks a person already reviewed, found without anyone configuring a path.

Before this, the export existed only if an operator ran a script and pointed a
settings field at the result, so no run ever read one: every clip of the SBT
sabatina came back with ``bloco_chub: null`` while fourteen reviewed blocks sat
unused in the Acervo. The names below are the real ones a downloader produces.
"""

import json

import pytest

from modules.acervo_library import (
    describe_snapshot,
    find_snapshot_for,
    store_export,
    youtube_id_from_name,
)


def _block_payload(youtube_id="o6yEVC-exk8", title="Renan defende flexibilizar a CLT"):
    return {
        "items": [{
            "kind": "bloco",
            "id": "bloco-1",
            "title": title,
            "startS": 1215.96,
            "endS": 1509.96,
            "durationS": 294.0,
            "renanSpeaking": True,
            "triggerQuestion": "Como a flexibilização da CLT aumentaria o emprego?",
            "possibleCuts": 3,
            "video": {
                "id": "180a1e73-4cf7-4b5f-b67f-5a7ce9722471",
                "youtubeId": youtube_id,
                "title": "Renan Santos defende mudar CLT e criar mais presídios",
                "durationS": 1863,
            },
            "highlights": [{
                "sentenceIdx": 416,
                "startS": 1311.84,
                "endS": 1317.88,
                "text": "A gente quer falar em direito ao trabalho, vamos falar primeiro no direito mais óbvio.",
                "reason": "Formula a tese central do bloco.",
            }],
            "sentences": [],
        }]
    }


def test_the_youtube_id_survives_the_downloader_name():
    assert youtube_id_from_name(
        "YTDown.com_YouTube_Media_o6yEVC-exk8_001_1080p_b2b50a903b74.mp4"
    ) == "o6yEVC-exk8"
    assert youtube_id_from_name("3XJfcqn56Rw.mp4") == "3XJfcqn56Rw"


def test_a_name_without_an_id_asks_for_nothing():
    assert youtube_id_from_name("entrevista gravada agora.mp4") is None
    assert youtube_id_from_name("") is None
    # Eleven digits in a row are a date or a counter, never an id.
    assert youtube_id_from_name("gravacao_20260818123.mp4") is None


def test_an_export_is_filed_under_the_video_and_found_again(tmp_path):
    stored = store_export(_block_payload(), video_path="Media_o6yEVC-exk8_1080p.mp4", data_dir=tmp_path)

    assert stored["blocks"] == 1
    assert stored["highlights"] == 1
    assert stored["title"].startswith("Renan Santos")

    found = find_snapshot_for("outra-pasta/Media_o6yEVC-exk8_720p.mp4", data_dir=tmp_path)
    assert found is not None
    assert describe_snapshot(found)["blocks"] == 1


def test_blocks_from_another_video_are_refused(tmp_path):
    """Importing the wrong blocks would silently poison every cut of the source."""
    with pytest.raises(ValueError, match="Importe o export correspondente"):
        store_export(
            _block_payload(youtube_id="3XJfcqn56Rw"),
            video_path="Media_o6yEVC-exk8_1080p.mp4",
            data_dir=tmp_path,
        )


def test_an_export_with_no_blocks_is_refused(tmp_path):
    with pytest.raises(ValueError, match="nenhum bloco"):
        store_export({"items": []}, video_path="Media_o6yEVC-exk8.mp4", data_dir=tmp_path)


def test_a_source_with_no_export_says_so(tmp_path):
    assert find_snapshot_for("Media_o6yEVC-exk8.mp4", data_dir=tmp_path) is None
    assert describe_snapshot(None)["available"] is False


def test_the_stored_export_keeps_the_privacy_contract(tmp_path):
    stored = store_export(_block_payload(), video_path="Media_o6yEVC-exk8.mp4", data_dir=tmp_path)
    payload = json.loads(open(stored["path"], encoding="utf-8").read())

    assert payload["metadata"]["privacy_contract"]["raw_media_included"] is False
    assert payload["records"]["blocks"][0]["trigger_question"].startswith("Como a flexibilização")
