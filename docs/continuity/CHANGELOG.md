# Changelog de continuidade

## 6.19 — Cancelamento seguro de jobs e feedback honesto

### Hipótese

Se o cancelamento for tratado de forma segura enquanto o job aguarda na fila e depois que o worker começou, e se a barra superior validar a resposta do servidor, o editor não verá falso sucesso nem ficará esperando por um job que ainda não iniciou.

### Incluído

- `modules/job_manager.py`: claim atômico de jobs `queued`, cancelamento terminal imediato antes do worker e verificação de cancelamento antes do alvo executar.
- `static/js/app.js`: cancelamento da barra superior com resposta validada, proteção contra cliques duplicados, reabilitação em erro, toast e registro no console.
- `tests/test_job_manager.py`: regressão que prova que um alvo enfileirado não é executado após cancelamento.
- `tests/test_frontend_integrity.py`: regressão para resposta HTTP, mensagem de erro e reabilitação do botão.
- `VERSION`: incremento para 6.19.

### Resultado medido

Jobs ainda enfileirados passam diretamente para `cancelled` com `cancelled_before_start`; o worker não executa o alvo. Jobs em execução preservam o caminho cooperativo `cancel_requested`. A barra superior só confirma aceitação depois de uma resposta HTTP válida.

### Validação

Os testes focados terminaram com **28 aprovados**. A suíte completa terminou com **557 aprovados e 4 ignorados** após o asset BlazeFace ser provisionado temporariamente, conferido e removido. Também passaram `node --check`, `py_compile` e `git diff --check`. Relatório: [`CYCLE_35_REPORT_2026-08-21.md`](CYCLE_35_REPORT_2026-08-21.md).

## 6.18 — Barra de execução com etapas, progresso e escopo da fonte

### Hipótese

Uma barra fixa que reúna etapa atual, progresso percentual, sequência do pipeline e faixa da fonte reduziria a ambiguidade durante operações longas e diminuiria a dependência do console para entender o estado do job.

### Incluído

- `templates/index.html`: `runBar` expandida com etapa, progresso acessível, sequência `Fonte → Transcrição → Contexto → Ranking → Cortes`, escopo da fonte e coluna lateral responsiva.
- `static/js/app.js`: inferência de etapa a partir das mensagens já existentes, renderização dos estados `complete`, `active`, `future` e `error`, atualização de `aria-valuenow` e persistência do rótulo de escopo entre execuções.
- `static/css/style.css`: hierarquia visual, badges, barra percentual, estados semânticos, responsividade abaixo de 620px e `prefers-reduced-motion`.
- `tests/test_ux_runbar.py`: regressões estáticas para markup, acessibilidade e estados visuais.
- Relatórios de auditoria e verificação visual do ciclo.

### Resultado medido

A simulação visual mostrou etapa `Transcrição` a 42% e `Ranking` a 78%, com `00:00–05:00` visível no chip de escopo. A etapa concluída, a etapa ativa e as etapas futuras ficaram distinguíveis, e `aria-valuenow` acompanhou o percentual. Nenhuma decisão editorial ou chamada de backend foi modificada.

### Validação

A suíte focada terminou com **37 testes aprovados**. A suíte completa terminou com **555 testes aprovados e 4 ignorados** após o asset BlazeFace ser provisionado temporariamente, conferido e removido. Também passaram `node --check`, `py_compile` e `git diff --check`. O ciclo não iniciou job real; a limitação está registrada em [`CYCLE_34_REPORT_2026-08-21.md`](CYCLE_34_REPORT_2026-08-21.md).

## 6.17 — Processamento parcial de fonte e UX de execução unificada

### Hipótese

Uma live longa deveria poder ser processada por faixa, sem alterar a fonte original. A mesma configuração visual deveria servir ao corte inteligente e ao processo completo, deixando claro ao editor qual timeline está sendo analisada.

### Incluído

- `modules/source_interval.py`: parsing de segundos, `mm:ss` e `hh:mm:ss`, validação, criação de cópia temporária por FFmpeg e rebase determinístico da transcrição.
- `app.py`: suporte a `processing_start` e `processing_end` nas rotas de corte inteligente e processo completo, com limpeza em sucesso, erro e cancelamento.
- `app.py`: resultados carregam `processing_interval`, `source_start` e `source_end`; a fonte original continua sendo usada como referência do projeto e dos diagnósticos.
- `app.py`: deduplicação anterior fica desativada somente em timelines locais de intervalo, evitando colisão com fingerprints da live inteira.
- `static/js/app.js`, `templates/index.html` e `static/css/style.css`: modal compartilhado, card de intervalo, chip de estado, validação amigável, responsividade e confirmação visual de que a fonte original não será alterada.
- A referência visual `manus/rebuild-opus-parity-2` foi usada apenas para padrões de UX; mudanças de ranking, backend e Campaign Hub foram excluídas.
- Regressões de parsing, limites, mídia real, transcrição, endpoints e integração com cobertura.

### Resultado medido

A cópia de intervalo da fixture audiovisual foi criada e medida por `ffprobe`, com a fonte original preservada. A interface local foi verificada visualmente em viewport de notebook. Nenhum job editorial externo foi iniciado nesta rodada; a integração pesada permanece coberta por testes, sintaxe e contratos de API.

### Validação

A suíte terminou com **552 testes aprovados e 4 ignorados** após o asset BlazeFace ser provisionado temporariamente, conferido e removido. Também passaram `node --check`, `py_compile` e `git diff --check`. Relatório: [`CYCLE_33_REPORT_2026-08-20.md`](CYCLE_33_REPORT_2026-08-20.md).

## 6.16 — Fila de descoberta Chub separada da fila publicável

### Hipótese

As propostas descobertas pelo Campaign Hub deveriam permanecer auditáveis mesmo quando não pudessem competir no pool Renan-first. Separar descoberta de publicação permitiria manter cobertura e motivos de exclusão sem confundir uma sugestão incerta com um corte pronto para revisão.

### Incluído

- `modules/clip_selector.py`: nova coleção sanitizada `campaign_hub_discovery_candidates`, com seed, bloco, highlight, intervalo, locutor, gate e motivo de exclusão.
- `modules/clip_selector.py`: `campaign_hub_publishable_candidates` passa a conter somente propostas Chub promovidas ao pool guiado; `final_candidates` representa o conjunto final geral.
- `modules/clip_selector.py`: diagnósticos adicionais para descoberta, promoção, filtragem por locutor e candidatos finais.
- `app.py`: os diagnósticos já são enviados nos eventos `selection_mode` e `cut_complete` e persistidos pelo relatório de seleção.
- `static/js/app.js`: o aviso de volume mostra quantos trechos o Chub encontrou, quantos entraram na fila publicável e quantos ficaram para revisão de locutor.
- Regressões para lista de descoberta, semântica dos campos e preservação dos gates.

### Resultado medido

Na live `3XJfcqn56Rw`, o Renan-first com Chub produziu 30 descobertas, promoveu 6 e deixou 24 em `speaker_gate_review`. O recall permaneceu em `7/66` no IoU 0,10 e `1/66` no IoU 0,25; o genérico com Chub permaneceu em `18/66` e `6/66`. A mudança não altera o ranking; melhora a observabilidade e a auditabilidade.

### Validação

A suíte terminou com 546 testes aprovados e 4 ignorados após o asset BlazeFace temporário ser removido. Relatório: [`CYCLE_32_REPORT_2026-08-20.md`](CYCLE_32_REPORT_2026-08-20.md).


