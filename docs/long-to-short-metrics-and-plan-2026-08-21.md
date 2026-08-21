# Métricas e plano de evolução do Furia Clips — long-form para shorts

**Data:** 21 de agosto de 2026
**Escopo:** precisão de cortes, contexto, localização temporal, multimodalidade, enquadramento e feedback editorial.
**Princípio:** o Furia deve replicar comportamentos verificáveis de produto, não copiar fórmula proprietária nem apresentar score de viralidade como probabilidade.

## 1. Conclusão executiva

É viável aproximar o Furia da experiência de ferramentas como CapCut, OpusClip, Vizard, Descript, Klap e Riverside, mas não por meio da cópia literal de um número de “viralidade”. As páginas oficiais descrevem capacidades e dimensões, porém não publicam pesos, conjunto de treinamento, rótulos ou benchmark independente suficiente para reproduzir exatamente os scores. O caminho tecnicamente correto é transformar o Furia em um sistema de **evidência editorial mensurável**: ele deve encontrar candidatos, demonstrar por que cada candidato é autocontido, medir a qualidade das bordas, conferir áudio/locutor/enquadramento, reduzir redundância e aprender com aprovação ou rejeição humana.

A principal ideia aproveitável do mercado é a separação entre **descoberta**, **ranking**, **edição/reframe** e **revisão**. CapCut declara identificar highlights usando alterações visuais, áudio e contexto, além de permitir escolher duração e pontos de tempo [1]. OpusClip declara um score de 0–99 com Hook, Flow, Value e Trend, filtros/ordenação e feedback de like/dislike [3] [4]. Vizard enfatiza speech, emoções, pacing, fluxo narrativo, edição por transcrição, conteúdo autoconsciente e identificação do locutor [6] [7] [9]. Descript expõe número de clips, duração e critérios de tópico/objetivo [10]. Klap explicita, em sua página comercial, hook, pacing, relevância e densidade de palavras como sinais, além de reframe e ranking [11] [12]. Riverside permite duração, layout, proporção, speaker e palavras-chave [13].

Para o Furia, a métrica primária não deve ser “viralidade”. Deve ser **qualidade do corte para revisão**. O potencial observado pode permanecer como camada secundária, limitada e explicitamente separada de views, ranking, XP e outras métricas pós-publicação. O objetivo do produto continua sendo produzir a nata de cada fonte, mesmo que a quantidade diária fique abaixo da faixa operacional quando os gates de contexto não forem atendidos.

## 2. O que o Furia já tem

O ranker atual já possui sinais editoriais de hook, flow, value, estrutura argumentativa, adequação ao contexto, energia de áudio, densidade de mudança visual, clareza, completude, qualidade contextual, fronteira de locutor, fronteira pergunta–resposta, alinhamento de hook, feedback, família editorial, prior de padrões do Instagram, coerência de capítulo, duração e prior observado do Campaign Hub. Também existem gates para transcrição, speaker, enquadramento, evidência visual, identidade de entidade política, contexto e payoff.

O portfólio já impõe piso de qualidade, deduplicação textual, limites por fonte e família, distribuição round-robin, formato e faixa operacional de 39–50 como alvo, não como quota. O armazenamento de métricas observadas já calcula views, ações informadas, engajamento, velocidade por hora e percentis de uma coorte fornecida, sem inventar retenção ou causalidade.

A lacuna principal não é ausência de sinais textuais. É ausência de **instrumentação de avaliação externa ao score**: o Furia ainda não mede sistematicamente se uma janela coincide com uma referência editorial, se as bordas estão precisas, se um portfólio cobre a fonte sem repetir a mesma tese, se o score está calibrado com decisões humanas ou se o reframe realmente manteve a pessoa certa dentro do quadro.

## 3. Matriz de comparação

