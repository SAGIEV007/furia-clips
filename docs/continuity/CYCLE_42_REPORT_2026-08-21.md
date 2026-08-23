# Relatório do ciclo 42 — Furia Clips 6.26

**Data:** 2026-08-21
**Branch:** `claude/repo-access-commits-imgjmk`
**Hipótese única:** decisões humanas reais devem entrar no benchmark `hard-negative-v1` por um histórico append-only, com conflitos explícitos e adjudicação separada, para preparar medição editorial sem alterar pesos do ranking.

## Contexto

A 6.25 tornou os near-misses do seletor persistentes em um benchmark local, mas ainda não havia uma forma segura de devolver ao sistema as decisões do editor depois da geração dos cortes. Sem essa ponte, o ledger servia apenas para observação; não havia caminho reprodutível para acumular `approved`, `rejected` e `needs_review` dentro da mesma fonte.

A pesquisa da rodada reforçou uma restrição importante: bordas temporais e qualidade de momentos em vídeo têm ambiguidade editorial. Portanto, o sistema não deve tratar uma última escrita como verdade nem apagar decisões divergentes. A referência acadêmica e o contrato proposto estão em [`RESEARCH_HUMAN_DECISIONS_2026-08-21.md`](RESEARCH_HUMAN_DECISIONS_2026-08-21.md).

## Implementação

`modules/editorial_benchmark.py` agora contém `apply_hard_negative_decisions()`. A função valida o schema `hard-negative-v1`, rejeita IDs que não existem, limita campos textuais, anexa eventos a `decision_history` e preserva o payload original. O item passa a declarar `decision_state` como `unlabeled`, `labeled`, `conflict` ou `adjudicated`, além de `decision_conflict`.

Quando dois eventos não adjudicados possuem decisões divergentes, o item fica explicitamente em `conflict` e sua decisão efetiva é `needs_review`. Uma decisão com `adjudication=true` resolve o estado, mas não remove os votos anteriores. O benchmark recalcula contagens de decisão, estados, conflitos e status humano, mantendo `measurement_status=descriptive_only`.

A criação inicial do benchmark também foi ajustada para registrar no histórico as decisões fornecidas no próprio momento da criação. Assim, a primeira importação não precisa inferir retrospectivamente a origem de uma decisão.

`app.py` expõe `POST /api/editorial/benchmark/<benchmark_id>/decisions`. O endpoint aceita `decisions` como mapa indexado pelo ID ou lista de objetos com `id`, além de `annotator_id`, `source` e `decided_at`. A resposta devolve apenas resumo de revisão, contagens e arquivo persistido; não devolve transcrição integral, mídia, cookies, tokens ou credenciais.

## Garantias preservadas

| Área | Resultado da rodada |
| --- | --- |
| Ranking e pesos | Não alterados |
| Gates Renan-first, Chub e locutor | Não alterados |
| Benchmark b354-v1 | Compatível e separado do hard-negative-v1 |
| Privacidade | Sem mídia, transcrição completa, tokens, cookies, credenciais ou modelos no Git |
| Conflitos | Explícitos; não resolvidos pelo último escritor |
| Adjudicação | Opcional, explícita e sem apagar histórico |
| Medição | Continua descritiva; nenhuma precisão/recall humano foi inventado |

## Validação

As regressões editoriais, de aplicação e diagnóstico passaram com **45 testes aprovados** após a implementação. O conjunto editorial/aplicação passou com **40 testes aprovados** depois da correção de indentação da cobertura existente. A suíte completa terminou com **594 aprovados e 4 ignorados**. Também passaram `py_compile`, `node --check` e `git diff --check`. O modelo BlazeFace foi baixado apenas durante o teste, teve o SHA-256 conferido e foi removido; a primeira checagem retornou código não-zero somente porque verificou a ausência antes do `trap` de limpeza, e a verificação posterior confirmou que o asset não permaneceu no checkout.

Ainda não houve decisão humana de uma live real nesta rodada. Portanto, a 6.26 entrega a infraestrutura para calibração, não uma alegação de ganho de precisão. O próximo experimento deve importar decisões reais do mesmo arquivo de benchmark, medir acordo/conflito e só então avaliar ajustes.

## Próximo passo

O próximo ciclo deve congelar uma fonte longa, coletar decisões por motivo (`contexto`, `payoff`, `speaker`, `timing`, `duplicata`, `não-conteúdo`, `headline`, `visual` ou `outro`) e produzir uma tabela before/after. Nenhum peso deve ser alterado enquanto essa evidência não existir.

## Referências

1. [Rodriguez-Opazo et al., “Proposal-free Temporal Moment Localization of a Natural-Language Query in Video using Guided Attention”, WACV 2020 / arXiv](https://arxiv.org/abs/1908.07236)
2. [Gao et al., “Detecting Moments and Highlights in Videos via Natural Language Queries”, NeurIPS 2021](https://proceedings.neurips.cc/paper_files/paper/2021/hash/62e0973455fd26eb03e91d5741a4a3bb-Abstract.html)
3. [“Temporal Sentence Grounding in Videos: A Survey and Future Directions”, IEEE](https://ieeexplore.ieee.org/abstract/document/10075491/)
