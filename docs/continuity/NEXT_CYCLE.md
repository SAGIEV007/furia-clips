# Próximo ciclo de melhoria — Furia Clips v2.1

## Objetivo da rodada

Construir o benchmark persistente da primeira onda entre candidatos locais do Furia Clips e unidades estruturadas do Campaign Hub/Acervo, começando pelo caso real b354 já validado. O benchmark deve reutilizar a comparação existente, registrar erro temporal, sobreposição, destaque coberto/perdido, locutor, contexto, payoff, risco e motivo da divergência. A rodada deve também permitir exportar um destaque individual da timeline local de um MP4 de bloco, sem depender de consulta ao Chub no corte.

Reels e posts publicados continuam `reference_only`. Lives longas e gravações cruas continuam `processing_source`. O Estúdio de Texto de Arte e qualquer editor pós-renderização permanecem adiados.

## Hipótese única

> Se o Furia persistir a comparação entre candidatos locais e os três destaques do b354, usando o mapeamento da fonte longa para o MP4 local e exportando highlights individuais, será possível medir recall e precisão editorial antes de aumentar a influência do Campaign Hub no ranking.

## Procedimento

1. Ler `docs/continuity/START_HERE.md`, `AGENTS.md`, `README.md`, `VERSION`, `docs/continuity/PROJECT_STATE.md`, `docs/continuity/DECISIONS.md`, `docs/VERSIONING.md` e `docs/continuity/CAMPAIGN_HUB_LINEAGE.md`.
2. Confirmar branch, commit, diff e baseline; não apagar alterações locais.
3. Repetir a suíte existente antes da mudança e registrar versão/revisão.
4. Consultar o Campaign Hub apenas em leitura, mantendo conta, plataforma, crosspost, métrica, amostra e estado settled/provisório separados.
5. Reutilizar o export local do vídeo `57nyfP9IDW4` e confirmar o bloco b354, seus três destaques e o mapeamento `6142.56–6692.0` para `0–549.44`.
6. Gerar ou carregar candidatos locais a partir do MP4 b354; não usar Reel publicado como fonte para recortar novamente.
7. Comparar início, fim, duração, sobreposição temporal, pergunta, resposta, tese, payoff, autossuficiência, contexto, risco, evidência visual e motivo da divergência.
8. Persistir cada comparação com origem, versão do benchmark, confiança, classificação `Furia melhor`, `Campaign Hub melhor` ou `ambos precisam de revisão`.
9. Mapear os três highlights QA-gated para a timeline local e testar exportação individual de cada highlight.
10. Criar regressões para highlight coberto, highlight perdido, mapeamento de timeline, início abrupto, pergunta sem resposta e payoff ausente.
11. Implementar no máximo uma alteração principal, preferencialmente no benchmark/highlight export; não misturar diarização, reframe, headlines e edição.
12. Reprocessar o mesmo lote e comparar recall de highlights, IoU, erro temporal, autossuficiência, payoff, duplicatas e duração.
13. Investigar range remoto apenas depois do caminho local; testar o provedor sem contornar anti-bot e manter fallback seguro.
14. Validar transcrição, intervalos, exports e FFprobe quando houver novo render.
15. Se a alteração for observável, atualizar `VERSION`, `CHANGELOG.md`, `PROJECT_STATE.md`, este arquivo e o relatório do ciclo.
16. Executar suíte completa, `py_compile`, `node --check` quando aplicável, `git diff --check`, verificação de segredos e revisão do diff.
17. Fazer commit pequeno, publicar a branch de trabalho e registrar o hash.

## Limites

O aplicativo local não deve chamar o MCP por job. O agente pode consultar o MCP para pesquisa e gerar snapshots sanitizados fora do checkout. Não incluir mídia grande, transcrições privadas, tokens, cookies, URLs privadas ou banco local no Git.

Um prior histórico pode desempatar candidatos que já passaram pelos gates, mas não pode compensar contexto, transcrição, locutor, payoff, evidência visual ou risco. Ausência de cobertura deve ser desconhecida, nunca zero.

Não implementar nesta rodada: editor estilo CapCut, correção manual de legendas/headlines, tradução, avatars, voz, música, branding complexo ou publicação automática.

## Formato do relatório

O relatório deve separar confirmado, reproduzido, corrigido, provável, não verificado e bloqueado. Inclua versão, revisão, branch, hipótese, arquivos, consultas Campaign Hub, lote, mídia analisada, métricas antes/depois, casos divergentes, testes, limitações e uma única próxima hipótese.
