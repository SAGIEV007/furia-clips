# Estado do projeto — Furia Clips

> Este arquivo é o ponto de entrada operacional para uma nova sessão ou uma nova IA. Atualize-o ao final de cada rodada verificável.

## Identidade atual

| Campo | Valor |
| --- | --- |
| Projeto | Furia Clips |
| Repositório | `SAGIEV007/furia-clips` |
| Versão pública | `1.1` |
| Fonte da versão | [`VERSION`](../../VERSION) |
| Branch de trabalho conhecida | `manus/rebuild-opus-parity` |
| Revisão registrada neste estado | `6349d37` — `fix: make scene detection resilient` |
| Última atualização deste documento | 2026-08-16 |
| Validação desta rodada | `283 passed`; `py_compile` aprovado; job real concluído com 3 clipes; servidor saudável após renderização |
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

## Resultado da rodada real 1.1

A detecção de cenas passou a ter timeout configurável, ignorar áudio desnecessário e tratar timeout/erro do ffmpeg com uma linha de base segura, evitando que metadados visuais sejam pré-requisito do corte. O primeiro benchmark real baixou um Reel público do Renan via Instagram pelo próprio Furia, validou MP4 H.264/AAC vertical, gerou 57 segmentos de transcrição e exportou três clipes. A análise audiovisual aprovou dois cortes com ressalvas e identificou que um termina antes do payoff e outro começa no meio da frase; esses casos viram regressões editoriais da próxima rodada.

## Próxima rodada recomendada

A próxima hipótese única é: **a seleção deve rejeitar ou expandir automaticamente qualquer candidato cujo início seja fragmentado ou cujo final ocorra antes do payoff**, mesmo que a janela tenha hook e alta pontuação. Criar regressões com os três cortes reais, comparar as janelas atuais com janelas expandidas e medir completude, concisão e fidelidade da headline.

Depois da execução, atualize este arquivo com a versão, commit, branch, testes, vídeos/análises realizados, métricas antes/depois e a próxima hipótese. A versão `1.1` foi publicada no commit `6349d37` da branch `manus/rebuild-opus-parity`, após `283 passed`, `py_compile` aprovado e smoke test real com três clipes exportados.
