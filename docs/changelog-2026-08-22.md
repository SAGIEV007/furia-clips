# Furia Clips — mudanças da rodada de 22 de agosto de 2026

Esta rodada consolidou uma evolução de robustez editorial e de experiência de revisão. O objetivo foi reduzir falsos positivos causados por dados legados, impedir que o contexto de um vídeo seja aplicado a outro e preservar evidências suficientes para que o editor possa conferir cada decisão.

## Contexto e seleção editorial

O seletor agora normaliza flags textuais e numéricas provenientes de dados antigos em perguntas e respostas, payoff, tópico, timing, sobreposição e locutor. Valores temporais, de confiança e de energia que não sejam finitos são descartados antes de influenciar a seleção, evitando que `NaN` ou infinito contaminem scores, gates ou limites de corte.

A recuperação de contexto ficou mais conservadora. Uma transcrição persistida só é reutilizada quando o caminho canônico da fonte ou a assinatura leve da mídia coincide com o vídeo atual. Dossiês pré-analisados também precisam corresponder ao caminho e à assinatura da fonte antes de influenciar o ranking. Isso protege o fluxo contra a combinação acidental de um vídeo com a transcrição de outro.

O ranking continua explicável e não teve pesos recalibrados artificialmente. Priors históricos, feedbacks e sinais do Campaign Hub permanecem limitados, separados por conta e tratados como evidência auxiliar; eles não são promessa de viralização nem substituem a revisão humana.

## Transcrições e evidências persistentes

A análise integral de contexto agora arquiva a transcrição timestampada usada no dossiê, além de expor no resultado a qualidade estrutural e o diretório relativo do arquivo persistente. O endpoint legado do botão de transcrição recebeu a mesma proteção: mede a duração da fonte, calcula cobertura, reutiliza uma transcrição manual sem iniciar Whisper, arquiva resultados manuais e automáticos e devolve qualidade e proveniência no evento de conclusão.

Com isso, o editor pode revisar posteriormente a transcrição completa e o trecho associado ao clip, mesmo que a sessão do navegador seja reconectada ou que o checkout do código seja substituído. Mídias, bancos, transcrições completas, feedbacks detalhados, snapshots e chaves continuam fora do repositório.

## Jobs, cancelamento e interface

O refinamento opcional agora encerra corretamente o vínculo com o job em sucesso, falha e cancelamento. Eventos WebSocket atrasados ou repetidos não conseguem mais reaplicar um dossiê depois que a análise terminou. A troca de vídeo continua invalidando tokens, fonte, contexto e resultados anteriores.

A interface também mantém a distinção entre contexto pronto, contexto incompatível, erro e cancelamento, sem transformar uma operação antiga em resultado do vídeo atualmente selecionado. O objetivo é tornar a revisão visualmente compreensível sem esconder as limitações estruturais da transcrição, da diarização, do áudio ou da identidade da fonte.

## Validação

A rodada adicionou regressões para persistência de transcrição, identidade de fonte, limpeza do job de contexto, descarte de eventos tardios e precedência da transcrição manual. A validação final executou `node --check`, compilação Python, a suíte integral, `git diff --check` e a varredura de padrões de credenciais.

> Resultado final: **604 testes aprovados em 5,73 segundos**.

Nenhuma chave de API, banco de dados, vídeo privado, transcrição privada ou URL assinada faz parte desta documentação. A publicação contém somente código, testes e documentação sanitizada.

## Próximos pontos de validação pelo editor

Depois de atualizar o checkout, o teste mais útil é selecionar um vídeo, confirmar uma transcrição manual, executar somente a análise integral de contexto e verificar se o dossiê é exibido e se o arquivo aparece no painel de arquivo de transcrições. Em seguida, trocar para outro vídeo e repetir a análise; o dossiê anterior não deve ser reutilizado. O segundo teste é iniciar a transcrição, solicitar parada e confirmar que a HUD informa o encerramento seguro sem deixar o job preso.

O feedback real de aprovação, rejeição, ajuste de entrada/saída e motivo editorial continuará sendo a melhor evidência para futuras calibrações. A amostra histórica existente é pequena e desbalanceada, portanto nenhum peso do ranking será alterado apenas por ela.

Veja também o [roadmap de evolução](roadmap.md) e o [plano de métricas long-form](long-to-short-metrics-and-plan-2026-08-21.md).

---

**Estado de publicação desta rodada:** código e testes preparados para o repositório selecionado; dados persistentes e credenciais mantidos fora do Git.


## Correção incremental após a publicação

Foi corrigida uma condição de corrida no download por URL. Em uma conclusão muito rápida, o evento terminal podia chegar ao navegador antes da resposta HTTP que informava o job. O frontend agora reconhece esse job já concluído, não reativa a HUD, não exibe uma operação falsa como em andamento e preserva o resultado que já foi aplicado. Respostas de inicialização sem identificador de job também são rejeitadas de forma explícita.

A regressão cobre conclusão, cancelamento e erro recebidos antes da resposta de inicialização. A validação desta correção confirmou **605 testes aprovados** e nenhuma credencial no diff.


## Proveniência visual da transcrição

