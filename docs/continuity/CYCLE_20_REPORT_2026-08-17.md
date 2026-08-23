# Ciclo 20 — Orçamento de candidatos governado pela fonte, não por um teto fixo

**Data:** 17 de agosto de 2026
**Projeto:** Furia Clips
**Branch:** `claude/repo-access-commits-imgjmk`
**Baseline:** release 2.9, commit `10c1fad`
**Release:** 3.0

## Objetivo e hipótese

> Se o orçamento de candidatos deixar de ser um teto fixo e passar a acompanhar a
> duração da fonte, então os destaques hoje intocados entrarão no alcance da seleção
> **sem que a precisão caia**, porque o desperdício em não-conteúdo já foi eliminado
> na release 2.9.

Precisão é a restrição da rodada, não um efeito colateral aceitável. A hipótese só
seria aprovada se o recall subisse **e** a precisão se mantivesse.

## Como a precisão virou número

O benchmark da 2.9 media recall e desperdício, mas não media precisão. Sem isso,
qualquer aumento de quantidade seria indistinguível de aumento de lixo. Duas medidas
foram acrescentadas antes de tocar no teto:

| Medida | Definição |
| --- | --- |
| `precision_on_block` | Fração de candidatos cuja maioria da janela cai dentro de um bloco QA-gated do Acervo. |
| `off_block_candidates` | Candidatos que não tocam nenhum bloco. |

Os blocos não cobrem 100% da fonte, então estar fora de bloco não é automaticamente
errado — é **não endossado**, e o relatório informa assim, sem transformar a métrica
em veredito.

## Varredura do teto

Mesma fonte da 2.9 (`3XJfcqn56Rw`, 98 minutos, 27 blocos, 66 destaques), caminho
guiado e filtro de não-conteúdo ativos:

| Teto | Candidatos | Destaques | Blocos | `precision_on_block` | Fora de bloco | IoU |
| --- | --- | --- | --- | --- | --- | --- |
| 20 | 20 | `18/66` | `10/27` | **1.00** | 0 | 0.0772 |
| 40 | 40 | `27/66` | `20/27` | **1.00** | 0 | 0.1600 |
| 60 | 60 | `30/66` | `22/27` | **1.00** | 0 | 0.1951 |
| 80 | 80 | `33/66` | `23/27` | **1.00** | 0 | 0.2127 |
| 120 | 120 | `50/66` | `25/27` | **1.00** | 0 | 0.2730 |
| 160 | **121** | `50/66` | `25/27` | **1.00** | 0 | 0.2730 |

Três leituras:

1. **A precisão não se move.** `precision_on_block` fica em `1.00` em todos os tetos e
   nenhum candidato cai fora de bloco. Aumentar a quantidade não produziu lixo.
2. **O IoU sobe junto com a quantidade**, de `0.0772` a `0.2730`. Mais candidatos
   melhoraram o alinhamento, não o contrário.
3. **A oferta satura em 121.** Elevar o teto de 120 para 160 não produziu um único
   candidato a mais. O pipeline para sozinho quando o material acaba — o teto não
   estava contendo excesso, estava cortando material aprovado.

## O defeito no cálculo do orçamento

```python
max_clips = min(36, max(15, int(span // 240) + 6)) if span >= 120 else 15
```

O termo `min(36, ...)` domina em qualquer fonte com mais de 2 horas:

| Fonte | Orçamento antigo | Orçamento novo |
| --- | --- | --- |
| 20 minutos | 15 | 32 |
| 98 minutos (o caso medido) | 30 | 137 |
| 2 horas | 36 | 166 |
| 3 horas | 36 | 246 |
| 4 horas | **36** | 326 |

Uma live de 4 horas recebia praticamente a mesma cota de uma de 1 hora. Quanto mais
longa a fonte, maior a fração dela que nunca era examinada — exatamente o oposto do
objetivo do produto.

O novo cálculo usa `SECONDS_PER_CANDIDATE = 45`, calibrado pela saturação observada
(121 candidatos em 5905s ≈ um por 49s), com piso `MIN_CANDIDATE_BUDGET = 15` e válvula
de segurança `MAX_CANDIDATE_BUDGET = 400`. O teto superior não é decisão editorial:
é proteção contra entrada patológica. Quem decide o que sobrevive são os gates.

