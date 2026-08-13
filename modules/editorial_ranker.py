"""Explainable editorial scoring for candidate clips.

This module deliberately avoids presenting a heuristic as a statistical
prediction. It returns a comparable editorial potential score plus the factors
that produced it, so the review UI can explain and calibrate the ranking.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Optional

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

FILLERS = {
    "ah", "eh", "tipo", "entao", "sabe", "basicamente", "na verdade",
    "ou seja", "entendeu", "digamos", "assim", "enfim", "bom", "olha",
}

MID_SENTENCE_STARTERS = {"e", "mas", "porem", "entao", "porque", "que", "ai", "ou", "nem"}


class EditorialRanker:
    def __init__(self, channel_context: str = "", editorial_profile: str = PROFILE_NAME):
        self.channel_context = channel_context or ""
        self.editorial_profile = editorial_profile or PROFILE_NAME

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

    def score_clip(self, clip: dict, *, user_context: str = "", energy_profile=None) -> dict:
        text = str(clip.get("text") or "").strip()
        duration = float(clip.get("duration") or max(1.0, float(clip.get("end", 0)) - float(clip.get("start", 0))))
        factors = {
            "hook": self._hook(text),
            "flow": self._flow(text, duration),
            "value": self._value(text),
            "context_match": self._context_match(text, user_context),
            "audio_energy": self._audio_energy(clip, energy_profile),
            "visual_change_density": self._visual_change_density(clip),
            "clarity": self._clarity(text),
            "completeness": self._completeness(text),
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
                if isinstance(value, (int, float)) and key not in {"questions", "exclamations"}
            })
        weights = {
            "hook": 0.17,
            "flow": 0.16,
            "value": 0.17,
            "context_match": 0.13,
            "audio_energy": 0.10,
            "visual_change_density": 0.06,
            "clarity": 0.08,
            "completeness": 0.13,
        }
        if not user_context:
            weights["context_match"] = 0.0
            weights["value"] += 0.07
            weights["flow"] += 0.07

        base_score = sum(factors[key] * weight for key, weight in weights.items())
        if political_signals:
            score = int(round(base_score * 0.65 + political_signals["political_editorial_fit"] * 0.35))
        else:
            score = int(round(base_score))
        confidence = self._confidence(text, factors, duration)
        breakdown = {
            "hook": self._grade(factors["hook"]),
            "flow": self._grade(factors["flow"]),
            "value": self._grade(factors["value"]),
            "energy": self._grade(factors["audio_energy"]),
        }
        reason = self._reason(factors, user_context)
        return {
            "viral_score": score,
            "editorial_potential_score": score,
            "editorial_score_version": "v1-explainable",
            "breakdown": breakdown,
            "factors": {key: round(value, 1) for key, value in factors.items()},
            "confidence": round(confidence, 2),
            "has_hook": factors["hook"] >= 55,
            "reason": clip.get("reason") or reason,
            "political_profile": self.editorial_profile if political_signals else "",
            "political_editorial_type": political_signals.get("editorial_type", "") if political_signals else "",
            "political_signals": political_signals,
        }

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

    def _completeness(self, text: str) -> float:
        score = 45.0
        if text.rstrip()[-1:] in ".!?":
            score += 35
        if len(text.split()) >= 20:
            score += 10
        first = _normalize(text).split()[:1]
        if first and first[0] in MID_SENTENCE_STARTERS:
            score -= 30
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
            overlap = _interval_overlap(clip, existing)
            similarity = _text_similarity(clip.get("text", ""), existing.get("text", ""))
            penalty = max(penalty, overlap * 100.0, similarity * 80.0)
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


def _text_similarity(first: str, second: str) -> float:
    left = set(_normalize(first).split())
    right = set(_normalize(second).split())
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)
