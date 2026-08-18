#!/usr/bin/env python3
"""Convert one Campaign Hub block-tool result into a Furia local-memory export.

The conversion itself lives in ``modules.acervo_library`` so the application can
do it too: the operator now imports the blocks from inside the program and the
export is filed under the video's id, instead of producing a file by hand and
pointing a settings field at it. This script stays for scripted use and for
producing an export outside the app.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.acervo_library import convert, read_tool_result  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Converte blocos Campaign Hub em export local do Furia.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--transcript",
        type=Path,
        help="Export de chub_acervo_transcript; traz as regiões que o Acervo marcou como sem conteúdo.",
    )
    args = parser.parse_args()
    payload = read_tool_result(json.loads(args.input.expanduser().read_text(encoding="utf-8")))
    transcript = json.loads(args.transcript.expanduser().read_text(encoding="utf-8")) if args.transcript else None
    export = convert(payload, transcript)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(export, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "blocks": len(export["records"]["blocks"]),
        "highlights": len(export["records"]["highlights"]),
        "sentences": len(export["records"]["sentences"]),
        "output": str(args.output),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
