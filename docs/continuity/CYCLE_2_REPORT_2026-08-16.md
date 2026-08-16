# Relatório do ciclo 2 — Prompt 2

## Objetivo

Retomar a versão 1.2, obter legitimamente uma live longa do Garimpo/Criadores, processá-la no Furia Clips e implementar uma única melhoria mensurável baseada em evidência real. Reels publicados permaneceram `reference_only` e não foram baixados para novo corte.

## Fonte operacional localizada

O painel autenticado do Criadores forneceu o bloco `Partido Missão quer formar nova elite e libertar Santa Catarina do centrão`, da live `RENAN SANTOS EM CHAPECÓ - SC`. A live possui 126:11; o bloco começa em 15:23, dura 10:51 e informa 2 segundos de contexto em cada borda. A fonte original é https://www.youtube.com/watch?v=WsbH8EixPqg&t=921s.

O bloco contém headline editorial, 112 trechos timestampados, quatro momentos fortes e a transcrição completa do intervalo. A transcrição do Acervo confirmou 114 frases na janela consultada, com a fonte `youtube_auto`, qualidade automática e exigência de verificação no áudio. O conteúdo apresenta setup sobre liderança e troca geracional, a tese de formar uma elite, definição de elite como influência sobre imaginário, leis e comportamentos, o ecossistema do Partido Missão e a progressão para pacto federativo/Santa Catarina.

## Aquisição

O probe direto do Furia para a URL do YouTube retornou o bloqueio anti-bot do yt-dlp. O endpoint autenticado do Criadores retornou HTTP 201 e uma `launchUrl` temporária `corteiros://download/...`. O helper oficial Corteiros foi executado pelo binário Linux x64, com flags de compatibilidade e display virtual Xvfb, mas não concluiu e não produziu MP4. Não foram extraídos cookies, tokens ou credenciais, e nenhum site externo de download foi usado.

## Validação do repositório

A versão pública permaneceu `1.2`. A suíte passou com `284 passed`; `py_compile` e `git diff --check` foram aprovados. Dois testes de identidade de runtime que ainda esperavam `1.1` foram alinhados para `1.2` e publicados no commit `a6846f9`.

## Decisão editorial

Sem um MP4 longo ou uma transcrição local com a mesma semântica de processamento, não foi feita uma nova alteração de ranking/contexto neste ciclo. Isso evita calibrar o Furia apenas sobre legenda automática do Campaign Hub, que é evidência de navegação e não substitui áudio/vídeo.

## Próximo passo

Obter o MP4 do bloco pelo Corteiros em um computador compatível, importar no Furia e comparar os candidatos gerados com o intervalo do Garimpo. A próxima hipótese permanece: calibrar recuperação de setup, pergunta/resposta, antecedentes anafóricos e headline usando a linhagem `live → bloco → transcrição → corte → referência publicada`.
