# Prompt de evolução profissional do Furia Clips

> **Como usar:** copie integralmente o bloco abaixo e envie-o como uma nova solicitação. Ele pede uma evolução completa, mas orienta o agente a primeiro pesquisar, auditar, projetar, testar e só então implementar e publicar.

```text
Atue como líder técnico de produto, engenheiro sênior de IA de vídeo, visão computacional, áudio, experiência editorial e pipeline de pós-produção. Trabalhe com autonomia máxima no repositório https://github.com/SAGIEV007/furia-clips, na branch manus/rebuild-opus-parity. Não me peça confirmação para decisões técnicas normais; preserve credenciais, não exponha chaves e publique commits verificáveis na branch de trabalho ao final.

## Contexto e objetivo

O Furia Clips é uma ferramenta local para um editor de vídeo do Renan Santos/MBL. O objetivo não é simplesmente cortar vídeos longos em trechos aleatórios ou aplicar crop vertical centralizado. O produto deve funcionar como um assistente editorial profissional de clipping político: analisar uma live/entrevista antes de renderizar, encontrar os melhores momentos, explicar por que são bons, indicar minutagens auditáveis e decidir se cada momento deve ser entregue em 9:16, mantido no original 16:9 ou encaminhado para edição manual em 1:1.

A meta operacional é selecionar apenas a nata de aproximadamente oito lives por dia, de três a quatro horas cada, para atingir 39 a 50 cortes diários no portfólio total, com qualidade e contexto acima de quantidade. Os formatos devem abranger política, propostas, críticas, confronto, reação, bastidor, conversa e momentos descontraídos. O campo de contexto do editor deve continuar opcional: o perfil político de Renan Santos/MBL é aplicado automaticamente.

O padrão de referência é profissional, próximo ao que ferramentas como OpusClip, Vizard, Klap e soluções de active-speaker reframing apresentam publicamente, mas sem afirmar que reproduziremos o modelo proprietário de nenhuma delas. Converta padrões verificáveis em requisitos, testes e métricas mensuráveis.

## Regra principal: análise antes da renderização

Não inicie a renderização de clips imediatamente após importar um vídeo. Primeiro implemente ou aperfeiçoe uma etapa obrigatória chamada **Análise editorial prévia**. Ela deve aceitar upload local, link público e transcrição manual Tactiq/SRT/VTT.

Para cada vídeo, gere e persista um relatório legível e um JSON estruturado. O relatório deve informar duração, resolução, proporção original, qualidade de áudio, layout visual, participantes prováveis, turnos de fala, perguntas, respostas, mudanças de assunto, pausas, sobreposições, cenas e blocos de entrevista. A transcrição deve preservar timestamps e usar Gemini online como primeira opção quando configurado, com fallback local para Whisper/faster-whisper. Nunca invente uma diarização perfeita: use rótulos como `Renan`, `mediador`, `convidado` ou `desconhecido` apenas com confiança explicada.

Antes de sugerir um render, produza um **Mapa editorial de candidatos** navegável na interface. Cada candidato deve conter no mínimo:

- Início, fim e duração precisos em segundos e em `HH:MM:SS.mmm`.
- Título editorial provisório, assunto, tese, gancho, conclusão e família de conteúdo.
- Texto da pergunta, quando necessária, e resumo da resposta.
- Quem é o foco do clip e a confiança dessa atribuição.
- Score de potencial, score de contexto, score técnico e score final explicável.
- Indicadores de risco: começa no meio de frase, termina sem conclusão, sobreposição de voz, pergunta sem resposta, resposta sem contexto, mudança brusca de câmera, legenda/GC da emissora cortado, crop inseguro ou repetição temática.
- Recomendação editorial: `APROVAR`, `REEDITAR`, `MANTER APENAS COMO MINUTAGEM`, `REJEITAR`.
- Recomendação de composição: `9:16_active_speaker`, `9:16_split`, `9:16_picture_in_picture`, `16:9_original`, `1:1_manual` ou `4:5_manual`.
- Justificativa curta e objetiva para cada decisão.

A interface deve permitir revisar, filtrar, buscar, ordenar por score, abrir o trecho em preview, ajustar início/fim por frames e exportar a lista de minutagens mesmo quando o editor preferir finalizar manualmente no CapCut ou em outro software. O export de minuta deve incluir CSV, JSON e TXT Tactiq ou Markdown, com links/nomes de fonte e todas as justificativas.

## Política de proporção e enquadramento

Não force todo vídeo para 9:16. Mantenha a mídia-fonte intacta. A análise deve decidir a composição antes do render e deixar essa decisão explícita para o editor.

1. Use `9:16_active_speaker` somente quando houver evidência suficiente de que um locutor visual é o foco durante o trecho. Combine transcrição timestampada, VAD, sinais de voz, mudanças de turno, detecção facial, movimento labial quando tecnicamente viável, tracking temporal, mudança de câmera e análise multimodal. O crop deve seguir o locutor ao longo do tempo, e não permanecer centralizado.
2. Use `9:16_split` ou `9:16_picture_in_picture` quando pergunta, reação ou duas pessoas falando forem editorialmente essenciais e a composição puder preservar ambos sem poluir o quadro.
3. Use `16:9_original` quando existirem múltiplas faces, split-screen complexo, troca de câmera, fala sobreposta, confiança baixa, rosto parcialmente detectado, GC/legenda da TV que seria destruído pelo crop ou qualquer ambiguidade. É preferível manter o vídeo inteiro do que cortar a pessoa errada.
4. Use `1:1_manual` quando a análise concluir que a ideia é boa, mas o editor deve montar uma versão quadrada manualmente. Não faça crop automático apenas porque a saída será quadrada; entregue a minutagem, a composição recomendada e o motivo.
5. Registre `framing_mode`, confiança, participantes visíveis, transições de locutor e motivo do fallback em todos os resultados.

Crie um preview visual por clip com safe zones de legenda, transições de locutor e opção para o editor aceitar, corrigir o foco, escolher original, escolher 1:1 manual ou renderizar 9:16. O sistema deve produzir uma planilha/manifesto de revisão com os candidatos e não apenas arquivos finais.

## Active speaker e entrevistas

Implemente uma arquitetura de active-speaker por camadas. Comece com ASR timestampado, VAD, diarização/agrupamento de voz quando disponível, detecção de faces, tracking de caixas faciais, análise de cenas e sincronização entre mudança de voz e mudança visual. Use Gemini multimodal como enriquecimento quando houver chave e custo permitido; o pipeline não pode depender exclusivamente dele.

Para entrevistas longas, identifique janelas de perguntas e respostas, preserve a pergunta quando ela for necessária para entendimento e detecte respostas autossuficientes que possam começar por uma tese forte. Faça teste específico com entrevistador, Renan e convidados. Para casos ambíguos, não declare certeza: entregue a minutagem e marque o clip para revisão.

O sistema deve diferenciar três coisas que hoje não podem ser confundidas: `quem está falando`, `quem aparece na imagem` e `quem é o foco editorial`. O Renan pode ser o foco mesmo quando o mediador faz uma pergunta curta; uma reação visual pode ser relevante, mas não deve substituir a fala principal sem justificativa.

## Ranking e seleção editorial

Reestruture o ranking de modo explicável. Não use um único “viral score” opaco. Calcule e mostre, no mínimo, gancho inicial, clareza da tese, completude, novidade/especificidade, tensão/conflito, potencial de comentário, densidade informativa, ritmo, qualidade de áudio, risco de descontextualização, adequação à família editorial e diversidade em relação a outros candidatos.

Use gates antes do ranking. Rejeite ou penalize fortemente: início no meio da frase, fim antes do payoff, pergunta sem resposta, resposta ininteligível, repetição sem nova informação, fala sobreposta sem tratamento, título enganoso e render com enquadramento inseguro. A seleção diária deve limitar repetição de tema/fonte/família e favorecer uma carteira editorial diversa entre as lives, em vez de gerar muitos cortes similares de um único vídeo.

Mantenha candidatos “quase bons” no relatório com a sugestão objetiva de como o editor pode salvar o corte manualmente: por exemplo, “voltar 7,2 s para incluir a pergunta”, “encerrar 3,1 s antes do mediador interromper”, “usar 16:9/1:1 em vez de 9:16”, ou “trocar o gancho pelo trecho em 00:06:25.400”.

## Benchmark obrigatório antes de implementar

Antes de alterar arquitetura, pesquise documentação oficial atual de OpusClip, Vizard, Klap, LumiClip e outras referências que se mostrarem relevantes. Separe afirmações de marketing de recursos concretos. Extraia, quando comprovável, padrões para: clipping por conteúdo, ranking, reframe de active speaker, múltiplas proporções, split/PIP, batch processing, revisão manual, brand kit, manifests, API/webhook, fila, métricas de qualidade e colaboração.

Use as páginas oficiais como ponto de partida:
- https://www.opus.pro/
- https://vizard.ai/tools/ai-reframe
- https://klap.app/tools/ai-video-clipping-tool
- https://lumiclip.ai/ai-active-speaker-video-reframing

Produza primeiro uma matriz “recurso de mercado → aplicável ao Furia Clips → prioridade → implementação local/online → risco/limitação → teste de aceitação”. Não copie interfaces nem alegue paridade com modelos proprietários.

## Dados editoriais e aprendizado com referências

Use como referência editorial os vídeos públicos dos perfis informados pelo usuário:
- https://www.instagram.com/renansantosreserva/
- https://www.instagram.com/renansantosmbl/

Analise apenas conteúdo publicamente acessível e respeite limites de plataforma. Construa um catálogo de padrões observáveis, não uma cópia de vídeos: duração, tipo de gancho, estrutura pergunta-resposta, tom, assunto, ritmo, payoff, composição, formato, presença de mediador, legibilidade e sinais de engajamento disponíveis. Compare com exemplos públicos de política viral somente quando isso agregar uma métrica ou hipótese editorial verificável.

Transforme as referências em um perfil versionado e explicável. Não treine nem afirme treinar um modelo proprietário sem dados, consentimento, métrica, separação treino/validação e avaliação humana. A primeira entrega deve usar regras, sinais e feedback do editor; a evolução posterior pode adicionar aprendizado supervisionado a partir de aprovações, rejeições e ajustes de minutagem feitos pelo usuário.

## Produto e fluxo de trabalho

Melhore a interface para que o editor veja claramente as etapas: `Importar → Analisar → Revisar candidatos/minutagens → Escolher composição → Renderizar selecionados → Revisar resultados`. O vídeo deve ser baixado na melhor qualidade disponível até 1080p para a pasta escolhida pelo usuário. A fonte original não deve ser alterada.

Ao fim da análise, o editor deve poder escolher entre:

- Renderizar somente os candidatos aprovados.
- Exportar somente o relatório/minutagens para edição manual.
- Renderizar em 9:16 quando o active speaker for confiável.
- Manter 16:9 original.
- Marcar para montagem manual em 1:1 ou 4:5.

Inclua status detalhado no console, logs persistentes, mensagens de erro acionáveis, reprocessamento de etapa isolada, cache seguro de transcrição/análise e modo de revisão que não obriga renderização. Preserve a abertura automática no Opera GX, o seletor nativo de arquivos/pastas e o fluxo por link público sem cookies pessoais, DRM ou conteúdo privado.

## Qualidade, validação e entrega

Antes de publicar, crie ou amplie testes para parser de transcrição, normalização de links, download até 1080p, escolha de pasta, geração de artefatos de transcrição, análise de candidatos, gates editoriais, avaliação de confiança facial, active speaker, split/ambiguidade, fallback 16:9, export de manifestos e render com áudio válido.

Faça smoke tests reais com vídeos horizontais de entrevista. Verifique as dimensões, áudio, duração, início/fim, presença do locutor correto, estabilidade do crop, visualização de GC/legenda e coerência da minuta. Audite manualmente uma amostra de clips com os critérios `APROVAR`, `REEDITAR` e `REJEITAR`; não use apenas testes unitários.

Entregue ao final:

1. Diagnóstico do estado inicial e lacunas comparadas ao benchmark.
2. Plano de arquitetura por fases, com prioridades e riscos.
3. Implementação testada, commit(s) e link(s) publicados em `manus/rebuild-opus-parity`.
4. Relatório de auditoria dos exemplos analisados.
5. Manual de uso em português brasileiro.
6. Lista honesta do que ainda não alcança o padrão de ferramentas comerciais e como medir evolução.

Não exponha chaves de API, não faça afirmações sem evidência, não use crop central como fallback “profissional” e não esconda candidatos rejeitados: mantenha a minutagem para revisão humana. O objetivo final é reduzir o trabalho mecânico do editor e aumentar a qualidade editorial, não substituir o julgamento final de quem conhece o público político do Renan.
```

## Referências de benchmark

O prompt direciona a pesquisa para capacidades públicas de clipping multimodal, reframe, múltiplas proporções, active speaker, processamento em lote e revisão manual. As páginas oficiais consultadas descrevem esses recursos como referências de produto, sem comprovar nem exigir paridade com os modelos proprietários.[1] [2] [3] [4]

## Referências

[1]: https://www.opus.pro/ — OpusClip, AI editing models e ReframeAnything.

[2]: https://vizard.ai/tools/ai-reframe — Vizard, AI Reframe e priorização de face/locutor.

[3]: https://klap.app/tools/ai-video-clipping-tool — Klap, ranking, reframe, batch e revisão para equipes.

[4]: https://lumiclip.ai/ai-active-speaker-video-reframing — LumiClip, active speaker e layouts para conversas.
