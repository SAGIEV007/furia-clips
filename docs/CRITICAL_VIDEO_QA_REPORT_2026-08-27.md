# Relatório sanitizado — QA do vídeo crítico

## Escopo e contrato

A rodada foi conduzida sobre uma entrevista privada longa de Renan Santos, usando uma transcrição manual fornecida pelo editor. O **Furia 1 continua sendo o único motor canônico** de transcrição reutilizada, formação de candidatos, score, gates, seleção e renderização. A interpretação multimodal do Gemini é uma evidência auxiliar para revisão; ela não aprova, pontua tecnicamente nem substitui as regras locais.

Nenhuma mídia, legenda, transcript, banco, cache, log de diagnóstico, URL privada ou credencial faz parte deste documento ou deve ser versionada.

## Resultado local pós-calibração

A correção de fronteiras de entrevista passou a reconhecer uma pergunta de seguimento dividida em várias linhas da legenda, desde que haja confirmação lexical próxima e intervalo curto. A fronteira da pergunta agora é estendida até o ponto de interrogação; o corte anterior não pode absorver o começo da nova pergunta. Também foi corrigido o cálculo de densidade de entrevista em transcrições recortadas: a duração é medida pelo span relativo do trecho, não pelo timestamp absoluto.

Na reexecução local pós-correção, o Furia 1 formou 32 candidatos antes dos gates, adiou 3 por contexto/revisão explícita e renderizou **29 clips**, sem reproduzir o falso positivo confirmado anteriormente em que chegava ao export apenas a pergunta da jornalista. O render sequencial continuou estável e terminou em aproximadamente 442 segundos.

A comparação temporal com 20 intervalos humanos é apenas descritiva: a rodada local pós-correção teve 10/29 candidatos com IoU ≥ 0,5, 4 com IoU ≥ 0,7 e 1 com IoU ≥ 0,9; 10 das 20 referências foram cobertas a IoU ≥ 0,5. A rodada local anterior teve 11/30, 4/30 e 1/30, com 11 referências cobertas. A pequena redução numérica não invalida a correção: o objetivo desta alteração foi remover um falso positivo editorial e proteger a próxima pergunta, não ajustar timestamps ao arquivo de referência. IoU não mede contexto, clareza, interrupção, payoff ou potencial viral.

## QA audiovisual amostral

Quatro exports temporários foram revisados por análise audiovisual independente. O trecho sobre a bomba foi aprovado: a pergunta/contexto está presente, Renan sustenta a fala e o payoff fecha antes da intervenção seguinte. O trecho sobre Estado Democrático de Direito foi aprovado com observação: a pergunta anterior não aparece, mas a primeira frase de Renan estabelece contexto suficiente e o argumento fecha. O trecho após o retorno do intervalo sobre dívida pública foi considerado aproveitável com ressalva: há um pequeno resíduo de fala anterior no início e uma interjeição da jornalista, mas o contexto e o payoff permanecem compreensíveis. O trecho iniciado por “Por que não” foi aprovado na amostra: a pergunta aparece e Renan conduz a resposta até uma conclusão central.

Nenhuma dessas quatro amostras reproduziu o falso positivo da pergunta isolada. A revisão audiovisual continua sendo amostral e não equivale a aprovação automática de todos os 29 clips.

## Gemini: medição e decisão

A rodada Gemini integral anterior terminou em aproximadamente 905 segundos, com cerca de 90 segundos de compactação local, poucos segundos de upload e o restante dominado pelo processamento remoto e por chamadas de seleção textual sujeitas a 429/503. O conjunto final quase não mudou em relação ao local, portanto o custo não se justificou como caminho padrão.

Uma chamada direta posterior, usando o prompt multimodal reduzido, mediu aproximadamente 90,7 segundos para compactar o proxy de 640 px e 1/8 fps, 1,2 segundo para upload e cerca de 171 segundos adicionais até o retorno remoto. O Gemini ainda devolveu JSON truncado; a resposta não foi tratada como seleção final. O problema principal não é a transferência do arquivo original: é preparar o proxy, aguardar a ativação/processamento remoto de uma fonte longa e lidar com limites/instabilidade da API.

Foram aplicadas quatro proteções: a referência textual enviada ao multimodal foi limitada a 24 mil caracteres, `transcript_segments` deixou de ser solicitado, a saída máxima foi reduzida para 4096 tokens e os deadlines passaram a ser fracionários e recalculados entre as etapas. A camada de parsing agora recupera somente propriedades de topo completamente decodificadas quando o objeto chega truncado, marca a resposta como parcial e mantém o fallback local; não inventa timestamps, falas ou campos incompletos. A recomendação de UX é deixar **NLP local/Furia 1 como padrão** e oferecer “revisar evidência audiovisual no Gemini” como ação explícita, limitada e cancelável.

## Chub: contribuição útil e segura

O Chub permanece **read-only, offline-first e baseado apenas em snapshot autorizado local**. Não houve consulta por clip, scraping, bypass de login/captcha, previsão de desempenho, publicação ou envio do transcript ao Chub.

A contribuição implementada nesta rodada é de governança e explicabilidade: propostas temporais guiadas por highlights do snapshot não entram no pool canônico por padrão. A nova configuração `campaign_hub_guided_selection` começa desativada; quando desativada, o snapshot pode ser exibido como memória histórica/descoberta e alimentar explicações limitadas, mas a seleção e o score técnico continuam no Furia 1. A ativação de propostas guiadas é um opt-in explícito e continua sujeita a gates de contexto, locutor, timing e revisão. O painel Studio também passa a expor a proveniência dos flags de borda e as razões de revisão, sem esconder um risco atrás do score.

Essa contribuição não foi medida como ganho de qualidade no vídeo crítico, porque o snapshot Chub não foi usado naquela execução local. Portanto, não há alegação de melhora viral ou de treinamento de pesos. O que foi validado foi o limite seguro da influência: memória histórica explica ou ajuda a desempatar; não decide sozinha qual clip publicar.

## Verificações de engenharia

Os testes focados de entrevistas, sabatina, gates, Gemini, quotas e espera passaram após a calibração. Os testes específicos de Chub, memória, ranqueador, adapter Studio e payload de flags também passaram. O próximo passo de entrega é executar a suíte completa, checagem de sintaxe Python/JavaScript, revisão de segredos e limpeza de artefatos temporários antes do commit exclusivo em `furia-studio-f1-integration`.
