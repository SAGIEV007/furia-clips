#!/usr/bin/env python3
"""Merge the next visually annotated main-profile batch into the private dataset."""
from __future__ import annotations

import json
from pathlib import Path

DATASET = Path.home() / "FuriaClipsData/analyses/instagram-editorial-dataset-v1-2026-08-15.json"

NEW_RECORDS = [
    {"account":"@renansantosmbl","content_key":"Db9RrFrNHRL","family":"reaction_external_evidence","hook":"question_reaction","narrative":"Renan_talking_head_plus_external_montage","context":"question_and_supporting_sequence_required","payoff":"interpretation_of_external_scene","layout":"vertical_talking_head_plus_montage","layout_policy":"preserve_face_question_and_support","evidence":"urban_police_and_public_scene","audio":"pending","confidence":0.84},
    {"account":"@renansantosmbl","content_key":"Db_-iFVNz6g","family":"reaction_electoral_poll","hook":"poll_result","narrative":"external_poll_screenshot_plus_Renan_reaction","context":"source_and_temporal_context_required","payoff":"percentage_reaction","layout":"screenshot_plus_talking_head","layout_policy":"preserve_source_and_numbers","evidence":"press_poll_screenshot","audio":"pending","confidence":0.95},
    {"account":"@renansantosmbl","content_key":"Db_VRDtNM9d","family":"official_statement","hook":"truth_reveal","narrative":"direct_selfie_statement_plus_kinetic_text","context":"controversy_and_explanation_required","payoff":"official_explanation","layout":"vertical_selfie_talking_head","layout_policy":"preserve_face_and_sync_text","evidence":"none_dominant","audio":"pending","confidence":0.91},
    {"account":"@renansantosmbl","content_key":"Db_zbMhNfYJ","family":"step_by_step_explanation","hook":"step_by_step","narrative":"chronological_talking_head_explanation","context":"causal_sequence_required","payoff":"timeline_conclusion","layout":"vertical_talking_head_with_text","layout_policy":"preserve_face_and_sequence_text","evidence":"laptop_context","audio":"pending","confidence":0.93},
    {"account":"@renansantosmbl","content_key":"DcBe7a9t7LA","family":"reaction_external_evidence","hook":"institutional_action","narrative":"selfie_plus_newspaper_and_legal_claim","context":"document_and_legal_context_required","payoff":"institutional_confrontation","layout":"selfie_plus_document_overlay","layout_policy":"preserve_ocr_source_and_face","evidence":"newspaper_and_TSE_claim","audio":"pending","confidence":0.96},
    {"account":"@renansantosmbl","content_key":"DcCF8NWN1zb","family":"event_mobilization","hook":"short_strong_fragment","narrative":"stage_speech_plus_community_support","context":"preceding_and_following_speech_required","payoff":"mobilization","layout":"event_stage_talking_head","layout_policy":"preserve_speaker_and_context","evidence":"audience_support_comments","audio":"pending","confidence":0.62},
    {"account":"@renansantosmbl","content_key":"DcCVfXMN7-Y","family":"political_diagnosis_question","hook":"broad_question","narrative":"talking_head_plus_political_collage","context":"question_and_diagnosis_required","payoff":"political_analysis_conclusion","layout":"talking_head_plus_black_red_banner","layout_policy":"preserve_collage_if_comparative","evidence":"third_party_political_figures","audio":"pending","confidence":0.9},
    {"account":"@renansantosmbl","content_key":"DcCl7irNcWt","family":"sensitive_personal_evidence","hook":"personal_safety_statement","narrative":"selfie_plus_threat_screenshot","context":"safety_and_source_context_required","payoff":"personal_account_and_call_for_protection","layout":"selfie_plus_sensitive_text_overlay","layout_policy":"preserve_context_redact_identifiers","evidence":"threat_message_screenshot","audio":"pending","confidence":0.96},
    {"account":"@renansantosmbl","content_key":"DXIQunmEQ9O","family":"public_policy_visual_explainer","hook":"policy_proposal","narrative":"third_party_tv_interview_plus_Brazil_map","context":"premise_and_policy_explanation_required","payoff":"proposal_explanation","layout":"tv_interview_plus_map","layout_policy":"preserve_speaker_and_map","evidence":"map_visualization","audio":"pending","confidence":0.91},
    {"account":"@renansantosmbl","content_key":"DZ7ZY6EtlNq","family":"social_documentary_political_contrast","hook":"social_reality_question","narrative":"talking_head_plus_real_person_social_scene","context":"person_and_political_connection_required","payoff":"social_critique","layout":"talking_head_plus_social_scene","layout_policy":"preserve_person_and_argument","evidence":"social_scene","audio":"pending","confidence":0.93},
]


def main() -> int:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    records = payload.setdefault("records", [])
    existing = {str(item.get("content_key")) for item in records if isinstance(item, dict)}
    added = [item for item in NEW_RECORDS if item["content_key"] not in existing]
    records.extend(added)
    coverage = payload.setdefault("coverage", {})
    coverage["individual_visual_records"] = len(records)
    accounts = coverage.setdefault("accounts", {})
    main_account = accounts.setdefault("@renansantosmbl", {})
    main_account["individual_visual_records"] = sum(1 for item in records if item.get("account") == "@renansantosmbl")
    payload["last_incremental_batch"] = {
        "profile": "@renansantosmbl",
        "batch_label": "main-window-current-complete",
        "added_records": len(added),
        "audio_status": "not_observed_browser_muted",
    }
    DATASET.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"added={len(added)} total={len(records)} main={main_account['individual_visual_records']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
