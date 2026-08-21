# Próximo ciclo

## Estado de partida

A release `6.21` está na branch `claude/repo-access-commits-imgjmk`, com observabilidade estruturada de jobs, breadcrumbs persistentes, endpoints de eventos/diagnóstico, captura de erros globais e botão de diagnóstico copiável. Ela preserva a identidade persistente de intervalo, digest/proveniência de transcrição, contrato narrativo, gate final de locutor, fidelidade explicável de headlines, cancelamento seguro, filtro Renan-first, separação de descoberta/publicação, processamento parcial e UX contextual. O futuro da ferramenta, reservado para uma fase final posterior, está em `FUTURE_PLATFORM_2026-08-21.md`; o inventário desde Claude está em `HANDOFF_SINCE_CLAUDE_2026-08-21.md`. O norte imediato continua sendo precisão de cortes e integração Chub/MBL.

A fonte original continua canônica. Reels e posts publicados continuam `reference_only`; lives longas e arquivos crus continuam `processing_source`. Nenhum snapshot do Campaign Hub é consultado durante o job normal fora dos arquivos locais autorizados. O ciclo 35 não iniciou mídia real nem dependeu de navegador; alterou somente o contrato operacional de cancelamento e seu feedback. O ciclo 37 também não baixou mídia real: validou a observabilidade com fixtures e jobs temporários, preservando o princípio de não adicionar arquivos de usuário ao checkout. O planejamento aprofundado do núcleo de cortes está em `CUTTING_PRECISION_PLAN_2026-08-21.md`, e a auditoria factual que o fundamenta está em `CUTTING_AUDIT_2026-08-21.md`. O arquivo `FUTURE_PLATFORM_2026-08-21.md` continua reservado à fase final de automações e integrações remotas.

## Hipótese única

> **Se o benchmark editorial registrar identidade da fonte/faixa, digest da transcrição, formato, bordas e decisão humana, então será possível medir quais melhorias realmente elevam recall, precisão temporal, contexto, payoff e aprovação Renan/MBL antes de alterar novamente os pesos do ranking.**

A identidade persistente de intervalo, a proveniência, o contrato narrativo, o gate final de locutor e a fidelidade de headlines foram implementados na 6.20. A 6.21 adicionou os instrumentos para que erros de execução e decisões de fallback sejam entregues no próprio diagnóstico, mas ainda não mediu uma execução real pela interface. O próximo ciclo deve primeiro executar uma faixa curta, copiar `ui-diagnostic-v1`, auditar sua cobertura e corrigir somente lacunas de observabilidade. Depois, usar essas fundações para comparar candidatos e decisões humanas por faixa, sem alterar pesos até existir uma medição. A ordem editorial continua: recall-first Chub, bordas, locutor, contexto/payoff, ranking pairwise e formatos.

## Procedimento de validação

1. Selecionar uma fonte longa autorizada com snapshot/fixture Chub e um conjunto de cortes humanos aprovados, rejeitados e pendentes.
2. Materializar o benchmark com `source_signature`, `processing_identity`, `transcript_digest`, formato, início/fim, bloco de referência e decisão humana.
3. Medir separadamente recall temporal, IoU de borda, precisão@k, contexto autossuficiente, payoff, locutor, diversidade, headline e qualidade técnica.
4. Comparar fonte inteira, duas faixas não sobrepostas e uma faixa repetida; repetir com transcript manual e automático quando os dois existirem.
5. Gerar uma tabela de falhas por motivo: início tardio, final precoce, anáfora, pergunta sem resposta, payoff ausente, locutor incerto, Chub não recuperado, headline não fundamentada ou problema visual.
6. Reexecutar o fluxo sem intervalo e confirmar que a identidade não altera o ranking por acidente; mudanças de score exigem uma hipótese separada.
7. Só depois retomar a visualização read-only da fila de descoberta Chub, com filtros por locutor, bloco, highlight, identidade e motivo de exclusão; a visualização não poderá renderizar nem aprovar.

## Critério de sucesso

A hipótese será confirmada se o benchmark reproduzir a mesma faixa e transcript por identidade, separar faixas diferentes, medir os motivos de erro e permitir comparar antes/depois por dimensão editorial. Nenhuma alteração de ranking será considerada ganho sem melhora mensurada em recall/precisão temporal e sem preservar os gates Renan-first, contexto, payoff, risco e Campaign Hub.

## Critério de falha

Se o benchmark misturar faixas, transcrições ou formatos, se decisões humanas não puderem ser rastreadas ao candidato original, ou se a identidade alterar ranking sem mudança editorial explícita, a hipótese falha. Nesse caso, corrigir a medição antes de alterar pesos ou adicionar aprendizado.

## Escopo excluído

Não alterar pesos do ranking até o benchmark produzir uma comparação. Não adicionar download autenticado, WhatsApp, smartwatch, pesquisa remota ou integração MCP nesta rodada. Não baixar Reels publicados. Não adicionar rotas de promoção automática. Não tocar a branch principal.

## Arquivos para ler primeiro

`PROJECT_STATE.md`, `HANDOFF_SINCE_CLAUDE_2026-08-21.md`, `CUTTING_AUDIT_2026-08-21.md`, `CUTTING_PRECISION_PLAN_2026-08-21.md`, `RESEARCH_CUTTING_PRECISION_2026-08-21.md`, `FUTURE_PLATFORM_2026-08-21.md`, `CYCLE_37_REPORT_2026-08-21.md`, `CYCLE_36_REPORT_2026-08-21.md`, `CYCLE_35_REPORT_2026-08-21.md`, `DECISIONS.md`, `modules/job_manager.py`, `app.py`, `static/js/app.js`, `tests/test_job_manager.py`, `tests/test_app_smoke.py` e `docs/VERSIONING.md`.

## Referências

- [`PROJECT_STATE.md`](PROJECT_STATE.md)
- [`HANDOFF_SINCE_CLAUDE_2026-08-21.md`](HANDOFF_SINCE_CLAUDE_2026-08-21.md)
- [`FUTURE_PLATFORM_2026-08-21.md`](FUTURE_PLATFORM_2026-08-21.md)
- [`CUTTING_AUDIT_2026-08-21.md`](CUTTING_AUDIT_2026-08-21.md)
- [`CUTTING_PRECISION_PLAN_2026-08-21.md`](CUTTING_PRECISION_PLAN_2026-08-21.md)
- [`RESEARCH_CUTTING_PRECISION_2026-08-21.md`](RESEARCH_CUTTING_PRECISION_2026-08-21.md)
- [`CYCLE_35_REPORT_2026-08-21.md`](CYCLE_35_REPORT_2026-08-21.md)
- [`CYCLE_34_REPORT_2026-08-21.md`](CYCLE_34_REPORT_2026-08-21.md)
- [`DECISIONS.md`](DECISIONS.md)
- [`CYCLE_33_REPORT_2026-08-20.md`](CYCLE_33_REPORT_2026-08-20.md)
- [`CYCLE_32_REPORT_2026-08-20.md`](CYCLE_32_REPORT_2026-08-20.md)
- [`REFERENCE_UX_NOTES_2026-08-20.md`](REFERENCE_UX_NOTES_2026-08-20.md)
- [`INTERVAL_UX_CHECK_2026-08-20.md`](INTERVAL_UX_CHECK_2026-08-20.md)
- [`docs/VERSIONING.md`](../VERSIONING.md)
- [Branch de trabalho no GitHub](https://github.com/SAGIEV007/furia-clips/tree/claude/repo-access-commits-imgjmk)
