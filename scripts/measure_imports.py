#!/usr/bin/env python3
"""Quick import-time profiler for Fúria modules."""
import time
import sys
import os
import importlib

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

TARGETS = [
    "modules.clip_selector",
    "modules.editorial_ranker",
    "modules.campaign_hub",
    "modules.headline_studio",
    "modules.video_cutter",
    "modules.editorial_context",
    "modules.editorial_search",
    "modules.face_tracker",
    "modules.source_ingest",
    "modules.transcriber",
    "modules.youtube_importer",
    "modules.job_manager",
    "modules.batch_queue",
    "modules.render_presets",
    "modules.persistent_data",
    "modules.repository_sync",
    "modules.security",
    "modules.native_dialogs",
    "modules.transcript_parser",
    "modules.clip_adjustments",
    "modules.editorial_block",
    "modules.performance_metrics",
    "modules.transcript_archive",
    "modules.editorial_search",
    "app",
]

def main():
    results = []
    for name in TARGETS:
        for mod in list(sys.modules):
            if mod == name or mod.startswith(name + "."):
                del sys.modules[mod]
        t0 = time.time()
        try:
            importlib.import_module(name)
            delta = time.time() - t0
            results.append((name, delta, None))
        except Exception as e:
            delta = time.time() - t0
            results.append((name, delta, str(e)))
    results.sort(key=lambda x: x[1], reverse=True)
    print(f"{'MODULE':<35} {'TIME':>8}  ERROR")
    print("-" * 70)
    for name, delta, err in results:
        print(f"{name:<35} {delta*1000:>7.1f} ms {err or ''}")
    print("-" * 70)
    total = sum(r[1] for r in results)
    print(f"{'TOTAL':<35} {total*1000:>7.1f} ms")

if __name__ == "__main__":
    main()
