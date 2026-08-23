# Relatório do ciclo 4 — 2026-08-16

## Identidade e escopo

A rodada foi executada na branch `manus/rebuild-opus-parity` sobre a fonte operacional enviada pelo usuário: `RENANSANTOS｜BPNASELEIÇÕES.mp4`, copiada para `workspace/uploads/renan-bp-nas-eleicoes.mp4`. O MP4 foi validado com FFprobe como vídeo AV1 1920×1080, áudio AAC estéreo 44,1 kHz e duração de `5046,346304` segundos, aproximadamente 84,1 minutos. O arquivo `0815(1).srt` foi copiado para `workspace/references/0815-reference-only.srt` e parseado isoladamente; ele não foi usado como transcrição ou legenda do MP4.

O arquivo também foi analisado audiovisualmente. A análise observou uma sabatina em estúdio com Renan Santos, perguntas de mediadores e múltiplos blocos temáticos. A análise identificou, entre outros, blocos sobre a filiação de Flávio Bolsonaro, referências políticas, liberalismo e Estado, governabilidade, relação com o eleitorado, imprensa, Judiciário e segurança pública. Essa análise não é uma transcrição literal e foi usada somente como observação audiovisual/editorial.

## Hipótese única

> Se o ranker marca um candidato como explicitamente `context_complete=false`, renderizá-lo como corte pronto ainda permite que um hook forte supere a falta de setup ou uma abertura abrupta. Adiar esse candidato antes do renderizador deve aumentar a qualidade mínima dos exports sem apagar o diagnóstico para revisão.

O Estúdio de Texto de Arte não foi alterado nesta rodada. As ideias de headline 1:1 foram geradas separadamente a partir do SRT de referência, conforme solicitado, e não foram atribuídas ao MP4.

## Baseline reproduzido

Foi transcrito o primeiro lote de 15 minutos do áudio extraído do MP4 original, usando o mesmo motor local `faster-whisper` do projeto, modelo `base`, CPU, `beam_size=1` e sem timestamps por palavra. O lote produziu `357` segmentos, `16.324` caracteres e duração de 900,096 segundos; o processamento levou aproximadamente 75 segundos.

O pipeline 1.3 foi executado pelo endpoint de corte com essa transcrição parcial e a timeline do vídeo original. O job `10c194cb-7c8a-403a-a08f-ada233a91018` concluiu em aproximadamente 5 minutos e 10 segundos, gerando quatro exports válidos. Entre os quatro havia um candidato de `168,09` segundos, iniciado em `627,56` segundos, com `context_complete=false`, `starts_mid_sentence=true`, `chapter_crosses_boundary=true` e gate técnico em revisão. Apesar desses sinais, o candidato foi enviado ao renderizador.

A fonte completa não pôde ser transcrita no limite operacional do ambiente: tanto o job Flask quanto o executor direto foram encerrados enquanto processavam o áudio de 84,1 minutos. O carregamento do Whisper base em si foi validado isoladamente e terminou com sucesso; a limitação ocorreu durante a transcrição longa, não por falta do modelo. Por isso, nenhum resultado desta rodada afirma cobertura editorial completa da live inteira.

## Implementação

Foi adicionado em `app.py` o helper `_defer_context_incomplete_candidates`. Depois do ranking, candidatos que contêm a flag explícita `context_complete=false` são retirados do lote enviado ao renderizador e registrados como rejeições editoriais com intervalo, duração, motivo e `review_flags`. Candidatos sem o contrato de contexto continuam compatíveis com o comportamento anterior. O job expõe a contagem em `candidate_diagnostics["render_deferred_context_count"]` e combina essas rejeições com as rejeições técnicas do `VideoCutter`.

A regressão principal está em `tests/test_render_context_gate.py`. Ela confirma que um candidato incompleto é adiado, que o motivo preserva o diagnóstico de início abrupto e que candidatos completos ou legados continuam renderizáveis.

## Resultado antes/depois

Para evitar a deduplicação entre execuções, a mesma mídia foi testada novamente por um hardlink local com nome de fonte distinto. O job `05d5f2fc-74f3-4782-a99f-b0ca4f20eb2a` processou o mesmo lote de 15 minutos após a alteração.

| Métrica | Antes, v1.3 | Depois, v1.4 |
| --- | ---: | ---: |
| Candidatos enviados ao renderizador | 4 | 3 |
| Exports concluídos | 4 | 3 |
| Candidato com `context_complete=false` renderizado | 1 | 0 |
| Candidato de 168,09 s iniciado no meio da frase | Sim | Adiado para revisão |
| Validação dos exports | 4 MP4 válidos | 3 MP4 válidos |
| Codec dos exports | H.264 + AAC | H.264 + AAC |
| Resolução dos exports | 1920×1080 | 1920×1080 |

Os três exports da repetição tiveram durações de aproximadamente 27,87 s, 180,00 s e 25,63 s. Todos possuem stream de vídeo H.264 e stream de áudio AAC estéreo e foram aceitos pelo FFprobe.

## Headlines de referência

O SRT externo foi normalizado pelo endpoint `/api/transcript/parse-file` com sucesso em `79` segmentos e último timestamp em aproximadamente `154,333` segundos. Ele foi mantido em `workspace/references/` e não contaminou a transcrição do projeto. As opções de headline foram registradas em `workspace/benchmarks/renan-bp-nas-eleicoes/headline-ideas-1x1-alfinetei.md`; a recomendação provisória foi `DEVASTAR — “Eu quero devastar o PT”`, sempre como citação atribuída e sujeita à conferência do vídeo correto.

## Validação técnica

A suíte específica do novo gate passou com `24 passed`. A suíte completa passou com `288 passed`. `py_compile` de `app.py` e dos módulos passou, e `git diff --check` passou antes da publicação. O servidor 1.3 utilizado para o baseline e o servidor com o código alterado permaneceram saudáveis durante os lotes de 15 minutos; o crash observado ocorreu apenas no processamento CPU da transcrição da fonte integral.

## Decisão e próxima hipótese

A hipótese foi aceita e publicada como release 1.4. O próximo ciclo deve usar uma fonte mais longa com transcrição completa ou um lote reproduzível maior para calibrar a menor janela suficiente em torno de antecedente anafórico, pergunta/resposta e mudança de pauta. O Estúdio de Texto de Arte continua adiado até que a seleção e a estabilidade tenham nova validação.
