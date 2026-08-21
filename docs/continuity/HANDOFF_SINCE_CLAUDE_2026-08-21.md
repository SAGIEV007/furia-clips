# Relatório de continuidade desde a retomada do Claude

## Escopo do relatório

Este documento registra tudo que foi alterado depois do ponto de retomada identificado no commit `085569f`, na branch isolada `claude/repo-access-commits-imgjmk`. Ele separa implementação efetiva, validação, limitações, decisões e propostas do novo norte de plataforma. O relatório não afirma que uma ideia foi implementada apenas porque foi desenhada.

## Estado atual

| Campo | Estado confirmado |
| --- | --- |
| Repositório | `SAGIEV007/furia-clips` |
| Branch | `claude/repo-access-commits-imgjmk` |
| Versão | `6.25` |
| HEAD local/remoto | `6ae281f` — commit funcional da 6.25 publicado; fechamento documental em andamento |
| Último commit funcional | `ce8dd98` — `feat: observabilidade estruturada com diagnóstico copiável (6.21)` |
| Checkout | Com atualização documental local para registrar o hash publicado |
| Branch principal | Não alterada |
| Suíte completa | 588 aprovados, 4 ignorados |
| Asset BlazeFace | Usado temporariamente para teste, conferido e removido |

## Alterações implementadas

### 1. Release 6.18 — barra de execução contextual

Commit funcional: `276ee87`.

A barra fixa `runBar` foi expandida para mostrar etapa atual, percentual, sequência visual `Fonte → Transcrição → Contexto → Ranking → Cortes`, escopo da fonte, cronômetro e cancelamento. A etapa é inferida pelas mensagens já emitidas pelo job e o percentual usa o progresso persistido existente; não foram criados novos endpoints ou decisões editoriais.

O HTML passou a ter elementos de etapa, progresso acessível, escopo e cinco passos visuais. O CSS recebeu estados `complete`, `active`, `future` e `error`, responsividade para telas estreitas, transições discretas e `prefers-reduced-motion`. O JavaScript passou a manter `processingScopeLabel`, inferir fases, atualizar `aria-valuenow` e preservar o escopo de intervalos como `00:00–05:00`.

Foi criada a regressão `tests/test_ux_runbar.py`, cobrindo markup, progresso acessível, estados visuais, responsividade e redução de movimento. O ciclo foi documentado em `CYCLE_34_REPORT_2026-08-21.md`, `UX_AUDIT_2026-08-21.md`, `UX_RUNBAR_CHECK_2026-08-21.md`, `DECISIONS.md`, `CHANGELOG.md`, `PROJECT_STATE.md` e `NEXT_CYCLE.md`.

A validação inicial terminou com 555 aprovados e 4 ignorados, além de `node --check`, `py_compile` e `git diff --check`. A inspeção visual simulou Transcrição a 42% e Ranking a 78%, com intervalo visível. Nenhum job real de mídia foi iniciado nesta rodada.

### 2. Release 6.19 — cancelamento seguro e feedback honesto

Commit funcional: `315279f`.

Foi corrigida uma corrida entre o cancelamento e o início do worker. Antes, um job que ainda estava na fila podia ser marcado como cancelado e depois iniciar o alvo. Agora o início do worker faz uma reivindicação atômica condicionada ao estado `queued`. Se o cancelamento venceu a corrida, o alvo não é executado e o job termina com `cancelled`, `stage=cancelled` e `error=cancelled_before_start`.

O worker também verifica cancelamento antes de qualquer trabalho do alvo. Jobs que já começaram continuam usando a transição cooperativa `cancel_requested` até uma etapa segura.

A barra superior agora valida a resposta HTTP do cancelamento, evita cliques duplicados, confirma aceitação somente após resposta válida, reabilita o botão em falha, exibe toast e registra a falha no console. A mudança não altera ranking, contexto, Campaign Hub, renderização, gates ou lógica editorial.

Foi adicionada uma regressão em `tests/test_job_manager.py` que cria um job enfileirado, cancela antes do worker e comprova que o alvo nunca é executado. `tests/test_frontend_integrity.py` passou a exigir validação da resposta, mensagem de falha e reabilitação do botão. O ciclo foi documentado em `CYCLE_35_REPORT_2026-08-21.md`, `DECISIONS.md`, `CHANGELOG.md`, `PROJECT_STATE.md` e `NEXT_CYCLE.md`.