| Capacidade observada | CapCut | OpusClip | Vizard | Descript | Klap | Riverside | Garimpo/Chub | Furia atual | Prioridade |
|---|---|---|---|---|---|---|---|---|---|
| Descoberta automática de highlights | Sim, por visual/áudio/contexto declarado | Sim, com curadoria e gênero | Sim, com speech/emoção/pacing | Sim, Create clips | Sim, com sinais multimodais declarados | Sim | Blocos e momentos fortes | Sim, por candidatos textuais/contextuais | Alta |
| Score explicável | Não publica fórmula | Hook/Flow/Value/Trend declarados | Critérios gerais, fórmula não publicada | Não é foco | Hook/pacing/relevância/densidade declarados | Não publica fórmula | Razões, confiança, gates e densidade | Fatores e gates explicáveis | Alta |
| Contexto narrativo | Declara “context” | Flow, Value e gênero | Narrative flow e content-aware | Cortes autocontidos | Relevância e tópico | Seleção por speaker/tópico | Blocos semânticos, pauta, transcrição e contexto de borda | Q&A, payoff, capítulos, recuperação de antecedente | Alta |
| Duração configurável | Sim | Sim; também mid-form | Sim | 10 s–5 min e 1–20 clips | Faixa por produto | Sim | Por bloco | Preferência até 180 s, exceções contextuais | Alta |
| Edição por transcrição | Transcrição/captions | Transcrição | Sim | Forte | Sim | Sim | Transcrição timestampada | Importação, arquivo e contexto | Alta |
| Speaker-aware reframe | Declara subject focus | Declara speaker/object detection | Declara face/speaker tracking e speaker identification | Layouts, sem a mesma promessa | Declara speaker/saliency tracking | Foco por speaker | Locutor e preview; não reframe automático | Política e fallback; tracking opcional | Alta |
| Avaliação de bordas | Não publicada | Não publicada | Evita cortar no meio de frase declarado | Ajuste por texto | Editor de polish | Editor textual | Intervalo/margem/preview | Ajuste manual e gates | Alta |
| Feedback do editor | Não é o foco principal | Like/dislike | Revisão | Revisão | Editor | Revisão | Revisão humana e gates | Aprovação/rejeição persistente | Alta |
| Diversidade e não repetição | Não publicada | Ordenação/filtros | Multi-highlight | Quantidade configurável | Ranking | Geração por foco | Blocos e fontes | Deduplicação e caps | Alta |
| Avaliação independente | Não fornecida | Não fornecida | Não fornecida | Não fornecida | Não fornecida | Não fornecida | Não é benchmark aberto | Ainda parcial | Crítica |

A matriz mostra que a vantagem do Furia pode ser justamente não esconder o processo. O produto deve mostrar **o que foi medido**, **o que foi inferido** e **o que ainda exige revisão**. A experiência visual pode ser limpa, mas a decisão precisa continuar auditável.

## 4. Taxonomia de métricas proposta

### 4.1 Métricas de descoberta e contexto

A primeira camada mede se o trecho vale a pena antes de considerar acabamento visual. Cada candidato deve carregar, no mínimo, `hook_strength`, `narrative_flow`, `value_density`, `topic_relevance`, `question_answer_completeness`, `evidence_presence`, `payoff_completeness`, `context_recovery`, `speaker_turn_valid`, `chapter_coherence` e `needs_review`.

O Furia deve distinguir três objetos que hoje podem ser confundidos. **Hook** é a porta de entrada; **janela editorial** é o intervalo completo que contém a fala necessária; **payoff** é o desenvolvimento ou consequência que fecha a promessa. Uma pergunta ou frase forte sozinha não deve receber o mesmo tratamento de uma janela que inclui pergunta, resposta, evidência e conclusão.

A métrica operacional recomendada é `context_complete_rate`: proporção dos candidatos aprovados pelo editor que já continham premissa, desenvolvimento e fechamento sem exigir recuperação manual. Como métrica complementar, `context_recovery_rate` deve indicar quantos candidatos só ficaram utilizáveis depois que o sistema buscou antecedente ou continuação. Recuperar contexto é útil, mas uma taxa alta pode revelar que a geração inicial está cortando cedo demais.

### 4.2 Métricas temporais

