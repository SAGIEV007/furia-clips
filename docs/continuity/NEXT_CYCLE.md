# Próximo ciclo

## Estado de partida

A release `6.22` está na branch `claude/repo-access-commits-imgjmk`, com a observabilidade da 6.21 preservada e uma recuperação textual conservadora para seeds do Campaign Hub cuja timeline não coincide com a transcrição local. A pesquisa MCP/Chub está em `RESEARCH_MCP_CHUB_2026-08-21.md` e o desenho do ciclo em `CYCLE_38_DESIGN_MCP_CHUB_2026-08-21.md`. O futuro da ferramenta, reservado para uma fase final posterior, está em `FUTURE_PLATFORM_2026-08-21.md`; o inventário desde Claude está em `HANDOFF_SINCE_CLAUDE_2026-08-21.md`. O norte imediato continua sendo precisão de cortes e integração Chub/MBL.

A fonte original continua canônica. Reels e posts publicados continuam `reference_only`; lives longas e arquivos crus continuam `processing_source`. Nenhum snapshot do Campaign Hub é consultado durante o job normal fora dos arquivos locais autorizados. O ciclo 35 não iniciou mídia real nem dependeu de navegador; alterou somente o contrato operacional de cancelamento e seu feedback. O ciclo 37 também não baixou mídia real: validou a observabilidade com fixtures e jobs temporários, preservando o princípio de não adicionar arquivos de usuário ao checkout. O planejamento aprofundado do núcleo de cortes está em `CUTTING_PRECISION_PLAN_2026-08-21.md`, e a auditoria factual que o fundamenta está em `CUTTING_AUDIT_2026-08-21.md`. O arquivo `FUTURE_PLATFORM_2026-08-21.md` continua reservado à fase final de automações e integrações remotas.

## Hipótese única

> **Se uma seed temporal do Campaign Hub não coincidir com a timeline local, mas o highlight tiver correspondência lexical conservadora na transcrição, então o Furia poderá recuperar a unidade correta para revisão sem tratar timestamps incompatíveis como verdade.**

A identidade persistente de intervalo, a proveniência, o contrato narrativo, o gate final de locutor e a fidelidade de headlines foram implementados na 6.20. A 6.21 adicionou os instrumentos para que erros de execução e decisões de fallback sejam entregues no próprio diagnóstico. A 6.22 mantém esse contrato e adiciona `alignment_method=text_anchor` para recuperar uma seed Chub por texto quando a sobreposição temporal falha; a proposta fica obrigatoriamente revisável. O próximo ciclo deve comparar esse caminho em benchmark reproduzível e executar uma faixa curta pela interface, copiando `ui-diagnostic-v1`, para auditar cobertura operacional. A ordem editorial continua: recall-first Chub, bordas, locutor, contexto/payoff, ranking pairwise e formatos.

## Procedimento de validação

1. Selecionar uma fonte longa autorizada com snapshot/fixture Chub e um conjunto de cortes humanos aprovados, rejeitados e pendentes.
2. Materializar o benchmark com `source_signature`, `processing_identity`, `transcript_digest`, formato, início/fim, bloco de referência e decisão humana.
3. Comparar o baseline temporal com `text_anchor`, medindo recall de highlights, IoU/erro de borda, taxa de ancoragem correta e falsos alinhamentos.
4. Medir separadamente contexto autossuficiente, payoff, locutor, risco, headline e qualidade técnica; toda proposta textual deve continuar marcada para revisão.
5. Comparar fonte inteira, duas faixas não sobrepostas e uma faixa repetida; repetir com transcript manual e automático quando os dois existirem.
6. Gerar uma tabela de falhas por motivo: início tardio, final precoce, anáfora, pergunta sem resposta, payoff ausente, locutor incerto, Chub não recuperado, âncora textual ambígua, headline não fundamentada ou problema visual.
7. Executar uma faixa curta pela interface e copiar `ui-diagnostic-v1`; só depois retomar a visualização read-only da fila de descoberta Chub, sem renderização ou aprovação automática.

## Critério de sucesso

A hipótese será confirmada se uma seed com timestamps incompatíveis for recuperada somente quando o texto corresponder acima dos limiares, com método e evidência persistidos, e se o benchmark mostrar aumento de recall sem aumento de falsos alinhamentos, falsos Renan ou perda de contexto/payoff. Nenhuma alteração de ranking será considerada ganho sem melhora mensurada em recall/precisão temporal e sem preservar os gates Renan-first, contexto, payoff, risco e Campaign Hub.

## Critério de falha

Se o benchmark misturar faixas, transcrições ou formatos, se decisões humanas não puderem ser rastreadas ao candidato original, ou se a identidade alterar ranking sem mudança editorial explícita, a hipótese falha. Nesse caso, corrigir a medição antes de alterar pesos ou adicionar aprendizado.

## Escopo excluído

Não alterar pesos do ranking até o benchmark produzir uma comparação. Não adicionar chamada MCP direta durante o job, download autenticado, WhatsApp, smartwatch, pesquisa remota ou promoção automática. O sync remoto deve continuar separado, read-only, sanitizado e instalável como snapshot local. Não baixar Reels publicados. Não tocar a branch principal.

## Arquivos para ler primeiro

`PROJECT_STATE.md`, `HANDOFF_SINCE_CLAUDE_2026-08-21.md`, `CUTTING_AUDIT_2026-08-21.md`, `CUTTING_PRECISION_PLAN_2026-08-21.md`, `RESEARCH_CUTTING_PRECISION_2026-08-21.md`, `RESEARCH_MCP_CHUB_2026-08-21.md`, `CYCLE_38_DESIGN_MCP_CHUB_2026-08-21.md`, `FUTURE_PLATFORM_2026-08-21.md`, `CYCLE_37_REPORT_2026-08-21.md`, `CYCLE_36_REPORT_2026-08-21.md`, `CYCLE_35_REPORT_2026-08-21.md`, `DECISIONS.md`, `modules/job_manager.py`, `app.py`, `static/js/app.js`, `tests/test_job_manager.py`, `tests/test_app_smoke.py` e `docs/VERSIONING.md`.

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
