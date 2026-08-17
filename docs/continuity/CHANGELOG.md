# Changelog de continuidade

## 2.6 — Primeira ponte funcional Campaign Hub→seeds→propostas

### Incluído

- `modules/campaign_hub_guidance.py` normaliza snapshots autorizados do Campaign Hub em seeds auditáveis, aceitando os formatos snake_case e camelCase usados pelos exports reais.
- A normalização preserva proveniência, `sentenceIdx`, `source_ref`, `renanSpeaking`, `trustTier`, `gateWarnings`, `riskFlags`, `densityRank` e `selfContainedRank`, além de suportar highlights aninhados, `possibleCuts` e fallback por bloco.
- `modules/clip_selector.py` passou a gerar propostas `campaign_hub_guided`: a seed é expandida até a menor janela local que complete antecedente, pergunta, tese/evidência e payoff quando a transcrição permitir.
- As propostas guiadas recebem gates explícitos de contexto, payoff, locutor, timing, risco, técnico, proveniência e avisos. Elas permanecem separadas de cortes aprovados e podem exigir revisão humana.
- `modules/editorial_context.py` expõe o diagnóstico da quantidade de seeds guiadas; `app.py` carrega o snapshot uma vez por job e o reutiliza offline-first na seleção, nos hooks e no ranking.
- `tests/test_campaign_hub_guidance.py` adiciona seis regressões para mapeamento de timeline, expansão contextual, fallback legado, origem auditável, formato camelCase real e revisão obrigatória de `third_party`/`gateWarnings`.
- `VERSION`, `README.md`, `AGENTS.md`, `START_HERE.md`, `PROJECT_STATE.md` e `NEXT_CYCLE.md` registram a nova identidade e o próximo experimento.

### Hipótese e baseline

A hipótese foi que transformar highlights/blocos autorizados em seeds temporais e semânticas e expandi-los até a menor janela completa aumentaria o recall sem sacrificar contexto, atribuição ou revisão. O baseline persistente b354 tinha sete candidatos locais, recall `0/3` e IoU médio `0.0`.

### Validação da rodada

A suíte completa terminou com **333 testes aprovados**. Também passaram `compileall`, `node --check static/js/app.js`, `git diff --check` e a verificação SHA-256 do asset BlazeFace provisionado temporariamente e removido antes do commit.

Com um payload real do Campaign Hub para o vídeo `gVrW6a5e6Tc` e o bloco `70358a7d-7848-48d1-8d3d-5ef7c61c149d`, a normalização produziu duas seeds a partir dos highlights `sentenceIdx=128` e `sentenceIdx=171`. A avaliação de proposta gerou as janelas `426.4–451.52s` e `511.0–566.12s`; ambas passaram `context_complete=true`. Como o bloco tinha `trustTier=third_party` e `gateWarnings=["start_continuation"]`, as duas ficaram com `review_required=true` por `provenance_gate` e `warning_gate`, sem autoaprovação.

### Resultado e limitações

A ponte está implementada e coberta por regressões, mas o recall do b354 **não foi medido nesta release** porque o snapshot autorizado correspondente não estava instalado localmente durante o job normal. Portanto, não há ganho de recall reivindicado sobre `0/3`; o resultado é funcional e reproduzido no payload real do Chub, mas o benchmark de mídia local permanece não verificado.

A proveniência `third_party` e os avisos de início abrupto continuam exigindo revisão, de forma intencional. Sem snapshot local em `~/FuriaClipsData/campaign_hub/profile.json`, o job normal permanece no caminho legado e não produz propostas guiadas. Nenhum token, cookie, snapshot privado, banco local, mídia grande ou modelo binário foi incluído no Git.

### Próxima hipótese

> Se um snapshot autorizado e sanitizado do Campaign Hub for instalado localmente e o Furia reprocessar o caso b354 com a ponte 2.6, o recall temporal deve sair de `0/3` sem aumentar falsos positivos, atribuições erradas, truncamentos ou confusão entre quem fala e quem é foco editorial.

## 2.5 — Prompt operacional Chub→cortes

### Incluído