## 6.15 — Filtro de locutor positivo no Renan-first e benchmark auditável

### Hipótese

Propostas guiadas pelo Campaign Hub sem evidência positiva de `renanSpeaking=true` estavam ocupando o pool primário Renan-first e reduzindo o recall. O benchmark também precisava deixar de pontuar um arquivo histórico fixo sem informar ao operador.

### Incluído

- `modules/clip_selector.py`: propostas guiadas preservam `renan_speaking` e `speaker_gate` no dossiê materializado.
- `modules/clip_selector.py`: no modo Renan-first, propostas Chub com locutor `false` ou desconhecido ficam fora do pool primário; a quantidade filtrada aparece em `campaign_hub_guided_filtered_by_speaker`.
- `modules/clip_selector.py`: `candidate_diagnostics.stage_counts` registra volume, origem, evidência Chub, identidade, contexto, payoff e revisão em cada etapa da seleção.
- `scripts/score_chub_recall.py`: scorer versionado exige explicitamente o JSON do benchmark e o arquivo de highlights, eliminando a leitura silenciosa de resultado histórico.
- Regressões para propagação do locutor, filtro Renan-first, diagnóstico por etapas e scorer explícito.

### Resultado medido

Na live `3XJfcqn56Rw`, com 66 highlights, o modo Renan-first com Chub passou de `5/66` para `7/66` em IoU 0,10, igualando o caminho sem Chub. Em IoU 0,25 permaneceu em `1/66`. As propostas guiadas finais caíram de `12` para `5`, com 24 propostas sem evidência positiva filtradas antes do ranking. O modo genérico permaneceu inalterado em `18/66` no IoU 0,10 e `6/66` no IoU 0,25.

A mudança melhora a estabilidade e impede que o Chub prejudique o foco Renan-first; não constitui diarização e não libera renderização automaticamente.

### Validação

Relatório: [`CYCLE_31_REPORT_2026-08-20.md`](CYCLE_31_REPORT_2026-08-20.md).


## Ciclo 30 — Fusão Chub-local medida e revertida

### Hipótese

Fusão semântica entre propostas guiadas pelo Campaign Hub e candidatos locais poderia preservar as bordas locais, aproveitar highlights alinhados e evitar que propostas guiadas largas ocupassem o orçamento no modo Renan-first.

### Resultado

A hipótese foi refutada para publicação. No checkout limpo da 6.14 e na fonte real `3XJfcqn56Rw`, o harness reproduziu `5/66` em IoU 0,10 no genérico sem e com Chub e `7/66` no Renan-first sem e com Chub. Em IoU 0,25, os resultados foram `0/66`, `0/66`, `1/66` e `1/66`. A tentativa chegou a anexar evidência Chub fundida a cinco candidatos locais, mas não aumentou recall nem precisão temporal.

A rodada também identificou que `renan_speaking` não era copiado para o dossiê da proposta materializada; a correção foi usada apenas durante o experimento e revertida junto com a fusão. A discrepância entre o resultado histórico de `27,27%` do ciclo 29 e o harness atual ficou registrada como problema de reprodutibilidade, não como ganho.

### Validação

As regressões focadas passaram com **72 testes**. A suíte completa passou com **541 aprovados e 4 ignorados** após o asset BlazeFace ser provisionado temporariamente, conferido e removido. O checkout final está limpo em `e360e74`; a versão permanece `6.14` e nenhum commit funcional novo foi publicado.

Relatório: [`CYCLE_30_REPORT_2026-08-20.md`](CYCLE_30_REPORT_2026-08-20.md).

## 6.14 — Snapshot rico do Chub no gate Renan-first

### Hipótese e descoberta

O Campaign Hub precisava ser avaliado pela utilidade real, não pela quantidade de dados integrada. Na live real `3XJfcqn56Rw` — 5.905 segundos, 27 blocos e 66 highlights — o snapshot rico aumentou o recall exploratório de IoU 0,10 de `7,58%` para `27,27%` no modo genérico, mas a condição Renan-first continuava com `0/30` identidades disponíveis. A auditoria encontrou que o caminho normal fornecia `campaign_hub_snapshot_path`, enquanto `_attach_block_evidence()` lia somente o snapshot já embutido.

### Incluído

- `modules/clip_selector.py`: leitura do snapshot pelo caminho persistido também no anexo de evidência local.
- `modules/clip_selector.py`: evidência conservadora `campaign_hub_aligned_owner_or_allied` quando o candidato cobre pelo menos 75% de bloco `renanSpeaking=true` em tier `owner`/`allied`.
- `tests/test_speaker_identity_context.py`: regressões para snapshot embutido, snapshot por caminho, tiers de baixa confiança e ausência de identidade.

### Resultado verificado

Na mesma fonte real, o Renan-first com snapshot rico passou de `0/30` para `3/30` candidatos com identidade disponível e `3/30` com contexto completo. Os demais permaneceram em revisão. O genérico não recebeu bloqueio novo. O prior lexical agregado do Acervo não alterou as 12 janelas do project-57 sem snapshot rico, confirmando que ele é um detector auxiliar de não-conteúdo, não uma seleção especializada.

### Validação e limitação

A rodada teve **45 testes focados aprovados** e **541 testes aprovados com 4 ignorados** na suíte completa, além de `compileall`, `node --check`, `git diff --check` e scanner de segredos limpos. A integração é útil, mas ainda parcial: cobertura melhorou mais do que precisão de borda, e nenhum resultado autoriza publicar automaticamente. O próximo ciclo deve fundir candidatos guiados e locais com quota, deduplicação e ranking, em vez de concatenar propostas guiadas antes do pool local.

Relatório: [`CYCLE_29_REPORT_2026-08-20.md`](CYCLE_29_REPORT_2026-08-20.md).

## 6.13 — Gate Renan-first para identidade de locutor

### Incluído

- `modules/clip_selector.py`: propagação de `speaker_identity_required`, `speaker_identity_available` e `speaker_identity_review_required` por NLP, Gemini/Ollama, expansão contextual e propostas guiadas pelo Campaign Hub.
- `modules/editorial_ranker.py`: penalidade técnica limitada e motivo explícito quando o foco Renan-first não tem identidade de locutor confirmada.
- `tests/test_speaker_identity_context.py` e `tests/test_speaker_identity_ranker.py`: regressões para foco explícito, perfil Renan com `auto`, locutor rotulado e modo genérico.

### Hipótese e baseline

Uma transcrição local persistida tinha 247 segmentos e nenhum locutor identificado. Antes da mudança, o caminho genérico produzia candidatos `context_complete=true` mesmo sem prova de que a fala era do Renan. A hipótese foi impedir que essa ausência passasse como corte Renan-first pronto.

### Validação da rodada

A comparação real produziu 9 candidatos no foco Renan-first; todos ficaram com `speaker_identity_available=false`, `speaker_identity_review_required=true`, `context_complete=false` e `review_required=true`. O modo genérico preservou 5 candidatos completos sem bloqueio novo. As regressões focadas passaram com 28 testes; a suíte completa terminou com 537 aprovados e 4 ignorados depois do provisionamento temporário e remoção do BlazeFace. `git diff --check` passou.

### Limitações e próxima hipótese

A release não identifica automaticamente a voz do Renan nem substitui diarização ou conferência audiovisual. O próximo ciclo deve usar, quando disponível, evidência temporal do Acervo em snapshot local autorizado, mantendo revisão obrigatória para tiers incertos, fontes desalinhadas ou snapshot ausente.