O Furia deve avaliar localização contra referências reais fornecidas pelo editor, por um benchmark autorizado ou por blocos/momentos fortes revisados. A nova camada `modules/quality_metrics.py` implementa a base para isso.

| Métrica | Definição operacional | Uso |
|---|---|---|
| Temporal IoU | Interseção temporal dividida pela união entre candidato e referência | Mede coincidência global de janela |
| Precision@IoU | Candidatos com IoU acima do limiar divididos pelos candidatos avaliados | Mede falsos positivos relativos |
| Recall@IoU | Referências cobertas por candidatos acima do limiar | Mede momentos perdidos |
| HIT@K | Pelo menos uma referência coberta entre os K primeiros | Mede qualidade do ranking |
| Erro de início/fim | Erro absoluto em segundos de cada borda pareada | Mede ajuste fino |
| Hit de borda | Proporção de pares com início e fim dentro de tolerância, por exemplo 2 s ou 5 s | Mede precisão prática para render |
| Cobertura de fonte | União de referências coberta pelo conjunto selecionado | Evita concentrar tudo em um único minuto |
| Redundância semântica | Fração de candidatos que se sobrepõem semanticamente a outro candidato | Evita gerar várias versões da mesma tese |
| Diversidade temporal | Distribuição dos selecionados por capítulos e regiões da fonte | Evita portfólio concentrado |

Os limiares 0,3, 0,5 e 0,7 devem ser mantidos simultaneamente. IoU baixo pode indicar que o momento foi encontrado, mas a borda está ruim; IoU alto indica coincidência mais estrita. Nenhum limiar isolado deve ser chamado de “precisão perfeita”.

### 4.3 Métricas multimodais e técnicas

A transcrição não é suficiente para aprovar um corte. O pipeline deve medir, com estados `observed`, `not_available` e `review_required`, a confiança de ASR, a cobertura temporal, a qualidade de timestamp, a diarização, a taxa de sobreposição de fala, clipping ou silêncio anômalo, variação de energia e continuidade de áudio.

Para vídeo, devem existir métricas de detecção de cena, presença de rosto, cobertura do locutor ativo, perda de sujeito no crop, estabilidade do centro do enquadramento, jitter do crop, proporção de frames sem sujeito, colisão com áreas seguras e preservação de texto ou evidência nas bordas. Uma decisão de não reenquadrar é melhor que um reenquadramento errado; portanto `preserve_composition` deve ser um resultado válido, não um fallback tratado como fracasso.

### 4.4 Métricas de ranking e calibração

O score editorial atual deve continuar sendo um índice relativo e explicável. A avaliação correta é medir se a ordem dos candidatos ajuda o editor. Para isso, o Furia precisa registrar `precision_at_1`, `precision_at_5`, `recall_at_10`, `approval_rate_by_score_bin`, `rejection_rate_by_reason`, `median_review_time_seconds` e `manual_boundary_adjustment_seconds`.

A métrica de calibração mais importante será a relação entre faixas de score e aprovação humana. Se candidatos entre 80–89 forem aprovados apenas 40% das vezes, o sistema não deve chamar esse intervalo de “alto potencial” sem aviso. O score pode continuar útil para ordenar, mas a interface deve exibir que sua calibração ainda é fraca.

### 4.5 Métricas observadas pós-publicação

Views, curtidas, comentários, compartilhamentos, salvamentos, velocidade e posição informada podem ensinar preferências de formato ou tema depois da publicação, mas não devem substituir contexto nem virar ground truth de seleção. A influência deve ser um prior fraco, por conta, plataforma e formato, com amostra mínima, timestamps de coleta e origem explícita. Ausência de dado deve ser `not_observed`, nunca zero.

## 5. Arquitetura recomendada para chegar ao nível profissional

O pipeline recomendado é hierárquico. Primeiro, o Furia deve registrar a identidade da fonte, duração, áudio/vídeo válido e proveniência da transcrição. Depois, deve criar uma timeline de baixo custo com silêncio, energia, mudanças de cena, texto timestampado e capítulos semânticos. Em vídeos de 4–7 horas, essa etapa deve trabalhar em janelas, cache e páginas, não enviar o arquivo inteiro a um modelo online.

