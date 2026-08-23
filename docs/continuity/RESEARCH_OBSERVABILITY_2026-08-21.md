# Pesquisa de observabilidade e diagnóstico — 2026-08-21

## Fontes consultadas

1. OpenTelemetry Logging — https://opentelemetry.io/docs/specs/otel/logs/
2. OpenTelemetry Context Propagation — https://opentelemetry.io/docs/concepts/context-propagation/
3. Flask Logging — https://flask.palletsprojects.com/en/stable/logging/
4. Sentry Flask Integration — https://docs.sentry.io/platforms/python/integrations/flask/

## Achados verificáveis

### OpenTelemetry Logging

A documentação recomenda um modelo de log estruturado e compatível com sistemas existentes, preservando campos de origem, recurso e contexto de execução. O principal ganho não é abandonar a biblioteca de logging atual, mas adicionar registros estruturados e correlação consistente.

A especificação destaca três dimensões de correlação: tempo de execução, contexto da execução e origem do telemetria. TraceId/SpanId são exemplos de identificadores de contexto; no Furia local, o equivalente mínimo deve ser `job_id`, `request_id`, `project_id`, `processing_identity` e `event_id`.

A pesquisa também recomenda que logs legados possam ser enriquecidos sem exigir a reescrita de cada mensagem. Para o Furia, isso significa manter o texto humano em português no console e emitir junto um evento estruturado com nome, etapa, nível, duração, campos seguros e exceção.

### Propagação de contexto

OpenTelemetry define contexto como o objeto usado para correlacionar sinais e propagação como o mecanismo que o transporta entre unidades de execução. A documentação explica que logs podem receber TraceId e SpanId e ficar correlacionados entre processos ou serviços.

O Furia não precisa instalar uma infraestrutura distribuída agora. Deve aplicar o princípio localmente: todo evento precisa carregar o mesmo `job_id`, e operações derivadas precisam preservar `project_id`, `processing_identity`, `transcript_digest` e uma sequência monotônica de evento. Nenhuma credencial, cookie ou dado pessoal deve entrar nesse contexto.

### Flask Logging

A documentação oficial recomenda configurar logging cedo, usar a biblioteca padrão do Python e permitir que logs da aplicação e de bibliotecas relacionadas cheguem ao mesmo handler. Também demonstra a injeção de informações da requisição no formatter.

No Furia, o diagnóstico deve combinar o console de progresso do job com `app.logger` e um arquivo local rotativo/sanitizado. Os campos de request devem ser limitados a método, endpoint, status, duração, `request_id` e tamanho; corpos de upload, tokens e segredos não devem ser gravados.

### Sentry Flask

A integração Flask do Sentry captura contexto de requisição, conecta eventos de erro à transação e transforma logs em breadcrumbs. O conceito de breadcrumb é útil para o Furia mesmo sem adotar Sentry: manter uma janela dos eventos anteriores ao erro, com etapa, mensagem, duração e campos seguros, para explicar a sequência que levou à falha.

Não foi adicionada dependência Sentry neste ciclo de pesquisa. A implementação local deve primeiro produzir breadcrumbs próprios e exportação manual; uma integração externa futura exigiria decisão separada, configuração de privacidade e autorização.

## Requisitos derivados para o Furia

| Requisito | Aplicação local |
|---|---|
| Correlação | `job_id`, `request_id`, `project_id`, `event_id`, `processing_identity` e `transcript_digest` |
| Evento estruturado | `event_name`, `level`, `stage`, `message`, `timestamp`, `duration_ms`, `data`, `error` |
| Texto humano | Mensagem em português preservada no console e na interface |
| Breadcrumbs | Janela dos últimos eventos e resumo das etapas antes de falha |
| Diagnóstico final | Pacote copiável com versão, revisão, origem sanitizada, configurações não secretas, etapas, contagens, artefatos e erro |
| Privacidade | Nunca registrar API keys, cookies, headers sensíveis, transcrição completa ou conteúdo de mídia no resumo copiável |
| Retenção | Console visual limitado; histórico completo rotativo e endpoint paginado por job |
| Compatibilidade | Mensagens atuais continuam válidas; campos estruturados são adicionados ao lado delas |

## Decisão de implementação

O Furia deve adotar uma camada local de eventos estruturados, sem depender de OpenTelemetry ou Sentry para funcionar. O JobManager persistirá um histórico limitado por job; o frontend mostrará resumo e oferecerá “Copiar diagnóstico completo”, enquanto o arquivo local manterá os detalhes necessários para investigação profunda.
