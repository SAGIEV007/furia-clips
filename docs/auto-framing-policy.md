# Política de enquadramento automático

O Furia Clips deve priorizar a pessoa que está falando, mas nunca sacrificar a identificação do locutor para forçar o formato vertical. O objetivo é gerar um reframe 9:16 publicável apenas quando a confiança visual e temporal for suficiente.

## Regras de decisão

| Situação detectada | Saída | Motivo |
|---|---|---|
| Uma única face detectada de forma estável durante o clip, com confiança mínima e cobertura suficiente | Reframe 9:16 com rastreamento suave | O locutor visual está suficientemente identificado |
| Mais de uma face, split-screen ou troca frequente de câmera | 16:9 original | A detecção simples não consegue atribuir voz e fala a uma face com segurança |
| Nenhuma face, MediaPipe/OpenCV indisponível ou detecção instável | 16:9 original | Evita crop centralizado que pode cortar o locutor |
| Sobreposição de falas, pergunta e resposta com locutores diferentes | 16:9 original por padrão; reframe apenas se a faixa temporal de cada locutor for confiável | A voz não deve ser inferida apenas pela maior face |
| Face detectada mas com baixa confiança, pouca cobertura ou posição fora do crop possível | 16:9 original | Evita enquadramento errado ou rosto parcialmente cortado |

## Critérios mínimos para reframe

O clip deve ter, no mínimo, três observações faciais válidas, cobertura de pelo menos 60% do intervalo útil e confiança média de 0,60. A posição deve variar pouco; grandes saltos entre observações devem invalidar o reframe, pois indicam troca de pessoa ou de câmera. Quando esses critérios não forem atendidos, `original_aspect_indices` deve marcar o clip e o renderizador deve preservar a resolução e o aspecto da fonte.

## Implementação

O rastreador continua sendo um sinal visual de apoio. A identificação editorial do Renan, da pergunta e da resposta vem da transcrição, do Gemini e do contexto de entrevista. A política de enquadramento não afirma diarização perfeita. O resultado deve registrar `framing_mode` como `face_tracking`, `center_crop` ou `original_16_9`, permitindo revisão rápida pelo editor.
