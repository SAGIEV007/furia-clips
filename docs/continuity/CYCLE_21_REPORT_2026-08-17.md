# Ciclo 21 — De candidato bruto a corte pronto e ranqueado

**Data:** 17 de agosto de 2026
**Projeto:** Furia Clips
**Branch:** `claude/repo-access-commits-imgjmk`
**Baseline:** release 3.0, commit `f83d1fb`
**Release:** 3.1

## Objetivo e hipótese

> Se cada candidato herdar o que o Acervo já estabeleceu sobre o trecho em que ele
> cai, então o revisor deixará de receber janelas anônimas e passará a receber cortes
> que se explicam — com tema, pergunta-gatilho, locutor, riscos e veredito de revisão.

As rodadas 2.9 e 3.0 resolveram **cobertura**: o Furia encontra o material. Esta
rodada trata de **entrega**: 121 candidatos em 98 minutos só viram produto se o
revisor souber, de cada um, o que é e se pode publicar.

## Primeiro: medir se o ranqueamento já funciona

Antes de mexer em qualquer ranking, a pergunta precisava de número. `precision@k` foi
acrescentada ao benchmark: dos `k` primeiros colocados, quantos carregam um destaque
QA-gated, qual a densidade média do bloco e quantos são de blocos com Renan falando.

| Topo | Carrega destaque | Densidade média | Renan falando |
| --- | --- | --- | --- |
| @5 | **100%** | 80.4 | 1 |
| @10 | **100%** | 83.0 | 3 |
| @20 | **100%** | 76.5 | 4 |
| @40 | 62% | 74.65 | 5 |
| geral (121) | 38% | — | — |

**O ranqueamento já funciona.** Os 20 primeiros carregam todos um destaque rotulado,
em blocos de densidade 76–83 de 99. A precisão decai de forma limpa conforme a lista
avança, que é exatamente o comportamento desejado numa fila de revisão.

Isso reordenou o plano da rodada: não havia defeito de ranking para corrigir.

## Renan-first: verificado, não alterado

A fonte tem **3 blocos com `renan_speaking=true` entre 27** — 13% do tempo em bloco e
9% dos destaques. O Furia coloca 4 desses no top 20, ou seja, **20% do topo para 9%
do material disponível**.

O Renan-first já está ativo e sobre-representa o Renan em relação à oferta. Nenhum
peso foi adicionado: mexer aqui seria intervenção sem defeito medido, e o contrato
trata priors do Chub como desempate fraco, nunca como aprovação.

## O defeito real: candidatos anônimos

Apenas os candidatos nascidos de uma seed do Campaign Hub carregavam proveniência. Os
demais — a maioria dos 121 — chegavam ao revisor sem título, sem tema, sem risco e,
principalmente, **sem indicação de quem fala**.

Num acervo em que 24 de 27 blocos têm `renan_speaking=false`, entregar uma janela
anônima é convidar exatamente o erro que o projeto proíbe: publicar como fala do Renan
algo que é fala de terceiro.

## Implementação

| Arquivo | Alteração |
| --- | --- |
| `modules/clip_selector.py` | Novo `_attach_block_evidence()`: todo candidato cuja maioria da janela cai num bloco QA-gated herda o contexto dele. Novo `_block_field()` para ler snapshots nas duas convenções de nome. |
| `scripts/run_acervo_recall_benchmark.py` | Nova métrica `precision_at_k`. |
| `scripts/convert_chub_blocks_export.py` | Preserva `speakers_note`. |
| `tests/test_campaign_hub_guidance.py` | Quatro regressões novas. |

Cada candidato passa a carregar `campaign_hub_block` com título, resumo,
pergunta-gatilho, tópicos, categoria, `density_rank`, `self_contained_rank` e a
justificativa da autossuficiência, `renan_speaking`, `speakers_note`, `risk_flags`,
`gate_warnings`, `trust_tier` e a fração da janela coberta pelo bloco.

O veredito de locutor tem três valores. `renan_confirmado` só quando o Acervo afirma
`true`. `terceiro_ou_indeterminado` quando afirma `false` — que cobre tanto outra
pessoa quanto voz não identificada, e as duas situações proíbem igualmente a
publicação como fala do Renan. `nao_confirmado` quando o campo está ausente.

Qualquer coisa diferente de `renan_confirmado`, ou qualquer risco sinalizado, marca
`review_required=true` com o motivo escrito em português.

O bloco viaja com `evidence_only: true`. Nenhum campo eleva score nem libera gate: a
release 3.1 não altera ranking.

Um defeito foi encontrado pelas próprias regressões: `_attach_block_evidence` lia
apenas nomes em snake_case, enquanto snapshots vindos direto do Acervo usam camelCase.
Ranks, riscos e o veredito de locutor eram silenciosamente perdidos nesse caminho.
`_block_field()` corrige isso lendo as duas convenções.

## Resultado

