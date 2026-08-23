# Plano mestre de precisão do Furia Clips — 2026-08-21

## 1. Enquadramento correto

O **norte imediato** do Furia continua sendo produzir cortes do Renan Santos/MBL que sejam curtos quando possível, autossuficientes, contextualmente completos, fiéis ao que foi dito, com tese identificável, payoff preservado, locutor correto e headline compatível com a fala.

As ideias de WhatsApp, smartwatch, pesquisa de última hora, dossiês, alertas e acionamento remoto pertencem ao **futuro da ferramenta**, em uma fase final. Elas não devem desviar os próximos ciclos do problema principal: melhorar a seleção, o contexto, as bordas, a precisão multimodal e o aproveitamento real do Campaign Hub e do universo MBL.

> Regra de produto: primeiro o Furia precisa escolher e cortar bem; depois ele deve automatizar a operação em torno de uma decisão editorial confiável.

## 2. Diagnóstico de partida

O motor já possui gates de início de frase, referências anafóricas, pergunta–resposta, payoff, evidência, sobreposição, timestamps ambíguos, locutor e identidade Renan-first. Também possui reparos de borda, alinhamento de turnos em entrevistas, segmentação temática local, descarte de propaganda/abertura/encerramento, filas Chub separadas e processamento por intervalo.

O Campaign Hub já fornece snapshots locais read-only para as contas `@renansantosmbl`, `@renansantosreserva` e `@partidomissao`. O Furia preserva highlights, blocos, possíveis cortes, tópicos, métricas, entidades, transcrições, locutor, riscos, confiança e proveniência quando estão disponíveis. Entretanto, o ranking usa a maior parte dessa memória de forma conservadora: priors de hook e evidência de bloco têm influência pequena e não substituem os gates.

A evidência quantitativa mais importante mostra por que aumentar pesos não é a resposta. Em uma fonte real com 66 highlights do Acervo, o recall em IoU 0,10 foi 7,58% no genérico sem Chub, 27,27% no genérico com Chub, 10,61% no Renan-first sem Chub e 10,61% no Renan-first com Chub. O Chub aumentou a descoberta, mas no modo Renan-first 24 de 30 propostas foram filtradas por falta de `renanSpeaking=true`, sem ganho de recall publicável. O problema prioritário é **recuperar e alinhar melhor os momentos corretos**, não fazer o histórico dominar a qualidade.

## 3. Meta de avaliação

O Furia deve deixar de usar uma única noção de “score” como se ela representasse tudo. A avaliação será separada em localização, qualidade editorial, identidade, segurança e utilidade operacional.

| Dimensão | Métricas recomendadas | O que prova |
| --- | --- | --- |
| Localização | Recall@IoU 0,10/0,25/0,50; erro absoluto de início e fim; cobertura dos highlights | O motor encontrou a região temporal correta |
| Seleção | Precision@K; nDCG; ganho de aprovação no top-K; taxa de duplicatas | O ranking colocou bons candidatos acima dos demais |
| Contexto | Taxa de início natural; antecedente recuperado; contexto autossuficiente; ponte pergunta–resposta | O espectador entende sem a live original |
| Payoff | Fechamento de tese; conclusão; resposta completa; corte em suspensão aceitável | O vídeo entrega o que prometeu |
| Locutor | Precisão/recall de Renan; taxa de `speaker_review`; conflitos Chub–diarização | O foco Renan-first não atribui fala incorreta |
| Fidelidade | Aderência da headline à transcrição; ausência de afirmação não dita; preservação de negação | O corte não cria uma afirmação editorialmente falsa |
| Visual | Rosto centralizado; troca de cena; OCR/documento preservado; composição por formato | O render continua legível e publicável |
| Operação | Tempo até primeira proposta; tempo até aprovação; reprocessamentos; cancelamentos; falhas de render | O sistema economiza trabalho de verdade |

