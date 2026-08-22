import json
from unittest.mock import patch

import app as furia_app

import modules.editorial_search as editorial_search
from modules.editorial_search import search_cached_campaign_hub


def _write_snapshot(path, channel, rows, total=10):
    path.write_text(
        json.dumps({"mode": "semantic", "channel": channel, "platform": "instagram", "totalMentions": total, "results": rows}),
        encoding="utf-8",
    )


def test_search_accepts_items_and_data_snapshot_envelopes(tmp_path):
    (tmp_path / "items.json").write_text(json.dumps({
        "mode": "semantic",
        "items": [{
            "url": "https://www.instagram.com/reel/items-format/",
            "channel": "@renansantosmbl",
            "platform": "instagram",
            "similarity": 0.8,
            "transcript": "Lula e segurança pública",
        }],
    }), encoding="utf-8")
    (tmp_path / "data.json").write_text(json.dumps({
        "mode": "semantic",
        "data": {"rows": [{
            "url": "https://www.instagram.com/reel/data-format/",
            "channel": "@renansantosmbl",
            "platform": "instagram",
            "similarity": 0.7,
            "transcript": "Lula e economia",
        }]},
    }), encoding="utf-8")

    result = search_cached_campaign_hub("Lula", cache_dir=tmp_path, limit=10)

    assert {item["url"] for item in result["results"]} == {
        "https://www.instagram.com/reel/items-format/",
        "https://www.instagram.com/reel/data-format/",
    }


def test_search_inherits_account_and_platform_from_snapshot_envelope(tmp_path):
    _write_snapshot(tmp_path / "envelope-only.json", "@renansantosmbl", [{
        "url": "https://www.instagram.com/reel/envelope-only/",
        "similarity": 0.8,
        "fullScript": "Lula e segurança pública",
    }])

    result = search_cached_campaign_hub("Lula segurança", cache_dir=tmp_path)

    assert result["counts"]["accounts"] == {"@renansantosmbl": 1}
    assert result["results"][0]["channel"] == "@renansantosmbl"
    assert result["results"][0]["platform"] == "instagram"


def test_search_ranks_semantic_and_account_local_performance(tmp_path):
    _write_snapshot(tmp_path / "main.json", "@renansantosmbl", [
        {
            "url": "https://www.instagram.com/reel/main-1/",
            "channel": "@renansantosmbl",
            "platform": "instagram",
            "similarity": 0.70,
            "ratio": 5.0,
            "fullScript": "Lula e a segurança pública no Brasil",
        },
        {
            "url": "https://www.instagram.com/reel/main-2/",
            "channel": "@renansantosmbl",
            "platform": "instagram",
            "similarity": 0.55,
            "ratio": 20.0,
            "fullScript": "economia e impostos",
        },
    ])
    _write_snapshot(tmp_path / "reserve.json", "@renansantosreserva", [
        {
            "url": "https://www.instagram.com/reel/reserve-1/",
            "channel": "@renansantosreserva",
            "platform": "instagram",
            "similarity": 0.65,
            "ratio": 1.0,
            "fullScript": "O Lula e o avanço do crime organizado",
        },
    ])

    result = search_cached_campaign_hub("Lula segurança", cache_dir=tmp_path, limit=10)

    assert result["read_only"] is True
    assert result["source"] == "campaign_hub_local_snapshot"
    assert result["counts"]["accounts"] == {"@renansantosmbl": 2, "@renansantosreserva": 1}
    assert result["results"][0]["url"].endswith("main-1/")
    assert result["results"][0]["performance_ratio"] == 5.0


def test_search_uses_transcript_field_as_lexical_evidence(tmp_path):
    _write_snapshot(tmp_path / "transcript.json", "@renansantosmbl", [{
        "url": "https://www.instagram.com/reel/transcript-field/",
        "channel": "@renansantosmbl",
        "platform": "instagram",
        "similarity": 0.0,
        "transcript": "Lula e segurança pública em debate",
    }])

    result = search_cached_campaign_hub("Lula segurança", cache_dir=tmp_path)

    assert result["results"][0]["lexical_match"] == 1.0
    assert result["results"][0]["full_script"] == "Lula e segurança pública em debate"


