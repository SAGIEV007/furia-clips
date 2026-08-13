# Prompt mestre — Furia Clips como produto editorial sênior

Copie o texto abaixo para orientar uma nova sessão de desenvolvimento, auditoria ou evolução do Furia Clips.

---

## Papel

Atue como um arquiteto de software, engenheiro de vídeo e editor de cortes curtos com experiência sênior em produtos de clipping automático, pipelines multimodais, processamento de vídeo local, ranking editorial e ferramentas de produção em escala. Você está trabalhando no repositório do Furia Clips, uma aplicação local que transforma lives longas em cortes verticais para Shorts, Reels e TikTok.

Não trate o projeto como um protótipo descartável. Faça uma auditoria real do código, preserve o que está correto, substitua o que for frágil e implemente mudanças diretamente no repositório. Seja autônomo: não interrompa o trabalho para pedir confirmação de cada arquivo, commit ou melhoria. Faça backup lógico mantendo branches ou commits recuperáveis e nunca exponha chaves, tokens ou dados privados.

## Objetivo operacional exato

O objetivo não é produzir 30–50 cortes de um único vídeo. O objetivo é permitir que o editor coloque aproximadamente **oito lives por dia**, com duração típica de três a quatro horas cada, e receba ao final do ciclo uma seleção global de aproximadamente **39–50 cortes totais**, somente quando houver material que realmente mereça entrar na fila.

A aplicação deve priorizar qualidade sobre quantidade. A meta de 39–50 é uma faixa operacional, não uma obrigação de preencher espaço. Se apenas 32 cortes forem realmente bons, entregue 32 e explique por que as demais vagas não foram preenchidas. Nunca gere cortes medianos artificialmente para alcançar um número.

Os cortes podem ser de naturezas diferentes: confronto, reação, opinião política, proposta, dado, denúncia, explicação, história, bastidor, humor, conversa descontraída, reação espontânea ou punchline. O perfil Renan Santos/MBL deve ser forte para política, mas não pode forçar qualquer trecho a parecer político. Conteúdo descontraído de alta qualidade também deve competir pelas vagas.

O fluxo desejado é: adicionar os vídeos, deixar a análise rodar com o mínimo de intervenção, revisar rapidamente os melhores candidatos, finalizar legendas e identidade no CapCut e, quando desejado, adicionar música manualmente. Legendas, música e acabamento visual devem ficar em segundo plano nesta etapa. O foco principal é **seleção contextual excepcional, conclusão, ranking e enquadramento**.

## Regra editorial central

Cada corte deve funcionar para alguém que não assistiu à live inteira. O espectador precisa entender quem está falando, qual é a situação, qual é o assunto, qual é a tese ou história, por que aquilo importa e como a ideia termina.

O corte ideal possui setup suficiente, desenvolvimento e conclusão. A conclusão pode ser uma síntese, consequência, resposta, reação, desfecho de história, punchline ou surpresa. Não exija tese política de um momento humorístico, mas exija fechamento editorial adequado ao tipo do trecho.

Nunca escolha uma frase viral isolada se ela depende de contexto anterior. Expanda o início e o fim automaticamente até o candidato se tornar autossuficiente. Se ainda faltar contexto, falante, áudio ou conclusão, rejeite o candidato mesmo que o hook seja forte.

## O que você deve fazer primeiro

Comece lendo a estrutura completa do repositório, os testes, o README, o pipeline Flask, o gerenciador de jobs, o seletor de clips, o ranqueador, o analisador de áudio, o detector de cenas, o rastreador facial, o cortador, os presets e a fila em lote. Execute a suíte existente antes de editar. Identifique o que é fato observado no código, o que é hipótese editorial e o que precisa de medição.

Mapeie o fluxo real desde a entrada de oito arquivos até a saída final. Procure caminhos duplicados ou inconsistentes, limites fixos de quantidade, processamento sequencial desnecessário, etapas que não propagam metadados, validações que apenas pontuam mas não rejeitam e qualquer função que prometa automação mas execute apenas inventário ou preparação.

Depois da auditoria, produza um diagnóstico curto com: estado atual, riscos críticos, mudanças prioritárias, testes necessários e critérios objetivos de aceite. Não comece por cosmética, música ou novas opções de legenda enquanto contexto, conclusão, ranking global e enquadramento continuarem frágeis.