A aba de transcrição agora usa a mesma identidade normalizada do pipeline para comparar a fonte vinculada com o vídeo selecionado. Caminhos relativos e absolutos equivalentes deixam de aparecer como incompatíveis por engano, enquanto fontes realmente diferentes continuam sinalizadas para revisão. A correção não relaxa a validação do backend nem autoriza reutilização entre mídias diferentes.

A validação integral desta rodada confirmou **606 testes aprovados**.


## Proveniência no arquivo persistente

O painel que lista transcrições arquivadas também passou a reconhecer caminhos relativos e absolutos equivalentes como a fonte atual. O fallback por nome-base continua deliberadamente marcado como “confirmar arquivo”, pois nomes iguais não provam identidade de mídia.

A validação integral desta rodada confirmou **607 testes aprovados**.


## Cobertura comportamental da transcrição manual

Foi adicionado um teste de integração da API legada de transcrição. O cenário simula uma fonte real, envia uma transcrição manual, confirma que o fallback Whisper não é necessário, verifica o salvamento no projeto e valida que o evento de conclusão devolve cobertura, qualidade e referência ao arquivo persistente.

A validação integral desta rodada confirmou **608 testes aprovados**.


## Linguagem de qualidade na aba de transcrição

O status da transcrição deixou de usar uma única etiqueta ambígua de “qualidade”. Agora informa separadamente a **estrutura timestampada** — intervalos válidos, cobertura e avisos — e a **validação semântica**, que permanece não confirmada até revisão adequada. Assim, um arquivo tecnicamente bem timestampado não é apresentado como semanticamente conferido.

A validação integral desta rodada confirmou **609 testes aprovados**.


## Revisão de contexto por clip

A revisão de contexto agora só usa a transcrição global quando ela está vinculada, por caminho normalizado, ao vídeo selecionado. Se a transcrição global pertence a outra fonte ou está aguardando vínculo, o painel usa os segmentos persistidos no próprio clip; quando eles não existem, informa que a transcrição não está disponível. Isso evita exibir a fala de outro vídeo como se fosse o contexto do corte atual.

A validação integral desta rodada confirmou **610 testes aprovados**.


## Refinamento integral com vínculo de fonte

O botão de análise integral agora envia a transcrição manual somente quando ela está vinculada ao vídeo atualmente selecionado. Se houver um transcript carregado de outra fonte, ele é descartado para essa análise e o console informa o motivo; texto ainda digitado, mas não aplicado, continua disponível para o editor enviar conscientemente.

A validação integral desta rodada confirmou **611 testes aprovados**.


## Reidratação ao selecionar a fonte correta

Quando uma transcrição terminava em segundo plano enquanto outro vídeo estava selecionado, ela permanecia guardada com sua identidade. Ao selecionar posteriormente a fonte correspondente, a interface agora reidrata o editor com a transcrição e o arquivo persistente corretos. Para outra fonte, a limpeza continua acontecendo normalmente.

A validação integral desta rodada confirmou **612 testes aprovados**.


## Eventos órfãos do importador

O frontend agora descarta eventos de importação quando não existe job de fonte ativo ou aguardando resposta. Isso evita que um evento atrasado de um download antigo substitua silenciosamente a seleção atual ou reabra a HUD. A corrida legítima continua coberta: enquanto o importador está ativo, o evento pode chegar antes da resposta HTTP e o resultado é preservado.

A validação integral desta rodada confirmou **613 testes aprovados**.


## Botão de pasta de downloads

Foi corrigido um erro funcional no botão “Abrir pasta de downloads”: ele estava enviando a pasta de saída dos clips (`outputDir`) ao sistema operacional. Agora abre a pasta configurada para salvar fontes baixadas (`sourceDownloadDir`) e, quando ela ainda não existe, solicita a escolha dessa pasta antes de abrir. A pasta de exports não é mais apresentada como se fosse a pasta de downloads.

A validação integral desta rodada confirmou **614 testes aprovados**.


## Vínculo do dossiê no corte

O corte inteligente e o processo completo agora reutilizam um dossiê editorial pré-analisado usando a mesma identidade normalizada de mídia do restante da aplicação. Isso evita perder um dossiê válido por diferenças de representação de caminho, sem permitir que um dossiê de outra fonte seja aplicado; a verificação correspondente continua existindo no backend.

A validação integral desta rodada confirmou **614 testes aprovados**.


## Orientação quando não há dossiê pré-analisado

Ao iniciar um corte sem contexto editorial vinculado, o console agora deixa explícito que o processamento seguirá com os sinais disponíveis e informa a ação recomendada: executar “Revisar contexto” antes do corte para orientar perguntas–respostas, capítulos e payoff. O aviso não bloqueia o editor nem transforma a análise opcional em requisito obrigatório.

A validação integral desta rodada confirmou **615 testes aprovados**.


## Status coerente do scorecard

Foi corrigida uma inconsistência de revisão: um clip podia ter `technical_gate` em estado `review` ou `weak`, com motivos de risco de contexto/payoff, mas ainda aparecer no scorecard como `candidate`. Agora qualquer gate técnico não limpo aparece como `review_required`, mantendo o ranking e seus pesos inalterados e tornando a decisão humana mais clara.

A validação integral desta rodada confirmou **616 testes aprovados**.


## Scorecard legado coerente

