import json

import pytest

from modules.campaign_hub_memory import (
    MEMORY_SCHEMA_VERSION,
    install_snapshot,
    memory_status,
    normalize_memory_payload,
)


def _rich_payload():
    return {
        "schema_version": "campaign-hub-export-v1",
        "version": "chub-test-1",
        "collected_at": "2026-08-17T00:00:00Z",
        "default_account": "@renansantosmbl",
        "metadata": {
            "source_label": "authorized test export",
            "privacy_contract": {"raw_media_included": False, "credentials_included": False},
        },
        "accounts": {
            "@renansantosmbl": {
                "platform": "instagram",
                "hook_observations": [
                    {"hook": "tese-provocativa", "ratio": 1.1},
                    {"hook": "tese-provocativa", "ratio": 1.2},
                    {"hook": "tese-provocativa", "ratio": 1.3},
                ],
            },
            "@renansantosreserva": {"platform": "instagram", "hook_observations": []},
        },
        "records": {
            "blocks": [
                {
                    "id": "b354",
                    "start_s": 100,
                    "end_s": 200,
                    "self_contained": True,
                    "risk_flags": [],
                }
            ],
            "highlights": [{"block_id": "b354", "start_s": 120, "end_s": 145}],
            "sentences": [{"id": "s1", "speaker": "renan", "text": "A tese é clara."}],
        },
        "sync": {"cursor": "cursor-1", "status": "ready", "source": "authorized_export"},
    }


def test_normalize_memory_preserves_legacy_contract_and_rich_records():
    normalized = normalize_memory_payload(_rich_payload())

    assert normalized["memory_schema_version"] == MEMORY_SCHEMA_VERSION
    assert normalized["accounts"]["@renansantosmbl"]["hook_observations"]
    assert normalized["records"]["blocks"][0]["id"] == "b354"
    assert normalized["record_counts"]["highlights"] == 1
    assert normalized["sync"]["cursor"] == "cursor-1"


def test_install_snapshot_is_atomic_and_reports_bounded_status(tmp_path):
    destination = tmp_path / "campaign_hub" / "profile.json"

    status = install_snapshot(_rich_payload(), destination=destination)

    assert status["available"] is True
    assert status["status"] == "ready"
    assert status["manifest_present"] is True
    assert status["record_counts"]["blocks"] == 1
    assert destination.is_file()
    assert destination.with_name("manifest.json").is_file()

    manifest = json.loads(destination.with_name("manifest.json").read_text(encoding="utf-8"))
    assert manifest["snapshot_sha256"] == status["snapshot_sha256"]
    assert manifest["privacy_contract"]["raw_media_included"] is False
    assert "credentials" not in json.dumps(manifest).lower() or manifest["privacy_contract"]["credentials_included"] is False


def test_invalid_payload_does_not_replace_existing_snapshot(tmp_path):
    destination = tmp_path / "campaign_hub" / "profile.json"
    install_snapshot(_rich_payload(), destination=destination)
    before = destination.read_text(encoding="utf-8")

    with pytest.raises(ValueError):
        install_snapshot({"accounts": {"@unknown": {}}}, destination=destination)

    assert destination.read_text(encoding="utf-8") == before


def test_memory_status_is_missing_without_snapshot(tmp_path):
    status = memory_status(tmp_path / "missing.json")
    assert status["available"] is False
    assert status["status"] == "missing"
    assert status["read_only_runtime"] is True


def test_incremental_merge_preserves_old_records_and_updates_by_identity(tmp_path):
    destination = tmp_path / "campaign_hub" / "profile.json"
    first = _rich_payload()
    install_snapshot(first, destination=destination)

    second = _rich_payload()
    second["version"] = "chub-test-2"
    second["records"]["blocks"] = [
        {"id": "b354", "start_s": 101, "end_s": 201, "self_contained": True},
        {"id": "b355", "start_s": 201, "end_s": 240, "self_contained": False},
    ]
    result = install_snapshot(second, destination=destination, merge=True)

    assert result["version"] == "chub-test-2"
    assert result["record_counts"]["blocks"] == 2
    assert result["merge_stats"]["records_added"] == 1
    assert result["merge_stats"]["records_updated"] >= 1
