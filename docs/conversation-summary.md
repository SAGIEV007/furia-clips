# Furia Clips — resumo durável da conversa e do projeto

**Data de consolidação:** 22 de agosto de 2026
**Repositório:** [`SAGIEV007/furia-clips`](https://github.com/SAGIEV007/furia-clips)
**Branch de publicação:** `publish-context-only`
**Propósito:** preservar o contexto essencial da conversa para que futuras sessões possam continuar o desenvolvimento sem depender do backup da conversa do Manus.

> Este documento é um resumo operacional sanitizado, não uma cópia literal da conversa. Credenciais, chaves, cookies, vídeos, bancos de dados, transcrições privadas, URLs assinadas e feedback bruto deliberadamente não são reproduzidos.

## 1. Objetivo central

O Furia Clips é uma bancada local de edição e seleção de cortes políticos e descontraídos em português brasileiro. O editor deve conseguir colocar uma fonte — arquivo local, vídeo baixado de uma URL pública ou transcrição timestampada — e receber candidatos curtos, autossuficientes, contextuais e revisáveis. O objetivo editorial é **qualidade e contexto antes de quantidade**: pergunta–resposta quando existir, setup compreensível, tese ou conflito, evidência, payoff ou conclusão, hook natural, precisão temporal e enquadramento visual seguro.

A meta operacional discutida foi produzir aproximadamente 39–50 cortes por dia a partir de várias fontes, e não extrair dezenas de cortes artificiais de um único vídeo. Em geral, cortes menores são preferíveis, mas não existe duração fixa: um trecho pode ultrapassar três minutos quando a pergunta, a explicação, a prova ou a conclusão exigirem isso. O teto técnico continua sendo um limite de segurança, não uma meta editorial.

Renan Santos/MBL é uma prioridade editorial para os priors e os exemplos, porém o programa deve permanecer genérico o suficiente para analisar outros oradores e vídeos. O sistema não deve forçar todo conteúdo a ser político: humor, reação, bastidor, cavalgada, berrante, música, gesto ou outro momento descontraído podem ser candidatos, desde que a revisão confirme que há valor no vídeo e no áudio.

## 2. Requisitos que foram consolidados

| Área | Decisão consolidada |
| --- | --- |
| Seleção | Contexto autossuficiente, hook, payoff, pergunta–resposta, clareza, densidade e precisão temporal têm prioridade sobre volume bruto. |
| Duração | Preferir o menor intervalo que preserve o raciocínio; normalmente até três minutos, sem cortar uma conclusão apenas para cumprir uma duração. Teto técnico separado. |
| Idioma | Priorizar português brasileiro nas fontes públicas quando o provedor expuser metadados de áudio; não inventar dublagem ou tradução. |
| Transcrição | Aceitar transcrição manual timestampada, legenda pública, transcrição automática online e Whisper local como fallback; validar identidade da fonte antes de reutilizar. |
| Contexto | Permitir análise integral antes do corte, com dossiê local que oriente tópico, capítulos, perguntas, respostas, payoff, regiões ignoradas e avisos de revisão. |
| Enquadramento | Face tracking opcional e conservador; sem reconhecimento de identidade ou memória biométrica. Quando a decisão visual for ambígua, preservar a composição original e pedir revisão. |
| Revisão humana | Aprovação, rejeição, ajuste de entrada/saída e motivo editorial são decisões finais do editor, não rótulos automáticos. |
| Persistência | Código, testes e documentação ficam no GitHub; dados editoriais, mídia, banco, transcrições e feedback bruto ficam fora do checkout em `~/FuriaClipsData`. |
| Campaign Hub | Consulta somente leitura. Nenhuma escrita, publicação, alteração, sincronização ou envio de dados ao Campaign Hub é permitido. |
| Licenças | Ferramentas externas de long-to-short servem como inspiração conceitual e de testes; não copiar código AGPL ou componentes com licença comercial incompatível. |

## 3. Linha do tempo da conversa

### 3.1 Diagnóstico inicial e visão de produto

A conversa começou com o pedido de auditar profundamente o Furia Clips, entender seu propósito e transformá-lo em uma ferramenta de nível profissional para cortes políticos. Foram discutidas automação de dependências no Windows, abertura automática do navegador, seleção de pastas por explorador de arquivos, download de URL pública, escolha de qualidade até 1080p, geração de transcrição timestampada e fallback local quando serviços online falhassem.

O foco foi progressivamente retirado de SEO, thumbnails e publicação. O produto passou a ser tratado como uma **bancada de edição e revisão**, com player, fila de clips, score explicável, contexto, transcrição, ajuste temporal e aprovação/rejeição. A geração de headlines e os formatos 9:16, 1:1 e fake tweet foram mantidos como apoio editorial, mas não devem tomar o lugar do núcleo de corte.

### 3.2 Transcrição, contexto e fontes longas

Foram discutidos vídeos de 20 minutos a várias horas, lives com trechos de entrevista e o problema de usar a transcrição de um vídeo em outro. A solução adotada foi associar transcrições a uma identidade normalizada da fonte, com caminho e assinatura leve quando disponíveis. Uma transcrição incompatível não pode entrar silenciosamente no ranking ou no dossiê.

O Furia passou a separar estrutura timestampada de validação semântica. Uma transcrição pode ter segmentos tecnicamente válidos sem ter sido semanticamente conferida; a interface precisa dizer isso de modo explícito. A análise integral é opcional e pode usar o dossiê local antes do corte, mas não deve obrigar o envio de um vídeo enorme para um serviço online. A rotina longa deve preferir processamento por blocos, cache local, jobs persistentes e cancelamento seguro.

### 3.3 Pesquisa dos perfis e do ecossistema Missão/Chub

Foi solicitada a análise de todos os vídeos dos perfis públicos de Renan Santos, principalmente `@renansantosreserva` e `@renansantosmbl`, incluindo áudio, imagem, captions, headlines, formatos, desempenho e padrões editoriais. A coleta pública não deve ser descrita como integral quando a paginação ou o servidor responderem 401, 403, 429, CAPTCHA ou outra restrição. Não foi autorizado contornar essas barreiras.

O Campaign Hub/Chub e o site de criadores da Missão foram tratados como fontes de inspiração e evidência auxiliar para contexto, blocos semânticos, transcrições, pauta, métricas, densidade, hooks, entidades, audiência e busca por termos. O Furia pode replicar **padrões funcionais genéricos** localmente, mas não deve depender de uma escrita no Chub nem afirmar que possui todo o corpus do site. A pesquisa long-to-short concluiu que FunClip é uma referência MIT forte para operação local e seleção por texto/locutor; OpenShorts é uma referência de arquitetura e jobs, com separação de licença em partes do projeto; outros projetos analisados têm limitações de APIs externas, são antigos ou têm licenças incompatíveis. Os detalhes estão em [`github-long-to-short-research-2026-08-22.md`](../FuriaClipsData/analyses/github-long-to-short-research-2026-08-22.md) fora do Git e em [`long-to-short-metrics-and-plan-2026-08-21.md`](long-to-short-metrics-and-plan-2026-08-21.md).

### 3.4 Aprendizado editorial

Foi explicado que observar vídeos públicos ou consultar o Chub não equivale a treinar automaticamente um modelo. Para que o Furia melhore com aprovações e rejeições reais, é necessário um dataset local sanitizado e decisões editoriais suficientes. O programa ganhou importação de CSV/JSON/JSONL e geração de priors agregados, mas o conjunto de aproximadamente 3.000 cortes reais ainda não foi importado; portanto, não há justificativa para recalibrar pesos do ranking como se esse treinamento já existisse.

Os priors locais podem resumir duração, formato, família de hook, forma de abertura, ponte pergunta–resposta, motivos de rejeição, tópico limitado e forma estatística de headline. Eles não retornam transcrição, mídia, caminho privado ou headline bruta, não fazem fine-tuning e não substituem o vídeo atual. O banco local inspecionado tinha muitos clips pendentes e zero eventos finais de `clip_feedback` no momento da auditoria; essa ausência foi tratada honestamente.

## 4. Capacidades atualmente implementadas

### 4.1 Contexto e ranking

O pipeline possui sinais explicáveis de contexto autossuficiente, pergunta–resposta, payoff, tese, evidência, consequência, fechamento, conflito, mobilização, tópico, capítulo e densidade. Existem gates para contexto, locutor, transcrição, técnica e payoff. A favorabilidade e a hipótese de coice pergunta-hostil → resposta forte são sinais auxiliares, com modo `off` padrão e modos opt-in `prioritize` e `require`.

O ranking também reconhece famílias como político, humor, reação, bastidor, conversa e descontraído. Sinais de áudio, movimento, Chub, Acervo e layout são bounded e revisáveis: nenhum deles deve superar um gate crítico ou prometer viralização.

### 4.2 Transcrição e análise de contexto

A transcrição manual ou pública pode ser reutilizada somente quando pertence à fonte atual. O pipeline arquiva resultados timestampados fora do Git, mantém proveniência, mede cobertura e diferencia “estrutura válida” de “semântica validada”. A análise integral de contexto possui job persistente, estado na HUD, cancelamento e proteção contra eventos atrasados.

A transcrição do trecho do clip é mantida associada ao candidato para a revisão. O arquivo persistente é reidratável entre sessões, mas continua dependente de o editor copiar ou sincronizar `~/FuriaClipsData` entre os dois computadores.

### 4.3 Evidência audiovisual auxiliar

O sistema pode solicitar evidências não verbais como risada possível, reação, gesto, objeto, animal, montaria, berrante, música, paisagem e silêncio expressivo, sempre com timestamp, categoria, confiança, descrição curta e `requires_visual_review`. Isso é evidência auxiliar: não cria automaticamente um corte independente, não reconhece a identidade de uma pessoa e não altera o score por si só.

O áudio local calcula RMS, dB, zero-crossing, onset, crest factor e possível textura de reação. Esses sinais não são apresentados como certeza de risada ou música. O movimento visual é efêmero e baseado em posições normalizadas; não existe memória facial.

### 4.4 Enquadramento

O face tracking é opcional. O Furia filtra coordenadas não finitas e confianças inválidas, limita os valores e recua para crop centralizado ou composição original quando não há confiança. Em layout dividido ou ambíguo, a política segura preserva 16:9 e exige revisão, em vez de cortar um interlocutor.

### 4.5 Ajuste temporal da bancada

A bancada oferece Entrada e Saída para corrigir um clip sem baixar o vídeo inteiro. A validação não promete playback novo: ela somente verifica e alinha limites. O botão **Renderizar ajuste** cria um único MP4 derivado usando a fonte original permitida pelo projeto.

O ajuste prefere timestamps de palavras, cai para segmentos quando necessário, respeita zero, duração mínima, teto da fonte e snapping outward-only. O intervalo canônico original permanece protegido para auditoria e deduplicação. O payload também diferencia `original_bounds`, `active_bounds`, `render_start`, `render_end`, `render_duration` e `active_render_status`.

O re-render é um job persistente `adjust_clip_render`. A HUD informa o clip, o botão fica ocupado, o editor pode pedir parada segura, o FFmpeg é encerrado cooperativamente, saídas parciais são removidas e eventos de conclusão atualizam player, caminho, cache, limites ativos e revisão. Jobs ativos guardam um artefato mínimo com `clip_id` para recuperação após recarga.

### 4.6 Deduplicação

A deduplicação entre execuções considera fonte, intervalo canônico, último intervalo ajustado e sinais editoriais persistidos. Sobreposição não é suficiente para descartar automaticamente um candidato quando existe uma decisão editorial diferente — por exemplo, uma conclusão, ponte de contexto ou payoff novo. Duplicatas exatas e repetições lexicalmente equivalentes continuam bloqueadas.

### 4.7 UX e operação

A aplicação possui shell dark-first, bancada, fila, player, scorecard, drawers de explicação, filtros, atalhos, foco de teclado, densidade compacta, estados de vazio/loading/erro/sucesso e HUD de jobs. O design foi orientado à decisão: uma ação principal por etapa, progressive disclosure e menos ruído visual. A UI preserva IDs, rotas e contratos legados.

Os logs incluem versão do programa e revisão de runtime. O re-render mostra seu estado sem fingir que o arquivo já foi atualizado antes da conclusão. A fila persistente identifica o tipo da operação e o clip associado.

## 5. Principais correções e publicações recentes

| Commit confirmado | Resultado |
| --- | --- |
| `62d5dc1` | Reidratação de clips ajustados após recarregar o projeto, normalizando `path/start/end/clip_id` e preservando enquadramento original quando necessário. |
| `dac0ccc` | Guarda thread-safe por clip contra dois re-renders simultâneos. |
| `8127aa6` | Liberação da guarda mesmo quando o construtor do `VideoCutter` falha antes do FFmpeg. |
| `564a69d` | Estado visual ocupado no botão de renderização, com `aria-busy`, rótulo de progresso e restauração segura. |
| `00249c6` | Migração do re-render para job persistente, cancelável e com atualização da HUD. Inclui callback de cancelamento cooperativo no `VideoCutter`. |
| `9519d46` | Atualização adicional do changelog com a recuperação pós-reload e proteção contra corrida de eventos. |
| `8d5fc21` | Regressões do cancelamento antes do FFmpeg e encerramento seguro do subprocesso. |

O commit deste documento também registra a identificação explícita do clip na fila persistente e as expectativas correspondentes da HUD. A branch continua privada e é a branch padrão observada no repositório.

## 6. Arquivos e áreas importantes

| Caminho | Papel |
| --- | --- |
| `app.py` | Rotas Flask, jobs, contexto integral, re-render individual, projetos, cancelamento e payloads de revisão. |
| `database.py` | SQLite, clips, feedback, ajustes, scorecards, proveniência e reidratação. |
| `modules/clip_adjustments.py` | Normalização temporal, snapping por palavras/segmentos, duração mínima e limites seguros. |
| `modules/video_cutter.py` | FFmpeg, validação de mídia, padding/refinamento, snapping de cena, face tracking opcional e cancelamento cooperativo. |
| `modules/job_manager.py` | Fila persistente, estados, progresso, recuperação de jobs órfãos e cancelamento. |
| `static/js/app.js` | Bancada, player, HUD, fila, inputs de Entrada/Saída, eventos em tempo real e reidratação. |
| `static/css/style.css` e `static/css/furia-tokens.css` | Design system e acabamento da bancada. |
| `tests/` | Regressões de contexto, transcrição, ranking, render, dedupe, UX, jobs, cancelamento e persistência. |
| `docs/changelog-2026-08-22.md` | Histórico detalhado e versionado das mudanças desta rodada. |
| `docs/roadmap.md` | Norte de evolução do produto. |
| `docs/ux-architecture-redesign-2026-08-22.md` | Decisões de arquitetura UX e organização da bancada. |
| `~/FuriaClipsData` | Dados persistentes fora do Git: análises, transcrições, feedbacks, learning store, checkpoints e snapshots locais. |

## 7. O que não deve ser afirmado ou feito

Não afirmar que todos os vídeos dos perfis foram analisados quando a coleta pública sofreu restrição; não contornar 401, 403, 429, CAPTCHA ou login. Não enviar nada ao Campaign Hub, mesmo que uma integração permita escrita. Não colocar chave de Gemini, chave de Manus, cookies, URLs assinadas, banco, vídeos ou transcrições privadas no GitHub, ainda que o repositório seja privado. Não tratar exemplos de Chub como labels perfeitos. Não recalibrar pesos sem decisões reais suficientes. Não reconhecer pessoas por rosto nem persistir biometria. Não declarar um momento não verbal como risada, cavalo ou música sem revisão audiovisual.

Também não misturar a pasta local do OpenShorts com o checkout do Furia Clips. O OpenShorts foi baixado pelo usuário no Windows e depende de Docker Desktop com engine Linux em execução; isso é um projeto separado.

## 8. Como manter o contexto em dois computadores

O GitHub contém o código, testes e documentação sanitizada. Ele **não contém automaticamente** o conteúdo de `~/FuriaClipsData`. Para manter aprovações, rejeições, transcrições, análises e snapshots entre os dois notebooks, o editor precisa copiar ou sincronizar essa pasta por um meio privado de sua escolha, preservando a estrutura relativa. Ao trocar o checkout pelo GitHub, os dados fora dele não são apagados, mas também não são baixados junto.

A rotina autônoma mantém checkpoints append-only em `~/FuriaClipsData/analyses/` para registrar commit, testes, limitações, privacidade e estado da pesquisa. Esses checkpoints não devem ser adicionados ao Git se contiverem dados de mídia, transcrição ou feedback bruto.

## 9. Próximos passos recomendados

A próxima melhoria deve continuar pequena, testável e documentada. As prioridades técnicas são melhorar recuperação de jobs e clareza da HUD, reduzir estados ambíguos na bancada, ampliar testes reais de cancelamento e reidratação, e somente depois avaliar otimizações de performance ou processamento por blocos para vídeos de várias horas.

A calibração do ranking com cortes aprovados/rejeitados deve esperar uma exportação real do editor. O dataset importado precisa passar pelo schema sanitizado e permanecer fora do Git. A análise pública de Renan pode continuar quando houver uma amostra verificável, mas resultados parciais devem continuar identificados como parciais.

## Referências internas e públicas

[1]: https://github.com/SAGIEV007/furia-clips "Repositório privado do Furia Clips"
[2]: https://github.com/mutonby/openshorts "OpenShorts — referência externa de long-to-short"
[3]: https://criadores.missao.org.br/garimpo "Site de criadores da Missão — referência funcional consultada pelo usuário"
[4]: https://www.instagram.com/renansantosreserva/ "Perfil público Renan Santos Reserva"
[5]: https://www.instagram.com/renansantosmbl/ "Perfil público Renan Santos MBL"

## 10. Correção posterior ao resumo

Após a consolidação inicial, foi identificada e corrigida uma borda de concorrência no JobManager: se o editor solicitasse cancelamento exatamente depois de o worker terminar seu trabalho, mas antes da atualização final do estado, o resultado pronto poderia ser rotulado como cancelado. Agora o cancelamento precisa ser verificado cooperativamente antes do trabalho irreversível; quando o worker retorna um resultado, ele é finalizado como concluído. Cancelamentos explícitos durante o trabalho continuam sendo registrados como cancelados. A regressão foi adicionada aos testes reais do JobManager.

## 11. Política de composição no ajuste manual

O re-render de um clip ajustado não consegue reconstruir automaticamente as posições faciais usadas no render original. Para evitar uma mudança visual silenciosa, o backend passou a inferir a política de preservação da composição a partir dos metadados persistidos quando o pedido não informa uma preferência explícita. Clips com `reframe_9_16`, `face_tracking` ou composição original passam a preservar o quadro da fonte por segurança; o editor ainda pode enviar uma preferência explícita quando quiser outro preset. Essa política foi coberta por regressão backend e a suíte integral chegou a 716 testes aprovados.

## 12. Proteção contra áudio em idioma inesperado

Como houve um caso de download em espanhol, a seleção pública mantém a preferência `pt-BR/pt/por` antes do fallback genérico. O resultado do importador agora também relata se o português foi confirmado pelos metadados da faixa, se houve fallback sem confirmação ou se o idioma não foi informado. O console orienta conferir o primeiro trecho quando a plataforma não provar o idioma; o Furia não afirma que o áudio é português apenas por preferir essa faixa. A mudança foi coberta por testes de seleção e transparência.

## 13. Recuperação terminal após desconexão

Após uma reconexão, a interface agora compara o job persistente que estava em andamento antes da perda de conexão com o histórico local. Se esse mesmo job terminou, falhou ou foi cancelado enquanto o navegador estava offline, a HUD deixa de ficar presa em “em andamento” e mostra o estado real. Para cortes, processo completo e ajustes individuais concluídos, os clips e a biblioteca do projeto também são atualizados. A lógica ignora jobs legados e operações concorrentes, preservando a associação entre fonte, projeto e revisão.

## 14. Confirmação de áudio pela faixa efetiva

O diagnóstico de idioma foi tornado mais conservador. O Furia não usa o idioma geral do upload para afirmar que a faixa baixada é portuguesa; só confirma português quando a própria faixa de áudio selecionada traz metadado compatível. Quando o provedor não informa a faixa, o estado permanece desconhecido ou não confirmado e o editor é orientado a conferir a reprodução.

## 15. Formato combinado e confirmação de áudio

A auditoria de áudio também considera downloads em que vídeo e áudio vêm juntos. Nessa situação, o idioma geral só é usado quando o próprio registro também declara um codec de áudio válido; um campo de idioma isolado não basta. Assim, o Furia permanece conservador sem rejeitar uma confirmação legítima de formato combinado.

## 16. Limite e sanitização dos metadados de áudio

Os metadados externos usados no diagnóstico de áudio agora são tratados como dados não confiáveis: códigos de idioma são normalizados, limitados e sanitizados antes de aparecerem no resultado, e a lista de idiomas observados também é limitada. Isso mantém a transparência sem deixar valores anormais contaminarem o console ou a interface.

## 17. Contrato de idioma no resultado do download

Além de verificar a expressão de prioridade, o teste do importador agora confere os campos do resultado real da função de download. Isso garante que a informação mostrada ao editor corresponde à faixa efetivamente devolvida pelo provedor, e não apenas à preferência configurada.

## 18. Evidência de locutor nos prompts de seleção

Para aumentar a precisão contextual, cada bloco enviado às IAs pode mostrar os turnos temporais dos locutores e suas confianças. Sem diarização, o modelo é instruído a não presumir quem fala. Isso ajuda a separar pergunta, resposta e troca de participante, mas continua exigindo revisão quando a fonte não identifica os locutores.

## 19. Recuperação de perguntas sem pontuação

Como `starts_late` foi o motivo de rejeição mais frequente na amostra local, o seletor passou a reconhecer perguntas de entrevista sem depender do ponto de interrogação. Quando a legenda começa diretamente na resposta, ele pode recuperar a pergunta anterior somente se a continuidade temporal for segura; a revisão de locutor e contexto continua obrigatória.

## 20. Detector de payoff mais conservador

Para reduzir rejeições por `no_payoff`, finais que terminam em conectivo, preposição ou pronome passaram a ser tratados como potencialmente abertos mesmo quando a pontuação da legenda parece encerrar a frase. O ranker também reduz a completude desses casos, enquanto o seletor tenta uma continuação próxima sem atravessar sobreposição, tópico ou locutor ambíguo.

## 21. Headline Studio calibrado com a legenda fiscal fornecida

A legenda exportada do CapCut foi testada diretamente. O problema não era o nome inglês do arquivo, mas a regra local que generalizava qualquer menção a imposto. O gerador agora usa claims presentes no texto, como “mais de 200 bilhões por ano”, “imposto de país rico” e revisão de despesas, sem sugerir cripto quando o corte não fala de cripto. A interface mostra a base textual usada e esclarece que o nome do arquivo não é levado em conta.

## 22. Alerta de transcrição incompleta em TXT

O Headline Studio não usa mais a ausência de ponto final como prova de que a legenda está incompleta. Isso evita o alerta falso em exportações do CapCut; o aviso permanece quando o texto realmente termina aberto, como em “porque”, “de”, “para” ou com vírgula. A legenda fornecida pelo editor foi reprocessada sem esse alerta.

## 23. Filtro de evidência no refinamento por IA

O caminho de IA do Headline Studio passou a receber os claims e termos usados pela regra local. Uma sugestão só substitui o fallback quando possui pelo menos dois sinais relevantes da legenda; variações naturais como “despesa” e “despesas” são reconhecidas, mas coincidências isoladas não. Isso reduz o risco de uma IA retornar uma frase chamativa, porém fora do contexto do corte.

## 24. Claim principal visível no Headline Studio

A interface passou a mostrar primeiro o claim mais forte usado para fundamentar a headline. No exemplo fiscal, o editor vê uma ideia concreta como “A CONTA EXIGE CORTAR MAIS DE 200 BILHÕES POR ANO”, em vez de apenas uma lista de palavras-chave.

## 25. Redação fiscal final do Headline Studio

Depois do probe com a legenda exportada do CapCut, a primeira alternativa passou a usar o contraste mais claro do próprio texto: “PAÍS POBRE COBRA IMPOSTO DE PAÍS RICO”. As demais destacam mais de 200 bilhões por ano em despesas e a necessidade de mexer nas despesas. A formulação genérica sobre “tributar o próprio futuro” foi removida desse caso.

## 26. Atribuição de locutor nas headlines

O Headline Studio deixou de inserir “RENAN” automaticamente em uma headline apenas porque o texto fala de cripto ou política. A atribuição só aparece quando o minic contexto identifica explicitamente Renan; caso contrário, o texto permanece ancorado no tema sem atribuir a fala à pessoa errada.

## 27. Formato escolhido preservado

O Headline Studio agora respeita o formato selecionado pelo editor mesmo se a IA sugerir outro formato no JSON. Isso evita uma inconsistência em que o painel poderia parecer recomendar 9:16 quando o editor havia escolhido 1:1; a IA continua responsável apenas pela redação dentro do perfil escolhido.

## 28. Fake tweet separado do minic contexto

O texto do fake tweet não mistura mais o minic contexto interno do editor com a sugestão que será copiada. Quando o locutor não foi identificado, o texto permanece impessoal; quando Renan é explicitamente confirmado, a primeira pessoa pode ser usada dentro dos fatos da legenda.

## 29. Selo superior contextual

No formato 1:1, o Headline Studio agora usa “ATENÇÃO” para uma legenda fiscal quando não há um sinal mais específico. Isso substitui o selo genérico “IMPRESSIONANTE” no exemplo fornecido e deixa a chamada superior coerente com o assunto, sem afirmar urgência nem mudar o conteúdo da headline.

## 30. Proteção contra entidades e números inventados

O refinamento por IA agora verifica nomes políticos e números antes de aceitar uma sugestão. Uma headline que introduza “Lula”, “Bolsonaro” ou um valor não mencionado no corte é descartada; “200” pode ser aceito quando a legenda diz “duzentos”. Isso protege o contexto sem impedir variações naturais da redação.

## 31. Origem do resultado sem falso refinamento

O Headline Studio agora diferencia uma sugestão realmente aceita pela IA de uma resposta que foi toda descartada pelas regras de segurança. Quando nenhuma opção passa pela validação, o sistema mantém a origem “regras editoriais”, preserva o formato escolhido e não mostra uma justificativa genérica da IA como se tivesse sido aplicada.

## 32. Identificação explícita para atribuição a Renan

Mencionar “Renan” dentro da legenda não basta para o sistema escrever como se ele fosse o autor da fala. O Headline Studio agora exige confirmação explícita no minic contexto para liberar primeira pessoa ou “Renan critica”; sem isso, a sugestão permanece temática e impessoal.

## 33. Regressão de atribuição coberta

O caso em que a IA transforma uma menção a Renan em autoria agora está protegido por teste automatizado. Sem confirmação no minic contexto, o resultado continua sendo o fallback editorial seguro.
