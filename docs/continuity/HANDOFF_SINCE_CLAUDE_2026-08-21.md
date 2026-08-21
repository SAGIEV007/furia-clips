# Relatório de continuidade desde a retomada do Claude

## Escopo do relatório

Este documento registra tudo que foi alterado depois do ponto de retomada identificado no commit `085569f`, na branch isolada `claude/repo-access-commits-imgjmk`. Ele separa implementação efetiva, validação, limitações, decisões e propostas do novo norte de plataforma. O relatório não afirma que uma ideia foi implementada apenas porque foi desenhada.

## Estado atual

| Campo | Estado confirmado |
| --- | --- |
| Repositório | `SAGIEV007/furia-clips` |
| Branch | `claude/repo-access-commits-imgjmk` |
| Versão | `6.19` |
| HEAD local/remoto | `94b8c56` |
| Último commit funcional | `315279f` |
| Checkout | Limpo e sincronizado |
| Branch principal | Não alterada |
| Suíte completa | 557 aprovados, 4 ignorados |
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

### 3. Fechamentos documentais

Os commits `32b2c53` e `94b8c56` fecharam `PROJECT_STATE.md` com os hashes reais publicados de 6.18 e 6.19. O estado local e remoto apontam para `94b8c56`.

## O que não foi alterado

Não houve alteração em pesos do ranking, gates de locutor, filtro Renan-first, integração editorial do Campaign Hub, contexto de candidatos, transcrição, renderização, ingestão autenticada, banco de dados editorial ou lógica de headlines. Também não foram adicionados MP4, WAV, SRT, banco SQLite, cookies, tokens, credenciais, snapshots reais do Campaign Hub ou modelo BlazeFace ao Git.

Nenhuma live foi baixada, ouvida ou processada nesta retomada. As validações audiovisuais recentes foram visuais/simuladas e baseadas em testes e fixtures locais. Portanto, nenhum ganho novo de recall editorial deve ser reivindicado por causa das releases 6.18 ou 6.19.

## Constatações técnicas atuais

O Furia já possui base funcional para receber arquivo, importar URL quando o provedor permite, transcrever, selecionar, ranquear, renderizar, processar intervalos e revisar resultados. O Campaign Hub já funciona como memória/seed e seus diagnósticos distinguem descoberta, promoção, filtro por locutor e candidatos finais.

A principal lacuna editorial continua sendo provar que a especialização Renan-first melhora a precisão e o contexto em fontes longas reais. A principal lacuna operacional futura é a identidade persistente de intervalo. A principal lacuna de produto é transformar o fluxo em missões completas com fila, dossiê, pesquisa recente e entrega remota sem quebrar o núcleo local.

## Novo norte de plataforma

Foi criado [`PLATFORM_NORTH_2026-08-21.md`](PLATFORM_NORTH_2026-08-21.md). Ele define a Furia como plataforma automatizada de mídia e inteligência, com cortes como núcleo, e organiza as ideias em seis camadas: motor de mídia, memória editorial, pesquisa/evidência, orquestração, experiência e aprendizado editorial.

O documento inclui ideias para Context Composer, rede de janelas, ranking em três passagens, lint audiovisual, dossiês com afirmações rastreáveis, pesquisa de última hora, GDELT, fontes primárias, watchlists, briefings, fila de revisão, feedback de rejeições, reprocessamento seletivo, botões remotos, notificações de smartwatch, control plane e worker local.

As integrações remotas foram pesquisadas nas documentações oficiais. WhatsApp Cloud API é viável, mas exige Meta Business, número, token seguro, webhook, opt-in e atenção à janela de atendimento. Telegram oferece uma primeira prova de conceito mais simples com API HTTP, webhook secreto e botões inline. Wear OS deve começar como camada de notificações do telefone, não como app nativo de relógio.

GDELT foi registrado como fonte de descoberta recente de artigos, temas, idiomas e imagens, com atualizações informadas de 15 minutos, mas sempre como evidência de descoberta e não como prova única. O dossiê deve separar descoberto, corroborado, não confirmado e contradito.

## Próxima sequência recomendada

1. Implementar identidade persistente de intervalo e regressões para mesma faixa, faixas diferentes e fonte inteira.
2. Auditar o contrato de transcrição manual para impedir substituição silenciosa por Whisper/Gemini.
3. Criar o Context Composer com limites de tokens e contexto temporal compacto.
4. Adicionar lint audiovisual e checklist antes da exportação.
5. Transformar aprovação/rejeição em feedback estruturado.
6. Criar dossiê por demanda com fontes, timeline e afirmações rastreáveis.
7. Implementar descoberta recente com GDELT e fontes primárias substituíveis.
8. Escolher um canal remoto; Telegram é a primeira prova técnica mais leve, WhatsApp é uma integração posterior de produção.
9. Criar control plane remoto e worker local somente depois de definir autenticação, computador ligado e armazenamento de artefatos.
10. Reexecutar benchmark audiovisual real antes de alterar pesos editoriais.

## Arquivos para a próxima IA

Ler primeiro `START_HERE.md`, `PROJECT_STATE.md`, este relatório, `PLATFORM_NORTH_2026-08-21.md`, `NEXT_CYCLE.md`, `DECISIONS.md`, `CYCLE_35_REPORT_2026-08-21.md`, `CYCLE_34_REPORT_2026-08-21.md` e `IDEAS_BACKLOG.md`. Confirmar a branch antes de editar e manter a branch principal intocada.
