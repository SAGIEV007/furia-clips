# Próximo ciclo de melhoria — Furia Clips v1.4

## Objetivo da rodada

Processar uma fonte longa do Renan com transcrição completa ou cobertura significativamente maior e calibrar a recuperação de setup, referências anafóricas, pergunta/resposta, tese e payoff sem reduzir a concisão. O Estúdio de Texto de Arte permanece fora da próxima hipótese principal até que a seleção e a estabilidade estejam mais maduras.

## Hipótese única

> A expansão contextual atual ainda precisa ser calibrada em trechos longos: quando uma referência anafórica ou uma pergunta aparece perto de uma mudança de pauta, o seletor deve recuperar o antecedente e a resposta mínima, mas parar antes da pauta seguinte, produzindo uma janela menor e autossuficiente.

A hipótese de hard gate para `context_complete=false` foi validada na release 1.4 e não deve ser misturada com novos pesos de headline ou mudanças visuais nesta próxima rodada.

## Procedimento

1. Ler `AGENTS.md`, `README.md`, `VERSION`, `docs/continuity/PROJECT_STATE.md`, `docs/continuity/DECISIONS.md`, `docs/VERSIONING.md` e o `git status`.
2. Confirmar a versão pública e capturar a revisão Git nos logs.
3. Repetir a suíte existente antes da mudança.
4. Usar uma live longa ou um lote longo autorizado do Renan/MBL; Reels publicados continuam sendo apenas `reference_only`.
5. Obter a transcrição completa com timestamps. Se o ambiente não suportar a transcrição integral, registrar o bloqueio e usar um lote reproduzível, sem alegar cobertura completa.
6. Medir baseline: início abrupto, referência ausente, pergunta sem resposta, payoff incompleto, duração, redundância, duplicata, candidatos adiados pelo gate, taxa de renderização e falha de validação.
7. Criar ou confirmar um teste regressivo para a hipótese de antecedente/pergunta e mudança de pauta.
8. Fazer uma única alteração no seletor ou no módulo de contexto responsável pela menor janela suficiente.
9. Reprocessar a mesma mídia e comparar antes/depois com os mesmos critérios.
10. Validar transcrição, timestamps, artefato visual e FFprobe.
11. Só depois avaliar uma hipótese separada do Estúdio de Texto de Arte, usando headlines derivadas do trecho correto, nunca do SRT de outra fonte.
12. Se a alteração for observável, atualizar `VERSION` de acordo com `docs/VERSIONING.md`; não incrementar apenas por conveniência.
13. Atualizar `PROJECT_STATE.md`, `DECISIONS.md` quando necessário, `CHANGELOG.md` e este arquivo.
14. Fazer `git diff --check`, verificar segredos e executar testes completos.
15. Commitar na branch de trabalho, fazer push e registrar branch/hash/testes.

## Formato do relatório

O relatório final deve indicar o que foi confirmado, reproduzido, corrigido, não verificado ou bloqueado. Inclua versão, revisão, branch, hipótese, arquivos, testes, mídia analisada, métricas antes/depois, exemplos de cortes, qualidade da headline por formato, limitações e uma única próxima hipótese.
