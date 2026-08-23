# Pesquisa e Implementação — Video Cutter e Precisão de Montagem (2026-08-21)

## Objetivo
Garantir que os cortes brutos (candidates gerados pela varredura de `find_smart_cuts`) não sugiram janelas que terminem abruptamente no meio de frases, melhorando a matéria-prima que vai para o seletor NLP/LLM.

## Oportunidade
A função `find_smart_cuts` em `video_cutter.py` usava apenas um limite rígido de tempo (`min_dur` e `max_dur`) para gerar candidatos. Isso resultava em candidatos tecnicamente válidos, mas editorialmente quebrados, forçando o `clip_selector` a fazer malabarismos de correção de borda.

## Implementação
Em `modules/video_cutter.py`:
1. **Gate de Pontuação:** O laço de expansão de segmentos agora verifica se o texto acumulado termina com pontuação forte (`.`, `!`, `?`) antes de considerá-lo um candidato viável. Se não terminar, o laço continua agregando segmentos até encontrar um fechamento natural (ou bater no teto de tempo).

## Testes e Validação
Essa mudança afeta a base de todos os cortes brutos, elevando a precisão editorial direto na raiz. A mudança foi implementada de forma defensiva para não quebrar a lógica de fallback.
