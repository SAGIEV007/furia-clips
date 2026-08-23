# Relatório do ciclo 16 — primeira ponte funcional Campaign Hub→cortes

**Data:** 2026-08-17
**Versão:** 2.6
**Branch:** `manus/rebuild-opus-parity`
**Baseline de código anterior:** `74bc611` — `docs: registrar commit do prompt operacional (2.5)`
**Baseline editorial:** caso b354, sete candidatos locais, recall `0/3`, IoU médio `0.0`.

## Resumo executivo

Este ciclo implementou a primeira ponte funcional entre o contexto autorizado do Campaign Hub e a geração de propostas de corte do Furia Clips. O Campaign Hub deixa de ser apenas memória consultada pela sessão de blocos e passa a alimentar seeds semânticas e temporais que entram no seletor, são expandidas dentro da transcrição local e recebem gates explícitos antes do ranking.

A implementação foi validada pela suíte completa e por um payload real do Campaign Hub. Ela demonstrou a geração de duas seeds e duas propostas contextualizadas, ambas com `context_complete=true`. O recall do benchmark b354, entretanto, **não foi medido nesta release**, pois o snapshot autorizado correspondente não estava instalado no caminho local durante o job normal. O baseline `0/3` permanece, portanto, sem reivindicação de ganho.

> **Conclusão:** a ponte funcional está corrigida e reproduzida em payload real; o ganho de recall no caso b354 está não verificado e é a próxima hipótese, não um resultado desta rodada.

## Hipótese

> Se cada highlight ou bloco autorizado do Campaign Hub for transformado em seed semântica e temporal e expandido até a menor janela completa que preserve antecedente, pergunta, tese, evidência e payoff, então o recall do benchmark b354 deverá sair de `0/3` sem aumentar falsos positivos, atribuições erradas ou cortes truncados.

A hipótese foi deliberadamente limitada à ponte de contexto e à geração de propostas. Não foram misturados reframe, headlines, editor estilo CapCut, diarização robusta, publicação automática, música, voz, avatares, múltiplas câmeras ou download remoto por range.

## Baseline e fonte de referência

O baseline b354 foi construído na release 2.2 com sete candidatos persistidos pelo Furia e três highlights QA-gated do Campaign Hub. Os destaques foram mapeados para `146.80–150.80s`, `223.24–228.40s` e `488.48–495.20s` no MP4 local de aproximadamente `549.449s`. O recall temporal foi `0/3` e o IoU médio foi `0.0`.

O payload real usado para validar a forma da ponte correspondeu ao vídeo `gVrW6a5e6Tc`, bloco `70358a7d-7848-48d1-8d3d-5ef7c61c149d`. Ele tinha dois highlights com `sentenceIdx=128` e `sentenceIdx=171`, `renanSpeaking=true`, `trustTier=third_party` e o aviso `start_continuation`.

## Implementação

| Arquivo | Alteração | Efeito verificável |
| --- | --- | --- |
| `modules/campaign_hub_guidance.py` | Novo normalizador de snapshots | Aceita snake_case/camelCase, highlights aninhados, `possibleCuts` e fallback por bloco; preserva proveniência e QA flags |
| `modules/clip_selector.py` | Novos caminhos `_select_with_campaign_hub_guidance()` e `_build_campaign_hub_proposal()` | Gera propostas guiadas, expande a seed e aplica gates antes do ranking |
| `modules/editorial_context.py` | Diagnóstico de seeds guiadas | Expõe `campaign_hub_guided_seed_count` no contexto editorial |
| `app.py` | Snapshot carregado uma vez por job | Mantém execução offline-first e evita recarga redundante na seleção, hooks e ranking |
| `tests/test_campaign_hub_guidance.py` | Seis regressões | Cobre timeline, expansão, fallback, origem, formato real e revisão obrigatória |
| `tests/test_runtime_version.py` | Identidade atualizada | Confirma a versão pública `2.6` |
| `VERSION` | Incremento de `2.5` para `2.6` | Identidade pública coerente com a alteração funcional |

As propostas entram com `source="campaign_hub_guided"` e `candidate_origin="campaign_hub_guided"`. Isso registra a origem da proposta, mas não equivale a corte aprovado. Os gates cobrem contexto, payoff, locutor, timing, risco, técnico, proveniência e avisos.

