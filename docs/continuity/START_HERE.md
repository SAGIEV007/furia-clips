# START_HERE — Furia Clips Renan-first

> **Este é o ponto de entrada canônico para qualquer nova IA que continuar o Furia Clips.** Leia este arquivo antes de alterar código. Ele substitui, como instrução de entrada, os antigos Prompts 1, 2 e 3. Os arquivos antigos permanecem no repositório como histórico, mas não devem ser tratados como o prompt vigente.

## 1. Missão do projeto

Você está continuando o projeto **Furia Clips**, repositório `https://github.com/SAGIEV007/furia-clips`. O Furia é uma ferramenta local de clipping automático especializada em encontrar cortes do universo **Renan Santos/MBL**.

O objetivo não é criar um editor geral parecido com CapCut. O objetivo principal é transformar vídeos longos, lives, entrevistas, eventos e arquivos MP4 em **cortes precisos, autossuficientes, contextualizados e editorialmente úteis**, com começo natural, desenvolvimento suficiente, tese ou resposta compreensível e encerramento com payoff.

> **Regra de prioridade:** precisão de contexto e de intervalo vem antes de quantidade de cortes, formatos sociais, headlines, facetracking, branding ou edição pós-renderização.

O usuário não é programador. Execute no ambiente autorizado tudo o que puder executar, explique os resultados em português simples, não transfira desnecessariamente tarefas técnicas ao usuário e nunca declare uma função pronta apenas porque existe uma rota, uma tela ou um módulo com esse nome.

## 2. Estado real conhecido — não confundir código com produto pronto

A branch de trabalho conhecida é `manus/rebuild-opus-parity`. O baseline documental anterior era a versão `1.9`, commit `40c78b1`, uma fase predominantemente documental e operacional. O Furia contém muitas peças do pipeline, mas ainda não oferece uma experiência diária equivalente ao Garimpo + Campaign Hub.

A validação prática mais recente foi feita a partir de um clone limpo do GitHub. As dependências foram instaladas, o modelo oficial pequeno de facetracking foi baixado apenas para satisfazer o teste de asset e a suíte terminou com **306 testes aprovados**. O modelo não deve ser incluído no Git se o repositório já o trata como asset externo; mantenha o fallback offline e registre a ausência de asset quando ela for relevante.

O caso real usado nesta auditoria foi o arquivo MP4 do vídeo `Primeiro ato de Campanha - Renan Santos Presidente`, baixado do fluxo de blocos do ecossistema Missão:

| Item | Resultado verificado |
| --- | --- |
| Duração da fonte local | aproximadamente 553,527 segundos, ou 9m14s |
| Resolução e aspecto | 1920×1080, 16:9 original |
| Codec | H.264 com áudio AAC |
| Upload no Furia | funcionou pela rota local de upload |
| Transcrição | Whisper local; 121 segmentos no segundo ciclo e 126 no primeiro |
| Seleção e renderização | job concluído; 7 cortes no segundo ciclo e 8 no primeiro |
| Saídas | arquivos H.264, 1920×1080, aspecto original preservado |
| Identidade audiovisual | Vinicius Poit aparece no abre; Kim Kataguiri fala nos discursos; Renan é apresentado e homenageado, mas não fala ao microfone nos intervalos testados |
| Q&A | não havia pergunta e resposta; era um comício com discurso e reação do público |
| Reprodutibilidade | o mesmo arquivo e parâmetros produziram conjuntos diferentes de candidatos entre os ciclos |

O resultado demonstra que o Furia atual **consegue receber um MP4, transcrever, selecionar e renderizar arquivos válidos**, mas ainda não consegue contextualizar esse evento com a riqueza que o usuário espera. No segundo ciclo, os candidatos foram principalmente trechos de Kim e do abre, apesar de o pedido ser Renan-first. Os objetos persistidos mantiveram `speaker_boundary_score=50` e `question_answer_complete=false`, ou seja, o sistema não tinha identificação confiável do locutor nem uma estrutura real de pergunta–resposta.

O snapshot local do Campaign Hub usado pelo Furia tinha apenas **12 observações de hooks por conta, zero exemplos e zero coortes** para as contas principal e Reserva. Isso está muito distante de uma memória editorial completa.