Relatório: [`CYCLE_28_REPORT_2026-08-20.md`](CYCLE_28_REPORT_2026-08-20.md).

## 6.12 — Download público com cookies locais opcionais

### Incluído

- `modules/source_ingest.py`: normalização segura de navegadores, suporte local a `cookiesfrombrowser`, User-Agent limitado e mensagens distintas para anti-bot e HTTP 403.
- `config.py`: preferências persistentes `source_cookie_browser` e `source_user_agent`, vazias por padrão.
- `app.py`: passagem validada das preferências para probe, importação de vídeo, importação de áudio e busca de legendas públicas.
- `templates/index.html` e `static/js/app.js`: seletor de navegador, User-Agent opcional e payloads consistentes na aba Link público.
- `tests/test_sources_and_context.py`: regressões para navegadores aceitos, entradas inválidas, mensagens acionáveis e passagem pela rota de probe.

### Hipótese e baseline

O baseline 6.11 reproduzia `Sign in to confirm you’re not a bot` antes do download e HTTP 403 após aproximadamente `0,5%` do stream. A hipótese foi permitir que o usuário escolha o navegador local autenticado sem transportar cookies ou credenciais.

### Validação da rodada

A suíte focada terminou com **27 testes aprovados**. A suíte completa terminou com **532 aprovados e 4 ignorados** depois de o modelo BlazeFace ser baixado temporariamente, conferido pelo SHA-256 esperado e removido antes do commit. `node --check static/js/app.js` e `git diff --check` também passaram. O download real usando a sessão autenticada do notebook do usuário permanece não verificado no sandbox.

### Limitações e próxima hipótese

A implementação não contorna CAPTCHA nem garante que todo stream 403 será aceito: ela usa o mecanismo suportado pelo yt-dlp e oferece fallback por MP4 local. A próxima hipótese é testar no mesmo computador/IP e navegador que concluiu a verificação, registrando somente o status sanitizado do download.

Relatório: [`CYCLE_27_REPORT_2026-08-20.md`](CYCLE_27_REPORT_2026-08-20.md).

## 3.1 — De candidato bruto a corte pronto e ranqueado

### Incluído

- `modules/clip_selector.py`: `_attach_block_evidence()` faz todo candidato herdar o contexto editorial do bloco QA-gated em que cai — título, resumo, pergunta-gatilho, tópicos, `density_rank`, `self_contained_rank`, `renan_speaking`, `speakers_note`, riscos e tier. Novo `_block_field()` lê snapshots em snake_case e camelCase.
- `scripts/run_acervo_recall_benchmark.py`: nova métrica `precision_at_k`.
- `scripts/convert_chub_blocks_export.py`: preserva `speakers_note`.
- `tests/test_campaign_hub_guidance.py`: quatro regressões novas.

### O ranqueamento já funcionava

`precision@k` foi medida antes de mexer em qualquer peso: **100%** dos 20 primeiros colocados carregam um destaque QA-gated, em blocos de densidade média 76–83 de 99. O Renan-first também já opera — 20% do top 20 vem dos blocos com Renan falando, que são apenas 9% dos destaques disponíveis. Nenhum peso de ranking foi alterado.

### O defeito real

Só os candidatos nascidos de seed do Campaign Hub carregavam proveniência. Os demais chegavam ao revisor sem tema, sem risco e **sem dizer quem fala** — num acervo em que 24 de 27 blocos têm `renan_speaking=false`.

Agora **121 de 121 candidatos (100%)** chegam com contexto e veredito de revisão. O veredito de locutor distingue `renan_confirmado`, `terceiro_ou_indeterminado` e `nao_confirmado`; qualquer coisa que não seja o primeiro exige revisão, assim como qualquer risco sinalizado. Tudo viaja como `evidence_only`: nada eleva score nem libera gate.

As próprias regressões encontraram um defeito: snapshots em camelCase perdiam ranks, riscos e locutor silenciosamente.

Cobertura e precisão não se moveram — `50/66` destaques, `25/27` blocos, precisão `1.00`, desperdício 0. Suíte: **347 aprovados, 7 falhas ambientais**.

Relatório em [`CYCLE_21_REPORT_2026-08-17.md`](CYCLE_21_REPORT_2026-08-17.md).

## 3.0 — Orçamento de candidatos governado pela fonte

### Incluído

- `app.py`: `_selection_coverage_plan()` passa a derivar o orçamento da duração da fonte (`SECONDS_PER_CANDIDATE = 45`), com piso `MIN_CANDIDATE_BUDGET = 15` e válvula de segurança `MAX_CANDIDATE_BUDGET = 400`. O antigo `min(36, ...)` dava a uma fonte de 4 horas praticamente a mesma cota de uma de 1 hora.
- `scripts/run_acervo_recall_benchmark.py`: novas métricas de precisão — `precision_on_block`, `precision_carrying_highlight` e `off_block_candidates`.
- `tests/test_candidate_budget.py`: cinco regressões novas.

### Precisão medida antes de mexer no teto

A varredura de tetos de 20 a 160 candidatos na mesma fonte mostrou `precision_on_block = 1.00` em **todos** os pontos, com zero candidatos fora de bloco. Aumentar a quantidade não produziu lixo. O IoU médio subiu junto, de `0.0772` para `0.2730`.

A oferta satura em **121** candidatos: elevar o teto de 120 para 160 não produziu nenhum candidato a mais. O teto não continha excesso — cortava material que os gates já haviam aprovado.

### Resultado

| Métrica | 2.9 | 3.0 |
| --- | --- | --- |
| Destaques recuperados | `27/66` | `50/66` |
| Blocos alcançados | `20/27` | `25/27` |
| `precision_on_block` | `1.00` | `1.00` |
| Candidatos fora de bloco | 0 | 0 |
| IoU médio | `0.1600` | `0.2730` |

Somando as rodadas na mesma fonte: `11/66` → `24/66` (ponte Chub) → `27/66` (descarte de não-conteúdo) → `50/66` (orçamento corrigido). **4,5× o ponto de partida, com precisão `1.00` do começo ao fim.**

Não existe quantidade mínima de cortes: o orçamento é limite, nunca meta, e o pipeline encerra sozinho quando o material acaba.

Suíte: **343 aprovados, 7 falhas ambientais**.

### Limitações

Medido em um único vídeo. O efeito do orçamento maior sobre o tempo de processamento de uma fonte de 3–4 horas não foi medido. Relatório em [`CYCLE_20_REPORT_2026-08-17.md`](CYCLE_20_REPORT_2026-08-17.md).

## 2.9 — Primeiro recall medido em fonte longa inteira

### Incluído

- `scripts/run_acervo_recall_benchmark.py`: novo benchmark que roda o seletor real sobre a transcrição completa de uma fonte longa e pontua contra **todos** os blocos e destaques que o Acervo produziu para ela. Não exige mídia local.
- `scripts/convert_chub_blocks_export.py`: aceita o payload cru além do envelope MCP e ganhou `--transcript`, que traz as regiões rotuladas como sem conteúdo para o snapshot.
- `modules/clip_selector.py`: `_labelled_non_content_regions()` e `_drop_labelled_non_content()` descartam candidatos que caem majoritariamente em trechos que o Acervo marcou como sem conteúdo editorial.
- `tests/test_campaign_hub_guidance.py`: duas regressões novas.

### O bloqueio removido

Os ciclos 16, 17 e 18 terminaram com a mesma frase: o recall real não pôde ser medido por falta do MP4. A observação que destravou é que a seleção do Furia roda sobre a **transcrição**, não sobre os pixels — então uma transcrição autorizada do Acervo basta para medir a seleção.

