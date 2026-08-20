# Ciclo 33 — Processamento parcial de fontes longas e UX de execução

## Objetivo

Adicionar uma forma segura de processar apenas uma faixa de uma fonte longa — por exemplo, 00:00–05:00 de uma live de duas horas — e aplicar somente melhorias visuais e de UX inspiradas no branch de referência `manus/rebuild-opus-parity-2`, sem importar mudanças de ranking, backend ou lógica editorial.

## Hipótese

Se o Furia criar uma cópia temporária precisa da faixa solicitada antes das etapas pesadas, então transcrição, contexto, seleção, análise de áudio, detecção de layout, tracking, legendagem e renderização poderão trabalhar em uma timeline curta, economizando tempo e processamento sem modificar a fonte original. A interface deve tornar o escopo explícito para evitar que o editor confunda os timestamps locais com a minutagem da live inteira.

## O que foi implementado

### Backend e mídia

`modules/source_interval.py` agora interpreta segundos, `mm:ss` e `hh:mm:ss`, valida limites e produz um contrato explícito com `start_seconds`, `end_seconds`, `duration_seconds`, `offset_seconds`, `active`, `status` e `label`. A faixa inteira continua sendo o comportamento padrão quando os campos ficam vazios.

A função `trim_media_to_interval()` cria uma cópia temporária com FFmpeg usando seek preciso, preserva a fonte original e permite limpeza garantida em sucesso, erro ou cancelamento. O job passa a usar a cópia somente nas etapas de processamento; o projeto, o diagnóstico e a trilha editorial continuam apontando para a fonte original.

As rotas `/api/process/cut` e `/api/process/complete` aceitam `processing_start` e `processing_end`. O intervalo é validado antes de enfileirar o job. O processo completo e o corte inteligente compartilham a mesma preparação, transcrição local, escopo de seleção e limpeza temporária.

Quando a legenda manual pertence à fonte inteira, seus segmentos são recortados e rebased para a timeline local. Quando o resultado é devolvido à interface, cada clip mantém `start` e `end` relativos ao intervalo para renderização e `source_start` e `source_end` absolutos para o editor. O evento final, os diagnósticos e os artefatos persistidos carregam `processing_interval`.

Para evitar uma colisão incorreta entre segundos locais de faixas diferentes, a deduplicação de fingerprints anteriores fica desativada apenas em execuções com intervalo ativo. A seleção integral mantém o comportamento anterior. Essa decisão é conservadora até existir um armazenamento persistente explícito da identidade do intervalo.

### Interface e UX

O modal compartilhado de execução agora serve tanto ao corte inteligente quanto ao processo completo. O editor informa início e fim, vê um chip com a faixa interpretada e recebe a confirmação de que a fonte original não será alterada. O modal aceita apenas uma configuração por execução, reduzindo a chance de o corte inteligente e o processo completo usarem escopos diferentes.

Foi adicionado um card visual de intervalo com hierarquia de título, explicação curta, chip de estado, campos alinhados, mensagem de validação e layout responsivo para notebook e telas menores. O processo completo deixou de iniciar por um `confirm()` separado e passa pelo mesmo fluxo visual do corte inteligente.

A referência visual consultada foi `manus/rebuild-opus-parity-2`, especialmente os commits `904152b`, `749ab90`, `a9e1437` e `2b9fdcb`. Foram reaproveitados apenas padrões de superfície, clareza de status, colapso de painéis e controles de revisão. O branch de referência também mostrou que a 6.16 já possuía central de revisão, avisos de proveniência, `candidateVolumeNotice` e métricas recolhíveis; esses componentes não foram duplicados nem alterados funcionalmente.

## Regressões e validação

Foram adicionados testes de parsing, limites, rebase de transcrição, cópia real de mídia com a fixture `tests/fixtures/sample_av.mp4` e rejeição antecipada de intervalos inválidos nos dois endpoints. A cópia de mídia foi conferida por `ffprobe` e a fonte original permaneceu intacta.

