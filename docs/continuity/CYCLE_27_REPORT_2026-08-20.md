# Ciclo 27 — cookies locais e diagnóstico acionável para ingestão pública

**Data:** 20 de agosto de 2026  
**Baseline:** release 6.11, commit `2196ce4`  
**Release:** 6.12  
**Branch:** `claude/repo-access-commits-imgjmk`

## Auditoria que abriu a rodada

O baseline reproduzia dois erros distintos no download público do YouTube. Antes de transferir o conteúdo, o `yt-dlp` retornava `Sign in to confirm you’re not a bot`. Em outro vídeo, a metadata era obtida, mas o stream era recusado em aproximadamente `0,5%`, com HTTP 403. Repetir a mesma tentativa três vezes não alterava o resultado.

A hipótese desta rodada foi: **se o Furia expuser uma escolha explícita do navegador local autenticado e encaminhar somente o nome do navegador e um User-Agent opcional às rotas públicas, o usuário poderá repetir a verificação usando o mesmo contexto local que resolveu o bloqueio, sem compartilhar cookies, tokens ou credenciais.**

## Implementação

A camada `modules/source_ingest.py` passou a normalizar os navegadores aceitos (`chrome`, `chromium`, `edge`, `firefox`, `brave`, `opera` e `vivaldi`), tratar `Opera GX` como `opera`, rejeitar valores desconhecidos e montar `cookiesfrombrowser` apenas dentro do processo local do `yt-dlp`. O User-Agent é limitado a 500 caracteres e nunca é registrado com cookies.

As mensagens de erro agora distinguem verificação anti-bot de HTTP 403 no stream. A primeira orienta o usuário a escolher o navegador em que concluiu a verificação; a segunda explica que a metadata funcionou, mas o stream foi recusado, sugerindo cookies locais, atualização do contexto ou importação de um MP4 autorizado como fallback.

`config.py` recebeu `source_cookie_browser` e `source_user_agent`. `app.py` passou a ler esses campos do payload ou das configurações persistidas e a encaminhá-los às rotas `/api/source/probe`, `/api/source/import` e `/api/source/transcribe`, incluindo download de vídeo, áudio e legendas públicas. O programa persiste somente a preferência do navegador e o User-Agent; não persiste o conteúdo da base de cookies.

A aba **Link público** ganhou um seletor de navegador, um campo opcional de User-Agent e um aviso explícito de que os cookies permanecem locais. O JavaScript envia os dois valores ao probe, ao download simples, ao download com transcrição e à transcrição sem cortes, e reidrata a preferência salva ao abrir o painel.

## Escopo excluído

Esta rodada não contornou CAPTCHA, não extraiu cookies, não transferiu credenciais, não baixou Reels publicados, não alterou a seleção editorial, o ranking, o Campaign Hub, as headlines, os formatos de corte, o reframe ou a branch principal. Também não declara que o bloqueio externo está resolvido em um computador específico, porque o sandbox não possui a sessão autenticada do notebook do usuário.

## Validação

| Verificação | Resultado |
| --- | --- |
| Testes focados `tests/test_sources_and_context.py` | **27 aprovados** |
| Suíte completa após provisionamento temporário do asset ambiental | **532 aprovados, 4 ignorados** |
| Falha inicial da suíte | 1 falha ambiental: modelo BlazeFace ausente |
| Asset ambiental | Baixado temporariamente, SHA-256 conferido, removido antes do commit |
| `node --check static/js/app.js` | Aprovado |
| `git diff --check` | Aprovado |
| Verificação de segredos/cookies | Nenhum cookie, token, chave ou mídia adicionada ao commit |
| Download real com sessão autenticada do usuário | Não verificado no sandbox; exige o navegador/contexto local do usuário |

A falha inicial do teste facial não era causada pela alteração. Para separar o problema ambiental da regressão, o modelo público especificado no próprio teste foi provisionado temporariamente, conferido pelo hash esperado e removido antes da publicação. Sem o asset, a suíte apresentava 531 aprovados, 1 falha e 4 ignorados; com o asset temporário, todos os testes executáveis passaram.

## Classificação das conclusões

| Classificação | Conclusão |
| --- | --- |
| **Reproduzido** | Os dois padrões de falha do YouTube são diferentes: anti-bot antes do download e 403 depois da metadata. |
| **Corrigido** | A preferência opcional de navegador/User-Agent percorre probe, importação de vídeo, importação de áudio e legendas. |
| **Corrigido** | Navegadores inválidos são rejeitados com mensagem clara, e `Opera GX` é normalizado para `opera`. |
| **Corrigido** | As mensagens anti-bot e 403 passaram a indicar ações diferentes e seguras. |
| **Confirmado** | 532 testes passaram após o asset ambiental temporário; `node --check` e `git diff --check` passaram. |
| **Não verificado** | A resolução do bloqueio em um notebook específico com sessão autenticada do YouTube. |
| **Bloqueado** | Não foi possível provar o download real com cookies do navegador do usuário no sandbox, pois cookies não podem ser compartilhados nem simulados como se fossem a sessão do usuário. |

## Próxima hipótese única

> **Se o usuário selecionar no Furia o mesmo navegador em que concluiu a verificação do YouTube e executar a importação no mesmo computador/IP, então o anti-bot deve deixar de ocorrer; se o stream ainda retornar 403, o diagnóstico deverá orientar atualização do yt-dlp ou o fallback seguro por MP4 local, sem transformar retries idênticos em falsa solução.**

O teste operacional desta hipótese deve ser feito no notebook do usuário, com o YouTube aberto e autenticado no navegador selecionado. O resultado deve registrar apenas a mensagem sanitizada, a versão do Furia, o navegador escolhido e o status do download; nunca registrar cookies, tokens, URLs privadas ou dados pessoais.

## Referências

[1]: https://github.com/yt-dlp/yt-dlp/wiki/FAQ — FAQ oficial do yt-dlp sobre cookies do navegador, IP e User-Agent.  
[2]: https://github.com/yt-dlp/yt-dlp — Repositório oficial do yt-dlp e manutenção do downloader.
