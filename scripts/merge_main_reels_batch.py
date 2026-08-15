#!/usr/bin/env python3
"""Merge the next visually annotated main-profile batch into the private dataset."""
from __future__ import annotations

import json
from pathlib import Path

DATASET = Path.home() / "FuriaClipsData/analyses/instagram-editorial-dataset-v1-2026-08-15.json"

NEW_RECORDS = [
    {"account":"@renansantosmbl","content_key":"Db9GlGatuQi","family":"event_mobilization","hook":"event_invitation","narrative":"documentary_mobilization_banner","context":"date_place_and_time_required","payoff":"event_details","layout":"vertical_documentary_banner","layout_policy":"preserve_original_scale","evidence":"public_event_banner","audio":"pending","confidence":0.91},
    {"account":"@renansantosmbl","content_key":"Db88Vu-Nmhu","family":"reaction_external_evidence","hook":"polarizing_claim","narrative":"street_evidence_plus_talking_head_reaction","context":"evidence_reaction_link_required","payoff":"verbal_interpretation_of_external_scene","layout":"vertical_split_evidence_and_face","layout_policy":"preserve_evidence_and_reaction","evidence":"street_scene","audio":"pending","confidence":0.88},
    {"account":"@renansantosmbl","content_key":"Db8fcmItfCw","family":"reaction_external_evidence","hook":"positive_reaction","narrative":"television_presenter_plus_commentator","context":"external_media_and_reaction_required","payoff":"reaction_statement","layout":"vertical_two_layer_media_commentary","layout_policy":"preserve_both_speakers","evidence":"television_studio","audio":"pending","public_likes":78800,"public_comments":3484,"public_reposts":7938,"metric_note":"public engagement counters, not views","confidence":0.87},
    {"account":"@renansantosmbl","content_key":"Db8D9DxNnUX","family":"interview_split_screen","hook":"action_promise","narrative":"stage_speaker_plus_audience_interview","context":"question_and_response_required","payoff":"fiscalization_statement","layout":"vertical_split_stage_and_interview","layout_policy":"preserve_multi_subject_layout","evidence":"event_interview","audio":"pending","public_likes":26600,"public_comments":519,"public_reposts":2789,"metric_note":"public engagement counters, not views","confidence":0.86},
    {"account":"@renansantosmbl","content_key":"Db6qoCUBulc","family":"descontraido","hook":"punchline_card","narrative":"black_card_headline_plus_social_scene","context":"headline_and_scene_complete","payoff":"humorous_or_cultural_punchline","layout":"vertical_black_card_plus_scene","layout_policy":"preserve_card_and_scene","evidence":"social_scene","audio":"pending","public_likes":43500,"public_comments":782,"public_reposts":5388,"metric_note":"public engagement counters, not views","confidence":0.85},
    {"account":"@renansantosmbl","content_key":"Db6g5dfteDn","family":"reaction_external_evidence","hook":"legal_position","narrative":"talking_head_plus_institutional_figure","context":"legal_premise_and_evidence_required","payoff":"legal_conclusion","layout":"vertical_split_commentator_and_institution","layout_policy":"preserve_both_sides","evidence":"institutional_scene","audio":"pending","public_likes":53200,"public_comments":1635,"public_reposts":6150,"metric_note":"public engagement counters, not views","confidence":0.9},
    {"account":"@renansantosmbl","content_key":"Db6XRaAtNTR","family":"ally_statement","hook":"ally_message","narrative":"stage_ally_plus_remote_political_message","context":"speaker_identity_and_statement_required","payoff":"ally_position","layout":"vertical_split_stage_and_remote_message","layout_policy":"preserve_multi_subject_layout","evidence":"political_event","audio":"pending","public_likes":24300,"public_comments":1689,"public_reposts":3036,"metric_note":"public engagement counters, not views","confidence":0.87},
    {"account":"@renansantosmbl","content_key":"Db56l1MNBHb","family":"reaction_external_evidence","hook":"shock_political_hook","narrative":"talking_head_plus_alleged_external_evidence","context":"attribution_evidence_and_context_required","payoff":"claim_must_be_delivered_and_qualified","layout":"vertical_face_plus_lower_evidence","layout_policy":"preserve_commentary_and_evidence","evidence":"external_social_scene","audio":"pending","public_likes":168000,"public_comments":7179,"public_reposts":22000,"metric_note":"public engagement counters, not views","confidence":0.84},
    {"account":"@renansantosmbl","content_key":"Db5lhGWt97n","family":"event_speech","hook":"mission_statement","narrative":"stage_speech_to_mission_headline","context":"complete_sentence_required","payoff":"mission_or_goal_conclusion","layout":"vertical_stage_talking_head","layout_policy":"preserve_speaker_and_context","evidence":"event_stage","audio":"pending","public_likes":47200,"public_comments":1936,"public_reposts":5047,"metric_note":"public engagement counters, not views","confidence":0.86},
    {"account":"@renansantosmbl","content_key":"Db4BVlMt6hO","family":"curiosity_gap","hook":"forbidden_video","narrative":"black_card_curiosity_plus_domestic_scene","context":"promise_and_reveal_required","payoff":"revelation_of_teased_content","layout":"vertical_black_card_plus_domestic_scene","layout_policy":"preserve_hook_and_reveal","evidence":"domestic_social_scene","audio":"pending","public_likes":363000,"public_comments":6819,"public_reposts":60800,"metric_note":"public engagement counters, not views","confidence":0.92},
    {"account":"@renansantosmbl","content_key":"Db32p6PNW_8","family":"interview_event","hook":"grand_project","narrative":"stage_interview_with_object_context","context":"preceding_and_following_sentence_required","payoff":"project_statement","layout":"vertical_interview_microphone_and_object","layout_policy":"preserve_speaker_and_context","evidence":"book_and_microphone","audio":"pending","public_likes":39500,"public_comments":1316,"public_reposts":5285,"metric_note":"public engagement counters, not views","confidence":0.87},
    {"account":"@renansantosmbl","content_key":"Db3fEHeNPOU","family":"political_contrast","hook":"anti_polarization_statement","narrative":"stage_speech_plus_stylized_counterimage","context":"thesis_and_counterpoint_required","payoff":"anti_polarization_conclusion","layout":"vertical_split_speaker_and_stylized_image","layout_policy":"preserve_comparative_composition","evidence":"political_counterimage","audio":"pending","public_likes":49700,"public_comments":6264,"public_reposts":5302,"metric_note":"public engagement counters, not views","confidence":0.9},
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