A avaliação deve ser dividida por fonte: live solo, entrevista, sabatina, debate, discurso, notícia, reação, tela/documento, abertura e encerramento. Um ganho em podcast não pode ser tratado como prova de ganho em uma live política longa.

## 4. Fase A — Fundamento de dados e benchmark

A primeira melhoria de precisão deve ser um benchmark editorial versionado. Cada item deve apontar para uma fonte autorizada e conter intervalo de referência, origem, transcrição, locutor, tema e rótulos humanos. O conjunto deve separar desenvolvimento de teste por fonte, nunca por corte aleatório da mesma live, para evitar vazamento temporal.

Os rótulos mínimos são: `good_interval`, `speaker_is_renan`, `context_complete`, `payoff_complete`, `starts_naturally`, `question_answer_complete`, `evidence_present`, `headline_faithful`, `format_fit`, `needs_fact_review`, `approved`, `rejected` e `rejection_reasons`. As rejeições devem ser categorizadas em começo sem contexto, final sem payoff, fala de terceiro, intervalo longo, intervalo curto demais, erro de transcrição, headline infiel, propaganda/jingle, duplicata, risco factual e problema visual.

O benchmark Chub existente continua útil para recall temporal, mas deve ganhar uma camada de qualidade humana. Highlights publicados são **referência editorial**, não rótulo automático de verdade. Sempre que possível, registrar também o motivo pelo qual um corte publicado foi escolhido e quais versões quase idênticas foram rejeitadas.

### Hipótese A1

Se o Furia tiver um benchmark com rótulos separados para localização, contexto, payoff, locutor e headline, então cada ciclo poderá provar qual parte melhorou, em vez de confundir aumento de volume com qualidade.

### Critério de publicação

Nenhuma mudança de ranking deve ser publicada sem comparação before/after no mesmo conjunto congelado, com pelo menos recall, precision@K, taxa de contexto completo e taxa de falsos Renan. Se uma métrica subir e outra cair de modo editorialmente relevante, a mudança fica em revisão.

## 5. Fase B — Ingestão, intervalo e sincronização

A identidade persistente de intervalo deve ser implementada antes de novas mudanças de score. Ela deve combinar identidade da fonte original, início/fim absolutos, hash da transcrição utilizada e versão do pipeline. O timestamp local de uma cópia processada nunca deve substituir a identidade da fonte.

O projeto deve guardar explicitamente a origem de cada transcrição: `manual`, `imported`, `faster_whisper`, `remote`, `edited`, versão do modelo, idioma, cobertura, offset, hash do conteúdo e faixa usada. Se o usuário fornecer uma transcrição, o job deve registrar que ela foi aceita e impedir que um caminho silencioso a substitua sem informar.

### Hipótese B1

Se a fonte, faixa e transcrição tiverem identidade explícita, o Furia poderá reprocessar a mesma faixa com segurança, comparar versões e usar o Chub sem misturar timestamps absolutos e locais.

## 6. Fase C — Recall-first multimodal

A geração de candidatos deve ter dois estágios. O primeiro é barato e amplo: seeds Chub, busca lexical/semântica na transcrição, densidade de entidades, picos de energia, fala contínua, perguntas, mudanças de tópico, mudanças de cena, reações e regiões visualmente informativas. Esse estágio deve maximizar recall e não descartar cedo demais.

O segundo estágio é caro e preciso: expandir cada seed para a menor janela que contenha antecedente, pergunta quando necessária, tese, resposta, evidência e payoff. A expansão deve parar quando o raciocínio se fechar, quando houver mudança de assunto ou quando atingir a preferência de duração. A janela pode ser marcada para revisão sem ser perdida no diagnóstico.

O motor deve gerar candidatos de três origens claramente separadas: `campaign_hub_guided`, `local_retrieval` e `local_discovery`. O Chub deve orientar onde procurar e que tipo de conteúdo já funcionou, mas candidatos locais não devem desaparecer só porque não há seed Chub.

### Hipótese C1

