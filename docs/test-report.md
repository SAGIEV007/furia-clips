# Relatório de testes — Fúria Clips

> Este documento contém o relatório inicial de testes (histórico) e o status atual da suíte.

## Status atual (2026-08-30 23:48)

A suíte atual está estabilizada com:

- **866 testes aprovados**
- **3 testes ignorados**
- **0 erros**
- **Tempo de execução**: ~37s

Ferramenta: `pytest` via `python -m pytest`.
Profiling de imports: `scripts/measure_imports.py`.

### Métricas de importação (23:48)

- **Import stack total**: 614.6 ms
- `app`: 427.3 ms
- `modules.clip_selector`: 137.5 ms
- `modules.video_cutter`: 15.4 ms
- `modules.headline_studio`: 10.2 ms
- `modules.editorial_ranker`: 8.1 ms
- `modules.job_manager`: 3.0 ms
- `modules.native_dialogs`: 2.0 ms
- `modules.render_presets`: 1.1 ms
- `modules.source_ingest`: 1.0 ms
- `modules.batch_queue`: 1.0 ms
- `modules.security`: 1.0 ms
- `modules.editorial_block`: 1.1 ms
- `modules.editorial_search`: 1.0 ms
- `modules.transcriber`: 1.1 ms
- `modules.youtube_importer`: 1.1 ms
- `modules.repository_sync`: 1.1 ms
- Outros módulos: <1 ms cada

---