### Resultado

Medido em `3XJfcqn56Rw` ("O ÚLTIMO ANÁLISES RENAIS"), 98 minutos, 27 blocos, 66 destaques:

| Configuração | Destaques | Blocos | IoU médio | Desperdício |
| --- | --- | --- | --- | --- |
| Seleção local (NLP) | `11/66` | `18/27` | `0.1012` | 14 de 40 |
| `+ campaign_hub_guided` | `24/66` | `17/27` | `0.1225` | 10 de 40 |
| `+ filtro de não-conteúdo` | `27/66` | `20/27` | `0.1600` | 0 de 40 |

A ponte do Campaign Hub **mais que dobrou** o recall — primeira evidência quantitativa de que a integração da 2.6 melhora a seleção.

O recall é binário: 24 destaques inteiros, 42 nunca tocados, **zero parciais**. O gargalo é cobertura, não recorte de janela.

Suíte: **338 aprovados, 7 falhas ambientais**.

### Limitações

Medido em um único vídeo, sem perfil de energia e sem mudanças de cena — o relatório declara ambos. Renderização e FFprobe continuam bloqueados por ausência de `ffmpeg` no container. Relatório em [`CYCLE_19_REPORT_2026-08-17.md`](CYCLE_19_REPORT_2026-08-17.md).

## 2.8 — Alinhamento temporal das seeds do Campaign Hub

### Incluído

- `modules/campaign_hub_guidance.py`: `_map_interval()` e `build_campaign_hub_guided_seeds()` aceitam `media_duration` e preferem a duração **medida** da mídia local sobre a **declarada** no snapshot.
- `modules/clip_selector.py`: novo `_media_duration()` para ler a duração medida das configurações do job, e nova constante `MAX_SEED_ANCHOR_GAP_S = 60.0` limitando a ancoragem de uma seed na frase mais próxima.
- `app.py`: o job passa a gravar `settings["media_duration"]` com a duração já obtida por `ffprobe`, que nunca chegava à camada de orientação.
- `tests/test_campaign_hub_guidance.py`: seis regressões com os dados do b354 verificados direto no Acervo.
- `tests/test_runtime_version.py`: lê `VERSION` em vez de repetir o número, corrigindo duas falhas que a 2.7 introduziu.

### Hipótese e baseline

A hipótese foi que as seeds do Campaign Hub nasciam no eixo de tempo errado. `_map_interval()` decidia o mapeamento pela duração declarada em `records.sources[].duration_s` — a live inteira — e não pela duração do arquivo em processamento. No b354 a live tem `11230s` e o bloco `549.44s`: a condição nunca fecha.

Reproduzido em execução real: as três seeds ficaram em `6289.36` / `6365.80` / `6631.04` enquanto a transcrição local ia de `0` a `497s`. Nenhuma seed dentro da transcrição.

Uma segunda falha apareceu na reprodução e não estava prevista: em vez de zero propostas, o seletor devolvia **três propostas idênticas** em `488.48–497.00`, porque `_build_campaign_hub_proposal()` ancorava qualquer seed órfã na frase mais próxima, sem limite de distância. Três destaques distintos viravam a mesma janela errada com proveniência do Campaign Hub.

### Resultado

Com a duração medida informada, os três destaques mapeiam para `146.80` / `223.24` / `488.48` — exatamente os valores do baseline documentado — e geram três propostas distintas, cada uma abrindo antes do destaque para recuperar a pergunta ou o antecedente, todas `review_required=true` porque o bloco tem `renanSpeaking=false`.

Suíte: **336 aprovados, 7 falhas ambientais**, contra 328/9 antes da rodada. A diferença de `+8` é exata: `+2` dos testes de versão corrigidos e `+6` das regressões novas.

### Limitações

O recall real do b354 continua **não verificado**. A transcrição usada nas regressões é sintética e serve para exercitar o alinhamento, não para medir seleção. Nenhum ganho sobre o baseline `0/3` é reivindicado. O MP4 local do bloco não está no ambiente. Relatório em [`CYCLE_18_REPORT_2026-08-17.md`](CYCLE_18_REPORT_2026-08-17.md).

## 2.7 — Confiabilidade declarada da medição do benchmark

### Incluído

- `modules/editorial_benchmark.py` ganhou `assess_measurement()` e o bloco `measurement` no payload: toda comparação agora declara se pode ser confrontada com o baseline, com `status`, `mapping_required`, `mapping_applied`, `source_is_full_length` e avisos em português.
- `metrics` repete `measurement_reliable` e `measurement_status`, porque `list_benchmarks()` expõe apenas `metrics` — um número de recall nunca deve viajar sem a confiabilidade dele.
- `source` passou a registrar `mapping_applied`.
- `scripts/run_editorial_benchmark.py` expande `~` em `--memory` e `--source`, imprime `measurement` e emite avisos em `stderr` quando a medição não é comparável.
- `app.py` devolve `measurement` em `POST /api/editorial/benchmark` e troca a mensagem de sucesso por um alerta explícito quando a medição não é confiável.
- `tests/test_editorial_benchmark.py` adiciona quatro regressões: mapeamento ausente, fonte longa completa, bloco iniciando em zero e lista de candidatos vazia.

### Hipótese e baseline

A hipótese foi que um `0/3` causado por timeline não mapeada estava indistinguível de um `0/3` causado por seleção ruim, tornando qualquer medição futura de recall não confiável. O baseline b354 permanece: 7 candidatos, 3 highlights, recall `0/3`, IoU médio `0.0`.

O caso foi reproduzido em execução real. Rodando o benchmark do b354 sem `--source`, o relatório devolvia `coverage_recall: 0.0` e `mean_boundary_error_s: 5904.771` sem qualquer aviso. Os `5904.771s` não são erro editorial: são o deslocamento do bloco dentro da live, porque os destaques permaneceram em segundos absolutos (`6289.36`) enquanto os candidatos estavam na timeline local (`146.80`).

### Validação da rodada

Suíte completa: **330 aprovados, 7 falhas ambientais**. As mesmas 7 falhas foram reproduzidas com `git stash` no código original (`326 aprovados, 7 falhas`), confirmando que são causadas por `ffmpeg`/`ffprobe` ausentes no container e pelo asset externo BlazeFace, não por esta mudança. A diferença de `+4` aprovados corresponde exatamente às regressões adicionadas.

Também passaram `compileall`, `node --check static/js/app.js` e `git diff --check`.

Após a mudança, o mesmo comando que antes silenciava agora imprime `measurement.reliable=false`, `status=unmapped_timeline` e a instrução de informar o MP4 do bloco.

### Resultado e limitações

Confirmado: um resultado de benchmark sem mapeamento temporal deixa de ser confundido com um resultado de seleção. Corrigido: `--memory ~/...` não falha mais silenciosamente com "Bloco não encontrado".

O recall real do b354 continua **não verificado**: o MP4 local do bloco não estava presente neste ambiente (`workspace/exports/` vazio) e o snapshot autorizado não pôde ser obtido do conector CHUB, que ficou indisponível durante a rodada. O baseline segue `0/3` sem reivindicação de ganho. Nenhuma alteração foi feita em seleção, ranking, expansão de seeds ou renderização.

## 2.6 — Primeira ponte funcional Campaign Hub→seeds→propostas

### Incluído