def test_search_joins_segmented_transcript_evidence(tmp_path):
    _write_snapshot(tmp_path / "segments.json", "@renansantosmbl", [{
        "url": "https://www.instagram.com/reel/segments-field/",
        "channel": "@renansantosmbl",
        "platform": "instagram",
        "similarity": 0.0,
        "segments": [{"start": 0, "text": "Lula"}, {"start": 2, "text": "e segurança pública"}],
    }])

    result = search_cached_campaign_hub("Lula segurança", cache_dir=tmp_path)

    assert result["results"][0]["lexical_match"] == 1.0
    assert result["results"][0]["full_script"] == "Lula e segurança pública"


def test_search_rejects_null_or_invalid_timestamp_evidence(tmp_path):
    _write_snapshot(tmp_path / "invalid-timing.json", "@renansantosmbl", [
        {
            "url": "https://www.instagram.com/reel/invalid-timing/",
            "channel": "@renansantosmbl",
            "platform": "instagram",
            "similarity": 0.8,
            "start": None,
            "segments": [{"start": "x", "end": "y", "text": "Lula e segurança pública"}],
            "fullScript": "Lula e segurança pública",
        }
    ])

    result = search_cached_campaign_hub("Lula segurança", cache_dir=tmp_path)
    item = result["results"][0]

    assert item["has_timestamps"] is False
    assert item["download_eligible"] is False
    assert item["download_status"] == "link_only_no_timestamps"


def test_search_accepts_real_timecode_strings_as_timestamp_evidence(tmp_path):
    _write_snapshot(tmp_path / "timecode.json", "@renansantosmbl", [{
        "url": "https://www.instagram.com/reel/timecode/",
        "channel": "@renansantosmbl",
        "platform": "instagram",
        "similarity": 0.8,
        "segments": [{"start": "01:02", "end": "01:08", "text": "Lula e segurança pública"}],
    }])

    result = search_cached_campaign_hub("Lula", cache_dir=tmp_path)

    assert result["results"][0]["has_timestamps"] is True
    assert result["results"][0]["download_eligible"] is True


def test_search_rejects_arbitrary_timestamp_text(tmp_path):
    _write_snapshot(tmp_path / "text-timing.json", "@renansantosmbl", [{
        "url": "https://www.instagram.com/reel/text-timing/",
        "channel": "@renansantosmbl",
        "platform": "instagram",
        "similarity": 0.8,
        "start": "timestamp unavailable",
        "timecode": "later",
        "fullScript": "Lula e segurança pública",
    }])

    result = search_cached_campaign_hub("Lula", cache_dir=tmp_path)

    assert result["results"][0]["has_timestamps"] is False
    assert result["results"][0]["download_eligible"] is False


def test_search_marks_link_without_timestamps_as_not_download_eligible(tmp_path):
    _write_snapshot(tmp_path / "main.json", "@renansantosmbl", [{
        "url": "https://www.instagram.com/reel/main-1/",
        "channel": "@renansantosmbl",
        "platform": "instagram",
        "similarity": 0.8,
        "fullScript": "Lula e o governo",
    }])

    result = search_cached_campaign_hub("Lula", cache_dir=tmp_path)
    item = result["results"][0]

    assert item["has_timestamps"] is False
    assert item["download_eligible"] is False
    assert item["download_status"] == "link_only_no_timestamps"


