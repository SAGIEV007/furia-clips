#!/usr/bin/env python3
"""Merge the next visually annotated reserve-profile batch into the private dataset."""
from __future__ import annotations

import json
from pathlib import Path

DATASET = Path.home() / "FuriaClipsData/analyses/instagram-editorial-dataset-v1-2026-08-15.json"

NEW_RECORDS = [
    {"account":"@renansantosreserva","content_key":"Db_4A6IDX1O","views":202000,"family":"question_answer_third_party","hook":"explicit_question","narrative":"third_party_influencer_plus_candidate_defense","context":"question_and_response_required","payoff":"social_proof_and_candidate_position","layout":"vertical_split_screen","layout_policy":"preserve_split_screen","evidence":"third_party_influencer","audio":"pending","confidence":0.92},
    {"account":"@renansantosreserva","content_key":"Db_svcovjix","views":138000,"family":"public_confrontation_systemic_evidence","hook":"call_for_explanation","narrative":"event_interview_plus_documented_allegation","context":"event_identity_and_question_response","payoff":"public_challenge","layout":"vertical_event_interview","layout_policy":"preserve_event_context","evidence":"event_stage_and_system_claim","audio":"pending","confidence":0.94},
    {"account":"@renansantosreserva","content_key":"Db_aVwFEkfD","views":108000,"family":"official_statement_humor","hook":"official_announcement","narrative":"direct_talking_head_plus_community_humor","context":"episode_and_statement_complete","payoff":"official_explanation","layout":"vertical_talking_head","layout_policy":"preserve_face_and_sync_text","evidence":"none_dominant","audio":"pending","confidence":0.87},
    {"account":"@renansantosreserva","content_key":"Db_qtXRgm1b","views":85200,"family":"ally_statement_backstage","hook":"behind_scenes","narrative":"third_party_ally_plus_backstage_claim","context":"question_and_answer_required","payoff":"specific_claim","layout":"vertical_podcast","layout_policy":"preserve_speaker_and_microphone","evidence":"podcast_context","audio":"pending","confidence":0.9},
    {"account":"@renansantosreserva","content_key":"Db_jBIqj1nb","views":98400,"family":"third_party_political_question","hook":"identity_question","narrative":"third_party_politician_plus_podcast_position","context":"question_and_statement_required","payoff":"ideological_positioning","layout":"vertical_split_screen","layout_policy":"preserve_split_screen","evidence":"third_party_image","audio":"pending","confidence":0.91},
    {"account":"@renansantosreserva","content_key":"Db_R92njTCq","views":44400,"family":"documentary_comparison","hook":"public_challenge","narrative":"Renan_post_plus_tv_evidence","context":"textual_post_and_third_party_required","payoff":"fiscal_contrast","layout":"text_post_plus_tv_commentator","layout_policy":"preserve_external_text","evidence":"social_post_and_tv","audio":"pending","confidence":0.93},
    {"account":"@renansantosreserva","content_key":"Db_cM5TlApr","views":43300,"family":"textual_evidence_commentator","hook":"fear_accusation","narrative":"Renan_post_plus_third_party_commentator","context":"quote_and_reaction_required","payoff":"contested_claim","layout":"text_post_to_commentator","layout_policy":"preserve_post_and_face","evidence":"textual_post","audio":"pending","confidence":0.91},
    {"account":"@renansantosreserva","content_key":"Db_foElAY3K","views":16800,"family":"political_meme","hook":"humorous_attack","narrative":"body_meme_plus_headline_plus_target_image","context":"montage_context","payoff":"humor_and_target","layout":"vertical_three_layer_montage","layout_policy":"preserve_reaction_and_target","evidence":"target_image","audio":"pending","confidence":0.86},
    {"account":"@renansantosreserva","content_key":"Db_VUXqjnyO","views":11300,"family":"security_controversial_statement","hook":"hardline_security","narrative":"textual_post_plus_stage_speech","context":"attribution_and_transcript_required","payoff":"policy_statement","layout":"portrait_plus_stage","layout_policy":"preserve_context_images","evidence":"textual_post_and_stage","audio":"pending","confidence":0.92},
    {"account":"@renansantosreserva","content_key":"Db_Y07LFV7J","views":9696,"family":"anti_label_conversation","hook":"honest_position","narrative":"podcast_split_screen_plus_anti_polarization_thesis","context":"thesis_and_explanation_required","payoff":"anti_polarization_position","layout":"vertical_split_podcast","layout_policy":"preserve_split_screen","evidence":"podcast_context","audio":"pending","confidence":0.9},
    {"account":"@renansantosreserva","content_key":"Db_fnFCDK8I","views":4784,"family":"casual_curiosity","hook":"curiosity_question","narrative":"travel_anecdote_plus_food_curiosity","context":"personal_anecdote_and_object_required","payoff":"visual_object_reveal","layout":"vertical_three_layer_curiosity","layout_policy":"preserve_transition","evidence":"object_closeup","audio":"pending","confidence":0.9},
    {"account":"@renansantosreserva","content_key":"Db_mfm5ihyd","views":18600,"family":"controversial_thesis_third_party","hook":"shock_headline","narrative":"ngo_claim_plus_indigenous_group_context","context":"third_party_scene_and_justification_required","payoff":"controversial_thesis","layout":"group_meeting_with_sync_text","layout_policy":"preserve_group_context","evidence":"indigenous_group_scene","audio":"pending","confidence":0.92},
]


def main() -> int:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    records = payload.setdefault("records", [])
    existing = {str(item.get("content_key")) for item in records if isinstance(item, dict)}
    added = [item for item in NEW_RECORDS if item["content_key"] not in existing]
    records.extend(added)
    coverage = payload.setdefault("coverage", {})
    coverage["individual_visual_records"] = len(records)
    reserve = coverage.setdefault("accounts", {}).setdefault("@renansantosreserva", {})
    reserve["individual_visual_records"] = sum(1 for item in records if item.get("account") == "@renansantosreserva")
    payload["last_incremental_batch"] = {
        "profile": "@renansantosreserva",
        "batch_label": "second-window-complete",
        "added_records": len(added),
        "audio_status": "not_observed_browser_muted",
    }
    DATASET.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"added={len(added)} total={len(records)} reserve={reserve['individual_visual_records']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
