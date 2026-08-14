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


## Evidência audiovisual adicional — `DZ7ZY6EtlNq`

A análise audiovisual local deste Reel identificou uma narrativa de **contraste entre realidade e propaganda**. O vídeo abre com uma imagem socialmente impactante, ancora o conflito com contexto territorial e político, usa pergunta–resposta para materializar o tema em uma família específica, retorna ao símbolo visual inicial e fecha com síntese política e identificação do autor. A leitura deve permanecer vinculada a este vídeo; ela não comprova padrão estatístico do conjunto inteiro.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Gancho visual/moral nos primeiros segundos | Elevar prioridade de candidatos que iniciem com cena anômala ou consequência concreta, desde que a fala subsequente explique o contexto. |
| Dados e entrevista de exposição | Detectar pares pergunta–resposta com números, idades, quantidades ou fatos verificáveis e preservar pergunta suficiente para a resposta não parecer solta. |
| Split-screen narrador + evidência | Nunca aplicar reframe simples 9:16 nesse formato; classificar como `split_screen` e preservar a composição ou exigir revisão explícita. |
| Retorno ao símbolo inicial | Valorizar fechamento que retoma a prova visual ou transforma o fato em tese, evitando encerrar apenas no meio da entrevista. |
| Branding ao final | Considerar identificação/CTA como elemento de publicação, mas não permitir que ela compense falta de contexto ou conclusão editorial. |

O relatório audiovisual completo está em `docs/instagram_mbl_local_audiovisual_DZ7ZY6EtlNq_2026-08-14.md`.


## Evidência audiovisual adicional — `Db_VRDtNM9d`

Este Reel é um formato de **selfie urgente / explicação de denúncia**. A abertura com expressão de transição, o ambiente de deslocamento, a tese de conflito, a promessa de prova técnica e o desafio público formam uma unidade curta de alta energia. O fechamento é um *cliffhanger*, não uma conclusão factual definitiva; por isso deve receber classificação diferente de um corte que resolve plenamente a pergunta.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Close-up de uma face, gestos de pontuação e fala contínua | Permitir reframe 9:16 conservador quando a confiança de uma face estável for alta; preservar mãos e headline. |
| Abertura “É o seguinte” + cenário de deslocamento | Considerar transição curta como hook quando a frase seguinte introduzir imediatamente um conflito específico; não pontuar a expressão isoladamente. |
| Vocabulário de denúncia e prova técnica | Elevar relevância de `fraude`, `comprovar`, `logs`, `IP`, `acareação` e entidades nomeadas, mas marcar para revisão quando a acusação não trouxer atribuição suficiente. |
| Urgência visual do ambiente | Usar deslocamento, câmera na mão e gestualidade como sinais auxiliares de energia, nunca como substitutos de tese e contexto. |
| Fecho de promessa futura | Rotular como `cliffhanger`/`continuidade`; não contabilizar como conclusão forte sem uma consequência, resposta ou CTA editorial explícito. |

O relatório audiovisual completo está em `docs/instagram_mbl_local_audiovisual_Db_VRDtNM9d_2026-08-14.md`.


## Evidência audiovisual adicional — `Db-0U1mt1UI`

Este Reel é um **corte de podcast com tese lógica de segurança pública**. Ele entra diretamente em uma premissa provocativa, desenvolve uma cadeia curta de argumento e fecha no conceito de “impunidade”. A estética preto e branco, o microfone visível, os *jump cuts*, a legenda de alto contraste e a trilha discreta reforçam seriedade e tensão, mas não devem ser confundidos com critério suficiente de seleção.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Premissa binária seguida de justificativa | Valorizar estruturas `premissa → explicação → consequência` e `se/então` quando o raciocínio termina em uma frase semântica completa. |
| Microfone e close/medium shot de podcast | Classificar como `podcast`; usar active-speaker/reframe apenas quando uma face for estável e não houver troca necessária de interlocutor. |
| Alta densidade de fala e ênfase em conceitos | Usar palavras por segundo e energia tonal como sinais auxiliares; não aprovar automaticamente fala rápida sem unidade argumentativa. |
| Conceito forte no fecho | Reconhecer conclusão por substantivo/ideia de impacto quando a frase fecha o argumento; isso é diferente de cliffhanger. |
| P&B, legenda e música de tensão | Registrar como tratamento de publicação, não como sinal de que o trecho bruto é necessariamente forte. |

