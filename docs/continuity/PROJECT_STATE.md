# PROJECT_STATE — Furia Clips

> Este é o estado vivo do projeto. Atualize-o ao final de cada rodada verificável. O histórico detalhado permanece nos relatórios de ciclo; não misture instruções antigas, hashes obsoletos ou alterações locais já encerradas com o estado corrente.

## Estado corrente

| Campo | Valor |
| --- | --- |
| Projeto | Furia Clips |
| Repositório | `SAGIEV007/furia-clips` |
| Versão pública atual | `2.8` |
| Última release funcional anterior | `2.7` |
| Natureza da release atual | Alinhamento temporal das seeds do Campaign Hub com a mídia local |
| Fonte da versão | [`VERSION`](../../VERSION) |
| Branch de trabalho | `claude/repo-access-commits-imgjmk` |
| Última publicação conhecida antes desta rodada | `a0452d3` — `fix: declarar confiabilidade da medição no benchmark editorial (2.7)` |
| Commit funcional 2.6 | `fec34fe` — `feat: primeira ponte funcional Campaign Hub para propostas (2.6)` |
| Commit funcional 2.7 | `a0452d3` — `fix: declarar confiabilidade da medição no benchmark editorial (2.7)` |
| Commit funcional 2.8 | `fdf5e6b` — `fix: alinhar seeds do Campaign Hub com a mídia local em processamento (2.8)` |
| Última atualização | 2026-08-17 |
| Baseline editorial | b354 com 7 candidatos, recall `0/3`, IoU médio `0.0` — **ainda não remedido com mídia local real** |
| Suíte no checkout | 336 aprovados, 7 falhas ambientais (`ffmpeg`/`ffprobe` ausentes e asset BlazeFace) |
| Objetivo | Gerar cortes Renan Santos/MBL concisos, autossuficientes, contextualizados e editorialmente úteis |

A branch de trabalho deve ser confirmada no checkout real. O GitHub é a fonte da revisão técnica; este arquivo não pode manter um hash diferente do `HEAD` final publicado. Antes de alterar qualquer arquivo, preserve mudanças locais e confirme `git status`.

## Norte imediato

A release 2.2 tornou mensurável o caso b354: sete candidatos locais cobriram `0/3` highlights QA-gated do Campaign Hub, com IoU médio `0.0`, embora o mapeamento da timeline e a exportação individual tenham funcionado. A release 2.6 implementa a primeira ponte funcional que converte contexto autorizado em seeds e propostas guiadas.

A ponte carrega o snapshot uma vez por job, preserva proveniência e riscos, expande a seed dentro da transcrição local e aplica gates antes do ranking. Ela não transforma o Campaign Hub em aprovador automático: propostas guiadas continuam separadas de cortes aprovados e podem exigir revisão humana. A hipótese seguinte está em [`NEXT_CYCLE.md`](NEXT_CYCLE.md): instalar snapshot autorizado do b354 e medir recall real em mídia local, sem ampliar escopo para reframe, headlines, editor estilo CapCut, tradução, avatars, voz, música, branding, publicação automática, múltiplas câmeras ou download remoto por range.

O caso b354 deve preservar `renanSpeaking=false` quando Kim ou outro terceiro fala. O fato de um bloco ser sobre Renan não autoriza atribuir a fala a Renan. Propostas guiadas devem permanecer separadas de cortes aprovados e não podem apagar candidatos de terceiros.

## Release atual — 2.8

A 2.8 corrigiu a causa do recall travado: as seeds do Campaign Hub nasciam no eixo de
tempo errado. `_map_interval()` decidia o mapeamento pela duração declarada em
`records.sources[].duration_s` — a live inteira — e não pela duração do arquivo em
processamento. No b354 a live tem `11230s` (valor conferido no Acervo; a documentação
anterior registrava `7241s`) e o bloco tem `549.44s`: a condição nunca fechava.

Reproduzido em execução real: as três seeds ficavam em `6289.36` / `6365.80` /
`6631.04` enquanto a transcrição do MP4 do bloco ia de `0` a `497s`. Nenhuma seed caía
dentro da transcrição.

A reprodução revelou uma segunda falha não prevista. Em vez de zero propostas, o
seletor devolvia **três propostas idênticas** em `488.48–497.00`, porque
`_build_campaign_hub_proposal()` ancorava qualquer seed órfã na frase mais próxima sem
limite de distância — e a frase mais próxima de uma seed em `6289s` é sempre a última
da transcrição. Três destaques distintos viravam a mesma janela errada carregando
proveniência do Campaign Hub. Isso é proposta errada com procedência falsa, não apenas
recall perdido.

