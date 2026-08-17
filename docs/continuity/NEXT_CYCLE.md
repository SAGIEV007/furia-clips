# Próximo ciclo de melhoria — Furia Clips v2.2

## Objetivo da rodada

A release 2.2 tornou mensurável o caso b354: os sete candidatos locais cobriram `0/3` destaques QA-gated do Campaign Hub, embora o mapeamento de timeline e a exportação individual tenham funcionado. O próximo ciclo deve atacar a lacuna de **cobertura da seleção**, não o render.

Reels e posts publicados continuam `reference_only`. Lives longas e gravações cruas continuam `processing_source`. O Estúdio de Texto de Arte, reframe social, diarização completa e download remoto por range continuam adiados.

## Hipótese única

> Se o Furia transformar cada highlight local do snapshot em uma semente de proposta e expandir a semente para a menor janela completa da transcrição, o recall temporal do b354 aumentará sem alterar o ranking, inventar locutor ou depender de consulta externa.

## Procedimento

1. Ler `docs/continuity/START_HERE.md`, `AGENTS.md`, `README.md`, `VERSION`, `docs/continuity/PROJECT_STATE.md`, `docs/continuity/DECISIONS.md`, `docs/VERSIONING.md` e este arquivo.
2. Confirmar branch, commit, diff e baseline; não apagar alterações locais.
3. Repetir a suíte existente antes da mudança e registrar versão/revisão.
4. Reutilizar a memória local autorizada, o benchmark `b354-v1`, os sete candidatos do baseline e o MP4 de bloco já disponível.
5. Para cada um dos três highlights, gerar uma proposta temporal na timeline local e expandi-la apenas até completar frase, tese, pergunta–resposta quando necessário e payoff.
6. Manter `renanSpeaking=false` para o b354; o highlight ser sobre Renan não autoriza atribuir a fala a Renan.
7. Aplicar os mesmos gates de início abrupto, referência sem antecedente, transcrição incompleta, contexto, payoff, risco e locutor.
8. Comparar candidatos antigos, propostas guiadas e destaques com recall, IoU, erro temporal, duração, duplicatas, autossuficiência, payoff e flags de revisão.
9. Persistir o lote como uma nova versão do benchmark, separando claramente proposta de highlight de corte aprovado.
10. Implementar no máximo uma alteração principal na geração de candidatos; não misturar ranking, diarização, reframe, headlines ou editor.
11. Exportar somente uma amostra dos candidatos guiados que passarem pelos gates e validar com FFprobe.
12. Reprocessar o mesmo lote e medir se o recall sai de `0/3` sem aumentar falsos positivos ou apagar falas de terceiros.
13. Só depois de um ganho reproduzível investigar download remoto por range; testar o provedor sem contornar anti-bot e manter fallback seguro.
14. Atualizar `VERSION`, `CHANGELOG.md`, `PROJECT_STATE.md`, `START_HERE.md`, este arquivo e o relatório do ciclo se a alteração for observável.
15. Executar suíte completa, `compileall`, `node --check`, `git diff --check`, verificação de segredos, revisão de mídia e revisão do diff.
16. Fazer commit pequeno, publicar a branch de trabalho e registrar o hash.

## Limites

O aplicativo local não deve chamar o MCP por job. O agente pode consultar o MCP para pesquisa e gerar snapshots sanitizados fora do checkout. O benchmark do Chub é uma referência editorial, não uma verdade absoluta e nunca uma aprovação automática.

A proposta guiada não pode forçar o ranking, substituir a transcrição canônica, inventar locutor ou apagar candidatos de terceiros. Ausência de cobertura continua desconhecida, nunca zero; uma unidade do Acervo pode estar incompleta ou conter erro de ASR.

Não implementar nesta rodada: editor estilo CapCut, correção manual de legendas/headlines, tradução, avatars, voz, música, branding complexo, publicação automática, múltiplas câmeras, formatos sociais ou download remoto por range.

## Formato do relatório

O relatório deve separar confirmado, reproduzido, corrigido, provável, não verificado e bloqueado. Inclua versão, revisão, branch, hipótese, arquivos, benchmark usado, mídia analisada, candidatos antigos e guiados, métricas antes/depois, casos divergentes, testes, limitações e uma única próxima hipótese.