A interface agora interpreta também scorecards antigos com `status` ou `gate_status` em `review`, `weak`, `review_required` ou `blocked` como “revisão necessária”. Assim, resultados já existentes não voltam a aparecer como simples candidatos quando seus próprios gates registram risco de contexto, payoff, locutor ou técnica.

A validação integral desta rodada confirmou **617 testes aprovados**.


## Diagnóstico de candidatos bloqueados

O aviso de volume agora reconhece `editorial_gate_blocked` e explica que nenhum candidato foi liberado porque todos exigem revisão editorial ou técnica antes do render. Isso diferencia ausência de material autossuficiente, redundância, falha de render e bloqueio deliberado por qualidade.

A validação integral desta rodada confirmou **618 testes aprovados**.


## Contagem de candidatos adiados

O aviso de volume não afirma mais que candidatos foram liberados para render quando todos foram adiados por contexto incompleto ou revisão técnica. A interface agora mostra “Nenhum candidato foi liberado para render” quando a contagem renderizável é zero, mantendo a quantidade adiada e a explicação dos motivos.

A validação integral desta rodada confirmou **619 testes aprovados**.


## Diagnóstico de renderização parcial

Falhas de FFmpeg e intervalos inválidos agora entram no relatório estruturado de rejeições do VideoCutter. Isso permite que o job diferencie seleção insuficiente de falha técnica, preserve os clips válidos de uma execução parcial e mostre a causa na revisão, sem deixar erros silenciosos quando um arquivo não é gerado ou não passa pela validação de mídia.

A validação integral desta rodada confirmou **621 testes aprovados**.


## Fallback seguro do face tracking

O face tracking opcional agora trata falhas de `ffprobe` ou ausência de stream de vídeo como indisponibilidade localizada: o clip cai para o corte convencional com o preset selecionado, em vez de abortar a operação inteira. A interface recebe um aviso explícito, e o processamento dos demais clips continua.

A validação integral desta rodada confirmou **622 testes aprovados**.


## Preferência por áudio em português

O download de fontes públicas agora tenta primeiro a melhor faixa de áudio marcada como português (`pt`/`pt-BR`) quando o provedor expõe metadados de idioma. Se não houver essa informação, o Furia mantém o fallback para a melhor faixa pública disponível e não inventa uma tradução. Isso reduz o risco de selecionar uma dublagem espanhola em vídeos que oferecem múltiplas faixas.

No benchmark individual do vídeo informado (`KdzrMY_QPiE`), a análise audiovisual confirmou **português do Brasil**, identificou Renan, Edson e Amanda e encontrou ações não verbais relevantes, como berrante, montaria, travessia, fauna e demonstrações culturais. O relatório completo foi salvo somente em `/home/ubuntu/FuriaClipsData/analyses/benchmark-KdzrMY_QPiE-2026-08-22.md`; não foi incluído no Git porque contém análise de mídia e dados de trabalho.

A validação integral desta rodada confirmou **623 testes aprovados**.

## Evidência não verbal revisável e face tracking resiliente
A análise multimodal agora solicita momentos não verbais timestampados — como risadas, reações, gestos, objetos, animais, montaria, cavalgada, berrante, música, paisagem e silêncio expressivo — sempre com descrição, valor editorial, confiança e `requires_visual_review`. O backend aceita somente intervalos finitos e positivos, categorias permitidas e descrições curtas; descarta observações quando a fonte multimodal é incompatível, limita a confiança quando a identidade não foi validada e anexa no máximo o melhor evento sobreposto a cada clip como evidência auxiliar. A interface mostra o timestamp, a categoria, a confiança e o aviso para confirmar imagem e áudio. O momento não cria corte independente, não altera automaticamente a pontuação e não remove gates de contexto.

O reenquadramento facial opcional agora filtra sinais não finitos, strings inválidas e confianças não positivas, limita coordenadas a `[0,1]` e usa o centro do quadro quando nenhum ponto confiável sobra, mantendo o fallback convencional e um aviso explicável. Não há persistência biométrica nem identificação pública de pessoas.

A validação integral desta rodada confirmou **628 testes aprovados**, além de `node --check`, `py_compile`, `git diff --check` e varredura de segredos sem achados.

## Correção prática: evidência multimodal no corte inteligente
Durante a validação do fluxo publicado foi identificado que o processo completo anexava os momentos não verbais, mas o caminho “Corte inteligente” ainda não os propagava antes do ranking e do payload final. O caminho inteligente agora usa o mesmo anexador seguro; os campos chegam aos dois tipos de resultado e continuam explicitamente fora do cálculo de score e dos gates automáticos. A ausência de mídia local de teste impediu um render audiovisual real nesta rodada, então a cobertura foi feita por testes sintéticos de contrato e pelo fluxo de payload.

Foram adicionados testes de seleção do melhor evento sobreposto, descarte por fonte incompatível, limite de confiança sem identidade validada e neutralidade do ranking. A validação integral desta rodada confirmou **632 testes aprovados**, além das checagens de sintaxe, compilação, whitespace e segredos.

## Diagnóstico transparente do snapshot offline do Campaign Hub
O Furia agora diferencia explicitamente quatro estados da memória editorial local: arquivo não encontrado, arquivo vazio ou sem observações utilizáveis, JSON/formato inválido e snapshot carregado. A interface e os logs mostram se há observações de hooks suficientes para auxiliar o ranking, além de explicar que esse prior é somente leitura, limitado e não cria cortes, não substitui a análise do vídeo e não promete viralidade.

