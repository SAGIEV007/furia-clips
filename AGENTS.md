# Instruções para qualquer IA que continuar o Furia Clips

## Leia antes de alterar qualquer arquivo

Você está continuando um projeto existente. Não comece reescrevendo o sistema e não trate este documento como autorização para apagar alterações locais. Primeiro leia [`docs/continuity/START_HERE.md`](docs/continuity/START_HERE.md), [`README.md`](README.md), [`VERSION`](VERSION), [`docs/continuity/PROJECT_STATE.md`](docs/continuity/PROJECT_STATE.md), [`docs/continuity/DECISIONS.md`](docs/continuity/DECISIONS.md), [`docs/continuity/NEXT_CYCLE.md`](docs/continuity/NEXT_CYCLE.md), [`docs/VERSIONING.md`](docs/VERSIONING.md), a documentação editorial relevante e o estado do Git.

O objetivo central é aprimorar o Furia Clips para gerar cortes do Renan Santos/MBL **concisos, autossuficientes, contextualizados, com tese/payoff completos e começo e encerramento naturais**. O usuário quer um agente executor: baixe o código, rode a aplicação, processe vídeos públicos, analise transcrição e vídeo, corrija bugs, escreva testes, compare antes/depois e publique alterações verificadas no GitHub.

## Ponto de entrada canônico

`docs/continuity/START_HERE.md` é o prompt mestre operacional vigente para futuras IAs. Ele unifica o contexto do projeto, o estado real verificado, as prioridades, o uso correto do Campaign Hub, o fluxo inspirado no Garimpo, as regras editoriais, o ciclo de testes e a continuidade no GitHub. Os arquivos `PROMPT_1`, `PROMPT_2`, `PROMPT_3` e `PROMPT_MESTRE` permanecem como histórico e referência, mas não substituem o START_HERE. O Furia continua sendo um sistema de cortes precisos; edição pós-renderização não entra na prioridade e o aplicativo local não deve chamar o MCP por job.

## Prioridades

1. Seleção de janelas menores que continuem completas, com excelente contexto.
2. Calibração com vídeos públicos publicados em `@renansantosmbl` e `@renansantosreserva`, usando Campaign Hub, transcrição, vídeo, legendas, headlines, formato e métricas.
3. Geração de headlines fiéis ao trecho e adequadas ao formato.
4. Correção de bugs, estabilidade, jobs, renderização, cancelamento, persistência e diagnóstico.
5. Recursos secundários somente depois de proteger as prioridades anteriores.

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

Não faça push direto na branch principal sem autorização explícita. Trabalhe em branch, faça commits pequenos, execute `git diff --check`, não inclua tokens, cookies, vídeos grandes, banco local ou dados pessoais e registre o commit em `docs/continuity/PROJECT_STATE.md`.

## Entrega obrigatória

Ao terminar uma rodada, atualize o pacote em `docs/continuity/`: estado atual, decisões, changelog, métricas, testes, limitações e próxima hipótese. Atualize os documentos apenas com fatos verificados. Se algo não foi executado, classifique como não verificado ou bloqueado. A resposta ao usuário deve informar versão, branch, commit, arquivos, testes, mídia processada, qualidade editorial, bugs e próxima hipótese.

Não finalize apenas com um plano. Se houver mídia pública disponível, execute um caso real. Se faltar mídia, continue com testes e diagnóstico e explique exatamente o bloqueio.
