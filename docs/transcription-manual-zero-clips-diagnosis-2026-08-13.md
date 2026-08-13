# Diagnóstico — transcrição manual, Gemini e zero clips

## O que aconteceu

O vídeo `URGENTE: A VERDADE SOBRE A FILIAÇÃO DO FLÁVIO` foi importado e a chamada `POST /api/transcript/parse` terminou com HTTP 200, mas o frontend informou **1 segmento**. Em seguida, o pipeline classificou o foco como Renan Santos mesmo sem prova suficiente, reenviou o vídeo inteiro ao Gemini, aguardou o processamento online e recebeu HTTP 400 por excesso de tokens de entrada. Depois, a seleção recebeu apenas um bloco muito curto/insuficiente, descartou candidatos abaixo da duração mínima e terminou com **0 clips**.

O log também registrou `"NoneType" object has no attribute "split"` na detecção de cenas. A origem era `VideoCutter.detect_scenes()` assumir que `subprocess.run(...).stderr` sempre seria uma string. Em algumas execuções Windows esse campo veio vazio/None.

Por fim, a seleção tentou o modelo `gemini-2.0-flash` depois da primeira resposta inválida, mas esse modelo já não estava disponível na API usada. Isso gerou um 404 adicional e atrasou o fallback local.

## Correções implementadas

| Problema | Correção |
|---|---|
| Timestamp inline ou texto colado em um único parágrafo | O parser reconhece timestamps inline, além do formato por linha, SRT e VTT. |
| Último/único segmento terminava em dois segundos | Quando a duração do vídeo está disponível e existe apenas um segmento sem fim explícito, o segmento se estende até a duração do vídeo. |
| Duração ausente no navegador | O frontend envia `video_path`; o backend usa ffprobe quando necessário antes de interpretar a transcrição. |
| Foco fixo em Renan Santos | O foco agora pode ser `auto`, `renan_santos` ou `generic_political`; o modo automático só assume Renan quando há referência textual suficiente. |
| Reenvio desnecessário do vídeo ao Gemini | Com transcrição manual, a análise multimodal adicional fica desligada por padrão. O usuário pode reativá-la por configuração quando realmente quiser análise visual/sonora. |
| Detecção de cenas quebrando com stderr None | O detector trata stderr vazio e bytes com decodificação segura. |
| Modelo Gemini obsoleto | O seletor não tenta mais `gemini-2.0-flash`; usa o modelo atual configurado e segue para fallback em caso de erro. |
| Nenhum clip por falta de duração | Um segmento manual longo válido agora pode gerar um candidato com duração entre os limites configurados. |

## Operação recomendada

Para vídeos que não são centrados no Renan, selecione **Foco Editorial → Político genérico / participante principal**. Cole ou importe uma transcrição com timestamps; o ideal é usar linhas no formato `00:12:34.000 Texto` ou SRT/VTT. Se o vídeo estiver selecionado na biblioteca, a aplicação tentará obter sua duração com ffprobe e usará essa informação para completar um segmento único.

Quando a transcrição manual já estiver pronta, o Furia Clips não precisa reenviar o vídeo ao Gemini. Ele usa a timeline fornecida, análise de energia, layout, mudanças de cena e ranking local/online dos blocos. Isso reduz latência, evita o limite de tokens multimodal e torna o fluxo reproduzível sem depender de uma segunda análise do arquivo.

## Limitação de vídeos longos

O limite observado no log foi do **contexto multimodal do Gemini**, não do tamanho físico do arquivo nem do plano Google AI Pro. O upload do arquivo pode terminar normalmente, mas a etapa que transforma o vídeo inteiro em sinais multimodais pode exceder o limite de tokens do modelo. A solução operacional é usar transcrição timestampada e analisar por janelas/candidatos, em vez de reenviar uma live inteira como um único pedido multimodal.

## Validação

A suíte local passou com **86 testes**, incluindo parser inline, foco genérico, segmento manual longo, stderr vazio do ffmpeg, prioridade Gemini e regressões de importação.
