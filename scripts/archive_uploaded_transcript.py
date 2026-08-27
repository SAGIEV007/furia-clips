"""Arquivar um transcript local fornecido pelo operador.

Uso:
    python scripts/archive_uploaded_transcript.py /caminho/transcript.txt

O arquivo permanece fora do repositório e é lido somente durante a execução.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.transcript_archive import archive_transcription  # noqa: E402
from modules.transcript_parser import parse_transcript_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="arquivo de transcript local")
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    parsed = parse_transcript_file(str(source))
    result = archive_transcription(
        parsed,
        source_video=source.stem,
        source="user_uploaded_transcript",
        source_artifact=str(source),
        archive_name=source.stem,
    )
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