A tentativa de consultar o link público do YouTube pelo endpoint de probe retornou HTTP 400 porque o `yt-dlp` encontrou a proteção do YouTube “Sign in to confirm you’re not a bot”. Isso é uma limitação de acesso do downloader naquele ambiente, não uma prova de que o vídeo seja privado. O fluxo por MP4 local funcionou. A entrada por link precisa de fallback, diagnóstico e reaproveitamento de fonte; não pode ser considerada robusta sem teste real.

## 3. O que são o Campaign Hub, o Garimpo e o Furia

**Campaign Hub** e **Garimpo** pertencem ao ecossistema Missão e estão interligados. O Garimpo é a experiência de trabalho por blocos: recebe ou encontra uma fonte, separa o vídeo em unidades compreensíveis, mostra resumo e momentos fortes e permite escolher um intervalo. O Campaign Hub mantém a memória editorial, as transcrições, os blocos QA-gated, os destaques, os riscos, a proveniência e os dados de desempenho.

O **Furia Clips é um projeto separado**. Ele não possui vínculo automático com o Garimpo nem com o Campaign Hub. A autorização de acesso ao Campaign Hub existe para melhorar o Furia, mas essa integração precisa ser construída de forma explícita.

O screenshot e o fluxo observado no Garimpo servem como referência de experiência:

> **Fonte longa → linha de blocos → bloco selecionado → resumo e momentos fortes → escolha do intervalo → download seletivo.**

O Furia deve implementar uma experiência própria e mais completa, que também funcione com **MP4 enviado pelo usuário**, não somente com vídeos já presentes no Garimpo.

Não contorne autenticação, CAPTCHA, paywall ou área administrativa. Se a área interna do Garimpo não estiver acessível, registre como bloqueada e use somente o que foi autorizado, o screenshot fornecido, o código do Furia e as consultas de leitura do Campaign Hub.

## 4. Arquitetura econômica do Campaign Hub

O usuário tem um notebook com aproximadamente 500 GB e não quer baixar uma cópia integral de todos os vídeos. A solução recomendada é uma **memória editorial local leve**, não uma cópia de toda a mídia.

O caminho preferencial é:

```text
consulta de leitura autorizada
        ↓
exportador incremental e paginado
        ↓
snapshot local sanitizado, compactado e versionado
        ↓
modules/campaign_hub.py
        ↓
contexto, candidatos, ranking e revisão local
```

O programa diário não deve chamar o MCP a cada corte. O Furia precisa funcionar offline com a última memória local válida. Um canal de atualização pode existir para o agente ou para uma ação administrativa explícita, mas o job normal não pode depender de uma chamada externa.

O snapshot local deve guardar, quando disponível:

| Camada | Conteúdo mínimo | Cuidados |
| --- | --- | --- |
| Proveniência | conta, plataforma, vídeo, URL pública, data, origem, versão do exportador | Nunca misturar contas silenciosamente. |
| Texto | transcrição, timestamps, segmentos, qualidade e origem | Legenda automática é evidência, não citação perfeita. |
| Estrutura | bloco, início, fim, duração, título, resumo, tópicos, trigger question | Preservar a relação com a fonte longa. |
| Editorial | autossuficiência, necessidade de contexto, payoff, highlights, motivos e riscos | Usar como benchmark e sinal, não como aprovação automática. |
| Desempenho | views, shares, saves, comentários, alcance, watch time e proporções | Separar conta, plataforma, crosspost e settled/provisório. |
| Feedback | aprovado, rejeitado, ajustado e motivo | Diferenciar aprovação humana de publicação e métrica. |
| Manifesto | data da coleta, páginas, cursor, contagens, falhas e hash | Permitir atualização incremental e auditoria. |

Não guardar mídia bruta, cookies, tokens, transcrições privadas ou URLs privadas no Git. Para economizar espaço, guarde textos, timestamps, metadados, hashes e pequenas amostras autorizadas; não baixe novamente uma fonte longa quando um arquivo ou bloco local já estiver disponível.

As contas podem contribuir juntas para uma memória **Renan-first**, mas a proveniência continua separada:

- `@renansantosmbl` e `@renansantosreserva` podem ser usados juntos para reconhecer padrões de fala, temas e estrutura editorial;
- métricas, públicos, amostras e baselines nunca devem ser somados como se fossem uma única conta;
- `@partidomissao` deve permanecer separado e ser usado apenas quando fizer sentido;
- ausência de TikTok na Reserva significa fora do escopo, não zero;
- X pertence à conta principal e deve conservar sua proveniência específica.