| Validação | Resultado |
| --- | ---: |
| Testes de intervalos e API | 30 aprovados |
| Intervalos, cobertura, fingerprints, seleção e Chub | 69 aprovados |
| Suíte completa com BlazeFace temporário | **552 aprovados, 4 ignorados** |
| `node --check static/js/app.js` | Aprovado |
| `python3 -m py_compile` | Aprovado |
| `git diff --check` | Aprovado |
| Verificação visual no navegador local | Aprovada; modal e campos visíveis |
| Arquivos proibidos no diff | Nenhum planejado; o modelo BlazeFace foi removido |

## Constatações confirmadas

A faixa parcial é um recorte operacional, não uma alteração destrutiva do vídeo. O Furia continuará preservando a origem original, mas processará a cópia curta nas etapas que consomem mais tempo.

O uso de timestamps relativos na seleção é necessário para manter todos os módulos coerentes; por isso o retorno também inclui timestamps absolutos de origem. O editor poderá localizar o corte na live inteira sem obrigar a seleção a operar novamente sobre duas horas de material.

A maior parte do norte visual da outra IA já estava presente na 6.16. A contribuição visual deste ciclo foi concentrada no novo fluxo de intervalo e na unificação do modal entre os dois modos de execução, evitando alterações cosméticas fora do escopo.

## Limitações e pontos ainda não comprovados

Ainda não foi executado um job editorial completo de uma live longa real usando um intervalo selecionado, porque isso exigiria uma fonte de mídia autorizada e uma rodada de processamento pesada. A criação e a duração da cópia foram testadas com fixture local; a integração das rotas foi validada por sintaxe, contratos de API, regressões e suíte completa.

A deduplicação entre execuções parciais ainda não possui uma identidade persistente de intervalo no banco. Por segurança, intervalos ativos não reaproveitam fingerprints da fonte inteira; isso pode permitir duplicatas entre duas execuções da mesma faixa até um ciclo futuro tratar esse armazenamento explicitamente.

A transcrição manual é tratada como fonte inteira quando seus timestamps excedem a duração da faixa e então é recortada/rebaseada. Se o editor enviar uma legenda parcial que coincidentemente termine dentro da duração local, o sistema a trata como já local; esse contrato deve ser tornado explícito na interface em uma rodada futura, caso o uso real mostre ambiguidade.

## Arquivos principais

- `modules/source_interval.py`: parsing, validação, trim e rebase.
- `app.py`: integração nas rotas de corte inteligente e processo completo.
- `static/js/app.js`: modal compartilhado, validação e payload.
- `templates/index.html`: card visual de intervalo.
- `static/css/style.css`: estilos responsivos do card.
- `tests/test_source_interval.py`: testes do módulo e da cópia de mídia.
- `tests/test_app_smoke.py`: rejeição antecipada de intervalos inválidos.
- `docs/continuity/REFERENCE_UX_NOTES_2026-08-20.md`: separação entre referência visual e mudanças funcionais.
- `docs/continuity/INTERVAL_UX_CHECK_2026-08-20.md`: verificação visual local do modal.

## Retomada futura

A próxima IA deve confirmar `git status`, ler este relatório, `PROJECT_STATE.md`, `NEXT_CYCLE.md`, `DECISIONS.md` e `REFERENCE_UX_NOTES_2026-08-20.md`. Deve preservar a branch `claude/repo-access-commits-imgjmk`, não tocar a branch principal e não adicionar mídia, banco, cookies ou credenciais.

A próxima hipótese recomendada é persistir uma identidade de intervalo no banco e na trilha editorial, permitindo deduplicação correta entre execuções parciais sem bloquear material de outras faixas. Somente depois disso deve ser retomada a visualização read-only da fila de descoberta Chub prevista no ciclo anterior. Não alterar ranking, pesos Chub ou gates Renan-first nesta próxima rodada.
