#!/usr/bin/env python3
"""Install or merge an authorized Campaign Hub JSON export locally."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running the script directly from the repository checkout.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.campaign_hub_memory import import_snapshot_file, memory_status  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Atualiza a memória local offline do Campaign Hub a partir de um export autorizado."
    )
    parser.add_argument("--input", required=True, type=Path, help="Arquivo JSON exportado de forma autorizada")
    parser.add_argument("--output", type=Path, default=None, help="Caminho final do profile.json")
    parser.add_argument("--replace", action="store_true", help="Substitui a memória em vez de mesclar registros")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Imprime apenas JSON de status")
    args = parser.parse_args()

    try:
        status = import_snapshot_file(
            args.input,
            destination=args.output,
            merge=not args.replace,
        )
    except (OSError, ValueError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        print(f"Memória local pronta: {status.get('path')}")
        print(f"Versão: {status.get('version') or 'não informada'}")
        print(f"Registros: {json.dumps(status.get('record_counts', {}), ensure_ascii=False, sort_keys=True)}")
        print(f"Mesclagem: {'sim' if status.get('merge') else 'não'}")
        print(f"Atualizado em: {status.get('last_sync_at') or status.get('modified_at') or 'não informado'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
