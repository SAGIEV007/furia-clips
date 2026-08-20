# Próximo ciclo — fusão de candidatos Chub + seleção local

## Estado de partida

A release `6.14` está na branch `claude/repo-access-commits-imgjmk`. O snapshot rico do Campaign Hub agora é lido também quando o job recebe `campaign_hub_snapshot_path`; candidatos locais podem herdar blocos, riscos, proveniência e evidência alinhada de locutor. A regra é conservadora: apenas match temporal de pelo menos 75% em bloco `renanSpeaking=true` de tier `owner` ou `allied` fornece `speaker_identity_available=true` como `evidence_only`.

Na fonte real `3XJfcqn56Rw`, com 5.905 segundos, 27 blocos e 66 highlights, o snapshot rico aumentou o recall exploratório genérico em IoU 0,10 de `7,58%` para `27,27%`; no Renan-first, resolveu `3/30` identidades e `3/30` contextos completos contra `0/30` sem snapshot. Em IoU 0,25, o genérico com Chub chegou a `9,09%`, portanto a melhoria de cobertura ainda não equivale a precisão de borda. A concatenação atual colocou propostas guiadas antes do pool local e, no lote Renan-first medido, reduziu o recall exploratório de `10,61%` para `7,58%`.

Lives longas e arquivos crus continuam sendo `processing_source`. Reels e posts publicados continuam `reference_only`. A prioridade é Renan Santos/MBL, mas nenhum sinal do Campaign Hub substitui contexto, payoff, risco, transcrição ou revisão audiovisual.

## Hipótese única

> **Se o Furia separar a fila de descoberta do Campaign Hub da fila de candidatos publicáveis, então poderá preservar highlights de locutor incerto para auditoria sem permitir que eles ocupem o pool Renan-first ou contaminem a seleção pronta para revisão editorial.**

## Procedimento de validação

1. Fixar a fonte `3XJfcqn56Rw`, a fixture do snapshot, a transcrição, a conta `@renansantosmbl`, o perfil editorial, a duração e o orçamento no manifesto do benchmark.
2. Manter duas coleções explícitas: `discovery_candidates`, com todas as seeds e propostas auditáveis, e `publishable_candidates`, com apenas o pool que pode seguir para ranking e revisão.
3. Para cada item da descoberta, registrar `renan_speaking`, origem, intervalo, bloco, highlight, motivo de revisão e motivo de exclusão do pool publicável.
4. Garantir que o modo genérico possa consultar a descoberta sem filtro Renan-first, enquanto o modo Renan-first só promova evidência positiva de locutor e preserve os demais itens em revisão.
5. Medir recall IoU 0,10 e 0,25 separadamente para descoberta e pool publicável, além de contexto, payoff, identidade, duplicação e quantidade de itens filtrados.
6. Criar regressões para seed positiva, seed `false`, seed desconhecida, snapshot sem match, fonte sem snapshot e preservação da proveniência fora do pool publicável.
7. Executar a suíte completa e comparar a fila publicável com a 6.15. Nenhum item de descoberta deve ser tratado como corte aprovado automaticamente.

## Critério de sucesso

A hipótese será confirmada se a fila de descoberta mantiver a cobertura do Chub, enquanto a fila publicável Renan-first não contiver propostas sem evidência positiva de locutor, não perder o recall da 6.15 e preservar a proveniência e o motivo de revisão de cada item excluído.

## Critério de falha

Se a separação esconder propostas, perder highlights legítimos ou permitir que itens sem identidade sejam apresentados como cortes Renan-first prontos, a mudança será revertida. A descoberta pode continuar existindo como diagnóstico, mas não poderá alterar o ranking publicável sem evidência editorial suficiente.

## Escopo excluído

Não treinar modelo vocal, não usar views como aprovação, não consultar MCP durante cada job, não baixar Reels publicados, não misturar contas, não copiar cookies ou tokens, não alterar headlines ou reframe nesta rodada, e não fazer merge na branch principal. O download autenticado da 6.12 permanece uma validação operacional separada.

## Depois da separação

Só depois de estabilizar as duas filas deve ser iniciado o lote de feedback editorial humano. Para cada candidato, registrar aprovação, rejeição, ajuste de borda, locutor, contexto, payoff, headline e formato. O objetivo é medir se o Chub reduz correções reais do editor, não apenas se aumenta recall de um rótulo do próprio Chub.

## Referências

- [`PROJECT_STATE.md`](PROJECT_STATE.md)
- [`DECISIONS.md`](DECISIONS.md)
- [`CYCLE_31_REPORT_2026-08-20.md`](CYCLE_31_REPORT_2026-08-20.md)
- [`CYCLE_30_REPORT_2026-08-20.md`](CYCLE_30_REPORT_2026-08-20.md)
- [`CYCLE_29_REPORT_2026-08-20.md`](CYCLE_29_REPORT_2026-08-20.md)
- [`docs/VERSIONING.md`](../VERSIONING.md)
- [Branch de trabalho no GitHub](https://github.com/SAGIEV007/furia-clips/tree/claude/repo-access-commits-imgjmk)