O leitor também ficou mais defensivo contra listas corrompidas nos campos de observações, exemplos e cohorts. O endpoint `/api/campaign-hub/status` expõe apenas metadados bounded e o escopo de influência; não existe caminho de escrita ou sincronização automática com o Campaign Hub.

No ambiente de validação, o snapshot persistente local foi reconhecido como **carregado**, com 46 observações de hooks, 45 exemplos e 2 cohorts distribuídos entre dois perfis. Isso significa que ele pode auxiliar o desempate e a classificação de hooks quando houver amostra suficiente; os cortes continuam dependentes principalmente da transcrição, contexto, payoff, áudio, layout e gates editoriais.

A validação integral desta rodada confirmou **638 testes aprovados**, além de `node --check`, `py_compile`, `git diff --check` e varredura de segredos sem achados.

## Extensão read-only do Acervo e dos sinais contextuais do Campaign Hub
O adaptador offline passou a aceitar, além dos priors de hooks legados, snapshots ricos com blocos Acervo QA-gated, candidatos de pauta, highlights timestampados, regiões ignoradas, entidades e priors de audiência. Os campos são normalizados com limites de tamanho, timestamps finitos, categorias e conta explícita; formatos corrompidos são ignorados com segurança.

Blocos Acervo só são alinhados a um candidato quando o identificador da mesma fonte e o intervalo temporal coincidem. Similaridade textual de outra fonte não é tratada como alinhamento. Quando há coincidência, o Furia mostra título, categoria, confiança, highlights e razão como evidência revisável; o sinal é bounded, não cria cortes, não substitui contexto ou payoff e não remove gates. Priors de audiência só são considerados quando um segmento é solicitado explicitamente e existe amostra suficiente, permanecendo auxiliares e não causais.

A busca editorial local também consulta blocos e pautas presentes em `~/FuriaClipsData/campaign_hub/profile.json`, com timestamps, previews canônicos do YouTube e indicação de leitura somente local. A interface global do snapshot agora exibe contagens de hooks, blocos, pautas e audiência, enquanto os logs dos fluxos inteligente e completo registram a mesma cobertura.

Foram adicionados testes de normalização, alinhamento same-source, rejeição de fonte diferente, snapshot rico sem hooks, audiência com segmento explícito, ranking subordinado aos gates, endpoint de status e busca de bloco Acervo. A validação integral desta rodada confirmou **644 testes aprovados**, além de `node --check`, `py_compile`, `git diff --check` e varredura de segredos sem achados.

## Sinais locais de áudio, movimento e força editorial do perfil Renan
A análise local de áudio agora preserva o RMS existente e acrescenta, em streaming, zero-crossing rate, onset strength, crest factor e um sinal acústico possível de reação. Esses valores não são apresentados como detecção certa de risada, música ou plateia: permanecem com baixa confiança e revisão obrigatória quando a textura acústica é ambígua. O resumo por janela alimenta os hooks e o ranking apenas como desempate bounded.

O ranker passou a expor `audio_context`, `favorability` e `favorability_score`. A favorabilidade representa força estrutural do trecho para o perfil editorial configurado — tese, evidência, consequência, conclusão e resposta — e não reconhecimento biométrico nem afirmação de que Renan está falando. Quando o locutor não foi confirmado, o resultado exibe base textual e pode exigir revisão explícita; o sinal não supera gates de contexto, payoff, locutor ou técnica.

O face tracking opcional também calcula movimento efêmero por segmento a partir de posições normalizadas, descartando pontos inválidos e múltiplas faces. O índice é mostrado como evidência de movimento visual e não identifica pessoas, não cria memória facial e exige confirmação da ação no vídeo. Menções Acervo sem `renanSpeaking` confirmado permanecem em revisão e não recebem prior positivo.

A interface passou a mostrar áudio contextual, movimento e força editorial do perfil nos cards, com linguagem que diferencia sinal auxiliar de fato confirmado. A validação integral desta rodada confirmou **651 testes aprovados**, além de `node --check`, `py_compile`, `git diff --check` e varredura de segredos sem achados.

## Camada 2 — seeds temporais, coice pergunta–resposta e priorização editorial revisável
O fluxo de Corte Inteligente e Processo Completo agora carrega blocos Acervo e pauta do snapshot local somente quando existe **mesma fonte identificada e intervalo temporal válido**. Esses blocos entram como `context_seed_only`, com resumo editorial limitado, `transcription_review_required` e gate técnico obrigatório. Não são renderizados automaticamente, não são aprovados pelo ranking e não atravessam a revisão de contexto sem confirmação da transcrição, do locutor e do payoff. Entradas inválidas, blocos não-objeto, timestamps invertidos e limites de seed malformados são ignorados com segurança.

O ranker passou a reconhecer uma hipótese de **coice** somente quando há pergunta ou setup explícito e uma ponte de resposta suficiente. Perguntas potencialmente hostis, tese, evidência, conclusão e confirmação do locutor são exibidas separadamente, com confiança e motivo. A hipótese é bounded e revisável; a palavra “resposta” isolada não cria coice e não substitui a confirmação audiovisual. Também foi removido um cálculo redundante de favorabilidade feito antes dos sinais políticos.