Na segunda passagem, o sistema deve gerar famílias de candidatos: pergunta–resposta, tese com consequência, acusação com evidência, reação/humor, explicação, contraponto, revelação e hook com payoff. Cada família precisa ter política própria de início, duração e fechamento. Um candidato só deve subir para o ranking final se sua janela tiver evidência suficiente ou uma marca explícita de revisão.

Na terceira passagem, sinais de texto, áudio e vídeo devem ser combinados. O texto responde “o que está sendo dito”; o áudio ajuda com pausa, ênfase, interrupção e continuidade; o vídeo responde “quem está falando, onde está e se o enquadramento funciona”. Nenhum sinal deve aprovar sozinho uma afirmação política, uma identidade ou um reenquadramento.

Na quarta passagem, o ranker deve fazer duas coisas diferentes. O score editorial ordena qualidade contextual e técnica. O selecionador de portfólio aplica diversidade, deduplicação, limites por fonte/família/formato e cobertura temporal. Assim, o candidato mais popular não consome toda a faixa diária quando existem outros bons momentos em capítulos distintos.

Na revisão, cada card deve mostrar uma nota de qualidade contextual, uma nota de confiança, uma nota técnica, a razão principal, o intervalo semântico, a margem aplicada, a transcrição do trecho, o contexto de borda, o locutor inferido, o estado do enquadramento e os motivos de revisão. O editor deve poder aprovar, rejeitar, ajustar início/fim, escolher preservar composição, selecionar outro layout e registrar o motivo em poucos cliques.

## 6. Plano completo de implementação

| Fase | Entrega | Critério de conclusão | Prioridade |
|---|---|---|---|
| M0 | Instrumentação temporal | IoU, precision/recall, erro de borda, hit de borda e redundância calculáveis com referências reais | Concluída nesta rodada |
| M1 | Contrato de métricas | Payload único para score, confidence, gates, métricas temporais e estados de disponibilidade | Alta |
| M2 | Dataset de referência editorial | Vídeos e transcrições autorizados, blocos, momentos, intervalos ajustados e decisões do editor; sem mídia privada no Git | Crítica |
| M3 | Benchmark de ranking | Relatório por fonte com Recall@K, Precision@K, IoU, bordas, contexto completo e rejeições | Crítica |
| M4 | Segmentação hierárquica longa | Capítulos por shot/pausa/semântica, processamento por janelas e recuperação de contexto entre janelas | Crítica |
| M5 | Geração por famílias | Q&A, tese/payoff, evidência, reação/humor e pergunta-gatilho com políticas distintas | Alta |
| M6 | Speaker e áudio | Diarização opcional, confiança, sobreposição, energia e revisão visual/sonora explícita | Alta |
| M7 | Reframe mensurável | Rastreamento opcional, cobertura de rosto, jitter, perda de sujeito e fallback de composição | Crítica |
| M8 | Ranking calibrado | Score relativo com faixas de aprovação observada e influência limitada do feedback | Alta |
| M9 | Portfólio | Diversidade por tempo, fonte, família, formato e tema; duplicata medida antes da exportação | Alta |
| M10 | HUD editorial | Scorecard simples, estados claros, progresso total, “por que foi escolhido”, “o que revisar” e comparação de intervalo | Alta |
| M11 | Aprendizado persistente | Feedback, ajustes e transcrições arquivados fora do Git, com backup portátil e reconciliação entre notebooks | Crítica |
| M12 | Avaliação contínua | Cada ciclo registra regressões, fonte, versão do score, amostra e limitações; sem alegar viralização | Alta |

## 7. O que deve ser implementado primeiro

A primeira implementação segura é a instrumentação já adicionada: avaliação temporal opcional com referências fornecidas, integrada ao resumo do portfólio sem alterar a seleção quando nenhuma referência existe. Isso permite medir o sistema antes de trocar seus pesos. Os testes cobrem IoU, intervalos no formato do Garimpo, erro de bordas, tolerâncias, ausência de referências e redundância.