- `docs/continuity/PROMPT_EXECUCAO_CHUB_CORTES.md`, prompt copiável para executar a próxima hipótese do projeto com foco em Campaign Hub→seeds→alinhamento→expansão→gates→propostas.
- `START_HERE.md`, `AGENTS.md` e `README.md` atualizados para encaminhar diretamente ao novo prompt, além do prompt mestre e do contrato funcional.
- `CYCLE_15_REPORT_2026-08-17.md`, relatório da criação do prompt e do estado funcional preservado.
- `VERSION` incrementado para `2.5`; nenhum módulo de seleção, ranking, ingestão, diarização, reframe ou renderização foi alterado.

### Validação da rodada

A revisão confirmou o prompt novo, os links relativos, a versão, **327 testes aprovados**, `git diff --check`, `compileall`, `node --check static/js/app.js` e a ausência de tokens, cookies, mídia grande, bancos locais, modelos binários ou dados privados. O asset BlazeFace foi usado apenas temporariamente com SHA-256 conferido e removido antes do commit.

### Limitações conhecidas

A revisão 2.5 não implementa a ponte funcional Chub→seeds→expansão→gates→propostas. O benchmark b354 permanece em `0/3` e a sessão de blocos continua sendo diagnóstico, revisão e fallback, não o produto final.

## 2.4 — Contrato Campaign Hub→cortes e reorientação do norte

### Incluído

- `docs/continuity/CHUB_INTEGRATION_CONTRACT.md`, contrato funcional que define o fluxo Campaign Hub → alinhamento à fonte local → seeds → expansão contextual → gates → propostas → revisão → renderização.
- `PROMPT_MESTRE_IA.md` e `START_HERE.md` atualizados para deixar claro que a sessão de blocos é superfície de diagnóstico/revisão e que o objetivo principal é melhorar de forma verificável a seleção de cortes Renan Santos/MBL usando contexto do Campaign Hub.
- `PROJECT_STATE.md` e `NEXT_CYCLE.md` reorientados para a hipótese de transformar blocos/highlights Chub em seeds temporais e semânticas, sem tratar o Campaign Hub como aprovador automático.
- `VERSION` incrementado para `2.4`, representando a mudança observável no contrato de continuidade; nenhuma lógica de seleção, ranking, ingestão, reframe ou renderização foi alterada nesta revisão.

### Validação da rodada

Foram revisados o adaptador do Campaign Hub, a memória local, o contexto editorial, o ranker, a sessão de blocos, o frontend e os dados autorizados de blocos/transcrição. O estado real registrado é que a memória e a UI existem, mas o contexto Chub ainda influencia pouco o resultado e não cria propostas de janela contextualizadas. A suíte terminou com **327 testes aprovados**, além de `compileall`, `node --check`, `git diff --check` e revisão de arquivos proibidos; o asset BlazeFace usado na validação foi removido antes do commit.

### Limitações conhecidas

A revisão 2.4 não melhora recall, geração de propostas, diarização, reconhecimento de voz, reframe, ranking, download remoto por range ou qualidade editorial. O benchmark b354 permanece em `0/3` até que a hipótese Chub→seed→expansão seja implementada e reproduzida. A sessão de blocos continua funcional apenas para a parte já implementada de consulta, inspeção e exportação; ela não deve ser interpretada como integração completa.

## 2.3 — Prompt mestre e contrato de continuidade

### Incluído

- `docs/continuity/PROMPT_MESTRE_IA.md`, prompt copiável que consolida o `START_HERE`, os prompts históricos, as decisões permanentes, o norte do benchmark b354, o uso do Campaign Hub, o ciclo de engenharia, segurança e o formato de entrega.
- `docs/continuity/COMMIT_MESSAGE_TEMPLATE.md`, modelo obrigatório para registrar hipótese, baseline, implementação, escopo excluído, validação, resultado, limitações e próxima hipótese no corpo dos commits.
- `docs/continuity/CYCLE_13_REPORT_2026-08-17.md`, relatório da rodada documental e da hipótese de tornar o GitHub autossuficiente para continuidade entre IAs.
- `README.md`, `AGENTS.md`, `START_HERE.md`, `PROJECT_STATE.md` e `NEXT_CYCLE.md` atualizados para encaminhar ao prompt mestre, manter o norte atual e eliminar a divergência do hash `a9a2803` para `074a129`.
- `VERSION` incrementado para `2.3`, representando a mudança no contrato de continuidade; nenhuma lógica de seleção, ranking, ingestão, reframe ou renderização foi alterada.

### Validação da rodada

