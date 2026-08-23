# Próximo ciclo — Furia Clips

## Estado de partida

A release `6.26` está em implementação na branch `claude/repo-access-commits-imgjmk`. Ela preserva a observabilidade da 6.21, a recuperação textual Chub da 6.22, o refinamento por palavra e a elegibilidade da 6.23, o ledger de hard negatives da 6.24 e o contrato persistente da 6.25. A 6.26 adiciona importação append-only de decisões humanas, estados de conflito/adjudicação e API local de revisão. A pesquisa acumulada está em `RESEARCH_CUTTING_PRECISION_2026-08-21.md` e `RESEARCH_HUMAN_DECISIONS_2026-08-21.md`; o relatório atual será `CYCLE_42_REPORT_2026-08-21.md`.

A fonte original continua canônica. Reels e posts publicados continuam `reference_only`; lives longas e arquivos crus continuam `processing_source`. O job normal continua offline-first, sem chamada MCP por candidato. O norte imediato segue sendo precisão de cortes e integração Chub/MBL; automações remotas, mensageria e smartwatch permanecem na fase futura.

## Hipótese única

> **Se decisões humanas reais forem associadas aos itens do `hard-negative-v1` por meio de um histórico append-only, com conflitos explícitos e adjudicação separada, então o Furia poderá medir falsos negativos e preparar calibração de borda, contexto, payoff e locutor sem confundir aumento de volume com aumento de qualidade.**

A 6.26 implementa o caminho de importação, mas ainda não contém decisões de uma fonte real. O endpoint local aceita os quatro estados controlados, preserva `processing_identity`, `transcript_digest`, fonte, formato e intervalo original, e nunca altera ranking automaticamente. Conflitos ficam em `needs_review` até adjudicação.

## Procedimento de validação

1. Selecionar uma fonte longa autorizada por família: live solo, entrevista/sabatina, notícia/reação, discurso ou tela/documento.
2. Gerar uma execução com timestamps por palavra e coletar o diagnóstico de seleção, o arquivo `hard-negative-v1` e os candidatos finais.
3. Para cada item, registrar uma decisão humana única: `approved`, `rejected` ou `needs_review`, além de um motivo primário (`contexto`, `payoff`, `speaker`, `timing`, `duplicata`, `não-conteúdo`, `headline`, `visual` ou `outro`). A decisão pode ser enviada pelo endpoint local e será anexada ao histórico.
4. Se dois revisores divergirem, não substituir a primeira decisão: importar a segunda, confirmar o estado `conflict` e registrar uma terceira decisão com `adjudication=true` somente após revisão.
5. Reexecutar a mesma faixa somente quando necessário e verificar que identidade, digest e intervalos permanecem estáveis.
6. Comparar baseline sem refinamento e refinamento por palavra em erro de início/fim, duração, início natural, contexto autossuficiente, payoff, locutor Renan, headline fiel e taxa de revisão.
7. Medir pares dentro da mesma live: vencedor versus hard negative, com preferência humana separada de saliência/hook.
8. Só depois testar pairwise ranking ou alterar pesos por perfil, conta ou formato.

## Critério de sucesso

O benchmark será considerado calibrável se decisões humanas puderem ser reproduzidas pelo item original, se os motivos permanecerem estáveis e se o mesmo caso não mudar de identidade entre execuções. Uma melhoria editorial será confirmada somente se reduzir falsos negativos ou erro de borda sem aumentar início abrupto, perda de contexto, payoff ausente, falso Renan ou duração inválida.

Nenhuma alteração de ranking será publicada sem before/after no mesmo conjunto congelado e sem separar relevância/autossuficiência de saliência/hook. O contrato pode ser melhorado como instrumento diagnóstico mesmo quando não houver amostra suficiente para ajustar pesos.

## Próximas hipóteses depois desta

A ordem recomendada é: coletar decisões reais na 6.26; calcular métricas de acordo/conflito e qualidade por motivo sem mexer nos pesos; checklist de revisão pela elegibilidade; expansão de candidatos em duas passagens; alinhamento de locutor por fusão de turnos/voz/rosto/Chub; validação visual seletiva; pairwise ranking por conta/formato; headline grounded; presets 9:16/1:1/fake tweet; e reprocessamento seletivo por etapa.

## Escopo excluído

Não alterar pesos do ranking sem benchmark. Não adicionar chamada MCP direta durante o corte, download autenticado, WhatsApp, smartwatch ou promoção automática. Não baixar Reels publicados. Não incluir mídia real, transcrições reais, cookies, tokens, bancos ou modelos no Git. Não tocar a branch principal.

## Arquivos para ler primeiro

`PROJECT_STATE.md`, `HANDOFF_SINCE_CLAUDE_2026-08-21.md`, `CYCLE_42_REPORT_2026-08-21.md`, `CYCLE_40_REPORT_2026-08-21.md`, `RESEARCH_CUTTING_PRECISION_2026-08-21.md`, `RESEARCH_MCP_CHUB_2026-08-21.md`, `FUTURE_PLATFORM_2026-08-21.md`, `modules/editorial_benchmark.py`, `modules/clip_selector.py`, `app.py`, `tests/test_editorial_benchmark.py` e `tests/test_diagnostics_detail.py`.

## Referências

- [`PROJECT_STATE.md`](PROJECT_STATE.md)
- [`HANDOFF_SINCE_CLAUDE_2026-08-21.md`](HANDOFF_SINCE_CLAUDE_2026-08-21.md)
- [`CYCLE_42_REPORT_2026-08-21.md`](CYCLE_42_REPORT_2026-08-21.md)
- [`CYCLE_41_REPORT_2026-08-21.md`](CYCLE_41_REPORT_2026-08-21.md)
- [`CYCLE_40_REPORT_2026-08-21.md`](CYCLE_40_REPORT_2026-08-21.md)
- [`RESEARCH_CUTTING_PRECISION_2026-08-21.md`](RESEARCH_CUTTING_PRECISION_2026-08-21.md)
- [`RESEARCH_MCP_CHUB_2026-08-21.md`](RESEARCH_MCP_CHUB_2026-08-21.md)
- [Branch de trabalho no GitHub](https://github.com/SAGIEV007/furia-clips/tree/claude/repo-access-commits-imgjmk)
