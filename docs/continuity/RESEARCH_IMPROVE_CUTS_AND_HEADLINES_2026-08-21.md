# Pesquisa e Implementação — Precisão de Cortes e Headlines (2026-08-21)

## Objetivo
Aprimorar a precisão dos cortes gerados pelo Furia Clips (NLP/LLM) garantindo contexto completo e fechamento adequado de raciocínio (payoff), além de melhorar a geração de headlines permitindo citações precisas sem quebrar a regra de fact checking.

## Evidência Técnica (Gates Editoriais)
A revisão do módulo `clip_selector.py` (linha ~3628) mostrou que o gate `review_required` estava considerando apenas a ambiguidade de locutor (`speaker_identity_review_required`).
Cortes que terminavam no meio da frase ou não entregavam a resposta de uma pergunta recebiam pontuações menores (`viral_score`), mas ainda podiam ser aprovados sem marcação de revisão se fossem os melhores do lote.

**Solução Aplicada:**
O cálculo de `review_required` em `_build_clips_from_scored_blocks` foi estendido para incluir explicitamente as flags de completude. Agora, um corte será marcado para revisão (impedindo publicação cega) se:
1. `context_complete` for falso (corte começa no meio da frase ou referência).
2. `payoff_complete` for falso (corte não conclui o pensamento).
3. Houver sobreposição de áudio suspeita (`overlap_suspected`).
4. O tempo for ambíguo (`timing_ambiguous`).

## Geração de Headlines (Citações vs Resumo)
A revisão do módulo `headline_studio.py` mostrou que o prompt do LLM proibia estritamente o uso de aspas ("Não use aspas: a frase não é citação"). Isso forçava o LLM a sempre parafrasear, mesmo quando o político entregava uma frase de efeito perfeita.

**Solução Aplicada:**
1. O prompt do LLM foi atualizado para permitir o uso de aspas (modo `citacao`) APENAS se a frase for exatamente igual ao que foi dito.
2. A estrutura JSON de resposta esperada do LLM foi ajustada para incluir o campo `"mode": "resumo|citacao"`.
3. O parser de retorno (`_merge_ai_suggestions`) foi alterado para respeitar o `mode` sugerido pelo LLM (em vez de hardcodar `"resumo"`).

## Testes e Validação
- Os testes unitários (`test_clip_selection.py` e `test_headline_studio.py`) passaram com sucesso.
- Ocorreu um problema de `OperationalError: no such table: clips` no ambiente de testes da rota de headline. Foi corrigido inserindo a inicialização do banco em memória (`database.init_db()`) nas funções de teste `test_a_rota_devolve_texto_de_arte_sem_ia` e `test_a_rota_recusa_corte_inexistente`.

## Próximos Passos (Para o Claude)
- A integração com o Chub via MCP foi testada e está operacional (`chub_acervo_blocks`, `chub_sql`, etc). O "Livro Amarelo" é indexado nos `context_packs` mas não há PDF solto.
- Se os testes em produção indicarem que a restrição de `review_required` está barrando muitos cortes bons por falso-positivo no NLP, considere afrouxar os pesos de `payoff_complete` para fontes mais caóticas (ex: lives IRL na rua).