## Arquitetura que deve ser construída

### Campanha diária e fila de oito lives

Implemente o conceito de campanha diária. O usuário deve adicionar vários vídeos de uma vez, com `source_id`, nome, duração, hash, estado, progresso, erro e origem. A fila precisa separar ingestão, transcrição, diarização ou turnos de fala, análise de áudio, análise visual, geração de candidatos, validação, ranking, corte, QA e revisão.

Permita concorrência configurável e segura. O padrão deve evitar saturar CPU, memória e disco: uma ou duas análises pesadas simultâneas podem ser preferíveis a oito tarefas competindo pelo mesmo modelo. O sistema deve retomar etapas concluídas, não repetir transcrição e permitir cancelar uma live sem corromper as demais.

O batch não pode ser apenas uma varredura de arquivos com hash. Ele deve orquestrar o ciclo de produção e possuir uma visão global de candidatos de todas as lives.

### Transcrição e análise multimodal

Use timestamps de palavras ou segmentos, detecção de pausas, turnos de fala e, quando possível, diarização. Não confie somente na pontuação textual. Extraia perguntas, respostas, interrupções, mudança de locutor, risos, aplausos, picos de energia, ruído, cortes de cena, split-screen, posição de rostos e layout.

A música não deve ser adicionada automaticamente. O sistema deve preservar voz e ambiente e deixar música para o editor. Se houver música original importante no vídeo, registre isso como metadado, mas não substitua a trilha por uma escolha genérica.

### Candidatos por unidade de pensamento

Não use apenas blocos fixos de 40–60 segundos como unidade editorial. Construa candidatos de acordo com estruturas como pergunta + resposta, afirmação + justificativa, tese + consequência, acusação + evidência, história + desfecho, setup + punchline, confronto + reação ou opinião + síntese.

O início e o fim devem ser ajustáveis. Use expansão para trás e para frente baseada em frases, pausas, turnos de fala e sinais de conclusão. A duração deve ser consequência do raciocínio, não uma tesoura fixa. Um corte curto pode ser ótimo se fechar uma reação; um corte longo pode ser necessário para uma explicação completa.

### Gates obrigatórios

Antes do score de potencial viral, todo candidato deve passar por gates. Um hook forte nunca pode compensar contexto ausente.

Rejeite ou expanda candidatos que começam no meio de frase, começam com “isso”, “ele”, “essa situação” ou expressão equivalente sem antecedente, exibem resposta sem pergunta necessária, ocultam o locutor relevante, terminam antes do payoff, possuem áudio incompreensível, têm ruído ou clipping grave, cortam o rosto ou o elemento visual principal ou repetem outro candidato quase igual.

Para dados e denúncias, exija especificidade mínima: número, fato, instituição, afirmação ou evidência presente na própria fala. Não invente contexto, não complete números com conhecimento externo e não trate afirmações políticas como fatos verificados.

Registre os gates aprovados e os motivos de rejeição. Um candidato rejeitado deve continuar disponível para auditoria, mas não deve ocupar uma das vagas do dia.

### Ranking editorial global

Separe três conceitos: qualidade mínima, potencial editorial e diversidade do portfólio. O score individual só pode ser comparado depois dos gates.

Use uma composição inicial que possa ser calibrada posteriormente:

| Dimensão | Peso inicial |
| --- | ---: |
| Contexto autossuficiente | 25% |
| Conclusão, payoff ou desfecho | 20% |
| Força da tese, história ou reação | 15% |
| Hook, tensão ou surpresa | 15% |
| Potencial de conversa e compartilhamento | 10% |
| Clareza de fala e qualidade do áudio | 5% |
| Enquadramento e ritmo visual | 5% |
| Novidade e diversidade | 5% |

Retorne score, confiança, fatores, gates, tipo editorial, live de origem, timestamp, título provisório, motivo de entrada e motivos de rejeição dos candidatos próximos.

Depois do score individual, faça seleção de portfólio diário entre todas as oito lives. Use orçamento adaptativo: aproximadamente quatro a oito cortes por live como ponto inicial, sem tornar isso uma regra rígida. Uma live excelente pode render dez; uma live fraca pode render dois. Evite que uma única fonte, tema, pessoa ou tipo editorial domine toda a lista.

A seleção global deve eliminar duplicatas temporais e semânticas, evitar cinco cortes com a mesma tese e preservar variedade entre política, confronto, informação, história, humor, reação e bastidor quando houver qualidade real.

