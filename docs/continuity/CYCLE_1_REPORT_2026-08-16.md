# Relatório do ciclo 1 — Furia Clips — 2026-08-16

## Objetivo

Validar uma rota de ingestão pública alternativa, executar o Furia com mídia real do Renan, reproduzir a falha de análise de cenas, corrigir a resiliência do job e observar a qualidade editorial dos cortes exportados.

## Fonte e ingestão

Foi usado o Reel público `https://www.instagram.com/reel/Davg97_tF4J/`, localizado pelo Campaign Hub como conteúdo do `@renansantosmbl`. O endpoint de probe identificou Instagram/`Davg97_tF4J`/Renan Santos. O Furia baixou o MP4 sem depender do YouTube. O arquivo tinha 135,7 s, vídeo H.264 720×1280, áudio AAC estéreo e 26.104.322 bytes.

## Transcrição

O Furia gerou 57 segmentos timestampados em português. A comparação com a transcrição de alta qualidade do Campaign Hub mostrou que a versão local ainda erra nomes próprios e frases politicamente sensíveis. A próxima camada de headline deve usar sinais do Campaign Hub quando disponíveis, sem substituir a validação da fala real.

## Estabilidade

O primeiro job integrado caiu durante análise de cenas e deixou um job marcado como running, sem exportação. O teste isolado mostrou que o ffmpeg consegue detectar 48 mudanças de cena no mesmo MP4. A correção adicionou timeout configurável, `-an`, tratamento de timeout/erro não-zero e fallback `[0.0]`, tornando cena um enriquecimento opcional.

Após a correção, o job integrado permaneceu saudável, concluiu em 100% e exportou três MP4s. O servidor respondeu normalmente depois do job.

## Resultado editorial observado

| Corte | Duração | Observação | Avaliação inicial |
| --- | ---: | --- | --- |
| `1. Eu não vou nem dar uma opinião...` | 59,2 s | Hook e contexto fortes, mas termina antes do payoff em “titular de direitos”. | Rejeitar ou expandir final |
| `2. Não haverá perdão` | 31,9 s | Hook forte, tese clara, contraste político e CTA limpo. | Aprovável |
| `3. De que o Brasil tem uma dívida com ele` | 46,5 s | Payoff visual forte e tese compreensível, mas começa no meio da frase. | Expandir início |

## Mudança publicada

A versão pública passou de 1.0 para 1.1. Foram adicionados timeout e fallback da detecção de cenas, testes de regressão e atualização da identidade de runtime. A suíte completa passou com 283 testes e `py_compile` foi aprovado.

Commits principais: `6349d37` implementa a correção; `be1b552` finaliza o estado persistente. Branch: `manus/rebuild-opus-parity`.

## Próxima hipótese única

A seleção deve rejeitar ou expandir automaticamente candidatos cujo início seja fragmentado ou cujo final ocorra antes do payoff, mesmo quando o hook e o score são fortes. A avaliação deve medir completude de contexto, menor janela suficiente, payoff preservado e fidelidade da headline.