O estado do Git, a branch `manus/rebuild-opus-parity`, a revisão de código `074a129`, os documentos vivos, os prompts históricos e os resultados da release 2.2 foram auditados. A validação desta revisão é documental e inclui revisão de links relativos, diff, versão, ausência de arquivos proibidos e confirmação do hash final após o commit.

### Limitações conhecidas

A revisão 2.3 não melhora recall, diarização, reconhecimento de voz, reframe, ranking, download remoto por range ou qualidade editorial. O benchmark b354 permanece em `0/3` até que a hipótese de expansão de seeds seja executada e reproduzida. A capacidade de uma IA externa seguir o contrato deverá ser avaliada em uma sessão futura com checkout limpo.

## 2.2 — Benchmark persistente e exportação individual de highlights

### Incluído

- `modules/editorial_benchmark.py` registra uma comparação local e reproduzível entre candidatos do Furia e destaques QA-gated do Campaign Hub, sem consultar o MCP durante os cortes.
- O benchmark persiste mapeamento da timeline longa para o MP4 de bloco, recall de cobertura, IoU, erro médio de fronteira, duplicatas e classificação explicável da divergência.
- `scripts/run_editorial_benchmark.py` permite repetir a comparação com um arquivo de candidatos e uma memória local autorizada.
- `POST /api/editorial/blocks/highlights/export` e os botões do painel exportam um destaque específico no aspecto original.
- `GET/POST /api/editorial/benchmark` permite consultar e salvar resultados locais; os relatórios ficam em `FuriaClipsData/benchmarks`, fora do Git.
- Testes de mapping, IoU, persistência, rotas e sintaxe da interface foram adicionados.

### Validação da rodada

O bloco b354 real foi comparado com os sete candidatos persistidos pelo Furia. Seus três destaques foram mapeados para `146.80–150.80s`, `223.24–228.40s` e `488.48–495.20s` no MP4 local de `549.449s`. O recall de cobertura foi `0/3`, o IoU médio foi `0.0` e os três casos foram classificados como `Campaign Hub melhor` neste benchmark temporal. Os três highlights foram exportados individualmente pelo backend e validados em 1920×1080 H.264/AAC, com durações de aproximadamente `4.004s`, `5.172s` e `6.740s`.

### Limitações conhecidas

O benchmark mede alinhamento temporal e preserva flags editoriais, mas não prova que o Campaign Hub esteja sempre correto nem resolve diarização, reconhecimento de voz, relevância semântica ou download remoto por range. O caso b354 mostrou uma lacuna real de cobertura; esta release não aumenta o peso do Chub no ranking com base em uma amostra única.

## 2.1 — Memória local do Campaign Hub, blocos e exportação seletiva local

### Incluído

- Memória local versionada e offline-first para exports autorizados do Campaign Hub, com manifesto, hash, instalação atômica e fusão incremental.
- Conversor e comando local de atualização em `scripts/convert_chub_blocks_export.py` e `scripts/update_campaign_hub_memory.py`, sem depender do MCP durante cada job.
- Leitura de blocos editoriais com filtro por fonte/YouTube ID, busca, destaques, pergunta-gatilho, riscos, proveniência e prioridade Renan-first sem ocultar terceiros.
- Novo painel visual de Blocos entre Fonte e Refinamento, mantendo o aspecto original como prioridade.
- Exportação seletiva local por intervalo e mapeamento seguro de timestamps absolutos do vídeo longo para MP4 de bloco que começa em zero.
- Evidência temporal/textual de blocos no ranking como ajuste pequeno, explicável e nunca como gate.
- Testes para memória, filtros, ranking, exportação, limites, timeline mapeada e UX; nenhum vídeo ou segredo foi versionado.

### Validação da rodada

A consulta autorizada por `videoId=57nyfP9IDW4` retornou 64 blocos reais do Primeiro Ato. O bloco b354, `6142.56–6692.0s`, foi exportado do MP4 local como `0–549.44s` e validado em 1920×1080, H.264/AAC, 549.4489s. A suíte completa terminou com **322 testes aprovados**; `node --check`, `compileall`, `git diff --check` e inspeção visual também passaram.

### Limitações conhecidas

O download remoto seletivo por range ainda depende do provedor e não foi prometido. O benchmark persistente ainda será construído na próxima onda, assim como exportação individual de highlights, diarização robusta, reconhecimento de voz e simplificação completa da sidebar.

## 2.0 — START_HERE canônico e validação prática Renan-first

### Incluído

