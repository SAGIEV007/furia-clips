# Instruções para qualquer IA que continuar o Furia Clips

## Leia antes de alterar qualquer arquivo

Você está continuando um projeto existente. Não comece reescrevendo o sistema e não trate este documento como autorização para apagar alterações locais. Primeiro leia [`docs/continuity/START_HERE.md`](docs/continuity/START_HERE.md), [`docs/continuity/PROMPT_MESTRE_IA.md`](docs/continuity/PROMPT_MESTRE_IA.md), [`docs/continuity/CHUB_INTEGRATION_CONTRACT.md`](docs/continuity/CHUB_INTEGRATION_CONTRACT.md), [`README.md`](README.md), [`VERSION`](VERSION), [`docs/continuity/PROJECT_STATE.md`](docs/continuity/PROJECT_STATE.md), [`docs/continuity/DECISIONS.md`](docs/continuity/DECISIONS.md), [`docs/continuity/NEXT_CYCLE.md`](docs/continuity/NEXT_CYCLE.md), [`docs/continuity/COMMIT_MESSAGE_TEMPLATE.md`](docs/continuity/COMMIT_MESSAGE_TEMPLATE.md), [`docs/VERSIONING.md`](docs/VERSIONING.md), a documentação editorial relevante e o estado do Git.

O objetivo central é aprimorar o Furia Clips para gerar cortes do Renan Santos/MBL **concisos, autossuficientes, contextualizados, com tese/payoff completos e começo e encerramento naturais**. O usuário quer um agente executor: baixe o código, rode a aplicação, processe vídeos públicos, analise transcrição e vídeo, corrija bugs, escreva testes, compare antes/depois e publique alterações verificadas no GitHub.

## Ponto de entrada canônico

`docs/continuity/START_HERE.md` é a entrada operacional canônica. O prompt copiável e consolidado está em [`docs/continuity/PROMPT_MESTRE_IA.md`](docs/continuity/PROMPT_MESTRE_IA.md); ele incorpora o START_HERE, os prompts históricos, as decisões e o norte atual. O contrato funcional da integração Campaign Hub→cortes está em [`docs/continuity/CHUB_INTEGRATION_CONTRACT.md`](docs/continuity/CHUB_INTEGRATION_CONTRACT.md). Os arquivos `PROMPT_1`, `PROMPT_2`, `PROMPT_3` e prompts antigos permanecem como histórico e referência, mas não substituem o contrato vigente. O padrão obrigatório de mensagens de commit está em [`docs/continuity/COMMIT_MESSAGE_TEMPLATE.md`](docs/continuity/COMMIT_MESSAGE_TEMPLATE.md). O Furia continua sendo um sistema de cortes precisos; edição pós-renderização não entra na prioridade e o aplicativo local não deve chamar o MCP por job, mas deve usar a memória Chub válida durante a seleção.

## Prioridades

1. Integração efetiva do contexto do Campaign Hub na geração de seeds, expansão, gates e propostas de corte.
2. Seleção de janelas menores que continuem completas, com excelente contexto, locutor correto e payoff.
3. Calibração com vídeos públicos publicados em `@renansantosmbl` e `@renansantosreserva`, usando Campaign Hub, transcrição, vídeo, legendas, headlines, formato e métricas.
4. Geração de headlines fiéis ao trecho e adequadas ao formato.
5. Correção de bugs, estabilidade, jobs, renderização, cancelamento, persistência e diagnóstico.
6. Recursos secundários somente depois de proteger as prioridades anteriores.

## Corpus editorial

Os perfis do Campaign Hub são públicos. Os cortes publicados são exemplos de seleção editorial entre muitos cortes produzidos, portanto são rótulos fracos de aprovação, não prova absoluta de qualidade. Separe publicado, analisado audiovisual, performou bem e aprovado diretamente pelo usuário. Priorize, nesta ordem, Renan falando, Renan aparecendo, contas do Renan/Reserva e, apenas como último recurso, conteúdo geral do MBL.

Quando o vídeo público estiver acessível, analise mais do que o JSON do Campaign Hub: assista ou extraia frames e áudio, observe enquadramento, rosto, troca de câmera, texto na tela, legenda, ritmo, pausa, início, encerramento e a diferença entre fala e headline. Aprenda a cadeia `tema → tese → trecho → transcrição/legenda → headline → formato → desempenho`.

## Formatos editoriais obrigatórios

| Formato | Regra |
| --- | --- |
| `16:9 original` | Preserva a paisagem e pode usar headline curta e mais descritiva; não force vertical nem remova evidência visual. |
| `1:1 Alfinetei` | Quadrado, com palavra de impacto no topo e headline branca integrada à composição; texto muito enxuto e legível. |
| `fake tweet` | Simula publicação em primeira pessoa do Renan; só use quando a fala sustentar essa voz, sem inventar fatos. |

O mesmo trecho não precisa funcionar igualmente nos três formatos. O sistema deve recomendar o formato e explicar a decisão.

## Ciclo obrigatório de engenharia

Cada rodada deve testar uma única hipótese principal. Registre baseline, lote, hipótese, mudança, teste regressivo, resultados antes/depois e decisão. Não altere seleção, ranking, headlines e renderização simultaneamente sem isolar os efeitos.

Execute testes antes e depois. Para mídia real, valide a transcrição, a janela temporal, o artefato renderizado e FFprobe. Gates de contexto, timing, locutor, final truncado, duração inválida e mídia sem stream não podem ser compensados por um hook forte.

## Versionamento obrigatório

A versão inicial é `1.0`, definida em [`VERSION`](VERSION). Toda alteração observável deve avaliar incremento de versão conforme [`docs/VERSIONING.md`](docs/VERSIONING.md). A versão e a revisão Git devem aparecer no console permanente, na API, na interface e nos logs estruturados. O primeiro evento de cada processamento deve identificar versão, revisão, `job_id`, `project_id`, origem e horário.

Não faça push direto na branch principal sem autorização explícita. Trabalhe em branch, faça commits pequenos, use sempre um corpo de commit completo conforme [`docs/continuity/COMMIT_MESSAGE_TEMPLATE.md`](docs/continuity/COMMIT_MESSAGE_TEMPLATE.md), execute `git diff --check`, não inclua tokens, cookies, vídeos grandes, banco local ou dados pessoais e registre o hash final em `docs/continuity/PROJECT_STATE.md`.

## Entrega obrigatória

Ao terminar uma rodada, atualize o pacote em `docs/continuity/`: estado atual, decisões quando duráveis, changelog, métricas, testes, limitações, relatório e próxima hipótese. Atualize os documentos apenas com fatos verificados e mantenha uma única seção de estado corrente; histórico antigo deve apontar para relatórios, não competir com o estado atual. Se algo não foi executado, classifique como não verificado ou bloqueado. A resposta ao usuário deve informar versão, branch, commit, arquivos, testes, mídia processada, qualidade editorial, bugs e próxima hipótese.

Não finalize apenas com um plano. Se houver mídia pública disponível, execute um caso real. Se faltar mídia, continue com testes e diagnóstico e explique exatamente o bloqueio.
