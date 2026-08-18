# Ciclo 25 — Onde o corte começa e onde ele termina

**Data:** 18 de agosto de 2026
**Baseline:** release 3.4, commit `2c6a6c4`
**Release:** 3.5

## O que a segunda execução real mostrou

A mesma sabatina de 47 minutos foi reprocessada na 3.4. O resultado mudou muito:

| | Execução na 3.3 | Execução na 3.4 |
| --- | --- | --- |
| Resposta do Gemini | 2134 chars, **1 candidato** | 12057 chars, **22 candidatos** |
| Títulos | `amarras da revista Cruzoer` | `Renan Santos explica 'prendeu matô'…` |
| Descarte de não-conteúdo | não existia | **2 removidos**, com intervalo e texto no log |

O anúncio do Crusoé e o agradecimento final não aparecem mais entre os cortes. O
filtro local da 3.4 fez o trabalho para o qual foi escrito.

Restaram dois defeitos, relatados pelo editor sobre cortes específicos.

## Os dois defeitos são o mesmo defeito

**O corte melhor ranqueado abria no meio de uma frase.** Começava em `729.5s`, em
*"você atender seus prazeres mais baixos"*. O editor queria `~732s`, em *"O escândalo
do Banco Master"* — e descreveu a correção como **cortar alguns segundos do início**.

**Outro corte terminava exatamente na pergunta.** Ia de `561.8s` a `630.0s`; a
pergunta do repórter fecha em `629.2s` e a resposta começa no mesmo instante. O
espectador recebe a provocação e nunca a resposta.

Os dois são a mesma falha: **os intervalos escolhidos não são ajustados a fronteiras
de frase nem à estrutura pergunta–resposta.**

Existia uma correção parcial, em `_parse_llm_response`, mas ela é estreita por duas
razões. Expande **para trás** um bloco inteiro, e só quando o intervalo entre eles é
de até `2.5s` — o oposto do que o editor pediu. E detecta início-no-meio-da-frase por
uma lista de palavras de continuação; *"você atender…"* começa com `você`, que não
está nela.

## Implementações

| Arquivo | Alteração |
| --- | --- |
| `modules/clip_selector.py` | `_trim_opening_fragment()` avança o início até a primeira frase que se sustenta sozinha; `_close_open_question()` estende o fim até o começo da resposta; constantes `MAX_OPENING_TRIM_S = 15.0` e `MIN_ANSWER_WORDS = 12`. |
| `tests/test_clip_boundaries.py` | Seis regressões, construídas sobre os dois casos reais. |

O início-no-meio-da-frase passou a ser reconhecido por um sinal mais simples e mais
geral: **a legenda abre em minúscula**. Nomes e siglas abrem corte legitimamente, então
apenas o primeiro caractere é consultado.

O tempo dentro de uma linha de legenda é interpolado por posição de caractere, porque
a legenda traz um timestamp por linha e várias frases podem dividir a mesma linha. A
taxa de fala é próxima do uniforme dentro de uma linha, e o deslocamento nunca passa
de `MAX_OPENING_TRIM_S`.

Fragmentos curtos deixados pela ideia anterior também são pulados: *"Não atua."* abre
um corte tão mal quanto meia frase.

## Resultado nos casos reais

| Caso | Antes | Depois | Alvo do editor |
| --- | --- | --- | --- |
| Corte 1 — início | `729.50s`, *"você atender seus prazeres…"* | **`732.28s`**, *"O escândalo do Banco Master…"* | `~732s` |
| Corte 3 — fim | `630.0s`, na pergunta | **`634.5s`**, com o início da resposta | incluir a resposta |

O erro no primeiro caso é de **0.3 segundos** em relação ao ponto pedido.

## Validação

| Verificação | Resultado |
| --- | --- |
| Suíte completa | **364 aprovados, 7 falhas ambientais** |
| Benchmark do Acervo, fonte de 98 min | `50/66` destaques, `25/27` blocos, precisão `1.00`, zero fora de bloco — **inalterado** |
| `compileall`, `node --check`, `git diff --check` | aprovados |

As métricas de cobertura e precisão não se moveram, como esperado: a rodada ajusta
fronteiras, não escolhe janelas diferentes.

## Classificação das conclusões

| Classificação | Conclusão |
| --- | --- |
| Confirmado | O filtro de não-conteúdo da 3.4 funcionou em execução real: o anúncio e o encerramento não voltaram. |
| Confirmado | A correção de início existente expande para trás e por lista de palavras; não cobre o caso relatado. |
| Corrigido | Um corte que abre no meio da frase avança para a primeira frase inteira, com erro de 0.3s no caso real. |
| Corrigido | Um corte que termina na pergunta é estendido até o começo da resposta. |
| Não verificado | O comportamento em execução real; medido sobre os intervalos e as transcrições relatados, não sobre um job novo. |
| Aberto | Títulos herdam erros da legenda automática. `prendeu matô` é a grafia da legenda, e o título a repete. A legenda é auxílio de navegação, nunca citação — títulos construídos sobre ela precisam de conferência no áudio. |
| Aberto | O Estúdio de Headlines, cuja melhoria o editor pediu **depois** de a capacidade de corte estar madura. |

## Próxima hipótese única

> **Se uma execução nova for feita com o relatório de diagnóstico em mãos, os dois
> ajustes de fronteira poderão ser confirmados em job real e o ranqueamento poderá
> enfim ser avaliado sobre uma lista de candidatos já limpa.**
