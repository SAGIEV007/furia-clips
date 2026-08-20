# Referência visual/UX consultada — 2026-08-20

A referência solicitada pelo usuário foi comparada nos branches públicos do repositório `SAGIEV007/furia-clips`, especialmente `manus/rebuild-opus-parity-2`.

## Componentes visuais/UX identificados

- Commit `904152b`: painel de métricas recolhível na área de revisão, deixando a área principal de cortes menos carregada.
- Commit `749ab90`: aviso visual de diagnóstico do pool de candidatos, com estados para pool adequado, fallback e material insuficiente; alterou `static/app.js` e `static/style.css`.
- Commit `a9e1437`: inserção do aviso acessível `candidateVolumeNotice` no centro de revisão.
- Commit `2b9fdcb`: badge visual de proveniência do candidato no card de revisão, com estados de origem primária e fallback; alterou `static/app.js` e `static/style.css`.

## Regra de escopo

A referência também contém mudanças de backend, ranking, Gemini, priors e seleção. Essas mudanças não serão copiadas nesta rodada. O trabalho atual deve reaproveitar apenas padrões de apresentação, acessibilidade, hierarquia visual, badges, painéis recolhíveis e feedback de estado.

A branch de trabalho atual é `claude/repo-access-commits-imgjmk`; a referência foi apenas buscada e comparada. Nenhum commit da referência foi mesclado automaticamente.

## Relação com a 6.16

A 6.16 já possui `candidateVolumeNotice`, badges de proveniência e o centro de revisão correspondente. O próximo trabalho visual deve ser incremental: melhorar a apresentação do intervalo de processamento, aproveitar o painel recolhível existente e evitar duplicar os componentes já presentes.

Fonte: [branch manus/rebuild-opus-parity-2](https://github.com/SAGIEV007/furia-clips/tree/manus/rebuild-opus-parity-2).
