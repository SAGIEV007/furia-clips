# Próximo ciclo — fusão de candidatos Chub + seleção local

## Estado de partida

A release `6.14` está na branch `claude/repo-access-commits-imgjmk`. O snapshot rico do Campaign Hub agora é lido também quando o job recebe `campaign_hub_snapshot_path`; candidatos locais podem herdar blocos, riscos, proveniência e evidência alinhada de locutor. A regra é conservadora: apenas match temporal de pelo menos 75% em bloco `renanSpeaking=true` de tier `owner` ou `allied` fornece `speaker_identity_available=true` como `evidence_only`.

Na fonte real `3XJfcqn56Rw`, com 5.905 segundos, 27 blocos e 66 highlights, o snapshot rico aumentou o recall exploratório genérico em IoU 0,10 de `7,58%` para `27,27%`; no Renan-first, resolveu `3/30` identidades e `3/30` contextos completos contra `0/30` sem snapshot. Em IoU 0,25, o genérico com Chub chegou a `9,09%`, portanto a melhoria de cobertura ainda não equivale a precisão de borda. A concatenação atual colocou propostas guiadas antes do pool local e, no lote Renan-first medido, reduziu o recall exploratório de `10,61%` para `7,58%`.

Lives longas e arquivos crus continuam sendo `processing_source`. Reels e posts publicados continuam `reference_only`. A prioridade é Renan Santos/MBL, mas nenhum sinal do Campaign Hub substitui contexto, payoff, risco, transcrição ou revisão audiovisual.

## Hipótese única

> **Se o benchmark registrar separadamente cada seed guiada, cada candidato local enriquecido, cada fusão e cada descarte por gate, então será possível reconciliar o resultado histórico de `27,27%` com o harness atual de `7,58%` e escolher a próxima melhoria sem otimizar contra uma métrica inconsistente.**

## Procedimento de validação

1. Fixar a fonte `3XJfcqn56Rw`, a fixture do snapshot, a transcrição, a conta `@renansantosmbl`, o perfil editorial, a duração e o orçamento em um manifesto de benchmark.
2. Executar quatro condições: genérico sem Chub, genérico com Chub, Renan-first sem Chub e Renan-first com Chub. Salvar a mesma lista de candidatos, não apenas os intervalos finais.
3. Instrumentar as etapas `seeds → propostas → reparos de borda → descarte de não-conteúdo → fusão → anti-overlap → limite final`, contando origem, `renan_speaking`, `context_complete`, `payoff_complete`, `review_required`, intervalo, motivo de descarte e relação com highlight.
4. Reproduzir o benchmark histórico do ciclo 29 com a mesma implementação ou identificar exatamente qual mudança de código, fixture ou configuração explica a diferença. Não comparar resultados de harnesses diferentes como se fossem baseline.
5. Medir recall IoU 0,10 e 0,25, cobertura de blocos, candidatos fundidos, destaques tocados por cada origem, precisão temporal e falsos `renan_confirmado`.
6. Criar regressões para seed positiva, seed `false`, seed desconhecida, proposta fundida, proposta órfã, candidato descartado por overlap e fonte sem snapshot.
7. Só depois da reconciliação escolher a fila de cobertura Chub ou uma nova fusão. Reexecutar a suíte completa e não alterar ranking, quota ou versão se a explicação da divergência continuar aberta.

## Critério de sucesso

A hipótese será considerada confirmada se o mesmo manifesto e a mesma fixture reproduzirem o resultado histórico, ou se a divergência puder ser atribuída a uma diferença documentada e testável. O relatório deve explicar quantos destaques foram encontrados por seeds, por candidatos locais, por evidência fundida e por cada etapa de descarte. Nenhum peso ou quota será alterado apenas para fazer os números coincidirem.

## Critério de falha

Se o resultado continuar divergente sem causa identificável, o benchmark será classificado como não comparável e nenhuma melhoria Chub será publicada com base nele. Se o Chub aumentar apenas a quantidade de candidatos, reduzir recall, criar janelas duplicadas ou aumentar revisão sem elevar cobertura ou identidade, ele continuará como benchmark read-only. Se a fonte não tiver snapshot alinhado, o sistema deve voltar ao caminho local e informar que a memória não foi usada para aquela fonte.

## Escopo excluído

Não treinar modelo vocal, não usar views como aprovação, não consultar MCP durante cada job, não baixar Reels publicados, não misturar contas, não copiar cookies ou tokens, não alterar headlines ou reframe nesta rodada, e não fazer merge na branch principal. O download autenticado da 6.12 permanece uma validação operacional separada.

## Depois da reconciliação

Só depois de reconciliar a medição e estabilizar a fila de cobertura deve ser iniciado o lote de feedback editorial humano. Para cada candidato, registrar aprovação, rejeição, ajuste de borda, locutor, contexto, payoff, headline e formato. O objetivo é medir se o Chub reduz correções reais do editor, não apenas se aumenta recall de um rótulo do próprio Chub.

## Referências

- [`PROJECT_STATE.md`](PROJECT_STATE.md)
- [`DECISIONS.md`](DECISIONS.md)
- [`CYCLE_30_REPORT_2026-08-20.md`](CYCLE_30_REPORT_2026-08-20.md)
- [`CYCLE_29_REPORT_2026-08-20.md`](CYCLE_29_REPORT_2026-08-20.md)
- [`docs/VERSIONING.md`](../VERSIONING.md)
- [Branch de trabalho no GitHub](https://github.com/SAGIEV007/furia-clips/tree/claude/repo-access-commits-imgjmk)
