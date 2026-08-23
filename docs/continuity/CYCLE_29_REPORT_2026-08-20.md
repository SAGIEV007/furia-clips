# Relatório do ciclo 29 — medir a utilidade real do Campaign Hub e conectar evidência de locutor

**Data:** 2026-08-20  
**Branch:** `claude/repo-access-commits-imgjmk`  
**Release:** `6.14`  
**Hipótese:** se o Furia receber um snapshot rico do Campaign Hub alinhado à timeline local e consumir esse snapshot também no pós-processamento dos candidatos locais, então os dados do Acervo poderão melhorar cobertura e resolver parte da identidade de locutor no modo Renan-first; caso contrário, a integração estará apenas aumentando volume sem melhorar a decisão.

## Baseline e auditoria

A branch 6.13 estava limpa em `9b334bf`. A memória rica do Campaign Hub não estava instalada no caminho padrão `~/FuriaClipsData/campaign_hub/profile.json`, o que confirmou que o job normal não tinha acesso persistente aos blocos ricos no sandbox. Para não usar dados sintéticos, foi consultada em modo read-only a fonte real `3XJfcqn56Rw`, “O ÚLTIMO ANÁLISES RENAIS”, com 5.905 segundos de duração, 1.951 frases, 27 blocos QA-gated e 66 highlights.

Foi construído fora do Git um fixture local autorizado contendo a fonte, os blocos, os highlights, `renanSpeaking`, tiers, riscos, perguntas, títulos, resumos e intervalos. A transcrição permaneceu com a proveniência automática do Acervo; ela foi usada para navegação e benchmark, não como citação factual sem conferência no áudio.

A comparação inicial revelou dois fatos distintos. Primeiro, o prior agregado de não-conteúdo do Acervo teve efeito zero na fonte persistida do project-57: havia 239 termos no arquivo, mas somente 4 segmentos tinham hits fracos (`olá`, `atualizar`, `obrigado`), e as 12 janelas selecionadas permaneceram idênticas com e sem esse prior. Isso confirma que o prior atual é útil como detector auxiliar de intro/produção, mas não é um sistema de seleção especializado.

Segundo, na live longa real, o snapshot rico aumentou a cobertura de referências do Acervo, mas não a identidade Renan-first. Antes do ciclo, `_attach_block_evidence()` lia apenas `settings["campaign_hub_snapshot"]`; o job normal fornece `campaign_hub_snapshot_path`. Assim, as propostas guiadas conseguiam ler o snapshot, mas candidatos locais não herdavam seus blocos, riscos ou sinal de locutor. A integração estava parcialmente ligada, exatamente como a preocupação do editor sugeria.

## Comparação antes da correção

| Condição na mesma fonte real | Candidatos | Guiados pelo Chub | Contexto completo | Revisão obrigatória | Identidade disponível |
| --- | ---: | ---: | ---: | ---: | ---: |
| Genérico sem Chub | 30 | 0 | 30 | 3 | 0 |
| Genérico com Chub rico | 30 | 20 | 30 | 20 | 0 |
| Renan-first sem Chub | 30 | 0 | 0 | 30 | 0 |
| Renan-first com Chub rico | 30 | 12 | 0 | 30 | 0 |

Com limiar exploratório de IoU de 0,10 contra os 66 highlights, o recall foi `7,58%` no genérico sem Chub e `27,27%` no genérico com Chub. Em IoU de 0,25, foi `0%` e `9,09%`, respectivamente. Portanto, o Chub demonstrou ganho de **cobertura**, mas não demonstrou ainda ganho de borda precisa, completude, locutor ou aprovação humana.

No modo Renan-first, o snapshot rico reduziu o recall exploratório de `10,61%` para `7,58%` na oferta limitada a 30 candidatos, porque as propostas guiadas entraram antes do pool local sem que a identidade fosse resolvida. Esse resultado não autoriza declarar o Chub vencedor no ranking; ele mostra a necessidade de fusão, deduplicação e orçamento por origem.

## Implementação 6.14

O `ClipSelector` agora lê o snapshot tanto quando ele está embutido nas configurações quanto quando chega pelo caminho persistido usado pelo aplicativo. Isso fecha a lacuna que deixava a evidência rica do Chub fora dos candidatos locais.

