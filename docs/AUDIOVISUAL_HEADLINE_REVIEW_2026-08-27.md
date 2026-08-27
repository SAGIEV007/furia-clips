# Revisão audiovisual e calibração de headlines — 2026-08-27

## Objetivo

Esta rodada responde a dois problemas observados em um corte real: headlines visualmente fortes, mas dependentes de contexto anterior, e a ausência de um mecanismo explícito para confrontar a seleção textual com o vídeo. O Furia continua sendo o **Furia 1 canônico**. Nenhuma análise audiovisual passa a decidir viralidade, verdade factual ou aprovação automática.

> A interpretação audiovisual é uma evidência auxiliar para revisão. O áudio, a legenda conferida e a decisão do editor continuam sendo as autoridades editoriais.

## Evidência da legenda enviada

O SRT de referência contém duas partes montadas em uma mesma legenda. O primeiro bloco termina em aproximadamente 01:24 e, em seguida, o relógio reinicia próximo de 00:00. A ordenação textual continua útil para gerar copy, mas não é correto tratar todos os timestamps como um único intervalo contínuo.

A imagem de referência mostrava três opções com o mesmo gancho `MEU DEUS!`. A opção baseada em “Portanto...” começava no meio de uma construção que prosseguia com “e a declaração de uma guerra”. A opção “Para permitir a continuidade desse processo” começava como continuação de uma explicação anterior. A opção sobre “uma vida triste” era mais autossuficiente, embora ainda exigisse conferência do áudio e do arco do corte.

A saída local, depois da calibração, deixou de promover esses dois fragmentos conhecidos. As alternativas principais passaram a usar intervalos de origem e a mostrar, no JSON e na interface, se a opção precisa de conferência audiovisual.

## Mudanças implementadas

| Camada | Contrato implementado |
| --- | --- |
| Seleção de citações | Fragmentos que começam como continuação — por exemplo `portanto`, `ou seja`, `para permitir` ou uma conjunção dependente — não são promovidos como citações autossuficientes. |
| Reparação local | Quando a continuação imediata cabe na mesma unidade, a pausa é reparada como `repaired_pause`, preservando a tese completa em vez de simplesmente esconder o trecho. |
| ASR | Padrões conservadores de concordância suspeita, como `é tomadas`, são marcados para conferência e não são corrigidos silenciosamente dentro de uma citação. Padrões genéricos demais foram evitados para não remover frases válidas como `está nos assistindo`. |
| Headline Studio | Cada sugestão recebe `headline_review`, com `status`, `self_contained`, `needs_audio_check`, `flags`, `fragment_reason`, `source_quality` e `confidence`. Sugestões sem intervalo temporal ficam explicitamente como `unanchored`. |
| Timeline | O parser reporta `timestamp_discontinuity`, `timestamp_reset_count` e `timeline_review` quando encontra um salto regressivo grande em SRT/Tactiq. A timeline normalizada não é alterada por esse aviso. |
| Interface | O Headline Studio mostra chips de revisão por sugestão e avisa quando a legenda não pontua ou quando o relógio foi reiniciado. Foi adicionado em Settings o controle `Interpretar vídeo com transcript manual`, desligado por padrão. |
| Vídeo + IA opcional | `multimodal_editorial_review` cruza `qa_moments` e `audio_visual_signals` com cada candidato, registra pergunta, resposta, sobreposição, foco e mudança de bloco, mas não altera `score`, não remove candidatos e não aprova clips. Fonte incompatível é recusada como evidência; identidade não validada permanece em revisão. |

## Como a interpretação audiovisual entra no processo

Quando o usuário ativa a opção de transcript manual e possui uma chave Gemini configurada, o vídeo pode ser enviado uma vez para análise multimodal. A resposta deve informar identidade da fonte, janelas de pergunta/resposta, possíveis sobreposições e sinais audiovisuais. O Furia cruza essas janelas com os candidatos já obtidos pelo motor textual e anexa uma explicação por intervalo.

Sem chave, com serviço indisponível ou com identidade não confirmada, o Furia permanece funcional em modo local. A ausência da análise multimodal não transforma um candidato em rejeitado; apenas deixa de fornecer essa camada auxiliar. Isso evita que uma falha de rede, cota ou reconhecimento de fonte produza uma falsa ausência de oportunidades.

Durante a calibração, a interpretação direta do vídeo pelo agente foi usada para confrontar a legenda e os cortes fornecidos. Esse procedimento pode ser repetido com novos arquivos privados. Ele serve para descobrir padrões gerais e convertê-los em testes e regras bounded. O aplicativo local não chama a conversa do agente como uma dependência oculta; ele usa regras locais e, opcionalmente, o Gemini configurado pelo próprio usuário.

## Validação

A suíte completa passou com **844 testes aprovados, 27 ignorados e 2 xfails em 16,10 segundos**. Também passaram `py_compile` para o backend e módulos, `node --check static/js/app.js` e `git diff --check`.

As regressões específicas cobrem fragmentos de continuação, concordância suspeita, reset de timestamp, ausência de intervalo, evidência multimodal, sobreposição, pergunta sem resposta e identidade audiovisual incompatível. Não foram incluídos no repositório vídeo, ZIP, SRT privado, transcript integral, diagnóstico privado, banco editorial, exports ou credenciais.

## Limites atuais e próxima evolução segura

A análise multimodal deve ser tratada como **triagem de revisão**, não como um juiz automático. O próximo ganho de precisão mais importante é reunir decisões humanas com razão estável — por exemplo `headline_fragment`, `headline_audio_mismatch`, `question_only`, `interrupted_answer`, `wrong_source` e `timeline_discontinuity` — e comparar essas decisões com os sinais multimodais. Só depois de uma amostra consistente será razoável medir quais sinais ajudam ou atrapalham; não há base para afirmar aprendizagem causal a partir de um único corte.

Também é recomendável manter uma etapa de conferência rápida no player: abrir o intervalo sugerido, ouvir alguns segundos antes e depois, e registrar se a sugestão está completa, se começa no locutor correto e se a headline corresponde ao que foi dito. A ferramenta agora torna esses pontos visíveis, em vez de apresentar todos os textos como igualmente prontos.
