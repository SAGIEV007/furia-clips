"""Medir a normalização de um transcript local.

Uso:
    python scripts/measure_transcript_parser.py /caminho/transcript.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.transcript_parser import parse_transcript_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="arquivo de transcript local")
    args = parser.parse_args()
    parsed = parse_transcript_file(str(args.source.expanduser().resolve()))
    print({
        "segment_count": parsed["segment_count"],
        "first": parsed["segments"][:3],
        "last": parsed["segments"][-3:],
        "html_entities_left": sum("&gt;" in segment["text"] for segment in parsed["segments"]),
        "arrow_tokens_left": sum(">>" in segment["text"] for segment in parsed["segments"]),
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