Quando um candidato cobre pelo menos 75% de um bloco que informa `renanSpeaking=true`, pertence à conta ativa e o bloco tem tier `owner` ou `allied`, o Furia registra `speaker_identity_basis=campaign_hub_aligned_owner_or_allied` e `speaker_identity_evidence_only=true`. O sinal é conservador: não copia áudio, não finge diarização, não libera risco, não ignora warnings, não altera a proveniência e não transforma uma proposta em corte aprovado. Tiers `third_party`, `critical`, `renanSpeaking=false`, matches fracos ou snapshots desalinhados continuam em revisão.

As flags de identidade, `context_complete` e `qa_bridge` são recalculadas somente para o candidato que recebeu essa evidência alinhada. O modo genérico não recebe bloqueio novo. Foi adicionada regressão para snapshot embutido, snapshot por caminho, tier third-party e ausência de identidade.

## Resultado depois da correção

| Condição na mesma fonte real | Candidatos | Guiados pelo Chub | Contexto completo | Revisão obrigatória | Identidade disponível |
| --- | ---: | ---: | ---: | ---: | ---: |
| Genérico sem Chub | 30 | 0 | 30 | 3 | 0 |
| Genérico com Chub rico | 30 | 20 | 30 | 25 | 0 |
| Renan-first sem Chub | 30 | 0 | 0 | 30 | 0 |
| Renan-first com Chub rico | 30 | 12 | 3 | 30 | 3 |

A mudança resolveu **3 de 30** identidades no lote Renan-first desta fonte, sem liberar os 27 casos restantes. Os três candidatos ainda podem exigir revisão por riscos, warnings, proveniência ou outros gates; identidade é apenas uma dimensão do corte. O ganho foi real, mas parcial. O Chub agora é útil para fornecer evidência alinhada e cobertura, porém ainda não é suficiente para tornar o Furia melhor que uma ferramenta genérica em todos os critérios.

## Validação

| Verificação | Resultado |
| --- | --- |
| Regressões focadas | **45 aprovadas** |
| Suíte completa com asset BlazeFace temporário validado | **541 aprovadas, 4 ignoradas** |
| `compileall` | Aprovado |
| `node --check static/js/app.js` | Aprovado |
| `git diff --check` | Aprovado |
| Scanner de padrões de segredo e artefatos | Limpo |
| Mídia grande, banco, cookies e tokens no commit | Não incluídos |
| Benchmark real | Fonte `3XJfcqn56Rw`, 5.905 s, 1.951 frases, 27 blocos, 66 highlights |

## Decisão da rodada

| Pergunta | Decisão |
| --- | --- |
| O Chub é inútil? | **Não.** Melhorou cobertura exploratória e agora resolveu parte da identidade alinhada. |
| O Chub já torna o Furia superior ao genérico? | **Não demonstrado.** Contexto e payoff ainda não foram comparados por revisão humana em lote suficiente. |
| O prior lexical atual é suficiente? | **Não.** Na fonte persistida do project-57, não alterou as 12 janelas selecionadas. |
| A integração estava completa? | **Não.** O caminho persistido do snapshot era ignorado no anexo de evidência local. |
| A correção foi útil? | **Confirmado, mas parcial.** `0/30` para `3/30` identidades disponíveis no Renan-first com snapshot alinhado. |

## Escopo excluído

Este ciclo não usou sites paralelos, não baixou Reels publicados, não treinou modelo vocal, não guardou credenciais, não chamou MCP durante o processamento local, não fez merge na branch principal e não alterou o ranker para transformar métricas de views em aprovação. O recall foi exploratório e não substitui revisão humana; os dados de legenda do Acervo exigem conferência audiovisual.

## Próxima hipótese única

> **Se o Furia fundir propostas guiadas e candidatos locais por cobertura temporal, deduplicação e quota de origem antes do ranking, então o ganho de recall do Campaign Hub não deverá reduzir o recall do modo Renan-first nem empurrar candidatos guiados de baixa confiança para o topo.**

O próximo ciclo deve comparar uma fusão com quota limitada contra a concatenação atual, usando a mesma fonte e medindo recall em IoU 0,10 e 0,25, taxa de duplicação, contexto completo, identidade, revisão obrigatória e correção humana de bordas.

## Referências

[1] [Furia Clips — branch `claude/repo-access-commits-imgjmk`](https://github.com/SAGIEV007/furia-clips/tree/claude/repo-access-commits-imgjmk).

[2] [FAQ oficial do yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/FAQ).

[3] Campaign Hub — consultas read-only autorizadas nesta sessão para `3XJfcqn56Rw`, seus blocos QA-gated, highlights e transcrição. O fixture de benchmark foi mantido fora do Git em `FuriaClipsData`.
