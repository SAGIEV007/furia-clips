# PROJECT_STATE — Furia Clips

> Estado vivo do projeto. Atualizado em 2026-09-04 19:30 BRT.

## Estado corrente

| Campo | Valor |
| --- | --- |
| Projeto | Furia Clips |
| Repositório | `SAGIEV007/furia-clips` |
| Versão | `6.63` |
| Branch de trabalho | `furia-treino-noturno` |
| HEAD local | `0af6a44` |
| Divergência origin | 0 ahead / 0 behind (sincronizada) |
| Suíte | **1215 passed, 13 skipped, 3 xfailed** em ~92s |
| Baseline editorial | Duas fontes medidas na 3.1. `3XJfcqn56Rw` (live 98 min): recall `50/66`, cobertura `25/27`. `j9FRVbb8CAI` (entrevista 31 min): recall `30/34`, cobertura `11/11`. Precisão `1.00`, zero fora de bloco e zero desperdício **nas duas**. |
| Objetivo | Gerar cortes Renan Santos/MBL concisos, autossuficientes, contextualizados e editorialmente úteis |

### Mídia local validada
- `FuriaClipsData/downloads/cnn-renan-santos-snjkrNF-aIU.mp4` (3394s, 16:9)
- `FuriaClipsData/exports/cnn-renan-santos-16x9/` (19 clips, 1920x1080)
- `FuriaClipsData/exports/cnn-renan-santos/` (19 clips)
- `FuriaClipsData/exports/snjkrNF-aIU/` (2 clips)

### Últimas medições reais
- `segment_speech` em `cnn-renan-santos-16x9/clip_01.mp4`: 7 segmentos VAD em 1,07s, cobertura completa do áudio, sem falhas.
- Crop dinâmico (Kalman) em `cnn-renan-santos-16x9/clip_01.mp4`: 30 faces, jitter reduzido **1,72x** (raw 0,0151 → smooth 0,0088). Render bloqueado por bug conhecido do ffmpeg MSYS2; fallback estático por segmento ativo.
- Transcrição e abertura em `flow-news-065`: manual 0/48 (0% abertura no meio), Whisper 2/40 (5%) — melhoria em relação a 25% documentado anteriormente.

### Decisões recentes
- `cbf02bf`: remoção de artefatos de validação do índice e disco.
- `c4f9d76`: fronteira de saída do acervo marcada como xfail (crossings são overshoots pequenos sobre fronteiras de território que alinham com boundaries de sentença; seletor não recebe `blocos_de_referencia` em produção).
- `75f8c11`: quality gate defaults ajustados (`context_complete`/`payoff_complete` usam `True` por padrão) para evitar rejeição silenciosa de clips sem flag explícito.
- `8b556e7`: crop estático por segmento integrado como padrão no `batch_cut` quando `use_face_tracking=True`, com fallback `center_crop`.
- `7f73b83`: gates de fronteira de abertura/fecho expandidos com conectivos reais, detecção de anáfora órfã e tratamento de toco.

### Bloqueios ativos
- ffmpeg MSYS2 no Windows rejeita expressões de crop dinâmico com parênteses/vírgulas (ex.: `between(n,0,1)`). Em estudo: `sendcmd`/`zoompan`/fallback por segmento/build diferente.
- Branch sincronizada com origin (0 ahead / 0 behind).

## Norte imediato

A integração do Campaign Hub continua como memória/seed read-only. O crop dinâmico (Kalman) reduz jitter em vídeo real do Renan (1,33x–1,72x), mas a renderização dinâmica está bloqueada no Windows/MSYS2. O fallback estático por segmento já está no `batch_cut`.

Prioridades:
1. Validar crop estático/dinâmico em vídeo real do Renan e contornar bug ffmpeg MSYS2.
2. Reduzir divergência da branch e sincronizar quando autorizado.
3. Integrar `segment_speech` validado no pipeline de corte automático.

## Histórico

Relatórios de ciclo e notas diárias detalhadas estão em [`01_SESSIONS/Daily/LATEST.md`](01_SESSIONS/Daily/LATEST.md) e [`03_FURIA/Next-Actions.md`](Next-Actions.md). Releases antigas (6.22–6.26) estão em relatórios específicos; não competem com o estado atual.
