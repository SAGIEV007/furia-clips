# Base editorial consolidada — Renan Santos/MBL

| Campo | Valor |
| --- | --- |
| Projeto | Furia Clips |
| Data da consolidação | 13 de agosto de 2026 |
| Autor | Manus AI |
| Escopo | Amostra audiovisual do perfil principal `@renansantosmbl`, relatórios audiovisuais do perfil reserva `@renansantosreserva` e catálogo público coletado para orientar a automação local. |

## 1. Escopo e nível de evidência

Esta consolidação não confunde catálogo público com audiência privada. O inventário disponível reuniu **60 itens do perfil principal** e **12 itens do perfil reserva**; esses números descrevem a amostra coletada nesta etapa, não a totalidade histórica dos perfis. O perfil principal possui milhares de publicações e a paginação pública foi interrompida por resposta de autenticação/rate limit; o perfil reserva também não foi esgotado. O catálogo e o status de coleta estão preservados no repositório para retomada incremental.[^1]

A leitura visual local foi concluída para os 12 Reels baixados do perfil principal, com folhas de contato e registro individual de padrões. No perfil reserva, foram produzidos sete relatórios audiovisuais completos e cinco relatórios visuais, com limitações explicitadas quando não houve transcrição ou análise multimodal. Portanto, o documento é uma **base editorial operacional de calibração**, não a afirmação de que todos os Reels dos dois perfis foram assistidos integralmente.

| Fonte de evidência | Cobertura desta etapa | Confiabilidade para implementação |
| --- | ---: | --- |
| Folhas de contato e inspeção visual do perfil principal | 12 Reels | Alta para composição, formato, faces, cards e legendagem original; parcial para áudio e minutagem |
| Relatórios audiovisuais do perfil reserva | 7 relatórios completos + 5 visuais | Alta nos relatórios com inspeção de quadros; parcial quando a transcrição online estava indisponível |
| Catálogo público paginado | 60 itens principal + 12 reserva | Alta para existência, identificação e metadados coletados; insuficiente para retenção e qualidade editorial |
| Métricas públicas de curtidas/comentários | Amostra indexada | Útil como proxy de distribuição; não substitui retenção, conclusão ou compartilhamentos |

## 2. Linguagem editorial comum

Os dois perfis trabalham com **ideia política apresentada como unidade audiovisual curta**, não com cortes aleatórios de fala. O padrão mais recorrente é um hook imediato, seguido por tese ou pergunta, materialização visual por b-roll/card/reação e uma conclusão ou punchline. A legenda é grande, de alto contraste e segmentada em frases curtas; amarelo, vermelho, magenta, branco e preto são usados para marcar ênfase, citação, alerta ou identidade visual. O Furia Clips deve selecionar o arco completo antes de qualquer etapa de legenda, e não tratar cor ou palavra isolada como prova de qualidade.[^2]

O perfil principal é mais heterogêneo no formato: monólogo de estúdio, podcast, entrevista externa, selfie de proximidade, react de notícia, comentário com câmera de segurança, palco e peça institucional. O perfil reserva reforça especialmente a lógica de **confronto pergunta–resposta**, com headline fixa, split-screen, múltiplos participantes, troca de reações e manutenção de uma composição 4:5. Essa diferença é importante: não existe um único crop ou uma única duração que represente a marca.

## 3. Taxonomia audiovisual para o seletor

A classificação abaixo deve ser tratada como sinal editorial intermediário. Ela pode ser inferida por faces, microfones, cortes de fonte, cards e transcript, mas deve conservar uma confiança e permitir `unknown` quando a evidência for fraca.

