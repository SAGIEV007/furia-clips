"""Fix the names automatic captioning gets wrong, and only the names.

Every caption engine loses proper nouns: they are rare words with no context to
lean on, and a Portuguese recogniser has never heard of Kataguiri. The Acervo
knows this and marks them — on a 31-minute sabatina, forty of its audio-check
flags were proper nouns. Published with the error, a clip carries a misspelt
name in front of thousands of people who know how it is written.

Correcting a name is safe in a way that correcting a word is not. A name is a
name: when the sound is "kataguiri" there is one person it can be, and the audio
is not ambiguous about it. A content word is different — "custos" and "cursos"
sound alike and only the sentence decides, so those are reported and never
rewritten in silence. That line is deliberate and this module does not cross it.

Matching is phonetic as well as literal, because the ways a recogniser can spell
a name it does not know are unbounded. "Cataguiri", "katagiri" and "catagüiri"
all reduce to the same sound, so the list of known misspellings does not have to
be complete to work.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any


_DATA = Path(__file__).resolve().parent.parent / "data" / "lexico"
_LEXICON_PATH = _DATA / "nomes_missao.json"
_CHUB_PATH = _DATA / "entidades_chub.json"
_CACHE: dict[str, Any] | None = None

_WORD = re.compile(r"[0-9A-Za-zÀ-ÿ']+")


def load_lexicon() -> dict[str, Any]:
    """The names, from the data files. A missing file simply disables the pass.

    Two sources, and they do not carry the same authority. ``nomes_missao.json``
    is hand-curated: a person vouched for each spelling, so it may rewrite. The
    Campaign Hub export knows which spellings are the same entity and what role
    it plays, but it was extracted from automatic captions and inherited their
    mistakes — it says "Nicolas Ferreira" four times as often as the deputy's
    real name. So only its confirmed entries rewrite; the rest come in as
    entities Furia recognises but will not respell on its own.
    """
    global _CACHE
    if _CACHE is None:
        try:
            curated = json.loads(_LEXICON_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            curated = {"nomes": []}
        names = list(curated.get("nomes") or [])
        roles: dict[str, str] = {}
        try:
            hub = json.loads(_CHUB_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            hub = {"entradas": []}
        known = {str(entry.get("canonico") or "").lower() for entry in names}
        for entry in hub.get("entradas") or []:
            canonical = str(entry.get("canonico") or "").strip()
            if not canonical:
                continue
            roles.setdefault(canonical.lower(), str(entry.get("papel") or ""))
            if entry.get("confirmado") and canonical.lower() not in known:
                names.append({"canonico": canonical, "variantes": entry.get("variantes") or []})
        # Keep the curated file's own fields (schema_version, notes): the merge
        # adds to it, it does not replace it.
        _CACHE = {**curated, "nomes": names, "papeis": roles}
    return _CACHE


def role_of(name: str) -> str:
    """What part this entity plays in the speaker's material: ally, villain, place…

    The headline generator needs this as much as the caption needs the spelling:
    "Renan Santos detona <villain>" is only a headline when the target really is
    one.
    """
    return load_lexicon().get("papeis", {}).get(str(name or "").strip().lower(), "")


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")


def phonetic_key(text: str) -> str:
    """Reduce a word to how it sounds in Portuguese, roughly.

    Enough to collapse the spellings a recogniser invents for the same name, and
    deliberately not more: an aggressive key would merge different names.
    """
    key = _strip_accents(str(text or "")).lower()
    key = key.replace("qu", "k").replace("q", "k")
    key = re.sub(r"c(?=[ei])", "s", key)
    key = key.replace("c", "k").replace("ç", "s")
    key = re.sub(r"g(?=[ei])", "j", key)
    key = re.sub(r"gu(?=[ei])", "g", key)
    key = key.replace("ph", "f").replace("h", "")
    key = key.replace("y", "i").replace("w", "v")
    key = re.sub(r"ss+", "s", key)
    key = re.sub(r"z\b", "s", key)
    key = re.sub(r"(.)\1+", r"\1", key)
    return key


def _phrase_key(words: list[str]) -> str:
    return " ".join(phonetic_key(word) for word in words if word)


def _entries() -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for entry in load_lexicon().get("nomes") or []:
        canonical = str(entry.get("canonico") or "").strip()
        if not canonical:
            continue
        forms = {canonical.lower(), *(str(v).lower() for v in entry.get("variantes") or [])}
        # Variants of one name can have different word counts — "PCC" and
        # "pe ce ce" are the same name spoken two ways — so each length carries
        # its own set of keys. Keeping only the longest silently stopped the
        # short spelling from ever matching.
        keys: dict[int, set[str]] = {}
        for form in forms:
            words = _WORD.findall(form)
            if not words:
                continue
            keys.setdefault(len(words), set()).add(_phrase_key(words))
        if keys:
            prepared.append({"canonical": canonical, "keys": keys, "words": max(keys)})
    # Longer names first, so "Movimento Brasil Livre" is matched before "Brasil".
    prepared.sort(key=lambda item: item["words"], reverse=True)
    return prepared


def _key_distance(left: str, right: str) -> int:
    """Levenshtein over two phonetic keys."""
    if left == right:
        return 0
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, start=1):
        current = [i]
        for j, b in enumerate(right, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def _near_enough(window_key: str, known_key: str) -> bool:
    """Whether a caption's spelling is the same name with a syllable lost.

    Exact phonetic equality was not enough. A recogniser that has never heard
    "Kataguiri" does not merely respell it, it drops sound: "Quim Catagui"
    reduces to ``kim katagi`` against ``kim katagiri`` and no exact match finds
    it — which is why the name kept going out wrong after the corrector existed.

    The tolerance scales with length and the first sound must survive, so short
    names stay exact. "Lula" and "Lira" are two edits apart and must never merge.
    """
    if not window_key or not known_key or window_key[0] != known_key[0]:
        return False
    if min(len(window_key), len(known_key)) < 8:
        return False
    # The budget is read off the known name, not off what the recogniser
    # produced: a caption that dropped a syllable is shorter than the truth, and
    # measuring against the short form denied the tolerance in exactly the case
    # that needs it — "kim katagi" against "kim katagiri".
    return _key_distance(window_key, known_key) <= (2 if len(known_key) >= 11 else 1)


def correct_names(text: str) -> tuple[str, list[dict[str, str]]]:
    """Rewrite the known names and report every change made.

    The report matters as much as the correction: an operator publishing a clip
    should be able to see that the caption was touched and what it said before.
    """
    original = str(text or "")
    if not original.strip():
        return original, []

    tokens = list(_WORD.finditer(original))
    if not tokens:
        return original, []

    entries = _entries()
    corrections: list[dict[str, str]] = []
    replacements: list[tuple[int, int, str]] = []
    index = 0
    while index < len(tokens):
        matched = False
        for entry in entries:
            for size in sorted(entry["keys"], reverse=True):
                if index + size > len(tokens):
                    continue
                window = [tokens[position].group(0) for position in range(index, index + size)]
                window_key = _phrase_key(window)
                if window_key not in entry["keys"][size] and not any(
                    _near_enough(window_key, known) for known in entry["keys"][size]
                ):
                    continue
                start = tokens[index].start()
                end = tokens[index + size - 1].end()
                found = original[start:end]
                if found != entry["canonical"]:
                    replacements.append((start, end, entry["canonical"]))
                    corrections.append({"de": found, "para": entry["canonical"]})
                index += size
                matched = True
                break
            if matched:
                break
        if not matched:
            index += 1

    if not replacements:
        return original, []

    rebuilt = []
    cursor = 0
    for start, end, canonical in replacements:
        rebuilt.append(original[cursor:start])
        rebuilt.append(canonical)
        cursor = end
    rebuilt.append(original[cursor:])
    return "".join(rebuilt), corrections


# Words that sound alike and mean different things. These are never rewritten:
# only the sentence decides which one was said, and a caption that silently picks
# the wrong one is worse than one that asks to be checked.
AMBIGUOUS_PAIRS = (
    ("custos", "cursos"),
    ("cessão", "sessão", "seção"),
    ("conserto", "concerto"),
    ("censo", "senso"),
    ("acender", "ascender"),
    ("descriminar", "discriminar"),
    ("emigrante", "imigrante"),
    ("mandato", "mandado"),
    ("tráfico", "tráfego"),
    ("comprimento", "cumprimento"),
)


def flag_ambiguous(text: str) -> list[dict[str, Any]]:
    """Point at words whose twin would change the meaning, without touching them."""
    lowered = _strip_accents(str(text or "")).lower()
    found = []
    for group in AMBIGUOUS_PAIRS:
        for word in group:
            if re.search(rf"\b{_strip_accents(word).lower()}\b", lowered):
                twins = [other for other in group if other != word]
                found.append({"palavra": word, "confunde_com": twins, "acao": "conferir no áudio"})
                break
    return found


# Nouns ending in -a that are masculine anyway. Portuguese gender is guessable
# from the ending often enough to be useful and never often enough to be trusted,
# so the common exceptions are listed rather than inferred.
_MASCULINE_IN_A = {
    "dia", "problema", "sistema", "programa", "mapa", "planeta", "cinema", "tema",
    "esquema", "clima", "drama", "poema", "telefonema", "dilema", "sofá", "guaraná",
    "papa", "policial", "capital",
}
# And the mirror case, where the ending lies the other way: "2 motos" came out
# "dois motos" because the noun is feminine and ends in -o.
_FEMININE_IN_O = {"moto", "foto", "tribo", "libido"}
_NUMBER_WORDS = {"1": ("um", "uma"), "2": ("dois", "duas")}
_DIGIT_AS_ARTICLE = re.compile(r"(?<![\d.,:/-])([12])\s+([A-Za-zÀ-ÿ']+)")


def restore_number_words(text: str) -> tuple[str, list[dict[str, str]]]:
    """Write back the numbers that were spoken as words.

    Nobody says "eu tenho 1 casa". The recogniser writes the digit because it
    heard a numeral, and the editor fixes it by hand on every clip. Only 1 and 2
    are touched: they are the ones that carry gender, which is what makes the
    digit read as wrong rather than merely as a style choice.
    """
    corrections: list[dict[str, str]] = []

    def swap(match: re.Match[str]) -> str:
        digit, following = match.group(1), match.group(2)
        masculine, feminine = _NUMBER_WORDS[digit]
        stem = _strip_accents(following.lower())
        # The plural hides the gender: "motos" does not end in -a, and reading it
        # as masculine produced "dois motos".
        singular = stem[:-1] if stem.endswith("s") and len(stem) > 2 else stem
        looks_feminine = (singular.endswith("a") and singular not in _MASCULINE_IN_A) or singular in _FEMININE_IN_O
        word = feminine if looks_feminine else masculine
        corrections.append({"de": f"{digit} {following}", "para": f"{word} {following}"})
        return f"{word} {following}"

    rebuilt = _DIGIT_AS_ARTICLE.sub(swap, str(text or ""))
    return rebuilt, corrections


# Openers that make a sentence a question in Portuguese no matter what follows.
# "como" and "que" are deliberately absent: "Como eu disse" and "Que bom" are
# statements, and a question mark invented on those is a new error, not a fix.
_ASKS_OPEN = re.compile(
    r"^\s*(?:mas\s+|e\s+|então\s+|aí\s+)?"
    r"(?:qual|quais|quem|quando|onde|aonde|quanto|quantos|quantas|cadê|"
    r"por\s+que|porque|pra\s+que|será\s+que|como\s+é\s+que|como\s+que)\b",
    re.IGNORECASE,
)
# Tags that turn a statement into a question by being tacked on the end.
_ASKS_TAG = re.compile(
    r"\b(?:né|não\s+é|certo|entendeu|entende|sacou|tá|ok|correto|concorda|não\s+acha)\s*$",
    re.IGNORECASE,
)


def restore_question_mark(text: str) -> tuple[str, bool]:
    """Close a question with the mark the recogniser dropped.

    Only where the sentence is unambiguously interrogative. A missing question
    mark costs the reader a beat; an invented one changes a statement into a
    challenge, which on this material can invert who is being accused.
    """
    value = str(text or "").rstrip()
    if not value or value[-1] in "?!.…":
        return str(text or ""), False
    if _ASKS_OPEN.search(value) or _ASKS_TAG.search(value.rstrip(",;: ")):
        return f"{value.rstrip(',;: ')}?", True
    return str(text or ""), False


def review_caption(text: str) -> dict[str, Any]:
    """One pass over a caption line: names fixed, look-alikes flagged."""
    corrected, corrections = correct_names(text)
    corrected, number_fixes = restore_number_words(corrected)
    corrected, asked = restore_question_mark(corrected)
    corrections.extend(number_fixes)
    return {
        "texto": corrected,
        "correcoes": corrections,
        "conferir": flag_ambiguous(corrected),
        "pergunta_fechada": asked,
        "alterado": bool(corrections) or asked,
    }
