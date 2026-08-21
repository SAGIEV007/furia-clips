# Pesquisa e Implementação — Refinamento de Prompt de Headlines (2026-08-21)

## Objetivo
Garantir que o LLM gere headlines mais concisas, diretas e com verbos fortes de ação, evitando frases longas ou narrativas passivas que prejudicam a legibilidade em telas de celular.

## Oportunidade
O prompt original em `headline_studio.py` dizia que "curta vence", mas não dava um limite explícito de caracteres, o que permitia ao LLM gerar frases longas e descritivas (ex: "Fulano fala sobre a importância de...").

## Implementação
Em `modules/headline_studio.py`:
1. **Limite de Caracteres:** Adicionada a restrição de "idealmente até 72 caracteres" diretamente no `system prompt`. Isso alinha a saída da IA com a constante `HEADLINE_IDEAL_CHARS` usada pelo modelo local.
2. **Verbos Fortes:** Adicionada a instrução explícita para evitar verbos fracos como "fala sobre", forçando o LLM a usar verbos de ação e impacto.

## Testes e Validação
A mudança no prompt afeta apenas o comportamento do LLM (Gemini/Ollama) quando acionado via API. O fallback determinístico (`_fallback_result`) permanece inalterado. Os testes de rota passaram.
