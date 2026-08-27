import json

import pytest

from modules.editorial_disagreement import (
    SCHEMA_VERSION,
    build_disagreement_record,
    summarize_records,
)
from modules.editorial_learning_store import load_disagreement_records, save_disagreement_record


def _clip(**overrides):
    clip = {
        "id": 7,
        "editorial_key": "abc123",
        "start_time": 12.0,
        "end_time": 28.0,
        "duration": 16.0,
        "viral_score": 91,
        "score_confidence": 0.82,
        "editorial_score_version": "furia1-v1",
        "transcript": "texto privado que não deve entrar na matriz",
        "score_factors": json.dumps({
            "flow": 90,
            "_review_flags": {"context_complete": False, "qa_bridge": True},
            "_review_metadata": {"candidate_origin": "local_primary", "selection_source": "nlp", "confidence": 0.82},
        }),
        "review_required": True,
        "review_reasons": ["confirmar conclusão no áudio"],
        "multimodal_editorial_review": {
            "status": "review",
            "identity_status": "validated",
            "identity_confidence": 0.9,
            "flags": ["multimodal_question_only_suspected"],
            "qa_evidence": [{
                "overlap_seconds": 4.5,
                "confidence": 0.8,
                "question_present": True,
                "answer_present": False,
                "renan_focus": True,
                "overlap_suspected": False,
                "reason": "a pergunta parece ocupar a abertura",
                "start": 12,
                "end": 16,
            }],
            "message": "Confira o player.",
        },
    }
    clip.update(overrides)
    return clip


def test_matrix_keeps_automatic_audiovisual_chub_and_human_namespaces_separate():
    record = build_disagreement_record(
        _clip(),
        {"action": "approved", "reason_code": "excellent_context", "quality_tags": ["payoff_confirmed"], "note": "revisado no player"},
        project_context={
            "available": True,
            "source": "campaign-hub",
            "channel": "@renansantosmbl",
            "schemaVersion": "2",
            "fetchedAt": "2026-08-27T16:48:53Z",
            "recordCounts": {"blocks": 19},
            "readOnly": True,
            "scoreTechnical": False,
        },
    )
    assert record["schema_version"] == SCHEMA_VERSION
    assert record["automatic"]["score"] == 91
    assert record["automatic"]["flags"]["context_complete"] is False
    assert record["audiovisual"]["identity_status"] == "validated"
    assert record["chub"]["channel"] == "@renansantosmbl"
    assert record["chub"]["record_counts"]["blocks"] == 19
    assert record["human"]["decision"] == "approved"
    assert record["human"]["reason_code"] == "excellent_context"
    assert record["measurement"]["score_used_as_decision"] is False
    serialized = json.dumps(record, ensure_ascii=False)
    assert "texto privado que não deve entrar na matriz" not in serialized
    assert "revisado no player" not in serialized


def test_matrix_rejects_non_final_action():
    with pytest.raises(ValueError, match="decisões finais"):
        build_disagreement_record(_clip(), {"action": "adjusted"})


def test_summary_is_descriptive_and_counts_warning_human_approval():
    first = build_disagreement_record(_clip(), {"action": "approved", "reason_code": "excellent_context"})
    second = build_disagreement_record(_clip(id=8, editorial_key="def456", review_required=False, review_reasons=[], multimodal_editorial_review={}, score_factors=json.dumps({"flow": 80})), {"action": "rejected", "reason_code": "sem_payoff"})
    summary = summarize_records([first, second])
    assert summary["status"] == "descriptive_only"
    assert summary["decision_counts"] == {"approved": 1, "rejected": 1}
    assert summary["reason_counts"] == {"excellent_context": 1, "sem_payoff": 1}
    assert summary["discordance_counts"]["warning_human_approved"] == 1
    assert summary["discordance_counts"]["no_warning"] == 1
    assert summary["score_used"] is False
    assert summary["causal_inference"] is False


def test_matrix_store_round_trip_is_project_scoped_and_bounded(tmp_path):
    record = build_disagreement_record(_clip(), {"action": "needs_review", "reason_code": "audio_ruim"})
    save_disagreement_record(record, project_id=3, clip_id=7, root=tmp_path)
    loaded = load_disagreement_records(project_id=3, root=tmp_path)
    assert len(loaded) == 1
    assert loaded[0]["clip"]["clip_id"] == 7
    assert load_disagreement_records(project_id=4, root=tmp_path) == []
