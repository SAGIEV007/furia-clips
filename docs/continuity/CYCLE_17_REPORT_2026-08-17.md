# Ciclo 17 — Confiabilidade declarada da medição do benchmark

**Data:** 17 de agosto de 2026
**Projeto:** Furia Clips
**Branch:** `manus/rebuild-opus-parity`
**Baseline:** release 2.6, commit `c530cd1`
**Release:** 2.7

## Objetivo e hipótese

> Se o benchmark editorial declarar explicitamente quando o mapeamento temporal não
> pôde ser aplicado, então um `0/3` produzido por falta da fonte local deixa de ser
> confundido com um `0/3` de seleção, e a próxima medição de recall passa a ser
> confiável.

A rodada não alterou seleção, ranking, expansão de seeds, gates editoriais,
diarização, reframe, headlines nem renderização.

## Como o problema foi encontrado

A auditoria começou pelo procedimento previsto em `NEXT_CYCLE.md`: instalar um
snapshot autorizado e reprocessar o b354. Sem acesso ao conector CHUB durante a
rodada, foi montado um snapshot local a partir dos dados já verificados em
`CYCLE_12_REPORT_2026-08-17.md` e o benchmark foi executado.

O comando devolveu:

```
coverage_recall      : 0.0
mean_best_iou        : 0.0
mean_boundary_error_s: 5904.771
classifications      : {campaign_hub_better: 3}
```

O `recall 0/3` **coincidia** com o baseline. A coincidência era enganosa. Os
`5904.771s` de erro de fronteira não são erro editorial: são o deslocamento do
bloco b354 dentro da live (`6142.56s`). As referências permaneceram em segundos
absolutos (`6289.36`) enquanto os sete candidatos estavam na timeline local
(`146.80`). Os intervalos comparados não descrevem o mesmo eixo de tempo.

A causa está em `map_interval_to_local()`: a conversão só ocorre quando
`source_duration` confirma o vínculo com o MP4 do bloco. Sem `--source` legível
pelo `ffprobe`, `source_duration` é `None`, o mapeamento cai em
`timeline_mapping: "source_timeline"` e nada no relatório sinaliza isso.

Esse é exatamente o modo de falha que o contrato do projeto proíbe: aceitar um
número como resultado sem que ele signifique o que aparenta.

## Implementações

| Arquivo | Alteração |
| --- | --- |
| `modules/editorial_benchmark.py` | Nova função `assess_measurement()` e bloco `measurement` no payload; `source.mapping_applied`; `metrics.measurement_reliable` e `metrics.measurement_status`. |
| `scripts/run_editorial_benchmark.py` | `expanduser()` em `--memory` e `--source`; `measurement` no stdout; avisos em `stderr` quando a medição não é comparável. |
| `app.py` | `POST /api/editorial/benchmark` devolve `measurement` e substitui a mensagem de sucesso por alerta explícito quando a medição não é confiável. |
| `tests/test_editorial_benchmark.py` | Quatro regressões novas. |

`assess_measurement()` decide por três vias, e não por uma regra binária:

1. **MP4 do bloco** — duração próxima do span do bloco → mapeamento aplicado →
   comparável.
2. **Fonte longa completa** — duração alcança o fim do bloco na live → candidatos e
   referências compartilham o eixo absoluto → comparável sem mapeamento.
3. **Qualquer outro caso** com bloco que não começa em zero → coordenadas
   incoerentes → **não comparável**, com aviso.

Um bloco que começa no início da fonte (`reference_start ≈ 0`) não precisa de
tradução e permanece comparável.

`measurement_reliable` e `measurement_status` foram repetidos dentro de `metrics`
porque `list_benchmarks()` expõe apenas `metrics`. Um número de recall não pode
circular separado da confiabilidade dele.

## Validação

| Verificação | Resultado |
| --- | --- |
| Regressões focadas (`tests/test_editorial_benchmark.py`) | 7 aprovados |
| Suíte completa | **330 aprovados, 7 falhas ambientais** |
| Suíte no código original (`git stash`) | **326 aprovados, as mesmas 7 falhas** |
| `compileall` | aprovado |
| `node --check static/js/app.js` | aprovado |
| `git diff --check` | aprovado |
| Verificação de segredos e mídia | nenhum token, cookie, chave, vídeo ou banco versionado |