A próxima melhoria de maior retorno é conectar a avaliação ao fluxo de revisão. Quando o editor ajustar manualmente o início e o fim, o Furia deve registrar o intervalo original, o intervalo final, o erro de cada borda e a razão do ajuste. Depois de uma amostra suficiente, isso permite calibrar o gerador de candidatos por família e duração, em vez de adivinhar pesos.

Em seguida, deve-se separar visualmente quatro scores: **Contexto**, **Força editorial**, **Técnica** e **Confiança**. O número agregado pode continuar existindo para ordenar, mas nunca deve esconder um veto técnico ou uma transcrição não verificada. Um card com alta força editorial e baixa confiança deve dizer “bom candidato, revisar áudio/locutor”, não aparecer como aprovado.

## 8. O que não deve ser copiado ou priorizado agora

Não é viável nem desejável copiar a fórmula proprietária de Virality Score de qualquer concorrente. Também não é correto inferir que uma promessa comercial de “viral” representa uma probabilidade calibrada. Publicação automática, SEO, hashtags, thumbnails, B-roll generativo, ranking financeiro, XP e scraping agressivo não melhoram diretamente a precisão do corte e permanecem fora do núcleo.

O Furia não deve contornar bloqueios de YouTube ou Instagram, reutilizar cookies, transportar URLs assinadas ou gravar dados privados no GitHub. O Campaign Hub continua somente leitura. Dados de aprovação, rejeição, transcrição e ajuste devem permanecer na pasta persistente local/backup do usuário; o GitHub deve receber apenas código, testes e documentação sanitizada.

## 9. Estado da implementação nesta rodada

Foi adicionado `modules/quality_metrics.py`, com `interval_iou`, `boundary_errors` e `evaluate_temporal_quality`. A função calcula contagem válida, IoU em múltiplos limiares, precision/recall, pares pareados, erro médio/mediano de bordas, hit rate por tolerância e taxa de redundância. Sem referências editoriais, retorna `basis: no_reference` e não fabrica score.

`modules/daily_portfolio.py` agora aceita `reference_intervals` opcional. Quando fornecido, o resumo do portfólio expõe `quality_evaluation`; quando ausente, a seleção e o contrato anterior permanecem inalterados. Foram adicionados testes em `tests/test_quality_metrics.py` e um teste de integração em `tests/test_daily_portfolio.py`.

## 10. Referências

[1]: https://www.capcut.com/tools/ai-long-video-to-short-video "CapCut — Transform Long Videos to Short Clips"
[2]: https://www.capcut.com/create/capcut-auto-reframing-16-9-to-9-16-video "CapCut — Auto Reframing"
[3]: https://help.opus.pro/docs/article/virality-score "OpusClip Help — Virality Score"
[4]: https://help.opus.pro/docs/article/get-clips-faq-1 "OpusClip Help — Result Page Walkthrough"
[5]: https://www.opus.pro/blog/opusclip-clip-different "OpusClip — Clip Different"
[6]: https://vizard.ai/tools/ai-highlights "Vizard — AI Highlights"
[7]: https://vizard.ai/tools/long-video-to-short-video-ai "Vizard — Long Video to Short Video AI"
[8]: https://vizard.ai/tools/ai-reframe "Vizard — AI Reframe"
[9]: https://vizard.ai/blog/vizard-now-automatically-centers-the-active-speaker "Vizard — Speaker Identification"
[10]: https://help.descript.com/hc/en-us/articles/10119670449293-Create-clips-from-your-content "Descript Help — Create Clips"
[11]: https://klap.app/tools/ai-video-clipping-tool "Klap — AI Video Clipping Tool"
[12]: https://klap.app/tools/ai-clip-generator "Klap — AI Clip Generator"
[13]: https://riverside.com/video-editor/video-editing-glossary/magic-clips "Riverside — Magic Clips"
[14]: https://criadores.missao.org.br/garimpo "Criadores Missão — Garimpo"
[15]: https://arxiv.org/html/2606.06926 "SVHighlights — Extremely Long Video Highlight Detection"
[16]: https://arxiv.org/html/2410.04449v1 "Video Summarization Techniques — Review"
[17]: https://www.twelvelabs.io/blog/twlv-i "Twelve Labs — Video Foundation Model Evaluation"