| Tipo editorial | Características observadas | Sinais de seleção | Regra de enquadramento |
| --- | --- | --- | --- |
| `talking_head` | Renan em plano médio/close, uma face estável, gesto e argumento contínuo | tese, consequência e frase final; hook nos primeiros segundos | Crop 9:16 permitido quando a face permanece estável e o texto não é cortado |
| `selfie_proximo` | Rosto muito próximo, apontamento, expressão forte e headline superior | monólogo curto com promessa e payoff | Reframe facial conservador; preservar headline e mãos quando gestuais |
| `entrevista` | Dois ou mais participantes, pergunta, resposta e reação | buscar pergunta + resposta completa + fechamento | Desativar crop agressivo; preservar participantes e alternância de fontes |
| `podcast` | Microfone, planos de interlocutores, cortes de reação e, às vezes, split-screen | priorizar raciocínio completo e mudança de interlocutor | Manter composição original ou usar crop apenas com active speaker seguro |
| `react` | Renan reage a TV, notícia, câmera de segurança ou depoimento | exigir evidência visual + interpretação de Renan | Acompanhar fonte visual; não cortar o card nem a reação conclusiva |
| `b_roll_argumentativo` | Fala âncora intercalada com notícia, rua, polícia, arquivo ou card | tese → evidência → consequência/proposta | Tracking pausa durante b-roll; respeitar áreas textuais e retorno ao rosto |
| `palco` | Renan em pé, microfone, gestos amplos, plateia e planos aberto/fechado | frase de transformação, mobilização ou conclusão | Preservar mãos, microfone e relação com a plateia; evitar crop no gesto-chave |
| `institucional` | Mensagem gráfica, grupo, campanha, assinatura e pouca fala contínua | mensagem autossuficiente com dado, chamada ou assinatura | Preservar margens, cards e área preta; proporção original é parte da peça |

## 4. Estrutura narrativa que deve virar ranking

O ranking do Furia Clips deve deixar de tratar “palavra política” como critério dominante. A pontuação deve avaliar se o trecho é publicável depois de revisão, mesmo sem legenda automática. Um candidato forte contém uma entrada compreensível, uma ideia identificável, evidência ou desenvolvimento e uma saída que fecha o pensamento. Em entrevista, o antecedente pode ser uma pergunta; em react, a evidência pode ser um card; em institucional, o texto visual pode substituir a fala.

| Dimensão | Pergunta operacional | Efeito no ranking |
| --- | --- | --- |
| Hook | O espectador entende o conflito, alvo, promessa ou pergunta nos primeiros segundos? | Aumenta prioridade; penaliza início no meio da frase |
| Unidade semântica | O trecho contém uma ideia completa, sem depender de contexto ausente? | Fator de qualidade obrigatório |
| Completude | Existe conclusão, consequência, resposta ou punchline? | Penaliza cortes interrompidos antes do payoff |
| Evidência | Há card, imagem, reação, número ou exemplo que sustente a tese? | Aumenta relevância quando a evidência é explicada |
| Especificidade | O trecho apresenta entidade, situação, número ou proposta identificável? | Diferencia comentário genérico de corte publicável |
| Energia editorial | Gestos, variação de plano, reação, aplauso ou tensão reforçam a fala? | Usa áudio e visão como sinais, sem substituir semântica |
| Clareza de locutor | É possível saber quem fala e quem é o alvo da fala? | Penaliza sobreposição e active speaker incerto |
| Segurança de contexto | A acusação, dado ou afirmação está claramente atribuída ao orador? | Exige revisão humana e reduz ranking automático quando ambígua |
| Diversidade | O candidato acrescenta formato ou tese diferente dos já escolhidos? | Evita 15 clips visualmente iguais do mesmo vídeo |

Uma implementação segura pode calcular uma nota composta, mas deve guardar o detalhamento por fator para a revisão. A faixa de **39–50 cortes por dia** deve ser tratada como portfólio de alta qualidade entre várias lives, não como meta para forçar candidatos fracos. Quando um vídeo não oferece unidades suficientes, o sistema deve retornar menos clips e explicar a razão.

## 5. Regras de pergunta–resposta e áudio

A unidade entrevista deve preservar a pergunta quando ela for necessária para entender a resposta. O pipeline deve marcar pausas, interrupções, risos, aplausos, música, mudança de fonte e sobreposição suspeita. A identificação de voz pode ajudar, mas não deve ser apresentada como reconhecimento perfeito; quando a confiança for baixa, o resultado deve marcar o locutor como desconhecido e manter o enquadramento original. Essa cautela é coerente com os relatórios do reserva, nos quais múltiplos rostos e split-screen tornam o crop centralizado editorialmente inadequado.[^3]