- Novo `docs/continuity/START_HERE.md`, ponto de entrada canônico que unifica o contexto do Furia, o estado real incompleto, o uso do Campaign Hub, o fluxo inspirado no Garimpo, as regras Renan-first, o ciclo de testes e a continuidade no GitHub.
- `AGENTS.md` atualizado para apontar o START_HERE; os Prompts 1, 2, 3 e o Prompt Mestre antigo permanecem como histórico, não como instrução vigente.
- Relatório `docs/continuity/CYCLE_10_REPORT_2026-08-17.md` com a primeira validação ponta a ponta usando o MP4 do Primeiro Ato de Campanha e comparação read-only com o bloco b354 do Campaign Hub.
- Diagnóstico explícito de que o Furia atual faz upload, transcrição, seleção e renderização, mas ainda não possui download seletivo de bloco, diarização confiável nem memória rica local do Campaign Hub.
- Versão pública atualizada de 1.9 para 2.0 e teste de identidade de runtime atualizado.

### Validação da rodada

O clone real da branch `manus/rebuild-opus-parity` foi executado com 306 testes aprovados. O MP4 de aproximadamente 9m14s foi processado pelo servidor local, gerando sete cortes H.264 1920×1080 em 16:9, validados por FFprobe e inspeção visual. O Campaign Hub identificou o mesmo material como o bloco b354, com 121 frases, três destaques QA-gated, pergunta-gatilho, riscos e `renanSpeaking=false`.

### Limitações conhecidas

Nenhum módulo de seleção, ranking ou renderização foi melhorado nesta release. O segundo ciclo não cobriu os três destaques do bloco b354, embora tenha produzido arquivos tecnicamente válidos. A entrada por link foi bloqueada pelo anti-bot do YouTube neste ambiente. A área autenticada interna do Garimpo não ficou disponível na sessão Sandbox. O benchmark temporal/editorial foi especificado, mas ainda não foi implementado como funcionalidade do aplicativo.

## 1.9 — Prompt executor e paridade editorial via Campaign Hub

### Incluído

- Novo `docs/continuity/PROMPT_3_EXECUTOR_CHUB_PARITY.md`, prompt copiável para futuras IAs continuarem o Furia Clips com auditoria do checkout, hipótese única, testes, versionamento e publicação verificável.
- Contrato explícito para usar blocos QA-gated, transcrições, perguntas-gatilho, autossuficiência, payoff, riscos e destaques do Campaign Hub como benchmark e calibração fraca, sem chamada MCP direta no runtime.
- Regras de escopo que mantêm o Furia Clips focado em cortes precisos e contextuais e adiam um editor pós-renderização semelhante ao CapCut.
- Registro de padrões profissionais pesquisados em OpusClip, Descript e Riverside, traduzidos para foco por locutor/tópico, busca editorial, score explicável, presets de composição, preservação de evidência e diagnóstico de divergência.
- `AGENTS.md` atualizado para apontar o prompt executor vigente.

### Validação da rodada

A mudança é documental e operacional; nenhum módulo de processamento foi alterado. Foram conferidos o estado da branch, a versão 1.8, o prompt mestre, o prompt executor, o estado do projeto, o próximo ciclo, a linhagem do Campaign Hub e o contrato de versionamento. A suíte completa passou com `306 passed`, `git diff --check` e `py_compile` foram aprovados, e o commit `d27cb05` foi publicado na branch `manus/rebuild-opus-parity`.

### Limitações conhecidas

O benchmark Campaign Hub versus candidatos do Furia ainda não foi implementado nesta release. A versão 1.9 registra o contrato e a hipótese para a próxima rodada; ela não declara melhoria editorial já medida. A validação audiovisual não faz parte desta alteração documental.


## 1.8 — Decodificação AV1 e cobertura canônica da transcrição


### Incluído

- FFmpeg passa a forçar decodificação por software nas etapas de detecção de cenas, análise de layout e renderização, evitando que fontes AV1 dependam de aceleração de hardware indisponível.
- Fontes AV1 deixam de acionar o caminho OpenCV/MediaPipe quando a análise segura de layout não é possível; o Furia preserva o quadro original com fallback explícito, em vez de repetir erros de decodificação.
- O pipeline deixa de executar Whisper uma segunda vez quando a transcrição automática já foi obtida; a transcrição efetivamente usada passa a receber cobertura e proveniência antes da análise de contexto.
- A visão de seleção, depois de remover o pré-roll, preserva o status de cobertura, a origem e a qualidade da transcrição completa. Isso impede que uma transcrição válida seja reclassificada como “identidade temporal não validada” e que todos os candidatos sejam adiados por engano.