## Resultado da avaliação real

A normalização do payload do Chub produziu duas seeds a partir dos highlights de `sentenceIdx=128` e `sentenceIdx=171`. A avaliação da expansão gerou duas propostas:

| Seed/highlight | Intervalo proposto | Contexto | Revisão |
| --- | ---: | --- | --- |
| `sentenceIdx=128` | `426.4–451.52s` | `context_complete=true` | `review_required=true` |
| `sentenceIdx=171` | `511.0–566.12s` | `context_complete=true` | `review_required=true` |

A revisão foi obrigatória porque a proveniência era `third_party` e o bloco carregava `gateWarnings=["start_continuation"]`. O comportamento é intencional: o Campaign Hub fornece contexto e calibração, mas não aprova automaticamente uma publicação.

## Validação técnica

| Verificação | Resultado |
| --- | --- |
| Suíte completa | **333 passed** |
| `compileall -q app.py modules scripts` | Aprovado |
| `node --check static/js/app.js` | Aprovado |
| `git diff --check` | Aprovado |
| BlazeFace temporário | SHA-256 conferido; arquivo removido antes do commit |
| Snapshot MCP durante o job normal | Não consultado; o fluxo usa snapshot local quando disponível |

As seis regressões novas confirmam que a ausência de snapshot não quebra o caminho legado, que o formato camelCase real é aceito, que a timeline de bloco pode ser mapeada quando justificado, que a expansão busca pergunta e payoff e que `third_party` com aviso permanece em revisão.

## Classificação das conclusões

### Confirmado

A ponte de normalização, seleção e expansão existe no código. O snapshot é reutilizado uma vez por job. Seeds e propostas mantêm proveniência, flags de risco e distinção entre origem da proposta e aprovação editorial.

### Reproduzido

O payload real do Campaign Hub produziu duas seeds e duas propostas, ambas com contexto completo e revisão obrigatória conforme proveniência e avisos.

### Corrigido

O Campaign Hub agora consegue alimentar diretamente a geração de propostas guiadas quando existe snapshot local autorizado. O caminho legado continua funcional quando o snapshot está ausente.

### Não verificado

O recall do benchmark b354 com a nova ponte não foi medido. Também não foram medidos nesta rodada o IoU depois da ponte, a estabilidade entre reprocessamentos, o número de falsos positivos em mídia real ou a qualidade audiovisual de um corte guiado aprovado.

### Bloqueado ou limitado

O job normal não gera propostas guiadas sem um snapshot em `~/FuriaClipsData/campaign_hub/profile.json` ou via importação equivalente. A proveniência `third_party` e `start_continuation` mantém revisão obrigatória. Nenhum snapshot privado, token, cookie, banco, mídia grande ou modelo binário foi versionado.

## Próxima hipótese

> Se um snapshot autorizado e sanitizado do Campaign Hub for instalado localmente e o Furia reprocessar o caso b354 com a ponte 2.6, o recall temporal deve sair de `0/3` sem aumentar falsos positivos, atribuições erradas, truncamentos ou confusão entre quem fala e quem é foco editorial.

O procedimento detalhado está em [`NEXT_CYCLE.md`](NEXT_CYCLE.md). O próximo ciclo deve instalar o snapshot de forma administrativa, reprocessar o MP4 b354 e comparar baseline e propostas guiadas com recall, IoU, erro de fronteira, duração, duplicatas, autossuficiência, pergunta–resposta, payoff, locutor, risco, proveniência e estabilidade.

## Referências internas

- [`CHUB_INTEGRATION_CONTRACT.md`](CHUB_INTEGRATION_CONTRACT.md)
- [`PROJECT_STATE.md`](PROJECT_STATE.md)
- [`NEXT_CYCLE.md`](NEXT_CYCLE.md)
- [`CHANGELOG.md`](CHANGELOG.md)
- [`COMMIT_MESSAGE_TEMPLATE.md`](COMMIT_MESSAGE_TEMPLATE.md)

[1]: CHUB_INTEGRATION_CONTRACT.md
[2]: PROJECT_STATE.md
[3]: NEXT_CYCLE.md
[4]: CHANGELOG.md
[5]: COMMIT_MESSAGE_TEMPLATE.md
