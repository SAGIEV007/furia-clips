# Ciclo 23 — Destilar o Acervo num arquivo local, e medir o que dele é aproveitável

**Data:** 17 de agosto de 2026
**Branch:** `claude/repo-access-commits-imgjmk`
**Baseline:** release 3.2, commit `03e79d0`
**Release:** 3.3

## Objetivo

O Furia deve reconhecer e estruturar um vídeo que o Acervo **nunca processou** — uma
entrevista gravada agora, uma live que ainda não entrou na playlist. Para isso ele
precisa carregar consigo o que o ecossistema aprendeu, sem depender de consulta por
job e sem ocupar disco.

> **Hipótese:** se o corpus rotulado do Acervo for destilado em estatística local
> leve, o Furia reconhecerá não-conteúdo em fonte nova muito acima dos 3.4% que a
> lista de indícios escrita à mão alcançou.

## O corpus disponível

| | |
| --- | --- |
| Vídeos rotulados | 517 |
| Blocos ativos | 16.559 |
| Destaques | 33.900 |
| Regiões sem conteúdo | 15.872 |
| Frases | 885.215 |

A destilação roda no servidor do Chub, em consulta somente leitura: o cálculo de
frequências acontece lá e só a estatística agregada volta. Nenhuma transcrição, URL,
mídia ou dado pessoal é transportado.

## O que foi aprendido

**Léxico de não-conteúdo** — log-odds entre frases dentro de bloco e frases dentro de
região ignorada. O sinal é forte, com termos chegando a `5.05`, e revelou categorias
inteiras que a lista escrita à mão não tinha:

| Categoria descoberta | Termos |
| --- | --- |
| Publicidade e patrocínio | `cupom`, `desconto`, `promoção`, `ofertas`, `sorteio`, `assina`, `oferecimento` |
| Doações e jargão do canal | `pimba`, `pimbas`, `valete`, `valetes`, `jumbito`, `tutu`, `aviãozinho`, `mochila` |
| Divulgação | `inscreva`, `inscrevam`, `notificações`, `compartilhe`, `discord`, `whatsapp`, `pix`, `descrição` |
| Produção | `microfone`, `fone`, `mic`, `estúdios`, `intervalo`, `voltamos` |
| Abertura e encerramento | `olá`, `alô`, `tchau`, `beijo`, `abraço`, `valeu`, `queridos`, `senhoras` |

**Estrutura de bloco** — medida em 16.559 blocos reais: duração mediana `87.6s`
(p10 `22.6s`, p90 `339s`), `25` frases na mediana, `2.0` destaques por bloco e `50.5%`
com `renan_speaking=true`.

**Léxico de destaque — deliberadamente não incluído.** O log-odds dos termos de
destaque contra frases comuns de bloco chega a apenas `0.89`, contra `5.05` do
não-conteúdo. O que torna um trecho um destaque **não está no vocabulário**: os termos
mais fortes são apenas temas (`crime organizado`, `penal`, `fiscal`) e verbos de
proposta (`derrotar`, `reduzir`, `transformar`). Um léxico fraco daria falsa confiança.

O arquivo `data/chub_priors/acervo_priors.json` tem **3 KB**.

## O resultado negativo, medido e mantido como tal

O léxico melhorou o detector, mas pouco:

| Fonte | Indícios escritos à mão | Com léxico aprendido |
| --- | --- | --- |
| Live 98 min | 3.4% | **4.8%** |
| Entrevista 31 min | 9.5% | **23.6%** |

Uma varredura de 18 combinações de limiar e janela encontrou o teto da abordagem:
**11% de recall na live, com 24–31% de precisão**. Nenhum ponto de operação a torna
utilizável.

O erro de granularidade ficou visível: o detector julgava **janelas deslizantes de
quatro frases**, enquanto o Acervo julga **unidades inteiras**. O léxico foi então
testado no nível certo, sobre as unidades do segmentador da release 3.2:

| Fonte | Unidades de conteúdo | Unidades sem conteúdo | Separação |
| --- | --- | --- | --- |
| Live 98 min | 38 (score médio `0.0106`) | 8 (score médio `0.0068`) | **0.6×, invertida** |
| Entrevista 31 min | 14 (`0.0024`) | 1 (`0.0568`) | 23.5×, amostra de um |

Na única fonte com amostra suficiente, **as unidades de conteúdo pontuam mais alto que
as de não-conteúdo**. O sinal por palavra é real, mas não sobrevive à média sobre um
trecho longo: uma live intercala promoção e argumento o tempo todo.

**Decisão:** o score aprendido é calculado e reportado, mas **não participa do
veredito**. Deixá-lo decidir descartaria fala real com base num sinal que foi medido e
não discrimina. A regressão `test_learned_priors_are_reported_but_never_decide` trava
esse contrato.

## Implementações

| Arquivo | Alteração |
| --- | --- |
| `data/chub_priors/acervo_priors.json` | Novo, 3 KB. Léxico de não-conteúdo, estrutura de bloco e proveniência. |
| `modules/non_content_detector.py` | `load_priors()` e `learned_non_content_score()`; o score é evidência, não veredito. Ausência do arquivo mantém o detector funcionando. |
| `tests/test_topic_segmenter.py` | Duas regressões novas. |

## Validação

| Verificação | Resultado |
| --- | --- |
| Suíte completa | **355 aprovados, 7 falhas ambientais** |
| `compileall`, `node --check`, `git diff --check` | aprovados |
| Disco | 3 KB versionados; nenhuma mídia, transcrição ou dado privado |

## Classificação das conclusões

| Classificação | Conclusão |
| --- | --- |
| Confirmado | O corpus é destilável: 885k frases viram 3 KB de estatística agregada e não reversível. |
| Confirmado | O léxico aprendido descobriu categorias reais que a lista manual não tinha, com log-odds até `5.05`. |
| Confirmado | O que torna um trecho um destaque não é lexical: log-odds máximo de `0.89`. |
| **Refutado** | **A hipótese da rodada.** O léxico não leva o detector a um patamar utilizável: teto de 11% de recall, e no nível de unidade a separação é invertida na fonte com amostra suficiente. |
| Corrigido | O score aprendido deixou de influenciar o veredito, para não descartar fala real com base em sinal que não discrimina. |
| Não verificado | Se o léxico funciona no nível da **frase** individual, granularidade em que o log-odds foi calculado e onde ainda não foi testado. |

## Próxima hipótese única

> **Se o léxico for aplicado na granularidade em que foi aprendido — a frase, e não a
> janela nem a unidade — então ele separará conteúdo de não-conteúdo, porque foi
> exatamente essa a comparação que produziu os log-odds.**

A capacidade que já funciona continua sendo a segmentação temática da release 3.2:
`23/27` e `9/11` blocos cobertos, com 75% e 85% de precisão temporal. Ligá-la ao
seletor permanece a entrega de maior valor pendente.