### Validação da rodada

No vídeo real `RENAN SANTOS — BP NAS ELEIÇÕES`, a primeira amostra de 15 minutos reproduzia o bug: 5 candidatos eram encontrados, mas os 5 eram adiados porque a seleção havia perdido a cobertura temporal. Depois da correção, a mesma amostra produziu **4 exports** válidos. Os arquivos finais preservaram 1920×1080 e foram validados por FFprobe como H.264/AAC, com durações aproximadas de 138,8 s, 40,4 s, 26,3 s e 27,2 s. A prova final não registrou novos erros AV1 no servidor.

A suíte completa passou com **306 testes**; os testes focados de contexto, fronteira, cenas, layout e AV1 passaram com **26 testes**. Também foram aprovados `py_compile` e uma renderização real de intervalo AV1 para H.264/AAC.

### Limitações conhecidas

A fonte BP completa tem aproximadamente 84 minutos. O ambiente encerrou o servidor durante a tentativa de transcrição integral, portanto a validação editorial desta rodada foi feita com uma amostra real de 15 minutos e com reanálise da transcrição/cortes antigos da fonte completa. Nenhum Gemini foi necessário. O Campaign Hub continua sendo prior agregado fraco e explicável; a próxima hipótese isolada permanece a detecção de erros semânticos do ASR antes de headlines.

## 1.7 — Contexto canônico, proxy multimodal e headlines específicas

### Incluído

- Transcrições coladas/importadas passam a carregar proveniência explícita e são marcadas como timeline canônica; o pipeline não executa Whisper silenciosamente quando o texto manual foi recebido.
- O Gemini recebe uma cópia audiovisual temporária compactada, com resolução máxima de 640 px, amostragem visual adaptativa e áudio mono a 16 kHz; o vídeo original não é alterado e o arquivo temporário é removido ao final.
- Upload e geração multimodal receberam timeouts menores e cancelamento cooperativo durante a compactação, upload, espera e geração.
- Cada sessão arquiva fora do GitHub a transcrição integral, a transcrição de seleção, o dossiê de contexto, headlines geradas, escolhas/rejeições de headlines, aprovações/rejeições de clips e um manifesto de proveniência.
- O botão de cópia do console usa o histórico completo da sessão, não somente as 200 linhas visíveis.
- O dossiê de contexto informa na interface a origem da transcrição, o uso do proxy Gemini e se o prior agregado do Campaign Hub foi realmente aplicado.
- O fallback de headlines reconhece o núcleo específico de mobilização, ato e ameaça, evitando slogans genéricos de segurança no caso real enviado pelo usuário.

### Validação da rodada

A suíte completa passou com `303 passed`; os testes focados passaram com `52 passed`; `py_compile`, `node --check` e uma prova local do proxy FFmpeg foram aprovados. A prova reduziu um vídeo sintético de 49.171 para 16.266 bytes, preservando a preparação de áudio e vídeo da cópia temporária. A regressão editorial do corte “não tenham medo/ato/ameaça” passou sem Gemini.

### Limitações conhecidas

O proxy reduz custo e risco de limite, mas não transforma uma análise visual longa em evidência perfeita; a transcrição canônica continua sendo a fonte temporal principal. O Campaign Hub ainda é usado como prior agregado fraco e explicável, não como memória de voz nem treinamento de pesos. A próxima hipótese isolada permanece a detecção de erros semânticos do ASR antes de headlines.

## 1.6 — Gate conservador de pré-roll e fronteira de conteúdo de live

### Incluído

- Novo módulo `modules/source_boundary.py` para detectar, com timestamps da transcrição, a fronteira entre pré-roll/propaganda e o conteúdo editorial da live.
- A seleção editorial recebe apenas a transcrição a partir da fronteira segura; a transcrição integral continua arquivada para auditoria.
- O detector prefere uma abertura forte de live, como “sejam bem-vindos” acompanhada de uma indicação inequívoca de início, sobre uma saudação promocional ambígua.
- Uma saudação genérica isolada, como “boa noite a todos”, não é suficiente para cortar automaticamente a fonte; nesse caso a timeline completa permanece em revisão segura.
- Regressões para pré-roll detectado, coletiva sem pré-roll, saudação genérica e limite manual de fronteira.

