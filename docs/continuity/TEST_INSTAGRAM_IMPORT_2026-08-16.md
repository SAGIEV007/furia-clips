# Teste real de ingestão alternativa — 2026-08-16

## Fonte

O teste utilizou o Reel público de Renan Santos `https://www.instagram.com/reel/Davg97_tF4J/`, localizado pelo Campaign Hub como crosspost de um conteúdo do perfil `@renansantosmbl`. O endpoint de probe do Furia identificou a fonte com sucesso como extractor `Instagram`, id `Davg97_tF4J`, uploader `Renan Santos` e `is_live=false`.

## Importação

O endpoint `/api/source/import` do Furia iniciou e concluiu o download sem depender de CAPTCHA do YouTube. O MP4 gerado tinha 26.104.322 bytes, duração de 135,717778 segundos, vídeo H.264 720x1280 e áudio AAC 44,1 kHz estéreo. O arquivo foi mantido fora do Git.

## Transcrição

O endpoint `/api/process/transcribe` concluiu a transcrição local em português e gerou 57 segmentos timestampados, cobrindo 0:00–2:15. A transcrição contém fala de Renan sobre facções, punição e segurança pública, mas também possui erros de reconhecimento que exigem revisão quando nomes próprios e frases sensíveis forem usados em headline.

## Corte automático

Foi iniciado um job real com perfil Renan/MBL, formato `vertical_916`, auditoria `full` e contexto de concisão/autossuficiência. A etapa de transcrição foi executada, mas o servidor caiu durante a análise de cenas/renderização e não houve MP4 exportado. O log não registrou traceback; o processo desapareceu enquanto um `ffmpeg` de detecção de cenas estava ativo. O Furia foi reiniciado e a API voltou a responder HTTP 200.

## Decisão editorial e de prompt

O resultado confirmou que a ingestão alternativa por Instagram deve ser uma rota oficial de fallback quando o YouTube falhar. O prompt mestre foi atualizado com uma escada de ingestão que prioriza o downloader existente, depois plataformas públicas alternativas, painel Criadores/Campaign Hub, Corteiros e arquivo fornecido pelo usuário. A regra também exige FFprobe, hash, registro de origem, separação entre crosspost e live original e validação do pipeline antes de calibrar o ranking.

## Estado

Importação e transcrição: confirmadas. Corte/renderização end-to-end: bloqueados nesta rodada por queda do servidor durante análise de cenas. Código funcional não foi alterado nesta rodada; somente o prompt e esta documentação foram atualizados.
