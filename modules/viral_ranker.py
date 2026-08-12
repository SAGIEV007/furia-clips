"""
Viral Ranker v2 — Category-based scoring with A/B/C grades.

Evaluates clips on 4 dimensions:
- Hook: Do the first 3 seconds grab attention?
- Flow: Does the clip have a coherent beginning, middle, and end?
- Value: Does it offer insight, strong opinion, emotion, or useful info?
- Energy: Is the vocal tone intense, animated, emotional?
"""

import re

from .editorial_ranker import EditorialRanker


HOOK_PATTERNS_PT = [
    r"voce\s+sabia",
    r"presta\s+atencao",
    r"olha\s+(isso|so)",
    r"a?\s*verdade\s+(e|eh)\s+que",
    r"ninguem\s+te\s+(conta|fala|diz)",
    r"(isso|aqui)\s+que\s+ninguem",
    r"por\s+que\s+(ninguem|nenhum)",
    r"cuidado",
    r"absurdo",
    r"vergonha",
    r"mentira",
    r"bomba",
    r"urgente",
    r"revelado",
    r"exposto",
    r"desmascarado",
    r"inacreditavel",
    r"chocante",
    r"polemic",
    r"escandal",
    r"denunci",
    r"corrupc",
    r"eu\s+vou\s+te\s+(falar|dizer|contar)",
    r"sabe\s+o\s+que",
    r"o\s+problema\s+e",
    r"a\s+questao\s+e",
]

EMOTIONAL_WORDS_PT = [
    "inacreditavel", "absurdo", "vergonha", "mentira", "corrupto",
    "criminoso", "covarde", "traidor", "hipocrita", "descarado",
    "lixo", "nojo", "revolta", "indignacao", "injustica",
    "liberdade", "patriota", "heroi", "coragem", "forca",
    "vitoria", "luta", "resistencia", "verdade", "justica",
    "povo", "nacao", "brasil", "deus", "familia",
    "impressionante", "incrivel", "surreal", "devastador", "chocante",
    "ridiculo", "tragedia", "desastre", "catastrofe", "horror",
]


