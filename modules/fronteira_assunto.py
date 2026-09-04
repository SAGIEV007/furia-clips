"""Pure gates for clip boundaries, with no external dependencies.

Research basis:
- `pesquisa-fronteira-de-saida-do-corte-2026-09-02.md` (Chub, 16.871 blocos)
- `pesquisa-fronteira-de-entrada-2026-09-01.md` (fronteira de assunto)
"""

from __future__ import annotations

import re

_BACKCHANNELS = {
    "ta",
    "tá",
    "uhum",
    "e isso",
    "é isso",
    "obrigado",
    "perfeito",
    "certo",
    "exato",
    "isso",
    "é",
    "sim",
    "não",
    "nao",
    "né",
    "aham",
    "show",
    "demais",
    "valeu",
}

_DEPENDENT_CONNECTIVES = {
    "e",
    "mas",
    "então",
    "aí",
    "ai",
    "pois",
    "porque",
    "que",
    "né",
    "certo",
    "é",
    "tá",
    "ta",
    "ah",
    "eh",
    "ih",
    "também",
    "tbm",
    "assim",
    "logo",
    "portanto",
    "contudo",
    "todavia",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def fim_fragmentado(text: str, *, min_chars: int = 15) -> bool:
    """Return True if the clip ending looks like a truncated fragment.

    A backchannel or legitimate closing phrase is not a fragment, even when
    short. Research shows short non-backchannel endings are 3,6x less likely
    to become excellence clips and 2,15x more likely to be bad clips.
    """
    normalized = _clean(text)
    if not normalized:
        return False
    if normalized.lower() in _BACKCHANNELS:
        return False
    return len(normalized) < min_chars


def abre_dependente(text: str, *, min_chars: int = 25) -> bool:
    """Return True if the clip opening depends on prior context.

    A dependent opening usually starts with a connective and is short enough
    to be an orphan anaphora rather than a complete sentence.
    """
    normalized = _clean(text)
    if not normalized:
        return False
    first_word = normalized.split()[0].lower().strip(".,;:!?…–—")
    if first_word not in _DEPENDENT_CONNECTIVES:
        return False
    return len(normalized) < min_chars
