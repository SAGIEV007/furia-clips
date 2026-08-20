# Relatório do ciclo 31 — diagnóstico do benchmark e filtro Renan-first

**Data:** 2026-08-20  
**Branch:** `claude/repo-access-commits-imgjmk`  
**Hipótese:** propostas Chub sem evidência positiva de fala do Renan estavam ocupando o pool primário Renan-first e reduzindo o recall.  
**Resultado:** confirmada; melhoria funcional candidata à release `6.15`.

## Descoberta do ciclo

O benchmark anterior parecia contraditório porque o scorer exploratório lia sempre o arquivo fixo `benchmark_rich_result.json`, que era um resultado histórico e podia não corresponder ao JSON recém-gerado. Isso fazia uma execução nova parecer reproduzir ou não reproduzir resultados antigos sem que o operador percebesse qual arquivo estava sendo pontuado.

Foi criado `scripts/score_chub_recall.py`, que exige explicitamente `--benchmark` e `--blocks`. A nova regressão garante que o scorer usa o resultado fornecido e aceita o envelope de conteúdo exportado pelo MCP. A instrumentação de `ClipSelector` também passou a registrar contagens por etapa, origem, evidência Chub, identidade, contexto, payoff e revisão.

## Evidência antes da mudança funcional

Na live `3XJfcqn56Rw`, com 5.905 segundos, 1.951 frases, 27 blocos e 66 highlights, o caminho Renan-first com Chub colocava 30 propostas guiadas no pool primário. Depois do filtro de conteúdo e das etapas de deduplicação, 12 ainda chegavam ao resultado final. Dessas propostas, 24 foram materializadas sem evidência positiva de `renanSpeaking=true` e não deveriam ter competido como candidatos Renan-first.

O resultado versionado antes da mudança era:

| Condição | IoU 0,10 | IoU 0,25 | Propostas guiadas finais |
| --- | ---: | ---: | ---: |
| Genérico sem Chub | 5/66 — 7,58% | 0/66 | 0 |
| Genérico com Chub | 18/66 — 27,27% | 6/66 — 9,09% | 20 |
| Renan-first sem Chub | 7/66 — 10,61% | 1/66 — 1,52% | 0 |
| Renan-first com Chub | 5/66 — 7,58% | 1/66 — 1,52% | 12 |

## Implementação

No modo Renan-first, o seletor agora preserva no pool primário somente propostas cujo dossiê Chub contenha `renan_speaking is True`. Propostas `false` ou desconhecidas não são tratadas como cortes do Renan. O número filtrado fica exposto em `campaign_hub_guided_filtered_by_speaker`, e as etapas registram quantas propostas guiadas sobreviveram.

A proposta materializada também passou a preservar `renan_speaking` e `speaker_gate` dentro do dossiê `campaign_hub`. Antes, o seed tinha essa informação, mas ela se perdia na construção da proposta e impedia qualquer filtro posterior de distinguir Renan de terceiro ou locutor desconhecido.

A regra não altera o modo genérico. Ela também não transforma `renanSpeaking=true` em aprovação automática: contexto, payoff, risco, proveniência, timing e revisão continuam valendo.

## Resultado depois da mudança

| Condição | IoU 0,10 | IoU 0,25 | Propostas guiadas finais | Observação |
| --- | ---: | ---: | ---: | --- |
| Genérico sem Chub | 5/66 — 7,58% | 0/66 | 0 | Inalterado |
| Genérico com Chub | 18/66 — 27,27% | 6/66 — 9,09% | 20 | Inalterado |
| Renan-first sem Chub | 7/66 — 10,61% | 1/66 — 1,52% | 0 | Baseline local |
| Renan-first com Chub | 7/66 — 10,61% | 1/66 — 1,52% | 5 | Recupera os 2 highlights perdidos e deixa de ficar abaixo do caminho sem Chub |

O ganho principal é de **estabilidade e precisão de escopo**: o Chub deixa de piorar o Renan-first. O recall volta de `5/66` para `7/66`, igualando o caminho local, enquanto 24 propostas sem evidência positiva são retiradas da competição primária. O genérico permanece exatamente igual.

A identidade disponível permaneceu em `3/30`, pois o filtro não inventa diarização; ele apenas impede que locutores não confirmados sejam tratados como candidatos guiados do Renan. A melhoria deve ser considerada uma proteção de precisão, não uma prova de superioridade geral sobre o modo local.

## Validação

Foram aprovados **77 testes focados** e **546 testes na suíte completa, com 4 ignorados** após o asset BlazeFace ser provisionado temporariamente, conferido e removido. Também passaram `compileall`, `node --check static/js/app.js` e `git diff --check`.

Nenhum vídeo, snapshot, transcrição, banco, cookie, token ou chave foi adicionado ao Git. A versão `6.15` foi publicada na branch isolada pelo commit [`07c51b0`](https://github.com/SAGIEV007/furia-clips/commit/07c51b0).

## Próximo ciclo sugerido

Separar formalmente uma **fila de descoberta Chub** da **fila de candidatos publicáveis**. A primeira poderá preservar highlights de locutor incerto para revisão e auditoria; a segunda deverá conter apenas janelas que passam os gates de contexto, payoff e identidade necessários ao foco editorial escolhido. Isso permitirá usar toda a memória do Chub sem contaminar o resultado principal.
