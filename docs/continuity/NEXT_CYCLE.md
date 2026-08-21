# Próximo ciclo — Furia Clips

## Estado de partida

A release `6.25` está na branch `claude/repo-access-commits-imgjmk`. Ela preserva a observabilidade da 6.21, a recuperação textual Chub da 6.22, o refinamento por palavra e a elegibilidade da 6.23, e o ledger de hard negatives da 6.24. A 6.25 adiciona o contrato `hard-negative-v1` e grava automaticamente um benchmark descritivo separado quando o diagnóstico contém near-misses. A pesquisa acumulada está em `RESEARCH_CUTTING_PRECISION_2026-08-21.md`; o relatório atual está em `CYCLE_41_REPORT_2026-08-21.md`.

A fonte original continua canônica. Reels e posts publicados continuam `reference_only`; lives longas e arquivos crus continuam `processing_source`. O job normal continua offline-first, sem chamada MCP por candidato. O norte imediato segue sendo precisão de cortes e integração Chub/MBL; automações remotas, mensageria e smartwatch permanecem na fase futura.

## Hipótese única

> **Se decisões humanas reais forem associadas aos itens do `hard-negative-v1`, dentro da mesma fonte e com motivo controlado, então o Furia poderá medir falsos negativos e calibrar borda, contexto, payoff e locutor sem confundir aumento de volume com aumento de qualidade.**

A 6.25 não presume que um hard negative seja errado: itens sem decisão permanecem `unlabeled` e `measurement_status=descriptive_only`. O próximo passo é importar decisões humanas aprovadas, rejeitadas e em revisão, preservando `processing_identity`, `transcript_digest`, fonte, formato e intervalo original.

## Procedimento de validação

1. Selecionar uma fonte longa autorizada por família: live solo, entrevista/sabatina, notícia/reação, discurso ou tela/documento.
2. Gerar uma execução com timestamps por palavra e coletar o diagnóstico de seleção, o arquivo `hard-negative-v1` e os candidatos finais.
3. Para cada item, registrar uma decisão humana única: `approved`, `rejected` ou `needs_review`, além de um motivo primário (`contexto`, `payoff`, `speaker`, `timing`, `duplicata`, `não-conteúdo`, `headline`, `visual` ou `outro`).
4. Reexecutar a mesma faixa somente quando necessário e verificar que identidade, digest e intervalos permanecem estáveis.
5. Comparar baseline sem refinamento e refinamento por palavra em erro de início/fim, duração, início natural, contexto autossuficiente, payoff, locutor Renan, headline fiel e taxa de revisão.
6. Medir pares dentro da mesma live: vencedor versus hard negative, com preferência humana separada de saliência/hook.
7. Só depois testar pairwise ranking ou alterar pesos por perfil, conta ou formato.

## Critério de sucesso

O benchmark será considerado calibrável se decisões humanas puderem ser reproduzidas pelo item original, se os motivos permanecerem estáveis e se o mesmo caso não mudar de identidade entre execuções. Uma melhoria editorial será confirmada somente se reduzir falsos negativos ou erro de borda sem aumentar início abrupto, perda de contexto, payoff ausente, falso Renan ou duração inválida.

Nenhuma alteração de ranking será publicada sem before/after no mesmo conjunto congelado e sem separar relevância/autossuficiência de saliência/hook. O contrato pode ser melhorado como instrumento diagnóstico mesmo quando não houver amostra suficiente para ajustar pesos.

## Próximas hipóteses depois desta

A ordem recomendada é: decisões humanas do benchmark; checklist de revisão pela elegibilidade; expansão de candidatos em duas passagens; alinhamento de locutor por fusão de turnos/voz/rosto/Chub; validação visual seletiva; pairwise ranking por conta/formato; headline grounded; presets 9:16/1:1/fake tweet; e reprocessamento seletivo por etapa.

## Escopo excluído

Não alterar pesos do ranking sem benchmark. Não adicionar chamada MCP direta durante o corte, download autenticado, WhatsApp, smartwatch ou promoção automática. Não baixar Reels publicados. Não incluir mídia real, transcrições reais, cookies, tokens, bancos ou modelos no Git. Não tocar a branch principal.

## Arquivos para ler primeiro

`PROJECT_STATE.md`, `HANDOFF_SINCE_CLAUDE_2026-08-21.md`, `CYCLE_41_REPORT_2026-08-21.md`, `CYCLE_40_REPORT_2026-08-21.md`, `RESEARCH_CUTTING_PRECISION_2026-08-21.md`, `RESEARCH_MCP_CHUB_2026-08-21.md`, `FUTURE_PLATFORM_2026-08-21.md`, `modules/editorial_benchmark.py`, `modules/clip_selector.py`, `app.py`, `tests/test_editorial_benchmark.py` e `tests/test_diagnostics_detail.py`.

## Referências

- [`PROJECT_STATE.md`](PROJECT_STATE.md)
- [`HANDOFF_SINCE_CLAUDE_2026-08-21.md`](HANDOFF_SINCE_CLAUDE_2026-08-21.md)
- [`CYCLE_41_REPORT_2026-08-21.md`](CYCLE_41_REPORT_2026-08-21.md)
- [`CYCLE_40_REPORT_2026-08-21.md`](CYCLE_40_REPORT_2026-08-21.md)
- [`RESEARCH_CUTTING_PRECISION_2026-08-21.md`](RESEARCH_CUTTING_PRECISION_2026-08-21.md)
- [`RESEARCH_MCP_CHUB_2026-08-21.md`](RESEARCH_MCP_CHUB_2026-08-21.md)
- [Branch de trabalho no GitHub](https://github.com/SAGIEV007/furia-clips/tree/claude/repo-access-commits-imgjmk)
