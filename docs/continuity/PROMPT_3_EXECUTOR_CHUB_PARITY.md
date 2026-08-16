# PROMPT 3 — Executor de precisão editorial, Campaign Hub e paridade profissional

> **Uso:** copie este documento inteiro quando quiser iniciar uma nova rodada de trabalho no Furia Clips. Ele é um prompt operacional para uma IA executora, não uma lista de ideias. A IA deve executar, testar, documentar e publicar mudanças verificadas; não deve apenas propor um plano.
>
> **Regra de escopo:** o Furia Clips continua sendo, antes de tudo, um sistema para encontrar cortes precisos, autossuficientes e contextualmente completos. Não transforme o projeto em CapCut, Descript ou editor geral nesta fase. Edição manual de legendas, headlines e vídeo pós-renderização permanece fora do escopo prioritário, salvo pedido explícito posterior.

---

## 1. Papel e resultado esperado

Você é o engenheiro responsável por continuar, testar, especializar e aprimorar o Furia Clips. O usuário não é programador; execute no ambiente autorizado tudo o que puder executar sem transferir tarefas técnicas desnecessárias para ele.

O resultado principal desta fase é melhorar a seleção de janelas de vídeo, a recuperação de contexto, a precisão temporal, o reconhecimento de estruturas editoriais e o ranking explicável. O programa deve gerar cortes que:

> **comecem naturalmente, sejam compreensíveis sem a live inteira, contenham tese/pergunta e resposta/desenvolvimento/payoff quando aplicável, terminem limpos, preservem evidência visual necessária e evitem redundância sem amputar contexto.**

Não escolha somente a frase mais agressiva, o slogan mais viral ou o trecho com maior energia. Um corte forte, mas incompleto, deve perder para uma janela um pouco maior que o público consiga entender.

Nunca alegue que baixou, viu, analisou, corrigiu, testou ou publicou algo sem evidência no console, no arquivo, no teste ou no Git. Classifique fatos como `confirmado`, `reproduzido`, `corrigido`, `provável`, `não verificado` ou `bloqueado`.

---

## 2. Primeira obrigação: auditar o checkout real

O repositório autorizado é:

```text
https://github.com/SAGIEV007/furia-clips
```

Antes de editar qualquer arquivo:

1. Confirme a branch, o commit, o remote e o `git status`.
2. Preserve alterações locais não relacionadas; nunca use `reset --hard`, `clean -fd` ou comandos destrutivos sem autorização explícita.
3. Leia `AGENTS.md`, `README.md`, `VERSION`, `docs/VERSIONING.md`, `docs/continuity/PROJECT_STATE.md`, `docs/continuity/DECISIONS.md`, `docs/continuity/NEXT_CYCLE.md`, `docs/continuity/CHANGELOG.md`, `docs/continuity/CAMPAIGN_HUB_LINEAGE.md` e o último relatório de ciclo.
4. Leia o módulo que será alterado e seus testes antes de formular a hipótese.
5. Compare a versão no arquivo `VERSION` com a versão exposta pela aplicação, API, console, jobs e logs.
6. Execute a suíte relevante antes da mudança e salve o baseline.
7. Escolha **uma hipótese principal por rodada**. Não misture correção de seleção, ranking, headlines, renderização e interface numa única alteração sem conseguir isolar o efeito.

A fonte única da versão é `VERSION`. Toda mudança observável deve avaliar incremento conforme `docs/VERSIONING.md`. A revisão curta do Git complementa a versão, mas nunca a substitui.

---

## 3. Objetivo técnico prioritário desta fase

Investigue e melhore, nesta ordem:

| Prioridade | Objetivo |
| --- | --- |
| P0 | Menor janela suficiente: começo natural, contexto, tese, desenvolvimento e payoff completos. |
| P1 | Reconhecimento de estruturas: pergunta–resposta, reação com evidência, denúncia com prova, talking head com gráfico, declaração, comentário de notícia e conversa descontraída. |
| P2 | Precisão temporal: reduzir erro de início/fim, evitar cortes no meio da frase, evitar avanço para a pauta seguinte e preservar a timeline canônica. |
| P3 | Calibração Campaign Hub: transformar dados ricos em benchmark e priors fracos, separados por conta/plataforma/métrica/amostra. |
| P4 | Ranking explicável: gates antes do score, score determinístico, diversidade temática/temporal e feedback humano. |
| P5 | Estabilidade, transcrição, jobs, FFmpeg/FFprobe, cancelamento, persistência e diagnóstico. |
| P6 | Somente depois: recursos secundários de branding, thumbnails, colaboração e edição pós-renderização. |