O relatório audiovisual completo está em `docs/instagram_mbl_local_audiovisual_Db-0U1mt1UI_2026-08-14.md`.

## Evidência audiovisual adicional — `Db-mlJ7tC5k`

Este Reel demonstra um **corte de entrevista com arco explicativo completo**: pergunta provocativa, tese imediata, contexto social, diagnóstico e frase-síntese final. A edição alterna interlocutores e B-roll semanticamente alinhado à fala; há ainda manchetes como apoio de autoridade. Isso confirma que, em entrevistas longas, o melhor ponto de entrada pode ser a pergunta que torna a resposta inteligível, e não necessariamente a primeira frase do entrevistado.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Pergunta curta seguida de tese (“o problema é X”) | Priorizar pares pergunta–resposta quando a pergunta define o objeto e a resposta traz uma posição clara; evitar perguntas sem resposta suficiente. |
| Arco `problema → explicação → consequência` | Bonificar cortes com ao menos dois estágios argumentativos e um fecho sintético; a duração maior é aceitável quando cada estágio é necessário. |
| Citação de dados, pesquisa ou manchete | Marcar como `apoio_de_evidência` para revisão editorial, sem tratar a presença de uma alegação como veracidade automática. |
| Alternância de entrevistador, entrevistado e B-roll | Manter a composição/original quando há mais de um interlocutor ou apoio visual relevante; não forçar reframe vertical de uma única face. |
| Frase final que resume a tese | Tratar como conclusão forte somente quando fecha o raciocínio iniciado no trecho, não apenas quando tem tom enfático. |

O relatório audiovisual completo está em `docs/instagram_mbl_local_audiovisual_Db-mlJ7tC5k_2026-08-14.md`.

## Evidência audiovisual adicional — `Db6qoCUBulc`

Este Reel é uma **peça institucional de campanha dirigida por narrativa visual e desenho de som**, não um corte de fala. A estrutura vai de uma cena cotidiana de amizade ao choque de um disparo, silêncio, ausência de um jovem e mensagem estatística. A assinatura final identifica a peça como campanha. Portanto, um sistema de clipping não pode descartar automaticamente vídeos com pouca transcrição: deve classificá-los como `institucional` e submetê-los a uma rota de seleção visual própria.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Sem discurso contínuo, mas com virada narrativa | Não usar baixa densidade de fala como rejeição automática em peças classificadas como `institucional`; exigir evidência visual e semântica de arco completo. |
| Mudança abrupta de euforia para impacto, silêncio e sirene | Registrar contraste de áudio e mudança de cena como sinais de retenção, sem usar conteúdo violento como bonificação automática. |
| Mesmo cenário com ausência visual de personagem | Priorizar continuidade visual com alteração significativa quando o trecho tiver mensagem inteligível; manter a proporção original. |
| Estatística e apelo no texto em tela | Marcar como `texto_visual_relevante` e `revisar_afirmação`; a ferramenta deve preservar a arte e nunca declarar a informação como verificada. |
| Assinatura final de campanha | Classificar como `campanha`/`institucional`, separando seu portfólio do ranking de entrevista e comentário político. |

O relatório audiovisual completo está em `docs/instagram_mbl_local_audiovisual_Db6qoCUBulc_2026-08-14.md`.

## Evidência audiovisual adicional — `Db88Vu-Nmhu`

Este Reel usa o formato **evidência externa → reação política → proposta/assinatura**. Ele abre com imagens de câmera de segurança e áudio de vítima, corta para o comentário de Renan e fecha com identidade de campanha. O impacto é real como mecanismo de atenção, mas o ranking não deve confundir choque, vocabulário agressivo ou uma afirmação política com qualidade factual; esses elementos precisam ser exibidos como sinais de revisão.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| CCTV ou material externo antes do comentário | Classificar como `react`; preservar a transição entre prova visual e interpretação do orador. |
| Grito, pedido de ajuda ou pico de áudio | Usar pico emocional para localizar o início, não para aprovar o trecho sem unidade semântica. |
| Linguagem forte e contraste ideológico | Mostrar `conflito/ênfase` na revisão, mantendo penalidade de segurança contextual quando a afirmação não tem atribuição clara. |
| B-roll de crime e proposta posterior | Preferir o arco `evidência → reação → explicação/proposta`; não terminar no choque inicial se o comentário for indispensável para o sentido. |
| Assinatura ou slogan político | Marcar como `campanha` e separar do portfólio orgânico de entrevistas, evitando que CTA/branding domine a meta diária. |

