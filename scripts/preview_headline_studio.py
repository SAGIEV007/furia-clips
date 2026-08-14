#!/usr/bin/env python3
"""Preview deterministic artwork-copy suggestions from a TXT, SRT or VTT file."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from modules.headline_studio import generate_artwork_copy


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python scripts/preview_headline_studio.py <transcricao> [formato] [minicontexto]", file=sys.stderr)
        return 2
    source = Path(sys.argv[1]).expanduser()
    if not source.is_file():
        print(f"Arquivo não encontrado: {source}", file=sys.stderr)
        return 2
    preferred_format = sys.argv[2] if len(sys.argv) > 2 else "auto"
    mini_context = sys.argv[3] if len(sys.argv) > 3 else ""
    studio = generate_artwork_copy(
        source.read_text(encoding="utf-8", errors="replace"),
        mini_context=mini_context,
        preferred_format=preferred_format,
        ai_backend=None,
    )
    print(json.dumps(studio, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