O portfólio diário ganhou `favorability_mode=off|prioritize|require`. O padrão permanece neutro e genérico. `prioritize` usa a favorabilidade somente como desempate de até dois pontos e marca candidatos ambíguos como `needs_review`; `require` é um gate estrito opt-in e rejeita somente quando solicitado explicitamente. O resumo da API expõe a política, o limiar e a contagem de candidatos revisáveis.

Foi criado `modules/approved_clip_priors.py`, que transforma decisões locais aprovadas/rejeitadas em agregados de duração, formato, família de hook, forma da headline e diferenças de fatores. O SQLite agora oferece `get_approved_clip_feature_prior()` sem retornar transcrição, caminho de mídia ou headline bruta. A amostra é elegível apenas com volume mínimo e grupo rejeitado para comparação; qualquer influência continua bounded e não é fine-tuning. O Headline Studio 2.0 usa esse prior apenas para recomendar o formato quando a amostra é suficiente e registra o escopo da influência, mantendo o texto gerado ancorado na transcrição atual.

Foi criado `modules/learning_importer.py` e os endpoints locais `/api/editorial/learning` e `/api/editorial/learning/import`. O importador aceita CSV, JSON ou JSONL real fornecido pelo editor, registra hash e manifest em `~/FuriaClipsData/learning` e grava somente features sanitizadas. Não há dataset artificial, chamada ao Campaign Hub, upload ao GitHub, persistência de mídia ou transcript bruto. O programa ainda **não possui os cerca de 3.000 cortes reais**: para ativar esse prior é necessário importar uma exportação verdadeira.

A validação integral desta rodada confirmou **663 testes aprovados**, além de `node --check`, `py_compile`, `git diff --check` e varredura de segredos sem achados.

## Camada 3 — calibração, import real e protocolo A/B
A Camada 2 foi preservada. O importador local agora aceita CSV, JSON, JSONL, itens JSON inline e multipart, com validação estrita opcional de `clip_id`, `label` e `duration_sec`, erros por linha, deduplicação last-write e saída somente com features agregáveis. Transcript, headline bruta, URL, path, token, cookie e mídia são descartados; o learning store permanece fora do Git.

Os priors aggregate-only foram ampliados com duração p25/mediana/p75, famílias, formatos, padrões de abertura, ponte QA, motivos de rejeição, tópicos bounded, forma estatística de headline e deltas de fatores. O GET de learning devolve whitelist de agregados e o POST de import informa `accepted`, `rejected_rows`, `errors`, tamanhos de amostra e `priors_updated`.

Foi adicionado o exportador A/B local em JSON/CSV. `/api/batch/rank` gera ou recebe `run_id` e registra `favorability_mode`, `ai_backend`, `seeds_enabled` e candidatos sanitizados. Também existem endpoints explícitos de exportação e leitura por run. O modo inválido cai para `off`; o default de produção não foi alterado. Seeds Acervo continuam revisáveis e nunca renderizam automaticamente.

Foram adicionados templates operacionais e documentação para o editor. A correção de cobertura em `test_daily_portfolio.py` recolocou os testes de `prioritize` e `require` na coleta normal. A validação integral desta rodada confirmou **673 testes aprovados**, `node --check`, `py_compile`, `git diff --check` e auditoria de segredos sem achados reais. Campaign Hub permaneceu somente leitura e nenhum dataset artificial foi criado.


## Camada UI — redesign da bancada editorial

- Integrados os tokens dark-first do Design System em `static/css/furia-tokens.css`, com superfícies neutras, âmbar de ação, estados semânticos e foco acessível.
- Reformulado o shell com navegação lateral Bancada/Ferramentas, toggle de sidebar, workflow visual, KPI strip sticky e adaptação para viewport estreito.
- Reorganizada a revisão de clips em player persistente + fila, preservando `resultsGrid`, filtros, busca, ações de aprovação/rejeição e revisão de contexto.
- Adicionados estado de foco do clip, score drawer “Por que este score?”, resumo de fatores, sinais de favorabilidade/coice/seed e empty state acionável.
- Implementados atalhos `J/K/A/R/E/H/?`, `Ctrl/Cmd+K` para command palette, alternância de densidade e foco visível. Sons permanecem desligados por padrão e `prefers-reduced-motion` é respeitado.
- Mantidos os contratos do backend, IDs legados e a regra de que Campaign Hub é somente leitura. Nenhuma mídia, transcrição, snapshot privado, feedback bruto ou credencial foi incluída.
- Validação desta rodada: `node --check`, `py_compile`, `git diff --check` e **673 testes aprovados**.

## Passe Professional UI/UX — bancada orientada à decisão

A interface recebeu um segundo passe estrutural orientado à rotina do editor. O shell agora muda de estado entre `empty`, `source`, `analysis` e `review`, atualiza o título e o status da bancada conforme a tarefa e oculta a faixa de KPIs quando ainda não existe fonte ativa. Depois que uma fonte é selecionada, a drop zone deixa de ocupar a superfície principal; quando há candidatos, a revisão recebe prioridade visual.