O relatório audiovisual completo está em `docs/instagram_mbl_local_audiovisual_Db88Vu-Nmhu_2026-08-14.md`.

## Evidência audiovisual adicional — `Db8D9DxNnUX`

Este Reel amplia o escopo do canal para um **corte de palco com pergunta da plateia, ironia, prova de campo e cobrança final**. Embora o foco seja Guto Zacarias, a estrutura é relevante para o modo político genérico: a pergunta externa estabelece o gancho, o orador responde com posicionamento, o B-roll de experiência própria sustenta a narrativa e a conclusão formula uma cobrança ou proposta.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Pergunta da plateia/entrevistador abre o tópico | Preservar o enunciado da pergunta quando ele contém o conflito; não iniciar apenas na resposta se ela depender do contexto. |
| Orador alterna ironia e cobrança | Detectar mudança de intenção/energia como marcador de progressão, não como aprovação isolada de palavras agressivas. |
| B-roll de experiência própria | Classificar como `prova_de_campo`; favorecer a sequência pergunta → posição → evidência → cobrança/proposta. |
| Palco, plateia e split-screen | Evitar crop agressivo; mãos, microfone e reação da plateia podem carregar o sentido. |
| Frase final propositiva ou de cobrança | Bonificar conclusão quando ela fecha o arco e deixa uma ação/posição identificável. |

O relatório audiovisual completo está em `docs/instagram_mbl_local_audiovisual_Db8D9DxNnUX_2026-08-14.md`.

## Evidência audiovisual adicional — `Db8fcmItfCw`

Este Reel é um **react econômico em split-screen** que parte de uma fala de telejornal, mostra a reação de Renan, desenvolve um contra-argumento, usa manchetes como apoio e termina com uma proposta política. A evidência confirma que um corte de react pode precisar de mais tempo do que um monólogo: o material externo dá o problema, a reação marca o conflito, os dados sustentam a resposta e a proposta fecha o arco.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Autoridade externa abre o assunto | Identificar a fonte/trecho citado e preservar contexto suficiente para a reação não parecer gratuita. |
| Split-screen com reação do protagonista | Classificar como `react`; manter a área da fonte e do rosto, sem reframe que elimine um dos lados. |
| Opinião seguida de manchete/dado | Separar `opinião`, `evidência_citada` e `proposta`; aumentar prioridade quando o arco inclui os três, mas pedir revisão factual. |
| Frase alarmante seguida de soluções | Evitar terminar apenas no alarmismo; preferir saída que apresenta proposta ou conclusão identificável. |
| Branding e CTA no final | Não usar assinatura ou pedido de compartilhamento como substituto de conclusão; marcar como metadado de campanha. |

O relatório audiovisual completo está em `docs/instagram_mbl_local_audiovisual_Db8fcmItfCw_2026-08-14.md`.

## Evidência audiovisual adicional — `Db9GlGatuQi`

Este Reel é uma **convocação institucional conduzida por música, montagem histórica, metáfora visual e CTA**. Não há fala contínua: o arco nasce do stop-scroll visual, da trajetória de Renan/MBL, da diferenciação entre passado e presente e de uma cartela final com data, hora e local. Ele deve ser reconhecido como `institucional`/`convocação`, não penalizado por ausência de transcript.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Música conduz o ritmo e não há voz principal | Rota multimodal pode usar batidas, mudanças de plano, cartelas e arco visual; não exigir densidade textual de fala. |
| Arquivo histórico em P&B e presente colorido | Proteger transições cromáticas e usar mudança de cena como unidade de montagem; não aplicar reframe que destrua o contraste temporal. |
| Metáfora visual forte no primeiro segundo | Registrar `stop_scroll_visual` como sinal de atenção, mas exigir sequência compreensível antes de recomendar o corte. |
| Protagonista reaparece ao longo da trajetória | Priorizar continuidade de identidade visual sem assumir que a pessoa é o único foco do trecho. |
| Cartela final com data, hora e local | Preservar a tela de CTA integralmente e marcar como informação operacional que deve ser revisada antes da publicação. |