A validação focada terminou com 28 aprovados. A suíte completa terminou com 557 aprovados e 4 ignorados após o asset BlazeFace ser provisionado temporariamente, conferido pelo SHA-256 conhecido e removido. A execução completa também passou por `node --check`, `python3 -m py_compile app.py` e `git diff --check`.

### 3. Release 6.20 — pacote amplo de inteligência editorial

Commit funcional: `6d88714`.

A 6.20 implementou identidade determinística de intervalo, assinatura da fonte, faixa absoluta, digest da transcrição e proveniência em projeto, banco, transcrição, bundles, diagnósticos e payloads finais. A identidade não depende do caminho temporário e separa faixas diferentes da mesma live sem reativar a colisão legada.

O contexto editorial agora expõe `context-contract-v1`, com setup, anáfora, pergunta, resposta/tese, payoff, evidências, score de completude e motivos de revisão. O seletor recebe esse contrato, e os dossiês de candidatos o preservam para a revisão da próxima IA.

O gate de locutor foi aplicado também depois da anotação de voz e antes do render nas rotas smart cut e processo completo. Voz confirmadamente incompatível não é renderizada como Renan-first; voz inconclusiva permanece em revisão. O relatório `headline-fidelity-v1` registra grounding lexical e citações verificadas sem confundir overlap com verdade factual.

Foram criadas regressões em `tests/test_interval_identity.py` e `tests/test_context_contract.py`. A primeira suíte completa revelou cinco incompatibilidades de monkeypatch legadas no fingerprint; um fallback explícito foi adicionado e a execução final terminou com **563 aprovados e 4 ignorados**. Também passaram `py_compile`, `node --check` e `git diff --check`; o BlazeFace foi temporário e removido.

O ciclo está documentado em `CYCLE_36_REPORT_2026-08-21.md`, `PROJECT_STATE.md`, `NEXT_CYCLE.md`, `DECISIONS.md` e `CHANGELOG.md`.

### 4. Release 6.21 — observabilidade estruturada e diagnóstico copiável

A 6.21 não altera ranking, pesos Chub, gates Renan-first, contexto editorial ou renderização. Ela resolve a lacuna operacional de não conseguir explicar um erro somente a partir do console visível.

`modules/job_manager.py` cria `job_events` com índice por job e sequência, registra `job.created`, persiste atualizações e breadcrumbs, limita detalhes, aplica retenção configurável e fornece `events()`/`diagnostic()`. `JobContext.note()` registra mensagens sem mudar o estado do job. A sequência é protegida por `BEGIN IMMEDIATE` e jobs inexistentes produzem `KeyError` no registro ou `None` na leitura.

`app.py` expõe `/api/jobs/<job_id>/events` e `/api/jobs/<job_id>/diagnostic`, mantendo `/diagnostics` como alias. `emit_progress()` carrega versão, revisão, evento, etapa, detalhes seguros e correlação opcional; quando há job persistido, o evento também é salvo.

`static/js/app.js` mantém `consoleHistory`, adiciona `consoleEvents`, captura `window.error` e `unhandledrejection`, busca o diagnóstico terminal automaticamente e copia um objeto `ui-diagnostic-v1`. `templates/index.html` renomeia o botão para **Copiar diagnóstico**. Regressões novas cobrem JobManager, rotas HTTP, retenção, `note()`, privacidade estrutural e integridade do frontend.

A validação final da rodada 6.21 terminou com **573 aprovados e 4 ignorados**, além de `py_compile`, `node --check` e `git diff --check`. O modelo BlazeFace foi baixado apenas para a suíte, conferido pelo hash conhecido e removido. O relatório completo está em [`CYCLE_37_REPORT_2026-08-21.md`](CYCLE_37_REPORT_2026-08-21.md).

### 5. Release 6.22 — pesquisa MCP/Chub e ancoragem textual

O ciclo 38 auditou a fundação local de Campaign Hub, a memória offline, o guidance, o benchmark e as capacidades read-only do MCP. A conclusão foi que o MCP deve ser usado como fronteira de aquisição/evidência e não como chamada por candidato. Um futuro sync deve buscar dados paginados, sanitizar, hashear e instalar um snapshot local atômico; o job de corte continua usando uma versão congelada.

