# Furia Studio — otimização e usabilidade

## Escopo

Esta rodada melhora o Studio único baseado exclusivamente no Furia 1. O objetivo foi reduzir ambiguidade, evitar trabalho pesado duplicado e tornar operações longas reversíveis, sem reintroduzir o Furia 2, sem criar uma segunda aplicação e sem transformar Campaign Hub ou Gemini em dependências.

## Melhorias verificadas

| Área | Alteração |
| --- | --- |
| Próxima ação | O cabeçalho do projeto agora explica a etapa seguinte e muda o comando principal conforme fonte, transcript, pool, revisão, aprovação ou exportação. |
| Resultado vazio | Uma análise concluída sem candidatos é persistida como `ready_no_results`, permanece em Entender e oferece `Reanalisar — Furia 1` explicitamente. |
| Contrato de jobs | A interface aceita tanto `jobId` quanto `job_id`, evitando que um job real apareça como `Job não encontrado`. |
| Estado terminal | Análise, transcrição e exportação redesenham a tela ao terminar; o projeto não fica visualmente preso em `EM ANDAMENTO`. |
| Cancelamento | O botão do Console solicita cancelamento, apresenta `Cancelando…` e o VideoCutter encerra cooperativamente o processo FFmpeg, removendo o arquivo parcial. |
| Polling | A fila usa scheduler único, deduplicação, backoff e pausa inteligente quando a aba está oculta; projetos não são carregados por chamadas concorrentes. |
| Renderização | Thumbnails da Biblioteca usam carregamento preguiçoso e a prévia ativa continua disponível. |
| Revisão | A navegação anterior/próximo reduz cliques repetitivos; rejeições podem guardar motivo e tags estruturadas para calibração editorial futura. |
| Diagnóstico | Ajustes ganhou atualização manual do status de Whisper, FFmpeg e Gemini, sem exibir a chave Gemini. |
| Windows | O launcher passa a construir a URL a partir de `FURIA_PORT`, mantendo o bloqueio de segunda instância e a abertura automática da mesma URL. |

## QA visual

A interface foi exercitada em uma única aba com fixture sintético local. A fonte persistiu após reload e navegação; o transcript manual foi exibido; a análise Furia 1 reutilizou o transcript e terminou com zero candidatos sem iniciar Whisper; a tela mostrou `SEM CANDIDATOS` e a ação explícita de reanálise. Em seguida, o Whisper local foi iniciado pelo botão da interface, o Console mostrou o fallback efetivo para `openai-whisper` e o cancelamento foi acionado durante a carga do modelo. O job terminou como `cancelled`, sem transcript parcial, e o botão voltou ao estado normal.

Os Ajustes abriram no mesmo Studio. O diagnóstico mostrou `openai-whisper` disponível, Gemini opcional sem chave e o comando `Atualizar diagnóstico` produziu feedback visível sem expor segredo. O uploader oculto não foi automatizado pelo navegador de QA; a importação funcional do fixture foi executada pela rota local, e a continuação do fluxo foi validada visualmente.

## Gate automatizado

O release gate foi executado com diretórios de dados e workspace limpos. O resultado foi **827 testes aprovados, 27 ignorados e 2 xfails em 15,04 segundos**. Também passaram `node --check static/app.js`, compilação Python dos módulos alterados e `git diff --check`.

A verificação de higiene confirmou que nenhum caminho de Furia 2, vídeo, SRT, SQLite, workspace, export ou log de QA está versionado. O launcher Windows recebeu uma regressão que protege host local, porta padrão, URL construída e abertura única.

## Limites

A execução foi feita no ambiente Linux isolado. Ainda é necessária uma confirmação final em uma máquina Windows real para bootstrap, permissões, instalação de Python/FFmpeg, comportamento do `run.bat` e abertura do navegador. Gemini online não foi testado com credencial real; seu caminho continua opcional e protegido. O ranking continua sendo uma ordenação explicável de candidatos para revisão humana, não uma previsão de viralidade.