O relatório audiovisual completo está em `docs/instagram_mbl_local_audiovisual_Db9GlGatuQi_2026-08-14.md`.

## Evidência audiovisual adicional — `Db9RrFrNHRL`

Este Reel combina **pergunta retórica, ocorrência policial, análise legal, comparação política, proposta e CTA**. O gancho une uma imagem incomum a uma pergunta que abre um mistério; a resposta evolui para números/lei e fecha com posição política. A presença de manchetes e artigos de lei aumenta a aparência de autoridade, mas torna indispensável marcar o trecho para revisão factual e jurídica, sem a ferramenta validar automaticamente a afirmação.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Imagem incomum nos primeiros segundos + “você sabe por quê?” | Aumentar prioridade de candidatos com hook visual e pergunta retórica alinhados, preservando a resposta necessária ao mistério. |
| Ocorrência externa seguida de comentário | Classificar como `react`/`segurança`; manter a transição ocorrência → interpretação → proposta, em vez de cortar apenas no choque. |
| Número de pena, artigo ou logo de imprensa | Marcar `alegação_verificável` e `revisar_fonte`; a presença de um card não transforma o conteúdo em fato confirmado. |
| Mudança de curiosidade para indignação | Usar mudança de energia como marcador de estrutura, não como bonificação isolada de retórica agressiva. |
| Final com assinatura e CTA | Preservar apenas se a chamada fizer parte do pedido do editor; não permitir que o branding substitua a conclusão argumentativa. |

O relatório audiovisual completo está em `docs/instagram_mbl_local_audiovisual_Db9RrFrNHRL_2026-08-14.md`.

## Evidência audiovisual adicional — perfil reserva `Db-2Y0OFNtr`

Este Reel do perfil reserva é um **corte de podcast de humanização e trajetória pessoal**. Uma manchete de vulnerabilidade abre o vídeo; a pergunta do entrevistador dá contexto; Renan responde de forma reflexiva, com pausas naturais, e o split-screen contrasta imagem institucional com o depoimento informal. O padrão confirma que cortes descontraídos e emocionais também pertencem ao portfólio, desde que tenham uma unidade narrativa clara.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Pergunta do entrevistador sobre evolução pessoal | Preservar a pergunta quando ela define a jornada; selecionar respostas com memória, mudança e consequência emocional. |
| Pausas naturais e emoção contida | Não remover todas as pausas: em confissões, a pausa pode ser evidência de sinceridade e parte do payoff. |
| Split-screen entre imagem pública e podcast | Proteger a composição dos dois lados; classificar como `entrevista_humanização`, não como talking head simples. |
| Headline “viralizou/emociona” e trilha de piano | Tratar headline e música como embalagem editorial; não pontuar apenas por palavras de viralidade ou trilha triste. |
| Fecho aberto sobre fluxo/crescimento | Diferenciar reflexão aberta de cliffhanger de promessa; pode ser publicável como corte emocional quando a pergunta e a resposta formam unidade. |

O relatório audiovisual completo está em `docs/instagram_reserva_local_audiovisual_Db-2Y0OFNtr_2026-08-14.md`.

## Evidência audiovisual adicional — perfil reserva `Db-9SUJG2F8`

Este Reel usa **contradição ideológica como hook**, formato de entrevista/podcast e um apoio visual fixo relacionado à figura pública discutida. A tese é desenvolvida com exemplos comparativos e o vídeo termina em card de mobilização. O padrão é útil para o modo político genérico, mas regras de edição como eliminar todas as pausas ou inserir sempre CTA não devem ser aplicadas automaticamente ao corte bruto.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Título contradiz o senso comum do nicho | Detectar `contradição/gancho` e verificar se o áudio realmente explica a tese antes de elevar a prioridade. |
| Objeto político em apoio visual + locutor | Preservar split-screen quando a referência visual é parte do argumento; não enquadrar apenas a face do locutor. |
| Entrevista com precisão conceitual | Valorizar pergunta, definição e exemplos comparativos; não confundir tom intelectual com argumento completo. |
| Jump cuts acelerados | Remover gordura com conservadorismo, preservando pausas que separam premissa, exemplo e conclusão. |
| Card final de evento | Marcar como `mobilização`; preservar a cartela como saída somente quando a revisão autorizar o CTA. |

