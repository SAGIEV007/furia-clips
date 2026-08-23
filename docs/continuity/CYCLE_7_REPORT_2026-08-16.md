# Relatório do ciclo 7 — Furia Clips 1.8

## Hipótese única

Uma fonte AV1 e uma transcrição automática válida não podem produzir zero cortes por falha de decodificação visual ou por perda do status de cobertura quando a transcrição integral é convertida em uma visão de seleção.

## Fonte e baseline

A fonte pendente identificada foi `RENAN SANTOS — BP NAS ELEIÇÕES`, com aproximadamente 84 minutos, vídeo AV1 1920×1080 e áudio AAC. A tentativa integral encerrou o servidor do ambiente durante a transcrição CPU. Para manter a validação reproduzível, foi criada uma amostra real de 15 minutos a partir do MP4 original, sem alterar a fonte.

No primeiro lote da amostra, a transcrição produziu 247 segmentos e 5 candidatos editoriais. Nenhum export foi gerado. A reprodução do pipeline mostrou que os 5 candidatos tinham sido adiados porque a visão de seleção perdeu os metadados de cobertura, foi classificada como `unknown` e recebeu o gate técnico “identidade temporal da transcrição não validada”.

| Medição | Antes da correção | Depois da correção |
|---|---:|---:|
| Candidatos encontrados | 5 | 5 candidatos preservados |
| Candidatos renderizáveis | 0 | 4 |
| Exports válidos | 0 | 4 |
| Erros AV1 no log | repetidos | não observados |
| Suíte completa | — | 306 passed |

## Correções implementadas

O fluxo de transcrição agora usa a saída automática já obtida como transcrição canônica e só chama o Whisper quando ainda não existe uma transcrição válida. A cobertura e a proveniência são calculadas depois dessa etapa final, não antes de uma possível retranscrição. Ao remover pré-roll, a transcrição de seleção preserva cobertura, proveniência e origem da transcrição completa.

O FFmpeg passou a receber `-hwaccel none` nas etapas de detecção de cenas, análise de layout e renderização. Para fontes AV1, o caminho OpenCV/MediaPipe é evitado quando o layout não pode ser validado de modo confiável; o fallback preserva o enquadramento original e informa a decisão no log.

## Resultado real

O replay final da amostra BP gerou quatro exports H.264/AAC em 1920×1080, com durações aproximadas de 138,8 s, 40,4 s, 26,3 s e 27,2 s. Um intervalo editorial real também foi renderizado diretamente com decodificação AV1 por software e validado por FFprobe.

Os quatro cortes antigos do projeto completo BP foram reanalisados localmente pelo contexto especializado em Renan/MBL e pelo Estúdio de Texto. Essa reanálise confirmou foco em Renan Santos, 53 perguntas detectadas e 49 candidatos pergunta–resposta, mas também confirmou que a transcrição local contém erros semânticos como “TSS” no lugar de TSE e “filhação” em lugar de filiação. Isso reforça a hipótese seguinte de revisão semântica do ASR antes de headlines definitivas.

O Campaign Hub foi consultado pelo snapshot local como prior agregado fraco e explicável. Ele influenciou padrões de hook e família editorial, mas não substituiu contexto, payoff, validação temporal ou decisão humana.

## Validações

A suíte completa passou com 306 testes. Os testes focados de fronteira, cobertura, contexto, detecção de cenas, layout e AV1 passaram com 26 testes. Também foram aprovados `py_compile`, extração real de frame AV1 por software, renderização real H.264/AAC e verificação FFprobe dos quatro exports.

## Limitações e classificação

Foi **confirmado** que o bug de cobertura causava o bloqueio indevido dos cinco candidatos e que o AV1 provocava erros repetidos em caminhos visuais. Foi **corrigido** o fluxo de transcrição, a propagação de cobertura e a decodificação visual por software. Foi **validado** um lote real de 15 minutos e a reanálise dos quatro cortes antigos do BP. A transcrição integral e o novo processamento completo de 84 minutos ficaram **não verificados nesta rodada** porque o ambiente encerrou o servidor durante a operação longa; nenhum resultado integral foi apresentado como concluído.

A próxima hipótese única permanece a marcação de baixa confiança lexical para nomes próprios, entidades políticas e termos raros antes da geração de headlines, sem misturar essa etapa com novos presets ou o Estúdio de Texto de Arte.