## 5. Primeira entrega funcional obrigatória

A ordem do produto deve ser esta:

| Ordem | O que precisa acontecer |
| --- | --- |
| 1 | Receber uma URL pública ou um arquivo MP4 e verificar a fonte. |
| 2 | Reutilizar uma transcrição timestampada fornecida pelo usuário quando existir. |
| 3 | Se não houver transcrição, escolher o melhor caminho testado entre Whisper local e Gemini; o caminho local deve continuar funcionando sem custo externo. |
| 4 | Criar pré-análise por blocos antes de gerar todos os cortes. |
| 5 | Mostrar cada bloco com início, fim, duração, resumo, tema, locutor provável, confiança, riscos e motivo editorial. |
| 6 | Permitir assistir ao bloco e ajustar início/fim. |
| 7 | Baixar ou exportar somente o intervalo escolhido quando a fonte permitir; se não permitir, baixar a fonte uma vez, reutilizá-la e explicar o fallback. |
| 8 | Dentro do bloco, gerar candidatos automáticos com critérios de qualidade. |
| 9 | Priorizar a fala do Renan quando ele estiver presente, mas nunca atribuir a ele uma fala de Kim, entrevistador ou convidado. |
| 10 | Renderizar primeiro no aspecto original, validar com FFprobe e registrar tudo para revisão. |

A quantidade de cortes não é fixa. “Todos os cortes” significa **todos os candidatos que passarem pelos critérios**, com diversidade e sem repetição. Uma entrevista curta pode gerar poucos cortes; uma live longa pode gerar mais. Nunca aumentar a quantidade apenas para atingir um número.

## 6. Download seletivo de blocos

O teste comprovou que o Furia atual possui upload local, ingestão por URL, transcrição e corte, mas **não possui download seletivo de um bloco de origem**. As rotas de intervalo existentes são de cortes derivados, não de obtenção seletiva da fonte.

Essa é uma prioridade P0/P1. O novo fluxo deve:

1. criar um manifesto da fonte inteira e do bloco selecionado;
2. usar `start` e `end` em segundos na timeline original;
3. aplicar uma margem pequena para não cortar áudio ou palavra nas bordas;
4. testar se a fonte permite busca/range/segmentação;
5. baixar somente o intervalo quando isso for tecnicamente confiável;
6. caso contrário, baixar a fonte completa uma única vez, armazená-la temporariamente e recortar localmente;
7. reutilizar o arquivo já baixado em vez de repetir a transferência;
8. informar claramente qual caminho foi usado;
9. permitir reprocessar apenas o bloco sem reanalisar quatro horas;
10. validar que o intervalo baixado corresponde ao bloco solicitado.

Não prometa “download por intervalo” para todo provedor antes de testar. A implementação deve ter fallback seguro e mensagens simples.

## 7. Transcrição, contexto e reconhecimento de fala

A ordem de confiança da transcrição é:

> **transcrição timestampada fornecida pelo usuário → melhor fonte automática validada entre Whisper local e Gemini → fallback local com revisão explícita.**

A transcrição fornecida deve ser a timeline canônica e nunca deve ser silenciosamente substituída por Whisper. Toda transcrição precisa informar origem, cobertura temporal, qualidade, número de segmentos e se exige conferência humana.

Para vídeos longos, não envie o arquivo inteiro ao Gemini por padrão. Primeiro extraia áudio/transcrição e divida em blocos. Use uma cópia compactada e temporária somente quando a visão, a troca de locutor, o texto em tela ou a evidência visual forem necessários. Nunca destrua ou substitua o original.

O reconhecimento do Renan deve evoluir em camadas:

1. identificação manual ou fornecida pelo usuário;
2. diarização e mudança de turno;
3. referência audiovisual e voz conhecida, quando houver dados autorizados;
4. confirmação por texto, imagem, palco e contexto;
5. confiança explícita e revisão humana quando a identificação for incerta.

Não trate `speakerChange` de uma legenda automática como identidade. Um bloco pode ser sobre Renan sem ser fala de Renan. O caso b354 comprovou isso: o Acervo classificou `renanSpeaking=false` e o orador audiovisual foi Kim.