O relatório audiovisual completo está em `docs/instagram_reserva_local_audiovisual_Db-9SUJG2F8_2026-08-14.md`.

## Evidência audiovisual adicional — perfil reserva `Db_Ax9tmcFu`

Este Reel é um **corte de podcast argumentativo com headline temática e composição de identidade**. O assunto é introduzido por uma tarja superior, enquanto o vídeo ativo ocupa um lado e imagens estáticas do protagonista ocupam o outro. O raciocínio percorre problema social, explicação, papel institucional e crítica final, terminando sem CTA. Isso reforça que uma unidade publicável pode começar no meio da fala quando uma headline fornece contexto suficiente.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Headline fixa resume o tópico | Registrar `contexto_visual_de_headline`; permitir entrada no meio da fala somente se o texto realmente contextualizar o trecho. |
| Problema → explicação → crítica | Bonificar arco argumentativo completo, com conclusão mesmo sem chamada para ação. |
| Split-screen de identidade do protagonista | Preservar composição quando o painel lateral é parte da embalagem; não tratá-lo como sinal de active speaker. |
| Jump cuts e trilha baixa | Reduzir gordura respeitando pausas argumentais; trilha é embalagem e não critério de completude. |
| Fecho seco sem CTA | Considerar publicável quando o raciocínio fecha; não exigir assinatura, compartilhamento ou card final. |

O relatório audiovisual completo está em `docs/instagram_reserva_local_audiovisual_Db_Ax9tmcFu_2026-08-14.md`.

## Evidência audiovisual adicional — perfil reserva `Db_ENAyjO3R`

Este Reel é um **corte de podcast de alta densidade sobre cultura, soft power e estratégia nacional**. Uma pergunta temática fornece o gancho; a resposta transforma um exemplo cultural em tese geopolítica e termina com proposta prática. O caso reforça que o ranking deve valorizar clareza e exemplos concretos mesmo em vocabulário sofisticado, sem reduzir a qualidade a palavras-chave políticas tradicionais.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Pergunta simples abre tese complexa | Procurar a ponte `pergunta acessível → desenvolvimento conceitual → exemplo → proposta`, mantendo o tempo necessário para compreensão. |
| Exemplos cotidianos tornam abstração concreta | Bonificar especificidade e exemplos quando eles sustentam a tese, não apenas quando aumentam a velocidade da fala. |
| Entrevista com microfones e split-screen | Classificar como `podcast`; proteger os dois interlocutores e manter a proporção original quando a composição for parte da leitura. |
| Trilha discreta e headline contextual | Tratar música/headline como suporte de retenção; não deixar que substituam a completude semântica. |
| Fecho propositivo sobre futuro/ação | Valorizar conclusão que deixa uma proposta identificável, distinguindo-a de CTA publicitário. |

O relatório audiovisual completo está em `docs/instagram_reserva_local_audiovisual_Db_ENAyjO3R_2026-08-14.md`.

## Evidência audiovisual adicional — perfil reserva `Db_F8qvE_Z_`

Este Reel é um **testemunhal/selfie com unboxing**, estruturado como vulnerabilidade emocional → justificativa → prova material. O início contrasta foto institucional com selfie chorando; depois a câmera passa para as mãos folheando um livro, mostrando capa, dedicatória, sumário, gráficos e propostas. É um formato de apoio orgânico e humanização, não um corte político falado convencional.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Emoção autêntica seguida de explicação | Preservar pausas e mudanças de estado quando elas fazem parte do arco; não aplicar jump cuts agressivos por padrão. |
| Selfie + objeto político/material impresso | Classificar como `testemunhal`/`unboxing`; manter mãos, rosto e produto quando ambos carregam o sentido. |
| Exibição de capa, sumário, gráficos e dados | Marcar `material_visual_de_prova` e preservar planos de detalhe; a ferramenta não deve verificar nem endossar automaticamente as alegações do material. |
| Trilha inspiracional e headline contextual | Tratar música e headline como embalagem de publicação, não como qualidade semântica. |
| Fecho validando acabamento/conteúdo | Considerar conclusão quando a avaliação do objeto fecha o arco de demonstração, mesmo sem tese política explícita. |