As ações foram contidas em uma rail compacta com um único acento dominante, os gradientes multicoloridos dos ícones foram removidos e as ações primárias passaram a ser promovidas por etapa. O estado visual combina texto, ícone, borda e cor, preservando a distinção entre aprovado, rejeitado e revisão necessária. O passe mantém os IDs, rotas, contratos de API, ranking e integrações existentes.

A auditoria heurística persistente registrou média observada de 3,1/5 antes deste passe e definiu os critérios de QA: localizar a ação primária em até dois segundos, identificar a fonte ativa, encontrar score/timecode na fila e operar por teclado. A validação desta rodada confirmou **673 testes aprovados**, `node --check`, `py_compile`, `git diff --check` e auditoria de segredos. Nenhum dado privado ou conteúdo do Campaign Hub foi incluído.

## Qualidade — refinamento temporal por timestamps de palavras

O selector passou a preservar spans numéricos de palavras quando a fonte de transcrição os fornece e a ancorar os limites do clip na primeira e na última palavra detectadas. A poda é conservadora: mantém margem de 120 ms, limita a remoção a 0,8 s por lado, preserva o intervalo original quando não há spans válidos e nunca reduz o trecho abaixo da duração mínima segura. O metadata `boundary_refinement` explica se a poda foi aplicada e quanto foi removido.

A mesma regra foi aplicada aos caminhos NLP, Gemini e Ollama. O texto bruto das palavras não é armazenado nesse metadata; somente posições numéricas bounded são propagadas. Foram adicionados testes para poda aplicada, ausência de timestamps seguros, sanitização numérica e compatibilidade do parser de IA.

Validação: **676 testes aprovados**, `node --check`, `py_compile`, `git diff --check` e auditoria de segredos sem achados. Campaign Hub permaneceu somente leitura.

## Qualidade — preservação dos limites refinados no render final

O `batch_cut` deixou de reaplicar automaticamente o padding legado de 300 ms antes e 800 ms depois quando o candidato já traz `boundary_refinement.applied=true`. Assim, o intervalo ancorado nas palavras chega ao FFmpeg sem ser parcialmente desfeito. Candidatos antigos sem esse metadata continuam usando o padding de segurança anterior para preservar compatibilidade.

O resultado de render agora informa `render_start`, `render_end`, `render_boundary_policy` e o refinamento aplicado, permitindo auditar a diferença entre o intervalo editorial canônico e o intervalo efetivamente enviado ao renderizador. Foram adicionados testes de integração para os caminhos refinado e legado.

Validação: **678 testes aprovados**, `node --check`, `py_compile`, `git diff --check` e auditoria de segredos sem achados. Campaign Hub permaneceu somente leitura.

## Revisão — transparência dos limites efetivamente renderizados

O payload de revisão passou a transportar `boundary_refinement`, `render_start`, `render_end` e `render_boundary_policy`. A fila de clips exibe uma nota discreta quando a ancoragem por timestamps de palavras foi aplicada, com o intervalo renderizado, a poda segura em cada lado e a confirmação de que o padding adicional não foi reaplicado.

A mudança torna auditável a diferença entre o intervalo editorial escolhido e o intervalo enviado ao FFmpeg, sem exibir texto bruto de palavras nem sobrecarregar candidatos que não possuem refinamento. Foi adicionada cobertura de contrato no frontend.

Validação: **679 testes aprovados**, `node --check`, `py_compile`, `git diff --check` e auditoria de segredos sem achados. Campaign Hub permaneceu somente leitura.

## Qualidade — snapping de cena somente para fora do discurso

O ajuste opcional por mudanças de cena deixou de mover limites para dentro do trecho falado. O início só pode recuar até uma transição anterior próxima e o fim só pode avançar até uma transição posterior próxima; timestamps inválidos, negativos ou não finitos são ignorados. O intervalo original é mantido quando o ajuste seria inválido, e cada clip recebe `scene_boundary_adjustment` com a direção e os limites antes/depois.

A mudança preserva o conteúdo semântico já selecionado e reduz o risco de cortar a primeira ou a última palavra apenas porque uma transição visual foi detectada. Foram adicionados testes para expansão externa, não redução e entradas inválidas.

Validação: **682 testes aprovados**, `node --check`, `py_compile`, `git diff --check` e auditoria de segredos sem achados. Campaign Hub permaneceu somente leitura.

## Precisão editorial — ajuste manual orientado por palavras

O ajuste manual de entrada e saída agora prefere `word.start` para o início e `word.end` para o fim quando a transcrição timestampada contém palavras válidas. Isso evita que um clique aproximado seja alinhado apenas ao limite amplo do segmento e reduz o risco de incluir ou remover fala desnecessária. Se não houver palavras válidas, o comportamento anterior por segmentos permanece como fallback; entradas inválidas continuam sendo ignoradas com segurança.

Foi adicionada cobertura de regressão para confirmar a preferência por palavras, a não mutação do clip canônico, a duração mínima e a rejeição de limites não finitos. Validação: **683 testes aprovados**, `node --check`, `py_compile`, `git diff --check` e auditoria de segredos sem achados. Campaign Hub permaneceu somente leitura.

## Cobertura de execução — deduplicação sensível ao contexto

