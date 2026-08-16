# Estado do projeto — Furia Clips

> Este arquivo é o ponto de entrada operacional para uma nova sessão ou uma nova IA. Atualize-o ao final de cada rodada verificável.

## Identidade atual

| Campo | Valor |
| --- | --- |
| Projeto | Furia Clips |
| Repositório | `SAGIEV007/furia-clips` |
| Versão pública | `1.7` |
| Fonte da versão | [`VERSION`](../../VERSION) |
| Branch de trabalho conhecida | `manus/rebuild-opus-parity` |
| Revisão registrada neste estado | pendente até o commit da release 1.7 |
| Última atualização deste documento | 2026-08-16 |
| Validação desta rodada | `303 passed`; testes focados `52 passed`; `py_compile`, `node --check`, prova local do proxy FFmpeg e `git diff --check` em fechamento |
| Asset validado | `models/blaze_face_short_range.tflite`, 229746 bytes, SHA-256 conforme manifesto |
| Objetivo | Gerar cortes do Renan Santos/MBL concisos, autossuficientes e contextualmente completos |

Esta é a revisão publicada desta rodada de continuidade. O commit de código `2ac5b1c` foi verificado localmente e publicado na branch de trabalho; esta atualização documental registra essa referência sem reescrever o commit de código.

## Estado funcional conhecido

O projeto é uma aplicação local Flask com Socket.IO, SQLite, FFmpeg/FFprobe, faster-whisper, MediaPipe/BlazeFace, yt-dlp e fallbacks locais/online opcionais. O princípio de timeline canônica mantém os intervalos derivados vinculados ao vídeo original.

O pipeline conhecido contém ingestão/validação da fonte, download público, transcrição com timestamps, análise de contexto, geração de candidatos, ranking editorial explicável, revisão humana, renderização por preset, legendas, validação audiovisual e persistência de jobs/feedback.

A evolução editorial recente concentrou-se em recuperação de contexto, tratamento de referências anafóricas como “isso” e “foi ali que”, completude de pergunta/resposta, gates antes do score e preferência por menor janela suficiente. As alterações locais existentes devem ser preservadas e avaliadas antes de qualquer commit.

## Formatos editoriais

O sistema deve distinguir:

| Formato | Intenção |
| --- | --- |
| `16:9 original` | Preservar paisagem/evidência visual e usar headline curta mais descritiva. |
| `1:1 Alfinetei` | Composição quadrada, palavra de impacto no topo e headline branca integrada; texto mais enxuto. |
| `fake tweet` | Simular publicação em primeira pessoa do Renan somente quando a fala sustentar essa voz. |

## Corpus e aprendizado

O Campaign Hub disponibiliza dados públicos dos perfis `@renansantosmbl`, `@renansantosreserva` e contas relacionadas. Priorize vídeos em que Renan fala, depois em que aparece, depois Reserva/Renan e somente em último caso MBL geral.

Para cada exemplo, relacione tema, tese, intervalo, transcrição, legenda, headline, formato, sinais visuais, publicação e métricas. Um corte publicado é evidência de seleção editorial, mas deve ser separado de “performou bem” e “aprovado diretamente pelo usuário”.

## Validações já conhecidas

O histórico da sessão anterior registrou suíte com 278 testes aprovados e smoke tests de clipping com fixtures reais. Nesta rodada, a suíte completa foi executada novamente: **284 testes passaram** antes da release 1.3. Também foram validados `py_compile app.py`, a fonte única `VERSION` e o asset público do BlazeFace. A próxima IA ainda deve repetir os testes após qualquer alteração, pois nenhum resultado histórico substitui a execução atual.

## Alterações locais a investigar

Antes da continuidade, examine o `git status`. O estado conhecido antes desta documentação continha alterações locais em:

- `modules/clip_selector.py`;
- `modules/editorial_ranker.py`;
- `tests/test_editorial_ranker.py`;
- `tests/test_editorial_concision.py`.

Não descarte essas alterações. Determine se já são parte do trabalho da rodada, rode a suíte e faça commit somente após verificar o diff.

## Resultado da rodada real 1.2

A primeira melhoria especializada do Prompt 2 alterou o `clip_selector`: a duração-alvo não encerra mais um candidato enquanto contexto ou payoff estiverem incompletos. A janela continua até encontrar o menor intervalo completo, sem incluir a pauta seguinte quando o bloco anterior já fecha naturalmente. A hipótese foi reproduzida com um teste de caso real e a suíte passou com 284 testes. O Campaign Hub/Garimpo localizou a live longa `RENAN SANTOS EM CHAPECÓ - SC`, com bloco de 10:51 iniciando em 15:23; o download autenticado foi solicitado, mas o helper Corteiros não concluiu no sandbox. Nenhum Reel publicado foi usado como fonte operacional nesta rodada.

## Resultado da rodada 1.7

A hipótese desta rodada foi: **quando o editor fornece uma transcrição e pede contexto ou headline específica, o Furia deve usar esse texto de forma inequívoca, evitar o limite multimodal com uma cópia compactada e preservar evidências para calibração posterior**.

A transcrição manual/importada agora recebe proveniência explícita, é usada como timeline canônica e aparece no dossiê como confirmada. A análise audiovisual opcional passa a usar uma cópia temporária de até 640 px, com amostragem adaptativa e áudio mono a 16 kHz; o original não é modificado. O cancelamento pode interromper a compactação e as janelas HTTP foram reduzidas para não deixar o job bloqueado por longos períodos.