## 8. Critérios de corte Renan-first

Antes do score, responda:

- Quem fala?
- O Renan está falando, aparecendo ou apenas sendo mencionado?
- Qual é o tema, a tese, o conflito, a proposta ou a consequência?
- Há pergunta e resposta? Se sim, ambas estão presentes?
- A pessoa, lugar, evento, número ou documento tem antecedente?
- O início é natural ou começa no meio da frase?
- O fim encerra o pensamento ou corta antes do payoff?
- O público entenderá o trecho sem assistir à live inteira?
- A imagem, tela, documento, reação ou enquadramento é necessária?
- A transcrição cobre o intervalo inteiro?
- Há risco factual, jurídico, linguagem ofensiva ou ataque pessoal?

Rejeite, expanda ou marque para revisão quando houver referência sem antecedente, pergunta sem resposta, resposta sem pergunta indispensável, mistura de locutores sem necessidade, acusação sem contexto, final truncado, transcrição parcial ou evidência visual ausente.

Um hook agressivo nunca pode compensar locutor errado ou contexto insuficiente. Priors do Campaign Hub, views, energia, palavras virais e duração curta só podem desempatar candidatos que já passaram pelos gates.

## 9. Campaign Hub como benchmark antes de peso

A primeira integração rica não deve aumentar pesos do ranking diretamente. Ela deve construir um benchmark read-only entre candidatos locais e unidades do Acervo.

Para cada comparação, registre:

| Medida | Pergunta |
| --- | --- |
| Erro temporal | O início/fim local está perto da unidade de referência? |
| Sobreposição/IoU | Os intervalos cobrem o mesmo conteúdo? |
| Duração | O Furia ficou excessivamente curto ou longo? |
| Locutor | A fala foi atribuída à pessoa correta? |
| Contexto | A unidade é autossuficiente? |
| Estrutura | A pergunta, resposta, tese e payoff estão presentes? |
| Risco | O candidato exige revisão factual, jurídica ou de linguagem? |
| Evidência | A tela, documento, rosto ou reação essencial permaneceu? |
| Resultado | Furia melhor, Campaign Hub melhor ou ambos precisam de revisão? |

O Acervo também pode estar errado, incompleto ou baseado em legenda automática. Não trate seus blocos como verdade absoluta. Use `densityRank` e `selfContainedRank`, não os valores brutos de autoavaliação. Preserve versão do labeler, origem, tier de confiança e avisos de gate.

## 10. Formatos editoriais

### Fase inicial: 16:9 original

O primeiro objetivo é precisão. Preserve aspecto, enquadramento, rosto, tela, documento e contexto visual. O usuário pode ajustar 1:1 ou 9:16 no CapCut depois.

### Fase posterior: 1:1 e 9:16

Só avance depois que a seleção e os limites temporais estiverem comprovadamente bons. Facetracking e reframe devem preservar evidência, não apenas centralizar o rosto. Em eventos com público, múltiplos oradores e bandeiras, o enquadramento original pode ser a decisão correta.

### Fake tweet

> **Regra permanente:** todo fake tweet é escrito em primeira pessoa do Renan, mesmo quando outra pessoa fala no trecho.

Isso não autoriza inventar que Renan disse algo que não disse. O texto deve ser uma simulação editorial contextualizada, fiel aos fatos e ao tom pedido pelo usuário. Registre se o trecho sustenta a voz, qual evidência foi usada e quais riscos exigem revisão.

## 11. Headlines e funções adiadas

Headlines só devem ser geradas depois de contexto, tese, payoff e locutor. Devem ser específicas ao trecho, fiéis ao conteúdo, legíveis e adequadas ao formato. O Estúdio de Texto de Arte pode evoluir depois, mas não deve ocupar a prioridade do corte.

Permanecem adiados, salvo pedido explícito posterior: editor completo estilo CapCut, correção manual de legendas dentro do Furia, edição pós-renderização, tradução, avatars, voz, música automática, branding complexo, publicação automática e sincronização de múltiplas câmeras.

A sincronização de câmeras do mesmo evento pode permanecer no backlog. O primeiro objetivo é analisar cada MP4 com precisão.

## 12. Gemini, memória e armazenamento

A chave Gemini deve ser inserida uma vez e armazenada localmente de forma segura, sem aparecer em logs, commits, snapshots ou respostas. O programa deve sobreviver a reinicialização e informar apenas se a chave está configurada, não o valor.

