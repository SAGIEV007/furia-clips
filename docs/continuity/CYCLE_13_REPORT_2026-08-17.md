# Relatório do ciclo 13 — Contrato de continuidade e Prompt Mestre 2.3

## Estado do ciclo

| Campo | Valor |
| --- | --- |
| Versão documental | `2.3` |
| Última release funcional de código | `2.2` |
| Branch | `manus/rebuild-opus-parity` |
| Baseline de código | `074a129` |
| Natureza da rodada | Somente documental e operacional; nenhum módulo de processamento foi alterado |
| Hipótese | Se todo o contexto relevante ficar consolidado no GitHub, com uma entrada copiável e um contrato de commits completo, outra IA poderá continuar o projeto sem depender de uma conversa privada ou de mensagens genéricas de commit. |
| Escopo excluído | Nenhuma mudança de seleção, ranking, diarização, reframe, ingestão, renderização, headline ou integração de runtime foi feita nesta rodada. |

## O que foi executado

Foi auditado o estado da branch `manus/rebuild-opus-parity`, o histórico recente, os documentos de continuidade, os prompts históricos, a próxima hipótese e as decisões permanentes. A revisão confirmou que a release 2.2 tinha norte explícito nos relatórios e documentos, embora seus três commits mais recentes não tivessem corpo explicativo.

Foi criado [`PROMPT_MESTRE_IA.md`](PROMPT_MESTRE_IA.md), uma versão copiável que consolida o `START_HERE`, os prompts de autonomia e evolução profissional, as decisões D-001–D-020, o benchmark 2.2, o norte do b354, as regras do Campaign Hub, o ciclo de engenharia, o contrato de documentação e o padrão de entrega.

Foi criado [`COMMIT_MESSAGE_TEMPLATE.md`](COMMIT_MESSAGE_TEMPLATE.md), exigindo hipótese, baseline, implementação, escopo excluído, validação, resultado, limitações e continuidade em cada commit relevante.

O `README.md`, o `AGENTS.md` e o `START_HERE.md` foram atualizados para apontar para o prompt mestre e o modelo de commit. O changelog, o estado vivo, a próxima hipótese e a versão foram alinhados com a revisão documental 2.3. O hash incorreto da release 2.2 em `PROJECT_STATE.md` foi corrigido para o commit observado `074a129`.

## Contexto preservado

O norte funcional não foi alterado: o caso b354 continua com recall `0/3` no benchmark temporal, e o próximo ciclo continua focado em usar highlights como sementes e expandi-los para a menor janela completa da transcrição. O benchmark permanece read-only e não aprova cortes automaticamente. O job local permanece offline-first e não deve chamar o MCP a cada corte.

As regras editoriais preservadas incluem contexto antes de slogan, gates antes do ranking, separação entre quem fala/aparece/é foco, transcrição manual como timeline canônica, preservação do original em decisões ambíguas de enquadramento, distinção entre contas e plataformas do Campaign Hub e proibição de atribuir fala de terceiros ao Renan.

## Validação

Foram conferidas a revisão Git `074a129`, a branch de trabalho, a versão base `2.2`, os documentos vivos, o benchmark b354 persistido e os três exports individuais historicamente validados por FFprobe. Os links relativos dos documentos novos e alterados não possuem destinos ausentes, e `git diff --check` passou.

A primeira execução local da suíte encontrou `324 passed` e três falhas: duas expectativas antigas de versão `2.2` nos testes de identidade de runtime e a ausência do asset externo BlazeFace. As expectativas foram atualizadas para `2.3`, sem alterar o pipeline. O asset oficial foi provisionado temporariamente, conferido pelo SHA-256 documentado e mantido fora do commit. A execução final terminou com **327 passed**.

Também foi verificado que nenhum arquivo proibido foi adicionado pela rodada e que não houve alteração em módulos de seleção, ranking, ingestão, reframe ou renderização. A revisão do diff completo e a confirmação do hash final devem ser repetidas imediatamente antes e depois do commit.

O relatório não afirma melhoria de recall ou qualidade editorial. A validação confirma a consistência do contrato documental e da identidade de runtime; qualquer resultado funcional futuro deve criar um novo relatório com métricas reproduzidas.

## Decisão

**Confirmado:** o GitHub agora contém uma entrada copiável, um contrato de continuidade e um padrão de commit que tornam explícito o norte do projeto e reduzem a dependência de contexto externo.

**Não verificado:** a capacidade de uma IA externa seguir todo o contrato corretamente só poderá ser avaliada em uma sessão futura com checkout limpo.

**Próxima hipótese única:** executar o ciclo de expansão de seeds descrito em `NEXT_CYCLE.md` e medir se o recall do b354 sai de `0/3` sem aumentar falsos positivos ou alterar a atribuição de locutor.
