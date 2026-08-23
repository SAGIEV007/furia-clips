# Pesquisa e Implementação — UX de Intervalo e Falha de Transcrição Longa (2026-08-21)

## O Problema
O usuário relatou dois comportamentos falhos:
1. **UX de Intervalo:** A interface de "Processar apenas um trecho" forçava o preenchimento de início e fim. Se o usuário quisesse cortar até o final, ele precisava descobrir a duração total do vídeo manualmente.
2. **Transcrição vs Vídeo:** Em lives longas (ou ao selecionar um intervalo de vídeo com a transcrição inteira), o sistema gerava o erro `A transcrição manual contém timestamps além da duração do vídeo selecionado` ou passava silenciosamente pelo NLP gerando dezenas de candidatos, mas entregando `0/0 clips` na hora de renderizar.

## A Causa Raiz
1. Em `static/js/app.js`, a função `readProcessingInterval` retornava erro se o fim estivesse em branco ou não validasse estritamente.
2. Em `app.py`, a função `_transcription_coverage_report` marca a cobertura como `mismatch_suspected` se a legenda exceder a duração do vídeo em 5%. A rotina que chama essa checagem levantava uma exceção bloqueante (`raise ValueError`), matando a execução ou, no caso do "Processo Completo", deferindo todos os candidatos porque eles caíam fora da faixa de tempo permitida para a renderização.

## A Solução
1. **Frontend (`app.js`):** Alterado o `readProcessingInterval` para ser mais tolerante. Se o fim ficar em branco, ele assume `Infinity` no frontend (o backend já sabe limitar à duração real do vídeo em `source_interval.py`). A label gerada também foi atualizada para guiar o usuário (ex: "início da fonte–22:00").
2. **Backend (`app.py`):** Relaxada a checagem de `mismatch_suspected`. Se a legenda manual for mais longa que o vídeo e *não houver um intervalo de recorte ativo*, o sistema agora apenas emite um aviso (`warning`) em vez de travar com `ValueError`. Se houver um intervalo ativo, a legenda já é podada (trim) para caber no intervalo *antes* da checagem. Se mesmo assim ela estourar, aí sim o erro é mantido.

Isso resolve o bug relatado onde "o programa continua reconhecendo a legenda inteira e dá erro" e o problema de UX onde o usuário não sabia o tempo total do vídeo.