O relatório audiovisual completo está em `docs/instagram_reserva_local_audiovisual_Db_F8qvE_Z__2026-08-14.md`.

## Evidência audiovisual adicional — perfil reserva `Db_HmR1iOy1`

Este Reel é um **corte de podcast político com múltiplos participantes, B-roll temático e proposta final**. Uma frase de indignação abre o assunto; o raciocínio passa por causa, comparação e solução. A headline fornece contexto, enquanto a alternância entre participantes e imagens de sala de aula cria dinamismo. O formato confirma a importância de preservar pergunta/contraponto e não presumir que o locutor dominante seja o único enquadramento válido.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Headline contextual + fala no meio da frase | Permitir entrada `in media res` quando a headline e a primeira frase formarem contexto suficiente; marcar dependência de contexto na revisão. |
| Problema → causa → comparação → solução | Reforçar o sinal de estrutura argumentativa com etapas explícitas, especialmente em debates educacionais e políticas públicas. |
| Múltiplos participantes + B-roll | Classificar como `entrevista_debate`; preservar interlocutores e imagens de apoio, evitando active-speaker estreito. |
| Termos técnicos/jurídicos | Bonificar especificidade e clareza, mas marcar entidades normativas para revisão; vocabulário técnico não prova a afirmação. |
| Fecho propositivo | Considerar conclusão forte quando a solução responde ao problema inicial sem depender de CTA. |

O relatório audiovisual completo está em `docs/instagram_reserva_local_audiovisual_Db_HmR1iOy1_2026-08-14.md`.

## Evidência audiovisual adicional — perfil reserva `Db_LANvAgY6`

Este Reel é um **react enquadrado por cartela fixa**, no qual a fala principal vem de um telejornal e a interpretação política é delegada ao texto estático superior. O formato usa notícia violenta de terceiros como prova de contexto e deixa a “conclusão” implícita na promessa política visível. Isso é relevante para o Furia Clips porque mostra um caso em que o vídeo pode ser publicável sem comentário oral do protagonista, mas exige classificação própria e revisão editorial forte.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Cartela superior fixa com slogan/posição + vídeo de terceiros abaixo | Classificar como `react_enquadrado` ou `curadoria_de_noticia`; preservar integralmente o layout composto. |
| Fala vem de telejornal, não do protagonista | Não inferir autoria da argumentação pelo áudio; marcar claramente a fonte principal do discurso. |
| Crime/violência serve como “prova do problema” | Priorizar somente quando houver contexto inteligível; o choque isolado não deve bastar para aprovação automática. |
| Conclusão política implícita no texto, não no áudio | Marcar `conclusao_visual` e distinguir de conclusão argumentativa verbal; isso ajuda a não confundir slogan com raciocínio completo. |
| Logos, GC e marcas de emissora | Preservar a origem visual como parte do sentido e marcar `fonte_terceira` para revisão antes de publicação. |

O relatório audiovisual completo está em `docs/instagram_reserva_local_audiovisual_Db_LANvAgY6_2026-08-14.md`.

## Evidência audiovisual adicional — perfil reserva `Db_OfZDjKMW`

Este Reel é um **destaque de podcast/advocacy com pergunta de seguidor, explicação técnica e promessa de futuro**. O formato usa headline de confronto, split-screen de identidade, B-roll para concretizar economia, infraestrutura e segurança e um fecho de alta energia. É um bom exemplo de como simplificar conceitos complexos em consequências cotidianas, mas a ferramenta deve preservar a distinção entre proposta, previsão e fato verificado.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Pergunta de seguidor lida no início | Preservar a pergunta quando ela é o desafio que organiza a resposta. |
| Conceito técnico ligado a benefício cotidiano | Bonificar `tradução_concreta`: termo abstrato seguido de exemplo compreensível, mantendo a cadeia argumentativa. |
| B-roll de entidade concreta mencionada | Registrar ponto de apoio visual e manter a proporção original quando o insert participa da explicação. |
| Split-screen com retrato fixo | Proteger identidade e active speaker; não considerar o retrato estático como participante da fala. |
| Fecho preditivo/retórico | Não tratar previsão ou promessa (“já está reeleito”, “revolução”) como conclusão factual; marcar `retórica_de_fecho` para revisão. |