- `modules/campaign_hub_guidance.py` normaliza snapshots autorizados do Campaign Hub em seeds auditáveis, aceitando os formatos snake_case e camelCase usados pelos exports reais.
- A normalização preserva proveniência, `sentenceIdx`, `source_ref`, `renanSpeaking`, `trustTier`, `gateWarnings`, `riskFlags`, `densityRank` e `selfContainedRank`, além de suportar highlights aninhados, `possibleCuts` e fallback por bloco.
- `modules/clip_selector.py` passou a gerar propostas `campaign_hub_guided`: a seed é expandida até a menor janela local que complete antecedente, pergunta, tese/evidência e payoff quando a transcrição permitir.
- As propostas guiadas recebem gates explícitos de contexto, payoff, locutor, timing, risco, técnico, proveniência e avisos. Elas permanecem separadas de cortes aprovados e podem exigir revisão humana.
- `modules/editorial_context.py` expõe o diagnóstico da quantidade de seeds guiadas; `app.py` carrega o snapshot uma vez por job e o reutiliza offline-first na seleção, nos hooks e no ranking.
- `tests/test_campaign_hub_guidance.py` adiciona seis regressões para mapeamento de timeline, expansão contextual, fallback legado, origem auditável, formato camelCase real e revisão obrigatória de `third_party`/`gateWarnings`.
- `VERSION`, `README.md`, `AGENTS.md`, `START_HERE.md`, `PROJECT_STATE.md` e `NEXT_CYCLE.md` registram a nova identidade e o próximo experimento.

### Hipótese e baseline

A hipótese foi que transformar highlights/blocos autorizados em seeds temporais e semânticas e expandi-los até a menor janela completa aumentaria o recall sem sacrificar contexto, atribuição ou revisão. O baseline persistente b354 tinha sete candidatos locais, recall `0/3` e IoU médio `0.0`.

### Validação da rodada

A suíte completa terminou com **333 testes aprovados**. Também passaram `compileall`, `node --check static/js/app.js`, `git diff --check` e a verificação SHA-256 do asset BlazeFace provisionado temporariamente e removido antes do commit.

Com um payload real do Campaign Hub para o vídeo `gVrW6a5e6Tc` e o bloco `70358a7d-7848-48d1-8d3d-5ef7c61c149d`, a normalização produziu duas seeds a partir dos highlights `sentenceIdx=128` e `sentenceIdx=171`. A avaliação de proposta gerou as janelas `426.4–451.52s` e `511.0–566.12s`; ambas passaram `context_complete=true`. Como o bloco tinha `trustTier=third_party` e `gateWarnings=["start_continuation"]`, as duas ficaram com `review_required=true` por `provenance_gate` e `warning_gate`, sem autoaprovação.

### Resultado e limitações

A ponte está implementada e coberta por regressões, mas o recall do b354 **não foi medido nesta release** porque o snapshot autorizado correspondente não estava instalado localmente durante o job normal. Portanto, não há ganho de recall reivindicado sobre `0/3`; o resultado é funcional e reproduzido no payload real do Chub, mas o benchmark de mídia local permanece não verificado.

A proveniência `third_party` e os avisos de início abrupto continuam exigindo revisão, de forma intencional. Sem snapshot local em `~/FuriaClipsData/campaign_hub/profile.json`, o job normal permanece no caminho legado e não produz propostas guiadas. Nenhum token, cookie, snapshot privado, banco local, mídia grande ou modelo binário foi incluído no Git.

### Próxima hipótese

> Se um snapshot autorizado e sanitizado do Campaign Hub for instalado localmente e o Furia reprocessar o caso b354 com a ponte 2.6, o recall temporal deve sair de `0/3` sem aumentar falsos positivos, atribuições erradas, truncamentos ou confusão entre quem fala e quem é foco editorial.

## 2.5 — Prompt operacional Chub→cortes

### Incluído

- `docs/continuity/PROMPT_EXECUCAO_CHUB_CORTES.md`, prompt copiável para executar a próxima hipótese do projeto com foco em Campaign Hub→seeds→alinhamento→expansão→gates→propostas.
- `START_HERE.md`, `AGENTS.md` e `README.md` atualizados para encaminhar diretamente ao novo prompt, além do prompt mestre e do contrato funcional.
- `CYCLE_15_REPORT_2026-08-17.md`, relatório da criação do prompt e do estado funcional preservado.
- `VERSION` incrementado para `2.5`; nenhum módulo de seleção, ranking, ingestão, diarização, reframe ou renderização foi alterado.

### Validação da rodada

A revisão confirmou o prompt novo, os links relativos, a versão, **327 testes aprovados**, `git diff --check`, `compileall`, `node --check static/js/app.js` e a ausência de tokens, cookies, mídia grande, bancos locais, modelos binários ou dados privados. O asset BlazeFace foi usado apenas temporariamente com SHA-256 conferido e removido antes do commit.

### Limitações conhecidas

A revisão 2.5 não implementa a ponte funcional Chub→seeds→expansão→gates→propostas. O benchmark b354 permanece em `0/3` e a sessão de blocos continua sendo diagnóstico, revisão e fallback, não o produto final.

## 2.4 — Contrato Campaign Hub→cortes e reorientação do norte

### Incluído

- `docs/continuity/CHUB_INTEGRATION_CONTRACT.md`, contrato funcional que define o fluxo Campaign Hub → alinhamento à fonte local → seeds → expansão contextual → gates → propostas → revisão → renderização.
- `PROMPT_MESTRE_IA.md` e `START_HERE.md` atualizados para deixar claro que a sessão de blocos é superfície de diagnóstico/revisão e que o objetivo principal é melhorar de forma verificável a seleção de cortes Renan Santos/MBL usando contexto do Campaign Hub.
- `PROJECT_STATE.md` e `NEXT_CYCLE.md` reorientados para a hipótese de transformar blocos/highlights Chub em seeds temporais e semânticas, sem tratar o Campaign Hub como aprovador automático.
- `VERSION` incrementado para `2.4`, representando a mudança observável no contrato de continuidade; nenhuma lógica de seleção, ranking, ingestão, reframe ou renderização foi alterada nesta revisão.

### Validação da rodada

Foram revisados o adaptador do Campaign Hub, a memória local, o contexto editorial, o ranker, a sessão de blocos, o frontend e os dados autorizados de blocos/transcrição. O estado real registrado é que a memória e a UI existem, mas o contexto Chub ainda influencia pouco o resultado e não cria propostas de janela contextualizadas. A suíte terminou com **327 testes aprovados**, além de `compileall`, `node --check`, `git diff --check` e revisão de arquivos proibidos; o asset BlazeFace usado na validação foi removido antes do commit.

### Limitações conhecidas

A revisão 2.4 não melhora recall, geração de propostas, diarização, reconhecimento de voz, reframe, ranking, download remoto por range ou qualidade editorial. O benchmark b354 permanece em `0/3` até que a hipótese Chub→seed→expansão seja implementada e reproduzida. A sessão de blocos continua funcional apenas para a parte já implementada de consulta, inspeção e exportação; ela não deve ser interpretada como integração completa.

## 2.3 — Prompt mestre e contrato de continuidade

### Incluído

