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
