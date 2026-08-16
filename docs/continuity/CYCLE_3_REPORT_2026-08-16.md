# Relatório do ciclo 3 — Auditoria do Prompt 2 e melhoria offline

## Resultado

O Prompt 2 foi reauditado antes de editar o código. A direção especializada Renan/MBL continua correta: Reels publicados são `reference_only`, lives longas do Garimpo são `processing_source`, o Campaign Hub é memória estruturada e cada rodada deve testar uma única hipótese. A aquisição de nova mídia longa e a validação audiovisual foram deliberadamente adiadas porque dependem do navegador/Criadores/Corteiros.

Foram encontradas três melhorias de continuidade no prompt: remover a versão hardcoded `1.1`, marcar o gate de payoff como hipótese já concluída e formalizar um modo offline para continuar com código, testes, logs, gates editoriais e documentação sem alegar validação audiovisual. O Prompt 2 revisado foi salvo em `docs/continuity/PROMPT_2_EXECUTOR.md`.

## Hipótese única

Uma pergunta explícita marcada com `?` não deve ser considerada uma janela contextualmente completa antes de preservar resposta suficiente. Antes da correção, o seletor podia considerar uma pergunta longa como completa se tivesse palavras suficientes, fechamento e payoff textual, mesmo quando a resposta estava no bloco seguinte.

## Implementação

O `ClipSelector` agora calcula e expõe `question_requires_answer`. Quando existe um ponto de interrogação, `context_complete` exige `question_answer_complete`; a duração-alvo permanece uma dica suave e o seletor expande até o bloco de resposta quando necessário. O `EditorialRanker` propaga a nova flag no resultado e nas `review_flags`, mantendo a decisão auditável no console e na revisão.

## Testes e validação

Foram adicionadas duas regressões: expansão de uma pergunta até a resposta sem incluir a pauta seguinte e rejeição de pergunta isolada como contexto completo. A suíte passou de 284 para 286 testes. Também passaram `python -m py_compile app.py modules/clip_selector.py modules/editorial_ranker.py` e `git diff --check`.

Nenhum navegador, login, cookie, Reel publicado, nova live ou fonte longa foi baixado nesta rodada. A validação audiovisual da fonte longa do Garimpo continua pendente e não foi simulada.

## Próximo passo

Quando o navegador estiver disponível, importar uma fonte longa do Garimpo e comparar a recuperação de setup, pergunta–resposta, referências anafóricas, tese, payoff e headline com o intervalo editorial do painel. Até lá, continuar somente com hipóteses reproduzíveis offline e correções de estabilidade/diagnóstico que não dependam de mídia nova.