- `docs/continuity/PROMPT_MESTRE_IA.md`, prompt copiável que consolida o `START_HERE`, os prompts históricos, as decisões permanentes, o norte do benchmark b354, o uso do Campaign Hub, o ciclo de engenharia, segurança e o formato de entrega.
- `docs/continuity/COMMIT_MESSAGE_TEMPLATE.md`, modelo obrigatório para registrar hipótese, baseline, implementação, escopo excluído, validação, resultado, limitações e próxima hipótese no corpo dos commits.
- `docs/continuity/CYCLE_13_REPORT_2026-08-17.md`, relatório da rodada documental e da hipótese de tornar o GitHub autossuficiente para continuidade entre IAs.
- `README.md`, `AGENTS.md`, `START_HERE.md`, `PROJECT_STATE.md` e `NEXT_CYCLE.md` atualizados para encaminhar ao prompt mestre, manter o norte atual e eliminar a divergência do hash `a9a2803` para `074a129`.
- `VERSION` incrementado para `2.3`, representando a mudança no contrato de continuidade; nenhuma lógica de seleção, ranking, ingestão, reframe ou renderização foi alterada.

### Validação da rodada

O estado do Git, a branch `manus/rebuild-opus-parity`, a revisão de código `074a129`, os documentos vivos, os prompts históricos e os resultados da release 2.2 foram auditados. A validação desta revisão é documental e inclui revisão de links relativos, diff, versão, ausência de arquivos proibidos e confirmação do hash final após o commit.

### Limitações conhecidas

A revisão 2.3 não melhora recall, diarização, reconhecimento de voz, reframe, ranking, download remoto por range ou qualidade editorial. O benchmark b354 permanece em `0/3` até que a hipótese de expansão de seeds seja executada e reproduzida. A capacidade de uma IA externa seguir o contrato deverá ser avaliada em uma sessão futura com checkout limpo.

## 2.2 — Benchmark persistente e exportação individual de highlights

### Incluído

- `modules/editorial_benchmark.py` registra uma comparação local e reproduzível entre candidatos do Furia e destaques QA-gated do Campaign Hub, sem consultar o MCP durante os cortes.
- O benchmark persiste mapeamento da timeline longa para o MP4 de bloco, recall de cobertura, IoU, erro médio de fronteira, duplicatas e classificação explicável da divergência.
- `scripts/run_editorial_benchmark.py` permite repetir a comparação com um arquivo de candidatos e uma memória local autorizada.
- `POST /api/editorial/blocks/highlights/export` e os botões do painel exportam um destaque específico no aspecto original.
- `GET/POST /api/editorial/benchmark` permite consultar e salvar resultados locais; os relatórios ficam em `FuriaClipsData/benchmarks`, fora do Git.
- Testes de mapping, IoU, persistência, rotas e sintaxe da interface foram adicionados.

### Validação da rodada

O bloco b354 real foi comparado com os sete candidatos persistidos pelo Furia. Seus três destaques foram mapeados para `146.80–150.80s`, `223.24–228.40s` e `488.48–495.20s` no MP4 local de `549.449s`. O recall de cobertura foi `0/3`, o IoU médio foi `0.0` e os três casos foram classificados como `Campaign Hub melhor` neste benchmark temporal. Os três highlights foram exportados individualmente pelo backend e validados em 1920×1080 H.264/AAC, com durações de aproximadamente `4.004s`, `5.172s` e `6.740s`.

### Limitações conhecidas

O benchmark mede alinhamento temporal e preserva flags editoriais, mas não prova que o Campaign Hub esteja sempre correto nem resolve diarização, reconhecimento de voz, relevância semântica ou download remoto por range. O caso b354 mostrou uma lacuna real de cobertura; esta release não aumenta o peso do Chub no ranking com base em uma amostra única.

## 2.1 — Memória local do Campaign Hub, blocos e exportação seletiva local

### Incluído

- Memória local versionada e offline-first para exports autorizados do Campaign Hub, com manifesto, hash, instalação atômica e fusão incremental.
- Conversor e comando local de atualização em `scripts/convert_chub_blocks_export.py` e `scripts/update_campaign_hub_memory.py`, sem depender do MCP durante cada job.
- Leitura de blocos editoriais com filtro por fonte/YouTube ID, busca, destaques, pergunta-gatilho, riscos, proveniência e prioridade Renan-first sem ocultar terceiros.
- Novo painel visual de Blocos entre Fonte e Refinamento, mantendo o aspecto original como prioridade.
- Exportação seletiva local por intervalo e mapeamento seguro de timestamps absolutos do vídeo longo para MP4 de bloco que começa em zero.
- Evidência temporal/textual de blocos no ranking como ajuste pequeno, explicável e nunca como gate.
- Testes para memória, filtros, ranking, exportação, limites, timeline mapeada e UX; nenhum vídeo ou segredo foi versionado.

### Validação da rodada

A consulta autorizada por `videoId=57nyfP9IDW4` retornou 64 blocos reais do Primeiro Ato. O bloco b354, `6142.56–6692.0s`, foi exportado do MP4 local como `0–549.44s` e validado em 1920×1080, H.264/AAC, 549.4489s. A suíte completa terminou com **322 testes aprovados**; `node --check`, `compileall`, `git diff --check` e inspeção visual também passaram.

### Limitações conhecidas

O download remoto seletivo por range ainda depende do provedor e não foi prometido. O benchmark persistente ainda será construído na próxima onda, assim como exportação individual de highlights, diarização robusta, reconhecimento de voz e simplificação completa da sidebar.

## 2.0 — START_HERE canônico e validação prática Renan-first

### Incluído

- Novo `docs/continuity/START_HERE.md`, ponto de entrada canônico que unifica o contexto do Furia, o estado real incompleto, o uso do Campaign Hub, o fluxo inspirado no Garimpo, as regras Renan-first, o ciclo de testes e a continuidade no GitHub.
- `AGENTS.md` atualizado para apontar o START_HERE; os Prompts 1, 2, 3 e o Prompt Mestre antigo permanecem como histórico, não como instrução vigente.
- Relatório `docs/continuity/CYCLE_10_REPORT_2026-08-17.md` com a primeira validação ponta a ponta usando o MP4 do Primeiro Ato de Campanha e comparação read-only com o bloco b354 do Campaign Hub.
- Diagnóstico explícito de que o Furia atual faz upload, transcrição, seleção e renderização, mas ainda não possui download seletivo de bloco, diarização confiável nem memória rica local do Campaign Hub.
- Versão pública atualizada de 1.9 para 2.0 e teste de identidade de runtime atualizado.

### Validação da rodada

O clone real da branch `manus/rebuild-opus-parity` foi executado com 306 testes aprovados. O MP4 de aproximadamente 9m14s foi processado pelo servidor local, gerando sete cortes H.264 1920×1080 em 16:9, validados por FFprobe e inspeção visual. O Campaign Hub identificou o mesmo material como o bloco b354, com 121 frases, três destaques QA-gated, pergunta-gatilho, riscos e `renanSpeaking=false`.

### Limitações conhecidas

Nenhum módulo de seleção, ranking ou renderização foi melhorado nesta release. O segundo ciclo não cobriu os três destaques do bloco b354, embora tenha produzido arquivos tecnicamente válidos. A entrada por link foi bloqueada pelo anti-bot do YouTube neste ambiente. A área autenticada interna do Garimpo não ficou disponível na sessão Sandbox. O benchmark temporal/editorial foi especificado, mas ainda não foi implementado como funcionalidade do aplicativo.

## 1.9 — Prompt executor e paridade editorial via Campaign Hub

### Incluído

