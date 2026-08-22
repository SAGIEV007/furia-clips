# Furia Clips — redesign total de UX e arquitetura da bancada

**Data:** 22 de agosto de 2026
**Escopo desta rodada:** arquitetura da informação, jornada editorial, organização visual, progressive disclosure, navegação contextual, estados de interface e microcopy. A lógica de seleção, ranking, transcrição, renderização e persistência técnica não foi alterada.

## Diagnóstico

A interface anterior já possuía muitas capacidades, mas apresentava quase todas na mesma página e com peso visual semelhante. Configurações de Whisper, backend de IA, pasta de saída, entrada de vídeo, contexto, pesquisa editorial, texto de arte, operações, backup, atualização, console e fila de revisão competiam pelo mesmo espaço. O resultado era tecnicamente completo, mas cognitivamente parecido com um formulário extenso.

O problema não era a ausência de cor ou de uma imagem de abertura. Era a falta de uma sequência decisória explícita. O editor precisava inferir a ordem entre importar, validar a fonte, analisar contexto, cortar, revisar e exportar. Funções que pertencem ao mesmo momento também estavam distantes: contexto, scorecard e revisão, por exemplo, precisavam parecer uma única bancada.

## Arquitetura adotada

A experiência agora é tratada como uma estação editorial com a sequência **Fonte → Contexto → Cortar → Revisar → Aprender**. A estrutura principal preserva as áreas e ids existentes, mas cria uma leitura mais clara da prioridade.

| Prioridade | Área | Decisão do editor | Tratamento |
|---|---|---|---|
| Primária | Matéria-prima | Qual vídeo será analisado? | Drop zone grande, CTA de importação e microfluxo visual. |
| Primária | Fonte da análise | Qual é a origem válida? | Upload, transcrição e link agrupados em tabs. |
| Primária | Contexto | O que está sendo dito e qual trecho tem fechamento? | Dossiê, tópicos, perguntas, hooks e alertas no mesmo espaço. |
| Primária | Cortar | Quero gerar candidatos ou executar o processo completo? | Ações editoriais reunidas em uma área de próximo movimento. |
| Primária | Revisar | O intervalo é útil, conclusivo e visualmente seguro? | Central de revisão, preview, scorecard, contexto e decisões locais. |
| Secundária | Texto de arte | Como preparar headline depois do corte? | Estúdio separado, acessível por atalho e sem competir com a seleção. |
| Secundária | Operação | O que está processando ou aguardando? | Dashboard de estados separado da ação editorial. |
| Avançada | IA e armazenamento | Como configurar o ambiente? | Seções recolhíveis com prioridade explicitamente indicada. |
| Diagnóstico | Console | O que ocorreu quando algo falhou? | Console continua disponível, mas não domina a jornada normal. |

## Alterações aplicadas

A sidebar agora possui seções `details` progressivas para **Configurações**, **Motor de IA** e **Pasta de saída**. Cada grupo mostra se é essencial, avançado ou relacionado ao destino. Isso reduz a presença inicial da complexidade sem remover controles ou mudar seus ids.

Foi criada uma rail de navegação da bancada com links para **Fonte**, **Contexto**, **Cortar**, **Revisar** e **Texto de arte**. O estado ativo acompanha a seção visível por scroll e resize, permitindo que o editor se localize mesmo em uma página longa. Os links continuam sendo âncoras simples e não substituem qualquer fluxo técnico.

O estado vazio da matéria-prima agora explica visualmente o caminho de trabalho com `01 importar → 02 entender → 03 revisar`. Isso substitui a sensação de uma caixa isolada por uma primeira orientação de produto.

A ordem visual em desktop foi definida por CSS para acompanhar a jornada sem reescrever a marcação legada: hero, workflow, atalhos, matéria-prima, fonte, preview, contexto, ações, fila de revisão, operação, texto de arte e console. A ordenação é apenas de apresentação; o JavaScript e os endpoints permanecem os mesmos.

## Sistema de decisão e disclosure

O primeiro nível da tela deve servir para iniciar e acompanhar o trabalho. Configurações de backend, modelos, chaves, sincronização e armazenamento aparecem como detalhes avançados. Essa decisão aplica progressive disclosure: a capacidade continua disponível, mas a complexidade só aparece quando é relevante.

Os cards e painéis devem explicar estado por texto, posição, forma e ícone, e não apenas por cor. A ação primária usa o acento da marca, mas a cor não significa probabilidade de viralização. A revisão continua sendo humana e os alertas continuam explícitos.

## Validação

A tela inicial foi validada em captura headless de 1440×1000. A captura confirmou o hero original, o dock flutuante, a trilha de workflow, a rail de atalhos, a drop zone e a fonte de análise em superfícies separadas. O HTML servido foi conferido para garantir a presença de `sidebar-disclosure`, `workbench-nav` e `hero-art`.

A validação técnica executou `node --check static/js/app.js`, `py_compile` para os módulos e testes e a suíte completa do projeto. Resultado: **512 testes aprovados**. O escopo deste redesign não modificou ranking, transcrição, seleção, renderização ou banco.

A próxima validação visual recomendada é capturar a mesma interface com um lote real de candidatos carregado, porque a fila de revisão é o centro operacional do produto. Esse passo deve avaliar a proximidade entre preview, contexto, scorecard e decisão, não apenas a tela inicial vazia.

## Referências de padrão

As referências foram usadas para padrões de UX, não para copiar identidade visual ou ativos. Editores como CapCut, OpusClip, Vizard, Descript e Riverside ajudam a pensar em fonte, preview, timeline, seleção e revisão [1] [2] [3] [4] [5]. Linear e Raycast são referências de navegação, command surface e hierarquia de produto [6] [7]. Grafana e Stripe ajudam a pensar em dashboards, densidade e estados [8] [9]. As heurísticas de Nielsen Norman Group orientam visibilidade de estado, consistência, prevenção de erros e reconhecimento em vez de memorização [10].

## Referências

[1]: https://www.capcut.com/tools/ai-long-video-to-short-video "CapCut — AI long video to short video"
[2]: https://www.opus.pro/ "OpusClip — AI video clipping"
[3]: https://vizard.ai/tools/ai-highlights "Vizard — AI Highlights"
[4]: https://www.descript.com/ai/find-good-clips "Descript — Find good clips"
[5]: https://riverside.com/magic-clips "Riverside — Magic Clips"
[6]: https://linear.app/now/how-we-redesigned-the-linear-ui "Linear — How we redesigned the Linear UI"
[7]: https://www.raycast.com/ "Raycast — productivity command surface"
[8]: https://grafana.com/blog/getting-started-with-grafana-best-practices-to-design-your-first-dashboard/ "Grafana — dashboard design practices"
[9]: https://stripe.com/atlas/guides/designing-a-dashboard "Stripe Atlas — dashboard design"
[10]: https://www.nngroup.com/articles/ten-usability-heuristics/ "Nielsen Norman Group — 10 usability heuristics"


## Refinamento posterior

A validação mostrou que a regra mobile herdada podia deixar o dock fora da viewport. O breakpoint foi corrigido para transformar a sidebar em painel superior rolável, mantendo a bancada acessível em 390px. O estado vazio da matéria-prima também ganhou um microfluxo de três etapas.

Dentro das configurações essenciais, detalhes de baixa frequência — pausa mínima, idioma, fonte de transcrição, gênero, perfil editorial, conta histórica e correção com IA — foram reunidos em `Ajustes avançados`, com disclosure próprio. O motor de IA e a pasta de saída continuam em grupos independentes. A intenção é que o editor encontre primeiro o que precisa para começar, sem perder acesso às opções avançadas.