Se a fase inicial parar de exigir contexto completo e a fase posterior fizer a expansão/revisão, o recall do Renan-first pode subir sem transformar o pool publicável em cortes quebrados.

## 7. Fase D — Contexto e payoff como estrutura narrativa

O contrato textual atual deve evoluir de flags lexicais para uma estrutura narrativa explícita. Cada candidato deve tentar identificar: situação, pergunta ou provocação, tese, sustentação, consequência e fechamento. Nem todo corte precisa conter todas as partes, mas o sistema deve saber o que está ausente.

A recuperação de contexto deve usar janela anterior e posterior, referências anafóricas, entidades e tópicos. Deve distinguir uma pergunta que o convidado responde de uma pergunta retórica, uma pergunta feita por Renan de uma pergunta feita a Renan e uma frase que apenas contém “quem/como/por que” sem exigir resposta.

O payoff deve ser classificado como conclusão, resposta, revelação, consequência, frase de impacto, reação, chamada para ação ou suspensão intencional. Uma suspensão só deve ser aprovada quando for uma unidade editorial válida, não quando o corte simplesmente terminou por limite de janela.

A regra de duração deve ser “menor janela suficiente”, não “mais curto sempre”. A duração deve variar por formato, velocidade de fala, quantidade de contexto e tipo de payoff.

### Hipótese D1

Se contexto e payoff forem representados como estrutura e não apenas como score textual, o Furia reduzirá cortes que contêm palavras fortes, mas não entregam a tese que o hook promete.

## 8. Fase E — Locutor Renan-first e identidade multimodal

`Renan falando`, `Renan aparecendo`, `Renan sendo citado` e `Renan sendo o assunto` devem ser campos diferentes. O motor não deve tratar citação de “Renan” como prova de que ele fala.

A identificação deve combinar, com confiança separada: turnos de diarização, voz conhecida quando houver amostra autorizada, rosto quando visível, posição na transmissão, texto do turno e evidência Chub. O Chub pode confirmar um bloco histórico, mas não deve ser tratado como diarização independente.

Quando as evidências discordarem, o resultado deve ser `speaker_review_required`, acompanhado da origem de cada evidência. O objetivo não é zerar todo risco por um gate agressivo; é recuperar material de Renan e marcar corretamente a incerteza.

### Hipótese E1

Se o sistema distinguir confirmação, probabilidade e desconhecimento do locutor, o Renan-first poderá aumentar recall sem publicar silenciosamente falas de terceiros.

## 9. Fase F — Uso profundo e seguro do Campaign Hub

A integração deve avançar em camadas. A primeira camada é sincronização local read-only com status, data, versão e contagem por conta. A segunda é alinhamento de source IDs, timestamps e offsets. A terceira é memória editorial por conta, formato, tema, hook, duração, locutor e resultado humano. A quarta é feedback de aprovação/rejeição e headline, sempre com amostra e confiança.

Os dados mais úteis a priorizar no Chub são: highlights e intervalos publicados; blocos com `renanSpeaking`; perguntas-gatilho e resumos; tópicos e entidades; `self_contained_rank`; `density_rank`; formatos dos posts; duração; hook/headline; métricas estabilizadas; riscos e motivos de revisão; e relação entre vídeo longo, corte publicado e conta de destino.

O Furia deve mostrar uma ficha de evidência por candidato: bloco correspondente, highlight correspondente, intervalo absoluto e local, conta, locutor, confiança, tópicos, possíveis cortes, risco, motivo de promoção ou exclusão e quais gates locais ainda faltam. Essa ficha deve ser explicativa, não uma ordem automática de publicação.

O prior deve ser calculado por coorte suficiente e com decaimento temporal. Um hook que funcionou no Instagram não é universalmente bom; ele precisa ser comparado por conta, formato e tipo de fonte. Reels publicados continuam `reference_only`; lives cruas e fontes longas permanecem `processing_source`.

### Hipótese F1

