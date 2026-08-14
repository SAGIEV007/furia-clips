# Política editorial do planejador visual — 14/08/2026

## Finalidade

O planejador visual transforma sinais de layout e tracking em uma decisão serializável por clip. Ele não reconhece pessoas com certeza, não valida alegações políticas e não tenta substituir a revisão do editor. Sua função é impedir o erro mais caro do fluxo atual: aplicar um crop vertical a uma entrevista, split-screen, card, B-roll ou peça institucional e remover justamente o elemento que explica a fala.

## Decisão conservadora

| Família | Decisão padrão | Motivo apresentado ao editor |
| --- | --- | --- |
| `single_face` | Permitir 9:16 ou 1:1 quando tracking tem cobertura, confiança e estabilidade suficientes | Uma única face permanece estável e há evidência suficiente para acompanhar o locutor |
| `multi_speaker` | Preservar a proporção original | A pergunta, a resposta ou a reação de outro participante pode ser perdida |
| `split_screen` | Preservar a proporção original | Os dois lados da composição fazem parte do argumento ou da embalagem |
| `text_card` | Preservar a proporção original | Card, headline, borda ou texto visual pode ser cortado |
| `b_roll` | Preservar a proporção original | A evidência externa precisa permanecer ligada à fala e ao retorno do locutor |
| `institutional` | Preservar a proporção original e exigir revisão | A peça pode ser conduzida por montagem, cartelas, música, assinatura e áreas de margem |
| `unknown` | Preservar a proporção original e exigir revisão | Não existe evidência suficiente para alegar que um crop é seguro |

## Contrato retornado

Cada decisão possui `layout_family`, `output_aspect`, `target_aspect`, `reframe_allowed`, `confidence`, `review_required`, `reason_code`, `reason`, `safe_area` e `signals`. O resultado do renderizador mantém esse plano em `layout_plan`, além do campo histórico `framing_mode`. Assim, o HUD pode mostrar não apenas “vertical” ou “original”, mas também **por que** a escolha foi feita e se o editor deve revisar.

A confiança expressa a qualidade dos sinais disponíveis, não a certeza semântica sobre o vídeo. Uma decisão `original` com confiança alta significa que preservar a composição é uma escolha segura; não significa que o vídeo seja ruim. A ausência de reframe é deliberada quando a composição visual tem valor editorial.

## Integração com o pipeline

O fluxo de corte rápido e o processo completo alimentam o planejador com o layout detectado pelo `FaceTracker`, a avaliação de estabilidade facial e o preset de exportação. O renderizador aceita `layout_plans` opcionalmente, por isso chamadas legadas continuam funcionando. Quando o plano proíbe reframe, o índice é incluído em `original_aspect_indices` e o arquivo é validado como saída original.

Essa arquitetura também deixa uma extensão segura para o futuro: o Gemini pode fornecer sinais como `split_screen`, `text_card`, `institutional`, `active_speaker_confidence` e `has_b_roll`; o planejador continuará sendo a camada determinística que transforma esses sinais em política de enquadramento, sem permitir que uma resposta livre da IA force um crop inseguro.

## Critérios de aceite

A implementação só deve ser considerada correta quando: uma face única estável pode receber reframe; múltiplas faces preservam o original; texto visual e B-roll não são destruídos; vídeos institucionais não são rejeitados apenas por pouca fala; a razão chega ao resultado do clip; chamadas antigas do renderizador continuam válidas; e a suíte de regressão permanece verde.

## Referências

[1]: https://www.opus.pro/ai-reframe "OpusClip — AI Reframe"
[2]: https://vizard.ai/tools/transcription "Vizard — Transcription"
[3]: https://vizard.ai/tools/audio-editor "Vizard — Audio Editor"
[4]: https://klap.app/ "Klap — página oficial"
[5]: ../docs/instagram-mbl-catalog-analysis.md "Base editorial consolidada do Furia Clips"
