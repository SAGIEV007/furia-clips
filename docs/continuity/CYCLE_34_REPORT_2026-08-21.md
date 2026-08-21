# Ciclo 34 — Barra de execução contextual e feedback visual do job

## Objetivo

Concentrar a rodada exclusivamente em UX e design, seguindo o norte visual do branch `manus/rebuild-opus-parity-2`, sem alterar ranking, contexto, Campaign Hub, gates Renan-first, transcrição, renderização ou contratos de backend.

## Hipótese única

> Se a barra fixa de execução mostrar etapa, progresso percentual, sequência do pipeline e escopo da fonte, o editor poderá entender o estado de uma operação longa sem abrir o console ou rolar até o painel inferior.

A hipótese foi escolhida porque a 6.17 já tinha uma barra com título, mensagem, cronômetro e cancelamento, além de um fluxo de etapas dentro do console. A informação existia, mas estava dividida entre dois locais e exigia interpretação manual durante processamento longo.

## O que foi implementado

### Barra fixa de execução

O componente `runBar` agora apresenta uma hierarquia visual compacta com título da operação, badge da etapa atual, mensagem contextual, barra de progresso percentual, escopo da fonte e cronômetro. O escopo pode mostrar `Fonte inteira` ou a faixa escolhida, como `00:00–05:00`.

A sequência visual fixa contém cinco estados: `Fonte`, `Transcrição`, `Contexto`, `Ranking` e `Cortes`. A etapa anterior fica visualmente concluída, a atual fica ativa e as próximas permanecem neutras. Em caso de erro, o estado atual possui uma classe semântica própria para feedback visual.

### Integração somente com sinais existentes

O JavaScript infere a etapa a partir das mensagens que o job já emitia e usa o `job.progress` já fornecido pelo backend. Não foram criados novos pesos, chamadas, endpoints ou decisões editoriais. O botão de cancelamento continua usando o mesmo fluxo seguro existente.

O rótulo do intervalo é guardado no estado do frontend no momento em que o editor envia a execução. Se o job já trouxer `processing_interval`, a barra usa esse valor; caso contrário, preserva `Fonte inteira` como fallback.

### Visual e acessibilidade

O CSS segue a linguagem existente e o norte visual consultado: painel escuro com dourado como estado ativo, badges compactos, contraste semântico, transições discretas, layout responsivo abaixo de 620px e respeito a `prefers-reduced-motion`.

A barra de progresso usa `role=progressbar`, `aria-valuemin`, `aria-valuemax` e `aria-valuenow`. O container mantém `role=status` e `aria-live=polite`. A alteração não esconde o cancelamento nem substitui o console detalhado.

## Validação

A aplicação 6.17 foi aberta localmente e um servidor antigo da 6.16 foi identificado e encerrado antes da inspeção correta. A 6.17 foi confirmada no cabeçalho, console e revisão `085569f`.

Sem iniciar qualquer job real, o navegador simulou um estado de `Corte inteligente`, etapa `Transcrição`, progresso `42%` e faixa `00:00–05:00`. Depois simulou `Ranking` a `78%`. A verificação DOM confirmou os estados concluídos, ativo e futuro, além de `aria-valuenow` correto. As capturas visuais mostraram a barra acima do workflow editorial, sem sobreposição e com o escopo legível.

| Validação | Resultado |
| --- | ---: |
| Regressões do contrato UX | **3 aprovadas** |
| Testes focados UX, runtime, intervalos e API | **37 aprovados** |
| Suíte completa com BlazeFace temporário | **555 aprovados, 4 ignorados** |
| `node --check static/js/app.js` | Aprovado |
| `python3 -m py_compile` | Aprovado |
| `git diff --check` | Aprovado |
| Console do navegador | Sem erro observado nas simulações |
| Job real iniciado | Não; validação visual foi deliberadamente read-only |

A primeira execução da suíte completa encontrou somente a ausência ambiental do asset BlazeFace. O asset foi baixado da URL e SHA-256 já documentados, a suíte foi repetida com sucesso e o arquivo foi removido antes do commit.

## Constatações confirmadas

A barra fixa consegue concentrar as informações essenciais do job sem substituir o console. O editor visualiza a faixa da fonte e a fase atual antes de precisar consultar detalhes técnicos.

A nova camada visual reutiliza sinais já existentes no backend, portanto não altera o ranking nem introduz divergência entre o estado exibido e o job persistente. O progresso é o mesmo percentual que já era usado na barra inferior.

O norte visual do branch de referência foi aplicado de forma incremental. A 6.17 já possuía badges de proveniência, avisos de volume, central de revisão e métricas recolhíveis; o ciclo 34 não duplicou esses elementos e concentrou o ganho na operação em andamento.

## Limitações e pontos não comprovados

A verificação do ciclo não processou uma live real. A barra foi testada com simulação controlada no navegador, porque o objetivo desta rodada era validar a camada visual sem consumir uma fonte longa nem alterar evidências editoriais.

O servidor local foi iniciado apenas para inspeção e deve ser encerrado ao final da rodada. A barra ainda depende das mensagens textuais do job para inferir a etapa; uma futura evolução poderá expor uma fase estruturada no payload, mas isso seria uma hipótese de contrato operacional e não faz parte deste ciclo visual.

## Arquivos alterados

- `templates/index.html`: markup da barra contextual.
- `static/js/app.js`: estado, inferência de etapa, progresso, escopo e atualização dos badges.
- `static/css/style.css`: painel, barra, badges, estados, responsividade e redução de movimento.
- `tests/test_ux_runbar.py`: regressões estáticas do contrato visual.
- `docs/continuity/UX_AUDIT_2026-08-21.md`: auditoria inicial e hipótese.
- `docs/continuity/UX_RUNBAR_CHECK_2026-08-21.md`: verificação DOM e visual.

## Retomada futura

A próxima IA deve ler este relatório, `PROJECT_STATE.md`, `NEXT_CYCLE.md`, `DECISIONS.md`, `CYCLE_33_REPORT_2026-08-20.md` e `REFERENCE_UX_NOTES_2026-08-20.md`. Deve confirmar a branch `claude/repo-access-commits-imgjmk`, não tocar a branch principal e não adicionar vídeos, transcrições, bancos, cookies ou credenciais.

Depois desta release visual, pode ser retomada a hipótese técnica já documentada no ciclo 33: persistir uma identidade de intervalo no banco e na trilha editorial para deduplicar a mesma faixa sem bloquear faixas diferentes. A visualização read-only da descoberta Chub continua posterior. Não alterar ranking ou gates nesta retomada.