Com a duração medida da mídia informada pelo job, os três destaques mapeiam para
`146.80` / `223.24` / `488.48` e geram três propostas distintas, cada uma abrindo antes
do destaque para recuperar a pergunta ou o antecedente, todas `review_required=true`
porque o bloco tem `renanSpeaking=false`.

O recall real continua **não verificado**: a transcrição das regressões é sintética e
exercita o alinhamento, não a seleção. O MP4 local do b354 não está no ambiente.
Nenhum ganho sobre o baseline `0/3` é reivindicado. Relatório em
[`CYCLE_18_REPORT_2026-08-17.md`](CYCLE_18_REPORT_2026-08-17.md).

## Release anterior — 2.7

A release 2.7 corrigiu um modo de falha da **medição**, não da seleção. O benchmark
podia devolver `recall 0/3` por dois motivos completamente diferentes — a seleção
realmente errou os destaques, ou as referências nunca foram mapeadas para a timeline
local — e o relatório não distinguia os dois casos.

O caso foi reproduzido em execução real: sem `--source` legível pelo `ffprobe`,
`map_interval_to_local()` mantém os destaques em segundos absolutos (`6289.36`)
enquanto os candidatos estão na timeline local (`146.80`). O relatório então
acusava `mean_boundary_error_s: 5904.771` — o deslocamento do bloco dentro da live,
não erro editorial — e mesmo assim exibia `coverage_recall: 0.0` como se fosse
comparável ao baseline.

`assess_measurement()` em `modules/editorial_benchmark.py` passou a declarar
`measurement.reliable`, `status`, `mapping_required`, `mapping_applied`,
`source_is_full_length` e avisos em português. A decisão tem três vias: MP4 do
bloco (mapeia), fonte longa completa (coerente sem mapear) e qualquer outro caso
com bloco fora do início (incoerente, avisa). `metrics` repete
`measurement_reliable` porque `list_benchmarks()` expõe apenas `metrics`.

`scripts/run_editorial_benchmark.py` passou a expandir `~` em `--memory` e
`--source` — antes falhava silenciosamente com "Bloco não encontrado" — e emite os
avisos em `stderr`. `app.py` devolve `measurement` na rota de benchmark.

Suíte: **330 aprovados, 7 falhas ambientais** (`ffmpeg`/`ffprobe` ausentes e asset
externo BlazeFace). As mesmas 7 falhas foram reproduzidas com `git stash` no código
original (`326 aprovados`), confirmando que não têm relação com a mudança.
`compileall`, `node --check` e `git diff --check` passaram.

O recall real do b354 continua **não verificado**: o MP4 local do bloco não estava
presente no ambiente e o conector CHUB ficou indisponível durante a rodada. O
baseline permanece `0/3`, sem reivindicação de ganho. Seleção, ranking, expansão de
seeds e renderização não foram alterados. Relatório em
[`CYCLE_17_REPORT_2026-08-17.md`](CYCLE_17_REPORT_2026-08-17.md).

## Histórico funcional anterior — 2.2

A release 2.2 implementou `modules/editorial_benchmark.py`, `scripts/run_editorial_benchmark.py`, persistência local de comparações, exportação individual de highlights e ações correspondentes no painel de Blocos. O benchmark real usou sete candidatos persistidos pelo Furia e três destaques QA-gated do snapshot local autorizado.

Os destaques foram mapeados para `146.80–150.80s`, `223.24–228.40s` e `488.48–495.20s` no MP4 local de `549.449s`. O recall temporal foi `0/3`; o IoU médio foi `0.0`; os três casos foram classificados como `Campaign Hub melhor` na métrica temporal. O resultado não aumenta o peso do Campaign Hub no ranking e não consulta MCP durante o corte. Isso é uma limitação consciente da release 2.2, não o norte final: a próxima integração deve usar snapshot Chub antes do score para gerar propostas contextualizadas, mantendo o job offline-first.

Os três exports individuais foram validados em 1920×1080 H.264/AAC, com durações aproximadas de `4.004s`, `5.172s` e `6.740s`. A suíte da release 2.2 terminou com **327 testes aprovados**. O modelo pequeno de facetracking permanece um asset externo e não deve ser incluído no Git.

## Release atual — 2.6

A release 2.6 adicionou `modules/campaign_hub_guidance.py`, os caminhos `_select_with_campaign_hub_guidance()` e `_build_campaign_hub_proposal()` em `modules/clip_selector.py`, o diagnóstico de seeds em `modules/editorial_context.py` e a carga única do snapshot em `app.py`. As propostas carregam `source=campaign_hub_guided`, `candidate_origin=campaign_hub_guided`, proveniência completa e gates de contexto, payoff, locutor, timing, risco, técnico, proveniência e avisos.