A implementação adicionou `ClipSelector._find_seed_text_anchor()`. Quando a seed Chub não sobrepõe a timeline local, o método procura até três frases com normalização Unicode, cobertura lexical mínima `0.55` e score mínimo `0.62`. A proposta preserva a proveniência e recebe `alignment_method=text_anchor`, `alignment_evidence` e `alignment_gate=review_required`. Sem correspondência suficiente, nenhuma frase distante é inventada como destino.

As fichas de discovery Chub agora carregam seed, bloco, highlight, resumo, pergunta, tópicos, ranks, tier, riscos, gates e evidência textual em limites seguros. Foram adicionadas regressões de recuperação válida, rejeição de falso alinhamento e diagnóstico explicável. A suíte completa da 6.22 terminou com **576 aprovados e 4 ignorados**; o BlazeFace foi temporário e removido. Relatório em [`CYCLE_38_REPORT_2026-08-21.md`](CYCLE_38_REPORT_2026-08-21.md), pesquisa em [`RESEARCH_MCP_CHUB_2026-08-21.md`](RESEARCH_MCP_CHUB_2026-08-21.md) e desenho em [`CYCLE_38_DESIGN_MCP_CHUB_2026-08-21.md`](CYCLE_38_DESIGN_MCP_CHUB_2026-08-21.md).

A 6.22 **ainda não prova ganho de recall em live real**, não implementa cliente MCP remoto no Furia e não altera pesos do ranking. O commit funcional `6dabc14` está publicado; o próximo ciclo deve executar uma faixa curta pela interface, copiar `ui-diagnostic-v1` e comparar baseline temporal versus `text_anchor` em benchmark reproduzível.

O que ainda não foi confirmado é a cobertura em uma operação real: executar uma faixa curta, copiar o diagnóstico e verificar se ingestão, transcrição, contexto, ranking, render, fallback e cancelamento aparecem sem pedir arquivos auxiliares. Também será necessária uma auditoria de mensagens legadas que possam conter pequenos previews de texto.

### 6. Release 6.23 — precisão de bordas e elegibilidade editorial

A 6.23 consolidou pesquisa de avaliação audiovisual fina, edição narrativa, OpusClip, Vizard, Descript, WhisperX, PySceneDetect e pairwise ranking. A decisão arquitetural é manter um núcleo genérico de seleção, narrativa, borda, locutor, ranking e formato, aprofundado por um perfil Renan/MBL com vocabulário, contas, fontes, gates, famílias editoriais e priors limitados.

`modules/clip_selector.py` passou a aproveitar timestamps `start/end/word` já presentes na transcrição canônica. `_refine_boundaries_with_words()` exige três palavras, cobertura lexical mínima `0.55`, deslocamento máximo de três segundos por borda e duração dentro dos limites; sem cobertura suficiente, preserva a janela e registra `word_boundary_refinement` para revisão.

`modules/editorial_ranker.py` passou a expor um ledger separado do score, com `eligibility_status=ready|review|blocked`, `hard_blockers`, `review_items` e `publishable_without_review`. O score legado e a ordem dos candidatos não mudaram, e nenhum candidato foi removido pela camada. A finalidade é separar “melhor pontuação” de “pronto para publicar”.

Foram adicionadas regressões para refinamento por palavra e para os três estados de elegibilidade. A validação focada terminou com 32 aprovados; a suíte completa da 6.23 terminou com **582 aprovados e 4 ignorados**. O BlazeFace foi temporário e removido. Relatório em [`CYCLE_39_REPORT_2026-08-21.md`](CYCLE_39_REPORT_2026-08-21.md), auditoria em [`AUDIT_CUTTING_PRECISION_CYCLE39_2026-08-21.md`](AUDIT_CUTTING_PRECISION_CYCLE39_2026-08-21.md) e próximo ciclo em [`NEXT_CYCLE.md`](NEXT_CYCLE.md).

A 6.23 não prova ganho editorial em live real, não habilita timestamps por palavra automaticamente e não altera pesos. O próximo ciclo deve construir hard negatives, medir erro de borda e testar se o ledger reduz falsos aprovados/revisões demoradas.

### 7. Release 6.24 — hard negatives e timestamps por palavra por padrão

A 6.24 adicionou `hard_negatives` a `candidate_diagnostics`. O seletor preserva no máximo 80 near-misses por execução e conta o total observado. Cada item mantém intervalo, duração, origem, score, confiança, preview textual curto, motivo e vencedor quando aplicável. Foram instrumentados descartes por fingerprint já exportado, duplicata temporal/lexical e irmão contíguo. O ledger é diagnóstico-only e não muda sobreviventes, score, gates Chub ou aprovação.

