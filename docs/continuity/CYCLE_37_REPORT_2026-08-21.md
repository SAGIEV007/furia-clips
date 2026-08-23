# Relatório do ciclo 37 — Observabilidade estruturada e diagnóstico copiável

## Identificação

| Campo | Valor |
| --- | --- |
| Projeto | Furia Clips |
| Release alvo | `6.21` |
| Branch | `claude/repo-access-commits-imgjmk` |
| Escopo | Observabilidade de jobs, console e diagnóstico local |
| Escopo explicitamente excluído | Ranking, pesos Chub, gates Renan-first, contrato editorial de cortes e renderização |
| Status | Implementação funcional publicada em `ce8dd98`; fechamento documental publicado em `042df18` |

## Hipótese única

> Se cada job persistir eventos estruturados correlacionados por `job_id`, e a interface puder reunir esses eventos com o console textual e o estado terminal do job, então uma falha poderá ser diagnosticada a partir de um único resumo copiável, sem solicitar repetidamente pastas, transcrições integrais, mídia ou credenciais ao editor.

A hipótese foi testada sem alterar o motor editorial. A camada de observabilidade passou a existir no banco local e na interface, mas a utilidade durante uma execução real do usuário ainda precisa ser observada após a publicação.

## Implementação

O `JobManager` agora cria a tabela `job_events`, com índice por `job_id` e sequência, e registra um evento inicial para cada job. `record_event()` usa transação `BEGIN IMMEDIATE` para evitar colisões de sequência entre threads, limita o tamanho e a profundidade dos detalhes, e aplica retenção configurável. `events()` devolve o histórico em ordem cronológica e distingue um job inexistente de um job sem eventos. `diagnostic()` reúne estado do job, eventos e os últimos breadcrumbs.

`JobContext.note()` permite registrar progresso, decisões, fallback e avisos sem modificar o estado visível do job. `JobContext.update()` e `JobManager.update()` aceitam `event_name`, `level` e `details`. A emissão legada de progresso agora carrega versão, revisão, `job_id` quando disponível, `event_id`, sequência, nome do evento, etapa e detalhes seguros; quando há correlação com um job persistido, o mesmo breadcrumb é gravado no SQLite.

O backend expõe `GET /api/jobs/<job_id>/events` e `GET /api/jobs/<job_id>/diagnostic`. O plural `/diagnostics` permanece como alias compatível. A resposta inclui versão e revisão do checkout e declara o contrato de privacidade.

A interface mantém o console textual, mas também guarda eventos estruturados em `state.consoleEvents`. O botão antes chamado “Copiar log” agora aparece como **“Copiar diagnóstico”** e copia um objeto `ui-diagnostic-v1` com linhas do console, eventos estruturados, diagnóstico persistido do job ativo e nota de privacidade. O frontend também captura `window.error` e `unhandledrejection` sem substituir o console existente.

## Contrato de privacidade

Os eventos não registram chaves de API, cookies, headers sensíveis, mídia ou transcrição integral. Os detalhes passam por normalização com limite de 32 chaves, strings curtas, listas truncadas e objetos achatados. Mensagens de erro também são limitadas. A interface não consulta nem copia conteúdo de vídeo; ela copia metadados operacionais, mensagens de diagnóstico e breadcrumbs.

A proteção é deliberadamente conservadora, mas ainda há uma limitação: mensagens legadas de progresso podem conter pequenos previews produzidos por módulos existentes. Elas não são transcrições completas, porém a próxima rodada deverá auditar e classificar esses previews por origem antes de transformar a observabilidade em um contrato de privacidade mais estrito.

## Validação

A sintaxe passou em `app.py`, `modules/job_manager.py`, testes Python e `static/js/app.js`. As regressões focadas terminaram com **56 aprovados**. A suíte completa, com o modelo BlazeFace temporário provisionado e depois removido, terminou com **573 aprovados e 4 ignorados**. `git diff --check` passou.

As regressões cobrem criação e sequência de eventos, diagnóstico correlacionado, `JobContext.note()`, limites de detalhes, migração de banco legado, retenção dos eventos mais recentes, job inexistente, endpoints HTTP e integridade do botão/captura de erros no frontend.

O asset BlazeFace não foi mantido no checkout. Não foram adicionados MP4, WAV, SRT, bancos de execução, chaves ou cookies.

## O que foi confirmado

| Classificação | Constatação |
| --- | --- |
| Confirmado | `job_manager.py` compila e `submit()` permanece distinto de `update()`. |
| Confirmado | Eventos têm `event_id`, `job_id`, sequência, etapa, nível, mensagem, detalhes e timestamp. |
| Confirmado | Retenção e limites de payload funcionam em regressões isoladas. |
| Confirmado | As duas rotas HTTP retornam histórico/diagnóstico e 404 para job inexistente. |
| Confirmado | O frontend mantém console textual e captura erros globais sem depender de um servidor remoto. |
| Confirmado | A suíte completa terminou com 573 aprovados e 4 ignorados. |
| Não verificado | A utilidade do diagnóstico em uma execução real de download, transcrição, contexto e renderização. |
| Não verificado | Se todas as mensagens legadas de progresso estarão correlacionadas a um job em cada caminho de produção. |
| Bloqueado | Qualquer avaliação editorial nova; este ciclo não alterou ranking, Chub ou gates. |

## Próximo passo recomendado

Após publicar a release, executar uma operação curta e segura — preferencialmente uma faixa parcial de fonte já disponível — e copiar o diagnóstico pela interface. O próximo ciclo deve verificar se o resumo contém o caminho completo de ingestão, transcrição, contexto, seleção, renderização, fallback, cancelamento e erro sem exigir arquivos auxiliares. Só depois dessa observação deve ser feita a auditoria dos previews legados e a instrumentação de etapas que ainda emitam somente texto.

O norte editorial permanece o benchmark por identidade de intervalo, digest de transcrição, formato e decisão humana. A observabilidade é suporte para esse benchmark, não um novo ranking.

## Arquivos alterados

- `modules/job_manager.py`
- `app.py`
- `static/js/app.js`
- `templates/index.html`
- `tests/test_job_manager.py`
- `tests/test_app_smoke.py`
- `tests/test_frontend_integrity.py`
- `docs/continuity/CYCLE_37_REPORT_2026-08-21.md`
- `docs/continuity/PROJECT_STATE.md`
- `docs/continuity/NEXT_CYCLE.md`
- `docs/continuity/HANDOFF_SINCE_CLAUDE_2026-08-21.md`

## Referências internas

- [`PROJECT_STATE.md`](PROJECT_STATE.md)
- [`NEXT_CYCLE.md`](NEXT_CYCLE.md)
- [`HANDOFF_SINCE_CLAUDE_2026-08-21.md`](HANDOFF_SINCE_CLAUDE_2026-08-21.md)
- [`RESEARCH_OBSERVABILITY_2026-08-21.md`](RESEARCH_OBSERVABILITY_2026-08-21.md)
- [`CYCLE_36_REPORT_2026-08-21.md`](CYCLE_36_REPORT_2026-08-21.md)
