# Próximo ciclo — Furia Clips

## Estado de partida

A release `6.23` está na branch `claude/repo-access-commits-imgjmk`. Ela preserva a observabilidade da 6.21, a recuperação textual conservadora de seeds Chub da 6.22 e adiciona refinamento opcional por timestamps de palavra e um ledger de elegibilidade editorial. A pesquisa acumulada está em `RESEARCH_CUTTING_PRECISION_2026-08-21.md`; a auditoria atual está em `AUDIT_CUTTING_PRECISION_CYCLE39_2026-08-21.md`; o relatório da rodada está em `CYCLE_39_REPORT_2026-08-21.md`.

A fonte original continua canônica. Reels e posts publicados continuam `reference_only`; lives longas e arquivos crus continuam `processing_source`. O job normal continua offline-first, sem chamada MCP por candidato. O norte imediato segue sendo precisão de cortes e integração Chub/MBL; automações remotas, mensageria e smartwatch permanecem na fase futura.

## Hipótese única

> **Se o Furia comparar janelas quase idênticas e registrar hard negatives por motivo, então poderá distinguir melhoria real de contexto, payoff, locutor e borda de uma simples alteração de score ou aumento de volume.**

A 6.23 já expõe `word_boundary_refinement` quando a transcrição contém timestamps por palavra e separa `ready`, `review` e `blocked` sem alterar o ranking. O próximo passo é medir essas dimensões com pares difíceis: a mesma tese com início tardio, a mesma fala antes do payoff, a mesma frase dita por terceiro, a mesma seed Chub ancorada no momento errado e a mesma headline com afirmação não sustentada.

## Procedimento de validação

1. Congelar uma fonte longa autorizada por família: live solo, entrevista/sabatina, notícia/reação, discurso ou tela/documento.
2. Criar itens positivos e hard negatives com `source_signature`, `processing_identity`, `transcript_digest`, formato, locutor, início/fim, seed Chub quando existir e decisão humana.
3. Comparar baseline de borda por segmento com `word_boundary_refinement`, medindo erro absoluto de início/fim, duração, início natural e preservação do payoff.
4. Comparar o mesmo conjunto com e sem os campos de elegibilidade, sem remover candidatos, verificando se a revisão humana localiza mais rápido os bloqueios e pendências.
5. Medir separadamente contexto autossuficiente, pergunta–resposta, payoff, locutor Renan, headline fiel, risco factual, duplicata e qualidade visual.
6. Registrar rejeições nas categorias `contexto`, `payoff`, `speaker`, `timing`, `transcrição`, `headline`, `não-conteúdo`, `visual` e `duplicata`.
7. Só depois construir pairwise ranking ou alterar pesos por perfil, conta ou formato.

## Critério de sucesso

A hipótese será confirmada se os hard negatives produzirem diagnósticos estáveis e se o refinamento por palavra reduzir erro de borda sem aumentar início abrupto, perda de contexto ou duração inválida. O ledger será considerado útil se separar claramente candidatos prontos, revisáveis e bloqueados sem modificar o score histórico.

Nenhuma mudança de ranking será publicada como melhoria comprovada sem before/after no mesmo conjunto congelado, com recall, precision@K, contexto, payoff, falso Renan, erro de borda e taxa de revisão. Uma melhoria pode ser publicada como instrumento diagnóstico mesmo sem ganho editorial, desde que não altere a decisão do motor e seja explicitamente rotulada como tal.

## Próximas hipóteses depois desta

A ordem recomendada é: expansão de candidatos em duas passagens; hard negatives e checklist de revisão; fila baseada em elegibilidade; word timestamps sob demanda; alinhamento de locutor por fusão de turnos/voz/rosto/Chub; validação visual seletiva; pairwise ranking por conta/formato; headline grounded; presets 9:16/1:1/fake tweet; e reprocessamento seletivo por etapa.

## Escopo excluído

Não alterar pesos do ranking sem benchmark. Não adicionar chamada MCP direta durante o corte, download autenticado, WhatsApp, smartwatch ou promoção automática. Não baixar Reels publicados. Não incluir mídia real, transcrições reais, cookies, tokens, bancos ou modelos no Git. Não tocar a branch principal.

## Arquivos para ler primeiro

`PROJECT_STATE.md`, `HANDOFF_SINCE_CLAUDE_2026-08-21.md`, `CYCLE_39_REPORT_2026-08-21.md`, `AUDIT_CUTTING_PRECISION_CYCLE39_2026-08-21.md`, `CUTTING_AUDIT_2026-08-21.md`, `CUTTING_PRECISION_PLAN_2026-08-21.md`, `RESEARCH_CUTTING_PRECISION_2026-08-21.md`, `RESEARCH_MCP_CHUB_2026-08-21.md`, `FUTURE_PLATFORM_2026-08-21.md`, `modules/clip_selector.py`, `modules/editorial_ranker.py`, `tests/test_clip_selector_word_boundaries.py` e `tests/test_editorial_ranker.py`.

## Referências

- [`PROJECT_STATE.md`](PROJECT_STATE.md)
- [`HANDOFF_SINCE_CLAUDE_2026-08-21.md`](HANDOFF_SINCE_CLAUDE_2026-08-21.md)
- [`CYCLE_39_REPORT_2026-08-21.md`](CYCLE_39_REPORT_2026-08-21.md)
- [`AUDIT_CUTTING_PRECISION_CYCLE39_2026-08-21.md`](AUDIT_CUTTING_PRECISION_CYCLE39_2026-08-21.md)
- [`CUTTING_PRECISION_PLAN_2026-08-21.md`](CUTTING_PRECISION_PLAN_2026-08-21.md)
- [`RESEARCH_CUTTING_PRECISION_2026-08-21.md`](RESEARCH_CUTTING_PRECISION_2026-08-21.md)
- [`RESEARCH_MCP_CHUB_2026-08-21.md`](RESEARCH_MCP_CHUB_2026-08-21.md)
- [Branch de trabalho no GitHub](https://github.com/SAGIEV007/furia-clips/tree/claude/repo-access-commits-imgjmk)
