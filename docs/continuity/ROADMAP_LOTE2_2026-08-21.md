# Conclusão do Roadmap - Lote 2: Contexto Editorial e Hook Detection
Data: 21/08/2026

## Implementações Realizadas
Seguindo o Roadmap de Evolução Técnica (itens 6, 7, 8 e 10), as seguintes melhorias foram implementadas e validadas:

### 1. Expansão do Vocabulário de Hook (Item 6)
- **Arquivo:** `modules/editorial_context.py`
- **Problema:** A detecção de ganchos estava limitada a contrastes ("mas", "porém") e números ("3 motivos").
- **Solução:** Adicionados gatilhos emocionais de surpresa ("você não vai acreditar", "o mais bizarro é", "chocante", "absurdo") com peso +12, e gatilhos de promessa ("vou te explicar", "te provar", "entenda por que") com peso +10.

### 2. Detecção de Setup/Payoff Longo (Item 7)
- **Arquivo:** `modules/editorial_context.py`
- **Problema:** O Furia Clips procurava o payoff (a conclusão da ideia) num raio de apenas 48 segundos. O Renan Santos costuma fazer construções retóricas mais longas, o que fazia o sistema rejeitar o corte por "payoff não confirmado".
- **Solução:** O `lookahead` foi expandido de 10 para 20 segmentos, e o limite temporal de busca foi de 48s para 90s, permitindo validar a estrutura de tese longa.

### 3. Penalidade Anafórica no Início (Item 8)
- **Arquivo:** `modules/editorial_context.py`
- **Problema:** Cortes começavam com "Ele fez isso" ou "Isso é um absurdo", deixando o espectador perdido sobre quem é "ele" ou o que é "isso".
- **Solução:** Inserida uma penalidade dura (-18 pontos) se a primeira palavra da janela for um pronome anafórico solto (`ele, ela, isso, isto, aquilo, esse, essa`). O motivo "começa com pronome (contexto quebrado)" é registrado no painel de diagnóstico.

### 4. Tolerância a Sobreposição (Overlap) Leve (Item 10)
- **Arquivo:** `modules/editorial_context.py`
- **Problema:** Qualquer sobreposição de voz (overlap) aplicava -14 pontos, mesmo que fosse apenas o entrevistador dizendo "aham" enquanto o Renan falava.
- **Solução:** Se o texto do overlap for curto (até 3 palavras) e contiver termos de concordância ("aham", "sim", "exato", "isso", "claro"), a penalidade cai para apenas -4 ("sobreposição leve (concordância)"), salvando o corte.

## Status dos Testes
- Todos os testes de contexto (`test_sources_and_context.py`, `test_context_contract.py`, `test_context_propagation.py`) passaram com sucesso (32/32).

## Próximos Passos
O Lote 3 pode focar em UI/Observabilidade (relatório de descarte e ajuste de bordas) ou melhorias de processamento offline. Como o agente opera no backend, o foco primário está sendo a inteligência de corte.