A suíte terminou com **333 testes aprovados**, incluindo seis regressões novas. Também passaram `compileall`, `node --check static/js/app.js`, `git diff --check` e a verificação SHA-256 do BlazeFace temporário. O payload real do Chub para `gVrW6a5e6Tc` produziu duas seeds e duas propostas: `426.4–451.52s` e `511.0–566.12s`, ambas com `context_complete=true`. Como eram `third_party` e tinham `start_continuation`, ambas ficaram com `review_required=true`.

O recall do b354 continua **não verificado nesta release**, porque o snapshot autorizado correspondente não estava instalado localmente durante o job normal. O baseline permanece `0/3`, sem reivindicação de ganho. Sem snapshot em `~/FuriaClipsData/campaign_hub/profile.json`, o caminho legado permanece disponível.

## Release documental — 2.3

A revisão 2.3 criou [`PROMPT_MESTRE_IA.md`](PROMPT_MESTRE_IA.md), uma versão copiável que consolida o `START_HERE`, os prompts históricos, as decisões permanentes, o norte do benchmark 2.2, as regras do Campaign Hub, o ciclo obrigatório de engenharia, o contrato de documentação, segurança e formato de entrega.

A revisão 2.4 criou [`CHUB_INTEGRATION_CONTRACT.md`](CHUB_INTEGRATION_CONTRACT.md) e reorientou o prompt mestre e o `START_HERE`: a prioridade agora é fazer o contexto do Campaign Hub alimentar seeds, alinhamento, expansão, gates, propostas e renderização de cortes; blocos permanecem como superfície de diagnóstico e revisão.

A revisão 2.5 criou [`PROMPT_EXECUCAO_CHUB_CORTES.md`](PROMPT_EXECUCAO_CHUB_CORTES.md), um roteiro copiável para implementar a ponte funcional Chub→cortes sem misturar escopo. A release 2.6 executou a primeira implementação funcional desse roteiro; o benchmark b354 permanece em `0/3` até ser reprocessado com snapshot local.

Também permanece vigente [`COMMIT_MESSAGE_TEMPLATE.md`](COMMIT_MESSAGE_TEMPLATE.md), que torna obrigatório registrar hipótese, baseline, implementação, escopo excluído, validação, resultado, limitações e continuidade no corpo dos commits relevantes.

`README.md`, `AGENTS.md` e `START_HERE.md` agora encaminham qualquer IA que receba apenas o link do GitHub para o prompt mestre, o estado vivo, a próxima hipótese, as decisões e o modelo de commit. O `PROJECT_STATE.md` foi normalizado para manter uma única seção corrente e corrigir o hash da release 2.2 para `074a129`.

## Estado funcional conhecido

O projeto é uma aplicação local Flask com Socket.IO, SQLite, FFmpeg/FFprobe, faster-whisper, MediaPipe/BlazeFace, yt-dlp e fallbacks locais/online opcionais. O princípio de timeline canônica mantém intervalos derivados vinculados ao vídeo original.

O pipeline conhecido contém ingestão e validação de fonte, download público, transcrição timestampada, análise de contexto, geração de candidatos, ranking editorial explicável, revisão humana, renderização por preset, legendas, validação audiovisual e persistência de jobs/feedback. A release 2.1 adicionou memória local offline-first do Campaign Hub, blocos editoriais e exportação seletiva; a release 2.2 adicionou benchmark persistente e exportação individual de highlights; a release 2.6 adicionou a primeira ponte para propostas guiadas.

O Furia consegue receber MP4 local, transcrever, selecionar e renderizar arquivos tecnicamente válidos, mas ainda não oferece uma experiência diária equivalente ao Garimpo + Campaign Hub. A seleção ainda precisa melhorar em contexto, cobertura, identidade do locutor, completude Q&A, autossuficiência e estabilidade entre reprocessamentos.

## Regras permanentes

As decisões duráveis estão em [`DECISIONS.md`](DECISIONS.md). As mais importantes são:

- contexto e payoff vencem slogan, duração curta ou palavra viral;
- gates de contexto, timing, locutor, transcrição, mídia e risco vêm antes do ranking;
- o Campaign Hub é prior fraco e benchmark read-only, nunca aprovador automático;
- uma rodada deve testar uma hipótese principal e comparar antes/depois;
- a transcrição fornecida pelo editor é a timeline canônica;
- `quem fala`, `quem aparece` e `quem é foco editorial` são campos distintos;
- em ambiguidade de enquadramento, preserve `16:9 original` em vez de crop central arbitrário;
- o job normal não chama MCP; snapshots autorizados devem ser locais, sanitizados e versionados;
- contas, plataformas, crossposts, métricas e proveniência permanecem separados;
- vídeos grandes, bancos, tokens, cookies, chaves, transcrições privadas e dados pessoais ficam fora do Git;
- trabalho ocorre em branch, commits são pequenos e merge na principal exige autorização explícita;
- todo commit relevante deve seguir [`COMMIT_MESSAGE_TEMPLATE.md`](COMMIT_MESSAGE_TEMPLATE.md).

## Validação e evidências

A validação da release 2.6 incluiu suíte com **333 testes aprovados**, `compileall`, `node --check static/js/app.js`, `git diff --check` e verificação SHA-256 do BlazeFace temporário. O payload real do Campaign Hub confirmou duas seeds e duas propostas guiadas com `context_complete=true`, mas o benchmark b354 não foi reprocessado porque o snapshot correspondente não estava instalado localmente. Esses resultados não substituem a medição futura de recall em mídia b354.

Em qualquer rodada, classifique conclusões como `confirmado`, `reproduzido`, `corrigido`, `provável`, `não verificado` ou `bloqueado`. O relatório desta rodada está em [`CYCLE_16_REPORT_2026-08-17.md`](CYCLE_16_REPORT_2026-08-17.md).

## Histórico resumido

| Release | Foco | Resultado principal | Relatório |
| --- | --- | --- | --- |
| 2.8 | Alinhamento temporal das seeds | Seeds do b354 passam a cair na timeline local; três propostas falsas idênticas eliminadas | [`CYCLE_18_REPORT_2026-08-17.md`](CYCLE_18_REPORT_2026-08-17.md) |
| 2.7 | Confiabilidade declarada da medição | Benchmark passa a distinguir `0/3` de seleção de `0/3` por timeline não mapeada | [`CYCLE_17_REPORT_2026-08-17.md`](CYCLE_17_REPORT_2026-08-17.md) |
| 2.6 | Primeira ponte Campaign Hub→seeds→propostas | 2 seeds e 2 propostas reproduzidas em payload real; recall b354 ainda não medido | [`CYCLE_16_REPORT_2026-08-17.md`](CYCLE_16_REPORT_2026-08-17.md) |
| 2.5 | Prompt operacional Chub→cortes | Roteiro copiável; sem alteração funcional | [`CYCLE_15_REPORT_2026-08-17.md`](CYCLE_15_REPORT_2026-08-17.md) |
| 2.4 | Contrato Chub→cortes e reorientação do prompt | Norte funcional atualizado; sem alteração de processamento | [`CYCLE_14_REPORT_2026-08-17.md`](CYCLE_14_REPORT_2026-08-17.md) |
| 2.3 | Prompt mestre e contrato de continuidade | Documentação consolidada; sem alteração de processamento | [`CYCLE_13_REPORT_2026-08-17.md`](CYCLE_13_REPORT_2026-08-17.md) |
| 2.2 | Benchmark persistente e highlights individuais | `0/3` highlights cobertos; mapeamento e exports funcionaram | [`CYCLE_12_REPORT_2026-08-17.md`](CYCLE_12_REPORT_2026-08-17.md) |
| 2.1 | Memória local, blocos e exportação seletiva | b354 exportado e validado; 322 testes | [`CYCLE_11_REPORT_2026-08-17.md`](CYCLE_11_REPORT_2026-08-17.md) |
| 2.0 | START_HERE canônico e diagnóstico prático | Contexto operacional formalizado; 306 testes | [`CYCLE_10_REPORT_2026-08-17.md`](CYCLE_10_REPORT_2026-08-17.md) |
| 1.9 | Prompt executor e benchmark como direção | Regras de continuidade e benchmark especificadas | Histórico no `CHANGELOG.md` |

## Leitura obrigatória para a próxima IA

Leia [`AGENTS.md`](../../AGENTS.md), [`README.md`](../../README.md), [`VERSION`](../../VERSION), [`docs/VERSIONING.md`](../VERSIONING.md), [`START_HERE.md`](START_HERE.md), [`PROMPT_MESTRE_IA.md`](PROMPT_MESTRE_IA.md), este arquivo, [`DECISIONS.md`](DECISIONS.md), [`NEXT_CYCLE.md`](NEXT_CYCLE.md), [`COMMIT_MESSAGE_TEMPLATE.md`](COMMIT_MESSAGE_TEMPLATE.md) e o relatório mais recente. Depois confirme `git status`, branch, commit e testes no checkout real antes de propor qualquer alteração.
