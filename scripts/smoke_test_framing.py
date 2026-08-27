"""Smoke test de framing em uma mídia local fornecida pelo operador.

Uso:
    python scripts/smoke_test_framing.py /caminho/video.mp4 [--output-dir /tmp/framing]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.video_cutter import VideoCutter  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="vídeo local para validar")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/tmp/furia-framing-smoke"),
        help="diretório temporário para os exports de teste",
    )
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    out = args.output_dir.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    cutter = VideoCutter(preset="shorts")
    cut = {"start": 382.5, "end": 387.5, "duration": 5.0, "title": "smoke"}

    vertical_results = cutter.batch_cut(
        str(source), [cut], str(out / "smoke_vertical"), use_face_tracking=True,
        face_positions_map={0: [
            {"time": 382.5, "center_x": 0.70, "confidence": 0.92},
            {"time": 384.5, "center_x": 0.71, "confidence": 0.91},
            {"time": 386.5, "center_x": 0.69, "confidence": 0.90},
        ]},
    )
    original_results = cutter.batch_cut(
        str(source), [cut], str(out / "smoke_original"), original_aspect_indices={0}
    )
    for label, results in [("vertical", vertical_results), ("original", original_results)]:
        if not results:
            raise SystemExit(f"{label}: no result")
        validation = results[0]["validation"]
        print(label, results[0]["framing_mode"], results[0]["preset"], validation["width"], validation["height"], validation["valid"])
        if not validation["valid"]:
            raise SystemExit(validation)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