A deduplicação entre execuções agora não descarta automaticamente um intervalo apenas porque ele se sobrepõe a um clip já exportado. Quando o novo candidato apresenta pelo menos duas diferenças editoriais coerentes — como conclusão, completude de pergunta–resposta, payoff, ponte de contexto, capítulo ou tipo editorial — ele pode permanecer na fila para revisão. Duplicatas exatas, limites praticamente iguais e repetições lexicalmente equivalentes continuam sendo removidos.

Isso preserva a possibilidade de uma segunda passada encontrar a conclusão de uma resposta ou um enquadramento editorial diferente dentro de uma janela já visitada, sem reabrir o risco de repetir o mesmo corte. Foram adicionados testes para sobreposição contextualmente distinta e para duplicata exata. Validação: **685 testes aprovados**, `node --check`, `py_compile`, `git diff --check` e auditoria de segredos sem achados. Campaign Hub permaneceu somente leitura.

## Persistência editorial — deduplicação do intervalo ajustado

Os fingerprints locais agora incluem, além do intervalo canônico salvo no clip, o último intervalo manual válido registrado pelo editor. Assim, uma nova execução evita repetir tanto a janela originalmente selecionada quanto a versão refinada que foi efetivamente revisada. A identidade da fonte, o filtro por assinatura e o fallback de registros legados permanecem inalterados; ajustes inválidos ou iguais ao intervalo canônico não geram fingerprint extra.

Foi adicionada regressão de integração para confirmar a recuperação dos dois intervalos a partir do SQLite. Validação: **686 testes aprovados**, `node --check`, `py_compile`, `git diff --check` e auditoria de segredos sem achados. Campaign Hub permaneceu somente leitura.

## Dedupe contextual — persistência dos sinais do ranker

O pipeline de corte agora grava no scorecard apenas os sinais não textuais necessários para deduplicação futura — completude de pergunta–resposta, payoff, ponte de contexto, tipo de fechamento, tipo editorial político e capítulo primário. Na execução seguinte, esses sinais são reconstruídos no fingerprint local e podem preservar um candidato sobreposto quando ele representa uma decisão editorial diferente. Nenhum texto novo, transcript, mídia ou dado do Campaign Hub é enviado ao repositório.

A cobertura de integração confirma o caminho SQLite → fingerprint → selector. Validação: **686 testes aprovados**, `node --check`, `py_compile`, `git diff --check` e auditoria de segredos sem achados. Campaign Hub permaneceu somente leitura.

## Segurança temporal — teto no snapping de cena

O snapping outward-only agora preserva o intervalo original quando a expansão até as transições próximas ultrapassaria `max_duration`. O Furia não encurta o discurso para caber no teto e também não cria um clip maior que o limite técnico configurado. O comportamento anterior de ignorar timestamps inválidos e manter o intervalo quando o ajuste é inseguro permanece ativo.

Foi adicionada regressão para expansão acima do teto. Validação: **687 testes aprovados**, `node --check`, `py_compile`, `git diff --check` e auditoria de segredos sem achados. Campaign Hub permaneceu somente leitura.

## Ajuste manual — fallback de proximidade por nível

O alinhamento de limites agora tenta primeiro a fronteira de palavra mais próxima quando ela está dentro da tolerância configurada. Se as palavras timestampadas estiverem longe, o Furia volta a considerar os limites do segmento; se nenhum nível estiver próximo, mantém o valor solicitado. Isso preserva a precisão fina sem transformar a existência de uma palavra distante em motivo para ignorar um segmento útil.

Foi adicionada regressão para o fallback palavra → segmento. Validação: **688 testes aprovados**, `node --check`, `py_compile`, `git diff --check` e auditoria de segredos sem achados. Campaign Hub permaneceu somente leitura.

## Revisão visual — transparência do snapping de cena

Os payloads de Corte inteligente e Processo completo agora carregam `scene_boundary_adjustment` até a bancada de revisão. Quando uma cena expandiu o intervalo, o card mostra discretamente os limites originais e ajustados e informa que a fala foi preservada. Clips sem expansão continuam sem aviso, evitando ruído na fila.

Foram adicionados contratos estáticos para o payload e a mensagem visível. Validação: **690 testes aprovados**, `node --check`, `py_compile`, `git diff --check` e auditoria de segredos sem achados. Campaign Hub permaneceu somente leitura.

## Dedupe contextual — leitura completa do scorecard

O contexto persistido usado na deduplicação agora recupera também sinais que o ranker mantém dentro de `review_flags`, especialmente `qa_bridge`. Isso evita que a distinção entre uma janela repetida e uma nova versão pergunta–resposta seja perdida ao reabrir o clip a partir do SQLite. A mudança continua limitada a flags editoriais pequenos e não textuais; não altera pesos, score, gates ou dados do Campaign Hub.

Foi adicionado contrato estático para o fallback aninhado. Validação: **691 testes aprovados**, `node --check`, `py_compile`, `git diff --check` e auditoria de segredos sem achados. Campaign Hub permaneceu somente leitura.

## Persistência de revisão — scene adjustment após reabertura

A metadata de snapping de cena agora percorre o scorecard editorial e é reidratada por `get_clips`. Assim, depois de recarregar um projeto, a bancada continua sabendo se o intervalo foi expandido, quais eram os limites original/ajustado e que a política foi outward-only. A normalização aceita somente números finitos, valores não negativos e a direção conhecida; campos extras são descartados.

