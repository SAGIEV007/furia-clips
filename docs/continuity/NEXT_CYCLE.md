# Próximo ciclo — validar a ingestão pública no contexto autenticado do usuário

## Estado de partida

A release `6.12` está na branch `claude/repo-access-commits-imgjmk`. Ela adiciona a escolha opcional de navegador local para cookies, User-Agent opcional e mensagens distintas para anti-bot e HTTP 403. A suíte completa passou com `532` testes aprovados e `4` ignorados depois de o asset BlazeFace ser provisionado temporariamente e removido antes do commit. A validação foi feita no sandbox; a sessão autenticada do notebook do usuário não está disponível nele.

Lives longas e arquivos crus continuam sendo `processing_source`. Reels e posts publicados continuam `reference_only` e não devem ser baixados para processamento. A prioridade editorial continua sendo Renan Santos/MBL, com contexto, tese, payoff, locutor correto e headlines fiéis somente depois dos gates.

## Hipótese única

> **Se o usuário selecionar no Furia o mesmo navegador em que concluiu a verificação do YouTube e executar a importação no mesmo computador/IP, então o anti-bot deve deixar de ocorrer; se o stream continuar em HTTP 403, o programa deverá produzir diagnóstico acionável e o usuário deverá conseguir seguir pelo fallback de MP4 local, sem cookies ou credenciais saírem do computador.**

## Procedimento de validação

1. Confirmar no notebook a versão `6.12` e a revisão Git mostrada pelo console.
2. Abrir o YouTube no navegador que passou pela verificação; não copiar cookies, tokens, senhas ou arquivos do perfil para a conversa ou para o repositório.
3. Abrir a aba **Link público**, manter User-Agent vazio no primeiro teste e selecionar o mesmo navegador autenticado.
4. Usar primeiro o botão **Verificar**, depois **Baixar somente** com um link público autorizado de teste. Registrar apenas se o probe e o download passaram, a mensagem sanitizada e a porcentagem de progresso.
5. Se o anti-bot persistir, confirmar que a seleção corresponde ao navegador correto e que o navegador está fechado ou disponível conforme a política do sistema; não tentar extrair a base de cookies manualmente.
6. Se ocorrer HTTP 403 depois da metadata, atualizar o yt-dlp pelo procedimento normal do ambiente autorizado e repetir uma única vez. Não tratar três retries idênticos como solução.
7. Se ainda falhar, usar o fluxo seguro **Importar vídeo** com um MP4 obtido de fonte autorizada. Registrar o bloqueio do provedor e não alterar seleção, ranking ou headlines para mascarar uma falha de ingestão.
8. Validar que o MP4 importado tem áudio, duração, resolução e codec corretos antes de iniciar transcrição ou corte.
9. Se a ingestão passar, repetir com **Transcrever sem cortar** e com **Baixar e transcrever**, verificando que ambas as rotas preservam a preferência local e que nenhuma rotina de cookies aparece no log.
10. Só depois de a aquisição estar confirmada, retomar uma hipótese editorial única: medir a completude contextual de um lote real de Renan/MBL com transcrição canônica e feedback aprovado/rejeitado.

## Critério de sucesso

O ciclo só será considerado bem-sucedido se um link público autorizado for verificado e baixado com a sessão local, ou se o bloqueio for reproduzido com uma mensagem correta e o fallback por MP4 funcionar. Em qualquer cenário, nenhum cookie, token, senha, base de navegador, mídia grande ou transcrição privada pode entrar no GitHub.

## Critério de falha e classificação

Um anti-bot ou 403 persistente não prova que o vídeo é privado. Deve ser classificado como bloqueio de provedor/contexto local, com a mensagem recebida e a versão do yt-dlp registradas de forma sanitizada. Não usar sites paralelos desconhecidos como parte automática do produto; quando o usuário já possuir um MP4 autorizado, importar esse arquivo é o fallback preferencial.

## Escopo excluído desta hipótese

Não alterar ranking, seleção contextual, Campaign Hub, diarização, facetracking, reframe, headlines, Estúdio de Texto de Arte, formatos sociais, publicação automática, editor estilo CapCut ou download remoto por range. Não transformar cookies em configuração obrigatória. Não implementar captura de cookies nem sincronização entre computadores.

## Próximo ciclo editorial após ingestão

Quando a ingestão estiver confirmada, escolher uma única fonte longa de Renan/MBL com transcrição timestampada. Medir baseline de candidatos, autossuficiência, pergunta–resposta, referências anafóricas, tese, payoff, encerramento natural, locutor e headline. Implementar somente a maior falha observada, criar regressões, comparar antes/depois e publicar apenas se o ganho for reproduzível.

## Referências

- [`PROJECT_STATE.md`](PROJECT_STATE.md)
- [`DECISIONS.md`](DECISIONS.md)
- [`CYCLE_27_REPORT_2026-08-20.md`](CYCLE_27_REPORT_2026-08-20.md)
- [`PROMPT_PROXIMOS_CICLOS_6_12.md`](PROMPT_PROXIMOS_CICLOS_6_12.md)
- [`docs/VERSIONING.md`](../VERSIONING.md)
- [FAQ oficial do yt-dlp](https://github.com/yt-dlp/yt-dlp/wiki/FAQ)
