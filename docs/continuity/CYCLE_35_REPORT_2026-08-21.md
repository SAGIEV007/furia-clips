# Ciclo 35 — Cancelamento seguro e feedback honesto do job

## Objetivo

Executar uma melhoria autônoma de estabilidade sem depender de navegador, credenciais, mídia externa ou autorização manual. O ciclo ficou restrito ao contrato de jobs e ao feedback visual de cancelamento; ranking, contexto, Campaign Hub, gates Renan-first, transcrição e renderização permaneceram fora do escopo.

## Hipótese única

> Se o cancelamento for tratado como uma transição segura tanto enquanto o job aguarda na fila quanto depois que o worker começou, e se a barra superior validar a resposta do servidor, o editor não verá um falso “cancelado” nem ficará esperando indefinidamente por um job que ainda nem iniciou.

## Problema reproduzido por inspeção

O `JobManager` marcava um job em execução como `cancel_requested`, mas a transição inicial do worker era um `UPDATE` direto para `running`. Existia uma janela em que a solicitação de cancelamento podia vencer enquanto o `Future` ainda estava na fila; nesse caso, o worker poderia começar o alvo depois de a interface já ter informado que a operação estava sendo cancelada.

A barra superior também disparava a solicitação sem verificar a resposta HTTP. Um erro de rota, job inexistente ou conflito de estado poderia deixar a interface mostrando que o cancelamento havia sido pedido, embora o servidor tivesse recusado a operação.

## Implementação

### Claim atômico do worker

O início do worker agora reivindica a linha com `UPDATE ... WHERE state = 'queued'`. Se a atualização não afetar exatamente uma linha, o worker não executa o alvo. Quando a linha está em `cancel_requested`, o gerenciador finaliza o job como `cancelled` com o erro sanitizado `cancelled_before_start`.

Depois da reivindicação, `JobContext.check_cancel()` é chamado antes de qualquer trabalho do alvo. Assim, uma solicitação que chega imediatamente após a transição para `running` também é respeitada antes de FFmpeg, Whisper ou outro processamento começar.

### Cancelamento imediato na fila

`request_cancel()` agora transforma diretamente um job `queued` em `cancelled`, porque nenhum trabalho do alvo foi iniciado nesse estado. Jobs `running` continuam passando por `cancel_requested` e só terminam quando o worker alcança uma etapa segura, preservando o comportamento anterior para processamento já iniciado.

### Barra superior honesta

O botão `runBarCancel` passou a desabilitar-se durante a solicitação, interpretar a resposta com o mesmo parser usado pelo restante da interface, exibir a confirmação somente depois de uma resposta válida e reabilitar-se quando o servidor recusar a operação. Falhas também entram no console e aparecem como toast de erro.

## Validação

A regressão nova cria um job enfileirado, solicita o cancelamento antes do worker e confirma estado terminal imediato, erro sanitizado e alvo nunca executado. Os testes existentes de cancelamento durante execução continuam aprovados.

| Validação | Resultado |
| --- | ---: |
| Testes focados de jobs, cancelamento, frontend e barra | **28 aprovados** |
| Suíte completa com BlazeFace temporário | **557 aprovados, 4 ignorados** |
| `node --check static/js/app.js` | Aprovado |
| `python3 -m py_compile app.py` | Aprovado |
| `git diff --check` | Aprovado |
| Asset BlazeFace no checkout após os testes | Ausente; removido após a suíte |
| Job real de mídia | Não iniciado; a hipótese é reproduzível em SQLite e testes locais |

A execução sem o asset apresentou a falha ambiental esperada em `test_face_model_manifest_and_asset_are_consistent`; a suíte foi repetida com o asset baixado, SHA-256 conferido e arquivo removido, terminando com 557 aprovados e 4 ignorados.

## Limitações

A correção não interrompe um processo externo que não chama `check_cancel()` durante uma etapa longa; ela impede o início indevido e mantém o cancelamento cooperativo já existente. A comprovação de tempo de resposta em uma fila real de renderização permanece não medida neste sandbox.

O ciclo não altera a política de deduplicação entre faixas. A hipótese de identidade persistente para intervalos continua sendo a próxima melhoria técnica, conforme `NEXT_CYCLE.md`.

## Arquivos alterados

- `modules/job_manager.py`: claim atômico, cancelamento terminal de jobs enfileirados e guarda antes do alvo.
- `static/js/app.js`: validação da resposta do cancelamento da barra superior, feedback de falha e proteção contra cliques duplicados.
- `tests/test_job_manager.py`: regressão de cancelamento antes do início.
- `tests/test_frontend_integrity.py`: regressão de resposta HTTP, reabilitação e mensagem de erro da barra.
- `VERSION`: versão pública 6.19.

## Retomada

A próxima IA deve confirmar a branch `claude/repo-access-commits-imgjmk`, ler este relatório, `PROJECT_STATE.md`, `NEXT_CYCLE.md` e `DECISIONS.md`, e não adicionar mídia, banco, cookies, tokens ou credenciais ao Git. O próximo ciclo pode implementar a identidade persistente de intervalo somente se conseguir preservar o comportamento da fonte inteira e provar que faixas distintas da mesma live não colidem.