class ViralRanker:
    def __init__(self, channel_context=""):
        self.channel_context = channel_context
        self._editorial_ranker = EditorialRanker(channel_context)

    def score_clip(self, clip):
        """Score a clip and assign A/B/C grades per category."""
        text = clip.get("text", "")
        duration = clip.get("duration", 30)

        # If clip already has LLM-assigned grades, convert and return
        if clip.get("breakdown") and isinstance(clip["breakdown"].get("hook"), str):
            return self._score_from_grades(clip)

        # Otherwise, calculate scores from text analysis
        hook_score = self._evaluate_hook(text)
        flow_score = self._evaluate_flow(text, duration)
        value_score = self._evaluate_value(text)
        energy_score = self._evaluate_energy(text)

        # Convert to grades
        hook_grade = self._score_to_grade(hook_score)
        flow_grade = self._score_to_grade(flow_score)
        value_grade = self._score_to_grade(value_score)
        energy_grade = self._score_to_grade(energy_score)

        # Weighted final score
        viral_score = int(
            hook_score * 0.30 +
            flow_score * 0.25 +
            value_score * 0.25 +
            energy_score * 0.20
        )

        return {
            "viral_score": viral_score,
            "breakdown": {
                "hook": hook_grade,
                "flow": flow_grade,
                "value": value_grade,
                "energy": energy_grade,
            },
            "has_hook": hook_grade in ("A", "B"),
        }

    def _score_from_grades(self, clip):
        """Convert existing A/B/C grades to numeric score."""
        grade_to_num = {"A": 90, "B": 55, "C": 25}
        breakdown = clip["breakdown"]

        hook = grade_to_num.get(breakdown.get("hook", "B"), 55)
        flow = grade_to_num.get(breakdown.get("flow", "B"), 55)
        value = grade_to_num.get(breakdown.get("value", "B"), 55)
        energy = grade_to_num.get(breakdown.get("energy", "B"), 55)

        viral_score = int(hook * 0.20 + flow * 0.35 + value * 0.25 + energy * 0.20)

        return {
            "viral_score": viral_score,
            "breakdown": breakdown,
            "has_hook": breakdown.get("hook", "C") in ("A", "B"),
        }

    def _evaluate_hook(self, text):
        """Evaluate if the opening grabs attention."""
        text_lower = self._normalize(text)
        first_words = " ".join(text_lower.split()[:20])

        score = 20  # base

        # Check for hook patterns
        hook_count = 0
        for pattern in HOOK_PATTERNS_PT:
            if re.search(pattern, first_words):
                hook_count += 1

        if hook_count >= 3:
            score = 100
        elif hook_count >= 2:
            score = 85
        elif hook_count >= 1:
            score = 70

        # Question or exclamation in first sentence
        first_sentence = text.split(".")[0] if "." in text[:100] else text[:80]
        if "!" in first_sentence:
            score = max(score, 60)
        if "?" in first_sentence:
            score = max(score, 55)

        # Short, punchy opening (under 10 words to first punctuation)
        first_punct_pos = len(first_sentence.split())
        if first_punct_pos <= 8:
            score += 10

        return min(100, score)

    def _evaluate_flow(self, text, duration):
        """Evaluate narrative completeness — beginning, middle, end."""
        score = 50  # base

        # Ends with proper punctuation (conclusion)
        stripped = text.strip()
        if stripped and stripped[-1] in ".!?":
            score += 25
        else:
            score -= 20

        # Has multiple sentences (development)
        sentence_count = len(re.split(r'[.!?]+', text))
        if sentence_count >= 3:
            score += 15
        elif sentence_count >= 2:
            score += 5

        # Duration sweet spot (25-55 seconds)
        if 25 <= duration <= 55:
            score += 10
        elif duration < 20 or duration > 70:
            score -= 10

        # Doesn't start with connector words (would indicate cut mid-thought)
        first_word = text.strip().split()[0].lower() if text.strip() else ""
        mid_sentence_starters = ["e", "mas", "porem", "entao", "porque", "que", "ai", "ou", "nem"]
        if first_word in mid_sentence_starters:
            score -= 25

        return max(0, min(100, score))

    def _evaluate_value(self, text):
        """Evaluate content value — insight, opinion, emotion, information."""
        text_lower = self._normalize(text)
        words = text_lower.split()
        total_words = max(len(words), 1)
        score = 40  # base

        # Emotional word density
        emotional_count = sum(1 for w in words if any(ew in w for ew in EMOTIONAL_WORDS_PT))
        density = emotional_count / total_words
        score += min(30, density * 400)

        # Exclamations and questions (engagement markers)
        score += min(15, text.count("!") * 4 + text.count("?") * 3)

        # Information density (more words per second = more content)
        # Approximate: if text is dense, it has more value
        if total_words > 50:
            score += 10
        elif total_words > 30:
            score += 5

        # CAPS words (emphasis)
        caps_words = sum(1 for w in text.split() if w.isupper() and len(w) > 2)
        score += min(10, caps_words * 3)

        return max(0, min(100, score))

    def _evaluate_energy(self, text):
        """Evaluate vocal energy from text cues (punctuation, caps, word choice)."""
        score = 50  # base

        # Exclamation marks indicate high energy
        excl = text.count("!")
        score += min(25, excl * 8)

        # ALL CAPS words
        caps = sum(1 for w in text.split() if w.isupper() and len(w) > 2)
        score += min(15, caps * 5)

        # Short, punchy sentences (high pace)
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        if sentences:
            avg_sentence_len = sum(len(s.split()) for s in sentences) / len(sentences)
            if avg_sentence_len < 10:  # Short sentences = fast pace
                score += 10
            elif avg_sentence_len > 25:  # Long sentences = slower pace
                score -= 10

        return max(0, min(100, score))

    def _score_to_grade(self, score):
        """Convert numeric score to A/B/C grade."""
        if score >= 75:
            return "A"
        elif score >= 50:
            return "B"
        else:
            return "C"

    def rank_clips(self, clips_data, user_context="", energy_profile=None):
        """Rank clips with explainable editorial factors and legacy aliases."""
        return self._editorial_ranker.rank_clips(
            clips_data,
            user_context=user_context,
            energy_profile=energy_profile,
        )

    def _normalize(self, text):
        text = text.lower()
        replacements = {
            "a": "aáàâã", "e": "eéèê", "i": "iíìî",
            "o": "oóòôõ", "u": "uúùû", "c": "cç",
        }
        for simple, accented in replacements.items():
            for char in accented[1:]:
                text = text.replace(char, simple)
        return text