def test_search_can_scope_one_account_and_deduplicate_urls(tmp_path):
    row = {
        "url": "https://www.instagram.com/reel/shared/",
        "channel": "@renansantosmbl",
        "platform": "instagram",
        "similarity": 0.7,
        "fullScript": "Lula fala sobre crime",
    }
    _write_snapshot(tmp_path / "first.json", "@renansantosmbl", [row])
    _write_snapshot(tmp_path / "second.json", "@renansantosmbl", [row])
    _write_snapshot(tmp_path / "reserve.json", "@renansantosreserva", [{
        **row,
        "url": "https://www.instagram.com/reel/reserve/",
        "channel": "@renansantosreserva",
    }])

    result = search_cached_campaign_hub("Lula crime", account="@renansantosmbl", cache_dir=tmp_path)

    assert len(result["results"]) == 1
    assert result["results"][0]["channel"] == "@renansantosmbl"


def test_search_scopes_partidomissao_without_cross_account_rows(tmp_path):
    _write_snapshot(tmp_path / "main.json", "@renansantosmbl", [{
        "url": "https://www.instagram.com/reel/main-topic/",
        "channel": "@renansantosmbl",
        "platform": "instagram",
        "similarity": 0.9,
        "fullScript": "Lula e segurança pública",
    }])
    _write_snapshot(tmp_path / "reserva.json", "@renansantosreserva", [{
        "url": "https://www.instagram.com/reel/reserva-topic/",
        "channel": "@renansantosreserva",
        "platform": "instagram",
        "similarity": 0.8,
        "fullScript": "Lula e segurança pública",
    }])
    _write_snapshot(tmp_path / "missao.json", "@partidomissao", [{
        "url": "https://www.instagram.com/reel/missao-topic/",
        "channel": "@partidomissao",
        "platform": "instagram",
        "similarity": 0.7,
        "fullScript": "Lula e segurança pública",
    }])

    result = search_cached_campaign_hub("Lula segurança", account="@partidomissao", cache_dir=tmp_path)

    assert result["counts"]["accounts"] == {"@partidomissao": 1}
    assert len(result["results"]) == 1
    assert result["results"][0]["channel"] == "@partidomissao"


def test_search_preserves_same_url_across_distinct_accounts(tmp_path):
    shared_url = "https://www.instagram.com/reel/shared-crosspost/"
    _write_snapshot(tmp_path / "main.json", "@renansantosmbl", [{
        "url": shared_url,
        "channel": "@renansantosmbl",
        "platform": "instagram",
        "similarity": 0.7,
        "ratio": 5.0,
        "fullScript": "Lula e segurança pública",
    }])
    _write_snapshot(tmp_path / "reserve.json", "@renansantosreserva", [{
        "url": shared_url,
        "channel": "@renansantosreserva",
        "platform": "instagram",
        "similarity": 0.7,
        "ratio": 1.0,
        "fullScript": "Lula e segurança pública",
    }])

    result = search_cached_campaign_hub("Lula segurança", cache_dir=tmp_path)

    assert len(result["results"]) == 2
    assert {item["channel"] for item in result["results"]} == {"@renansantosmbl", "@renansantosreserva"}


def test_search_filters_by_published_date_without_treating_missing_date_as_match(tmp_path):
    _write_snapshot(tmp_path / "dated.json", "@renansantosmbl", [
        {
            "url": "https://www.instagram.com/reel/old/",
            "channel": "@renansantosmbl",
            "platform": "instagram",
            "similarity": 0.8,
            "publishedAt": "2026-01-10T12:00:00Z",
            "fullScript": "Lula e segurança pública",
        },
        {
            "url": "https://www.instagram.com/reel/new/",
            "channel": "@renansantosmbl",
            "platform": "instagram",
            "similarity": 0.7,
            "published_at": "2026-08-15",
            "fullScript": "Lula e segurança pública",
        },
        {
            "url": "https://www.instagram.com/reel/unknown/",
            "channel": "@renansantosmbl",
            "platform": "instagram",
            "similarity": 0.95,
            "fullScript": "Lula e segurança pública",
        },
    ])

    result = search_cached_campaign_hub(
        "Lula segurança",
        published_from="2026-08-01",
        published_to="2026-08-31",
        cache_dir=tmp_path,
    )

    assert [item["url"] for item in result["results"]] == ["https://www.instagram.com/reel/new/"]
    assert result["results"][0]["published_at"] == "2026-08-15"
    assert result["published_from"] == "2026-08-01"
    assert result["published_to"] == "2026-08-31"


