# Pesquisa e Implementação — Detecção de Hooks e Payoffs (2026-08-21)

## Objetivo
Melhorar a capacidade do `editorial_context.py` de identificar inícios de raciocínio promissores (hooks) e desfechos claros (payoffs) antes mesmo de a transcrição ser enviada ao LLM.

## Oportunidade
O Furia Clips usa expressões regulares para identificar "sinais de contraste" no início de frases e "sinais de conclusão" no lookahead (texto futuro). Contudo, a lista de expressões era conservadora. Faltavam gatilhos comuns no vocabulário de lives e debates ("o problema é", "a questão é", "no final das contas", "pra resumir").

## Implementação
Em `modules/editorial_context.py`:
1. **Sinais de Contraste (Hook):** Adicionados os padrões `\bo problema [eé]\b` e `\ba quest[aã]o [eé]\b`. Isso pontua positivamente frases que começam apresentando um dilema direto.
2. **Sinais de Conclusão (Payoff):** Adicionados `em resumo`, `pra resumir`, `o que acontece [eé]` e `no final das contas` à expressão regular de `explicit_payoff`. Isso garante que o algoritmo reconheça quando o palestrante encerra o pensamento.

Em `modules/headline_copy.py`:
1. **Ganchos de Arte (HOOKS):** Expandida a paleta de ganchos curtos para as categorias "denuncia", "alerta", "promessa" e "neutro", adicionando termos como "INACREDITÁVEL", "CUIDADO", "A VERDADE É" e "ENTENDA", para dar mais opções ao editor sem precisar reescrever.

## Testes e Validação
- Os testes unitários focados em hooks (`test_campaign_hub.py` e `test_context_contract.py`) rodaram e passaram.
- A melhoria aumenta a cobertura do detector de hooks local, ajudando o `clip_selector.py` a ancorar candidatos com mais facilidade.
