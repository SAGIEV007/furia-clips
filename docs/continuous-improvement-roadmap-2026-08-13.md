# Roadmap de evolução contínua — Furia Clips

| Campo | Valor |
| --- | --- |
| Data | 13 de agosto de 2026 |
| Branch | `manus/rebuild-opus-parity` |
| Objetivo operacional | Selecionar a melhor nata de aproximadamente oito lives por dia e apoiar uma carteira final de 39–50 cortes com revisão rápida. |
| Princípio | Qualidade editorial, contexto e controle do editor são mais importantes que forçar quantidade. |

## Evidências usadas nesta priorização

O ciclo anterior confirmou que o Gemini online é prioritário, mas pode retornar HTTP 503 após o upload/processamento do vídeo; por isso, o fallback local precisa ser confiável. O log do usuário revelou uma falha específica do `openai-whisper` em CPU com `float16`, já corrigida com regressão automatizada. A aplicação também possui filas persistentes no processo completo, enquanto o botão de corte rápido ainda utiliza execução legada em thread. Por fim, a nova central de revisão já persiste aprovação, rejeição e necessidade de contexto, criando a base para calibrar a seleção com decisões reais do editor.

## Ordem de implementação por impacto

| Prioridade | Melhoria | Por que vem agora | Critério de aceite |
| --- | --- | --- | --- |
| P0 | Tornar o corte rápido resiliente e retomável | É o fluxo mais usado e ainda não usa a infraestrutura persistente de jobs do processo completo. | Uma execução pode ser acompanhada, cancelada, reaberta e diagnosticada sem perder o estado. |
| P0 | Endurecer a segurança e a renderização de resultados | Transcrições, títulos e razões vindas de fonte externa não devem ser interpoladas sem escape no HTML. | Texto externo aparece literalmente, sem executar marcação ou script. |
| P1 | Mostrar previsão de tempo e etapa real | Lives longas exigem visibilidade de espera, fallback, progresso e motivo de degradação. | A interface diferencia upload, espera Gemini, tentativa local, seleção, corte e conclusão. |
| P1 | Portfolio diário visual | O editor precisa enxergar variedade, qualidade e meta diária entre múltiplas lives. | Painel agrupa candidatos por live, formato editorial, score e estado de revisão. |
| P1 | Feedback editor → ranking | Ações de aprovar, rejeitar, ajustar e pedir contexto devem alterar sinais mensuráveis do ranking. | Relatório mostra aprovação por fonte, formato, score e decisão de enquadramento. |
| P2 | Edição rápida de ponto de entrada/saída | O editor deve ajustar segundos sem abrir outro aplicativo para pequenos reparos. | Preview permite definir início/fim e salvar o ajuste como feedback. |
| P2 | Diarização e pergunta–resposta | Melhora cortes de entrevista, interrupções e múltiplos participantes. | O sistema mostra confiança de locutor e preserva a pergunta necessária. |
| P2 | Processamento em lote de lives | Reduz trabalho repetitivo em uma rotina de oito fontes diárias. | Fila aceita várias fontes, respeita concorrência e gera uma carteira consolidada. |

## Regras de qualidade para cada ciclo

Cada alteração deve cumprir quatro condições antes de publicação. Deve haver teste automatizado para a regra nova ou para a regressão corrigida; falhas de IA externa precisam virar mensagens acionáveis e fallback seguro; a interface deve explicar o que a automação decidiu; e arquivos de mídia, logs e resultados volumosos não devem entrar no GitHub por acidente.

## Expansão da análise dos vídeos do Renan

A análise dos perfis deve avançar por lotes verificáveis, não por uma alegação genérica de cobertura. O processo recomendado é retomar o catálogo público com cursor e atraso, baixar uma amostra controlada, registrar evidência visual e transcrita por vídeo, atualizar a taxonomia editorial e só então modificar pesos ou prompts. O inventário já produzido permite comparar o perfil principal e o reserva enquanto a paginação pública permanece limitada.

A próxima rodada de análise deve iniciar depois que o corte rápido estiver retomável e a revisão gerar feedback persistente, porque os novos dados então poderão ser convertidos diretamente em critérios de seleção e não apenas em documentação.
