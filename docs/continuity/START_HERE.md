# START_HERE — Furia Clips Renan-first

> **Este é o ponto de entrada canônico para qualquer nova IA que continuar o Furia Clips.** Leia este arquivo antes de alterar código. O prompt de execução copiável e focado em Chub→cortes está em [`PROMPT_EXECUCAO_CHUB_CORTES.md`](PROMPT_EXECUCAO_CHUB_CORTES.md), o prompt mestre consolidado está em [`PROMPT_MESTRE_IA.md`](PROMPT_MESTRE_IA.md), o contrato funcional está em [`CHUB_INTEGRATION_CONTRACT.md`](CHUB_INTEGRATION_CONTRACT.md) e o modelo obrigatório de commit está em [`COMMIT_MESSAGE_TEMPLATE.md`](COMMIT_MESSAGE_TEMPLATE.md). Este arquivo substitui, como instrução de entrada, os antigos Prompts 1, 2 e 3. Os arquivos antigos permanecem no repositório como histórico, mas não devem ser tratados como o prompt vigente.

## 1. Missão do projeto

Você está continuando o projeto **Furia Clips**, repositório `https://github.com/SAGIEV007/furia-clips`. O Furia é uma ferramenta local de clipping automático especializada em encontrar cortes do universo **Renan Santos/MBL**.

O objetivo não é criar um editor geral parecido com CapCut. O objetivo principal é transformar vídeos longos, lives, entrevistas, eventos e arquivos MP4 em **cortes precisos, autossuficientes, contextualizados e editorialmente úteis**, com começo natural, desenvolvimento suficiente, tese ou resposta compreensível e encerramento com payoff.

> **Regra de prioridade:** precisão de contexto e de intervalo vem antes de quantidade de cortes, formatos sociais, headlines, facetracking, branding ou edição pós-renderização.

O usuário não é programador. Execute no ambiente autorizado tudo o que puder executar, explique os resultados em português simples, não transfira desnecessariamente tarefas técnicas ao usuário e nunca declare uma função pronta apenas porque existe uma rota, uma tela ou um módulo com esse nome.

## 2. Estado real conhecido — não confundir código com produto pronto

A branch de trabalho conhecida é `manus/rebuild-opus-parity`. A última release funcional de código é a versão `2.2`, commit `074a129`; as versões documentais `2.4` e `2.5` formalizam o contrato Campaign Hub→cortes e o prompt operacional `PROMPT_EXECUCAO_CHUB_CORTES.md` orienta a próxima implementação. O Furia contém muitas peças do pipeline, mas ainda não oferece uma experiência diária equivalente ao Garimpo + Campaign Hub.

A validação prática mais recente do código foi feita no clone real do GitHub para a release `2.2`. A suíte terminou com **327 testes aprovados**, o benchmark b354 foi persistido, três highlights foram exportados individualmente e todos os MP4s foram validados por FFprobe. As revisões 2.3, 2.4 e 2.5 são documentais/operacionais e não reivindicam melhoria funcional; a próxima rodada deve implementar a ponte Chub→seeds→expansão→gates. O modelo oficial pequeno de facetracking continua sendo um asset externo; não o inclua no Git e mantenha o fallback offline quando ele não estiver disponível.

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

O **Furia Clips é um projeto separado**, mas sua prioridade funcional é construir uma integração explícita com o Campaign Hub. O objetivo não é apenas importar memória, listar blocos ou exportar intervalos conhecidos: o contexto do Campaign Hub deve orientar seeds, alinhamento à fonte local, expansão temporal, gates de contexto e propostas de cortes Renan Santos/MBL. O contrato detalhado está em [`CHUB_INTEGRATION_CONTRACT.md`](CHUB_INTEGRATION_CONTRACT.md).

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
        contexto Chub → seeds → propostas de corte
        ranking, revisão e renderização local
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
| 4 | Criar pré-análise por blocos e importar, quando disponível, o contexto autorizado do Campaign Hub antes de gerar os cortes. |
| 5 | Alinhar fonte, YouTube ID, timestamps, transcrição e proveniência Chub com o MP4 local; declarar qualquer mismatch. |
| 6 | Transformar blocos, highlights, pergunta-gatilho, pauta, riscos e locutor em seeds semânticas/temporais. |
| 7 | Expandir cada seed até a menor janela completa com antecedente, pergunta–resposta quando necessária, tese, evidência e payoff. |
| 8 | Aplicar gates de contexto, locutor, transcrição, timing, mídia e risco; somente depois gerar propostas e ranking. |
| 9 | Mostrar a origem Chub, a razão da expansão, a confiança e as flags; permitir revisão e exportar/renderizar apenas a proposta confirmada. |
| 10 | Priorizar a fala do Renan quando ele estiver presente, mas nunca atribuir a ele uma fala de Kim, entrevistador ou convidado. |
| 11 | Renderizar primeiro no aspecto original, validar com FFprobe e registrar tudo para revisão. |

