# Pesquisa oficial de capacidades concorrentes — 14/08/2026

## Objetivo e limite da evidência

Esta rodada verificou páginas oficiais de OpusClip, Vizard e Klap para separar capacidades declaradas de requisitos que realmente fazem sentido no Furia Clips. As páginas são materiais de produto e marketing; portanto, descrevem o que cada plataforma afirma oferecer, mas não comprovam a implementação interna, a precisão, a taxa de aprovação ou a equivalência de qualidade em vídeos políticos brasileiros.[1] [2] [3] [4]

## Capacidades observadas

| Plataforma | Capacidade declarada nas fontes oficiais | Tradução segura para o Furia Clips |
| --- | --- | --- |
| OpusClip | Reframe automático para 9:16, 16:9 e 1:1, rastreamento de pessoas/objetos, layouts dinâmicos por tipo de conteúdo e ajuste manual por quadro ou prompt.[1] | Criar um plano de enquadramento por segmento, com famílias `single_face`, `multi_speaker`, `split_screen`, `b_roll`, `text_card` e `institutional`. Aplicar crop somente quando a cobertura visual e a confiança forem suficientes; sempre mostrar a razão e permitir preservar o original. |
| OpusClip | A página também afirma suportar entrevistas, podcasts, webinars, TV, lives e vídeos com pouco diálogo, usando sinais visuais, sonoros e de sentimento.[1] | Não rejeitar automaticamente vídeos institucionais ou narrativas com pouca fala. Criar uma rota visual multimodal separada, sem fingir que o ranking de fala resolve esse caso. |
| Vizard | Transcrição pesquisável e editável, exportação em SRT/TXT e criação de clips ao destacar ou remover texto.[2] | Implementar timeline/transcrição canônica e edição não destrutiva: selecionar texto para ajustar entrada/saída, sem apagar o arquivo original nem converter a escolha em render irreversível. |
| Vizard | Editor de áudio textual com remoção opcional de silêncios, fillers e ruído, além de controle fino por segmento e timeline.[3] | Tratar limpeza de pausas como sugestão revisável. Preservar pausas emocionais, de raciocínio e de entrevista; a automação deve marcar o motivo, não remover tudo por padrão. |
| Klap | Extração de tópicos, geração de vários clips, smart reframing, insights de score, legendas e layouts como split-screen.[4] | Agrupar candidatos por tema/família editorial e calcular um score explicável de potencial relativo ao canal. O score deve servir à ordenação e à revisão, nunca prometer viralidade. |
| Klap | A própria página informa que o algoritmo depende fortemente de detecção de fala e funciona melhor em podcasts, entrevistas, aulas e outros vídeos falados.[4] | Usar densidade de fala como sinal apenas na rota falada; vídeos institucionais, campanha e montagem devem seguir uma rota visual própria para não serem descartados por transcript esparsa. |

## Prioridades técnicas derivadas

A convergência mais útil entre as fontes não é “copiar o algoritmo viral”, mas combinar **reframe explicável**, **edição por transcrição**, **controle manual rápido**, **diversidade por tópico** e **tratamento explícito de vídeos com pouca fala**. Para o objetivo do editor, publicação direta e agendamento social continuam secundários: o fluxo final é revisar e levar o corte ao CapCut.

A ordem recomendada para o próximo ciclo é: primeiro criar `layout_planner.py` ou equivalente para classificar a composição e decidir entre crop seguro e proporção original; depois adicionar uma camada de edição textual não destrutiva para entrada/saída; em seguida incluir a rota `institutional`/`low_dialogue`; por fim, mostrar no portfólio diário diversidade por tema e família editorial. Cada etapa deve preservar score, confiança, fonte da decisão e feedback do editor.

## Regras de segurança editorial

O Furia Clips não deve declarar que um trecho é viral, verdadeiro ou juridicamente seguro apenas porque contém palavras fortes, um card, uma manchete, uma acusação, um número ou uma pontuação alta. O ranking deve separar potencial de retenção, completude, debate e necessidade de revisão factual/jurídica. O sistema também não deve replicar fórmulas privadas de XP, dados internos ou promessas de desempenho de concorrentes.

> A regra prática desta pesquisa é: automatizar o trabalho mecânico, explicar a decisão editorial e manter o editor no controle quando a evidência de locutor, contexto ou enquadramento for ambígua.

## Referências

[1]: https://www.opus.pro/ai-reframe "OpusClip — AI Reframe"
[2]: https://vizard.ai/tools/transcription "Vizard — Transcription"
[3]: https://vizard.ai/tools/audio-editor "Vizard — Audio Editor"
[4]: https://klap.app/ "Klap — página oficial"
