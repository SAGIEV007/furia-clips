# Análise do catálogo público do Instagram

**Arquivo de origem:** `docs/instagram-api-catalog.csv`. A amostra contém **24 linhas normalizadas**, com contagens públicas observadas para os dois perfis [5].

> Esta versão distingue evidência observada de hipótese editorial. Ela não transforma curtidas ou visualizações em uma garantia de viralidade e não substitui a análise do vídeo individual.

## Métricas observadas

![Visualizações observadas por Reel](./instagram-catalog-views-log.png)

| Perfil | Amostra | Vídeos | Visualizações na amostra | Mediana de visualizações | Máximo | Engajamento médio por visualização | Formato predominante |
|---|---:|---:|---:|---:|---:|---:|---|
| `renansantosreserva` | 12 | 12 | 277803 | 5831 | 180609 | 18.02% | vertical_4x5 |
| `renansantosmbl` | 12 | 12 | 5087906 | 209292 | 2687788 | 24.83% | vertical_9x16 |

## Padrões editoriais preliminares

Na amostra disponível, os Reels combinam afirmação política direta, conflito com adversários ou instituições, reação a fatos noticiosos, humor/meme e chamadas para ação. Esses padrões foram observados nos itens públicos retornados pelos perfis [1] [2] e normalizados no catálogo local [5]. O perfil principal apresenta escala de visualizações muito superior à conta de reserva; por isso, o ranking do Furia Clips deve comparar cortes dentro de uma mesma live e normalizar sinais de audiência histórica, em vez de copiar limiares absolutos de um perfil para outro.

Os formatos observados variam entre 9:16, 4:5 e quadrado. Para o produto, isso sustenta um enquadramento seguro com prioridade a 9:16, preservando margem para rosto, legendas futuras e elementos de interface; o sistema deve registrar o formato original e não cortar automaticamente uma fala importante para preencher a tela.

A presença de legendas de publicação curtas, hashtags e CTAs sugere que o corte precisa entregar uma frase-âncora rapidamente, mas o catálogo não informa duração nem retenção. Consequentemente, a regra de seleção deve privilegiar contexto autossuficiente, progressão e payoff medidos na transcrição, deixando legenda visual e música como pós-produção.

## Itens de maior alcance observados

### `renansantosreserva`

