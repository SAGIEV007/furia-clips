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


_LEXICON_PATH = Path(__file__).resolve().parent.parent / "data" / "lexico" / "nomes_missao.json"
_CACHE: dict[str, Any] | None = None

_WORD = re.compile(r"[0-9A-Za-zÀ-ÿ']+")


def load_lexicon() -> dict[str, Any]:
    """The names, from the data file. A missing file simply disables the pass."""
    global _CACHE
    if _CACHE is None:
        try:
            _CACHE = json.loads(_LEXICON_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            _CACHE = {"nomes": []}
    return _CACHE


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
                if _phrase_key(window) not in entry["keys"][size]:
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


def review_caption(text: str) -> dict[str, Any]:
    """One pass over a caption line: names fixed, look-alikes flagged."""
    corrected, corrections = correct_names(text)
    return {
        "texto": corrected,
        "correcoes": corrections,
        "conferir": flag_ambiguous(corrected),
        "alterado": bool(corrections),
    }
