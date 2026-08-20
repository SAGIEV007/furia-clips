# Próximo ciclo — auditoria read-only da descoberta Chub

## Estado de partida

A release `6.16` está na branch `claude/repo-access-commits-imgjmk`. O snapshot rico do Campaign Hub alimenta duas coleções: descoberta auditável e propostas guiadas promovidas. No Renan-first, apenas match com `renanSpeaking=true` entra no pool primário; itens filtrados permanecem visíveis no diagnóstico com motivo de revisão. Candidatos locais podem herdar blocos, riscos, proveniência e evidência alinhada de locutor. A regra continua conservadora: apenas match temporal de pelo menos 75% em bloco `renanSpeaking=true` de tier `owner` ou `allied` fornece `speaker_identity_available=true` como `evidence_only`.

Na fonte real `3XJfcqn56Rw`, com 5.905 segundos, 27 blocos e 66 highlights, a 6.16 registrou 30 propostas de descoberta no Renan-first, promoveu 6 e deixou 24 em `speaker_gate_review`. O recall publicável permaneceu em `7/66` no IoU 0,10 e `1/66` no IoU 0,25; o genérico com Chub permaneceu em `18/66` e `6/66`. Lives longas e arquivos crus continuam sendo `processing_source`. Reels e posts publicados continuam `reference_only`. A prioridade é Renan Santos/MBL, mas nenhum sinal do Campaign Hub substitui contexto, payoff, risco, transcrição ou revisão audiovisual.

## Hipótese única

> **Se o Furia oferecer uma visualização read-only da fila de descoberta Chub, com filtros por locutor, bloco, highlight e motivo de exclusão, então o editor e futuras IAs poderão auditar a cobertura sem transformar propostas incertas em cortes renderizáveis.**

## Procedimento de validação

1. Fixar a fonte `3XJfcqn56Rw`, a fixture do snapshot, a transcrição, a conta `@renansantosmbl`, o perfil editorial, a duração e o orçamento no manifesto do benchmark.
2. Adicionar uma superfície read-only no diagnóstico da seleção para listar `campaign_hub_discovery_candidates` sem permitir renderização direta.
3. Implementar filtros por `renan_speaking`, `publication_status`, `exclusion_reason`, bloco, highlight e intervalo temporal.
4. Exibir a proveniência completa — seed, bloco, highlight, intervalo, gate e motivo — sem expor transcrição real, tokens, cookies ou credenciais.
5. Garantir que qualquer ação futura de promoção reexecute os gates de identidade, contexto, payoff, risco e timing; a visualização não pode funcionar como aprovação.
6. Criar regressões para lista vazia, descoberta com 30 itens, 24 itens em `speaker_gate_review`, modo genérico, snapshot sem match e tentativa de renderização direta.
7. Medir se a visualização reduz diagnósticos ambíguos e acelera a correção editorial. Não alterar pesos, quotas ou bordas temporais nesta rodada.

## Critério de sucesso

A hipótese será confirmada se a visualização mostrar todas as descobertas sem alterar o conjunto publicável, permitir localizar por que uma proposta foi filtrada e mantiver o recall e os gates da 6.16. Nenhuma ação de auditoria deve renderizar ou aprovar automaticamente um item.

## Critério de falha

Se a superfície ocultar itens, misturar descoberta com publicáveis, vazar dados sensíveis, criar uma rota de promoção sem gates ou alterar o ranking, a mudança será revertida. A fila poderá continuar existindo somente no diagnóstico persistido.

## Escopo excluído

Não treinar modelo vocal, não usar views como aprovação, não consultar MCP durante cada job, não baixar Reels publicados, não misturar contas, não copiar cookies ou tokens, não alterar headlines ou reframe nesta rodada, e não fazer merge na branch principal. O download autenticado da 6.12 permanece uma validação operacional separada.

## Depois da auditoria

Só depois de estabilizar a visualização read-only deve ser iniciado o lote de feedback editorial humano. Para cada candidato, registrar aprovação, rejeição, ajuste de borda, locutor, contexto, payoff, headline e formato. O objetivo é medir se o Chub reduz correções reais do editor, não apenas se aumenta recall de um rótulo do próprio Chub.

## Referências

- [`PROJECT_STATE.md`](PROJECT_STATE.md)
- [`DECISIONS.md`](DECISIONS.md)
- [`CYCLE_32_REPORT_2026-08-20.md`](CYCLE_32_REPORT_2026-08-20.md)
- [`CYCLE_31_REPORT_2026-08-20.md`](CYCLE_31_REPORT_2026-08-20.md)
- [`CYCLE_30_REPORT_2026-08-20.md`](CYCLE_30_REPORT_2026-08-20.md)
- [`CYCLE_29_REPORT_2026-08-20.md`](CYCLE_29_REPORT_2026-08-20.md)
- [`docs/VERSIONING.md`](../VERSIONING.md)
- [Branch de trabalho no GitHub](https://github.com/SAGIEV007/furia-clips/tree/claude/repo-access-commits-imgjmk)