O relatório audiovisual completo está em `docs/instagram_reserva_local_audiovisual_Db_OfZDjKMW_2026-08-14.md`.

## Evidência audiovisual adicional — perfil reserva `Db_R92njTCq`

Este Reel é uma **sabatina técnica adaptada para campanha**, com desafio textual, âncora de telejornal, explicação fiscal e identidade visual de canal econômico. A montagem usa um adversário em imagem fixa para contextualizar o conflito e uma fonte jornalística para dar credibilidade ao trecho técnico. O final observado é abrupto e deixa conteúdo adicional implícito; portanto, o ranking deve distinguir densidade técnica de completude editorial.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Desafio textual contra figura pública | Detectar `gancho_de_confronto` e preservar a explicação que responde ao desafio. |
| Canal de notícias e GC de sabatina | Marcar `fonte_jornalística`/`sabatina`; preservar logotipo, GC e ticker quando forem parte do contexto. |
| Vocabulário econômico e proposta detalhada | Valorizar especificidade e estrutura argumentativa, sem pontuar jargão isolado como prova de clareza. |
| Imagem estática do alvo + vídeo do autor | Manter split-screen e não aplicar crop que elimine o alvo ou o apresentador. |
| Final abrupto após explicação | Penalizar completude quando a tese ainda promete desenvolvimento; não confundir “muito conteúdo” com cliffhanger publicável. |

O relatório audiovisual completo está em `docs/instagram_reserva_local_audiovisual_Db_R92njTCq_2026-08-14.md`.

## Evidência audiovisual adicional — perfil reserva `Db_Y07LFV7J`

Este Reel apresenta uma **quebra de polarização baseada em experiência de campo**, seguida de diagnóstico e proposta de gestão. A headline polêmica atrai atenção, mas a unidade publicável vem da sequência constatação → problema → exemplo concreto → metas/indicadores. O caso mostra que uma posição contraintuitiva só deve ser elevada quando a resposta desenvolve a tese e termina em proposta identificável.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Frase que desafia a polarização | Detectar `quebra_de_padrão` e exigir desenvolvimento; não pontuar a provocação isolada. |
| Experiência de viagem/campo | Classificar como `experiência_de_campo` quando sustenta a tese com caso concreto. |
| Problema social seguido de metas/indicadores | Bonificar o arco diagnóstico → proposta, especialmente quando o fecho explica o critério de gestão. |
| Split-screen de identidade + podcast | Preservar composição e manter o interlocutor/reação quando necessário para o contexto. |
| Exemplo divisivo ou comparação internacional | Marcar `tema_sensível` para revisão; a ferramenta não deve inferir consenso pela segurança do tom. |

O relatório audiovisual completo está em `docs/instagram_reserva_local_audiovisual_Db_Y07LFV7J_2026-08-14.md`.

## Evidência audiovisual adicional — perfil reserva `Db_aVwFEkfD`

Este Reel é um **pronunciamento de esclarecimento político**, não um corte de debate. Ele começa com o fato/trending topic, explica tecnicamente o ocorrido, atribui responsabilidade ou suspeita, posiciona-se e encerra de forma protocolar. A ausência de música, o card fixo superior e a fala limpa reforçam que nem todo corte de alto potencial precisa de trilha ou B-roll; a clareza e a atualidade podem ser o principal ativo.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Fato urgente já no primeiro frame | Priorizar entrada direta quando o assunto é atual e identificável, sem exigir pergunta ou introdução. |
| Card contextual fixo no topo | Preservar o cabeçalho e marcar `contexto_visual_permanente`; ele pode tornar a fala compreensível sem áudio. |
| Exposição → explicação → posicionamento | Bonificar cadeia de esclarecimento completa; separar alegação, suspeita e fato atribuído para revisão. |
| Áudio limpo sem música | Não penalizar ausência de trilha; fala inteligível e mensagem autossuficiente podem ser suficientes. |
| Fecho protocolar “é isso” | Aceitar como conclusão quando o objetivo é comunicado/atualização, sem exigir punchline ou CTA. |

O relatório audiovisual completo está em `docs/instagram_reserva_local_audiovisual_Db_aVwFEkfD_2026-08-14.md`.

## Evidência audiovisual adicional — perfil reserva `Db_VUXqjnyO`

