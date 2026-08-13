# Pesquisa técnica para a evolução solicitada — 2026-08-13

## Evidências externas

1. O yt-dlp fornece binários oficiais para Windows, Linux e macOS, suporta milhares de sites e recomenda FFmpeg/ffprobe para mesclar vídeo e áudio quando as fontes são separadas. O projeto também documenta atualização por canal e uso de templates de saída. Fonte: https://github.com/yt-dlp/yt-dlp

2. A documentação oficial do Gemini Video Understanding recomenda a Files API para arquivos grandes ou vídeos longos, com upload, espera até o estado ACTIVE e depois uma chamada de análise. A documentação informa suporte a vídeo e áudio, timestamps no formato MM:SS, análise multimodal e entrada direta de URLs públicas do YouTube em prévia. Para vídeos públicos do YouTube, o limite gratuito documentado é de até 8 horas de vídeo por dia; URLs privadas ou não listadas não são aceitas pela entrada direta. Fonte: https://ai.google.dev/gemini-api/docs/video-understanding

3. A documentação de long context do Gemini descreve uso para perguntas e respostas em vídeo longo, recomendação de conteúdo e personalização, mas alerta que a recuperação de muitos pontos específicos pode perder precisão e que o custo/latência crescem com contexto e quantidade de consultas. Fonte: https://ai.google.dev/gemini-api/docs/long-context

## Implicações para o Furia Clips

- O fluxo por link deve aceitar primeiro URLs públicas do YouTube; para outras plataformas, deve baixar localmente com yt-dlp quando o extrator suportar o domínio, sempre com aviso de direitos e sem prometer disponibilidade universal.
- A análise multimodal de vídeo longo deve ser feita por etapas: inspeção global, transcrição/segmentação, candidatos por unidades de pensamento e validação multimodal somente nos candidatos. Enviar toda a live repetidamente ao modelo aumenta latência e custo.
- A transcrição manual no formato Tactiq, com timestamp no início de cada linha, deve ser aceita como fonte de alta prioridade e convertida para segmentos canônicos sem exigir reprocessamento do áudio.
- Gemini pode analisar tom/áudio e imagem, mas não substitui diarização e detecção precisa de sobreposição de fala. O pipeline deve combinar sinais de áudio, pausas, VAD, mudanças de energia e, quando disponível, identificação de turnos; a decisão final continua sendo editorial e revisável.
