#!/usr/bin/env python3
"""Run a local editorial benchmark against Campaign Hub highlights.

Example:
  python scripts/run_editorial_benchmark.py \
    --block-id b3545938-e3a5-4287-82b1-5f7dcdc218c3 \
    --source workspace/exports/bloco-b3545938-e3a5-4287-82b1-5f7dcdc218c3-0-549_77e7ec2d6a20.mp4 \
    --candidates /path/to/candidates.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.editorial_benchmark import compare_candidates, save_benchmark
from modules.editorial_block_memory import get_block


def probe_duration(path: Path) -> float | None:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return float(result.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def load_candidates(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("candidates"), list):
        payload = payload["candidates"]
    if not isinstance(payload, list):
        raise ValueError("O arquivo de candidatos precisa conter uma lista ou {\"candidates\": [...]}.")
    return [item for item in payload if isinstance(item, dict)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa benchmark editorial local contra destaques do Campaign Hub.")
    parser.add_argument("--block-id", required=True)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--memory", type=Path, default=None)
    parser.add_argument("--version", default="b354-v1")
    args = parser.parse_args()

    memory_path = args.memory.expanduser() if args.memory else None
    block = get_block(args.block_id, str(memory_path) if memory_path else None)
    if not block:
        raise SystemExit("Bloco não encontrado na memória local.")
    source_path = args.source.expanduser() if args.source else None
    source_duration = probe_duration(source_path) if source_path else None
    candidates = load_candidates(args.candidates)
    payload = compare_candidates(
        block,
        candidates,
        source_duration=source_duration,
        source_name=str(source_path or ""),
        benchmark_version=args.version,
    )
    target = save_benchmark(payload)
    print(json.dumps({
        "benchmark_id": payload["benchmark_id"],
        "file": str(target),
        "candidate_count": payload["candidate_count"],
        "measurement": payload["measurement"],
        "metrics": payload["metrics"],
        "references": payload["references"],
    }, ensure_ascii=False, indent=2))
    if not payload["measurement"]["reliable"]:
        for warning in payload["measurement"]["warnings"]:
            print(f"AVISO: {warning}", file=sys.stderr)
        print(
            "AVISO: estas métricas NÃO podem ser comparadas com o baseline b354.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