Se o Chub for usado principalmente para localizar, contextualizar, comparar e explicar candidatos, e não apenas para somar pontos, ele poderá melhorar recall e revisão sem contaminar o ranking com métricas de audiência incompatíveis.

## 10. Fase G — Ranking em dois níveis

O ranking deve ser dividido em `eligibility` e `ordering`. Eligibility verifica segurança mínima: mídia válida, duração possível, transcrição suficiente, borda não quebrada, locutor compatível ou revisão explícita, ausência de propaganda dominante e inexistência de conflito técnico grave. Ordering organiza os candidatos elegíveis por adequação editorial.

O ordering deve incluir hook, tese, novidade, consequência, emoção, clareza, contexto, payoff, duração, locutor, relevância ao pedido, adequação ao formato e diversidade. Chub, feedback humano e sinais de Instagram devem ser priors limitados e auditáveis.

Depois de reunir amostra suficiente, o Furia pode aprender um modelo pairwise ou uma regressão calibrada a partir de aprovados/rejeitados, mas não deve começar por pesos livres. O primeiro estágio de feedback deve mostrar quais motivos de rejeição mudaram o ranking e aplicar limites por família de fonte.

### Hipótese G1

Se o sistema aprender primeiro preferências pairwise e motivos de rejeição, em vez de otimizar “viralidade”, o top-K ficará mais próximo do trabalho real do editor.

## 11. Fase H — Validação visual e produção por formato

A validação visual deve ser seletiva. O Furia não precisa enviar a live inteira para um modelo multimodal: deve amostrar frames e pequenos trechos dos candidatos, com compressão, resolução e duração controladas. Deve verificar rosto, presença de Renan, tela, documento, cartaz, legenda, troca de cena, crop, texto queimado, sobreposição e áudio.

Os presets precisam ser verdadeiramente diferentes:

| Formato | Regra principal |
| --- | --- |
| 9:16 | Rosto/locutor centralizado, captions legíveis, safe areas, payoff rápido e headline curta |
| 1:1 | Composição mais larga, preservação do contexto visual, headline de publicação/fake tweet quando solicitado |
| Fake tweet | Texto fiel à legenda/transcrição, indicação clara de que é tratamento visual, sem transformar opinião de jornalista em fala de Renan |

O arquivo de projeto deve preservar corte original, versão reeditada, texto removido, bordas alteradas, preset e headline. Isso permite voltar um passo sem repetir toda a análise.

## 12. Fase I — Headline fiel e revisão humana rápida

A headline deve ser produzida depois da janela final e da transcrição final. Deve receber apenas o texto e os metadados permitidos daquele corte, não uma descrição vaga do tema. O gerador deve produzir versões por formato, classificar literalidade e marcar entidades ou afirmações que não aparecem no áudio.

A interface deve permitir comparar headline literal, headline de tese, headline de conflito e headline de pergunta. Nenhuma versão deve introduzir número, acusação, local, pessoa ou causalidade não sustentada pela fala ou por evidência explicitamente anexada.

A aprovação humana precisa ser rápida: botões de aprovar, rejeitar, ajustar borda, ajustar headline, locutor incorreto, contexto insuficiente, payoff faltante, duplicata e risco factual. Cada decisão deve alimentar o dossiê local com fonte, versão do pipeline e motivo.

## 13. Ordem de execução recomendada

