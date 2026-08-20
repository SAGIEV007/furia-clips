# Próximo ciclo — fusão de candidatos Chub + seleção local

## Estado de partida

A release `6.14` está na branch `claude/repo-access-commits-imgjmk`. O snapshot rico do Campaign Hub agora é lido também quando o job recebe `campaign_hub_snapshot_path`; candidatos locais podem herdar blocos, riscos, proveniência e evidência alinhada de locutor. A regra é conservadora: apenas match temporal de pelo menos 75% em bloco `renanSpeaking=true` de tier `owner` ou `allied` fornece `speaker_identity_available=true` como `evidence_only`.

Na fonte real `3XJfcqn56Rw`, com 5.905 segundos, 27 blocos e 66 highlights, o snapshot rico aumentou o recall exploratório genérico em IoU 0,10 de `7,58%` para `27,27%`; no Renan-first, resolveu `3/30` identidades e `3/30` contextos completos contra `0/30` sem snapshot. Em IoU 0,25, o genérico com Chub chegou a `9,09%`, portanto a melhoria de cobertura ainda não equivale a precisão de borda. A concatenação atual colocou propostas guiadas antes do pool local e, no lote Renan-first medido, reduziu o recall exploratório de `10,61%` para `7,58%`.

Lives longas e arquivos crus continuam sendo `processing_source`. Reels e posts publicados continuam `reference_only`. A prioridade é Renan Santos/MBL, mas nenhum sinal do Campaign Hub substitui contexto, payoff, risco, transcrição ou revisão audiovisual.

## Hipótese única

> **Se o Furia fundir propostas guiadas pelo Campaign Hub e candidatos locais por sobreposição temporal, deduplicação e quota de origem antes do ranking, então o ganho de cobertura do Chub será preservado sem reduzir o recall Renan-first nem empurrar candidatos guiados de baixa confiança para o topo.**

## Procedimento de validação

1. Reproduzir a mesma fonte `3XJfcqn56Rw` com quatro condições: genérico sem Chub, genérico com Chub, Renan-first sem Chub e Renan-first com Chub.
2. Medir o baseline atual com 30 candidatos, separando `campaign_hub_guided`, `local_primary`, `local_fallback`, identidade, contexto, payoff, revisão e riscos.
3. Implementar uma fusão que mantenha candidatos de ambas as origens, remova duplicatas por IoU e similaridade textual, e imponha uma quota inicial limitada para propostas guiadas. A quota deve ser proporcional à cobertura confiável do snapshot, não fixa para todos os vídeos.
4. Ordenar o pool fundido por gates primeiro. Entre candidatos elegíveis, usar contexto, payoff, identidade, risco, densidade e somente depois prior histórico. `third_party` e `critical` permanecem em revisão.
5. Comparar recall exploratório em IoU 0,10 e 0,25, precisão temporal, duplicação, contexto completo, payoff, identidade, taxa de revisão e número de candidatos que o editor precisaria descartar.
6. Criar regressões para duplicatas entre seed e seleção local, quota cheia, snapshot sem match, snapshot com tier baixo, candidatos em blocos diferentes e fonte sem Chub.
7. Reexecutar a suíte completa, validar o smoke test e classificar o resultado como ganho, neutro ou regressão. Não alterar o ranking global se a fusão não melhorar em fonte real.

## Critério de sucesso

A fusão será considerada melhor se, na fonte real, mantiver ou aumentar recall em IoU 0,10 e 0,25 em relação ao melhor baseline, reduzir duplicatas e não aumentar falsos `renan_confirmado`. O modo genérico não pode perder contexto completo ou precisão. No Renan-first, a taxa de revisão pode continuar alta enquanto não houver evidência suficiente, mas a fila deve ficar mais útil e menos repetitiva.

## Critério de falha

Se o Chub aumentar apenas a quantidade de candidatos, reduzir recall, criar janelas duplicadas ou aumentar revisão sem elevar cobertura ou identidade, reduzir sua quota e mantê-lo como benchmark. Se a fonte não tiver snapshot alinhado, o sistema deve voltar ao caminho local e informar que a memória não foi usada para aquela fonte.

## Escopo excluído

Não treinar modelo vocal, não usar views como aprovação, não consultar MCP durante cada job, não baixar Reels publicados, não misturar contas, não copiar cookies ou tokens, não alterar headlines ou reframe nesta rodada, e não fazer merge na branch principal. O download autenticado da 6.12 permanece uma validação operacional separada.

## Depois da fusão

Só depois de estabilizar a fusão deve ser iniciado o lote de feedback editorial humano. Para cada candidato, registrar aprovação, rejeição, ajuste de borda, locutor, contexto, payoff, headline e formato. O objetivo é medir se o Chub reduz correções reais do editor, não apenas se aumenta recall de um rótulo do próprio Chub.

## Referências

- [`PROJECT_STATE.md`](PROJECT_STATE.md)
- [`DECISIONS.md`](DECISIONS.md)
- [`CYCLE_29_REPORT_2026-08-20.md`](CYCLE_29_REPORT_2026-08-20.md)
- [`docs/VERSIONING.md`](../VERSIONING.md)
- [Branch de trabalho no GitHub](https://github.com/SAGIEV007/furia-clips/tree/claude/repo-access-commits-imgjmk)
