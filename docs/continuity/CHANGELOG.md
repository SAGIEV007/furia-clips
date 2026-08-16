# Changelog de continuidade

## 1.9 — Prompt executor e paridade editorial via Campaign Hub

### Incluído

- Novo `docs/continuity/PROMPT_3_EXECUTOR_CHUB_PARITY.md`, prompt copiável para futuras IAs continuarem o Furia Clips com auditoria do checkout, hipótese única, testes, versionamento e publicação verificável.
- Contrato explícito para usar blocos QA-gated, transcrições, perguntas-gatilho, autossuficiência, payoff, riscos e destaques do Campaign Hub como benchmark e calibração fraca, sem chamada MCP direta no runtime.
- Regras de escopo que mantêm o Furia Clips focado em cortes precisos e contextuais e adiam um editor pós-renderização semelhante ao CapCut.
- Registro de padrões profissionais pesquisados em OpusClip, Descript e Riverside, traduzidos para foco por locutor/tópico, busca editorial, score explicável, presets de composição, preservação de evidência e diagnóstico de divergência.
- `AGENTS.md` atualizado para apontar o prompt executor vigente.

### Validação da rodada

A mudança é documental e operacional; nenhum módulo de processamento foi alterado. Foram conferidos o estado da branch, a versão 1.8, o prompt mestre, o prompt executor, o estado do projeto, o próximo ciclo, a linhagem do Campaign Hub e o contrato de versionamento. A validação automatizada final deve ser executada antes do commit.

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