def test_search_returns_published_date_fallback_from_snapshot(tmp_path):
    _write_snapshot(tmp_path / "date-field.json", "@renansantosmbl", [{
        "url": "https://www.instagram.com/reel/date-field/",
        "channel": "@renansantosmbl",
        "platform": "instagram",
        "similarity": 0.8,
        "publishedDate": "2026-08-16",
        "fullScript": "Lula e segurança pública",
    }])

    result = search_cached_campaign_hub("Lula segurança", cache_dir=tmp_path)

    assert result["results"][0]["published_at"] == "2026-08-16"


def test_search_rejects_inverted_date_range(tmp_path):
    try:
        search_cached_campaign_hub("Lula", published_from="2026-08-31", published_to="2026-08-01", cache_dir=tmp_path)
    except ValueError as exc:
        assert "posterior" in str(exc)
    else:
        raise AssertionError("inverted date range should be rejected")


def test_search_empty_cache_returns_successful_empty_result(tmp_path):
    result = search_cached_campaign_hub("Lula", cache_dir=tmp_path)
    assert result["success"] is True
    assert result["read_only"] is True
    assert result["results"] == []
    assert result["total_cached_matches"] == 0
    assert result["counts"]["with_timestamps"] == 0


def test_search_rejects_empty_query(tmp_path):
    try:
        search_cached_campaign_hub("", cache_dir=tmp_path)
    except ValueError as exc:
        assert "assunto" in str(exc)
    else:
        raise AssertionError("empty query should be rejected")


def test_search_exposes_garimpo_style_block_dossier_and_nested_video(tmp_path):
    _write_snapshot(tmp_path / "acervo-block.json", "@renansantosmbl", [{
        "id": "block-123",
        "blockVersionId": "version-123",
        "sentenceTableId": "sentences-123",
        "semanticScore": 0.81,
        "title": "Segurança pública precisa de investigação",
        "summary": "A tese defende integração das polícias e investigação criminal.",
        "category": "Segurança Pública",
        "topics": ["Segurança pública", "investigação"],
        "startS": 120.5,
        "endS": 180.5,
        "possibleCuts": 4,
        "densityRank": 96,
        "selfContainedRank": 72,
        "needsContext": True,
        "triggerQuestion": "Como melhorar a segurança pública?",
        "riskFlags": ["número"],
        "gateWarnings": ["conferir áudio"],
        "trustTier": "owner",
        "selfContainedReason": "A tese é clara, mas depende de contexto institucional.",
        "moments": [{
            "startS": 130.0,
            "endS": 150.0,
            "label": "Momento forte",
            "reason": "Apresenta uma proposta concreta.",
        }],
        "video": {
            "url": "https://www.youtube.com/watch?v=source-123",
            "youtubeId": "source-123",
            "title": "Entrevista longa sobre segurança pública",
            "platform": "youtube",
            "publishedAt": "2026-08-01T12:00:00Z",
            "durationS": 3600,
        },
    }])

    result = search_cached_campaign_hub("segurança pública", cache_dir=tmp_path, platform="youtube")
    item = result["results"][0]

    assert item["block_id"] == "block-123"
    assert item["title"] == "Segurança pública precisa de investigação"
    assert item["source_title"] == "Entrevista longa sobre segurança pública"
    assert item["source_video_id"] == "source-123"
    assert item["source_platform"] == "youtube"
    assert item["source_published_at"] == "2026-08-01T12:00:00Z"
    assert item["source_preview_url"] == "https://www.youtube.com/watch?v=source-123&t=120s"
    assert item["source_preview_kind"] == "youtube_timestamped"
    assert item["source_preview_available"] is True
    assert item["start_seconds"] == 120.5
    assert item["end_seconds"] == 180.5
    assert item["duration_seconds"] == 60.0
    assert item["has_timestamps"] is True
    assert item["download_eligible"] is True
    assert item["needs_context"] is True
    assert item["trigger_question"] == "Como melhorar a segurança pública?"
    assert item["moments"][0]["start_seconds"] == 130.0
    assert item["moments"][0]["preview_url"] == "https://www.youtube.com/watch?v=source-123&t=130s"
    assert item["risk_flags"] == ["número"]