As 7 falhas são `ffmpeg`/`ffprobe` ausentes no container e o asset externo
BlazeFace. Foram reproduzidas idênticas no código sem as mudanças desta rodada,
o que descarta relação com a alteração. A diferença de `+4` aprovados corresponde
exatamente às regressões adicionadas.

Execução real após a mudança, no mesmo comando que antes silenciava:

```
reliable        : False
status          : unmapped_timeline
coverage_recall : 0.0
boundary_error  : 5904.771

AVISO: A duração da fonte local não foi informada, então os destaques permaneceram
em segundos absolutos da live e foram comparados com candidatos da timeline local.
As métricas desta execução não são comparáveis ao baseline.
AVISO: Informe o MP4 do bloco baixado (ou a fonte longa completa) para que o
mapeamento temporal seja aplicado antes de medir recall.
AVISO: estas métricas NÃO podem ser comparadas com o baseline b354.
```

## Descobertas do ambiente registradas para a próxima rodada

1. **`normalize_snapshot()` rejeita o payload inteiro sem `accounts`.** Um export
   contendo apenas blocos e highlights do Acervo é descartado por completo:
   `read_memory()` devolve `None` e o benchmark falha com "Bloco não encontrado",
   mesmo com os dados corretos no arquivo. A conta pode ter listas vazias, mas a
   chave precisa existir com pelo menos uma de `@renansantosmbl`,
   `@renansantosreserva` ou `@partidomissao`. Isso não foi alterado nesta rodada —
   é comportamento intencional de compatibilidade — mas falha sem diagnóstico e
   merece avaliação futura.
2. **`Path.home()` resolveu para `/root`** no container auditado, não para
   `/home/user`. Os artefatos foram parar em `/root/FuriaClipsData/benchmarks/`.
3. **`workspace/exports/` estava vazio** e o MP4 do b354
   (`549.449s`, 1920×1080, H.264/AAC) não estava disponível.
4. **O conector CHUB ficou indisponível durante a rodada.** As 18 ferramentas
   chegaram a ser expostas uma vez (`chub_acervo_blocks`, `chub_acervo_transcript`,
   `chub_acervo_pauta`, `chub_acervo_stats`, `chub_transcript`, `chub_search`,
   `chub_sql`, `chub_youtube_longform_search`, `chub_mission_book_search`,
   `chub_city_dossiers`, `chub_cohort_stats`, `chub_tag_performance`,
   `chub_top_posts`, `chub_video_metrics`, `chub_audience`, `chub_x_interactions`,
   `chub_accounts`, `chub_ads`) e depois caíram, sem retornar.

## Classificação das conclusões

| Classificação | Conclusão |
| --- | --- |
| Confirmado | Um `0/3` sem mapeamento temporal era indistinguível de um `0/3` de seleção no relatório anterior. |
| Confirmado | As três vias de decisão de `assess_measurement()` cobrem MP4 de bloco, fonte longa completa e bloco iniciando em zero. |
| Reproduzido | As 7 falhas da suíte são ambientais e existem sem esta mudança. |
| Corrigido | `--memory ~/...` deixou de falhar silenciosamente com "Bloco não encontrado". |
| Corrigido | O relatório, o script e a API passaram a declarar quando a medição não é comparável ao baseline. |
| Não verificado | O recall real do b354 com mapeamento correto; o MP4 local do bloco não estava presente. |
| Bloqueado | Snapshot autorizado real do Campaign Hub; o conector ficou indisponível durante a rodada. |

## Próxima hipótese única

> **Se o MP4 local do bloco b354 e um snapshot autorizado do Campaign Hub forem
> instalados e o benchmark for reprocessado com `measurement.reliable=true`, então
> o recall temporal medido será o recall real da seleção — e só então a ponte da
> release 2.6 poderá ser avaliada quanto a ganho sobre o baseline `0/3`.**

A rodada seguinte não deve alterar seleção nem ranking antes de obter uma medição
declarada confiável. Reframe, headlines, editor pós-renderização, publicação
automática e download remoto por range continuam fora de escopo.

## Referências

[1]: `CHUB_INTEGRATION_CONTRACT.md` — contrato funcional da integração.
[2]: `CYCLE_12_REPORT_2026-08-17.md` — origem do baseline b354 e dos três destaques.
[3]: `CYCLE_16_REPORT_2026-08-17.md` — primeira ponte funcional da release 2.6.
[4]: `NEXT_CYCLE.md` — procedimento da hipótese em andamento.
