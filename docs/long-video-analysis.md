# Análise de vídeos longos e fontes de entrada

## Objetivo

O Furia Clips parte do perfil editorial `renan_santos_politics` e cria uma camada de contexto antes do ranking. O sistema não depende mais de um prompt manual para entender que o material é político; o campo do editor serve apenas para priorizar um tema específico.

A primeira camada é determinística. Ela normaliza a timeline, identifica perguntas por pontuação e forma, observa pausas e sobreposições temporais, procura referências a Renan/Santos/MBL, agrupa janelas prováveis de entrevista e constrói candidatos preliminares de pergunta–resposta. Esses sinais são explicáveis e não afirmam reconhecimento perfeito de locutor.

Se Gemini estiver configurado e o backend estiver em `auto` ou `gemini`, a aplicação tenta a análise multimodal online antes da seleção. O vídeo é enviado pela Files API, o processamento é aguardado e a resposta pede descrição global, segmentos com timestamps, observações de participantes, momentos de pergunta–resposta e sinais de áudio/imagem. Quando a resposta contém segmentos utilizáveis, Whisper é pulado; caso contrário, a aplicação recorre ao Whisper local e mantém os sinais multimodais como enriquecimento. Sem chave ou sem internet, o caminho local continua disponível.

## Transcrição manual

Na interface, abra **Fonte da análise → Transcrição**. É possível colar ou importar `.txt`, `.srt` e `.vtt`. O formato Tactiq esperado é uma linha por segmento, por exemplo:

```text
00:12:34.500 Pergunta do entrevistador sobre segurança pública?
00:12:40.200 Renan explica a proposta, apresenta a consequência e conclui.
```

Após clicar em **Usar transcrição**, o parser informa quantos segmentos foram reconhecidos. A transcrição é enviada como segmentos canônicos no próximo corte e o console registra que Whisper não será executado.

## Link público

Na aba **Link público**, informe uma URL `http(s)` acessível sem login, preferencialmente um vídeo público do YouTube. O botão **Verificar** obtém metadados e duração quando o extrator disponível consegue fazê-lo. **Importar** baixa a fonte para o workspace com yt-dlp e mantém o caminho dentro de `workspace/uploads`.

O fluxo não aceita cookies pessoais, credenciais, bypass de DRM, bypass de paywall, URL `file://`, localhost, endereços privados ou conteúdo privado/restrito. A disponibilidade de cada plataforma depende do extrator e dos termos aplicáveis. Para renderizar cortes, a ferramenta ainda precisa de mídia local; quando download parcial não for tecnicamente possível, o fallback é baixar a mídia completa de maneira transparente.

## Entrevistas longas

Em uma live com mais de duas horas, uma entrevista de aproximadamente quarenta minutos pode ser localizada a partir de concentração de perguntas, referências nominais, turnos, pausas, assunto e sinais multimodais. Um corte que contém apenas uma resposta é penalizado quando a pergunta for necessária para compreender o tema. O ranking também rejeita começo no meio da frase, término sem payoff, fala sobreposta com inteligibilidade baixa, locutor incerto e repetição de janela.

Tom, volume, risos, aplausos, música e tensão são sinais auxiliares. Eles não substituem a avaliação do contexto nem garantem diarização. A revisão humana continua sendo necessária para casos ambíguos, especialmente quando duas pessoas falam simultaneamente ou quando o vídeo contém várias vozes parecidas.

## Limitações e referências

A análise multimodal depende da disponibilidade, cota, tamanho do arquivo e latência do Gemini. A documentação oficial recomenda a Files API para arquivos grandes e vídeos longos, descreve timestamps no formato `MM:SS` e informa que o modelo analisa áudio e imagem, mas também alerta que amostragens visuais e recuperação de muitos pontos específicos não são perfeitas [1] [2]. O yt-dlp é utilizado apenas como biblioteca de fontes públicas suportadas; FFmpeg/ffprobe continuam necessários para merge e renderização [3].

## Referências

[1]: https://ai.google.dev/gemini-api/docs/video-understanding — Google AI for Developers, Video understanding.

[2]: https://ai.google.dev/gemini-api/docs/long-context — Google AI for Developers, Long context.

[3]: https://github.com/yt-dlp/yt-dlp — yt-dlp, documentação e opções de download.
