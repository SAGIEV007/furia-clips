# Próximo ciclo

## Estado de partida

A release `6.17` está na branch `claude/repo-access-commits-imgjmk`, aguardando apenas o commit e a publicação finais deste ciclo. A 6.17 preserva o filtro Renan-first e a separação de descoberta/publicação da 6.16. O editor agora pode informar uma faixa de fonte em segundos, `mm:ss` ou `hh:mm:ss`; o Furia cria uma cópia temporária, processa a timeline local e devolve também `source_start`, `source_end` e `processing_interval`.

A fonte original continua canônica. Reels e posts publicados continuam `reference_only`; lives longas e arquivos crus continuam `processing_source`. Nenhum snapshot do Campaign Hub é consultado durante o job normal fora dos arquivos locais autorizados. A interface visual consultada foi `manus/rebuild-opus-parity-2`; apenas padrões visuais/UX foram considerados.

## Hipótese única

> **Se cada execução parcial receber uma identidade persistente de intervalo no banco e nos bundles editoriais, então a deduplicação poderá comparar somente a mesma faixa da fonte, evitando tanto duplicatas na faixa já processada quanto o bloqueio indevido de faixas diferentes.**

## Procedimento de validação

1. Fixar uma fonte local curta e uma fonte longa autorizada, além de duas faixas não sobrepostas e uma faixa repetida.
2. Definir um identificador estável composto por assinatura da fonte original, início, fim e versão do contrato de intervalo; nunca usar o caminho da cópia temporária como identidade.
3. Persistir o identificador no projeto, no bundle de transcrição, nos diagnósticos e nos clips gerados sem incluir mídia, transcrição real ou credenciais no Git.
4. Executar a mesma faixa duas vezes e confirmar que fingerprints equivalentes são evitados; executar uma faixa diferente e confirmar que seus candidatos não são bloqueados pela primeira.
5. Reexecutar o fluxo integral sem intervalo e confirmar que a deduplicação e o ranking atuais permanecem iguais.
6. Criar regressões para intervalo vazio, início/fim parcial, faixas adjacentes, fonte substituída, caminho temporário removido e fonte inteira.
7. Só depois retomar a visualização read-only da fila de descoberta Chub, com filtros por locutor, bloco, highlight e motivo de exclusão; a visualização não poderá renderizar nem aprovar.

## Critério de sucesso

A hipótese será confirmada se duas execuções da mesma faixa compartilham a identidade e evitam duplicatas, enquanto faixas diferentes da mesma live continuam independentes. A fonte inteira deve conservar o comportamento anterior e nenhum gate Renan-first, contexto, payoff, risco ou Campaign Hub pode ser relaxado.

## Critério de falha

Se a identidade depender do caminho temporário, colidir entre fontes com o mesmo nome, bloquear faixas distintas, vazar conteúdo sensível ou alterar o ranking integral, a mudança será revertida. Nesse caso, a deduplicação parcial continuará desativada até existir um contrato seguro.

## Escopo excluído

Não alterar pesos do ranking, quota Chub, bordas temporais, diarização, headlines, reframe, download autenticado ou integração MCP. Não baixar Reels publicados. Não adicionar rotas de promoção automática. Não tocar a branch principal.

## Arquivos para ler primeiro

`PROJECT_STATE.md`, `CYCLE_33_REPORT_2026-08-20.md`, `DECISIONS.md`, `REFERENCE_UX_NOTES_2026-08-20.md`, `INTERVAL_UX_CHECK_2026-08-20.md`, `modules/source_interval.py`, `tests/test_source_interval.py` e `docs/VERSIONING.md`.

## Referências

- [`PROJECT_STATE.md`](PROJECT_STATE.md)
- [`DECISIONS.md`](DECISIONS.md)
- [`CYCLE_33_REPORT_2026-08-20.md`](CYCLE_33_REPORT_2026-08-20.md)
- [`CYCLE_32_REPORT_2026-08-20.md`](CYCLE_32_REPORT_2026-08-20.md)
- [`REFERENCE_UX_NOTES_2026-08-20.md`](REFERENCE_UX_NOTES_2026-08-20.md)
- [`INTERVAL_UX_CHECK_2026-08-20.md`](INTERVAL_UX_CHECK_2026-08-20.md)
- [`docs/VERSIONING.md`](../VERSIONING.md)
- [Branch de trabalho no GitHub](https://github.com/SAGIEV007/furia-clips/tree/claude/repo-access-commits-imgjmk)