A música não deve ser inserida automaticamente como requisito da seleção. Nos exemplos analisados, a energia frequentemente vem da voz, do ambiente, de reações sociais e da alternância com material de prova. O Furia Clips deve registrar se há música original ou ambiente, mas deixar a escolha de trilha para o editor, especialmente em notícias, entrevistas e cortes políticos com fala sobreposta.

## 6. Enquadramento e proporção

A decisão de reframe deve ser uma saída explicável do analisador, não um efeito aplicado a todos os cortes. O comportamento esperado é o seguinte:

| Evidência detectada | Saída recomendada |
| --- | --- |
| Uma face dominante, estável, com margem para olhos e boca | Permitir 9:16 com tracking facial conservador |
| Duas faces ou pergunta–resposta | Preservar proporção original ou usar quadro amplo; não cortar o interlocutor |
| Split-screen, headline fixa ou card jornalístico | Manter composição original; proteger todo o texto e borda da arte |
| B-roll sem locutor visível | Desativar tracking durante o insert e retornar ao tracking somente após validação |
| Reação silenciosa relevante | Manter o trecho mesmo com baixa energia sonora; julgar expressão e contexto |
| Palco com gestos e microfone | Usar crop que preserve mãos, microfone e direção do gesto |
| Vídeo institucional com áreas pretas e cartelas | Preservar proporção e margens; não ampliar o rosto em detrimento da mensagem |
| Confiança insuficiente | Exportar no original e registrar “revisar enquadramento” |

A regra editorial é **“reframe somente quando seguro”**. Um export 16:9 original, 4:5 ou 1:1 pode ser a decisão correta quando a composição publicada depende de mais de uma pessoa ou de uma área gráfica. A ferramenta deve mostrar no resultado `layout`, `reframe_confidence`, `original_aspect_reason` e, quando possível, as posições faciais usadas.

## 7. Aplicação direta ao produto

A base consolidada deve calibrar o Furia Clips em quatro pontos. Primeiro, o prompt do seletor deve receber a taxonomia, a exigência de arco completo e a distinção entre fala, evidência e reação. Segundo, o analisador multimodal deve retornar segmentos timestampados, janelas de foco, momentos pergunta–resposta, observações de locutor e sinais audiovisuais. Terceiro, o renderizador deve usar a confiança de layout para decidir entre 9:16 e proporção original. Quarto, o sistema deve registrar feedback do editor — aprovado, rejeitado, início/fim ajustado e motivo — para calibrar os pesos com dados reais do canal.

| Componente | Calibração editorial aplicada |
| --- | --- |
| Transcrição | Gemini online primeiro; legenda pública ou transcrição manual como fonte timestampada; Whisper adaptativo apenas como fallback |
| Contexto | `auto`, `renan_santos` ou `generic_political`, sem exigir que todo vídeo seja centrado em Renan |
| Seleção | Pergunta–resposta, tese–evidência–conclusão, hook, especificidade, energia, diversidade e segurança contextual |
| Reframe | Uma face estável permite crop; múltiplas faces, cards e split-screen preservam original |
| Saída | 1080p máximo para fontes públicas; clip ranqueado com score e decomposição dos fatores |
| Revisão | Rejeitar ou ajustar clips com acusação, número, contexto incompleto, fala sobreposta ou enquadramento ambíguo |

## 8. Limitações e próximos dados necessários

A base ainda não mede retenção, conclusão, compartilhamentos, BPM, loudness integrado ou taxa de aprovação por formato. Curtidas e comentários públicos podem orientar descoberta de temas, mas não devem ser usados como verdade causal sobre viralidade. Também não é seguro afirmar padrões de música em todos os vídeos quando a análise audiovisual completa não capturou áudio de cada publicação.