Foi adicionada regressão de round-trip SQLite e os dois fluxos de corte passaram a fornecer a metadata ao persistir o score. Validação: **692 testes aprovados**, `node --check`, `py_compile`, `git diff --check` e auditoria de segredos sem achados. Campaign Hub permaneceu somente leitura.

## Transparência do render — scene adjustment no resultado final

O resultado de `VideoCutter.batch_cut` agora devolve também a metadata sanitizada de `scene_boundary_adjustment`, junto de `render_start`, `render_end` e da política de limites. Isso mantém o artefato de render autocontido para consumidores genéricos, revisão e diagnósticos: quem recebe somente o resultado consegue saber se a cena expandiu o intervalo para preservar a fala, sem depender do payload original do selector.

Foi adicionada regressão no contrato de render, preservando os caminhos legados de padding e as políticas de refinamento por palavras. Validação: **692 testes aprovados**, `node --check`, `py_compile`, `git diff --check` e auditoria de segredos sem achados. Campaign Hub permaneceu somente leitura.

## Contrato temporal — duração efetivamente renderizada

Os resultados de `VideoCutter.batch_cut` agora incluem `render_duration`, calculada a partir de `render_start` e `render_end` após padding legado, refinamento por palavras e limites da fonte. Isso evita que consumidores confundam a duração editorial do candidato com a duração real do arquivo gerado, especialmente em clips legados com padding ou próximos ao fim do vídeo.

A regressão cobre tanto o caminho refinado sem padding quanto o caminho legado com padding. Validação: **692 testes aprovados**, `node --check`, `py_compile`, `git diff --check` e auditoria de segredos sem achados. Não houve alteração de pesos de ranking nem escrita no Campaign Hub.

## Deduplicação Acervo — candidatos locais sem identidade explícita

A entrada de seeds Acervo same-source agora trata um candidato local sem `source_id` como pertencente à fonte atualmente analisada, porque o selector já trabalha dentro de uma única fonte por execução. Seeds não são bloqueados quando o candidato traz um identificador não vazio de outra fonte. Isso evita que o mesmo intervalo apareça duas vezes após o ranker, sem inferir identidade entre vídeos diferentes e mantendo a separação de contas.

Foi adicionada regressão para o formato real dos candidatos locais, que pode omitir a identidade explícita. Validação: **693 testes aprovados**, `node --check`, `py_compile`, `git diff --check` e auditoria de segredos sem achados. Campaign Hub permaneceu somente leitura.


## Bancada de ajuste com re-renderização individual — 2026-08-22

- **Problema confirmado:** a bancada permitia pré-visualizar e salvar novos limites, mas o botão apenas registrava o ajuste no histórico; o MP4 original continuava sendo o único arquivo reproduzido, obrigando o editor a baixar o vídeo inteiro para corrigir uma entrada ou saída.
- **Implementado:** `POST /api/clips/<clip_id>/adjust/render` valida os limites com a mesma política de timestamps e duração mínima, recupera a fonte original vinculada ao projeto, re-renderiza somente o clip ajustado com o preset escolhido e valida o arquivo produzido.
- **Persistência segura:** o arquivo derivado passa a ser o caminho reproduzido pelo clip, enquanto `clips.start_time`/`end_time` canônicos continuam preservados para histórico, deduplicação e auditoria. O ajuste mantém origem, limites renderizados, duração efetiva, política de boundary e estado `rendered`.
- **UX de bancada:** “Salvar ajuste” foi substituído por **“Renderizar ajuste”**; após sucesso, o card atualiza o player com cache-busting e informa que o MP4 foi corrigido, mantendo a necessidade de revisão antes da aprovação.
- **Regressão:** smoke test cobre re-render, atualização do arquivo persistido, preservação do intervalo canônico e retorno de `render_duration`.
- **Validação:** `node --check static/js/app.js`, `py_compile`, suíte integral com **695 testes aprovados**, `git diff --check` e auditoria de segredos sem ocorrência.
- **Limitação honesta:** a re-renderização exige que a fonte original ainda esteja disponível em uma raiz de mídia permitida; quando ela não existir, a API retorna diagnóstico e não altera o clip.


### Complemento do ciclo de re-renderização

A rota de ajuste agora também consegue descobrir a duração da fonte via `ffprobe` quando o navegador não a envia; foi corrigido o import necessário no `VideoCutter` e adicionada regressão para esse caminho. A validação integral foi repetida após essa correção, mantendo **695 testes aprovados**.


## Priorização de seeds Acervo por evidência editorial — 2026-08-22

Os seeds read-only do Acervo agora são ordenados de forma estável pelo maior `self_contained_rank` e, em seguida, pelo maior `density_rank` já disponível no snapshot. Isso evita que o limite de seeds consuma primeiro blocos menos completos apenas por ordem de chegada. Empates preservam a ordem original do snapshot. A mudança não altera os pesos do ranker principal, não mistura contas e continua subordinada à validação de mesma fonte e à revisão humana.

Foi adicionada regressão para confirmar que, com limite de um seed, o bloco mais autossuficiente é escolhido mesmo quando aparece depois de um bloco menos completo. A validação integral deste ciclo confirmou **695 testes aprovados** e nenhuma credencial no diff.