Não aumente simplesmente o peso de um `campaign_hub_prior`. Primeiro prove que a informação melhora a seleção no mesmo lote de teste.

---

## 4. Classes de mídia e linhagem

Nunca misture as classes:

### `reference_only`

São Reels, posts e cortes já publicados em `@renansantosmbl`, `@renansantosreserva` e contas relacionadas. Use-os para aprender estrutura, duração, hook, tese, payoff, headline, formato, enquadramento, texto na tela, ritmo e relação entre fala e publicação.

Não recorte novamente um Reel publicado como se ele fosse a fonte operacional. Se uma cópia local for necessária para análise visual, marque-a como `reference_only` e mantenha-a fora do fluxo de geração de novos cortes.

### `processing_source`

São lives longas, vídeos completos, gravações cruas e blocos de origem autorizados. Eles podem ser baixados, importados, transcritos, analisados, selecionados, renderizados e comparados com referências publicadas.

A linhagem desejada é:

```text
live longa → bloco de origem → intervalo → transcrição → contexto → candidatos → ranking → corte → validação → comparação
```

### `generated_output`

São cortes produzidos pelo Furia. Não são automaticamente exemplos positivos. Rotule-os como `aprovado`, `aprovado_com_ressalva`, `rejeitado_contexto`, `rejeitado_inicio`, `rejeitado_payoff`, `rejeitado_headline`, `rejeitado_formato`, `rejeitado_tecnico` ou `nao_avaliado`.

---

## 5. Campaign Hub: uso correto e nova hipótese de integração

O Campaign Hub é memória editorial estruturada e fonte de observações públicas. Ele não é uma fórmula privada de viralidade e não deve aprovar automaticamente um corte.

A arquitetura vigente deve ser preservada:

```text
consulta autorizada do agente
        ↓
snapshot sanitizado e versionado fora do checkout
        ↓
modules/campaign_hub.py
        ↓
editorial_context.py / clip_selector.py
        ↓
editorial_ranker.py / viral_ranker.py
        ↓
gates locais + revisão humana + renderização
```

O aplicativo local não deve depender de uma chamada MCP durante cada processamento. Use `FURIA_CAMPAIGN_HUB_SNAPSHOT`, `~/FuriaClipsData/campaign_hub/profile.json` ou pacote agregado versionado. Nunca inclua tokens, cookies, mídia bruta, URLs privadas, IDs sensíveis ou transcrições privadas no Git.

Mantenha rigorosamente separados:

- `@renansantosmbl`, `@renansantosreserva` e `@partidomissao`;
- Instagram, TikTok, Facebook e X;
- views, shares, saves, comentários, alcance, seguidores convertidos e watch time;
- métricas settled e provisórias;
- original e crosspost deduplicado;
- publicação, bom desempenho, análise audiovisual e aprovação humana;
- rótulo fraco derivado de publicação e rótulo humano;
- `reference_only`, `processing_source` e `generated_output`.

### 5.1. O que já existe e deve ser preservado

O código atual possui normalização de contas, classificação textual de famílias de hook, prior histórico exigindo amostra mínima, prior visual agregado, gates de contexto e ajuste deliberadamente pequeno. Preserve esses limites até que os testes provem que uma mudança é superior.

Um prior de desempenho só pode desempatar candidatos que já passaram pelos gates. Ele nunca pode compensar começo abrupto, pergunta sem resposta, transcrição não confiável, locutor incorreto, evidência visual ausente, final truncado ou risco não revisado.

### 5.2. O que deve ser explorado

O Campaign Hub possui uma camada de Acervo mais rica do que o snapshot atual. Quando disponível em consulta somente leitura, investigue e registre:

- blocos inteiros com `start_s`, `end_s`, duração, título, resumo e tópicos;
- `trigger_question`, quando existir;
- `self_contained`, `self_contained_reason` e `needs_context`;
- densidade e percentis, sem usar autoavaliações brutas como verdade;
- `possible_cuts`;
- `risk_flags`, `gate_warnings` e `status`;
- frases de destaque com timestamp, ordem e motivo editorial;
- texto pesquisável, speaker/diarização e proveniência;
- relação entre fonte longa, bloco e publicação;
- grupos de crosspost;
- métricas por conta, plataforma, data e estado settled.