- Novo `docs/continuity/PROMPT_3_EXECUTOR_CHUB_PARITY.md`, prompt copiável para futuras IAs continuarem o Furia Clips com auditoria do checkout, hipótese única, testes, versionamento e publicação verificável.
- Contrato explícito para usar blocos QA-gated, transcrições, perguntas-gatilho, autossuficiência, payoff, riscos e destaques do Campaign Hub como benchmark e calibração fraca, sem chamada MCP direta no runtime.
- Regras de escopo que mantêm o Furia Clips focado em cortes precisos e contextuais e adiam um editor pós-renderização semelhante ao CapCut.
- Registro de padrões profissionais pesquisados em OpusClip, Descript e Riverside, traduzidos para foco por locutor/tópico, busca editorial, score explicável, presets de composição, preservação de evidência e diagnóstico de divergência.
- `AGENTS.md` atualizado para apontar o prompt executor vigente.

### Validação da rodada

A mudança é documental e operacional; nenhum módulo de processamento foi alterado. Foram conferidos o estado da branch, a versão 1.8, o prompt mestre, o prompt executor, o estado do projeto, o próximo ciclo, a linhagem do Campaign Hub e o contrato de versionamento. A suíte completa passou com `306 passed`, `git diff --check` e `py_compile` foram aprovados, e o commit `d27cb05` foi publicado na branch `manus/rebuild-opus-parity`.

### Limitações conhecidas

O benchmark Campaign Hub versus candidatos do Furia ainda não foi implementado nesta release. A versão 1.9 registra o contrato e a hipótese para a próxima rodada; ela não declara melhoria editorial já medida. A validação audiovisual não faz parte desta alteração documental.


## 1.8 — Decodificação AV1 e cobertura canônica da transcrição


### Incluído

- FFmpeg passa a forçar decodificação por software nas etapas de detecção de cenas, análise de layout e renderização, evitando que fontes AV1 dependam de aceleração de hardware indisponível.
- Fontes AV1 deixam de acionar o caminho OpenCV/MediaPipe quando a análise segura de layout não é possível; o Furia preserva o quadro original com fallback explícito, em vez de repetir erros de decodificação.
- O pipeline deixa de executar Whisper uma segunda vez quando a transcrição automática já foi obtida; a transcrição efetivamente usada passa a receber cobertura e proveniência antes da análise de contexto.
- A visão de seleção, depois de remover o pré-roll, preserva o status de cobertura, a origem e a qualidade da transcrição completa. Isso impede que uma transcrição válida seja reclassificada como “identidade temporal não validada” e que todos os candidatos sejam adiados por engano.

### Validação da rodada

No vídeo real `RENAN SANTOS — BP NAS ELEIÇÕES`, a primeira amostra de 15 minutos reproduzia o bug: 5 candidatos eram encontrados, mas os 5 eram adiados porque a seleção havia perdido a cobertura temporal. Depois da correção, a mesma amostra produziu **4 exports** válidos. Os arquivos finais preservaram 1920×1080 e foram validados por FFprobe como H.264/AAC, com durações aproximadas de 138,8 s, 40,4 s, 26,3 s e 27,2 s. A prova final não registrou novos erros AV1 no servidor.

A suíte completa passou com **306 testes**; os testes focados de contexto, fronteira, cenas, layout e AV1 passaram com **26 testes**. Também foram aprovados `py_compile` e uma renderização real de intervalo AV1 para H.264/AAC.

### Limitações conhecidas

A fonte BP completa tem aproximadamente 84 minutos. O ambiente encerrou o servidor durante a tentativa de transcrição integral, portanto a validação editorial desta rodada foi feita com uma amostra real de 15 minutos e com reanálise da transcrição/cortes antigos da fonte completa. Nenhum Gemini foi necessário. O Campaign Hub continua sendo prior agregado fraco e explicável; a próxima hipótese isolada permanece a detecção de erros semânticos do ASR antes de headlines.

## 1.7 — Contexto canônico, proxy multimodal e headlines específicas

### Incluído

- Transcrições coladas/importadas passam a carregar proveniência explícita e são marcadas como timeline canônica; o pipeline não executa Whisper silenciosamente quando o texto manual foi recebido.
- O Gemini recebe uma cópia audiovisual temporária compactada, com resolução máxima de 640 px, amostragem visual adaptativa e áudio mono a 16 kHz; o vídeo original não é alterado e o arquivo temporário é removido ao final.
- Upload e geração multimodal receberam timeouts menores e cancelamento cooperativo durante a compactação, upload, espera e geração.
- Cada sessão arquiva fora do GitHub a transcrição integral, a transcrição de seleção, o dossiê de contexto, headlines geradas, escolhas/rejeições de headlines, aprovações/rejeições de clips e um manifesto de proveniência.
- O botão de cópia do console usa o histórico completo da sessão, não somente as 200 linhas visíveis.
- O dossiê de contexto informa na interface a origem da transcrição, o uso do proxy Gemini e se o prior agregado do Campaign Hub foi realmente aplicado.
- O fallback de headlines reconhece o núcleo específico de mobilização, ato e ameaça, evitando slogans genéricos de segurança no caso real enviado pelo usuário.

### Validação da rodada

A suíte completa passou com `303 passed`; os testes focados passaram com `52 passed`; `py_compile`, `node --check` e uma prova local do proxy FFmpeg foram aprovados. A prova reduziu um vídeo sintético de 49.171 para 16.266 bytes, preservando a preparação de áudio e vídeo da cópia temporária. A regressão editorial do corte “não tenham medo/ato/ameaça” passou sem Gemini.

### Limitações conhecidas

O proxy reduz custo e risco de limite, mas não transforma uma análise visual longa em evidência perfeita; a transcrição canônica continua sendo a fonte temporal principal. O Campaign Hub ainda é usado como prior agregado fraco e explicável, não como memória de voz nem treinamento de pesos. A próxima hipótese isolada permanece a detecção de erros semânticos do ASR antes de headlines.

## 1.6 — Gate conservador de pré-roll e fronteira de conteúdo de live

### Incluído

- Novo módulo `modules/source_boundary.py` para detectar, com timestamps da transcrição, a fronteira entre pré-roll/propaganda e o conteúdo editorial da live.
- A seleção editorial recebe apenas a transcrição a partir da fronteira segura; a transcrição integral continua arquivada para auditoria.
- O detector prefere uma abertura forte de live, como “sejam bem-vindos” acompanhada de uma indicação inequívoca de início, sobre uma saudação promocional ambígua.
- Uma saudação genérica isolada, como “boa noite a todos”, não é suficiente para cortar automaticamente a fonte; nesse caso a timeline completa permanece em revisão segura.
- Regressões para pré-roll detectado, coletiva sem pré-roll, saudação genérica e limite manual de fronteira.

### Validação da rodada

No benchmark renal de 15 minutos, o baseline do projeto 42 gerava 3 exports e incluía o material promocional `1. se não ser na rua, porque pode ser.mp4`, iniciado em `66,0333s` e estendido até `215,29s`. Com a fronteira detectada em `169,5s`, o projeto 47 gerou 4 exports, nenhum iniciado antes de `169,5s`; os quatro foram validados por FFprobe como H.264/AAC 1920×1080. A suíte completa passou com `299 passed`. O resultado foi reproduzido depois do endurecimento conservador do detector, usando a amostra v2 para evitar deduplicação por assinatura.

### Limitações conhecidas

A fronteira é um diagnóstico de seleção e ainda não é persistida como campo próprio na tabela de projetos; o evento do job e os artefatos de benchmark registram o resultado. Uma fonte sem uma abertura forte pode permanecer sem corte automático, deliberadamente, para evitar remover conteúdo válido. A próxima rodada continua sendo a detecção de erros semânticos do ASR antes da headline.


## 1.5 — Transcrição por áudio via URL e gate técnico antes da renderização

### Incluído

