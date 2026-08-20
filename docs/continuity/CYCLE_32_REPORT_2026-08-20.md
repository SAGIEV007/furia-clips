# Relatório do ciclo 32 — fila de descoberta e fila publicável

**Data:** 2026-08-20  
**Branch:** `claude/repo-access-commits-imgjmk`  
**Estado de partida:** release `6.15`, commit funcional `07c51b0`, documentação fechada em `401ae58`.  
**Hipótese:** separar formalmente as propostas descobertas pelo Campaign Hub da fila de candidatos guiados que podem competir no ranking e chegar à revisão.

## Contexto e objetivo

A release 6.15 passou a impedir que propostas Chub sem evidência positiva de fala do Renan ocupassem o pool Renan-first. Porém, essas propostas eram simplesmente descartadas do ponto de vista operacional. Isso protegia o ranking, mas dificultava a auditoria: não era possível distinguir “o Chub não encontrou nada”, “o Chub encontrou, mas o locutor não foi confirmado” e “a proposta foi promovida e depois perdeu no anti-overlap”.

O objetivo do ciclo foi preservar essa memória de descoberta sem permitir que ela contaminasse a fila de cortes publicáveis. A fila de descoberta é diagnóstica e auditável; a fila publicável é a única que entra na seleção e no ranking.

## Implementação

O `ClipSelector` agora registra, a cada job, os campos:

| Campo | Significado |
| --- | --- |
| `campaign_hub_discovery_count` | Quantidade de propostas guiadas produzidas pelo snapshot autorizado antes do filtro de foco. |
| `campaign_hub_discovery_candidates` | Lista sanitizada com seed, bloco, highlight, intervalo, locutor, gate e motivo de exclusão. |
| `campaign_hub_publishable_guided_count` | Quantidade de propostas Chub promovidas ao pool primário. |
| `campaign_hub_publishable_candidates` | Apenas as propostas guiadas promovidas; não inclui todos os candidatos finais locais. |
| `final_candidates` | Resumo de todos os candidatos que chegaram ao final da seleção, independentemente da origem. |
| `campaign_hub_guided_filtered_by_speaker` | Quantidade de propostas retiradas do pool Renan-first por não terem `renanSpeaking=true`. |

Quando o foco é Renan-first, uma proposta `false` ou desconhecida permanece na descoberta com `publication_status="speaker_gate_review"` e `exclusion_reason` explícito. Quando o foco é genérico, o filtro de identidade não é aplicado: as propostas descobertas podem ser promovidas normalmente, continuando sujeitas aos demais gates.

A interface passou a mostrar no aviso de volume quantos trechos o Campaign Hub encontrou, quantos entraram na fila publicável e quantos ficaram para revisão de locutor. O backend já transmite `candidate_diagnostics` nos eventos `selection_mode` e `cut_complete`, e também grava os diagnósticos sanitizados junto ao relatório da seleção.

Uma correção de contrato foi feita durante o ciclo: `campaign_hub_publishable_candidates` inicialmente estava sendo sobrescrito no final por todos os candidatos gerais. O campo agora mantém exclusivamente a fila Chub promovida, enquanto `final_candidates` representa o resultado geral.

## Medição na fonte real

A fonte permanece `3XJfcqn56Rw`, com 5.905 segundos, 1.951 frases, 27 blocos e 66 highlights do Acervo.

| Condição | Descoberta Chub | Promovidas | Filtradas por locutor | Recall IoU 0,10 | Recall IoU 0,25 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Genérico sem Chub | 0 | 0 | 0 | 5/66 — 7,58% | 0/66 |
| Genérico com Chub | 30 | 30 | 0 | 18/66 — 27,27% | 6/66 — 9,09% |
| Renan-first sem Chub | 0 | 0 | 0 | 7/66 — 10,61% | 1/66 — 1,52% |
| Renan-first com Chub | 30 | 6 | 24 | 7/66 — 10,61% | 1/66 — 1,52% |

A separação não altera o ranking nem o recall em relação à 6.15. Ela torna observável que o Chub encontrou 30 propostas, das quais 24 não tinham evidência positiva de locutor e 6 puderam ser promovidas no foco Renan-first. O recall publicável continua igual ao caminho sem Chub, portanto o ciclo confirma **controle e auditabilidade**, não um novo ganho de cobertura.

## Constatações confirmadas

A hipótese de separar descoberta e publicação é tecnicamente viável sem alterar a seleção. A interface e os eventos de job conseguem mostrar a diferença entre descoberta e promoção. O modo genérico permanece inalterado. O modo Renan-first não apresenta as propostas filtradas como candidatos guiados, mas preserva seus motivos para auditoria.

A instrumentação também elimina uma ambiguidade importante para futuras IAs: `campaign_hub_publishable_candidates` não é sinônimo de “todos os cortes finais”; ele representa apenas propostas guiadas promovidas. `final_candidates` representa a fila final geral, que pode conter NLP local, fallback ou Chub.

## Limitações e especulações

Ainda não há uma tela dedicada para navegar e aprovar manualmente a fila de descoberta. Ela está disponível no diagnóstico do job, na persistência sanitizada e no aviso de interface, mas não é uma segunda lista visual de cortes renderizáveis. Isso é intencional neste ciclo: criar uma tela de revisão seria uma hipótese de produto diferente e poderia misturar descoberta com publicação.

A métrica de recall continua baseada nos 66 highlights do próprio Acervo e não substitui a aprovação editorial humana. `renanSpeaking=true` é evidência de identidade fornecida pelo snapshot; não é diarização independente e não garante que o trecho seja bom, autossuficiente ou seguro para publicação.

A próxima hipótese recomendada é criar uma visualização de auditoria read-only para a fila de descoberta, com filtros por locutor, bloco, motivo de exclusão e highlight, sem permitir que um item seja renderizado sem passar novamente pelos gates. Antes disso, não se deve aumentar pesos, quotas ou duração das propostas Chub.

## Validação e retomada

A suíte completa terminou com **546 testes aprovados e 4 ignorados** após o asset BlazeFace ser provisionado temporariamente, conferido e removido. Também passaram os testes focados de Campaign Hub, diagnóstico de volume, identidade e frontend, além de `node --check static/js/app.js` e `git diff --check`.

Nenhum vídeo, áudio, transcrição real, snapshot, banco, cookie, token ou segredo deve ser adicionado ao Git. A continuidade deve ser lida em `PROJECT_STATE.md`, `NEXT_CYCLE.md`, `DECISIONS.md` e neste relatório antes do próximo ciclo. O trabalho continua exclusivamente na branch `claude/repo-access-commits-imgjmk`; a branch principal não deve ser alterada.
