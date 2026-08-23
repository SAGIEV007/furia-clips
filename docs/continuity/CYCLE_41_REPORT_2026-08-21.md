# Relatório do ciclo 41 — benchmark hard-negative-v1 integrado ao diagnóstico

**Data:** 2026-08-21
**Branch:** `claude/repo-access-commits-imgjmk`
**Versão do ciclo:** `6.25`
**Hipótese:** se os hard negatives do seletor forem convertidos em um contrato versionado, sanitizado e persistente, com decisões humanas opcionais, o Furia poderá medir falsos negativos e calibrar bordas, contexto, payoff e locutor sem confundir uma observação não rotulada com uma aprovação ou rejeição.

## Pesquisa e desenho

A pesquisa adicional revisou o QVHighlights, que separa consulta textual, momentos relevantes e saliência em escala de cinco pontos. A consequência para o Furia é manter `relevance`/autossuficiência separado de `saliency`/força do hook. A avaliação temporal continua usando IoU e erro de borda, mas a qualidade editorial precisa de rótulos separados para contexto, payoff, locutor, risco, headline e formato.

O contrato criado é `hard-negative-v1`. Cada item tem identidade local, motivo do descarte, intervalo, duração, origem, score, confiança, preview textual curto, vencedor opcional e decisão humana opcional. As decisões aceitas são `approved`, `rejected`, `needs_review` e `unlabeled`; qualquer valor desconhecido vira `unlabeled`. Isso impede que uma decisão automática ou campo não reconhecido seja promovido silenciosamente a verdade editorial.

## Implementação

`modules/editorial_benchmark.py` agora expõe `build_hard_negative_benchmark()`. A função normaliza e limita os dados do ledger, preserva `processing_identity` e `transcript_digest`, calcula contagens descritivas de decisões e motivos e registra avisos quando a identidade, digest ou decisão humana faltam. O status de medição é explicitamente `descriptive_only`; não há precisão, recall ou qualidade humana inferida sem rótulos válidos.

`app._write_selection_diagnostics()` agora detecta `candidate_diagnostics["hard_negatives"]`, materializa um arquivo persistente de benchmark em `FuriaClipsData/benchmarks/` e inclui no diagnóstico principal somente um manifesto com schema, ID, contagem e nome do arquivo. O benchmark é separado do JSON de seleção e não contém mídia nem transcrição integral. A integração é opcional: execuções sem hard negatives continuam exatamente no fluxo anterior.

O contrato de benchmark existente `b354-v1` não foi alterado. O novo contrato convive com recall temporal Chub e pode ser usado depois para associar uma decisão humana ao mesmo `processing_identity` e `transcript_digest`.

## Validação

A validação focada do benchmark, diagnóstico, smoke e seletor terminou com **51 aprovados**. A suíte completa terminou com **588 aprovados e 4 ignorados**. Também passaram `py_compile` em `app.py`, `editorial_benchmark.py` e `clip_selector.py`, `node --check` e `git diff --check`. O BlazeFace foi baixado temporariamente para a suíte, conferido pelo hash esperado e removido depois.

As regressões cobrem normalização de itens inválidos, decisões humanas válidas, decisões desconhecidas, itens sem rótulo, avisos de medição descritiva, salvamento persistente, manifesto no diagnóstico, compatibilidade com comparação Chub e limite do ledger original.

## Limites honestos

Nenhum arquivo de live real foi processado nesta rodada e nenhuma decisão humana real foi importada. Portanto, o ciclo não demonstra melhoria editorial, redução de falsos negativos ou ganho de recall. Ele entrega a infraestrutura necessária para que esses ganhos possam ser medidos quando o usuário fornecer decisões aprovadas/rejeitadas ou quando uma execução real gerar near-misses.

A API do Instagram continua retornando 403 por falta de permissão da aplicação na consulta de conta. Nenhum perfil Instagram foi usado como evidência no ciclo. O Campaign Hub continua sendo memória/seed read-only e o job continua offline-first.

## Próxima hipótese

A próxima rodada deve associar decisões humanas reais aos itens do `hard-negative-v1`, construir pares dentro da mesma fonte e medir before/after do refinamento por palavra e do ledger de elegibilidade. Nenhum peso do ranking deve mudar antes de haver amostra suficiente por família de fonte, conta e formato.

## Referências

[1]: https://proceedings.neurips.cc/paper_files/paper/2021/hash/62e0973455fd26eb03e91d5741a4a3bb-Abstract.html "QVHighlights — momentos relevantes e saliência anotados por humanos"
[2]: https://cvpr.thecvf.com/virtual/2026/poster/39067 "FAVE — avaliação audiovisual temporal fina"
[3]: https://aclanthology.org/2025.emnlp-industry.185/ "HIVE — compreensão narrativa e edição de vídeos longos"