### Validação da rodada

No benchmark renal de 15 minutos, o baseline do projeto 42 gerava 3 exports e incluía o material promocional `1. se não ser na rua, porque pode ser.mp4`, iniciado em `66,0333s` e estendido até `215,29s`. Com a fronteira detectada em `169,5s`, o projeto 47 gerou 4 exports, nenhum iniciado antes de `169,5s`; os quatro foram validados por FFprobe como H.264/AAC 1920×1080. A suíte completa passou com `299 passed`. O resultado foi reproduzido depois do endurecimento conservador do detector, usando a amostra v2 para evitar deduplicação por assinatura.

### Limitações conhecidas

A fronteira é um diagnóstico de seleção e ainda não é persistida como campo próprio na tabela de projetos; o evento do job e os artefatos de benchmark registram o resultado. Uma fonte sem uma abertura forte pode permanecer sem corte automático, deliberadamente, para evitar remover conteúdo válido. A próxima rodada continua sendo a detecção de erros semânticos do ASR antes da headline.


## 1.5 — Transcrição por áudio via URL e gate técnico antes da renderização

### Incluído

- Nova operação assíncrona `POST /api/source/transcribe` para transcrever fontes públicas sem criar projeto ou gerar cortes.
- Transcrição por URL baixa áudio por padrão (`media_type: audio` / `format=ba/b`), mantendo o download de vídeo para o fluxo operacional de cortes.
- Botão separado no frontend para “somente transcrever”, com acompanhamento persistente do job, cancelamento existente e carregamento no editor.
- Candidatos com `technical_gate_status=review` agora são adiados antes do `VideoCutter`, preservando motivos, `review_flags` e intervalos no diagnóstico.
- Correção da persistência de `start_time`/`end_time` nos motivos de rejeição.
- Regressões para URL, áudio, enfileiramento sem cortes, gate técnico e identidade de runtime.

### Validação da rodada

A coletiva de 33m38s gerou 12 exports H.264/AAC e o vídeo `OÚLTIMOANÁLISESRENAIS.mp4` gerou 30 exports antes do gate; o replay sobre os candidatos reais identificou 13/30 para revisão técnica. A amostra renal de 15 minutos processada após o gate concluiu com 3 exports H.264/AAC válidos. A suíte completa chegou a 293 testes aprovados; `py_compile`, `node --check` e `git diff --check` foram aprovados. A URL do YouTube foi enfileirada no modo áudio, mas o downloader foi bloqueado por anti-bot nesta sessão; nenhum cookie ou credencial foi usado.

## 1.4 — Gate de contexto autossuficiente antes da renderização

### Incluído

- Candidatos explicitamente marcados com `context_complete=false` agora permanecem disponíveis para revisão diagnóstica, mas não são renderizados como cortes prontos.
- O job registra quantos candidatos foram adiados em `render_deferred_context_count` e preserva o motivo e os `review_flags` em `render_rejections`.
- A mudança foi baseada em mídia real: no lote de 15 minutos do MP4 enviado, o comportamento anterior renderizou 4 candidatos, incluindo um trecho de 168,09 segundos que começava no meio da frase e tinha `context_complete=false`; após a alteração, 3 candidatos foram renderizados e esse trecho foi adiado.
- O SRT `0815(1).srt` foi parseado como referência externa, sem ser associado ao MP4.

### Validação da rodada

A suíte completa passou com `288 passed`; os testes focados do gate passaram com `24 passed`; `py_compile` e `git diff --check` foram aprovados. A repetição real concluiu com `3` exports H.264/AAC válidos, em comparação com `4` antes da alteração. O processamento da fonte completa de 84,1 minutos foi bloqueado pelo limite operacional do ambiente durante a transcrição CPU; o lote verificável de 15 minutos foi processado com timestamps gerados do áudio do próprio MP4.

## 1.3 — Gate de pergunta explícita e modo offline do Prompt 2

### Incluído

- Perguntas explícitas com `?` agora exigem resposta suficiente antes de um candidato ser considerado contextualmente completo.
- A flag explicável `question_requires_answer` é propagada pelo seletor e pelo ranker para revisão e diagnóstico.
- Regressões para pergunta sem resposta e para expansão até a resposta antes de avançar para a pauta seguinte.
- Prompt 2 atualizado para não presumir a versão `1.1`, registrar a versão real pelo arquivo `VERSION`, reconhecer a hipótese de payoff como concluída e continuar com melhorias offline quando navegador/Criadores/Corteiros estiverem bloqueados.
- Cópia versionada do Prompt 2 em [`PROMPT_2_EXECUTOR.md`](PROMPT_2_EXECUTOR.md).