| Métrica | Release 3.0 | Release 3.1 |
| --- | --- | --- |
| Candidatos com contexto editorial | apenas os guiados | **121 de 121 (100%)** |
| Destaques recuperados | `50/66` | `50/66` |
| Blocos alcançados | `25/27` | `25/27` |
| `precision_on_block` | `1.00` | `1.00` |
| Candidatos fora de bloco | 0 | 0 |
| Desperdício em não-conteúdo | 0 | 0 |
| Top 20 carregando destaque | 100% | 100% |

Nenhuma métrica de cobertura ou precisão se moveu, como esperado: a rodada não mexeu
em seleção nem em ranking.

Exemplo do segundo colocado, como ele chega hoje ao revisor:

```
#2  4385s-4406s (21s)
    bloco    : Número 14: estratégia para tirar Flávio do segundo turno e derrotar Lula
    pergunta : Como Renan pretende tirar Flávio Bolsonaro do segundo turno...
    locutor  : renan_confirmado  (renan_speaking=True)
    ranks    : densidade 99 | autossuficiência 96
    riscos   : ['ataque_pessoal', 'linguagem_ofensiva', 'juridico_sensivel']
    revisão  : True — riscos sinalizados
```

## Validação

| Verificação | Resultado |
| --- | --- |
| Suíte completa | **347 aprovados, 7 falhas ambientais** |
| Suíte antes da rodada | 343 aprovados, 7 falhas |
| `compileall` | aprovado |
| `node --check static/js/app.js` | aprovado |
| `git diff --check` | aprovado |
| Segredos, mídia e transcrições | nada versionado |

## Classificação das conclusões

| Classificação | Conclusão |
| --- | --- |
| Confirmado | O ranqueamento já entrega: 100% dos 20 primeiros carregam um destaque QA-gated, em blocos de densidade 76–83. |
| Confirmado | O Renan-first já opera: 20% do top 20 vem de blocos com Renan falando, contra 9% dos destaques disponíveis. |
| Confirmado | Antes desta rodada, a maioria dos candidatos chegava sem qualquer indicação de locutor. |
| Corrigido | 100% dos candidatos passam a carregar contexto, locutor, riscos e veredito de revisão. |
| Corrigido | Snapshots em camelCase perdiam ranks, riscos e locutor silenciosamente. |
| Reproduzido | As 7 falhas ambientais da suíte. |
| Não verificado | Se o comportamento se mantém em outras fontes; um único vídeo foi medido. |
| Bloqueado | Renderização e FFprobe; `ffmpeg` não existe neste container. |

## Próxima hipótese única

> **Se os 16 destaques ainda intocados forem examinados um a um, a causa será
> estrutural — blocos curtos, frase isolada ou piso de duração — e não falta de
> orçamento, porque a oferta satura antes do teto.**

Os dois blocos ainda não alcançados têm `51s` e `27s`, e o piso de candidato é `20s`.
Em todas as rodadas, os destaques perdidos ficaram **inteiramente** intocados: zero
parciais. O Furia nunca truncou uma ideia nesta fonte.

Sinais do Acervo ainda não consumidos: `corpus_verdict`/`corpus_keep`,
`pauta_temporality` (evergreen versus datado) e `audio_check_ranges`.

---

## Adendo — validação em segunda fonte

A limitação declarada em todas as rodadas anteriores era a mesma: tudo havia sido
medido em **um único vídeo**, então os números podiam ser calibração para um caso
particular. A segunda fonte foi escolhida pelo contraste máximo com a primeira.

| | `3XJfcqn56Rw` | `j9FRVbb8CAI` |
| --- | --- | --- |
| Formato | live, 98 minutos | **entrevista, 31 minutos** |
| Frases | 1951 | 578 |
| Blocos | 27 | 11 |
| Blocos com `renan_speaking=true` | 3 (11%) | **11 (100%)** |
| Destaques | 66 | 34 |
| Regiões sem conteúdo | 20 | 4 |

Resultado com o mesmo código e o mesmo orçamento derivado da duração:

| Métrica | Live 98 min | Entrevista 31 min |
| --- | --- | --- |
| Candidatos | 121 | 43 |
| Destaques recuperados | `50/66` (76%) | **`30/34` (88%)** |
| Blocos alcançados | `25/27` (93%) | **`11/11` (100%)** |
| `precision_on_block` | `1.00` | **`1.00`** |
| Candidatos fora de bloco | 0 | **0** |
| Desperdício em não-conteúdo | 0 | **0** |
| Top 5 / Top 10 com destaque | 100% / 100% | **100% / 100%** |
| Duração média | `31.18s` | `29.81s` |

As três garantias — precisão `1.00`, zero candidatos fora de bloco e zero desperdício
— se mantiveram em um formato completamente diferente. O recall foi **melhor** na
entrevista, o que é coerente: uma entrevista de 31 minutos é mais uniformemente densa
que uma live de 98 minutos com abertura, intervalos e trechos ininteligíveis.

| Classificação | Conclusão |
| --- | --- |
| Confirmado | Precisão `1.00`, zero fora de bloco e zero desperdício não são específicos de uma fonte. |
| Confirmado | O orçamento derivado da duração funciona nos dois extremos testados, de 31 a 98 minutos. |
| Não verificado | Fontes de 3–4 horas, o alvo declarado do produto; a mais longa medida tem 98 minutos. |
