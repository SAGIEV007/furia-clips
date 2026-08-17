# Próximo ciclo — medir recall da ponte Chub em mídia local

## Objetivo da rodada

A release 2.6 adicionou a primeira ponte funcional **Campaign Hub → seeds → expansão contextual → gates → propostas guiadas**. Ela já transforma snapshots em propostas auditáveis quando o contexto autorizado está disponível, mas ainda não foi medida no benchmark b354 com a mídia local correspondente. O próximo ciclo deve testar a ponte no mesmo lote e separar claramente proposta reconhecida, recuperação temporal e corte revisado.

Reels e posts publicados continuam `reference_only`. Lives longas e gravações cruas continuam `processing_source`. O Estúdio de Texto de Arte, reframe social, diarização completa, publicação automática e download remoto por range continuam adiados.

## Hipótese única

> Se um snapshot autorizado e sanitizado do Campaign Hub for instalado localmente e o Furia reprocessar o caso b354 com a ponte da release 2.6, então o recall temporal deve sair do baseline `0/3` sem aumentar falsos positivos, atribuições erradas, truncamentos ou confusão entre quem fala e quem é foco editorial.

## Procedimento

1. Ler `docs/continuity/START_HERE.md`, `docs/continuity/PROMPT_MESTRE_IA.md`, `docs/continuity/CHUB_INTEGRATION_CONTRACT.md`, `AGENTS.md`, `README.md`, `VERSION`, `docs/continuity/PROJECT_STATE.md`, `docs/continuity/DECISIONS.md`, `docs/continuity/COMMIT_MESSAGE_TEMPLATE.md`, `docs/VERSIONING.md` e este arquivo.
2. Confirmar branch, commit, diff e baseline; não apagar alterações locais.
3. Confirmar a suíte, a versão e o benchmark `b354-v1` antes de alterar qualquer lógica.
4. Instalar somente um snapshot autorizado, sanitizado e local usando `scripts/convert_chub_blocks_export.py` ou a importação equivalente da UI; não chamar o MCP a cada corte e não versionar o snapshot privado.
5. Confirmar o vínculo entre o snapshot, o bloco `b3545938-e3a5-4287-82b1-5f7dcdc218c3`, a fonte do YouTube e o MP4 local `workspace/exports/bloco-b354-0-549_*.mp4`; registrar cobertura, hash e método fora do Git quando necessário.
6. Reprocessar o mesmo lote com os sete candidatos antigos e as propostas `campaign_hub_guided`, preservando a transcrição canônica e `renanSpeaking=false` quando terceiro fala.
7. Comparar baseline e propostas com recall, IoU, erro temporal de início/fim, duração, duplicatas, autossuficiência, pergunta–resposta, payoff, locutor, risco, proveniência e flags de revisão.
8. Confirmar que as propostas guiadas permanecem separadas de cortes aprovados e que `third_party`/`gateWarnings` não viram aprovação automática.
9. Se houver ganho reproduzível, exportar somente uma amostra aprovada pela revisão humana e validar FFprobe, duração, resolução, áudio, início e encerramento. Se não houver ganho, registrar o caso divergente e não ampliar o escopo.
10. Repetir o processamento para medir estabilidade entre execuções e verificar que não surgem falsos positivos nem atribuições erradas.
11. Não implementar nesta rodada reframe, headlines, editor estilo CapCut, tradução, avatars, voz, música, branding, publicação automática, múltiplas câmeras, formatos sociais ou download remoto por range.
12. Atualizar `VERSION`, `CHANGELOG.md`, `PROJECT_STATE.md`, `START_HERE.md`, este arquivo e o relatório do ciclo somente se houver alteração observável; documentar hipótese, baseline, métricas e limitações no commit.
13. Executar a suíte completa, `compileall`, `node --check`, `git diff --check`, verificação de segredos, revisão de mídia e revisão do diff. Publicar somente a branch de trabalho, sem merge na principal.

## Contrato de continuidade

Toda alteração relevante deve deixar no GitHub a hipótese, o baseline, o escopo excluído, os testes, as métricas, as limitações e a próxima hipótese. Não deixar essa informação apenas na conversa, no terminal ou no título do commit. Se a rodada não medir recall real, declarar explicitamente que o resultado está bloqueado ou não verificado.

## Limites

O aplicativo local não deve chamar o MCP por job. O agente ou uma ação administrativa explícita pode consultar o MCP para pesquisa e gerar snapshots sanitizados antes do job; o corte normal usa a última memória local válida. O contexto do Chub deve influenciar a geração de propostas quando o snapshot estiver disponível, mas continua não sendo verdade absoluta nem aprovação automática.

A proposta guiada deve alimentar contexto e gates antes do score, sem forçar aprovação. Ela não pode substituir a transcrição canônica, inventar locutor ou apagar candidatos de terceiros. Ausência de cobertura continua desconhecida, nunca zero; uma unidade do Acervo pode estar incompleta ou conter erro de ASR. Blocos e highlights são seeds e referências auditáveis, não cortes finais por definição.

## Formato do relatório

O relatório deve separar **confirmado**, **reproduzido**, **corrigido**, **provável**, **não verificado** e **bloqueado**. Inclua versão, revisão, branch, hipótese, arquivos, benchmark usado, mídia analisada, candidatos antigos e guiados, métricas antes/depois, casos divergentes, testes, limitações e uma única próxima hipótese.

## Referências internas

- [`CHUB_INTEGRATION_CONTRACT.md`](CHUB_INTEGRATION_CONTRACT.md)
- [`PROJECT_STATE.md`](PROJECT_STATE.md)
- [`PROMPT_EXECUCAO_CHUB_CORTES.md`](PROMPT_EXECUCAO_CHUB_CORTES.md)
- [`COMMIT_MESSAGE_TEMPLATE.md`](COMMIT_MESSAGE_TEMPLATE.md)
- [`docs/VERSIONING.md`](../VERSIONING.md)

## Referências

Não há fontes externas necessárias para esta hipótese; ela é derivada dos artefatos versionados do próprio projeto e do benchmark local autorizado.

[1]: CHUB_INTEGRATION_CONTRACT.md
[2]: PROJECT_STATE.md
[3]: PROMPT_EXECUCAO_CHUB_CORTES.md
[4]: COMMIT_MESSAGE_TEMPLATE.md
[5]: ../VERSIONING.md
