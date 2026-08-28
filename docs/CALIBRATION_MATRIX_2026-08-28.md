# Matriz sanitizada de calibração

Esta matriz não contém nomes de arquivos, URLs, transcripts, legendas, mídia ou intervalos privados. Os rótulos são locais e não reversíveis.

| Caso | Duração aproximada | Resolução | Áudio | Referência humana | Estado |
|---|---:|---|---|---:|---|
| Fonte adicional A | 29 min 32 s | 1920×1080 | Sim | disponível | aguardando Furia 1 |
| Fonte adicional B | 17 min 15 s | 1920×1080 | Sim | disponível | aguardando Furia 1 |
| Caso crítico já validado | 44 min 31 s | 1280×720 | Sim | disponível | baseline pós-calibração concluído |

## Métricas a preencher por ciclo

Para cada fonte serão registrados somente contagens e tempos: candidatos iniciais, candidatos aprovados, candidatos adiados, clips renderizados, tempo de seleção, tempo de render, IoU em faixas de 0,5/0,7/0,9, referências cobertas e quantidade de falhas editoriais encontradas na revisão audiovisual.

IoU será usado como proximidade temporal descritiva. A decisão de qualidade continuará dependendo de contexto, locutor, continuidade, interrupção, payoff, áudio e revisão humana.

## Critérios de comparação

Uma alteração só será considerada melhoria quando reduzir uma falha editorial reproduzível sem criar regressão em outro caso, ou quando melhorar operação/legibilidade sem modificar a decisão canônica do Furia 1. A quantidade de clips, isoladamente, não é critério de sucesso.

## Resultados do ciclo 1

| Caso | Candidatos finais | Clips renderizados | Resultado operacional | Comparação temporal |
|---|---:|---:|---|---|
| Fonte adicional A | 25 | 20 | Whisper local concluído; 4 amostras revisadas, 3 aproveitáveis e 1 com alerta de fechamento | Sem referência renderizada comparável nesta rodada |
| Fonte adicional B | 9 | 9 | Transcript Tactiq absoluto corrigido no parser integrado | 3/9 candidatos com IoU ≥ 0,5; 0 com IoU ≥ 0,7; média do melhor IoU dos candidatos: 0,306 |

A fonte B também foi executada sem alinhamento, produzindo apenas 2 clips. Esse resultado foi tratado como diagnóstico de entrada, não como calibração editorial. Depois da correção generalizável para blocos Tactiq e relógio absoluto, a execução com o arquivo original produziu 9 clips no caminho normal do produto.

A comparação temporal não prova qualidade editorial. A validação audiovisual confirmou qualidade aproveitável em amostras selecionadas, mas a próxima rodada deverá ampliar a revisão de fronteiras, interrupções e encerramentos.
