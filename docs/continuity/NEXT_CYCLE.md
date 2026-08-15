# Próximo ciclo de melhoria — Furia Clips v1.0

## Objetivo da rodada

Executar um benchmark audiovisual público do Renan Santos usando exemplos do Campaign Hub e validar a hipótese de que a seleção contextual produz a **menor janela suficiente** sem eliminar setup, referência, tese ou payoff.

## Hipótese única

> Expandir ou contrair a janela com base em referências anafóricas, pergunta/resposta e fechamento semântico melhora a autossuficiência dos cortes sem aumentar redundância desnecessária.

Não altere simultaneamente os pesos de headline, os presets visuais e a infraestrutura, salvo se uma falha impedir a execução. Se uma correção de infraestrutura for necessária, registre-a como bloqueio operacional separado.

## Procedimento

1. Ler `AGENTS.md`, `README.md`, `VERSION`, `docs/continuity/PROJECT_STATE.md`, `docs/continuity/DECISIONS.md`, `docs/VERSIONING.md` e o `git status`.
2. Confirmar a versão pública e capturar a revisão Git nos logs.
3. Repetir a suíte existente antes da mudança.
4. Selecionar um pequeno lote público do Renan no Campaign Hub, priorizando cortes publicados e tentando cobrir `16:9 original`, `1:1 Alfinetei` e `fake tweet`.
5. Para cada exemplo acessível, registrar URL, perfil, plataforma, duração, intervalo, transcrição, legenda, headline, formato, sinais visuais e métricas disponíveis.
6. Processar ao menos uma mídia completa pelo Furia Clips e salvar manifestos fora do Git quando forem grandes.
7. Medir baseline: início abrupto, referência ausente, pergunta sem resposta, payoff incompleto, duração, redundância, duplicata, taxa de renderização e falha de validação.
8. Criar ou confirmar um teste que falhe para o caso editorial escolhido.
9. Fazer a menor alteração em `clip_selector.py`, `editorial_ranker.py` ou módulo responsável.
10. Reprocessar a mesma mídia e comparar antes/depois com os mesmos critérios.
11. Validar texto, timestamps, artefato visual e FFprobe.
12. Se a alteração for observável, atualizar `VERSION` de acordo com `docs/VERSIONING.md`; não incrementar apenas por conveniência.
13. Atualizar `PROJECT_STATE.md`, `DECISIONS.md` quando necessário, `CHANGELOG.md` e este arquivo.
14. Fazer `git diff --check`, verificar segredos e executar testes completos.
15. Commitar em branch de trabalho, fazer push e registrar branch/hash/testes.

## Formato do relatório

O relatório final deve indicar o que foi confirmado, reproduzido, corrigido, não verificado ou bloqueado. Inclua versão, revisão, branch, hipótese, arquivos, testes, mídia analisada, métricas antes/depois, exemplos de cortes, qualidade da headline por formato, limitações e uma única próxima hipótese.
