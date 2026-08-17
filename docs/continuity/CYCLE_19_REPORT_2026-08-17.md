# Ciclo 19 — Primeiro recall medido em fonte longa inteira

**Data:** 17 de agosto de 2026
**Projeto:** Furia Clips
**Branch:** `claude/repo-access-commits-imgjmk`
**Baseline:** release 2.8, commit `fdf5e6b`
**Release:** 2.9

## Objetivo e hipótese

> Se o Furia for medido contra **todos** os blocos e destaques que o Acervo produziu
> para uma fonte longa inteira, então existirá pela primeira vez um número de recall
> comparável — e ele mostrará onde o orçamento de candidatos está sendo gasto.

## O bloqueio que foi removido

Todas as rodadas anteriores dependiam do MP4 local para medir qualquer coisa. Os
ciclos 16, 17 e 18 terminaram com a mesma limitação: *"o recall real continua não
verificado; o MP4 do bloco não estava disponível"*.

A observação que destravou a rodada é simples: **a seleção do Furia roda sobre a
transcrição, não sobre os pixels.** `ClipSelector.select_clips()` recebe segmentos com
`start`, `end` e `text`. O perfil de energia e as mudanças de cena são opcionais.

Logo, uma transcrição autorizada do Acervo é suficiente para medir a seleção — sem
baixar mídia, sem chamar o MCP durante o job e sem simular nada. O que se mede é a
seleção guiada por transcrição, e o relatório declara isso explicitamente em
`run.energy_profile: false` e `run.scene_changes: false`.

## Caso medido

| Item | Valor |
| --- | --- |
| Vídeo | `3XJfcqn56Rw` — "O ÚLTIMO ANÁLISES RENAIS" |
| Duração | `5905s` (98 minutos), `was_live` |
| Frases | 1951 |
| Blocos QA-gated | 27 |
| Destaques de referência | 66 |
| Regiões marcadas como sem conteúdo | 20 |
| Origem da legenda | `youtube_auto`, `qualityTier: automatic`, `audioVerificationRequired: true` |

É um caso 9× mais rico que o b354 (1 bloco, 3 destaques) e muito mais próximo do
objetivo real do produto: uma fonte de horas, com muitos cortes possíveis.

O bloco pedido pelo usuário — `8412ac67-b018-4e63-a193-4f4cbca14149`, "Brasil seguro,
próspero e entre as cinco nações mais importantes do mundo" — pertence a esse vídeo
(`62.52–168.04`, `renanSpeaking=false`, `riskFlags: ["violencia"]`).

## Medição

`scripts/run_acervo_recall_benchmark.py` roda o seletor real sobre a transcrição
completa e pontua contra os 27 blocos e os 66 destaques.

| Configuração | Destaques | Blocos | IoU médio | Candidatos desperdiçados |
| --- | --- | --- | --- | --- |
| Seleção local (NLP) | `11/66` | `18/27` | `0.1012` | 14 de 40 |
| `+ campaign_hub_guided` | `24/66` | `17/27` | `0.1225` | 10 de 40 |
| `+ filtro de não-conteúdo` | **`27/66`** | **`20/27`** | **`0.1600`** | **0 de 40** |

### A ponte do Campaign Hub funciona — agora medido

O caminho guiado **mais que dobrou** o recall de destaques, de `11/66` para `24/66`.
Esta é a primeira evidência quantitativa de que a ponte criada na release 2.6 melhora
a seleção. Até aqui ela era plausível, nunca medida.

### O recall é binário, e isso muda o diagnóstico

Dos 66 destaques: **24 recuperados inteiros, 42 nunca tocados, zero parcialmente
cobertos.**

Nenhum destaque ficou cortado no meio. Isso descarta a hipótese de que o problema
principal fosse borda de janela — o Furia não está truncando ideias, ele simplesmente
**não olha** para 42 das 66 regiões. O problema é cobertura, não recorte.

### Um quarto do orçamento era gasto em nada

14 dos 40 candidatos da seleção local caíam em trechos que o Acervo já havia rotulado
como sem conteúdo editorial — a maioria com 100% da janela dentro da região. Seis
deles amontoados na mesma zona morta, entre `3022s` e `3667s`.

O Acervo marca essas regiões com motivo explícito, como *"Transcrição ininteligível e
isolada"*. Isso não é ausência de dado: é **evidência rotulada de ausência de
conteúdo**. O Furia tinha esse sinal disponível e nunca o consumia.