`config.DEFAULT_SETTINGS["whisper_word_timestamps"]` passou a `True`. O usuário ainda pode desligar a opção para uma máquina de poucos recursos, mas o padrão editorial passa a coletar a evidência necessária ao refinamento de bordas da 6.23.

Foram adicionadas regressões em `tests/test_candidate_volume_diagnostics.py` e `tests/test_editing_scope.py`. A suíte focada terminou com 46 aprovados; a suíte completa terminou com **585 aprovados e 4 ignorados**. O BlazeFace foi temporário e removido. Relatório em [`CYCLE_40_REPORT_2026-08-21.md`](CYCLE_40_REPORT_2026-08-21.md) e próximo ciclo em [`NEXT_CYCLE.md`](NEXT_CYCLE.md).

A 6.24 não prova ganho editorial em mídia real e não altera pesos. A integração Instagram está habilitada, mas a API retornou 403 por falta de permissão da aplicação; nenhum perfil foi usado nesta rodada.

### 8. Release 6.25 — benchmark hard-negative-v1 integrado ao diagnóstico

A 6.25 criou `build_hard_negative_benchmark()` em `modules/editorial_benchmark.py`. O contrato `hard-negative-v1` normaliza o ledger do seletor, preserva identidade de processamento e digest da transcrição, limita previews/detalhes e aceita somente `approved`, `rejected`, `needs_review` e `unlabeled`. Itens não rotulados permanecem descritivos; o payload declara `measurement_status=descriptive_only`.

`app._write_selection_diagnostics()` agora salva um benchmark separado em `FuriaClipsData/benchmarks/` quando há hard negatives e adiciona ao relatório principal somente um manifesto com schema, ID, contagem e nome do arquivo. O comportamento de execuções sem near-misses não muda. O benchmark `b354-v1`, o ranking e os gates Chub permanecem compatíveis.

Foram adicionadas regressões em `tests/test_editorial_benchmark.py` e `tests/test_diagnostics_detail.py`. A validação focada terminou com 51 aprovados; a suíte completa terminou com **588 aprovados e 4 ignorados**. Relatório em [`CYCLE_41_REPORT_2026-08-21.md`](CYCLE_41_REPORT_2026-08-21.md), pesquisa atualizada em [`RESEARCH_CUTTING_PRECISION_2026-08-21.md`](RESEARCH_CUTTING_PRECISION_2026-08-21.md) e próxima hipótese em [`NEXT_CYCLE.md`](NEXT_CYCLE.md).

A 6.25 não prova ganho editorial em mídia real e não altera pesos. A API do Instagram retornou 403 por falta de permissão da aplicação; nenhum perfil foi usado nesta rodada.

### 9. Fechamentos documentais

Os commits `32b2c53` e `94b8c56` fecharam `PROJECT_STATE.md` com os hashes reais publicados de 6.18 e 6.19. O commit `6d88714` publicou a implementação funcional da 6.20. O commit `ce8dd98` publicou a implementação funcional da 6.21 e `042df18` publicou o fechamento documental, ambos na branch de trabalho remota. O commit `6dabc14` publicou a implementação funcional da 6.22 na mesma branch. O commit `ee2cc6d` publicou a implementação funcional da 6.23, seguido pelos fechamentos `7950346`, `c91cd52` e `41e52c3`. A 6.24 foi publicada no commit funcional `08d8429` e fechada em `b1af379`. A 6.25 foi publicada no commit funcional `6ae281f`; este fechamento documental ainda será publicado.

## O que não foi alterado

Não houve alteração nos pesos principais do ranking, no filtro Renan-first, na promoção automática do Campaign Hub, na ingestão autenticada ou nas integrações remotas da fase final. A 6.20 adicionou contratos de proveniência, contexto, locutor e headline, mas preservou os fallbacks. Também não foram adicionados MP4, WAV, SRT, banco SQLite, cookies, tokens, credenciais, snapshots reais do Campaign Hub ou modelo BlazeFace ao Git.

Nenhuma live foi baixada, ouvida ou processada nesta retomada. As validações audiovisuais recentes foram visuais/simuladas e baseadas em testes e fixtures locais. Portanto, nenhum ganho novo de recall editorial deve ser reivindicado por causa das releases 6.18 ou 6.19.

## Constatações técnicas atuais