## 8. Validação real do pipeline e calibração segura

Em 21 de agosto de 2026, o pipeline foi executado de ponta a ponta sobre a mídia local `DbWxJ54hbKO.mp4`, com 298,931 segundos, 720×1280, H.264 e áudio AAC. No checkout limpo, a primeira tentativa revelou uma falha de instalação: `faster-whisper` estava declarado, mas não instalado, e o fallback tentava importar `whisper`, que não fazia parte das dependências. Após preparar a dependência declarada, a execução concluiu com 7 clips renderizados; os tempos foram 43,879 s de transcrição, 3,522 s de análise de vídeo, 0,871 s de candidatos, 0,033 s de ranking e 34,103 s de renderização.

Com o código atualizado e banco isolado, a transcrição veio do cache em 0,263 s e o pipeline novamente gerou 7 clips sem rejeição de renderização. O diagnóstico foi explícito: 9 candidatos esperados, 7 candidatos primários e 7 finais, com `quality_pool_below_reference`. Isso significa que o pool ficou abaixo da referência operacional estimada, não que o sistema deva fabricar cortes de menor qualidade para atingir uma quota. A execução no banco compartilhado reconheceu os 7 intervalos já processados e os descartou, comprovando a deduplicação entre execuções.

O ranker passou a fornecer quatro dimensões independentes — contexto, força editorial, técnica e confiança — e a interface as apresenta no próprio card. O scorecard não substitui o score editorial nem representa probabilidade de viralização. Ele existe para que o editor entenda por que um candidato forte ainda pode exigir confirmação de locutor, continuidade, cobertura da transcrição, áudio ou enquadramento. O scorecard também é persistido com campos limitados e reaparece quando o projeto é recarregado.

A avaliação temporal agora inclui cobertura de referência e `HIT@K` para K=1, 3, 5 e 10, além de IoU, precision/recall, erro de bordas e taxa de redundância. Essas métricas só devem ser calculadas quando o editor fornecer intervalos de referência reais; sem referência, o sistema não inventa uma qualidade objetiva. Também foi corrigida a restauração de `start_time`/`end_time` no estado do frontend, evitando que um projeto reaberto perca os limites usados para pré-visualização e ajuste manual.

A ausência de `faster-whisper` agora gera uma mensagem acionável sobre a instalação do projeto, em vez de um `ModuleNotFoundError` de um fallback não declarado. Nenhum peso do ranker foi recalibrado com esse vídeo porque ainda não existem rótulos humanos confiáveis dos melhores e piores intervalos dessa fonte. A próxima calibração válida deve usar decisões aprovadas/rejeitadas e, quando possível, intervalos de referência anotados.


## 9. Reprodutibilidade do checkout limpo

A verificação de um checkout limpo da branch publicada encontrou uma inconsistência no teste do modelo facial: o teste exigia o binário `blaze_face_short_range.tflite` dentro do Git, enquanto o contrato documentado pelo instalador é baixá-lo em runtime, validar o SHA-256 e continuar com composição original quando o download ou o MediaPipe não estiverem disponíveis. O teste foi ajustado para aceitar a ausência do binário no checkout e validar seu tamanho somente quando ele já estiver instalado. A mudança evita uma falsa falha de instalação e mantém o modelo fora do Git, conforme a política de não publicar assets gerados ou de runtime.

Depois da correção, a suíte local voltou a passar com 512 testes. O asset facial continua opcional, e a ausência dele não deve ser interpretada como ausência de suporte ao facetracking: significa que o launcher ainda precisa preparar o modelo quando o recurso for ativado.
