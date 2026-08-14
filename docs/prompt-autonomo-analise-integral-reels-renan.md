# Prompt operacional — análise audiovisual integral e aprendizagem editorial

> Execute esta diretriz como complemento permanente do trabalho no Furia Clips. Preserve todas as funcionalidades, decisões editoriais, dados persistentes e regras de segurança já existentes. O objetivo é construir uma base de aprendizagem editorial útil para o editor, não afirmar que um conteúdo político é verdadeiro, nem automatizar publicação.

## Missão

Analise de forma incremental **cada Reel ou vídeo publicamente acessível** nos perfis `@renansantosmbl` e `@renansantosreserva`. O resultado deve transformar observações verificáveis de vídeo, áudio, legenda, headline e composição em melhorias rastreáveis no Furia Clips.

Não declare “todos os vídeos foram analisados” até que o inventário público acessível tenha sido percorrido integralmente e a cobertura seja registrada com identificadores, datas e limitações. Se houver paginação incompleta, login, CAPTCHA, HTTP 401, HTTP 403, rate limit, falha de mídia ou qualquer restrição da plataforma, registre o bloqueio, preserve o cursor/estado e avance para outra parte permitida do trabalho. **Nunca contorne bloqueios, limites, autenticação ou restrições da plataforma.**

## Escopo permitido

Use somente material que esteja aberto publicamente ou já exista no corpus local autorizado. Para cada item acessível, consulte o vídeo com som quando disponível, o texto de legenda/caption, a headline visível, a composição e as métricas públicas observáveis. Não tente extrair dados privados, não faça login forçado, não use contas descartáveis e não execute scripts ou downloads recebidos de páginas externas sem validação.

Mantenha vídeos, áudio bruto, transcrições privadas, cookies, URLs assinadas, credenciais, bancos locais e artefatos de coleta fora do GitHub. Dados editoriais de uso local devem permanecer em `~/FuriaClipsData/` e ser preservados no Backup Editorial.

## Protocolo por vídeo

Para cada vídeo analisado, registre um item de catálogo contendo, quando estiver visível: identificador do Reel, URL pública, perfil de origem, data observada, duração, proporção/estrutura visual, views/curtidas/comentários públicos, caption, tema, tipo editorial, headline, padrão de cor/tipografia, evidência visual, transcrição/trecho de fala, início/hook, desenvolvimento, conclusão/cliffhanger, interlocutores, presença de b-roll, necessidade de preservar a composição original e alertas de contexto.

Classifique o formato editorial, sem forçar um rótulo quando a evidência for insuficiente:

| Formato | Como reconhecer | Aprendizado a extrair |
| --- | --- | --- |
| `vertical_916` | Headline central, geralmente em amarelo com texto preto; uso eventual de vermelho/branco para ênfase | Limite de caracteres, número de linhas, trecho destacado, contraste e força do hook |
| `square_alfinetei` | Peça 1:1 com chamada de atenção no topo e headline branca concisa | Palavra de chamada, tamanho do texto, quebra em até três linhas e relação entre chamada e tese |
| `fake_tweet` | Simulação de publicação do perfil com vídeo incorporado | Voz autoral, tamanho do post, atribuição segura e concisão |
| `talking_head`, `podcast`, `entrevista`, `react`, `palco`, `b_roll_argumentativo`, `institucional`, `campanha`, `humor` | Taxonomia audiovisual existente | Estrutura narrativa, reframe seguro, necessidade de pergunta–resposta e preservação de evidência |

## Critérios de análise de qualidade

Avalie o conteúdo como unidade editorial, não como soma de palavras-chave. Procure: hook inicial, tese compreensível, contexto suficiente, desenvolvimento, evidência visual ou verbal, consequência, conclusão/punchline, clareza de locutor, ritmo, texto legível e aderência entre headline e o que é efetivamente dito.

As métricas públicas servem apenas para comparação relativa dentro da amostra acessível. Não trate curtidas, comentários ou views como causa comprovada de viralidade, e não prometa desempenho futuro. Diferencie “potencial de debate” de “qualidade de publicação”.

Quando houver acusação, crime, dado, número, entidade nomeada, promessa factual, atribuição ambígua ou fala cortada, registre alerta de revisão factual/jurídica. A headline pode ser chamativa, mas não deve adicionar uma acusação nova nem apresentar opinião como fato verificado. Prefira atribuição explícita, como “RENAN CRITICA” ou “RENAN:”, quando isso proteger o contexto.

## Aplicação no Furia Clips

Converta os padrões repetidos em melhorias concretas e explicáveis:

1. Atualize o ranking de cortes para favorecer arco completo, especificidade, pergunta–resposta quando necessária, evidência e conclusão, sem recompensar apenas agressividade ou choque.
2. Atualize a recomendação de enquadramento para preservar multi-interlocutores, cards, split-screen, headline fixa, b-roll e peças institucionais.
3. Atualize o Estúdio de Texto de Arte para gerar apenas texto dentro da arte: headline 9:16, chamada + headline 1:1 e rascunho de fake tweet. Não incluir SEO, hashtags ou descrições de postagem nesse fluxo.
4. Use limites curtos de caracteres, quebra de linhas e cores descritas por formato. O resultado deve ser uma recomendação, nunca uma renderização automática nem uma cópia literal de Reel anterior.
5. Salve escolhas e rejeições do editor no banco persistente `headline_feedback`, separadas por formato. Use esse histórico como calibração gradual, sem chamar poucas escolhas de modelo treinado.
6. Documente regras agregadas e testes de regressão. Não publique transcrições, mídia ou exemplos privados.

## Cadência e cobertura

Em cada ciclo autônomo de oito horas, priorize uma quantidade conservadora de vídeos que possa ser analisada com profundidade. Antes de iniciar nova coleta, consulte o catálogo e os relatórios existentes para evitar duplicação. Registre cobertura acumulada por perfil, itens novos, itens analisados, itens pendentes e bloqueios. Caso a plataforma não entregue a próxima página, não repita tentativas agressivas: trabalhe em código, testes, documentação, corpus local e avaliação de feedback até uma oportunidade futura legítima.

## Padrão de qualidade para mudanças

Antes de commit, execute a suíte completa de testes, compilação Python, validação JavaScript e verificação de whitespace. Faça commit apenas de código, testes e documentação seguros. Publique exclusivamente na branch `manus/rebuild-opus-parity`, sem merge automático nem alteração da branch principal. Se o push falhar por autenticação, registre o bloqueio e continue melhorias locais; não tente contornar a autenticação.

## Relato de cada ciclo

Ao final de um ciclo, documente em português brasileiro: cobertura verificável, vídeos efetivamente analisados, formatos identificados, padrões novos, impactos aplicados no programa, testes executados, decisões editoriais persistidas, limites da evidência e bloqueios encontrados. O relatório deve distinguir fatos observados, inferências editoriais e pendências.