## Implementações

| Arquivo | Alteração |
| --- | --- |
| `scripts/run_acervo_recall_benchmark.py` | Novo. Mede recall de destaques, cobertura de blocos, IoU, duração e desperdício contra um vídeo inteiro rotulado, sem exigir mídia. |
| `scripts/convert_chub_blocks_export.py` | Aceita o payload cru além do envelope MCP; novo `--transcript` traz `ignored_regions` para o snapshot. |
| `modules/clip_selector.py` | Novos `_labelled_non_content_regions()` e `_drop_labelled_non_content()`; constante `NON_CONTENT_DROP_RATIO = 0.5`. |
| `tests/test_campaign_hub_guidance.py` | Duas regressões novas. |

O descarte só ocorre quando a **maioria** da janela cai na região rotulada. Tocar a
borda não desqualifica: uma ideia pode começar logo depois de um trecho
ininteligível. Sem snapshot autorizado, o filtro é inerte e o comportamento anterior
é preservado — o app continua offline-first.

## Validação

| Verificação | Resultado |
| --- | --- |
| Suíte completa | **338 aprovados, 7 falhas ambientais** |
| Suíte antes da rodada | 336 aprovados, 7 falhas |
| `compileall` | aprovado |
| `node --check static/js/app.js` | aprovado |
| `git diff --check` | aprovado |
| Segredos, mídia e transcrições | nada versionado; snapshot e relatórios ficam em `FuriaClipsData/` |

## Sinais do Acervo que o Furia ainda não usa

A auditoria do schema encontrou campos disponíveis e hoje ignorados pela integração:

| Campo | O que oferece |
| --- | --- |
| `speakers_note` | Nota textual sobre a incerteza de atribuição de fala. No bloco pedido: *"todas as linhas atribuídas à (fala 1), mas a transcrição não identifica nominalmente quem é esse falante"*. Sinal direto para o gate de locutor. |
| `corpus_verdict` / `corpus_keep` | Veredito de auditoria do corpus (`argumento`, `keep=true`). |
| `pauta_temporality` | `evergreen` versus datado — decide se um corte continua útil depois da semana. |
| `audio_check_ranges` | 1065 trechos de maior risco de erro na legenda automática. |
| `self_contained_reason` | Justificativa textual da autossuficiência. |

Nenhum foi consumido nesta rodada; ficam registrados como matéria-prima da próxima.

## Classificação das conclusões

| Classificação | Conclusão |
| --- | --- |
| Confirmado | A ponte `campaign_hub_guided` melhora o recall: `11/66` → `24/66` na mesma fonte. |
| Confirmado | 14 de 40 candidatos da seleção local caíam em trechos rotulados como sem conteúdo. |
| Confirmado | O recall é binário: 24 inteiros, 42 intocados, zero parciais. O gargalo é cobertura, não borda. |
| Corrigido | Candidatos sobre não-conteúdo rotulado deixaram de consumir orçamento; recall subiu para `27/66` e IoU para `0.16`. |
| Reproduzido | As 7 falhas ambientais da suíte. |
| Não verificado | O comportamento com perfil de energia e mudanças de cena reais, ausentes nesta medição. |
| Não verificado | Se `27/66` se sustenta em outras fontes longas; foi medido em um vídeo. |
| Bloqueado | Renderização e validação FFprobe; `ffmpeg` não existe neste container. |

## Próxima hipótese única

> **Se o orçamento de candidatos deixar de ser um teto fixo e passar a ser governado
> pelos gates de qualidade — permitindo tantos cortes quantos passarem —, então os 42
> destaques hoje intocados entrarão no alcance da seleção sem que a precisão caia,
> porque o desperdício em não-conteúdo já foi eliminado.**

O número `40` é arbitrário: vem de `_selection_coverage_plan()`, que deriva a
quantidade da duração da fonte. Para 27 blocos e 66 destaques em 98 minutos, ele é o
limite ativo. A rodada seguinte deve medir o recall com o teto elevado e verificar se
a precisão se mantém — usando `speakers_note`, `corpus_keep` e `audio_check_ranges`
como gates, e não como pontuação.

Regra do usuário a preservar: **não existe quantidade mínima de cortes.** A meta é que
todo corte entregue passe pelos critérios, e não que um número seja atingido.