- Nova operação assíncrona `POST /api/source/transcribe` para transcrever fontes públicas sem criar projeto ou gerar cortes.
- Transcrição por URL baixa áudio por padrão (`media_type: audio` / `format=ba/b`), mantendo o download de vídeo para o fluxo operacional de cortes.
- Botão separado no frontend para “somente transcrever”, com acompanhamento persistente do job, cancelamento existente e carregamento no editor.
- Candidatos com `technical_gate_status=review` agora são adiados antes do `VideoCutter`, preservando motivos, `review_flags` e intervalos no diagnóstico.
- Correção da persistência de `start_time`/`end_time` nos motivos de rejeição.
- Regressões para URL, áudio, enfileiramento sem cortes, gate técnico e identidade de runtime.

### Validação da rodada

A coletiva de 33m38s gerou 12 exports H.264/AAC e o vídeo `OÚLTIMOANÁLISESRENAIS.mp4` gerou 30 exports antes do gate; o replay sobre os candidatos reais identificou 13/30 para revisão técnica. A amostra renal de 15 minutos processada após o gate concluiu com 3 exports H.264/AAC válidos. A suíte completa chegou a 293 testes aprovados; `py_compile`, `node --check` e `git diff --check` foram aprovados. A URL do YouTube foi enfileirada no modo áudio, mas o downloader foi bloqueado por anti-bot nesta sessão; nenhum cookie ou credencial foi usado.

## 1.4 — Gate de contexto autossuficiente antes da renderização

### Incluído

- Candidatos explicitamente marcados com `context_complete=false` agora permanecem disponíveis para revisão diagnóstica, mas não são renderizados como cortes prontos.
- O job registra quantos candidatos foram adiados em `render_deferred_context_count` e preserva o motivo e os `review_flags` em `render_rejections`.
- A mudança foi baseada em mídia real: no lote de 15 minutos do MP4 enviado, o comportamento anterior renderizou 4 candidatos, incluindo um trecho de 168,09 segundos que começava no meio da frase e tinha `context_complete=false`; após a alteração, 3 candidatos foram renderizados e esse trecho foi adiado.
- O SRT `0815(1).srt` foi parseado como referência externa, sem ser associado ao MP4.

### Validação da rodada

A suíte completa passou com `288 passed`; os testes focados do gate passaram com `24 passed`; `py_compile` e `git diff --check` foram aprovados. A repetição real concluiu com `3` exports H.264/AAC válidos, em comparação com `4` antes da alteração. O processamento da fonte completa de 84,1 minutos foi bloqueado pelo limite operacional do ambiente durante a transcrição CPU; o lote verificável de 15 minutos foi processado com timestamps gerados do áudio do próprio MP4.

## 1.3 — Gate de pergunta explícita e modo offline do Prompt 2

### Incluído

- Perguntas explícitas com `?` agora exigem resposta suficiente antes de um candidato ser considerado contextualmente completo.
- A flag explicável `question_requires_answer` é propagada pelo seletor e pelo ranker para revisão e diagnóstico.
- Regressões para pergunta sem resposta e para expansão até a resposta antes de avançar para a pauta seguinte.
- Prompt 2 atualizado para não presumir a versão `1.1`, registrar a versão real pelo arquivo `VERSION`, reconhecer a hipótese de payoff como concluída e continuar com melhorias offline quando navegador/Criadores/Corteiros estiverem bloqueados.
- Cópia versionada do Prompt 2 em [`PROMPT_2_EXECUTOR.md`](PROMPT_2_EXECUTOR.md).

### Validação da rodada

A suíte completa passou com `286 passed`; `py_compile` e `git diff --check` foram aprovados. Nenhum navegador, login, cookie, Reel publicado ou nova fonte longa foi necessário para esta alteração. A validação audiovisual da fonte longa do Garimpo permanece pendente.

## 1.2 — Gate de payoff e menor janela completa

### Incluído

- A duração-alvo voltou a ser tratada estritamente como uma dica suave: o seletor não encerra o candidato enquanto o pensamento/payoff estiver aberto.
- A expansão continua até encontrar a menor janela com contexto e payoff completos, sem incluir a pauta seguinte quando o bloco anterior já fecha naturalmente.
- Regressão editorial baseada no padrão observado nos outputs reais: hook forte que terminava antes da conclusão.
- A versão de runtime passa a identificar a especialização editorial desta rodada como `1.2`.

### Validação da rodada

O teste específico de concisão passou com `5 passed`; a suíte completa passou com `284 passed`; `py_compile` e `git diff --check` foram aprovados. A fonte longa do Garimpo foi localizada e o download autenticado foi solicitado, mas o Corteiros não concluiu no sandbox por limitação do helper Electron; nenhum Reel publicado foi usado como fonte de corte nesta rodada.

## 1.1 — Resiliência da análise de cenas e primeiro benchmark real

### Incluído

- Timeout configurável na detecção de cenas via `FURIA_SCENE_DETECTION_TIMEOUT_SECONDS`, com padrão de 120 segundos.
- A detecção de cenas passou a ignorar áudio desnecessário, tratar timeout/erro do ffmpeg e retornar uma linha de base segura (`[0.0]`) sem derrubar o job.
- Três testes de regressão para retorno normal, timeout e retorno não-zero do ffmpeg.
- Primeiro teste real com Reel público do Renan: download, FFprobe, transcrição com 57 segmentos e geração de três clipes verticais.
- Benchmark audiovisual dos três clipes para identificar cortes aprováveis, cortes que terminam antes do payoff e cortes que começam no meio da frase.
- Escada de ingestão legítima documentada no prompt mestre para YouTube bloqueado, plataformas públicas alternativas, Criadores/Campaign Hub e Corteiros.

### Validação da rodada

Os testes específicos passaram com `11 passed` e a suíte completa com `283 passed`; `py_compile` também foi aprovado. O job integrado após a correção permaneceu ativo, concluiu com `3` artefatos e deixou o servidor saudável. O benchmark real mostrou que a estabilidade melhorou, mas a seleção ainda precisa impedir finais antes do payoff e penalizar inícios fragmentados. A versão 1.1 foi publicada no commit `6349d37` após a atualização do estado persistente.

## 1.0 — Fundação do contrato de continuidade

### Incluído

- Fonte única de versão em [`VERSION`](../../VERSION), iniciada em `1.0`.
- Leitura da versão pelo servidor Flask, com exposição no console de progresso, na interface e em `/api/settings`.
- Contrato de versionamento em [`docs/VERSIONING.md`](../VERSIONING.md).
- Instruções de retomada para qualquer IA em [`AGENTS.md`](../../AGENTS.md).
- Estado atual persistente em [`PROJECT_STATE.md`](PROJECT_STATE.md).
- Decisões editoriais e técnicas em [`DECISIONS.md`](DECISIONS.md).
- Procedimento da próxima rodada em [`NEXT_CYCLE.md`](NEXT_CYCLE.md).
- Registro explícito de que vídeos públicos publicados nos perfis do Renan podem ser analisados como corpus audiovisual legítimo.
- Registro dos três formatos editoriais: `16:9 original`, `1:1 Alfinetei` e `fake tweet`.

### Validação concluída

A suíte completa foi executada com `280 passed`; `python -m py_compile app.py` foi aprovado; a versão foi carregada de `VERSION`; e o asset público do BlazeFace foi validado pelo tamanho e SHA-256 do manifesto. A documentação de estado foi atualizada após a publicação no commit `fbbe5ca`, na branch `manus/rebuild-opus-parity`.