Este Reel é um **manifesto/campanha de alta intensidade**, montado com discurso de palco, split-screen de identidade, texto fixo em formato de post e trilha cinematográfica. O arco cresce por desafios sucessivos e fecha em frase de efeito com aplausos. O formato pode ser útil para o portfólio de campanha, mas agressividade, gritos e estética messiânica devem ser mostrados como sinais de revisão, não como aprovação automática.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Entrada já no auge vocal | Permitir hook `in media res` quando a tese visual superior contextualizar o conflito; alertar dependência de contexto. |
| Discurso público com plateia e aplausos | Classificar como `palco_manifesto`; preservar reação, microfone e gestos antes de qualquer crop. |
| Texto fixo em forma de ultimato | Marcar `mensagem_fixa_de_campanha` e revisar datas, ameaças e promessas antes de publicar. |
| Desafio crescente com frase final forte | Bonificar progressão e fecho somente se as frases formarem unidade; não confundir retórica inflamável com proposta. |
| Música orquestral e picos vocais | Registrar energia audiovisual; evitar que trilha ou volume dominate o score semântico. |

O relatório audiovisual completo está em `docs/instagram_reserva_local_audiovisual_Db_VUXqjnyO_2026-08-14.md`.

## Evidência audiovisual adicional — perfil principal `DbWxJ54hbKO`

Este Reel combina **storytelling pessoal, lista episódica e prova visual em split-screen**. O hook numérico promete três episódios de sabotagem; o arco migra da experiência individual para uma oferta política. A montagem usa active speaker no quadro superior, imagens de apoio na base, legendas dinâmicas e trilha crescente. O padrão é relevante para seleção, mas acusações nominais contra pessoas ou instituições devem receber alerta de revisão factual/jurídica e não podem ser tratadas como verdade pelo ranking.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Hook com número e promessa de lista | Bonificar curiosidade somente quando o candidato contém a lista ou uma conclusão, evitando cortar após a promessa. |
| Active speaker + evidências visuais em split-screen | Classificar como `testemunhal_com_prova_visual`; proteger rosto, texto e imagem de apoio no reframe. |
| Legendas com palavras de impacto e trilha crescente | Usar energia audiovisual como sinal secundário; não substituir completude semântica por volume ou música. |
| Transição de denúncia pessoal para proposta eleitoral | Bonificar arco problema–exemplo–posicionamento quando o fecho estiver presente. |
| Alegações sobre juiz, instituições ou dados econômicos | Marcar `needs_fact_review`/`needs_legal_review` quando houver entidade nominal e linguagem acusatória; não afirmar veracidade. |

O relatório audiovisual completo está em `docs/instagram_mbl_local_audiovisual_DbWxJ54hbKO_2026-08-14.md`.

## Evidência audiovisual adicional — perfil principal `Dayg4dyhvpA`

Este Reel usa **contraste de identidade, testemunhal de ruptura e aliança política** como arco. O locutor permanece como âncora estável no topo, enquanto a metade inferior alterna manchetes, rostos e imagens de apoio. A energia é solene e pausada, com trilha crescente; portanto, o ranking não deve exigir gritos ou cortes frenéticos para reconhecer potencial. Alegações de crimes ou vínculos de terceiros devem produzir alerta de revisão factual/jurídica, não uma bonificação cega por controvérsia.

| Sinal observado | Regra aplicável ao Furia Clips |
| --- | --- |
| Declaração inicial que une grupos políticos em conflito | Classificar como `contraste_de_identidade`; bonificar curiosidade quando a resolução da mudança de posição estiver no mesmo corte. |
| Locutor estável no topo e B-roll/manchetes na base | Classificar como `active_speaker_anchor_broll`; preservar a âncora e a área inferior no plano de reframe. |
| Tom solene com pausas sincronizadas | Reconhecer autoridade/clareza sem penalizar baixa energia; preservar pausas que precedem tese ou fecho. |
| Crescendo da denúncia para aliança e CTA | Bonificar arco ruptura–justificativa–nova posição–chamada, desde que a chamada não seja o único conteúdo. |
| Alegações nominais de crime, corrupção ou facções | Marcar `needs_fact_review` e `needs_legal_review`; separar potencial de atenção de veracidade. |

O relatório audiovisual completo está em `docs/instagram_mbl_local_audiovisual_Dayg4dyhvpA_2026-08-14.md`.