A quantidade de cortes não é fixa. “Todos os cortes” significa **todos os candidatos que passarem pelos critérios**, com diversidade e sem repetição. Uma entrevista curta pode gerar poucos cortes; uma live longa pode gerar mais. Nunca aumentar a quantidade apenas para atingir um número.

## 6. Download seletivo de blocos

O teste comprovou que o Furia possui upload local, ingestão por URL, transcrição, corte e **exportação seletiva local** de um bloco ou highlight quando a fonte correspondente já está disponível. O download remoto seletivo por range da URL de origem ainda não está garantido para todos os provedores.

Essa é uma prioridade P0/P1 para a próxima etapa de ingestão, depois que o recall local for melhorado. O fluxo deve:

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

## 9. Campaign Hub como contexto, seed e calibração

A integração rica deve usar o Campaign Hub antes do score para construir contexto e propostas de corte, e depois manter um benchmark read-only para medir se essa orientação melhora o baseline. O Campaign Hub fornece seeds, evidência e calibração; não aprova automaticamente a saída.

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

O Acervo também pode estar errado, incompleto ou baseado em legenda automática. Não trate seus blocos como verdade absoluta. Use `densityRank` e `selfContainedRank`, não os valores brutos de autoavaliação. Preserve versão do labeler, origem, tier de confiança e avisos de gate. `turn` e `speakerChange` não são identidade; `renanSpeaking=false` deve continuar excluindo atribuição automática da fala ao Renan. Para o contrato completo de campos, operações, gates e critérios de aceitação, leia [`CHUB_INTEGRATION_CONTRACT.md`](CHUB_INTEGRATION_CONTRACT.md).

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
14. faça commits pequenos na branch de trabalho, sempre usando o corpo completo de [`COMMIT_MESSAGE_TEMPLATE.md`](COMMIT_MESSAGE_TEMPLATE.md);
15. publique no GitHub somente alterações verificadas;
16. atualize `PROJECT_STATE.md` com o hash final e o relatório correspondente;
17. não faça merge na branch principal sem autorização explícita.

Não inclua no Git vídeos grandes, bancos locais, cookies, tokens, chaves, transcrições privadas ou dados pessoais.

## 14. Relatório obrigatório

O relatório de cada rodada e o corpo do commit devem responder, em português simples:

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

## 15. Primeira onda implementada e validada

A primeira onda operacional foi implementada no clone real da branch `manus/rebuild-opus-parity` e validada em **17/08/2026**. Ela não transforma o Furia em produto final, mas cria a fundação real da ponte local entre Campaign Hub, blocos e exportação seletiva.

