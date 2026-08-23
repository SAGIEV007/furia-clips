# Ciclo 22 — Interpretação própria: o Furia deixa de depender do rótulo alheio

**Data:** 17 de agosto de 2026
**Branch:** `claude/repo-access-commits-imgjmk`
**Baseline:** release 3.1, commit `a170aab`
**Release:** 3.2

## O problema

As releases 2.9 a 3.1 melhoraram muito o Furia usando os rótulos do Acervo: blocos,
destaques e regiões sem conteúdo. Mas essa inteligência é **emprestada**. Ela existe
apenas para vídeos que o Acervo já processou.

O tamanho exato da dependência foi medido na 2.9, sem que se percebesse na hora:

| | Furia sozinho | Furia com o Acervo |
| --- | --- | --- |
| Destaques recuperados | `11/66` | `50/66` |
| Candidatos desperdiçados | 14 de 40 | 0 |

**O rótulo alheio vale 4,5×.** Numa fonte nova, tudo isso desaparece.

> **Hipótese:** se o Furia produzir sozinho, a partir da transcrição, uma estrutura
> temática comparável à do Acervo, ele deixa de depender de rótulo externo — e a
> concordância com o Acervo pode ser medida em vez de suposta.

## Primeira tentativa — falhou, e a falha foi útil

O caminho inicial foi reconhecer **não-conteúdo por vocabulário**: saudações, pedidos
de like, conversa de produção, jingles.

| Fonte | Recall do não-conteúdo | Precisão |
| --- | --- | --- |
| Live 98 min | **3.4%** | 24% |
| Entrevista 31 min | **9.5%** | 100% |

Inaceitável, e a lista de palavras não foi ajustada até o número subir. O motivo da
falha estava nos próprios rótulos: *"transição e conversa casual com analogias"*,
*"reação e comemoração"*, *"comentário fragmentário"*. São julgamentos sobre **haver
ou não um argumento sustentado**, não sobre quais palavras aparecem. Conversa casual
com uma analogia sobre Pokémon não tem palavra-chave.

A falha revelou que o problema estava mal formulado. O Acervo declara
`tempo total = tempo em blocos + tempo fora de bloco`, com `accountingConsistent`.
**Região sem conteúdo é simplesmente o que sobra fora dos blocos.** A capacidade real
não é reconhecer lixo: é **segmentar a fonte em unidades temáticas**.

## Segunda formulação — segmentação por coesão lexical

`modules/topic_segmenter.py` compara o vocabulário das frases antes e depois de cada
intervalo. Um vale de coesão é uma troca de assunto. Frases funcionais são removidas,
porque mantê-las achata a curva e apaga as fronteiras.

A primeira calibração fragmentou demais: 141 unidades para 27 blocos. Uma varredura
de parâmetros mostrou o teto real da abordagem e onde ela fica:

| `min_sentences` | limiar | Unidades | Blocos cobertos ≥50% | Precisão temporal |
| --- | --- | --- | --- | --- |
| 8 | 0.5 | 141 | 12/27 (44%) | 80% |
| 16 | 1.0 | 73 | 20/27 (74%) | 76% |
| 24 | 1.0 | 59 | 22/27 (81%) | 76% |
| **32** | **1.0** | **46** | **23/27 (85%)** | **72%** |
| 48 | 1.0 | 35 | 23/27 (85%) | 69% |

## Validação em fonte reservada

A calibração usou apenas a live de 98 minutos. A entrevista de 31 minutos **nunca
entrou na calibração** e foi medida com os mesmos parâmetros:

| | Live 98 min (calibração) | Entrevista 31 min (reservada) |
| --- | --- | --- |
| Blocos reais do Acervo | 27 | 11 |
| Unidades detectadas | 46 | 15 |
| **Blocos cobertos ≥50%** | **23/27 (85%)** | **9/11 (82%)** |
| **Precisão temporal** | **75%** | **85%** |

A fonte reservada teve desempenho igual em cobertura e **melhor** em precisão. Não é
ajuste a um caso particular.

## Um defeito conceitual encontrado pelos testes

A medida de repetição contava **palavras isoladas**, para pegar jingles. Mas um bloco
realmente sobre tributação repete "imposto" o tempo todo: qualquer argumento focado
era marcado como jingle. A medida passou a contar **sequências de quatro palavras** —
um canto repete a frase inteira, um argumento repete o termo em frases novas.

A correção melhorou a precisão temporal nas duas fontes reais, de 72% para 75% e de
81% para 85%.

## Implementações

| Arquivo | Alteração |
| --- | --- |
| `modules/topic_segmenter.py` | Novo. Curva de coesão, detecção de fronteiras por vale e julgamento de cada unidade. |
| `modules/non_content_detector.py` | Novo. Pontua indícios de não-conteúdo: abertura, encerramento, engajamento, produção, repetição de frase, legenda ininteligível e fala esparsa. |
| `tests/test_topic_segmenter.py` | Oito regressões. |

O detector é deliberadamente conservador: descartar fala real é pior que manter um
candidato fraco, então um indício decisivo sozinho basta, ou dois independentes
precisam concordar.

## Validação

| Verificação | Resultado |
| --- | --- |
| Suíte completa | **355 aprovados, 7 falhas ambientais** |
| Suíte antes da rodada | 347 aprovados, 7 falhas |
| `compileall`, `node --check`, `git diff --check` | aprovados |
| Segredos, mídia e transcrições | nada versionado |

## Classificação das conclusões

| Classificação | Conclusão |
| --- | --- |
| Confirmado | Reconhecer não-conteúdo por vocabulário não funciona: 3.4% de recall na fonte principal. |
| Confirmado | Região sem conteúdo é o complemento dos blocos; o problema é segmentação. |
| Corrigido | O Furia produz estrutura temática própria com 85% e 82% de cobertura dos blocos do Acervo em duas fontes. |
| Corrigido | Repetição medida por sequência, e não por palavra, deixou de confundir argumento focado com jingle. |
| Reproduzido | As 7 falhas ambientais da suíte. |
| **Não verificado** | **O segmentador ainda não está ligado ao seletor.** Esta rodada entrega e mede a capacidade; usá-la no lugar do snapshot é a rodada seguinte. |
| Não verificado | Fontes de 3–4 horas. A mais longa medida tem 98 minutos. |

Uma limitação honesta: o julgamento `carries_subject` é mais restritivo que a
segmentação. Contando só as unidades marcadas com assunto, a cobertura cai para 18/27
e 7/11. As fronteiras estão boas; o filtro de mérito ainda não está calibrado.

## Próxima hipótese única

> **Se o seletor usar o segmentador próprio quando não houver snapshot autorizado,
> então o recall de uma fonte não rotulada subirá acima do baseline `11/66` sem que a
> precisão caia — e o Furia funcionará em qualquer vídeo, não só nos do Acervo.**

A calibração de `carries_subject` deve vir junto, medida contra as mesmas duas fontes.
