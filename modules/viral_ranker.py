import re
import math


HOOK_PATTERNS_PT = [
    r"voce\s+sabia",
    r"presta\s+atencao",
    r"olha\s+isso",
    r"verdade\s+(e|eh)\s+que",
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
    r"traic",
    r"brasil",
    r"povo\s+brasileiro",
    r"nosso\s+pais",
    r"liberdade",
    r"democracia",
    r"constituicao",
    r"direita",
    r"conservador",
]

EMOTIONAL_WORDS_PT = [
    "inacreditavel", "absurdo", "vergonha", "mentira", "corrupto",
    "criminoso", "covarde", "traidor", "hipocrita", "descarado",
    "lixo", "nojo", "revolta", "indignacao", "injustica",
    "liberdade", "patriota", "heroi", "coragem", "forca",
    "vitoria", "luta", "resistencia", "verdade", "justica",
    "povo", "nacao", "brasil", "deus", "familia",
    "impressionante", "incrivel", "surreal", "devastador", "chocante",
]

CALL_TO_ACTION_PATTERNS = [
    r"compart[iy]lh",
    r"inscrev",
    r"coment[ae]",
    r"deixa\s+(o\s+)?like",
    r"segue\s+o\s+canal",
    r"ativa\s+o\s+sininho",
    r"link\s+na\s+descricao",
]


class ViralRanker:
    def __init__(self, channel_context=""):
        self.channel_context = channel_context

    def score_clip(self, text, duration, start_time, energy_data=None):
        scores = {}

        scores["hook"] = self._score_hook(text)
        scores["emotional"] = self._score_emotional_intensity(text)
        scores["duration"] = self._score_duration(duration)
        scores["density"] = self._score_text_density(text, duration)
        scores["cta"] = self._score_cta(text)
        scores["energy"] = self._score_energy(energy_data) if energy_data else 5.0
        scores["opening"] = self._score_opening_strength(text)

        weights = {
            "hook": 0.25,
            "emotional": 0.20,
            "duration": 0.10,
            "density": 0.10,
            "cta": 0.05,
            "energy": 0.15,
            "opening": 0.15,
        }

        final_score = sum(scores[k] * weights[k] for k in scores)
        final_score = min(100, max(0, final_score))

        return {
            "viral_score": round(final_score),
            "breakdown": {k: round(v, 1) for k, v in scores.items()},
            "has_hook": scores["hook"] > 50,
            "emotional_intensity": round(scores["emotional"] / 10, 2),
        }

    def _score_hook(self, text):
        text_lower = self._normalize(text)
        first_words = " ".join(text_lower.split()[:20])

        hook_count = 0
        for pattern in HOOK_PATTERNS_PT:
            if re.search(pattern, first_words):
                hook_count += 1

        if hook_count >= 3:
            return 100
        elif hook_count >= 2:
            return 80
        elif hook_count >= 1:
            return 60

        if len(first_words.split()) >= 5 and any(
            c in first_words for c in ["?", "!"]
        ):
            return 40

        return 15

    def _score_emotional_intensity(self, text):
        text_lower = self._normalize(text)
        words = text_lower.split()
        total_words = max(len(words), 1)

        emotional_count = 0
        for word in words:
            for ew in EMOTIONAL_WORDS_PT:
                if ew in word:
                    emotional_count += 1
                    break

        exclamation_count = text.count("!")
        question_count = text.count("?")
        caps_words = sum(1 for w in text.split() if w.isupper() and len(w) > 2)

        density = emotional_count / total_words
        score = min(100, density * 500 + exclamation_count * 5 + question_count * 3 + caps_words * 3)

        return score

    def _score_duration(self, duration):
        if 25 <= duration <= 55:
            return 100
        elif 15 <= duration <= 60:
            return 80
        elif duration < 15:
            return 40
        elif duration <= 90:
            return 60
        else:
            return max(20, 100 - (duration - 60) * 2)

    def _score_text_density(self, text, duration):
        words = len(text.split())
        words_per_second = words / max(duration, 1)

        if 2.0 <= words_per_second <= 3.5:
            return 100
        elif 1.5 <= words_per_second <= 4.0:
            return 70
        elif words_per_second < 1.0:
            return 30
        else:
            return 50

    def _score_cta(self, text):
        text_lower = self._normalize(text)
        cta_count = 0
        for pattern in CALL_TO_ACTION_PATTERNS:
            if re.search(pattern, text_lower):
                cta_count += 1
        return min(100, cta_count * 40)

    def _score_energy(self, energy_data):
        if not energy_data:
            return 50

        energies = [e.get("energy_normalized", 0) for e in energy_data]
        if not energies:
            return 50

        avg = sum(energies) / len(energies)
        peak = max(energies)
        variance = sum((e - avg) ** 2 for e in energies) / len(energies)

        score = avg * 40 + peak * 30 + min(variance * 100, 30)
        return min(100, max(0, score))

    def _score_opening_strength(self, text):
        words = text.split()
        first_sentence = ""
        for i, word in enumerate(words):
            first_sentence += word + " "
            if any(first_sentence.rstrip().endswith(p) for p in [".", "!", "?", "..."]):
                break
            if i > 15:
                break

        first_sentence = first_sentence.strip()
        score = 30

        if first_sentence.endswith("!"):
            score += 20
        if first_sentence.endswith("?"):
            score += 15

        first_lower = self._normalize(first_sentence)
        for pattern in HOOK_PATTERNS_PT:
            if re.search(pattern, first_lower):
                score += 15
                break

        if len(first_sentence.split()) <= 10:
            score += 10

        return min(100, score)

    def rank_clips(self, clips_data, energy_profiles=None):
        ranked = []
        for i, clip in enumerate(clips_data):
            energy = None
            if energy_profiles and i < len(energy_profiles):
                energy = energy_profiles[i]

            score_data = self.score_clip(
                clip.get("text", ""),
                clip.get("duration", 30),
                clip.get("start", 0),
                energy
            )

            ranked.append({
                **clip,
                **score_data,
            })

        ranked.sort(key=lambda x: x["viral_score"], reverse=True)
        return ranked

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