| Prioridade | Ciclo | Mudança principal | Critério de sucesso |
| ---: | --- | --- | --- |
| 1 | P1 | Identidade persistente de fonte/faixa/transcrição | Reprocessar faixas sem colisão e sem misturar timestamps |
| 2 | P2 | Benchmark editorial versionado | Métricas separadas e teste reproduzível |
| 3 | P3 | Auditoria de transcrição manual/importada | A transcrição fornecida é usada e aparece na proveniência |
| 4 | P4 | Recall-first Chub + busca local | Aumentar recall sem piorar taxa de contexto no top-K |
| 5 | P5 | Alinhamento de bordas por palavra/turno/pausa | Reduzir erro de início/fim e cortes no meio da fala |
| 6 | P6 | Identidade Renan multimodal | Reduzir falso Renan sem derrubar recall de Renan |
| 7 | P7 | Contexto/payoff estruturados | Aumentar aprovação humana por completude |
| 8 | P8 | Integração profunda do Chub | Melhorar recall, evidência e explicabilidade por conta/formato |
| 9 | P9 | Ranking pairwise com feedback | Melhorar precision@K e aprovação do top-K |
| 10 | P10 | Validação visual e presets | Menos retrabalho em 9:16, 1:1 e fake tweet |
| 11 | P11 | Headline fiel e dossiê de revisão | Menos headlines inutilizáveis e erros factuais |
| 12 | P12 | Automação final remota | Comandos, alertas, pesquisa e publicação com confirmação |

## 14. Fase final futura da ferramenta

Somente depois de o núcleo editorial estar validado devem entrar os módulos de plataforma. O primeiro canal remoto recomendado é um bot com webhook e autenticação forte, preferencialmente Telegram para prototipação e WhatsApp Cloud API para operação institucional. O smartwatch deve funcionar como superfície de alerta e confirmação simples, não como editor completo.

A camada de pesquisa poderá receber pedidos como “investigue se X ocorreu” e montar um dossiê com fontes recentes, data de coleta, trechos, imagens, vídeos, links, entidades, nível de confiança e divergências. Ela deve separar descoberta de confirmação, nunca afirmar que uma notícia é verdadeira apenas porque apareceu em uma busca. O Chub servirá para complementar o universo MBL e localizar material relacionado, mas cada afirmação terá sua fonte.

A automação final também poderá monitorar fontes autorizadas, detectar novas lives, criar jobs por faixa, gerar fila de revisão, avisar no celular, preparar formatos e aguardar confirmação antes de publicar. Nenhum canal remoto deve permitir download arbitrário, divulgação de credenciais, publicação automática ou ação irreversível sem controle de permissão.

## 15. Regra de continuidade para futuras IAs

A próxima IA deve ler `START_HERE.md`, `PROJECT_STATE.md`, `CUTTING_AUDIT_2026-08-21.md`, este plano, `RESEARCH_CUTTING_PRECISION_2026-08-21.md` e `HANDOFF_SINCE_CLAUDE_2026-08-21.md`. Deve implementar uma hipótese por ciclo, registrar before/after, executar a suíte, não incluir mídia real/segredos no Git e publicar somente na branch isolada.

A pergunta obrigatória antes de qualquer novo peso é: **qual métrica do benchmark ele melhora, em qual família de fonte, e qual risco pode piorar?** Se a resposta não for mensurável, a mudança deve permanecer como experimento ou documentação.

## Referências externas

[1]: https://arxiv.org/html/2410.10818v1 "TemporalBench: Benchmarking Fine-grained Temporal Understanding for Multimodal Video Models"
[2]: https://openaccess.thecvf.com/content/WACV2025/papers/Islam_Unsupervised_Video_Highlight_Detection_by_Learning_from_Audio_and_Visual_WACV_2025_paper.pdf "Unsupervised Video Highlight Detection by Learning from Audio and Visual Recurrence — WACV 2025"
[3]: https://mn.cs.tsinghua.edu.cn/xinwang/PDF/papers/2022_A%20Survey%20on%20Temporal%20Sentence%20Grounding%20in%20Videos.pdf "A Survey on Temporal Sentence Grounding in Videos"
[4]: https://docs.pyannote.ai/tutorials/speech-to-text-diarization "pyannoteAI — Speech-to-text diarization"
[5]: https://www.opus.pro/ "OpusClip — ClipAnything, ReframeAnything, templates, API e automação"
[6]: https://help.opus.pro/docs/article/virality-score "OpusClip — Virality Score"
[7]: https://vizard.ai/tools/ai-clips-generator "Vizard — AI Clips Generator"
[8]: https://www.descript.com/tools/video-editor "Descript — text-based video editing"