### Validação da rodada

A suíte completa passou com `286 passed`; `py_compile` e `git diff --check` foram aprovados. Nenhum navegador, login, cookie, Reel publicado ou nova fonte longa foi necessário para esta alteração. A validação audiovisual da fonte longa do Garimpo permanece pendente.

## 1.2 — Gate de payoff e menor janela completa

### Incluído

- A duração-alvo voltou a ser tratada estritamente como uma dica suave: o seletor não encerra o candidato enquanto o pensamento/payoff estiver aberto.
- A expansão continua até encontrar a menor janela com contexto e payoff completos, sem incluir a pauta seguinte quando o bloco anterior já fecha naturalmente.
- Regressão editorial baseada no padrão observado nos outputs reais: hook forte que terminava antes da conclusão.
- A versão de runtime passa a identificar a especialização editorial desta rodada como `1.2`.

### Validação da rodada

O teste específico de concisão passou com `5 passed`; a suíte completa passou com `284 passed`; `py_compile` e `git diff --check` foram aprovados. A fonte longa do Garimpo foi localizada e o download autenticado foi solicitado, mas o Corteiros não concluiu no sandbox por limitação do helper Electron; nenhum Reel publicado foi usado como fonte de corte nesta rodada.

## 1.1 — Resiliência da análise de cenas e primeiro benchmark real

### Incluído

- Timeout configurável na detecção de cenas via `FURIA_SCENE_DETECTION_TIMEOUT_SECONDS`, com padrão de 120 segundos.
- A detecção de cenas passou a ignorar áudio desnecessário, tratar timeout/erro do ffmpeg e retornar uma linha de base segura (`[0.0]`) sem derrubar o job.
- Três testes de regressão para retorno normal, timeout e retorno não-zero do ffmpeg.
- Primeiro teste real com Reel público do Renan: download, FFprobe, transcrição com 57 segmentos e geração de três clipes verticais.
- Benchmark audiovisual dos três clipes para identificar cortes aprováveis, cortes que terminam antes do payoff e cortes que começam no meio da frase.
- Escada de ingestão legítima documentada no prompt mestre para YouTube bloqueado, plataformas públicas alternativas, Criadores/Campaign Hub e Corteiros.

### Validação da rodada

Os testes específicos passaram com `11 passed` e a suíte completa com `283 passed`; `py_compile` também foi aprovado. O job integrado após a correção permaneceu ativo, concluiu com `3` artefatos e deixou o servidor saudável. O benchmark real mostrou que a estabilidade melhorou, mas a seleção ainda precisa impedir finais antes do payoff e penalizar inícios fragmentados. A versão 1.1 foi publicada no commit `6349d37` após a atualização do estado persistente.

## 1.0 — Fundação do contrato de continuidade

### Incluído

- Fonte única de versão em [`VERSION`](../../VERSION), iniciada em `1.0`.
- Leitura da versão pelo servidor Flask, com exposição no console de progresso, na interface e em `/api/settings`.
- Contrato de versionamento em [`docs/VERSIONING.md`](../VERSIONING.md).
- Instruções de retomada para qualquer IA em [`AGENTS.md`](../../AGENTS.md).
- Estado atual persistente em [`PROJECT_STATE.md`](PROJECT_STATE.md).
- Decisões editoriais e técnicas em [`DECISIONS.md`](DECISIONS.md).
- Procedimento da próxima rodada em [`NEXT_CYCLE.md`](NEXT_CYCLE.md).
- Registro explícito de que vídeos públicos publicados nos perfis do Renan podem ser analisados como corpus audiovisual legítimo.
- Registro dos três formatos editoriais: `16:9 original`, `1:1 Alfinetei` e `fake tweet`.

### Validação concluída

A suíte completa foi executada com `280 passed`; `python -m py_compile app.py` foi aprovado; a versão foi carregada de `VERSION`; e o asset público do BlazeFace foi validado pelo tamanho e SHA-256 do manifesto. A documentação de estado foi atualizada após a publicação no commit `fbbe5ca`, na branch `manus/rebuild-opus-parity`.
