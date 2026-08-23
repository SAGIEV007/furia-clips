# Relatório do ciclo 30 — fusão Chub-local e precedência Renan-first

**Data:** 2026-08-20  
**Branch:** `claude/repo-access-commits-imgjmk`  
**Release preservada:** `6.14`  
**Resultado:** hipótese refutada; nenhuma alteração funcional publicada.

## Hipótese

A hipótese desta rodada foi que uma fusão semântica entre propostas guiadas pelo Campaign Hub e candidatos locais preservaria a precisão das janelas locais, aproveitaria a evidência editorial do Chub e impediria que propostas guiadas largas ocupassem o orçamento de candidatos. O teste incluiu também uma precedência conservadora para seeds com `renanSpeaking=true` no modo Renan-first.

## Baseline reproduzido no checkout

A fonte foi a live `3XJfcqn56Rw`, com 5.905 segundos, 1.951 frases locais, 27 blocos QA-gated e 66 highlights do snapshot autorizado. O mesmo harness de quatro condições foi executado no checkout limpo da 6.14 depois da reversão da hipótese.

| Condição | Candidatos | Recall IoU 0,10 | Recall IoU 0,25 |
| --- | ---: | ---: | ---: |
| Genérico sem Chub | 30 | 5/66 — 7,58% | 0/66 — 0,00% |
| Genérico com Chub | 30 | 5/66 — 7,58% | 0/66 — 0,00% |
| Renan-first sem Chub | 30 | 7/66 — 10,61% | 1/66 — 1,52% |
| Renan-first com Chub | 30 | 7/66 — 10,61% | 1/66 — 1,52% |

Esses números não reproduzem o resultado histórico registrado no ciclo 29, que informava `27,27%` no genérico com Chub. A divergência foi registrada como um problema de reprodutibilidade do harness ou de uma mudança anterior ao ciclo 30; não foi mascarada nem tratada como ganho.

## Implementação experimental

A tentativa criou uma fusão que mantinha as propostas guiadas separadas durante os reparos de abertura, pergunta e fronteiras e as incorporava depois à janela local estabilizada. Quando havia sobreposição suficiente, a janela local era preservada e recebia a proveniência do highlight, o bloco, o `highlight_id`, a janela guiada e a marca `evidence_only`. Propostas sem par poderiam permanecer como propostas guiadas para revisão.

Durante a reprodução foi encontrado um defeito adicional: a proposta materializada não copiava `renan_speaking` para o dossiê `campaign_hub`. A correção experimental mostrou que o filtro Renan-first então conseguia distinguir as seis seeds positivas das demais, mas a fusão final não aumentou o recall nem em IoU 0,10 nem em IoU 0,25. A proteção contra descarte por vizinhança e anti-overlap também não produziu ganho temporal.

## Comparação antes/depois

Após a implementação experimental, as quatro condições permaneceram com os mesmos números do baseline reproduzido: `5/66`, `5/66`, `7/66` e `7/66` em IoU 0,10; e `0/66`, `0/66`, `1/66` e `1/66` em IoU 0,25. A inspeção interna mostrou que cinco candidatos locais carregavam evidência Chub fundida no final do pipeline, mas isso não significou cobertura adicional dos highlights e não justificou uma release.

A tentativa anterior de precedência local também foi abandonada. Ela fazia candidatos locais vencerem propostas Chub em revisão, mas, sem uma fila de cobertura separada, eliminava todas as propostas guiadas do resultado final. Propostas Chub aprovadas por seus próprios gates não deveriam desaparecer apenas por não haver uma candidata local sobreposta; essa regressão foi corrigida no checkout experimental e depois todo o experimento foi revertido.

## Validação

As regressões focadas passaram com **72 testes aprovados**. A suíte completa, após provisionamento temporário do asset BlazeFace com o SHA-256 documentado e sua remoção antes do encerramento, passou com **541 testes aprovados e 4 ignorados**. O teste sem o asset apresentou uma única falha ambiental esperada; nenhum binário foi incluído no Git.

O checkout final está limpo, permanece na branch isolada e continua em `e360e74`. Nenhum arquivo de mídia, snapshot, transcrição, banco, cookie, token ou chave foi adicionado ao repositório.

## Decisão

A hipótese foi **refutada para publicação**. A fusão pode melhorar a auditabilidade de alguns candidatos, mas não demonstrou ganho de recall, precisão temporal ou contexto na fonte real. A versão pública continua `6.14`; não houve incremento de versão nem commit funcional novo.

## Próximo ciclo recomendado

Antes de tentar outra quota ou outro peso, o próximo ciclo deve resolver a divergência de medição: instrumentar o benchmark para contar separadamente propostas guiadas, candidatos locais enriquecidos por Chub e seeds positivas que foram descartadas em cada etapa. Depois, reproduzir o resultado histórico de `27,27%` usando exatamente a mesma fixture, conta, timeline e caminho de seleção. Só após essa reconciliação deve ser testada uma fila de cobertura Chub separada do pool publicável, com revisão obrigatória e sem permitir que a memória histórica substitua a precisão local.