O próximo ganho de qualidade não é apenas coletar mais vídeos: é executar o pipeline local sobre uma amostra maior, associar cada clip às decisões do editor e comparar aprovação por tipo editorial, duração, reframe e presença de evidência. A retomada do crawler deve respeitar atraso e cursor incremental, sem tentar contornar bloqueios do Instagram. Quando o proxy multimodal estiver disponível, os arquivos já baixados podem ser analisados em lote; até lá, os relatórios visuais permanecem válidos como calibração de layout, não como transcrição.

## Referências

[^1]: [Catálogo paginado e status do inventário](instagram-feed-catalog-full.json) e [relatório de status da coleta](instagram-crawl-status-2026-08-13.md).
[^2]: [Achados visuais dos 12 Reels do perfil principal](instagram_mbl_sample_visual_findings.md) e [síntese audiovisual anterior](video-analysis/editorial-patterns.md).
[^3]: [Relatório audiovisual do Reel Db_OfZDjKMW, perfil reserva](instagram_reserva_analysis/Db_OfZDjKMW.md).

Fontes públicas de contexto: [perfil principal @renansantosmbl](https://www.instagram.com/renansantosmbl/) e [perfil reserva @renansantosreserva](https://www.instagram.com/renansantosreserva/).


## Rodada pública via navegador — Reels recentes

Em uma rodada adicional, foram abertas diretamente no navegador as páginas públicas de um Reel novo do perfil principal (`Db_zbMhNfYJ`) e de doze Reels recentes do perfil reserva (`Db_qtXRgm1b`, `Db_mfm5ihyd`, `Db_jBIqj1nb`, `Db_foElAY3K`, `Db_fnFCDK8I`, `Db_cM5TlApr`, `Db_aVwFEkfD`, `Db_Y07LFV7J`, `Db_VUXqjnyO`, `Db_R92njTCq`, `Db_OfZDjKMW` e `Db_LANvAgY6`). A evidência foi registrada no [log de análise via navegador](instagram-browser-analysis-log-2026-08-13.md).

A rodada ampliou a base com formatos que não devem ser confundidos com o comentário político padrão. O perfil reserva publica peças de **campanha/identidade**, com repetição de símbolos, slogan e CTA; peças de **bastidor/humor**, com curiosidade ou reação espontânea; **comparação eleitoral**, em que uma referência a outra figura serve de ponte para o posicionamento de Renan; **política pública/economia**, com desafio, número, diagnóstico e proposta; e **react com notícia**, no qual a emoção precisa permanecer ligada à evidência que a provocou.

| Novo sinal | Regra editorial incorporada |
| --- | --- |
| Campanha com slogan, cores e símbolos | Pode ser candidato integral quando a mensagem visual já tem começo e assinatura; proteger texto e identidade, sem exigir arco argumentativo de entrevista. |
| Humor/bastidor | Manter curiosidade, reação e payoff; separar do ranking de confronto político e não pontuar imagem isolada como corte completo. |
| Referência a outra figura + voto em Renan | Preservar a transição `referência externa → posicionamento próprio → conclusão eleitoral`. |
| Diagnóstico fiscal/econômico | Exigir premissa, número/atribuição e proposta; marcar `needs_review` quando a afirmação factual não estiver contextualizada. |
| React de notícia | Manter `evidência → reação → interpretação`; não terminar em frase extrema ou CTA. |
| CTA do aplicativo Missão | Marcar como chamada promocional, não como conclusão editorial; permitir corte separado apenas se o usuário solicitar campanha. |
| Comentários polarizados | Usar como sinal de debate, nunca como prova suficiente de qualidade ou viralidade. |

A principal consequência para o Furia Clips é que o ranking diário precisa distinguir **potencial de publicação** de **potencial de debate**. Uma peça pode gerar comentários pela controvérsia e ainda precisar de revisão factual, atribuição ou contexto. A central visual deve mostrar essa distinção e permitir que o editor aprove um corte de humor, campanha, economia ou react sem obrigá-lo a competir com um monólogo político no mesmo eixo.
