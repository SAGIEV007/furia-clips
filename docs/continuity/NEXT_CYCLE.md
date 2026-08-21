# Próximo ciclo — Furia Clips

## Estado de partida

A release `6.24` está na branch `claude/repo-access-commits-imgjmk`. Ela preserva a observabilidade da 6.21, a recuperação textual conservadora de seeds Chub da 6.22, o refinamento por timestamps de palavra e o ledger de elegibilidade da 6.23, e adiciona hard negatives sanitizados e timestamps por palavra como padrão editorial. A pesquisa acumulada está em `RESEARCH_CUTTING_PRECISION_2026-08-21.md`; os relatórios recentes estão em `CYCLE_39_REPORT_2026-08-21.md` e `CYCLE_40_REPORT_2026-08-21.md`.

A fonte original continua canônica. Reels e posts publicados continuam `reference_only`; lives longas e arquivos crus continuam `processing_source`. O job normal continua offline-first, sem chamada MCP por candidato. O norte imediato segue sendo precisão de cortes e integração Chub/MBL; automações remotas, mensageria e smartwatch permanecem na fase futura.

## Hipótese única

> **Se o Furia transformar hard negatives em um benchmark com decisão humana rastreável, então poderá medir falsos negativos e melhorar contexto, payoff, locutor e borda sem confundir aumento de candidatos com aumento de qualidade.**

A 6.24 preserva até 80 near-misses por execução em `candidate_diagnostics["hard_negatives"]`, com motivo, vencedor e evidência limitada. O próximo passo é importar esse ledger para um benchmark versionado, sem alterar o ranking, e associar cada item a uma decisão humana `approved`, `rejected` ou `needs_review` e a um motivo editorial controlado.

## Procedimento de validação

1. Selecionar uma fonte longa autorizada por família: live solo, entrevista/sabatina, notícia/reação, discurso ou tela/documento.
2. Congelar `source_signature`, `processing_identity`, `transcript_digest`, formato, locutor, início/fim, seed Chub quando existir e a versão do motor.
3. Materializar pares e quase-pares: início tardio, final precoce, payoff ausente, anáfora sem antecedente, locutor de terceiro, duplicata temporal, não-conteúdo, headline infiel e formato incompatível.
4. Associar cada item a uma decisão humana e a um único motivo primário, preservando notas secundárias em tags separadas.
5. Medir erro absoluto de início/fim, duração, contexto autossuficiente, pergunta–resposta, payoff, locutor Renan, headline fiel, risco factual, duplicata e qualidade visual.
6. Comparar baseline sem refinamento, refinamento por palavra e ledger de elegibilidade; não remover candidatos durante a medição.
7. Só depois construir pairwise ranking ou alterar pesos por perfil, conta ou formato.

## Critério de sucesso

O benchmark será útil se decisões humanas puderem ser reproduzidas a partir do item original, se o motivo da rejeição for estável e se o mesmo caso não mudar de identidade entre execuções. A melhoria editorial será confirmada somente se o refinamento reduzir erro de borda sem aumentar início abrupto, perda de contexto, payoff ausente, falso Renan ou duração inválida.

Nenhuma mudança de ranking será publicada como melhoria comprovada sem before/after no mesmo conjunto congelado, com recall, precision@K, contexto, payoff, falso Renan, erro de borda e taxa de revisão. Uma melhoria pode ser publicada como instrumento diagnóstico mesmo sem ganho editorial, desde que não altere a decisão do motor e seja explicitamente rotulada como tal.

## Próximas hipóteses depois desta

A ordem recomendada é: benchmark de hard negatives; checklist de revisão pela elegibilidade; expansão de candidatos em duas passagens; alinhamento de locutor por fusão de turnos/voz/rosto/Chub; validação visual seletiva; pairwise ranking por conta/formato; headline grounded; presets 9:16/1:1/fake tweet; e reprocessamento seletivo por etapa.

## Escopo excluído

Não alterar pesos do ranking sem benchmark. Não adicionar chamada MCP direta durante o corte, download autenticado, WhatsApp, smartwatch ou promoção automática. Não baixar Reels publicados. Não incluir mídia real, transcrições reais, cookies, tokens, bancos ou modelos no Git. Não tocar a branch principal.

## Arquivos para ler primeiro

`PROJECT_STATE.md`, `HANDOFF_SINCE_CLAUDE_2026-08-21.md`, `CYCLE_40_REPORT_2026-08-21.md`, `CYCLE_39_REPORT_2026-08-21.md`, `CUTTING_AUDIT_2026-08-21.md`, `CUTTING_PRECISION_PLAN_2026-08-21.md`, `RESEARCH_CUTTING_PRECISION_2026-08-21.md`, `RESEARCH_MCP_CHUB_2026-08-21.md`, `FUTURE_PLATFORM_2026-08-21.md`, `modules/clip_selector.py`, `modules/editorial_ranker.py`, `tests/test_candidate_volume_diagnostics.py` e `tests/test_clip_selector_word_boundaries.py`.

## Referências

- [`PROJECT_STATE.md`](PROJECT_STATE.md)
- [`HANDOFF_SINCE_CLAUDE_2026-08-21.md`](HANDOFF_SINCE_CLAUDE_2026-08-21.md)
- [`CYCLE_40_REPORT_2026-08-21.md`](CYCLE_40_REPORT_2026-08-21.md)
- [`CYCLE_39_REPORT_2026-08-21.md`](CYCLE_39_REPORT_2026-08-21.md)
- [`CUTTING_PRECISION_PLAN_2026-08-21.md`](CUTTING_PRECISION_PLAN_2026-08-21.md)
- [`RESEARCH_CUTTING_PRECISION_2026-08-21.md`](RESEARCH_CUTTING_PRECISION_2026-08-21.md)
- [`RESEARCH_MCP_CHUB_2026-08-21.md`](RESEARCH_MCP_CHUB_2026-08-21.md)
- [Branch de trabalho no GitHub](https://github.com/SAGIEV007/furia-clips/tree/claude/repo-access-commits-imgjmk)
