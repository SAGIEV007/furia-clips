# Próximo ciclo — evidência temporal de locutor do Campaign Hub

## Estado de partida

A release `6.13` está na branch `claude/repo-access-commits-imgjmk`. Ela impede que uma transcrição sem diarização seja tratada como contexto completo no foco Renan Santos/MBL. Na transcrição persistida usada na medição, `9/9` candidatos Renan-first ficaram com identidade indisponível e revisão obrigatória, enquanto o caminho genérico preservou `5/5` candidatos completos. A suíte completa terminou com `537` testes aprovados e `4` ignorados depois de o asset BlazeFace ser provisionado temporariamente e removido antes do commit.

Lives longas e arquivos crus continuam sendo `processing_source`. Reels e posts publicados continuam `reference_only` e não devem ser baixados para processamento. A prioridade editorial continua sendo Renan Santos/MBL, com contexto, tese, payoff, locutor correto e headlines fiéis somente depois dos gates.

A release `6.12` ainda aguarda teste operacional no notebook do usuário usando o navegador local que passou pela verificação do YouTube. Esse bloqueio de ingestão não deve ser mascarado nem misturado à hipótese editorial desta rodada.

## Hipótese única

> **Se um snapshot local autorizado do Campaign Hub trouxer `renanSpeaking`, `speakersNote`, tier de confiança e intervalos temporais alinhados à fonte em processamento, então o Furia poderá resolver parte da identidade de locutor como evidência auditável; quando o snapshot estiver ausente, desatualizado, terceiro ou desalinhado, a revisão obrigatória deverá permanecer.**

## Procedimento de validação

1. Obter somente um export autorizado e sanitizado do Campaign Hub, sem cookies, tokens, credenciais, mídia grande ou dados pessoais. O snapshot deve permanecer fora do checkout, em `FuriaClipsData/campaign_hub/profile.json`.
2. Validar a memória local pelo importador existente e registrar apenas status, versão, contas, contagens e hash sanitizado do snapshot.
3. Selecionar uma fonte longa de Renan/MBL com transcrição timestampada canônica e, se possível, correspondência no Acervo. Não baixar nem processar Reels já publicados.
4. Medir o baseline sem snapshot: candidatos, identidade disponível, revisão obrigatória, contexto completo, payoff e cobertura temporal.
5. Ativar o snapshot local e repetir a seleção. Comparar quantos candidatos foram resolvidos como `renan_confirmado`, quantos permaneceram `nao_confirmado` e quantos foram marcados como `terceiro_ou_indeterminado`.
6. Exigir sobreposição temporal e textual suficiente antes de transferir evidência do Hub para um candidato local. Um match fraco deve permanecer como evidência ausente, não como identidade afirmada.
7. Manter `qa_gated`, tier, `speakersNote`, riscos e proveniência visíveis na revisão. Nenhum campo do snapshot poderá liberar sozinho um corte com contexto, payoff, timing ou transcrição problemáticos.
8. Criar regressões para snapshot ausente, match alinhado, match desalinhado, `renanSpeaking=false`, tier terceiro e fonte sem cobertura.
9. Reexecutar a suíte completa, validar o smoke test e comparar antes/depois em uma fonte real ou em um export autorizado real. Só incrementar a versão se o comportamento observável melhorar sem regressão.

## Critério de sucesso

O ciclo será bem-sucedido se a evidência temporal do snapshot resolver corretamente uma parte mensurável dos candidatos sem aumentar falsos `renan_confirmado`, mantiver revisão nos casos incertos e não alterar o modo genérico. A medição deve separar precisão de identidade, cobertura e taxa de revisão.

## Critério de falha e classificação

Se o snapshot não existir, não possuir intervalos alinháveis ou tiver `renanSpeaking` ausente, o resultado correto é continuar em revisão. Isso será classificado como bloqueio de evidência, não como falha do seletor. Se o match temporal produzir candidatos duplicados, órfãos ou deslocados, corrigir o alinhamento antes de alterar pesos do ranking.

## Escopo excluído desta hipótese

Não consultar MCP durante cada job, não enviar transcrições privadas ao Campaign Hub, não importar cookies ou tokens, não treinar modelo vocal, não alterar o ranking por views, não baixar Reels publicados, não alterar facetracking, reframe, Estúdio de Texto de Arte, publicação automática ou editor estilo CapCut. O download autenticado da 6.12 permanece uma validação operacional separada.

## Próximo ciclo posterior

Depois de medir identidade com snapshot alinhado, escolher uma única fonte longa e calibrar a completude contextual com decisões editoriais aprovadas/rejeitadas. O dataset deve distinguir `setup`, `contexto`, `tese`, `evidência`, `payoff`, `locutor`, `headline` e `formato`, sem transformar viralidade em rótulo automático.

## Referências

- [`PROJECT_STATE.md`](PROJECT_STATE.md)
- [`DECISIONS.md`](DECISIONS.md)
- [`CYCLE_28_REPORT_2026-08-20.md`](CYCLE_28_REPORT_2026-08-20.md)
- [`PROMPT_PROXIMOS_CICLOS_6_12.md`](PROMPT_PROXIMOS_CICLOS_6_12.md)
- [`docs/VERSIONING.md`](../VERSIONING.md)
- [FAQ oficial do yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/FAQ)
