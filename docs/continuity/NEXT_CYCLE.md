# Próximo ciclo de melhoria — Furia Clips v2.0

## Objetivo da rodada

Construir o primeiro benchmark read-only entre candidatos locais do Furia Clips e unidades estruturadas do Campaign Hub/Acervo, usando blocos QA-gated, transcrições, timestamps, perguntas-gatilho, autossuficiência, payoff, riscos e destaques. O objetivo é medir precisão editorial antes de transformar qualquer sinal do Campaign Hub em comportamento do seletor ou do ranker.

Reels e posts publicados continuam `reference_only`. Lives longas e gravações cruas continuam `processing_source`. O Estúdio de Texto de Arte e qualquer editor pós-renderização permanecem adiados.

## Hipótese única

> Se os blocos QA-gated e transcrições reais do Campaign Hub forem comparados temporal e editorialmente com os candidatos locais, será possível reduzir cortes com início abrupto, pergunta sem resposta, payoff ausente e contexto insuficiente sem aumentar indiscriminadamente a duração.

## Procedimento

1. Ler `docs/continuity/START_HERE.md`, `AGENTS.md`, `README.md`, `VERSION`, `docs/continuity/PROJECT_STATE.md`, `docs/continuity/DECISIONS.md`, `docs/VERSIONING.md` e `docs/continuity/CAMPAIGN_HUB_LINEAGE.md`.
2. Confirmar branch, commit, diff e baseline; não apagar alterações locais.
3. Repetir a suíte existente antes da mudança e registrar versão/revisão.
4. Consultar o Campaign Hub apenas em leitura, mantendo conta, plataforma, crosspost, métrica, amostra e estado settled/provisório separados.
5. Montar um lote pequeno de blocos QA-gated e, quando possível, transcrições de criativos publicados; não usar Reel publicado como fonte para recortar novamente.
6. Gerar candidatos pelo pipeline local a partir de uma `processing_source` autorizada ou fixture temporal equivalente.
7. Comparar início, fim, duração, sobreposição temporal, pergunta, resposta, tese, payoff, autossuficiência, contexto, risco, evidência visual e motivo da divergência.
8. Classificar cada caso como `Furia melhor`, `Campaign Hub melhor` ou `ambos precisam de revisão`; não converter o Acervo em verdade absoluta.
9. Criar regressões para pelo menos início abrupto, pergunta sem resposta, payoff ausente e contexto anafórico.
10. Implementar no máximo uma alteração principal, preferencialmente no diagnóstico/benchmark ou na geração de candidatos; não misturar pesos, presets, headlines e renderização.
11. Reprocessar o mesmo lote e comparar métricas antes/depois: erro temporal, autossuficiência, payoff, começo abrupto, perguntas incompletas, duplicatas e duração.
12. Validar transcrição, intervalos, exports e FFprobe quando houver novo render.
13. Se a alteração for observável, atualizar `VERSION`, `CHANGELOG.md`, `PROJECT_STATE.md`, este arquivo e o relatório do ciclo.
14. Executar suíte completa, `py_compile`, `node --check` quando aplicável, `git diff --check`, verificação de segredos e revisão do diff.
15. Fazer commit pequeno, publicar a branch de trabalho e registrar o hash.

## Limites

O aplicativo local não deve chamar o MCP por job. O agente pode consultar o MCP para pesquisa e gerar snapshots sanitizados fora do checkout. Não incluir mídia grande, transcrições privadas, tokens, cookies, URLs privadas ou banco local no Git.

Um prior histórico pode desempatar candidatos que já passaram pelos gates, mas não pode compensar contexto, transcrição, locutor, payoff, evidência visual ou risco. Ausência de cobertura deve ser desconhecida, nunca zero.

Não implementar nesta rodada: editor estilo CapCut, correção manual de legendas/headlines, tradução, avatars, voz, música, branding complexo ou publicação automática.

## Formato do relatório

O relatório deve separar confirmado, reproduzido, corrigido, provável, não verificado e bloqueado. Inclua versão, revisão, branch, hipótese, arquivos, consultas Campaign Hub, lote, mídia analisada, métricas antes/depois, casos divergentes, testes, limitações e uma única próxima hipótese.