| Reel | Visualizações | Curtidas | Comentários | Leitura editorial pública |
|---|---:|---:|---:|---|
| [Db8wfUyFHiV](https://www.instagram.com/p/Db8wfUyFHiV/) | 180,609 | 29,878 | 969 | Ué, será que esse jornalista mudou de ideia sobre o Renan Santos? 🤔  #Eleições2026 #Política #PartidoMissão #RenanSantos #eleições |
| [Db9ImrRjMh4](https://www.instagram.com/p/Db9ImrRjMh4/) | 28,707 | 4,228 | 44 | Por essa ninguém esperava! Renan Santos defendeu Mano Brown e falou a verdade sobre Oruam, que muita gente não tem coragem de admitir.  #RenanSantos #Política #PartidoMissão #Oruam |
| [Db8tEDiD0eD](https://www.instagram.com/p/Db8tEDiD0eD/) | 22,595 | 3,898 | 95 | Piada! O sistema está tentando esconder o que as redes sociais não escondem, Renan Santos está GIGANTE e crescendo cada vez mais.  #Eleições2026 #Política #PartidoMissão #RenanSant |
| [Db8-QOnCemH](https://www.instagram.com/p/Db8-QOnCemH/) | 13,793 | 2,621 | 28 | Ao ser questionado se acataria todas as decisões do STF em um eventual governo seu, Renan Santos disse: decisão ilegal não se cumpre!  #RenanSantos #Política #PartidoMissão #Eleiçõ |
| [Db9PagNj1QQ](https://www.instagram.com/p/Db9PagNj1QQ/) | 11,068 | 2,257 | 119 | Renan Santos afirma que o Brasil precisa ter sua própria Bomba Atômica e jornalistas ficam chocado!  #RenanSantos #Política #PartidoMissão #Eleições2026 #Direita |

### `renansantosmbl`

| Reel | Visualizações | Curtidas | Comentários | Leitura editorial pública |
|---|---:|---:|---:|---|
| [DZ7ZY6EtlNq](https://www.instagram.com/p/DZ7ZY6EtlNq/) | 2,687,788 | 456,503 | 12,409 | O que é o mundo por trás da propaganda do PT  Siga @renansantosmbl |
| [DbWxJ54hbKO](https://www.instagram.com/p/DbWxJ54hbKO/) | 630,418 | 126,394 | 8,642 | O PT destruiu minha vida 3 vezes.  Siga @renansantosmbl |
| [Db8fcmItfCw](https://www.instagram.com/p/Db8fcmItfCw/) | 326,665 | 67,680 | 3,007 | Veja como isso é bom!   Siga @renansantosmbl |
| [Db6qoCUBulc](https://www.instagram.com/p/Db6qoCUBulc/) | 324,954 | 40,661 | 747 | Nao deixa que a última risada seja a deles. Siga @renansantosmbl |
| [Db6g5dfteDn](https://www.instagram.com/p/Db6g5dfteDn/) | 242,299 | 50,893 | 1,562 | Decisão ilegal não se cumpre 👍🏻 Siga @renansantosmbl |

## Limitações e próximo nível de evidência

A coleta integral está sujeita ao limite público do Instagram: a primeira página é acessível, mas as requisições seguintes sofreram HTTP 429, comportamento compatível com as limitações de automação descritas na documentação do extrator e em referências técnicas recentes [3] [4]. A tentativa via gallery-dl também não localizou os perfis sem autenticação. O coletor foi deixado retomável e registra cada página bruta [6]. Para cumprir literalmente a análise audiovisual de todos os Reels, seria necessário acesso autenticado ou uma exportação autorizada dos dados/mídias, além de tempo e capacidade de análise proporcionais a milhares de vídeos.

A calibração do algoritmo nesta etapa deve ser tratada como **calibração inicial**, não como conclusão estatística. O próximo conjunto de dados prioritário é: duração, transcrição, início/fim do trecho, música/áudio, formato, presença de rosto e métricas de alcance por Reel. Com isso, será possível ajustar os gates de contexto e payoff com evidência audiovisual real.

## Referências

[1]: https://www.instagram.com/renansantosreserva/ — Perfil público @renansantosreserva.
[2]: https://www.instagram.com/renansantosmbl/ — Perfil público @renansantosmbl.
[3]: https://manpages.debian.org/unstable/gallery-dl/gallery-dl.conf.5.en.html — Documentação do gallery-dl 1.32.9.
[4]: https://scrapfly.io/blog/posts/how-to-scrape-instagram — Referência técnica recente sobre endpoints públicos e limites de automação.
[5]: ./instagram-api-catalog.csv — Catálogo normalizado salvo no repositório.
[6]: ./instagram-full-collection.log — Log local da coleta paginada e dos checkpoints.


## Complemento audiovisual: catálogo dos 12 Reels baixados

### Escopo e nível de evidência

Além da amostra pública de métricas já registrada acima, foram baixados e catalogados 12 Reels do perfil `@renansantosreserva`. Sete receberam relatórios audiovisuais completos, com estrutura temporal, cortes, enquadramento, áudio e contexto. Cinco receberam inspeção visual quadro a quadro e leitura da legenda pública; quatro desses cinco não puderam receber análise multimodal online nem transcrição por falta de créditos, e o quinto também permanece sem transcrição completa. Essa distinção é obrigatória: os cinco últimos não devem ser usados como prova de frase exata, música ou minutagem fina.

| Grupo | Reels | Evidência disponível | Uso permitido |
|---|---|---|---|
| Relatório audiovisual completo | `Db-2Y0OFNtr`, `Db-9SUJG2F8`, `Db_Ax9tmcFu`, `Db_ENAyjO3R`, `Db_F8qvE_Z_`, `Db_HmR1iOy1`, `Db_LANvAgY6` | Vídeo analisado, estrutura, cortes, áudio, contexto e classificação editorial | Regras positivas, contraexemplos e critérios de ranking |
| Inspeção visual e legenda pública | `Db_OfZDjKMW`, `Db_R92njTCq`, `Db_VUXqjnyO`, `Db_Y07LFV7J`, `Db_aVwFEkfD` | Quadros amostrados, headline/legenda pública, formato e composição | Padrões de layout, OCR, proporção e hipóteses; não validar áudio ou frase exata |

Os sete relatórios completos classificaram seis peças como `gold` e uma como `good`. O `good`, `Db_LANvAgY6`, é um contraexemplo útil: a peça engaja, mas o layout 1:1, o GC de emissora e a prova visual tornam inadequado forçar um crop vertical. Isso refina a recomendação preliminar do catálogo: **9:16 é preferível somente quando o reframe for seguro; preservar a proporção original é a decisão correta quando o layout carrega contexto**.

### DNA editorial recorrente

O padrão mais frequente é uma peça curta que comunica a tese antes de o espectador entender toda a fala. Um bloco superior branco, geralmente no formato de captura de publicação ou headline, informa a situação, a controvérsia ou a promessa do vídeo. O sistema deve detectar e preservar esse bloco quando ele já existe, sem sobrepor uma nova legenda automática na mesma área.

A composição visual costuma combinar **locutor ativo e referência temática**. A referência pode ser fotografia fixa de autoridade ou adversário, B-roll de escola, palco ou notícia, ou uma coluna estática de branding. O podcast aparece em plano médio ou close-up, e o corte alterna entre quem pergunta e quem responde. Quando há uma câmera estável e um locutor identificado, o zoom digital discreto pode funcionar como ênfase; quando há split-screen, imagem fixa, várias faces ou GC de emissora, o crop automático agressivo tende a destruir contexto.

As legendas dinâmicas usam fonte sem serifa pesada, alto contraste, frases curtas e destaques cromáticos, principalmente amarelos. Esse padrão é útil como sinal visual, mas **não deve ser o foco do seletor de cortes**. A transcrição deve servir primeiro para entender tese, pergunta, resposta, pausa, sobreposição e conclusão; as legendas entram como OCR para detectar áreas ocupadas e como evidência de edição já feita.

| Padrão observado | Frequência qualitativa | Tradução para o Furia Clips |
|---|---:|---|
| Headline ou contexto fixo no topo | Muito alta | Detectar OCR, preservar área segura e usar headline como contexto |
| Split-screen, foto fixa ou B-roll temático | Muito alta | Reconhecer composição e penalizar crops que removam referência necessária |
| Legenda curta com destaque amarelo | Muito alta | Usar para OCR/área segura, não para ranquear um corte por quantidade de texto |
| Locutor em plano médio ou close-up | Alta | Identificar active speaker e manter rosto, microfone e gestos |
| Jump cuts e redução de pausas | Alta | Remover dead air conservadoramente; preservar pausas com função emocional |
| Voz acima de música ou trilha | Alta nos relatórios completos | Detectar voz, música e clipping; nunca deixar trilha superar fala |
| Música temática | Variável | Tratar como sinal opcional de edição, não como requisito de seleção |
| Conclusão ou CTA visível | Alta | Exigir payoff ou penalizar término antes da consequência |

### Famílias editoriais

**Entrevista com pergunta e resposta.** É a família central para lives e entrevistas do Renan. O hook pode ser pergunta do host, acusação ou comparação. O corte ideal inclui o contexto mínimo da pergunta e a resposta até o ponto em que a tese fecha. `Db_ENAyjO3R` mostra a forma limpa, com pergunta curta, transição para Renan e resposta longa. `Db-9SUJG2F8` mostra o confronto político com argumento denso e card final de conversão. `Db_OfZDjKMW`, observado visualmente, adiciona vários participantes; exige diarização e não deve ser dividido apenas por troca de rostos.

**Tese política com problema, exemplo e solução.** Nos Reels sobre professores, escolas, paternidade e política fiscal, o maior valor editorial está na progressão `proposição → evidência/exemplo → saída`. `Db_HmR1iOy1` abre com o problema da humilhação do professor, desenvolve o debate e chega à solução. `Db_Ax9tmcFu` também é exemplo positivo de tese, desenvolvimento e conclusão. Palavras fortes como “humilhado”, “autoridade” ou “problema fiscal” não bastam: o score deve subir quando houver relação causal, exemplo, número, nome, proposta ou consequência.

**Declaração emocional ou narrativa de resiliência.** `Db-2Y0OFNtr` combina crescimento político, emoção, imagem heroica, entrevista e trilha. Essa família diversifica os 39–50 cortes diários: nem todo corte precisa ser debate ou ataque. O seletor deve reconhecer emoção, vulnerabilidade, surpresa, humor ou orgulho, desde que haja ideia completa.

**Notícia ou B-roll recontextualizado.** `Db_LANvAgY6` combina notícia policial, headline política, âncora, repórter e CFTV. A edição é funcional, mas a composição 1:1 e os GC limitam a adaptação vertical. Deve virar contraexemplo de qualidade: o sistema preserva original e sinaliza revisão humana.

**Pronunciamento direto com face estável.** `Db_aVwFEkfD`, catalogado por amostragem, mostra Renan falando sozinho sobre a filiação de Flávio Bolsonaro ao Partido Missão, com headline e legendas cinéticas. Essa configuração é promissora para autoenquadramento, mas permanece `unknown` sem áudio/transcrição completa. Só deve receber 9:16 se os gates de rastreamento forem atendidos.

### Ranking editorial explicável

O ranking deve medir a qualidade do segmento, não apenas volume de palavras, intensidade sonora ou ocorrência de termo político. A pontuação sugerida soma 100 pontos.

| Componente | Peso | Pergunta operacional |
|---|---:|---|
| Autossuficiência de contexto | 20 | Quem fala, sobre o quê e por que importa ficam claros? |
| Hook e quebra de padrão | 15 | Os primeiros segundos criam curiosidade, conflito, urgência, humor ou emoção? |
| Tese e densidade argumentativa | 20 | Há ideia específica e relevante, em vez de opinião vaga? |
| Conclusão ou payoff | 15 | O trecho chega a consequência, exemplo, resposta, proposta ou fechamento? |
| Tensão, emoção ou surpresa | 10 | Há discordância, indignação, vulnerabilidade, humor, contraste ou virada? |
| Especificidade e evidência | 8 | Há nome, número, caso, mecanismo, comparação ou exemplo? |
| Clareza audiovisual | 7 | A voz é inteligível, sem sobreposição destrutiva, clipping ou ruído impeditivo? |
| Editabilidade e enquadramento | 5 | Há início/fim limpos e aspecto seguro sem cortar locutor ou GC? |

Devem existir penalidades explícitas por início sem contexto, final abrupto, sobreposição não resolvida, múltiplos locutores sem diarização, GC coberto, crop inseguro, repetição semântica e dependência de reação visual fora da tese. Um score alto com `speaker_confidence` ou `context_sufficiency` baixo deve aparecer como **revisão obrigatória**, não como resultado definitivo.

Para oito lives longas e a meta de 39–50 cortes por dia, a primeira camada pode gerar candidatos e a segunda selecionar apenas a nata, com deduplicação semântica e diversidade entre conflito, proposta, entrevista, emocional, humor, notícia e cortes descontraídos. A quota nunca deve ser alcançada reduzindo o limiar de qualidade.

### Política de enquadramento derivada da amostra

A política em [`docs/auto-framing-policy.md`](./auto-framing-policy.md) é reforçada. O modo padrão preserva o aspecto original em split-screen, imagem fixa, múltiplas faces, headline, GC, B-roll indispensável ou troca de câmera. Isso vale especialmente para `Db_OfZDjKMW`, `Db_R92njTCq`, `Db_VUXqjnyO`, `Db_Y07LFV7J` e `Db_aVwFEkfD`.

O reframe 9:16 só deve ocorrer quando uma única face é identificada com segurança, existe cobertura temporal suficiente, não há saltos ou trocas de pessoa e a área de crop não remove headline, microfone, gesto ou GC. O resultado deve registrar `framing_mode`, confiança, cobertura e motivo. Se o gate falhar, a saída correta é `original_aspect`, não crop centralizado genérico.

### Regras imediatas para o produto

1. **Analisar antes de cortar.** Concluir ingestão, transcrição ou importação de timestamps, segmentação semântica e diagnóstico editorial antes do render.
2. **Gemini Online primeiro.** Com internet e API key, a análise online é prioritária. Whisper CPU é fallback explícito, com log da tentativa e do motivo da queda.
3. **Entrevista é unidade editorial.** Detectar pergunta, resposta, troca de locutor e encerramento; não selecionar frase forte dependente de pergunta omitida.
4. **Preservar a nata, não preencher quota.** Aplicar score, deduplicação semântica e diversidade antes da fila diária.
5. **Tratar texto como contexto visual.** OCR detecta headline, tweet, GC e legenda para evitar sobreposição; headline não substitui transcrição.
6. **Usar áudio para ritmo, não para provar viralidade.** Picos de amplitude sugerem ênfase, mas não substituem tese, contexto e conclusão.
7. **Separar fato de hipótese.** Os relatórios devem distinguir observação do vídeo, legenda pública e recomendação editorial.
8. **Registrar explicabilidade.** Cada candidato deve guardar score por componente, intervalos, locutor provável, evidência textual, modo de enquadramento e penalidades.

### Limitações e próximos testes

A tentativa de análise multimodal estruturada dos quatro Reels restantes foi bloqueada pelo proxy por saldo de créditos insuficiente; o serviço de speech-to-text também retornou erro 402. O quinto Reel sem relatório completo foi catalogado visualmente e por legenda pública. Nenhuma frase ou música foi inventada para preencher essa lacuna. Os achados visuais estão preservados em [`docs/remaining-visual-findings.md`](./remaining-visual-findings.md).

Os próximos testes devem confirmar: chamada Gemini antes da inicialização do Whisper; seleção de uma entrevista como intervalo autossuficiente; preservação do aspecto em layouts com múltiplas faces e GC; e diversidade de qualidade quando oito lives longas são processadas sem transformar 39–50 cortes em quota artificial por vídeo.

### Referências audiovisuais públicas

[7]: https://www.instagram.com/reel/Db_aVwFEkfD/ "Reel Db_aVwFEkfD"
[8]: https://www.instagram.com/reel/Db_Y07LFV7J/ "Reel Db_Y07LFV7J"
[9]: https://www.instagram.com/reel/Db_VUXqjnyO/ "Reel Db_VUXqjnyO"
[10]: https://www.instagram.com/reel/Db_R92njTCq/ "Reel Db_R92njTCq"
[11]: https://www.instagram.com/reel/Db_OfZDjKMW/ "Reel Db_OfZDjKMW"
[12]: https://www.instagram.com/reel/Db_LANvAgY6/ "Reel Db_LANvAgY6"
[13]: https://www.instagram.com/reel/Db_HmR1iOy1/ "Reel Db_HmR1iOy1"
[14]: https://www.instagram.com/reel/Db_F8qvE_Z_/ "Reel Db_F8qvE_Z_"
[15]: https://www.instagram.com/reel/Db_ENAyjO3R/ "Reel Db_ENAyjO3R"
[16]: https://www.instagram.com/reel/Db_Ax9tmcFu/ "Reel Db_Ax9tmcFu"
[17]: https://www.instagram.com/reel/Db-9SUJG2F8/ "Reel Db-9SUJG2F8"
[18]: https://www.instagram.com/reel/Db-2Y0OFNtr/ "Reel Db-2Y0OFNtr"