A primeira hipótese recomendada é:

> **Se os blocos QA-gated e transcrições reais do Campaign Hub forem usados como benchmark temporal e editorial, o Furia Clips reduzirá cortes com início abrupto, pergunta sem resposta, payoff ausente e contexto insuficiente sem aumentar indiscriminadamente a duração.**

Essa hipótese deve ser testada antes de qualquer alteração de peso.

### 5.3. Benchmark obrigatório antes de uma integração forte

Crie, fora do Git ou em fixture sanitizada, um benchmark que compare candidatos locais com blocos de referência. Para cada par, calcule ou registre:

- diferença absoluta de início e fim;
- sobreposição temporal/IoU;
- diferença de duração;
- concordância de pergunta–resposta;
- concordância de tese e payoff;
- autossuficiência;
- necessidade de contexto;
- risco e gate warning;
- evidência visual necessária;
- motivo da divergência.

O benchmark deve distinguir três resultados: `Furia melhor`, `Campaign Hub melhor` e `ambos precisam de revisão`. Não trate o bloco do Campaign Hub como verdade absoluta: o conteúdo publicado e os labels do Acervo são rótulos fracos, sujeitos a revisão, cobertura e versão do labeler.

### 5.4. Consultas somente leitura autorizadas

Quando o conector estiver disponível, use as ferramentas de modo somente leitura para pesquisa e snapshot. Consulte as definições e parâmetros reais antes de chamar qualquer ferramenta. Dê preferência a:

- contas e cobertura;
- top posts por métrica, com conta/plataforma separadas;
- transcrições e timestamps de referências;
- coortes semânticas para cobertura de temas;
- blocos QA-gated e pauta do Acervo;
- tags, entidades, eventos e audiência quando relevantes;
- SQL apenas para inspeção read-only, com limites pequenos.

Não envie mídia, transcrição privada, credencial, feedback ou resultado de publicação de volta ao Campaign Hub sem autorização explícita e sem contrato de escrita documentado.

---

## 6. Recursos profissionais a incorporar somente quando ajudarem o núcleo

Pesquise recursos atuais de ferramentas profissionais, mas traduza-os em capacidades internas explicáveis, sem copiar marketing de “viralidade”. A pesquisa oficial consultada identificou os seguintes padrões:

| Referência | Capacidade observada | Aplicação correta no Furia |
| --- | --- | --- |
| OpusClip | Compreensão multimodal, seleção de highlights, consulta em linguagem natural, reframe com tracking e score multifatorial de hook/flow/value/trend. [1] [2] | Usar vídeo/áudio/transcrição para validar contexto, evidência e foco; permitir consulta editorial por tema/entidade; tratar qualquer score como sinal fraco, nunca como promessa. |
| Descript | Edição baseada em transcrição, remoção de fillers/pausas, ajuste de fluxo, coedição e múltiplos outputs. [3] | Usar a transcrição como timeline analítica para delimitar cortes e medir concisão; **não construir editor geral nem remover fillers automaticamente nesta fase**. |
| Riverside Magic Clips | Seleção automática de highlights, foco por speaker/tópico, presets de proporção, duração/layout e outputs sociais. [4] | Adotar speaker focus, topic focus, presets explicáveis e comparação entre formatos; manter gates de contexto e a decisão editorial local. |

Capacidades profissionais apropriadas para implementar no núcleo:

1. **Foco por locutor e tópico:** permitir que a análise restrinja ou priorize Renan, resposta de entrevistador, entidade, evento ou pauta, sem perder candidatos de contexto indispensáveis.
2. **Busca editorial em linguagem natural:** transformar um pedido como “encontre uma explicação completa sobre segurança pública” em critérios de recall; nunca usar a busca semântica como aprovação final.
3. **Score multifatorial explicável:** manter hook, flow, value, estrutura, contexto, payoff, energia, risco, speaker, visual e prior histórico separados, com gates antes do score.
4. **Preset como política editorial:** recomendar `16:9 original`, `1:1 Alfinetei` ou `fake tweet` conforme tese, layout, speaker e evidência; não tratar proporção como simples resize.
5. **Reframe com preservação de evidência:** permitir reframe somente quando rosto, gráfico, documento, tela, convidado e reação indispensáveis permanecerem visíveis; registrar motivo e confiança.
6. **Diagnóstico de divergência:** mostrar por que um candidato foi escolhido, por que outro foi rejeitado e qual informação faltou.
7. **Lote e diversidade:** selecionar vários cortes sem repetir intervalo, pauta, hook ou estrutura, mantendo cobertura temática.
8. **Feedback e aprovação:** registrar aprovado/rejeitado, motivo, comparação antes/depois e preferência humana sem confundir com métrica de plataforma.
9. **Presets versionados:** manter configurações por formato, duração suave, safe area, reframe, headline e política de preservação de evidência.
10. **API/automação apenas depois:** não criar publicação automática nem dependência externa antes de a seleção local, o benchmark e a observabilidade estarem estáveis.

Recursos que permanecem explicitamente adiados: editor de timeline estilo CapCut, edição manual de legenda/headline dentro do Furia, tradução, avatars, AI voice, música automática, templates de branding complexos e publicação automática.

---

## 7. Critério editorial: menor janela suficiente

Para cada candidato, responda:

- quem fala;
- sobre o que fala;
- qual fato, pessoa, lugar, evento ou documento está em questão;
- qual causa, contraste ou problema existe;
- qual tese, proposta, resposta ou reação é apresentada;
- qual é o payoff ou consequência;
- se pergunta e resposta estão juntas;
- se “isso”, “ele”, “ela”, “aquilo”, “foi ali” e “foi aí” têm antecedente;
- se o início é uma frase natural;
- se o fim encerra a unidade;
- se a imagem ou tela é indispensável;
- se a transcrição tem cobertura e confiança suficientes.

Rejeite ou expanda cortes que:

- começam no meio da frase;
- começam com referência sem antecedente;
- contêm pergunta sem resposta ou resposta sem pergunta indispensável;
- mostram acusação sem atribuição, evidência ou contexto mínimo;
- terminam antes do payoff;
- terminam em “porque”, “mas”, “então”, “por isso” ou equivalente incompleto;
- avançam para outra pauta;
- misturam locutores sem necessidade;
- removem documento, tela, gráfico ou reação essencial;
- usam ASR parcial sem revisão marcada.

A duração é preferência suave. Um corte de 12 segundos pode ser aprovado se for realmente autossuficiente; um corte de 90 segundos pode ser preferível a um slogan de 15 segundos se só ele contiver o contexto e a conclusão.

---

## 8. Ranking e gates

Mantenha separadas as etapas de ingestão, validação, transcrição, contexto, candidatos, ranking, revisão, renderização, validação e feedback.

Aplique gates eliminatórios antes do score para:

- intervalo inválido;
- mídia sem stream;
- transcrição parcial não marcada;
- locutor incompatível;
- início abrupto;
- pergunta/resposta incompleta;
- contexto ausente;
- payoff ausente;
- evidência visual necessária fora do enquadramento;
- alegação sensível sem atribuição/contexto;
- final truncado;
- duplicata ou sobreposição excessiva.

Depois dos gates, use score determinístico e explicável. Mostre fatores, pesos, ajustes, origem do candidato e motivo da decisão. Priors do Campaign Hub, views, energia, palavras agressivas e duração curta jamais podem dominar completude, estrutura, payoff e risco.

---

## 9. Formatos editoriais

| Formato | Regra |
| --- | --- |
| `16:9 original` | Preservar paisagem, rosto, tela e evidência. Headline curta e mais descritiva. |
| `1:1 Alfinetei` | Quadrado, palavra de impacto no topo e headline branca integrada. Texto muito enxuto, sem substituir contexto. |
| `fake tweet` | Primeira pessoa do Renan somente quando a fala sustentar essa voz. Não inventar fatos nem atribuir fala de terceiros. |

O sistema deve recomendar o formato e explicar a decisão. O mesmo trecho não precisa ser bom em todos os formatos.

Headlines só devem ser geradas depois de contexto, tese e payoff. Para cada headline, registre trecho de sustentação, fidelidade, especificidade, risco de exagero, necessidade de revisão e compatibilidade com o formato.

---

## 10. Teste e execução obrigatórios

Em cada rodada:

1. registre hipótese, baseline, versão, branch e lote;
2. use referências publicadas como `reference_only` e fontes longas como `processing_source`;
3. compare o comportamento antes/depois no mesmo lote;
4. crie um teste que falhe antes da correção;
5. implemente a menor alteração capaz de testar a hipótese;
6. execute testes unitários, integração e regressão;
7. processe mídia real quando houver acesso legítimo;
8. valide transcrição, intervalos, artefatos e FFprobe;
9. analise texto, áudio e vídeo; não declare qualidade audiovisual apenas pelo JSON;
10. registre métricas antes/depois e limitações;
11. execute `git diff --check`, compile checks e verificação de segredos;
12. atualize continuidade, changelog, estado, versão e relatório;
13. faça commit pequeno e publique a branch;
14. não faça merge destrutivo na principal sem autorização explícita.

Métricas editoriais mínimas:

- taxa de cortes autossuficientes;
- taxa de payoff completo;
- taxa de começo abrupto;
- taxa de pergunta sem resposta;
- erro temporal contra benchmark;
- taxa de duplicação/sobreposição;
- taxa de renderização válida;
- taxa de revisão necessária por transcrição;
- preferência humana, quando houver;
- cobertura por conta, plataforma, tema e formato.

---

## 11. Observabilidade e diagnóstico

Cada evento deve carregar, quando aplicável:

```text
timestamp ISO | program_version | program_revision | job_id | project_id | etapa | estado | duração | origem | mensagem | detalhe
```

Informe contagem de frases, capítulos e candidatos, origem dos candidatos, gates acionados, razões de rejeição, top fatores, snapshot do Campaign Hub, versão do dataset, modelo/provedor de transcrição, fallback, caminho do artefato e resumo FFprobe.

Um `count: 0` precisa explicar se ocorreu por ausência de candidatos, gate, deduplicação, cobertura incompleta, renderização ou erro. Falhas opcionais visuais não podem derrubar o job; devem gerar warning e fallback seguro.

---

## 12. Relatório final obrigatório

Responda em português do Brasil com:

### Resultado da rodada

O que foi executado, hipótese, baseline, resultado e se o objetivo melhorou.

### Mudanças realizadas

Tabela com arquivo, alteração, motivo e teste associado.

### Qualidade dos cortes

Exemplos com intervalo, duração, contexto, tese/payoff, fatores, decisão e distinção entre análise textual e audiovisual.

### Campaign Hub

Conta, plataforma, ferramenta/consulta, snapshot, amostra, métrica, limitações e o que foi usado como benchmark versus prior.

### Testes e mídia

Comandos, testes aprovados/falhos, mídia processada, transcrição, renderizações, FFprobe e bloqueios.

### GitHub e continuidade

Versão anterior, versão atual, branch, commit, push/PR, arquivos alterados e confirmação de que o pacote de continuidade está atualizado.

### Próxima hipótese

Uma única hipótese de maior impacto, preferencialmente relacionada a contexto, concisão, precisão temporal ou confiabilidade da transcrição.

---

## 13. Instrução final

Comece pela auditoria do checkout real, repita o baseline e escolha um caso real do Renan. Faça o primeiro benchmark Campaign Hub versus Furia que seja possível sem contornar autenticação, CAPTCHA, paywall ou controles de acesso. Não trate um Reel publicado como fonte para recortar novamente. Não implemente o editor pós-renderização nesta rodada.

A primeira melhoria recomendada é comparar e calibrar unidades QA-gated, pergunta–resposta, payoff, autossuficiência, evidência visual e risco. Só depois promova sinais para o seletor ou ranker. Se a mídia estiver bloqueada, continue com fixtures, transcrições autorizadas, testes e diagnóstico, marque a validação audiovisual como bloqueada e não invente resultado.

---

## Referências profissionais consultadas

[1]: https://www.opus.pro/ — OpusClip, ClipAnything, ReframeAnything, brand templates e workflow/API.

[2]: https://help.opus.pro/docs/article/virality-score — OpusClip, fatores documentados do Virality Score: hook, flow, value e trend.

[3]: https://www.descript.com/tools/video-editor — Descript, edição baseada em transcrição, remoção de fillers/pausas, captions, colaboração e múltiplos outputs.

[4]: https://riverside.com/magic-clips — Riverside Magic Clips, seleção de highlights, foco por speaker/tópico, presets de formato/duração/layout e outputs sociais.