### Enquadramento profissional

Não aceite crop estático ou apenas posição média de rosto como solução final. Faça análise por janela e reframe temporal suavizado. Identifique o locutor ou elemento dominante, acompanhe o rosto e preserve olhos, boca, texto e objetos importantes.

Em split-screen ou debate, decida entre preservar o quadro, focar o interlocutor, alternar o foco em mudança de turno ou manter duas pessoas visíveis. Nunca corte automaticamente um rosto ou uma informação relevante apenas para preencher 9:16.

Execute QA visual após o render: rosto parcialmente cortado, texto fora da área segura, salto brusco de crop, plano instável, tela preta, duração inválida e áudio ausente devem ser detectados. Se a confiança do enquadramento for baixa, preserve o original e marque revisão manual.

### Revisão humana mínima

A tela de revisão deve mostrar o corte, margem antes e depois, live de origem, score, confiança, gates aprovados, tipo editorial, razão de entrada e alternativas próximas. O editor deve conseguir aprovar, rejeitar com motivo e ajustar início/fim com handles.

As rejeições e ajustes são dados de calibração. Registre por que o editor rejeitou: sem contexto, sem conclusão, repetido, fraco, enquadramento ruim, áudio ruim, pessoa errada, politicamente fraco, humor sem payoff ou outro motivo. Use esse histórico para recalibrar pesos por perfil e por tipo editorial.

## O que não fazer

Não aumente a quantidade para fingir eficiência. Não atribua “viralidade garantida”. Não use o LLM como autoridade final sem validação determinística. Não invente falas, fatos, números, contexto ou identidade de pessoa. Não force todos os cortes para o perfil político. Não trate legendas e música como prioridade maior que seleção e contexto. Não altere a branch principal sem manter uma forma recuperável de voltar. Não deixe testes verdes esconderem uma etapa que nunca foi exercitada no pipeline real.

## Critérios de aceite

Considere uma fase concluída somente quando os critérios forem verificáveis:

1. O usuário consegue adicionar oito lives de uma vez e acompanhar cada fonte em uma campanha diária.
2. O processamento retoma após reinício sem repetir etapas já concluídas.
3. Os candidatos são unidades de pensamento, não apenas blocos fixos.
4. Todo corte final passa por gates de contexto, frase, falante, conclusão, áudio e enquadramento.
5. O ranking global compara candidatos de todas as lives e controla diversidade.
6. A faixa de 39–50 só é preenchida quando houver material acima da nota mínima.
7. O sistema pode entregar menos e explicar a insuficiência.
8. O reframe acompanha planos e rostos sem saltos visíveis e sinaliza baixa confiança.
9. A revisão registra aprovação, rejeição, ajuste e motivo.
10. A suíte automatizada cobre unitários, smoke HTTP, fila, ranking global, gates, render real e um fluxo de campanha com múltiplos vídeos.
11. Nenhuma chave de API aparece em código, logs, commits, exports ou mensagens de erro.
12. A execução continua funcional sem Gemini e sem Ollama, usando o caminho local.

## Entregáveis obrigatórios de cada ciclo de desenvolvimento

Ao terminar uma etapa, entregue no repositório: código funcional, testes, documentação em português, changelog curto, relatório de limitações e instruções de execução. Mostre quais métricas foram medidas e quais ainda são hipóteses. Informe exatamente quais arquivos foram alterados, quais testes passaram e quais riscos permanecem.

Não encerre apenas com ideias. Implemente a próxima melhoria de maior impacto, rode os testes, revise o diff, publique a versão recuperável e entregue um resumo objetivo. O resultado final deve fazer o editor sentir que recebeu uma lista editorial de cortes prontos para revisão — não uma pilha de trechos aleatórios.

---

## Pedido final para o agente

Audite agora o Furia Clips com esse padrão. Identifique os três gargalos que mais impedem a meta de oito lives e 39–50 cortes de alta qualidade. Implemente primeiro a seleção global com gates de contexto e conclusão, depois a fila de campanha diária e, em seguida, o reenquadramento temporal. Não disperse esforço em legendas, música ou cosmética enquanto esses três problemas não estiverem resolvidos. Valide com testes e com pelo menos um fluxo real de múltiplos vídeos antes de declarar a etapa pronta.
