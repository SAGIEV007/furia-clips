# Relatório de testes — Fúria Clips

> Este documento contém o relatório inicial de testes (histórico) e o status atual da suíte.

## Status atual (2026-08-31 02:46)

A suíte atual está estabilizada com:

- **873 testes aprovados**
- **3 testes ignorados**
- **0 erros**
- **Tempo de execução**: ~37.5s

Ferramenta: `pytest` via `python -m pytest`.
Profiling de imports: `scripts/measure_imports.py`.

### Métricas de importação (02:46)

- **Import stack total**: 528.3 ms
- `app`: 352.6 ms
- `modules.clip_selector`: 135.2 ms
- `modules.video_cutter`: 12.1 ms
- `modules.headline_studio`: 8.2 ms
- `modules.editorial_ranker`: 7.0 ms
- `modules.job_manager`: 3.0 ms
- `modules.editorial_context`: 1.2 ms
- `modules.native_dialogs`: 1.1 ms
- `modules.transcript_parser`: 1.0 ms
- `modules.face_tracker`: 1.0 ms
- `modules.persistent_data`: 1.0 ms
- `modules.batch_queue`: 1.0 ms
- `modules.repository_sync`: 1.0 ms
- `modules.security`: 1.0 ms
- `modules.transcriber`: 1.0 ms
- `modules.performance_metrics`: 1.0 ms
- `modules.campaign_hub`: 0.0 ms
- `modules.editorial_search`: 0.0 ms
- `modules.source_ingest`: 0.0 ms
- `modules.youtube_importer`: 0.0 ms
- `modules.render_presets`: 0.0 ms
- `modules.clip_adjustments`: 0.0 ms
- `modules.editorial_block`: 0.0 ms
- `modules.transcript_archive`: 0.0 ms
- `modules.editorial_search`: 0.0 ms

---