**Não existe quantidade mínima.** O orçamento é um limite, nunca uma meta: o pipeline
encerra sozinho quando o material acaba, como a saturação em 121 demonstra.

## Resultado

No orçamento que a produção passa a usar para essa fonte (137):

| Métrica | Release 2.9 | Release 3.0 |
| --- | --- | --- |
| Destaques recuperados | `27/66` | **`50/66`** |
| Blocos alcançados | `20/27` | **`25/27`** |
| `precision_on_block` | `1.00` | **`1.00`** |
| Candidatos fora de bloco | 0 | **0** |
| Candidatos em não-conteúdo | 0 | **0** |
| IoU médio | `0.1600` | **`0.2730`** |
| Duração média | `29.73s` | `31.18s` |

O recall quase dobrou e nenhuma medida de precisão se moveu.

Somando as três rodadas na mesma fonte: `11/66` na seleção local, `24/66` com a ponte
do Campaign Hub, `27/66` com o descarte de não-conteúdo e `50/66` com o orçamento
corrigido — **4,5× o ponto de partida**, com precisão `1.00` do começo ao fim.

## Validação

| Verificação | Resultado |
| --- | --- |
| Suíte completa | **343 aprovados, 7 falhas ambientais** |
| Suíte antes da rodada | 338 aprovados, 7 falhas |
| `compileall` | aprovado |
| `node --check static/js/app.js` | aprovado |
| `git diff --check` | aprovado |
| Segredos, mídia e transcrições | nada versionado |

As 5 regressões novas estão em `tests/test_candidate_budget.py` e travam o piso, o
crescimento com a duração, a válvula de segurança, a entrada inválida e — o defeito
corrigido — o fato de 2h e 4h não poderem mais devolver o mesmo número.

## Classificação das conclusões

| Classificação | Conclusão |
| --- | --- |
| Confirmado | A precisão não depende do teto: `precision_on_block` = `1.00` de 20 a 160 candidatos, sempre com zero candidatos fora de bloco. |
| Confirmado | A oferta satura em 121 nesta fonte; o teto cortava material já aprovado pelos gates. |
| Confirmado | O cálculo antigo dava a uma fonte de 4 horas a mesma cota de uma de 1 hora. |
| Corrigido | Recall de `27/66` para `50/66` e cobertura de `20/27` para `25/27`, sem perda de precisão. |
| Reproduzido | As 7 falhas ambientais da suíte. |
| Não verificado | Se `50/66` e `precision_on_block = 1.00` se sustentam em outras fontes; um único vídeo foi medido. |
| Não verificado | O efeito do orçamento maior no tempo de processamento de uma fonte de 3–4 horas. |
| Bloqueado | Renderização e validação FFprobe; `ffmpeg` não existe neste container. |

Uma observação metodológica: `mean_best_iou` compara a janela do candidato com o
**bloco inteiro**. Um corte de 31s dentro de um bloco de 500s nunca terá IoU alto, e
não deveria ter — o IoU contra bloco serve como proxy de cobertura, não como alvo de
recorte. Nenhum bloco passou de `0.6`, e isso não é defeito.

## Próxima hipótese única

> **Se os 16 destaques ainda intocados forem examinados um a um, a causa será
> estrutural — blocos curtos, fala de terceiro ou frases isoladas — e não falta de
> orçamento, porque a oferta já satura antes do teto.**

Os dois blocos ainda não alcançados são curtos (`51s` e `27s`), e os 16 destaques
perdidos continuam **inteiramente** intocados: zero parciais em todas as rodadas. O
Furia nunca truncou uma ideia nesta fonte; ele deixa regiões inteiras de fora. A
próxima rodada deve descobrir o que essas regiões têm em comum.

Os sinais do Acervo registrados na 2.9 e ainda não consumidos continuam disponíveis:
`speakers_note`, `corpus_verdict`/`corpus_keep`, `pauta_temporality`,
`audio_check_ranges` e `self_contained_reason`.