O Furia já possui base funcional para receber arquivo, importar URL quando o provedor permite, transcrever, selecionar, ranquear, renderizar, processar intervalos e revisar resultados. O Campaign Hub já funciona como memória/seed e seus diagnósticos distinguem descoberta, promoção, filtro por locutor e candidatos finais.

A principal lacuna editorial continua sendo provar que a especialização Renan-first melhora a precisão e o contexto em fontes longas reais. A identidade persistente de intervalo e a proveniência agora existem; a próxima lacuna é usá-las em um benchmark editorial por faixa, transcript e formato. A principal lacuna de produto continua sendo transformar o fluxo em missões completas com fila, dossiê, pesquisa recente e entrega remota sem quebrar o núcleo local.

## Novo norte de plataforma

Foi criado [`FUTURE_PLATFORM_2026-08-21.md`](FUTURE_PLATFORM_2026-08-21.md). Ele registra o futuro da ferramenta como fase final posterior ao fortalecimento do motor de cortes, com ideias de memória editorial, pesquisa/evidência, orquestração, experiência e aprendizado editorial. O norte imediato continua sendo o núcleo de cortes e a integração Chub/MBL.

O documento inclui ideias para Context Composer, rede de janelas, ranking em três passagens, lint audiovisual, dossiês com afirmações rastreáveis, pesquisa de última hora, GDELT, fontes primárias, watchlists, briefings, fila de revisão, feedback de rejeições, reprocessamento seletivo, botões remotos, notificações de smartwatch, control plane e worker local.

As integrações remotas foram pesquisadas nas documentações oficiais. WhatsApp Cloud API é viável, mas exige Meta Business, número, token seguro, webhook, opt-in e atenção à janela de atendimento. Telegram oferece uma primeira prova de conceito mais simples com API HTTP, webhook secreto e botões inline. Wear OS deve começar como camada de notificações do telefone, não como app nativo de relógio.

GDELT foi registrado como fonte de descoberta recente de artigos, temas, idiomas e imagens, com atualizações informadas de 15 minutos, mas sempre como evidência de descoberta e não como prova única. O dossiê deve separar descoberto, corroborado, não confirmado e contradito.

## Próxima sequência recomendada

1. Executar uma faixa curta pela interface, copiar o diagnóstico `ui-diagnostic-v1` e auditar cobertura, correlação e privacidade.
2. Materializar benchmark editorial por fonte, faixa, transcript, formato e decisão humana usando a identidade 6.20.

3. Medir recall temporal, IoU de borda, precisão@k, contexto, payoff, locutor, headline, diversidade e qualidade técnica separadamente.
4. Auditar o contrato de transcrição manual usando o novo `input_kind`, digest e cobertura persistidos.
5. Usar o benchmark para calibrar recall-first Chub e bordas, sem alterar pesos antes da comparação.
6. Transformar aprovação/rejeição em feedback estruturado e comparações pairwise.
7. Adicionar lint audiovisual e checklist antes da exportação.
8. Só depois retomar dossiê por demanda, pesquisa recente e fontes primárias substituíveis.
9. Escolher um canal remoto; Telegram é a primeira prova técnica mais leve, WhatsApp é uma integração posterior de produção.
10. Criar control plane remoto e worker local somente depois de definir autenticação, computador ligado e armazenamento de artefatos.
11. Manter automações remotas na fase final futura.

## Arquivos para a próxima IA

Ler primeiro `START_HERE.md`, `PROJECT_STATE.md`, este relatório, `CYCLE_38_REPORT_2026-08-21.md`, `CYCLE_38_DESIGN_MCP_CHUB_2026-08-21.md`, `RESEARCH_MCP_CHUB_2026-08-21.md`, `CYCLE_37_REPORT_2026-08-21.md`, `CYCLE_36_REPORT_2026-08-21.md`, `CUTTING_AUDIT_2026-08-21.md`, `CUTTING_PRECISION_PLAN_2026-08-21.md`, `FUTURE_PLATFORM_2026-08-21.md`, `NEXT_CYCLE.md`, `DECISIONS.md`, `modules/job_manager.py`, `modules/clip_selector.py`, `app.py`, `static/js/app.js`, `tests/test_job_manager.py`, `tests/test_campaign_hub_guidance.py`, `tests/test_app_smoke.py` e `IDEAS_BACKLOG.md`. Confirmar a branch antes de editar e manter a branch principal intocada.
