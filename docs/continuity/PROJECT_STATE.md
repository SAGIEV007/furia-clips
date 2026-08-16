# Estado do projeto — Furia Clips

> Este arquivo é o ponto de entrada operacional para uma nova sessão ou uma nova IA. Atualize-o ao final de cada rodada verificável.

## Identidade atual

| Campo | Valor |
| --- | --- |
| Projeto | Furia Clips |
| Repositório | `SAGIEV007/furia-clips` |
| Versão pública | `1.2` |
| Fonte da versão | [`VERSION`](../../VERSION) |
| Branch de trabalho conhecida | `manus/rebuild-opus-parity` |
| Revisão registrada neste estado | `a6846f9` — `test: align runtime assertions with v1.2` |
| Última atualização deste documento | 2026-08-16 |
| Validação desta rodada | `284 passed`; `py_compile` aprovado; `git diff --check` aprovado; fonte longa do Garimpo localizada; transcrição do Acervo consultada; download direto bloqueado pelo YouTube e download autenticado não concluído pelo helper Corteiros no sandbox |
| Asset validado | `models/blaze_face_short_range.tflite`, 229746 bytes, SHA-256 conforme manifesto |
| Objetivo | Gerar cortes do Renan Santos/MBL concisos, autossuficientes e contextualmente completos |

Esta é a revisão publicada desta rodada de continuidade. Depois de qualquer commit novo, substitua-a pelo hash real e registre o resultado dos testes.

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

O histórico da sessão anterior registrou suíte com 278 testes aprovados e smoke tests de clipping com fixtures reais. Nesta rodada, a suíte completa foi executada novamente: **280 testes passaram**. Também foram validados `py_compile app.py`, a fonte única `VERSION` e o asset público do BlazeFace. A próxima IA ainda deve repetir os testes após qualquer alteração, pois nenhum resultado histórico substitui a execução atual.

## Alterações locais a investigar

Antes da continuidade, examine o `git status`. O estado conhecido antes desta documentação continha alterações locais em:

- `modules/clip_selector.py`;
- `modules/editorial_ranker.py`;
- `tests/test_editorial_ranker.py`;
- `tests/test_editorial_concision.py`.

Não descarte essas alterações. Determine se já são parte do trabalho da rodada, rode a suíte e faça commit somente após verificar o diff.

## Resultado da rodada real 1.2

A primeira melhoria especializada do Prompt 2 alterou o `clip_selector`: a duração-alvo não encerra mais um candidato enquanto contexto ou payoff estiverem incompletos. A janela continua até encontrar o menor intervalo completo, sem incluir a pauta seguinte quando o bloco anterior já fecha naturalmente. A hipótese foi reproduzida com um teste de caso real e a suíte passou com 284 testes. O Campaign Hub/Garimpo localizou a live longa `RENAN SANTOS EM CHAPECÓ - SC`, com bloco de 10:51 iniciando em 15:23; o download autenticado foi solicitado, mas o helper Corteiros não concluiu no sandbox. Nenhum Reel publicado foi usado como fonte operacional nesta rodada.

## Próxima rodada recomendada

A próxima hipótese única é: **usar blocos longos do Garimpo como referência operacional para calibrar a recuperação de setup, pergunta/resposta, antecedente anafórico e headline, sem recortar Reels publicados novamente**. Primeiro resolver ou contornar legitimamente a aquisição do MP4 longo; depois comparar os candidatos do Furia com os intervalos do Garimpo.

Depois da execução, atualize este arquivo com a versão, commit, branch, testes, vídeos/análises realizados, métricas antes/depois e a próxima hipótese. A versão `1.2` foi publicada no commit `1860276`; o alinhamento dos testes de runtime foi publicado no commit `a6846f9`, ambos na branch `manus/rebuild-opus-parity`. O ciclo 2 manteve `284 passed`, `py_compile` e `git diff --check` aprovados.