Gemini é opcional. O Furia precisa continuar funcionando offline com Whisper, análise de áudio, heurísticas e ranking local. Se Gemini falhar, exceder limite ou não estiver configurado, o job deve seguir com fallback explícito.

Para um notebook de 500 GB, priorize texto, timestamps, metadados, hashes e snapshots compactados. Não mantenha quatro cópias da mesma live. O backup deve proteger os dados importantes, mas a aba precisa ser simples, curta e útil. Um backup não pode restaurar credenciais ou sobrescrever dados sem confirmação.

## 13. Ciclo obrigatório de trabalho da IA executora

Em cada rodada:

1. confirme remote, branch, commit e `git status`;
2. leia este arquivo e os documentos vivos de continuidade;
3. proteja alterações locais e nunca use comandos destrutivos sem autorização;
4. defina uma única hipótese principal;
5. execute baseline antes da alteração;
6. leia o código e os testes envolvidos;
7. faça a menor mudança capaz de testar a hipótese;
8. crie ou atualize regressões;
9. execute a suíte, `py_compile`, `git diff --check` e validações de mídia quando aplicáveis;
10. processe uma mídia real quando houver acesso autorizado;
11. compare antes/depois com métricas claras;
12. classifique cada conclusão como confirmado, reproduzido, corrigido, provável, não verificado ou bloqueado;
13. atualize estado, decisões, changelog, relatório e próxima hipótese;
14. faça commits pequenos na branch de trabalho;
15. publique no GitHub somente alterações verificadas;
16. não faça merge na branch principal sem autorização explícita.

Não inclua no Git vídeos grandes, bancos locais, cookies, tokens, chaves, transcrições privadas ou dados pessoais.

## 14. Relatório obrigatório

O relatório de cada rodada deve responder, em português simples:

- o que foi executado;
- qual era a hipótese;
- qual foi o baseline;
- qual mídia foi processada;
- qual transcrição foi usada;
- quantos blocos e candidatos foram produzidos;
- quais cortes foram renderizados;
- quais eram os locutores prováveis;
- quais gates foram acionados;
- o que o Campaign Hub forneceu;
- o que veio do snapshot local;
- quais resultados foram melhores ou piores;
- quais testes passaram ou falharam;
- quais limitações ficaram bloqueadas;
- qual é a única próxima hipótese de maior impacto.

Nunca esconda uma falha atrás de uma lista de funcionalidades. Se o job terminou, isso prova apenas que terminou; não prova que os cortes são editorialmente bons.

## 15. Próxima hipótese recomendada

A hipótese de maior impacto após esta auditoria é:

> **Se o Furia comparar cada candidato local com blocos QA-gated, destaques, perguntas-gatilho, riscos, autossuficiência e locutor do Campaign Hub antes do ranking final, ele reduzirá a seleção de trechos de outro orador, perderá menos momentos importantes e explicará melhor por que um corte foi escolhido ou rejeitado, sem depender do MCP em cada job.**

Primeiro implemente o benchmark e o diagnóstico. Depois, com evidência suficiente, promova somente os sinais que melhorarem o resultado para priors fracos. Não transforme o Campaign Hub em aprovador automático.

## 16. Referências vivas

- [Repositório Furia Clips](https://github.com/SAGIEV007/furia-clips)
- [Campaign Hub MCP autorizado](https://chub-api.missao.org.br/mcp/wk_a07206ced171ac72acb18d6746e735486790ea98a2a2f51b)
- [Criadores/Garimpo](https://criadores.missao.org.br/garimpo)
- [`AGENTS.md`](../../AGENTS.md)
- [`PROJECT_STATE.md`](PROJECT_STATE.md)
- [`DECISIONS.md`](DECISIONS.md)
- [`NEXT_CYCLE.md`](NEXT_CYCLE.md)
- [`CAMPAIGN_HUB_LINEAGE.md`](CAMPAIGN_HUB_LINEAGE.md)
- [`IDEAS_BACKLOG.md`](IDEAS_BACKLOG.md)
- [`PROMPT_3_EXECUTOR_CHUB_PARITY.md`](PROMPT_3_EXECUTOR_CHUB_PARITY.md), mantido como histórico técnico até ser incorporado e eventualmente arquivado.
