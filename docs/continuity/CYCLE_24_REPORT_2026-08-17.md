# Ciclo 24 — O que os logs de uma execução real revelaram

**Data:** 17 de agosto de 2026
**Baseline:** release 3.3, commit `d2354a9`
**Release:** 3.4

## O que motivou a rodada

O usuário processou a *Sabatina OA!/G4 com Renan Santos* (47 minutos) e enviou os
logs completos. Eles mostraram algo que nenhuma medição anterior tinha visto, porque
todas as medições rodaram **com** um snapshot instalado.

**O painel de blocos mostrava "Memória local indisponível".** Sem snapshot, tudo o que
as releases 2.9 a 3.1 construíram sobre o Campaign Hub — descarte de não-conteúdo,
contexto por bloco, veredito de locutor, caminho guiado — fica **inerte**. As melhorias
existiam e não rodavam.

Os cortes gerados provam o efeito:

| Corte | Intervalo | O que era de fato |
| --- | --- | --- |
| 3 | `2777.9–2805.5` | O anúncio de assinatura do Antagonista/Crusoé |
| 7 | `42.7–214.6` | O VT de abertura, com narração em terceira pessoa |
| 12 | `213.5–307.2` | A saudação de abertura |
| 1 | `2705.1–2746.4` | O agradecimento final |

Além disso, o Gemini recebeu 92 blocos e devolveu **1 candidato** numa resposta de 2134
caracteres; 65 candidatos locais entraram por fallback. Os títulos dos arquivos são
fragmentos no meio da frase.

## Hipótese

> Se o julgamento de não-conteúdo funcionar **sem snapshot**, a partir da transcrição,
> então uma fonte que o Acervo nunca viu deixa de gastar cortes com propaganda,
> abertura e encerramento.

## A correção do léxico, e uma conclusão anterior derrubada

O ciclo 23 concluiu que o léxico aprendido **não discriminava** e o manteve fora do
veredito. Essa conclusão valia para um léxico de 86 termos, pontuado como média sobre
janelas deslizantes.

Testado contra o caso real do usuário, o detector daquela versão falhou nos três
trechos. O anúncio tinha apenas 2 termos conhecidos em ~55 palavras.

O léxico foi então reextraído do corpus com um corte de frequência mais baixo,
chegando a **239 termos**, e passou a cobrir a superfície inteira de propaganda,
produção, divulgação, abertura e encerramento — `assine`, `assinar`, `combo`, `clique`,
`exclusiva`, `promoção`, `garanta`, `aproveite`, `patrocínio`, `qrcode`, `tela`.

Com isso a separação deixou de ser ambígua, medida nos trechos reais da sabatina:

| Trecho | Densidade |
| --- | --- |
| Anúncio do Crusoé | **0.579** |
| Encerramento e agradecimentos | **0.389** |
| Direito penal centrado na vítima | `0.000` |
| Nomeações e poderes do STF | `0.000` |
| Plano de desfavelização | `0.000` |
| Fusão de municípios e emendas | `0.000` |

Quatro passagens de argumento real do mesmo vídeo pontuam **exatamente zero**. O
limiar foi fixado em `0.15`, dentro dessa lacuna.

A conclusão do ciclo 23 foi, portanto, **revista com evidência melhor**, e as duas
regressões que a travavam foram reescritas para o comportamento novo.

## Efeito nas duas fontes com gabarito

| Fonte | Recall antes | Recall agora | Dano ao conteúdo real |
| --- | --- | --- | --- |
| Live 98 min | 3.4% | **10.6%** | 4.3% do tempo em bloco |
| Entrevista 31 min | 23.6% | **27.2%** | 0.9% do tempo em bloco |

O recall total continua baixo, e isso é esperado: boa parte do que o Acervo marca é
conversa casual, que o ciclo 23 já demonstrou não ser detectável por vocabulário. O
ganho prático está em **quais** trechos passaram a ser reconhecidos — exatamente os que
produziram os cortes ruins do usuário.

## Implementações

| Arquivo | Alteração |
| --- | --- |
| `modules/clip_selector.py` | `_drop_labelled_non_content()` recebe a transcrição e, sem snapshot, usa o detector local. Os descartes passam a ser listados no progresso, com intervalo e texto. |
| `modules/non_content_detector.py` | Densidade de léxico aprendido entra no veredito, com `LEARNED_NON_CONTENT_THRESHOLD = 0.15`. |
| `data/chub_priors/acervo_priors.json` | 239 termos, 6.2 KB. |
| `app.py` | Novo `_write_selection_diagnostics()`: grava em `FuriaClipsData/diagnostics/` um JSON com cada corte renderizado e cada candidato adiado — posição no ranking, `viral_score`, gates, motivo do adiamento, locutor e riscos. |
| `tests/test_topic_segmenter.py` | Duas regressões reescritas, uma nova. |

O relatório de diagnóstico existe porque o console mostra apenas os intervalos
renderizados e nada sobre o raciocínio: quais gates dispararam, o que o ranqueador
pontuou, por que 36 candidatos foram adiados. Diagnosticar uma execução ruim pelo
console era adivinhação.

## Validação

| Verificação | Resultado |
| --- | --- |
| Suíte completa | **358 aprovados, 7 falhas ambientais** |
| `compileall`, `node --check`, `git diff --check` | aprovados |
| Execução real de `_write_selection_diagnostics()` | aprovada |

O teste de execução encontrou um defeito que o `compileall` não pega: `Path` não estava
importado em `app.py`, e a função quebraria com `NameError` na primeira execução real.

## Classificação das conclusões

| Classificação | Conclusão |
| --- | --- |
| Confirmado | Sem snapshot, toda a camada Campaign Hub das releases 2.9–3.1 fica inerte. |
| Confirmado | O detector da 3.3 falhava nos três trechos reais que produziram cortes ruins. |
| Corrigido | Com 239 termos e regra de densidade, anúncio e encerramento são reconhecidos e o argumento real pontua zero. |
| **Revisto** | A conclusão do ciclo 23 — o léxico não decide — valia para 86 termos e média sobre janelas; com o léxico completo e densidade, decide. |
| Corrigido | O julgamento de não-conteúdo passou a funcionar sem snapshot. |
| Não verificado | Se o ranqueamento está correto. Os logs mostram um anúncio em 3º e o VT de abertura em 7º, mas a entrada estava contaminada; só o relatório de diagnóstico de uma execução nova permite separar erro de ranqueamento de erro de entrada. |
| **Aberto** | O Gemini devolveu 1 candidato para 92 blocos, em resposta de 2134 caracteres. Não investigado nesta rodada. |
| Aberto | Títulos de corte são fragmentos no meio da frase. |
| Aberto | Cortes de até 2min52 numa fonte em que o usuário quer no máximo 3 minutos, de preferência menos. |

## Próxima hipótese única

> **Se o relatório de diagnóstico de uma execução nova for analisado, será possível
> separar erro de ranqueamento de erro de geração de candidatos — hoje indistinguíveis,
> porque a lista que chegou ao ranqueador já continha propaganda e abertura.**