| Entrega | Estado verificado |
| --- | --- |
| Memória local versionada | Implementada em `modules/campaign_hub_memory.py`, com validação, manifesto, instalação atômica, fusão incremental e fallback offline. |
| Export autorizado do Acervo | Implementado em `scripts/convert_chub_blocks_export.py`; preserva blocos, destaques, frases, fontes e proveniência, sem mídia bruta. |
| Atualização local | Implementada em `scripts/update_campaign_hub_memory.py` e nas rotas de status/importação. |
| Blocos no backend | Implementados em `modules/editorial_block_memory.py`, com busca, filtro por fonte, prioridade Renan-first sem ocultar terceiros e leitura detalhada. |
| UX de Blocos | Implementado entre Fonte e Refinamento, com resumo, pergunta, intervalo, duração, destaques, ranks, riscos e tier. |
| Exportação seletiva local | Implementada em `/api/editorial/blocks/export`, preservando o aspecto original e validando mídia. |
| MP4 de bloco baixado | O b354 real foi mapeado de `6142.56–6692.0` na fonte longa para `0–549.44s` no MP4 local. O arquivo produzido foi validado em 1920×1080, H.264/AAC e 549.4489s. |
| Sinal do Chub no ranking | Implementado como evidência temporal/textual limitada e explicável; não é gate nem aprovação automática. |
| Testes | `322 passed`; JavaScript, compilação Python, diff e FFprobe também passaram. |

O caso b354 continua sendo a regressão editorial principal: é um bloco sobre Renan, mas com `renanSpeaking=false` porque Kim fala. A interface deve mostrar esse fato, não convertê-lo em “fala do Renan”. O campo `speakerChange` do Acervo continua sendo evidência automática e não identidade definitiva.

A exportação seletiva implementada nesta onda é **local**: ela recorta uma fonte já disponível no workspace ou um MP4 de bloco baixado. O download remoto por range de uma URL longa ainda não está garantido para todos os provedores e permanece na próxima onda, com fallback seguro.

## 16. Segunda onda implementada e validada

A segunda onda foi implementada na release `2.2`. Ela transforma a comparação b354 em um benchmark persistente local e permite exportar cada highlight de referência, sem chamar o Campaign Hub durante o corte e sem colocar o Chub como aprovador automático.

| Entrega | Estado verificado |
| --- | --- |
| Benchmark local | `modules/editorial_benchmark.py` compara intervalos, mapeia timelines, calcula recall, IoU, erro de fronteira, duplicatas e classificação da divergência. |
| Repetição do benchmark | `scripts/run_editorial_benchmark.py` repete o caso com memória local e candidatos autorizados. |
| Persistência | Relatórios leves são salvos em `FuriaClipsData/benchmarks`; nenhuma mídia, transcrição privada ou base local entra no Git. |
| Resultado b354 | Sete candidatos do Furia cobriram `0/3` highlights QA-gated; IoU médio `0.0`; os três casos foram classificados como `Campaign Hub melhor` no critério temporal desta amostra. |
| Mapeamento | Highlights absolutos foram convertidos para `146.80–150.80s`, `223.24–228.40s` e `488.48–495.20s` no MP4 local de `549.449s`. |
| Exportação individual | Nova rota e botões do painel exportaram os três highlights no aspecto original; FFprobe confirmou 1920×1080 H.264/AAC. |
| Testes | `327 passed`; `compileall`, `node --check`, `git diff --check`, verificação de segredos e revisão de mídia rastreada passaram. |

O resultado é um diagnóstico útil, não uma aprovação cega do Acervo: a amostra mostra que o candidato local atual não alcançou nenhum dos três momentos de referência. A lacuna está na cobertura da seleção, não no mapeamento ou na renderização do highlight. O b354 continua sendo sobre Kim (`renanSpeaking=false`) e deve continuar sendo mostrado assim.

## 17. Próxima hipótese recomendada

> **Se a geração de candidatos usar os highlights locais apenas como sementes de proposta e expandir cada semente até a menor janela completa da transcrição, o Furia aumentará o recall temporal do b354 sem alterar o ranking, inventar locutor ou depender de download remoto.**

A próxima implementação deve ser offline-first: propor janelas ao redor de cada highlight, ajustar as bordas para frases e turnos completos, executar os mesmos gates de contexto, payoff e locutor e repetir o benchmark b354. Download remoto por range, diarização robusta, reframe e headlines continuam fora desta hipótese.

## 18. Referências vivas

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
- [`CYCLE_11_REPORT_2026-08-17.md`](CYCLE_11_REPORT_2026-08-17.md), relatório da primeira onda operacional.
- [`CYCLE_12_REPORT_2026-08-17.md`](CYCLE_12_REPORT_2026-08-17.md), relatório do benchmark b354 e dos highlights individuais.