def test_remote_preview_drops_signed_query_and_rejects_non_youtube_sources(tmp_path):
    _write_snapshot(tmp_path / "sources.json", "@renansantosmbl", [
        {
            "url": "https://example.com/video?id=abc",
            "platform": "vimeo",
            "similarity": 0.8,
            "startS": 10,
            "endS": 20,
            "video": {
                "url": "https://youtu.be/AbCdEfGhI12?si=temporary&feature=share",
                "youtubeId": "AbCdEfGhI12",
                "platform": "youtube",
            },
            "moments": [{"startS": 12, "endS": 15, "reason": "tese"}],
            "fullScript": "Lula e segurança pública",
        },
    ])

    result = search_cached_campaign_hub("Lula segurança", platform="youtube", cache_dir=tmp_path)
    item = result["results"][0]

    assert item["source_preview_url"] == "https://www.youtube.com/watch?v=AbCdEfGhI12&t=10s"
    assert item["moments"][0]["preview_url"] == "https://www.youtube.com/watch?v=AbCdEfGhI12&t=12s"
    assert "si=" not in item["source_preview_url"]


def test_editorial_search_endpoint_passes_date_filters_and_remains_read_only():
    client = furia_app.app.test_client()
    expected = {
        "success": True,
        "source": "campaign_hub_local_snapshot",
        "read_only": True,
        "results": [],
        "counts": {"with_timestamps": 0, "download_eligible": 0},
    }
    with patch.object(furia_app, "search_cached_campaign_hub", return_value=expected) as search:
        response = client.post(
            "/api/editorial/search",
            json={"query": "Lula", "date_from": "2026-08-01", "date_to": "2026-08-17"},
        )
    assert response.status_code == 200
    assert response.get_json()["read_only"] is True
    search.assert_called_once_with(
        "Lula",
        account=None,
        platform=None,
        published_from="2026-08-01",
        published_to="2026-08-17",
        limit=25,
    )



def test_search_reads_rich_acervo_blocks_from_profile_snapshot(tmp_path):
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({
        "accounts": {
            "@renansantosmbl": {
                "acervo_blocks": [{
                    "id": "block-1",
                    "title": "Segurança pública e resposta concreta",
                    "summary": "A tese fala de segurança pública e combate ao crime.",
                    "startS": 120,
                    "endS": 180,
                    "densityRank": 95,
                    "video": {
                        "youtubeId": "AbCdEfGhI12",
                        "youtubeUrl": "https://youtu.be/AbCdEfGhI12",
                        "title": "Live de teste",
                        "platform": "youtube",
                    },
                    "highlights": [{"startS": 130, "endS": 145, "text": "A resposta precisa ser concreta.", "reason": "tese"}],
                }]
            }
        }
    }), encoding="utf-8")

    with patch.object(editorial_search, "DEFAULT_PROFILE_PATH", profile):
        result = search_cached_campaign_hub("segurança pública", account="@renansantosmbl", platform="youtube", cache_dir=tmp_path)

    assert result["returned"] == 1
    item = result["results"][0]
    assert item["block_id"] == "block-1"
    assert item["has_timestamps"] is True
    assert item["source_preview_url"] == "https://www.youtube.com/watch?v=AbCdEfGhI12&t=120s"
    assert item["moments"][0]["preview_url"] == "https://www.youtube.com/watch?v=AbCdEfGhI12&t=130s"
    assert result["read_only"] is True
