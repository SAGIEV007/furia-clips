"""Explainable editorial scoring for candidate clips.

This module deliberately avoids presenting a heuristic as a statistical
prediction. It returns a comparable editorial potential score plus the factors
that produced it, so the review UI can explain and calibrate the ranking.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Optional

from .editorial_format import classify_editorial_format
from .political_profile import PROFILE_NAME, analyze_political_text
from .campaign_hub import build_performance_prior
from .instagram_editorial_priors import build_editorial_pattern_prior


HOOK_PATTERNS = [
    r"voce\s+sabia",
    r"presta\s+(muita\s+)?atencao",
    r"leia\s+de\s+novo",
    r"olha\s+(isso|so)",
    r"a\s+verdade\s+(e|eh)",
    r"ninguem\s+te\s+(conta|fala|diz)",
    r"o\s+problema\s+e",
    r"a\s+questao\s+e",
    r"eu\s+vou\s+te\s+(falar|dizer|contar)",
    r"(absurdo|vergonha|mentira|bomba|urgente|chocante)",
    r"qual\s+(e|é)\s+(o\s+)?nosso\s+maior\s+inimigo",
    r"que\s+brasil\s+vou\s+pegar",
    r"eles\s+nao\s+querem\s+que\s+voce\s+veja",
]

EMOTIONAL_TERMS = {
    "absurdo", "vergonha", "mentira", "corrupto", "criminoso", "covarde",
    "traidor", "hipocrita", "revolta", "indignacao", "injustica", "liberdade",
    "coragem", "vitoria", "luta", "verdade", "justica", "impressionante",
    "incrivel", "surreal", "chocante", "ridiculo", "tragedia", "desastre",
}

TOPIC_STOPWORDS = {
    "a", "ao", "aos", "as", "com", "como", "da", "das", "de", "do", "dos", "e", "em", "ele", "ela", "esse", "esta", "eu", "foi", "isso", "ja", "mais", "na", "nas", "no", "nos", "o", "os", "ou", "para", "por", "pra", "que", "se", "sem", "ser", "sobre", "tem", "um", "uma", "vai", "voce", "voces",
}

FILLERS = {
    "ah", "eh", "tipo", "entao", "sabe", "basicamente", "na verdade",
    "ou seja", "entendeu", "digamos", "assim", "enfim", "bom", "olha",
}

MID_SENTENCE_STARTERS = {"e", "mas", "porem", "entao", "porque", "que", "ai", "ou", "nem"}
CONTINUITY_PATTERNS = ("acompanhe", "aguarde", "em breve", "novidades", "vou mostrar", "depois eu", "na proxima", "fique ligado")
RESOLUTION_PATTERNS = ("portanto", "por isso", "entao", "a conclusao", "fica claro", "e isso", "essa e a verdade")
ARGUMENT_MARKERS = ("porque", "portanto", "por isso", "significa", "se ", "entao", "logo", "portanto")
PREFERRED_MAX_DURATION = 180.0



class EditorialRanker:
    def __init__(
        self,
        channel_context: str = "",
        editorial_profile: str = PROFILE_NAME,
        feedback_calibration: Optional[dict] = None,
        campaign_hub_snapshot: Optional[dict] = None,
        campaign_hub_account: Optional[str] = None,
    ):
        self.channel_context = channel_context or ""
        self.editorial_profile = editorial_profile or PROFILE_NAME
        self.feedback_calibration = feedback_calibration or {}
        self.campaign_hub_snapshot = campaign_hub_snapshot
        self.campaign_hub_account = campaign_hub_account

    def rank_clips(
        self,
        clips: Iterable[dict],
        *,
        user_context: str = "",
        energy_profile: Optional[Iterable[dict]] = None,
    ) -> list:
        scored = [
            {**clip, **self.score_clip(clip, user_context=user_context, energy_profile=energy_profile)}
            for clip in clips
        ]
        scored.sort(
            key=lambda clip: (
                clip.get("editorial_potential_score", clip.get("viral_score", 0)),
                (clip.get("factors") or {}).get("duration_fit", 50),
                -float(clip.get("duration", 0) or 0),
            ),
            reverse=True,
        )

        selected = []
        for clip in scored:
            penalty = self._diversity_penalty(clip, selected)
            clip["factors"]["diversity"] = round(max(0.0, 100.0 - penalty), 1)
            clip["diversity_penalty"] = round(penalty, 1)
            clip["diversity_reason"] = self._diversity_reason(clip, selected)
            if penalty >= 70:
                continue
            if penalty >= 35:
                clip["editorial_potential_score"] = max(
                    0,
                    int(clip["editorial_potential_score"] - penalty * 0.12),
                )
                clip["viral_score"] = clip["editorial_potential_score"]
            selected.append(clip)

        selected.sort(
            key=lambda clip: (
                clip.get("editorial_potential_score", 0),
                (clip.get("factors") or {}).get("duration_fit", 50),
                -float(clip.get("duration", 0) or 0),
            ),
            reverse=True,
        )
        return selected

    def rank_daily_portfolio(self, clips, **kwargs) -> dict:
        """Select the best quality-gated portfolio across multiple live sources."""
        from .daily_portfolio import build_daily_portfolio

        ranked = self.rank_clips(clips, user_context=kwargs.pop("user_context", ""), energy_profile=kwargs.pop("energy_profile", None))
        return build_daily_portfolio(ranked, **kwargs)

    def score_clip(self, clip: dict, *, user_context: str = "", energy_profile=None) -> dict:
        text = str(clip.get("text") or "").strip()
        duration = float(clip.get("duration") or max(1.0, float(clip.get("end", 0)) - float(clip.get("start", 0))))
        closure_type = self._closure_type(text)
        format_profile = classify_editorial_format(clip, text)
        campaign_hub_prior = build_performance_prior(
            text,
            account=self.campaign_hub_account,
            snapshot=self.campaign_hub_snapshot,
        )
        instagram_pattern_prior = build_editorial_pattern_prior(text, clip)
        factors = {
            "hook": self._hook(text),
            "flow": self._flow(text, duration),
            "value": self._value(text),
            "argument_structure": self._argument_structure(text, closure_type),
            "context_match": self._context_match(text, user_context),
            "audio_energy": self._audio_energy(clip, energy_profile),
            "visual_change_density": self._visual_change_density(clip),
            "clarity": self._clarity(text),
            "completeness": self._completeness(text, closure_type),
            "context_quality": self._context_quality(clip, text, closure_type),
            "speaker_boundary": self._speaker_boundary_score(clip),
            "qa_boundary": self._qa_boundary_score(clip),
            "contextual_hook_alignment": self._contextual_hook_alignment(clip),
            "feedback_reason_alignment": self._feedback_reason_alignment(clip),
            "editorial_family_fit": 50.0,
            "instagram_pattern_prior": instagram_pattern_prior["signal"],
            "chapter_coherence": self._chapter_coherence(clip),
            "duration_fit": self._duration_fit(duration),
            "campaign_hub_prior": campaign_hub_prior["observed_signal"],
        }
        political_signals = {}
        if self.editorial_profile in (PROFILE_NAME, "politics", "political"):
            political_signals = analyze_political_text(
                text,
                user_context=user_context,
                channel_context=self.channel_context,
            )
            factors.update({
                key: value
                for key, value in political_signals.items()
                if isinstance(value, (int, float))
                and not isinstance(value, bool)
                and key not in {"questions", "exclamations", "sensitive_claim_hits", "named_entity_count"}
            })
        weights = {
            "hook": 0.17,
            "flow": 0.16,
            "value": 0.12,
            "argument_structure": 0.07,
            "context_match": 0.13,
            "audio_energy": 0.10,
            "visual_change_density": 0.06,
            "clarity": 0.08,
            "completeness": 0.10,
            "context_quality": 0.10,
            "editorial_family_fit": 0.02,
            "instagram_pattern_prior": 0.04,
        }
        if not user_context:
            weights["context_match"] = 0.0
            weights["value"] += 0.07
            weights["flow"] += 0.07
            weights["editorial_family_fit"] += 0.02

        base_score = sum(factors[key] * weight for key, weight in weights.items())
        if political_signals:
            family = political_signals.get("editorial_family", "politico")
            if family == "politico":
                score = int(round(base_score * 0.65 + political_signals["political_editorial_fit"] * 0.35))
            else:
                # A political channel can still publish strong humor, reaction,
                # backstage, or casual clips; do not force them into politics.
                score = int(round(base_score * 0.84 + political_signals.get("editorial_family_fit", 50.0) * 0.16))
        else:
            score = int(round(base_score))

        # Shorter is preferred, but duration never overrides context and payoff.
        # The preference is deliberately bounded so an exceptional long answer
        # can still win when its editorial evidence is substantially stronger.
        score += int(round((factors["duration_fit"] - 70.0) * 0.16))

        # Chapter coherence is a bounded, explainable adjustment layered on top
        # of the established score so legacy ranking remains comparable.
        if clip.get("editorial_chapter_available"):
            score += int(round((factors["chapter_coherence"] - 65.0) * 0.08))
            if clip.get("chapter_crosses_boundary") and not clip.get("qa_bridge"):
                score -= 2
        if campaign_hub_prior["available"]:
            # Post-publication evidence is intentionally bounded to +/- 2 points.
            score += int(round((campaign_hub_prior["observed_signal"] - 50.0) * 0.12))
        # Speaker and Q&A boundaries are tie-breakers, never substitutes for
        # context, payoff or technical gates. Combined impact is <= 4 points.
        score += int(round(
            (factors["speaker_boundary"] - 50.0) * 0.04
            + (factors["qa_boundary"] - 50.0) * 0.04
            + (factors["contextual_hook_alignment"] - 50.0) * 0.05
            + (factors["feedback_reason_alignment"] - 50.0) * 0.03
        ))
        context_contract = any(
            key in clip
            for key in (
                "starts_mid_sentence", "question_detected", "question_answer_complete",
                "evidence_present", "payoff_complete", "context_complete",
            )
        )
        technical_gate = self._technical_gate(clip, factors, political_signals)
        score -= technical_gate["penalty"]
        if context_contract:
            if not clip.get("context_complete") and not clip.get("qa_bridge"):
                score = min(score, 74)
            if clip.get("overlap_suspected"):
                score = min(score, 62)
            elif clip.get("timing_ambiguous"):
                score = min(score, 70)
        score = max(0, min(100, score))

        candidate_origin = str(clip.get("candidate_origin") or "")
        candidate_confidence = clip.get("confidence")
        if not isinstance(candidate_confidence, (int, float)):
            candidate_confidence = clip.get("score_confidence")
        feedback_adjustment = self._feedback_adjustment(
            factors,
            candidate_origin=candidate_origin,
            candidate_confidence=candidate_confidence,
        )
        if feedback_adjustment:
            score = max(0, min(100, int(round(score + feedback_adjustment))) )
            factors["editor_feedback_alignment"] = round(50.0 + feedback_adjustment * 5.0, 1)

        feedback_calibration = self._feedback_payload(
            feedback_adjustment,
            candidate_origin=candidate_origin,
            candidate_confidence=candidate_confidence,
        )
        confidence = self._confidence(text, factors, duration)
        if clip.get("transcription_review_required"):
            confidence = min(confidence, 0.74 if str(clip.get("transcription_coverage_status", "")).lower() == "partial" else 0.68)
        duration_preference = self._duration_preference(duration, factors)
        breakdown = {
            "hook": self._grade(factors["hook"]),
            "flow": self._grade(factors["flow"]),
            "value": self._grade(factors["value"]),
            "energy": self._grade(factors["audio_energy"]),
            "speaker_boundary": self._grade(factors["speaker_boundary"]),
                            "qa_boundary": self._grade(factors["qa_boundary"]),
                "contextual_hook": self._grade(factors["contextual_hook_alignment"]),
                "feedback_reason": self._grade(factors["feedback_reason_alignment"]),
            }

        reason = self._reason(factors, user_context)
        topic_signature = self._topic_signature(text, political_signals)
        score_version = (
            "v3-context-gates-feedback" if feedback_adjustment and context_contract
            else "v3-context-gates" if context_contract
            else "v1-feedback-calibrated" if feedback_adjustment
            else "v1-explainable"
        )
        return {
            "viral_score": score,
            "editorial_potential_score": score,
            "editorial_score_version": score_version,
            "topic_signature": topic_signature,
            "closure_type": closure_type,
            "starts_mid_sentence": bool(clip.get("starts_mid_sentence")),
            "question_detected": bool(clip.get("question_detected")),
            "question_answer_complete": bool(clip.get("question_answer_complete")),
            "evidence_present": bool(clip.get("evidence_present")),
            "payoff_complete": bool(clip.get("payoff_complete")),
            "context_complete": bool(clip.get("context_complete")),
            "starts_with_context_reference": bool(clip.get("starts_with_context_reference")),
            "payoff_weak_ending": bool(clip.get("payoff_weak_ending")),
            "transcription_review_required": bool(clip.get("transcription_review_required")),
            "transcription_coverage_status": str(clip.get("transcription_coverage_status", "") or ""),
            "breakdown": breakdown,
            "factors": {key: round(value, 1) for key, value in factors.items()},
            "confidence": round(confidence, 2),
            "duration_fit": factors["duration_fit"],
            "duration_preference": duration_preference,
            "has_hook": factors["hook"] >= 55,
            "reason": clip.get("reason") or reason,
            "political_profile": self.editorial_profile if political_signals else "",
            "political_editorial_type": political_signals.get("editorial_type", "") if political_signals else "",
            "political_signals": political_signals,
            "visual_format": format_profile["visual_format"],
            "visual_format_confidence": format_profile["visual_format_confidence"],
            "visual_format_reason": format_profile["visual_format_reason"],
            "visual_observation": str(clip.get("visual_observation") or ""),
            "visual_observation_confidence": clip.get("visual_observation_confidence"),
            "editorial_chapter_ids": list(clip.get("editorial_chapter_ids") or []),
            "chapter_primary_id": clip.get("chapter_primary_id"),
            "chapter_count": int(clip.get("chapter_count", 0) or 0),
            "chapter_coherence_score": clip.get("chapter_coherence_score"),
            "qa_bridge": bool(clip.get("qa_bridge")),
            "qa_boundary_basis": str(clip.get("qa_boundary_basis", "") or ""),
            "qa_boundary_review_required": bool(clip.get("qa_boundary_review_required")),
            "speaker_turn_valid": clip.get("speaker_turn_valid"),
            "speaker_boundary_score": factors["speaker_boundary"],
            "qa_boundary_score": factors["qa_boundary"],
            "contextual_hook_alignment": factors["contextual_hook_alignment"],
            "feedback_reason_alignment": factors["feedback_reason_alignment"],
            "transcription_review_required": bool(clip.get("transcription_review_required")),
            "transcription_coverage_status": str(clip.get("transcription_coverage_status", "") or ""),
            "transcription_review_reason": str(clip.get("transcription_review_reason", "") or ""),
            "campaign_hub_prior": campaign_hub_prior,
            "instagram_pattern_prior": instagram_pattern_prior,
            "feedback_calibration": feedback_calibration,
            "technical_gate": technical_gate,
            "hook_family": campaign_hub_prior["hook_family"],
            "hook_evidence": list(campaign_hub_prior.get("hook_evidence") or []),
            "hook_classification_confidence": campaign_hub_prior.get("hook_classification_confidence", 0.0),
            "reframe_policy": format_profile["reframe_policy"],
            "preserve_composition": format_profile["preserve_composition"],
            "review_flags": {
                "needs_fact_review": bool(political_signals.get("needs_fact_review")),
                "needs_legal_review": bool(political_signals.get("needs_legal_review")),
                "sensitive_claim_hits": int(political_signals.get("sensitive_claim_hits", 0) or 0),
                "named_entity_count": int(political_signals.get("named_entity_count", 0) or 0),
                "preserve_composition": format_profile["preserve_composition"],
                "visual_observation_available": bool(clip.get("visual_observation")),
                "editorial_chapter_available": bool(clip.get("editorial_chapter_available")),
                "chapter_coherence_score": clip.get("chapter_coherence_score"),
                "chapter_count": int(clip.get("chapter_count", 0) or 0),
                "qa_bridge": bool(clip.get("qa_bridge")),
                "qa_boundary_basis": str(clip.get("qa_boundary_basis", "") or ""),
                "qa_boundary_review_required": bool(clip.get("qa_boundary_review_required")),
                "chapter_crosses_boundary": bool(clip.get("chapter_crosses_boundary")),
                "duration_preference": duration_preference["status"],
                "duration_exception": bool(duration_preference["exception"]),
                "starts_mid_sentence": bool(clip.get("starts_mid_sentence")),
                "starts_with_context_reference": bool(clip.get("starts_with_context_reference")),
                "payoff_weak_ending": bool(clip.get("payoff_weak_ending")),
                "question_detected": bool(clip.get("question_detected")),
                "question_answer_complete": bool(clip.get("question_answer_complete")),
                "evidence_present": bool(clip.get("evidence_present")),
                "payoff_complete": bool(clip.get("payoff_complete")),
                "context_complete": bool(clip.get("context_complete")),
                "overlap_suspected": bool(clip.get("overlap_suspected")),
                "timing_ambiguous": bool(clip.get("timing_ambiguous")),
                "speaker_turn_valid": clip.get("speaker_turn_valid"),
                "speaker_review_required": bool(clip.get("needs_speaker_review")) or clip.get("speaker_turn_valid") is None,
                "transcription_review_required": bool(clip.get("transcription_review_required")),
                "transcription_coverage_status": str(clip.get("transcription_coverage_status", "") or ""),
                "transcription_review_reason": str(clip.get("transcription_review_reason", "") or ""),
                "speaker_boundary_score": factors["speaker_boundary"],
                "qa_boundary_score": factors["qa_boundary"],
                "contextual_hook_alignment": factors["contextual_hook_alignment"],
                "feedback_reason_alignment": factors["feedback_reason_alignment"],
                "technical_gate_status": technical_gate["status"],
                "technical_gate_reasons": list(technical_gate["reasons"]),
                "campaign_hub_prior_available": bool(campaign_hub_prior["available"]),
                "campaign_hub_hook_family": campaign_hub_prior["hook_family"],
                "instagram_pattern_prior_available": bool(instagram_pattern_prior["available"]),
                "instagram_pattern_family": instagram_pattern_prior["family"],
                "instagram_pattern_sample_count": instagram_pattern_prior["sample_count"],
                "campaign_hub_hook_evidence": list(campaign_hub_prior.get("hook_evidence") or []),
                "campaign_hub_hook_classification_confidence": campaign_hub_prior.get("hook_classification_confidence", 0.0),
                "campaign_hub_sample_count": campaign_hub_prior["sample_count"],
                "feedback_calibration_eligible": feedback_calibration["eligible"],
                "feedback_sample_size": feedback_calibration["sample_size"],
                "feedback_duration_signal_usable": feedback_calibration["duration_signal"]["usable"],
                "feedback_duration_gap_seconds": feedback_calibration["duration_signal"]["gap_seconds"],
            },
        }

    def _speaker_boundary_score(self, clip: dict) -> float:
        if clip.get("speaker_turn_valid") is False:
            return 25.0
        confidence = clip.get("speaker_confidence")
        if isinstance(confidence, (int, float)):
            normalized = max(0.0, min(1.0, float(confidence)))
            return round(45.0 + normalized * 45.0, 1)
        if clip.get("speaker_change_detected") or clip.get("speaker_boundary"):
            return 82.0
        return 50.0

    def _qa_boundary_score(self, clip: dict) -> float:
        if clip.get("qa_bridge"):
            return 90.0
        if clip.get("question_answer_complete"):
            return 78.0
        if clip.get("question_detected"):
            return 42.0 if clip.get("needs_speaker_review") else 58.0
        return 55.0

    def _feedback_reason_alignment(self, clip: dict) -> float:
        calibration = self.feedback_calibration if isinstance(self.feedback_calibration, dict) else {}
        coverage = calibration.get("reason_coverage") if isinstance(calibration.get("reason_coverage"), dict) else {}
        if not calibration.get("eligible") or not coverage:
            return 50.0
        categories = coverage.get("categories") if isinstance(coverage.get("categories"), dict) else {}
        if clip.get("overlap_suspected") or clip.get("speaker_turn_valid") is False:
            category = "speaker_audio"
        elif clip.get("duration", 0) > PREFERRED_MAX_DURATION:
            category = "duration"
        elif clip.get("question_detected") or clip.get("context_complete") or clip.get("payoff_complete"):
            category = "context_payoff"
        else:
            category = "hook"
        item = categories.get(category) if isinstance(categories.get(category), dict) else {}
        total = int(item.get("total", 0) or 0)
        if total < 3:
            return 50.0
        approved = int(item.get("approved", 0) or 0)
        share = max(0.0, min(1.0, approved / total))
        return round(25.0 + share * 50.0, 1)

    def _contextual_hook_alignment(self, clip: dict) -> float:
        hook = clip.get("contextual_hook")
        if not isinstance(hook, dict) or not str(hook.get("hook_text") or "").strip():
            return 50.0
        try:
            hook_score = max(0.0, min(100.0, float(hook.get("score", 50) or 50)))
            distance = max(0.0, float(clip.get("hook_distance_seconds", 0) or 0))
        except (TypeError, ValueError):
            return 50.0
        proximity = max(0.0, min(1.0, 1.0 - distance / 12.0))
        return round(50.0 + (hook_score - 50.0) * 0.55 * proximity, 1)

    def _technical_gate(self, clip: dict, factors: dict, political_signals: Optional[dict] = None) -> dict:
        """Apply bounded, explainable penalties for technical uncertainty."""
        reasons = []
        penalty = 0
        contract_keys = {
            "starts_mid_sentence", "question_detected", "question_answer_complete",
            "evidence_present", "payoff_complete", "context_complete",
            "overlap_suspected", "timing_ambiguous", "speaker_turn_valid",
        }
        has_contract = any(key in clip for key in contract_keys)
        inferred_context = bool(
            factors.get("context_completeness", 50) >= 70
            or factors.get("completeness", 50) >= 75
        )
        context_complete = bool(clip.get("context_complete")) if "context_complete" in clip else inferred_context
        payoff_complete = bool(clip.get("payoff_complete")) if "payoff_complete" in clip else bool(factors.get("completeness", 50) >= 75)
        question_detected = bool(clip.get("question_detected")) if "question_detected" in clip else False
        qa_bridge = bool(clip.get("qa_bridge")) if "qa_bridge" in clip else False
        starts_mid_sentence = bool(clip.get("starts_mid_sentence"))
        overlap_suspected = bool(clip.get("overlap_suspected"))
        timing_ambiguous = bool(clip.get("timing_ambiguous"))
        transcription_review_required = bool(clip.get("transcription_review_required"))
        transcription_coverage_status = str(clip.get("transcription_coverage_status", "") or "").strip().lower()
        political_signals = political_signals if isinstance(political_signals, dict) else {}
        sensitive_claim_hits = int(political_signals.get("sensitive_claim_hits", 0) or 0)
        explicit_context_contract = any(
            key in clip for key in ("context_complete", "evidence_present", "payoff_complete")
        )

        if starts_mid_sentence:
            penalty += 14
            reasons.append("início possivelmente no meio da frase")
        if overlap_suspected:
            penalty += 22
            reasons.append("sobreposição de fala ou timestamps")
        if timing_ambiguous:
            penalty += 10
            reasons.append("timestamps inferidos com baixa confiança")
        if transcription_review_required:
            coverage_penalty = 8 if transcription_coverage_status == "partial" else 10
            penalty += coverage_penalty
            reasons.append(
                "cobertura parcial da transcrição" if transcription_coverage_status == "partial"
                else "identidade temporal da transcrição não validada"
            )
        if has_contract and question_detected and not qa_bridge:
            penalty += 10
            reasons.append("pergunta detectada sem ponte pergunta–resposta validada")
        if has_contract and not payoff_complete:
            penalty += 12
            reasons.append("payoff ou fechamento não confirmado")
        if clip.get("speaker_turn_valid") is False:
            penalty += 18
            reasons.append("troca de locutor incompatível")
        normalized_clip_words = len(_normalize(str(clip.get("text") or "")).split())
        if has_contract and not context_complete and normalized_clip_words < 16:
            penalty += 8
            reasons.append("pouca evidência textual para contexto autossuficiente")
        starts_with_context_reference = bool(clip.get("starts_with_context_reference"))
        if has_contract and starts_with_context_reference:
            if not context_complete:
                penalty += 6
                reasons.append("referência contextual sem antecedente recuperado")
        if sensitive_claim_hits and explicit_context_contract and (not context_complete or not bool(clip.get("evidence_present"))):
            penalty += 10
            reasons.append("alegação sensível sem contexto ou evidência explícitos")
        status = "clean" if not reasons else "review" if penalty < 30 else "weak"
        return {
            "status": status,
            "penalty": min(42, penalty),
            "reasons": reasons,
            "context_gate": context_complete,
            "payoff_gate": payoff_complete,
            "timing_gate": not (timing_ambiguous or overlap_suspected),
            "contract_available": has_contract,
        }

    def _duration_fit(self, duration: float) -> float:
        """Score brevity as a preference, never as a hard duration quota.

        Very short clips are not automatically ideal: the curve leaves room for
        enough speech to establish a premise and payoff. After the preferred
        ceiling, the score falls gradually instead of rejecting the candidate.
        """
        duration = max(0.0, float(duration or 0.0))
        if duration < 8:
            return 55.0
        if duration <= 30:
            return 100.0
        if duration <= 60:
            return 100.0 - (duration - 30.0) * 0.30
        if duration <= 120:
            return 91.0 - (duration - 60.0) * 0.25
        if duration <= PREFERRED_MAX_DURATION:
            return 76.0 - (duration - 120.0) * 0.30
        return max(25.0, 58.0 - (duration - PREFERRED_MAX_DURATION) * 0.15)

    def _duration_preference(self, duration: float, factors: dict) -> dict:
        exception = bool(
            duration > PREFERRED_MAX_DURATION
            and factors.get("hook", 0) >= 65
            and factors.get("completeness", 0) >= 78
            and factors.get("argument_structure", 0) >= 60
        )
        if duration <= PREFERRED_MAX_DURATION:
            status = "curto_preferencial"
        elif exception:
            status = "excecao_contextual"
        else:
            status = "longo_para_revisao"
        return {
            "status": status,
            "preferred_max_seconds": int(PREFERRED_MAX_DURATION),
            "shorter_is_preferred": True,
            "exception": exception,
            "reason": (
                "menor intervalo autossuficiente priorizado"
                if status == "curto_preferencial"
                else "corte acima da preferência mantido por hook, argumento e completude"
                if exception
                else "duração acima da preferência; revisar se há contexto suficiente"
            ),
        }

    def _topic_signature(self, text: str, political_signals: dict) -> str:
        """Build a transparent lexical topic key for portfolio diversification.

        This is intentionally a lightweight signal, not a claim of semantic
        understanding. It combines the political/editorial type with the most
        repeated meaningful terms so the UI and tests can audit its behavior.
        """
        normalized = _normalize(text)
        terms = [
            term for term in normalized.split()
            if len(term) >= 4 and term not in TOPIC_STOPWORDS and not term.isdigit()
        ]
        counts = {}
        for term in terms:
            counts[term] = counts.get(term, 0) + 1
        top_terms = sorted(counts, key=lambda term: (-counts[term], term))[:3]
        editorial_type = str(political_signals.get("editorial_type") or "geral")
        return f"{editorial_type}:{'-'.join(top_terms)}" if top_terms else editorial_type

    def _feedback_payload(self, adjustment: float, *, candidate_origin="", candidate_confidence=None) -> dict:
        calibration = self.feedback_calibration if isinstance(self.feedback_calibration, dict) else {}
        duration_signal = calibration.get("duration_signal") if isinstance(calibration.get("duration_signal"), dict) else {}
        origin_deltas = calibration.get("candidate_origin_deltas") if isinstance(calibration.get("candidate_origin_deltas"), dict) else {}
        origin_delta = origin_deltas.get(str(candidate_origin or ""), 0.0)
        try:
            origin_delta = float(origin_delta)
        except (TypeError, ValueError):
            origin_delta = 0.0
        try:
            normalized_confidence = max(0.0, min(1.0, float(candidate_confidence)))
        except (TypeError, ValueError):
            normalized_confidence = 0.75
        origin_adjustment = origin_delta * 0.075 * (0.5 + normalized_confidence * 0.5)
        return {
            "eligible": bool(calibration.get("eligible")),
            "sample_size": int(calibration.get("sample_size", 0) or 0),
            "approved_count": int(calibration.get("approved_count", 0) or 0),
            "rejected_count": int(calibration.get("rejected_count", 0) or 0),
            "adjustment": round(float(adjustment or 0.0), 2),
            "candidate_origin": str(candidate_origin or ""),
            "candidate_origin_delta": round(origin_delta, 2),
            "candidate_origin_adjustment": round(origin_adjustment, 2),
            "candidate_origin_confidence": round(normalized_confidence, 3),
            "origin_calibration_eligible": bool(
                calibration.get("origin_calibration", {}).get("eligible")
                if isinstance(calibration.get("origin_calibration"), dict)
                else False
            ),
            "duration_signal": {
                "usable": bool(duration_signal.get("usable")),
                "approved_mean_seconds": float(duration_signal.get("approved_mean_seconds", 0.0) or 0.0),
                "rejected_mean_seconds": float(duration_signal.get("rejected_mean_seconds", 0.0) or 0.0),
                "gap_seconds": float(duration_signal.get("gap_seconds", 0.0) or 0.0),
                "interpretation": str(duration_signal.get("interpretation") or ""),
            },
        }

    def _feedback_adjustment(self, factors: dict, *, candidate_origin="", candidate_confidence=None) -> float:
        """Return a bounded factor adjustment plus a weak, source-level signal.

        Factor deltas compare approved and rejected clips. Origin deltas are
        smoothed approval-rate lifts and can contribute at most 1.5 points before
        the global +/- 6 point cap, so provenance never overrides context gates.
        """
        calibration = self.feedback_calibration
        if not calibration.get("eligible"):
            return 0.0
        deltas = calibration.get("factor_deltas") or {}
        contributions = []
        for factor, delta in deltas.items():
            value = factors.get(factor)
            if not isinstance(value, (int, float)) or not isinstance(delta, (int, float)):
                continue
            if abs(delta) < 2:
                continue
            direction = 1.0 if delta > 0 else -1.0
            contributions.append(direction * ((float(value) - 50.0) / 50.0) * min(abs(float(delta)), 25.0))
        factor_adjustment = (
            sum(contributions) / len(contributions) * 0.35
            if contributions
            else 0.0
        )
        origin_deltas = calibration.get("candidate_origin_deltas") or {}
        origin_delta = origin_deltas.get(str(candidate_origin or ""), 0.0)
        try:
            origin_delta = float(origin_delta)
        except (TypeError, ValueError):
            origin_delta = 0.0
        try:
            confidence = max(0.0, min(1.0, float(candidate_confidence)))
        except (TypeError, ValueError):
            confidence = 0.75
        origin_adjustment = origin_delta * 0.075 * (0.5 + confidence * 0.5)
        return max(-6.0, min(6.0, factor_adjustment + origin_adjustment))

    def _hook(self, text: str) -> float:
        normalized = _normalize(text)
        opening = " ".join(normalized.split()[:24])
        matches = sum(bool(re.search(pattern, opening)) for pattern in HOOK_PATTERNS)
        score = 35 + min(45, matches * 15)
        if "?" in text[:100]:
            score += 8
        if "!" in text[:100]:
            score += 8
        return min(100.0, score)

    def _flow(self, text: str, duration: float) -> float:
        if not text:
            return 0.0
        sentences = [part.strip() for part in re.split(r"[.!?]+", text) if part.strip()]
        score = 45.0
        if len(sentences) >= 2:
            score += 20
        if len(sentences) >= 4:
            score += 10
        if text.rstrip()[-1:] in ".!?":
            score += 15
        # Duration is scored separately by ``_duration_fit`` so flow measures
        # narrative continuity rather than rewarding an arbitrary time window.
        first = _normalize(text).split()[:1]
        if first and first[0] in MID_SENTENCE_STARTERS:
            score -= 25
        return max(0.0, min(100.0, score))

    def _value(self, text: str) -> float:
        words = _normalize(text).split()
        if not words:
            return 0.0
        emotional = sum(word in EMOTIONAL_TERMS or any(term in word for term in EMOTIONAL_TERMS) for word in words)
        numbers = sum(bool(re.search(r"\d", word)) for word in words)
        unique_ratio = len(set(words)) / len(words)
        score = 35 + min(25, emotional * 5) + min(20, numbers * 4) + unique_ratio * 15
        if "?" in text or "!" in text:
            score += 5
        return max(0.0, min(100.0, score))

    def _argument_structure(self, text: str, closure_type: str) -> float:
        normalized = _normalize(text)
        marker_count = sum(marker in normalized for marker in ARGUMENT_MARKERS)
        sentence_count = len([part for part in re.split(r"[.!?]+", text) if part.strip()])
        score = 35.0 + min(35.0, marker_count * 12.0)
        if sentence_count >= 2:
            score += 12.0
        if closure_type == "conclusion":
            score += 15.0
        elif closure_type == "cliffhanger":
            score -= 8.0
        return max(0.0, min(100.0, score))

    def _context_match(self, text: str, context: str) -> float:
        if not context:
            return 70.0
        words = {
            word for word in _normalize(context).split()
            if len(word) > 3 and word not in {"quero", "encontre", "momentos", "fale", "sobre", "para", "onde"}
        }
        if not words:
            return 50.0
        text_words = set(_normalize(text).split())
        matched = len(words & text_words)
        return min(100.0, 25.0 + (matched / len(words)) * 75.0)

    def _chapter_coherence(self, clip: dict) -> float:
        value = clip.get("chapter_coherence_score")
        if isinstance(value, (int, float)):
            return max(0.0, min(100.0, float(value)))
        return 50.0

    def _visual_change_density(self, clip: dict) -> float:
        """Estimate visual rhythm only when the pipeline provides scene metadata."""
        for key in ("visual_change_density", "scene_change_density"):
            value = clip.get(key)
            if isinstance(value, (int, float)):
                return max(0.0, min(100.0, float(value)))
        changes = clip.get("scene_changes")
        duration = float(clip.get("duration") or 0.0)
        if isinstance(changes, (list, tuple)) and duration > 0:
            changes_per_second = len(changes) / duration
            return max(0.0, min(100.0, 45.0 + changes_per_second * 35.0))
        return 50.0

    def _audio_energy(self, clip: dict, energy_profile) -> float:
        for key in ("audio_energy", "energy_score", "energy"):
            value = clip.get(key)
            if isinstance(value, (int, float)):
                return max(0.0, min(100.0, float(value)))
        if isinstance(energy_profile, dict):
            value = energy_profile.get("score") or energy_profile.get("mean")
            if isinstance(value, (int, float)):
                return max(0.0, min(100.0, float(value)))
        if isinstance(energy_profile, (list, tuple)):
            start = float(clip.get("start", 0))
            end = float(clip.get("end", start))
            points = [
                item for item in energy_profile
                if start <= float(item.get("time", -1)) <= end
            ]
            normalized = [
                float(item.get("energy_normalized", 0.0))
                for item in points
                if isinstance(item, dict)
            ]
            if normalized:
                mean_energy = sum(normalized) / len(normalized)
                peak_energy = max(normalized)
                return max(0.0, min(100.0, 35.0 + mean_energy * 45.0 + peak_energy * 20.0))
        return 55.0

    def _clarity(self, text: str) -> float:
        words = _normalize(text).split()
        if not words:
            return 0.0
        filler_count = 0
        normalized = " ".join(words)
        for filler in FILLERS:
            if " " in filler:
                filler_count += normalized.count(filler)
            else:
                filler_count += sum(word == filler for word in words)
        return max(0.0, min(100.0, 92.0 - (filler_count / len(words)) * 180.0))

    def _closure_type(self, text: str) -> str:
        ending = _normalize(text)[-260:]
        has_continuity = any(pattern in ending for pattern in CONTINUITY_PATTERNS)
        has_resolution = any(pattern in ending for pattern in RESOLUTION_PATTERNS)
        if has_continuity and not has_resolution:
            return "cliffhanger"
        if has_resolution:
            return "conclusion"
        if str(text or "").rstrip().endswith((".", "!", "?")):
            return "closed_statement"
        return "open"

    def _completeness(self, text: str, closure_type: str = "open") -> float:
        score = 45.0
        if text.rstrip()[-1:] in ".!?":
            score += 35
        if len(text.split()) >= 20:
            score += 10
        first = _normalize(text).split()[:1]
        if first and first[0] in MID_SENTENCE_STARTERS:
            score -= 30
        # Cliffhangers may still be good updates, but they cannot be ranked as
        # equally self-contained as a resolved statement or answer.
        if closure_type == "cliffhanger":
            score -= 12
        elif closure_type == "conclusion":
            score += 6
        return max(0.0, min(100.0, score))

    def _context_quality(self, clip: dict, text: str, closure_type: str) -> float:
        """Score whether the candidate can stand alone without hiding uncertainty."""
        flags = clip if isinstance(clip, dict) else {}
        score = 50.0
        if flags.get("context_complete"):
            score += 18.0
        if flags.get("starts_mid_sentence"):
            score -= 28.0
        if flags.get("starts_with_context_reference"):
            score -= 22.0
        if flags.get("question_answer_complete") or flags.get("qa_bridge"):
            score += 14.0
        elif flags.get("question_detected"):
            score -= 4.0
        if flags.get("evidence_present"):
            score += 6.0
        if flags.get("payoff_complete") or closure_type in {"conclusion", "closed_statement"}:
            score += 12.0
        if closure_type == "cliffhanger":
            score -= 18.0
        if len(_normalize(text).split()) < 12:
            score -= 12.0
        return max(0.0, min(100.0, score))

    def _confidence(self, text: str, factors: dict, duration: float) -> float:
        evidence = min(1.0, len(text.split()) / 35.0)
        consistency = 1.0 - (max(factors.values()) - min(factors.values())) / 200.0
        duration_evidence = 1.0 if 8 <= duration <= PREFERRED_MAX_DURATION else 0.78
        context_evidence = max(0.35, min(1.0, float(factors.get("context_quality", 50.0)) / 100.0))
        return max(0.0, min(1.0, 0.30 * evidence + 0.30 * consistency + 0.20 * duration_evidence + 0.20 * context_evidence))

    def _reason(self, factors: dict, context: str) -> str:
        labels = {
            "hook": "abertura forte",
            "flow": "fluxo coerente",
            "value": "valor informativo/emocional",
            "argument_structure": "estrutura de argumento",
            "context_match": "aderência ao pedido",
            "context_completeness": "contexto autossuficiente",
            "audio_energy": "energia de áudio",
            "visual_change_density": "ritmo visual",
            "clarity": "clareza de fala",
            "completeness": "raciocínio completo",
            "topic_relevance": "tema político aderente",
            "claim_strength": "tese ou posicionamento claro",
            "conflict_or_stakes": "conflito ou consequência",
            "proposal_strength": "proposta concreta",
            "evidence_density": "dado ou evidência",
            "mobilization": "potencial de mobilização",
            "specificity": "especificidade",
            "conclusion": "conclusão editorial",
            "political_editorial_fit": "aderência ao formato político",
            "editorial_family_fit": "aderência à família editorial",
            "profile_fit": "aderência ao perfil do canal",
            "chapter_coherence": "coerência de capítulo e contexto temporal",
            "campaign_hub_prior": "observação histórica de hook no Campaign Hub",
            "duration_fit": "brevidade preferencial sem cortar contexto",
            "context_quality": "contexto autossuficiente e payoff",
            "speaker_boundary": "fronteira de locutor",
            "qa_boundary": "ponte pergunta–resposta",
            "contextual_hook_alignment": "alinhamento ao hook contextual",
            "feedback_reason_alignment": "calibração por motivo editorial",
        }
        ordered = sorted(factors.items(), key=lambda pair: pair[1], reverse=True)
        top = [labels[key] for key, value in ordered[:3] if value >= 60]
        return "; ".join(top) if top else "evidência editorial insuficiente"

    def _grade(self, value: float) -> str:
        return "A" if value >= 75 else "B" if value >= 50 else "C"

    def _diversity_reason(self, clip: dict, selected: list) -> str:
        strongest = (0.0, "")
        for existing in selected:
            same_source = True
            source_keys = ("source_id", "live_id", "source", "origin", "video_id")
            left_source = next((str(clip.get(key) or "") for key in source_keys if clip.get(key)), "")
            right_source = next((str(existing.get(key) or "") for key in source_keys if existing.get(key)), "")
            if left_source and right_source and left_source != right_source:
                same_source = False
            overlap = _interval_overlap(clip, existing) if same_source else 0.0
            similarity = _text_similarity(clip.get("text", ""), existing.get("text", ""))
            topic_similarity = _topic_similarity(clip.get("topic_signature", ""), existing.get("topic_signature", "")) if same_source else 0.0
            signals = [
                (overlap * 100.0, "intervalo temporal sobreposto"),
                (similarity * 80.0, "texto muito semelhante"),
                (topic_similarity * 48.0, "tema editorial semelhante"),
            ]
            strongest = max(strongest, max(signals, key=lambda item: item[0]))
        return strongest[1]

    def _diversity_penalty(self, clip: dict, selected: list) -> float:
        penalty = 0.0
        for existing in selected:
            same_source = True
            source_keys = ("source_id", "live_id", "source", "origin", "video_id")
            left_source = next((str(clip.get(key) or "") for key in source_keys if clip.get(key)), "")
            right_source = next((str(existing.get(key) or "") for key in source_keys if existing.get(key)), "")
            if left_source and right_source and left_source != right_source:
                same_source = False
            overlap = _interval_overlap(clip, existing) if same_source else 0.0
            similarity = _text_similarity(clip.get("text", ""), existing.get("text", ""))
            topic_similarity = _topic_similarity(
                clip.get("topic_signature", ""), existing.get("topic_signature", "")
            ) if same_source else 0.0
            penalty = max(penalty, overlap * 100.0, similarity * 80.0, topic_similarity * 48.0)
        return penalty


def _normalize(text: str) -> str:
    raw = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in raw if not unicodedata.combining(char))


def _interval_overlap(first: dict, second: dict) -> float:
    start = max(float(first.get("start", 0)), float(second.get("start", 0)))
    end = min(float(first.get("end", 0)), float(second.get("end", 0)))
    intersection = max(0.0, end - start)
    first_duration = max(0.001, float(first.get("end", 0)) - float(first.get("start", 0)))
    second_duration = max(0.001, float(second.get("end", 0)) - float(second.get("start", 0)))
    return intersection / min(first_duration, second_duration)


def _topic_similarity(first: str, second: str) -> float:
    """Compare transparent topic signatures generated by ``_topic_signature``."""
    left_type, _, left_terms = str(first or "").partition(":")
    right_type, _, right_terms = str(second or "").partition(":")
    left = {item for item in left_terms.split("-") if item}
    right = {item for item in right_terms.split("-") if item}
    lexical = len(left & right) / len(left | right) if left and right else 0.0
    type_bonus = 0.15 if left_type and left_type == right_type and lexical >= 0.34 else 0.0
    return min(1.0, lexical + type_bonus)


def _text_similarity(first: str, second: str) -> float:
    left = set(_normalize(first).split())
    right = set(_normalize(second).split())
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)
