# Próximo ciclo de melhoria — Furia Clips v2.4

## Objetivo da rodada

A release 2.2 tornou mensurável o caso b354: os sete candidatos locais cobriram `0/3` destaques QA-gated do Campaign Hub, embora o mapeamento de timeline e a exportação individual tenham funcionado. O próximo ciclo deve construir a ponte funcional **Campaign Hub → seleção contextualizada → revisão → renderização**, não apenas ampliar a visualização em blocos.

Reels e posts publicados continuam `reference_only`. Lives longas e gravações cruas continuam `processing_source`. O Estúdio de Texto de Arte, reframe social, diarização completa, publicação automática e download remoto por range continuam adiados.

## Hipótese única

> Se o Furia importar um lote autorizado de unidades do Campaign Hub, transformar cada bloco/highlight em seed semântica e temporal, alinhar a seed à fonte local e expandi-la até a menor janela completa que passe pelos gates de contexto e locutor, então o recall do benchmark b354 deve sair de `0/3` sem aumentar falsos positivos, atribuições erradas ou cortes truncados.

## Procedimento

1. Ler `docs/continuity/START_HERE.md`, `docs/continuity/PROMPT_MESTRE_IA.md`, `docs/continuity/CHUB_INTEGRATION_CONTRACT.md`, `AGENTS.md`, `README.md`, `VERSION`, `docs/continuity/PROJECT_STATE.md`, `docs/continuity/DECISIONS.md`, `docs/continuity/COMMIT_MESSAGE_TEMPLATE.md`, `docs/VERSIONING.md` e este arquivo.
2. Confirmar branch, commit, diff e baseline; não apagar alterações locais.
3. Repetir a suíte existente antes da mudança e registrar versão/revisão.
4. Reutilizar a memória local autorizada, o benchmark `b354-v1`, os sete candidatos do baseline, o MP4 de bloco já disponível e o snapshot Chub correspondente.
5. Para cada bloco/highlight autorizado, recuperar resumo, pergunta-gatilho, highlights, frases, riscos, locutor, proveniência e versão da fonte.
6. Alinhar a unidade Chub à fonte local por YouTube ID, timestamps, manifesto e texto; registrar mismatch ou cobertura parcial.
7. Gerar uma seed de proposta e recuperar na timeline local as frases anteriores, a pergunta, a resposta, a tese, a evidência e o payoff necessários.
8. Manter `renanSpeaking=false` para o b354; o highlight ser sobre Renan não autoriza atribuir a fala a Renan.
9. Aplicar gates de início abrupto, referência sem antecedente, transcrição incompleta, contexto, payoff, risco, locutor e mídia antes do ranking.
10. Comparar candidatos antigos, propostas guiadas e destaques com recall, IoU, erro temporal, duração, duplicatas, autossuficiência, pergunta–resposta, payoff, locutor e flags de revisão.
11. Persistir o lote como uma nova versão do benchmark, separando seed, proposta guiada, corte revisado e highlight de referência.
12. Implementar no máximo uma alteração principal na geração guiada; não misturar reframe, headlines, editor, publicação ou download remoto por range.
13. Exportar somente uma amostra das propostas guiadas que passarem pelos gates e validar com FFprobe e inspeção audiovisual.
14. Reprocessar o mesmo lote e medir se o recall sai de `0/3` sem aumentar falsos positivos, atribuições erradas ou cortes truncados.
15. Só depois de um ganho reproduzível investigar download remoto por range; testar o provedor sem contornar anti-bot e manter fallback seguro.
16. Atualizar `VERSION`, `CHANGELOG.md`, `PROJECT_STATE.md`, `START_HERE.md`, este arquivo e o relatório do ciclo se a alteração for observável.
17. Executar suíte completa, `compileall`, `node --check`, `git diff --check`, verificação de segredos, revisão de mídia e revisão do diff.
18. Atualizar `PROJECT_STATE.md`, `CHANGELOG.md`, o relatório do ciclo e qualquer decisão durável; fazer commit pequeno com corpo completo conforme `COMMIT_MESSAGE_TEMPLATE.md`, publicar a branch de trabalho e registrar o hash final conferido com `git rev-parse`.

## Contrato de continuidade

Toda alteração relevante deve deixar no GitHub a hipótese, o baseline, o escopo excluído, os testes, as métricas, as limitações e a próxima hipótese. Não deixar essa informação apenas na conversa, no terminal ou no título do commit. Se a rodada for somente documental, declarar isso explicitamente e não reivindicar melhoria funcional.

## Limites

O aplicativo local não deve chamar o MCP por job. O agente ou uma ação administrativa explícita pode consultar o MCP para pesquisa e gerar snapshots sanitizados antes do job; o corte normal usa a última memória local válida. O contexto do Chub deve influenciar a geração de propostas quando o snapshot estiver disponível, mas continua não sendo verdade absoluta nem aprovação automática.

A proposta guiada deve alimentar contexto e gates antes do score, sem forçar aprovação. Ela não pode substituir a transcrição canônica, inventar locutor ou apagar candidatos de terceiros. Ausência de cobertura continua desconhecida, nunca zero; uma unidade do Acervo pode estar incompleta ou conter erro de ASR. Blocos e highlights são seeds e referências auditáveis, não cortes finais por definição.

Não implementar nesta rodada: editor estilo CapCut, correção manual de legendas/headlines, tradução, avatars, voz, música, branding complexo, publicação automática, múltiplas câmeras, formatos sociais ou download remoto por range.

## Formato do relatório

O relatório deve separar confirmado, reproduzido, corrigido, provável, não verificado e bloqueado. Inclua versão, revisão, branch, hipótese, arquivos, benchmark usado, mídia analisada, candidatos antigos e guiados, métricas antes/depois, casos divergentes, testes, limitações e uma única próxima hipótese.
