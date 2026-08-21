# Relatório de Auditoria e Melhorias (2026-08-21)

## 1. Visão Geral
Este documento detalha as investigações, decisões e implementações realizadas no Furia Clips para melhorar a precisão dos cortes, a qualidade das headlines e a detecção de hooks e payoffs, garantindo um produto final mais refinado e alinhado com as diretrizes editoriais do MBL e Renan Santos.

## 2. Melhorias Implementadas

### 2.1. Precisão Temporal e Cortes Brutos (`video_cutter.py`)
- **Problema:** A função `find_smart_cuts` gerava candidatos a cortes baseando-se quase exclusivamente em limites de tempo (`min_dur` e `max_dur`). Isso resultava em cortes crus que terminavam no meio de frases, exigindo que o seletor (NLP/LLM) tentasse corrigir a borda, o que nem sempre era bem-sucedido.
- **Solução:** Foi adicionada uma verificação de pontuação forte. Agora, um segmento só é considerado um candidato viável se o texto acumulado terminar com `.` (ponto), `!` (exclamação) ou `?` (interrogação). Isso garante que o material bruto entregue ao seletor já tenha completude sintática.

### 2.2. Detecção de Hooks e Payoffs (`editorial_context.py`)
- **Problema:** O vocabulário usado para detectar ganchos de contraste e fechamentos de raciocínio era muito formal e conservador, perdendo expressões comuns em debates e lives.
- **Solução:** 
  - Adicionados gatilhos de contraste: `"o problema é"`, `"a questão é"`.
  - Adicionados gatilhos de payoff: `"pra resumir"`, `"em resumo"`, `"o que acontece é"`, `"no final das contas"`.
  - Isso aumenta a sensibilidade do algoritmo para identificar inícios e fins de pensamentos de forma mais natural.

### 2.3. Perfil Político e Contexto (`political_profile.py`)
- **Problema:** O perfil de classificação não estava pontuando corretamente temas e jargões específicos da campanha atual (ex: Livro Amarelo, desfavelização).
- **Solução:** O dicionário `TOPIC_TERMS` foi enriquecido com termos como `"livro amarelo"`, `"desfavelizacao"`, `"favela"`, `"pcc"`, `"milicia"`. Os `CONFLICT_CUES` receberam palavras de impacto como `"bola de ferro"`, `"fuzil"`, `"cadeia"`. Isso melhora a categorização do vídeo e o peso dado a esses assuntos durante a seleção.

### 2.4. Geração de Headlines (`headline_copy.py` e `headline_studio.py`)
- **Problema:** O LLM estava estritamente proibido de usar aspas, o que impedia a criação de citações literais fortes. Além disso, as headlines geradas por IA tendiam a ser longas e passivas.
- **Solução:** 
  - O prompt em `headline_studio.py` foi atualizado para permitir o uso de aspas (`mode: citacao`) quando a frase for uma transcrição exata e de efeito.
  - Foi adicionada a restrição explícita de "idealmente até 72 caracteres" e a exigência de evitar verbos fracos como "fala sobre".
  - Em `headline_copy.py`, o leque de ganchos curtos (`HOOKS`) foi expandido com opções como `"INACREDITÁVEL"`, `"ENTENDA"`, `"CUIDADO"`, dando mais variedade à arte final.

### 2.5. Gates Editoriais Obrigatórios (`clip_selector.py`)
- **Problema:** Cortes que não concluíam um raciocínio (`payoff_complete == False`) ou que começavam no meio de uma frase (`context_complete == False`) perdiam pontos no `viral_score`, mas ainda podiam ser aprovados silenciosamente se a pontuação geral fosse alta.
- **Solução:** A função `_build_clips_from_scored_blocks` foi alterada para forçar `review_required = True` caso o contexto não esteja completo, o payoff falhe, haja sobreposição de áudio ou ambiguidade de tempo. O sistema agora barra cortes quebrados de irem direto para publicação.

## 3. Testes e Validação
Todos os testes unitários afetados (`test_video_cutter.py`, `test_political_profile.py`, `test_campaign_hub.py`, `test_context_contract.py`, `test_headline_studio.py`, `test_clip_selection.py`) foram executados e passaram com sucesso, garantindo que as regras de não-regressão fossem respeitadas.

## 4. Próximos Passos Sugeridos
- **Monitoramento do Gate de Revisão:** Acompanhar se a exigência de pontuação forte no `video_cutter.py` aliada aos novos gates no `clip_selector.py` está gerando um excesso de falsos positivos para `review_required` em vídeos com transcrições de baixa qualidade (sem pontuação). Se sim, pode ser necessário um fallback que relaxe a exigência de pontuação baseando-se apenas em pausas longas de áudio.
- **Expansão do Livro Amarelo:** Como o PDF do Livro Amarelo não está disponível, a taxonomia foi baseada em termos conhecidos. Quando o material completo estiver acessível, o `political_profile.py` deve ser atualizado com as teses centrais do documento.
