# Matriz de discordância editorial

## Objetivo

A matriz registra, no armazenamento local do Furia 1, quando uma decisão humana é tomada diante dos sinais produzidos pelo motor editorial. Ela existe para permitir calibração comparativa e diagnóstico de revisão; **não é um novo score, não é um modelo de viralidade e não aprova ou rejeita cortes automaticamente**.

Cada entrada usa o schema `editorial-disagreement-v1` e mantém cinco espaços separados: identidade do clip; sinais automáticos do Furia; evidência audiovisual opcional; contexto resumido do Campaign Hub; e decisão humana.

## Contrato

| Espaço | Conteúdo | Limite editorial |
| --- | --- | --- |
| `clip` | Identidade estável, chave editorial, início, fim e duração. | Não guarda nome de arquivo completo nem transcript. |
| `automatic` | Score histórico, confiança, versão, fatores numéricos, flags e razões de revisão. | É uma fotografia do que o Furia sinalizou; não é reavaliado nem transformado em verdade. |
| `audiovisual` | Estado da evidência multimodal, identidade da fonte, confiança, flags e até cinco evidências QA resumidas. | A análise audiovisual é auxiliar; fonte incompatível permanece recusada como evidência. |
| `chub` | Conta, versão, freshness, contagens agregadas e read-only. | Não copia blocks, captions, transcript, métricas brutas ou tokens. |
| `human` | `approved`, `rejected` ou `needs_review`, motivo, tags e presença de nota. | É a decisão do editor, não uma etiqueta inferida automaticamente. |
| `measurement` | `descriptive_only`, `score_used_as_decision: false` e `causal_inference: false`. | Impede que o arquivo seja confundido com dataset causal ou ranking. |

## Onde os dados ficam

As entradas são anexadas a `disagreement_matrix.jsonl` dentro da sessão editorial local do projeto, normalmente sob `FURIA_EDITORIAL_SESSIONS_DIR` ou `~/FuriaClipsData/editorial_sessions`. O arquivo não é criado no checkout Git e não é enviado a serviços externos pelo Studio.

O endpoint local `GET /api/editorial/disagreements?project_id=N` retorna os registros bounded e um resumo com contagens de decisão, motivos e combinações descritivas entre alertas e decisão humana. O painel da Revisão mostra apenas esse resumo compacto para não competir com o player, a transcrição ou os controles de intervalo.

## Interpretação segura

Uma entrada como `warning_human_approved` significa somente que havia algum flag automático ou audiovisual e que o editor aprovou o intervalo. Isso pode revelar um falso positivo do detector, uma exceção editorial válida ou uma necessidade de melhorar a evidência. Não significa que o editor “venceu” o modelo, que o clip é viral ou que a decisão é causalmente correta.

A matriz não deve ser usada para recalibrar pesos diretamente. Antes de qualquer uso em calibração, é necessário reunir uma amostra suficiente de decisões finais, preservar a razão de cada decisão, separar mudanças de intervalo de aprovação/rejeição e revisar conflitos. O fato de uma conta Chub ou um rank aparecer na entrada não pode superar os gates de contexto, continuidade, locutor, áudio ou identidade da fonte.

## Testes

A cobertura inclui separação dos namespaces, recusa de ações não finais, ausência de transcript e nota bruta, agregação descritiva de alertas, round-trip do armazenamento por projeto e fluxo HTTP completo de decisão e consulta. A matriz é auxiliar: se o arquivo de auditoria falhar, a decisão humana continua válida e a falha é registrada no log local.
