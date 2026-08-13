# Diagnóstico de download e transcrição — 13/08/2026

## Log analisado

O download do vídeo público foi concluído em até 1080p. A porcentagem chegou a 100% e depois voltou para aproximadamente 33% porque o yt-dlp baixou streams separados de vídeo e áudio; cada stream possui seu próprio progresso. A segunda porcentagem não representava uma regressão do arquivo, mas o início do segundo stream seguido da etapa de merge.

A análise multimodal Gemini recebeu o arquivo e avançou até o processamento, mas retornou HTTP 503 por alta demanda do serviço. Isso não indica chave inválida, vídeo corrompido ou erro de download. O fallback correto foi acionado e, neste log, a execução parou na inicialização do faster-whisper em CPU; a mensagem agora identifica explicitamente essa etapa e mantém o botão de cancelamento disponível.

## Correções publicadas

| Área | Antes | Depois |
| --- | --- | --- |
| Progresso | Um percentual global parecia voltar de 100% para 33%. | O console identifica `vídeo`, `áudio`, transferência concluída e merge MP4. |
| Merge | A mensagem genérica não distinguia término de stream de união final. | Eventos de postprocessor mostram “Unindo vídeo e áudio” e “Arquivo final pronto”. |
| HTTP 503 | O log apenas dizia que o Gemini não concluiu. | A mensagem informa sobrecarga temporária e que o arquivo não será reenviado. |
| Fallback | O início do Whisper era pouco explícito. | O console mostra motor, dispositivo, modelo e disponibilidade do cancelamento. |
| Regressão | Não havia teste para streams separados e merge. | Foram adicionados testes para rotulagem e mensagens das etapas. |

## Operação esperada após a atualização

Em uma nova execução, o log poderá mostrar percentuais separados, por exemplo `[Download · vídeo] 42,5%` e `[Download · áudio] 18,0%`. Depois aparecerá a mensagem de união do arquivo final. A etapa de transcrição mostrará primeiro a tentativa Gemini; se houver HTTP 503, o sistema seguirá sem reenviar o vídeo, tentará legenda pública quando disponível e então iniciará o Whisper local com precisão compatível com CPU.

## Limitação operacional

HTTP 503 é uma indisponibilidade temporária do serviço Gemini. O retry permanece limitado e usa backoff para não aumentar a pressão sobre o serviço. Para lives longas, o Whisper em CPU continua sendo mais lento; o usuário pode interromper a operação pelo botão **Parar operação** e fornecer uma transcrição timestampada manual para evitar nova transcrição.
