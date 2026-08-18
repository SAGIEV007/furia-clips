# Ciclo 26 — O Furia lê temas sozinho, e o léxico deixa de condenar sozinho

**Data:** 18 de agosto de 2026
**Baseline:** release 3.5, commit `0f09f2f`
**Release:** 3.6

## Auditoria que abriu a rodada

Uma pergunta do editor — *o CHUB está realmente entrando no Furia?* — foi respondida
lendo o código, e a resposta era pior do que parecia:

| Capacidade | Estado antes desta rodada |
| --- | --- |
| Reconhecer não-conteúdo | Funcionando, com 8 KB destilados do corpus |
| Dividir a fonte em temas | `topic_segmenter.py` **órfão**: nenhum chamador |
| Locutor, riscos, ranks | Só com snapshot, que a máquina do editor não tem |
| Sumarizar / titular | Não existe; os títulos bons vinham do Gemini |

O segmentador tinha sido construído no ciclo 22, medido em `23/27` e `9/11` blocos
contra o Acervo, documentado — e nunca ligado.

## Ligação do segmentador

`_attach_local_topic_context()` lê a fonte em blocos temáticos a partir da transcrição
e dá a cada candidato o assunto do trecho. Numa execução sobre a live de 98 minutos,
**sem snapshot algum**, produziu 24 blocos e cobriu 100% dos candidatos.

Ele nunca sobrescreve evidência do Acervo. Um bloco endossado pelo Acervo é fato
QA-gated; uma unidade encontrada aqui é a leitura do próprio Furia, e viaja sob a
chave `topic_block`, com `provenance` e `evidence_only`.

## O defeito que a ligação expôs

Com o filtro rodando sobre a fonte inteira, 6 candidatos foram descartados. Conferidos
contra o gabarito do Acervo, **4 estavam errados**:

| Descarte | Veredito real | Bloco do Acervo atingido |
| --- | --- | --- |
| pedido de like | lixo ✓ | — |
| saudação de abertura | lixo ✓ | — |
| "guerra / 40.000" | **conteúdo** | Partido Missão mobiliza ato na USP |
| "livro amarelo" | **conteúdo** | Da live diária à candidatura |
| "Voto 14" | **conteúdo** | Partido Missão mobiliza ato na USP |
| "Lula e Bolsonaro / futuro" | **conteúdo** | Brasil seguro, próspero e entre as cinco nações |

O último é o bloco que o editor havia usado para abrir o trabalho com o Acervo.

Os `4.3%` de dano agregado medidos na 3.4 escondiam isso: numa execução concreta, a
taxa de falso positivo foi de **4 em 6**.

## Diagnóstico e correção

Os três falsos positivos com léxico dispararam **por `lexico_aprendido` sozinho**, e os
termos dizem o porquê:

| Trecho | Termos que dispararam | O que era |
| --- | --- | --- |
| guerra / 40.000 | `aplicativo`, `app`, `org` | o aplicativo da campanha |
| livro amarelo | `live` ×6 | a origem do partido, contada na live |
| Voto 14 | `códigos`, `chat` | os códigos de voto |

Os dois acertos, em contraste, tinham **dois indícios independentes**.

Vocabulário de campanha pertence ao assunto tanto quanto à propaganda. O léxico virou
prova de dois níveis, com ambos os valores lidos de material medido:

- `LEARNED_NON_CONTENT_THRESHOLD = 0.15` — conta como **um** indício, precisa de outro;
- `LEARNED_NON_CONTENT_DECISIVE = 0.45` — sozinho basta.

O anúncio real de patrocínio marca `0.579`; o falso positivo mais denso marcou `0.337`.
A regra separa os dois sem tocar em nenhum dos casos anteriores.

## Resultado

Nos oito trechos reais usados como referência — dois lixos confirmados, o anúncio de
patrocínio e cinco passagens editoriais — a decisão ficou **8 de 8 correta**.

| Fonte | Dano ao conteúdo real, antes | Depois |
| --- | --- | --- |
| Live 98 min | 4.3% | **2.1%** |
| Entrevista 31 min | 0.9% | **0.9%** |

O recall do não-conteúdo permanece baixo (`4.8%` e `27.2%`), o que é a consequência
aceita: descartar fala real é pior que manter um candidato fraco.

## Validação

| Verificação | Resultado |
| --- | --- |
| Suíte completa | **367 aprovados, 7 falhas ambientais** |
| `compileall`, `node --check`, `git diff --check` | aprovados |

Uma regressão nova falhou por fixture irreal — uma frase inventada e saturada de
termos de campanha pontua muito acima da fala real. Foi substituída pelo texto
verbatim do vídeo, em `4897s`.

## Classificação das conclusões

| Classificação | Conclusão |
| --- | --- |
| Confirmado | `topic_segmenter` estava órfão desde o ciclo 22; nenhuma chamada no código. |
| Confirmado | Em execução real, 4 dos 6 descartes atingiam blocos endossados pelo Acervo. |
| Confirmado | Os falsos positivos vinham todos do léxico sozinho; os acertos, de dois indícios. |
| Corrigido | O Furia lê a fonte em blocos temáticos próprios, sem snapshot; 24 blocos e 100% dos candidatos com assunto na live de 98 min. |
| Corrigido | O léxico deixou de condenar sozinho abaixo de `0.45`; 8 de 8 nos trechos de referência e dano na live reduzido pela metade. |
| Não verificado | Comportamento em job real do editor. |
| Aberto | Os `topic_terms` são as palavras mais frequentes do trecho, não um resumo. Servem para agrupar, não para titular. |
| Aberto | Sumarização e headline continuam sem implementação própria. |

## Próxima hipótese única

> **Se os 12 candidatos adiados pelo gate numa execução real forem examinados um a um,
> ficará claro se o limite para chegar a 20–30 cortes por dia está no gate, no
> orçamento ou na renderização — hoje indistinguíveis.**
