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


HOOK_PATTERNS = [
    r"voce\s+sabia",
    r"presta\s+atencao",
    r"olha\s+(isso|so)",
    r"a\s+verdade\s+(e|eh)",
    r"ninguem\s+te\s+(conta|fala|diz)",
    r"o\s+problema\s+e",
    r"a\s+questao\s+e",
    r"eu\s+vou\s+te\s+(falar|dizer|contar)",
    r"(absurdo|vergonha|mentira|bomba|urgente|chocante)",
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


class EditorialRanker:
    def __init__(
        self,
        channel_context: str = "",
        editorial_profile: str = PROFILE_NAME,
        feedback_calibration: Optional[dict] = None,
    ):
        self.channel_context = channel_context or ""
        self.editorial_profile = editorial_profile or PROFILE_NAME
        self.feedback_calibration = feedback_calibration or {}

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
                clip.get("duration", 0),
            ),
            reverse=True,
        )

        selected = []
        for clip in scored:
            penalty = self._diversity_penalty(clip, selected)
            clip["factors"]["diversity"] = round(max(0.0, 100.0 - penalty), 1)
            clip["diversity_penalty"] = round(penalty, 1)
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
            key=lambda clip: clip.get("editorial_potential_score", 0), reverse=True
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
            "editorial_family_fit": 50.0,
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
            "completeness": 0.12,
            "editorial_family_fit": 0.04,
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
        feedback_adjustment = self._feedback_adjustment(factors)
        if feedback_adjustment:
            score = max(0, min(100, int(round(score + feedback_adjustment))) )
            factors["editor_feedback_alignment"] = round(50.0 + feedback_adjustment * 5.0, 1)

        confidence = self._confidence(text, factors, duration)
        breakdown = {
            "hook": self._grade(factors["hook"]),
            "flow": self._grade(factors["flow"]),
            "value": self._grade(factors["value"]),
            "energy": self._grade(factors["audio_energy"]),
        }
        reason = self._reason(factors, user_context)
        topic_signature = self._topic_signature(text, political_signals)
        return {
            "viral_score": score,
            "editorial_potential_score": score,
            "editorial_score_version": "v1-feedback-calibrated" if feedback_adjustment else "v1-explainable",
            "topic_signature": topic_signature,
            "closure_type": closure_type,
            "breakdown": breakdown,
            "factors": {key: round(value, 1) for key, value in factors.items()},
            "confidence": round(confidence, 2),
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
            "reframe_policy": format_profile["reframe_policy"],
            "preserve_composition": format_profile["preserve_composition"],
            "review_flags": {
                "needs_fact_review": bool(political_signals.get("needs_fact_review")),
                "needs_legal_review": bool(political_signals.get("needs_legal_review")),
                "sensitive_claim_hits": int(political_signals.get("sensitive_claim_hits", 0) or 0),
                "named_entity_count": int(political_signals.get("named_entity_count", 0) or 0),
                "preserve_composition": format_profile["preserve_composition"],
                "visual_observation_available": bool(clip.get("visual_observation")),
            },
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

    def _feedback_adjustment(self, factors: dict) -> float:
        """Return a bounded adjustment only after enough final editor decisions.

        Factor deltas compare approved and rejected clips. The adjustment stays
        within +/- 6 points so model and editorial signals remain dominant.
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
        if not contributions:
            return 0.0
        return max(-6.0, min(6.0, sum(contributions) / len(contributions) * 0.35))

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
        if 20 <= duration <= 75:
            score += 10
        elif duration < 8 or duration > 180:
            score -= 15
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

    def _confidence(self, text: str, factors: dict, duration: float) -> float:
        evidence = min(1.0, len(text.split()) / 35.0)
        consistency = 1.0 - (max(factors.values()) - min(factors.values())) / 200.0
        duration_evidence = 1.0 if 10 <= duration <= 120 else 0.7
        return max(0.0, min(1.0, 0.35 * evidence + 0.4 * consistency + 0.25 * duration_evidence))

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
        }
        ordered = sorted(factors.items(), key=lambda pair: pair[1], reverse=True)
        top = [labels[key] for key, value in ordered[:3] if value >= 60]
        return "; ".join(top) if top else "evidência editorial insuficiente"

    def _grade(self, value: float) -> str:
        return "A" if value >= 75 else "B" if value >= 50 else "C"

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