Cada sessão passa a arquivar, fora do GitHub, a transcrição integral e de seleção, o dossiê de contexto, headlines geradas, decisões de headlines, decisões de clips e o manifesto de proveniência. O console mantém histórico completo da sessão para cópia, enquanto o painel de contexto informa a origem da transcrição, o proxy e o prior do Campaign Hub.

O caso editorial real do corte sobre o ato e a ameaça ganhou candidatos específicos como “NÃO TENHAM MEDO DE IR AO ATO” e “A AMEAÇA NÃO VAI IMPEDIR O ATO”, em vez do fallback genérico “IMPASSE DA SEGURANÇA”. A regressão passou sem depender do Gemini.

A suíte completa passou com **303 testes**. A prova local do proxy reduziu um vídeo sintético de 49.171 para 16.266 bytes. Não foi usado token, mídia real ou transcrição privada no commit.

## Resultado da rodada 1.6

A hipótese desta rodada foi: **uma fonte longa que começa com propaganda ou pré-roll não deve contaminar a seleção editorial com candidatos iniciados antes do conteúdo de live**. Foi criado o detector conservador `modules/source_boundary.py`, integrado antes da análise de contexto, mantendo `full_transcription` arquivada e usando `selection_transcription` somente a partir da fronteira segura.

No baseline do projeto 42, a amostra renal de 15 minutos gerava 3 exports e incluía o corte promocional `1. se não ser na rua, porque pode ser.mp4`, iniciado em `66,0333s` e terminando em `215,29s`. No benchmark final v2, projeto 47, a fronteira foi detectada em `169,5s` com confiança `0,90`; foram gerados 4 exports, nenhum iniciado antes dessa marca. O resultado foi reproduzido após o endurecimento que impede cortar uma saudação genérica isolada. Todos os quatro arquivos foram validados como H.264/AAC 1920×1080 por FFprobe.

A regressão adicionada confirma ainda que uma coletiva sem intro não recebe fronteira artificial e que `boa noite a todos` isolado não basta para descartar os primeiros segundos de uma fonte. A limitação conhecida é que `source_boundary` ainda não é uma coluna própria na tabela `projects`; o diagnóstico fica disponível no evento de seleção e nos artefatos do job. A suíte completa desta revisão candidata passou com **299 testes**.

## Resultado da rodada 1.5

A rodada implementou a rota assíncrona `POST /api/source/transcribe`, com áudio por padrão e nenhum corte, além do botão correspondente no frontend. O smoke real com a URL do usuário confirmou o job em `media_type=audio` e falhou de forma sanitizada no anti-bot do YouTube sem usar cookies ou credenciais.

A hipótese editorial foi transformar `technical_gate_status=review` em uma fronteira de renderização. No projeto renal real com 30 candidatos, 17 seriam renderizáveis e 13 seriam adiados: 10 por pergunta sem ponte validada, 2 por alegação sensível sem contexto/evidência e 1 pelos dois motivos. Uma amostra renal de 15 minutos processada após o gate concluiu com 3 exports H.264/AAC 1920×1080. O replay também corrigiu a preservação dos intervalos persistidos em `start_time`/`end_time`.

A fonte renal completa foi transcrita localmente com faster-whisper base em dez lotes: 1.429 segmentos, 86.837 caracteres, qualidade estrutural 92/100, três sobreposições e sem validação semântica automática. A análise audiovisual multimodal devolvida para o arquivo foi genérica e não foi usada como evidência específica.

## Resultado da rodada 1.4

A hipótese desta rodada foi: **um candidato explicitamente marcado como `context_complete=false` não deve ser renderizado como corte pronto**. O novo gate mantém o candidato no diagnóstico de revisão, mas o adia antes do `VideoCutter` e registra `render_deferred_context_count` e os motivos em `render_rejections`. No mesmo lote de 15 minutos, o baseline v1.3 gerou 4 exports, incluindo um trecho de 168,09 segundos com início no meio da frase e contexto incompleto; a repetição v1.4 gerou 3 exports e adiou esse trecho. Os três exports foram validados com FFprobe como H.264/AAC 1920×1080. A suíte passou de 286 para 288 testes.

O MP4 operacional tem duração de aproximadamente 84,1 minutos, vídeo AV1 1920×1080 e áudio AAC estéreo 44,1 kHz. A transcrição integral CPU foi tentada e interrompida pelo limite operacional do ambiente; o lote de 15 minutos foi transcrito do áudio do próprio MP4 com 357 segmentos. O SRT externo foi parseado em separado e não foi usado como legenda do MP4.

## Próxima rodada recomendada

Usar os candidatos reais da coletiva e da live renal para calibrar detecção de erros semânticos do ASR em nomes próprios, entidades políticas e termos raros antes de gerar headlines. Marcar baixa confiança lexical para revisão humana e comparar a transcrição local com uma fonte corrigida quando disponível. O Estúdio de Texto de Arte permanece adiado; Reels publicados continuam `reference_only` e somente fontes longas/cruas são `processing_source`.

Depois da execução, atualize este arquivo com a versão, commit, branch, testes, vídeos/análises realizados, métricas antes/depois e a próxima hipótese. As versões anteriores `1.2` e os commits `1860276`, `a6846f9` e `2c92b09` permanecem no histórico; a release `1.3` foi publicada no commit `aa678fe`; a release `1.4` está registrada no commit `2528cec`; esta release `1.5` está registrada no commit `337e2dd`; a release `1.6` está registrada no commit `2ac5b1c` da branch `manus/rebuild-opus-parity`.
