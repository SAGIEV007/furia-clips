# Auditoria do Criadores/Missão — 14/08/2026

## Escopo e cautela

A auditoria usa somente a interface autenticada autorizada pelo usuário e registra capacidades observáveis. Não serão copiadas senhas, cookies, tokens, URLs assinadas de mídia ou dados de terceiros além do necessário para compreender o produto. A existência de uma métrica ou classificação no Criadores não prova a fórmula interna nem autoriza reproduzi-la literalmente no Furia Clips.

## Estado de acesso

A sessão autenticada reconheceu o perfil `Fernando Filho` (`@fernandof`). O caminho `/painel` abriu, mas retornou a mensagem de falha transitória “Não foi possível atualizar este espaço”, oferecendo “Tentar novamente”. O caminho `/garimpo` carregou normalmente e mostrou a área “Seu acervo de ideias”, com busca, filtros, busca de blocos e geração de novas pautas.

## Área Recentes

A página [Vídeos recentes do Garimpo](https://criadores.missao.org.br/garimpo/recentes) informa que ordena vídeos do mais novo para o mais antigo e que cada card abre diretamente no primeiro bloco disponível. Na amostra carregada, o site exibiu:

| Publicação | Fonte | Duração | Blocos disponíveis |
| --- | --- | ---: | ---: |
| Sabatina completa Renan Santos na Blockchain.Rio 2026 | Entrevistas do Renan | 46:27 | 11 |
| Renan ao vivo — Fórum Caminho da Liberdade | Canal do Renan — lives | 1:23:35 | 39 |
| Janja vai para cima do Discord — Análises Renais | Canal do Renan — lives | 1:16:41 | 29 |
| Renan Santos, Kim Kataguiri e Renato Battista — Podcast 3 Irmãos #1033 | Entrevistas do Renan | 1:45:30 | 33 |
| Batemos 10%! — Análises Renais | Canal do Renan — lives | 1:24:36 | 33 |
| Limão Rosa — ao vivo | Canal do Renan — lives | 1:33:18 | 4 |
| Discurso Renan Santos ao vivo — Congresso Paraná | Canal do Renan — lives | 1:06:14 | 25 |
| Preparação para o início da campanha — Análises Renais | Canal do Renan — lives | 49:45 | 13 |
| Renan Santos faz pronunciamento oficial — Análises Renais | Canal do Renan — lives | 48:00 | 15 |
| g1 e GloboNews entrevistam hoje Renan Santos | Entrevistas do Renan | 1:40:21 | 26 |

A lista é útil para o Furia Clips por mostrar uma unidade editorial intermediária entre live e clip: **bloco**. A quantidade de blocos por vídeo pode inspirar uma previsão de oferta de candidatos, mas não deve virar score de viralidade. A duração e a fonte podem alimentar priorização de fila, enquanto a família de conteúdo diferencia live, entrevista e transmissão musical/ambiente.

## Área Garimpo

A página [Pautas do Garimpo](https://criadores.missao.org.br/garimpo) expôs cards com fonte, data de publicação, categoria, duração, número de momentos sugeridos, uma tese em headline e um resumo contextual. A amostra apresentou categorias como Eleições e Política, Agropecuária e Tecnologia, Segurança Pública e Gestão Pública. Também mostrou um marcador textual equivalente a “Fala forte e aproveitável”.

O padrão editorial observável é: **tese curta**, **explicação contextual**, **momento específico aproveitável** e **ação de abrir/adicionar à lista**. A tradução segura para o Furia Clips é um objeto de candidato com `topic`, `thesis`, `context_summary`, `moment_reason`, `source_family`, `duration`, `candidate_count` e `review_state`. O sistema não deve importar alegações como fatos; deve preservá-las como texto atribuído e manter os flags de revisão factual/jurídica.

## Próximas áreas a consultar

A auditoria deve continuar em `/videos`, `/conexoes`, `/ranking`, `/convites`, `/perfil`, `/garimpo/buscar` e nas páginas de bloco abertas a partir do Garimpo. O painel inicial requer nova tentativa apenas se o site continuar oferecendo a ação sem pedir dados adicionais.

## Busca de blocos

A página [Buscar no Garimpo](https://criadores.missao.org.br/garimpo/buscar) descreve que o usuário encontra “momentos de fala e contexto” e pode ler antes de assistir. Ela separa explicitamente “resultados são blocos, não conteúdo pronto”, oferece busca textual, filtros e categorias iniciais como Agropecuária e Tecnologia, Corrupção, Costumes, Economia, Educação e Eleições e Política. Ao selecionar Eleições e Política, a URL preserva `q` e `category`, confirmando que o filtro é parte do estado pesquisável e que a busca retorna uma coleção de blocos, não uma publicação final.

A decisão aplicável ao Furia Clips é manter uma camada intermediária entre candidato bruto e clip aprovado: o sistema pode agrupar segmentos por tese e permitir busca por assunto, mas deve continuar exigindo revisão de contexto, conclusão e enquadramento antes de renderizar/publicar.

A busca por Eleições e Política apresentou estado de carregamento (“Procurando no acervo”) nesta rodada; não foram inventados resultados enquanto a resposta dinâmica não terminou.

## Resultado observável da busca “Eleições e Política”

Após o carregamento, o Criadores informou “20 primeiros blocos” e uma navegação por teclado `j/k` com `Enter` para abrir. Cada resultado exibiu fonte, data, título/tese, resumo, duração do bloco, posição de início no vídeo, categoria, tags, uma justificativa “Momento forte” e um número de momentos sugeridos. Exemplos visíveis incluíram: `Eleição despolitizada pode definir reformas e o futuro do Brasil` (3:16, começa em 23:44, 2 momentos sugeridos); `Voltar às eleições depende do projeto político, não de uma pessoa` (1:19, começa em 21:32, 2); `Missão aposta nas redes para romper o roteiro eleitoral de 2026` (7:59, começa em 1:45:43, 3); `Propostas concretas e transparência contra o discurso vazio na política` (3:10, começa em 16:10, 3); e vários outros com a mesma estrutura.

O produto separa claramente quatro camadas que interessam ao Furia Clips: `block`/trecho candidato, `thesis`/título editorial, `context_summary`/resumo, `moment_reason`/justificativa e `suggested_moments`/alternativas temporais. A existência de tags e de um timestamp inicial sugere que a busca não depende apenas de palavras-chave, mas de indexação semântica e contexto. O Furia Clips deve adaptar essa arquitetura como dados locais explicáveis, sem copiar a fórmula privada nem tratar “Momento forte” como verdade automática.

## Ranking e fontes de alcance

A página [Ranking](https://criadores.missao.org.br/ranking) oferece três leituras: `Visualizações` (“alcance dos vídeos”), `Vídeos do dia` (“maior alcance hoje”) e `Nível geral` (“XP compartilhado”). Os filtros observáveis são período (`Hoje`, `Esta semana`, `Este mês`, `Desde o começo`), plataforma (`Todas`, `Instagram`, `Facebook`, `YouTube`, `TikTok`) e região (`Brasil`, `Estado`, `Minha cidade`), com ação de atualizar. A tabela mostra posição, criador e alcance, e o próprio layout diferencia Brasil inteiro, leitura recente e consolidação de posições.

Na rodada, o ranking exibiu a regra textual `200 novas views aceitas = 1 XP` e uma lista ordenada de criadores com alcance; a regra foi tratada somente como observação do produto, não como fórmula a ser copiada para o score do Furia Clips. A adaptação segura é manter `views`, `age_hours`, `view_velocity`, `ranking_position`, `platform`, `region` e `collection_state` como métricas pós-publicação separadas do score editorial pré-publicação.

A página [Contas](https://criadores.missao.org.br/conexoes) informa que o acompanhamento começa no instante da confirmação e que somente Shorts, Reels e TikToks publicados depois disso entram em views, ranking e XP. Ela limita a conexão a até duas contas por plataforma. Para Instagram profissional, declara que a autorização é de Perfil e mídia e que as views dos Reels vêm de dados públicos; para Facebook e YouTube descreve confirmação por código temporário; para TikTok descreve confirmação do perfil. A conta YouTube `Fúria Da Nação` aparece acompanhada desde 3 de agosto de 2026 às 15:01. O aprendizado aplicável é a importância de uma **janela de observação explícita** e de não misturar conteúdo anterior à conexão com dados posteriores.

## Perfil e gamificação social

A página [Perfil](https://criadores.missao.org.br/perfil) exibiu `0` views acompanhadas, `Nível 0`, `0 XP no Core`, ranking geral `#25259` e ranking all-time por views `—`. Também exibiu a conta pública `Fúria Da Nação` e controles de privacidade para perfil público, estado e cidade. O produto informa que ocultar o perfil não apaga views, XP ou conquistas já registradas. Para o Furia Clips, isso reforça separar **dados de desempenho**, **visibilidade** e **estado de treinamento**; uma preferência de privacidade não deve apagar feedback editorial.

A página [Convites](https://criadores.missao.org.br/convites) é uma área de crescimento da rede, não de qualidade de conteúdo. Ela pede um código de seis letras ou números, informa que a equipe analisa o pedido e explicita que cada entrada é registrada no servidor, que o código não cria outra identidade nem outro saldo de XP. Não foi feita nenhuma solicitação. Nenhum elemento de convite será incorporado ao ranking editorial do Furia Clips.

## Meus vídeos e ficha de bloco

A página [Meus vídeos](https://criadores.missao.org.br/videos) informa que acompanha Shorts, Reels e TikToks, mostra views aceitas e XP, aplica filtros por plataforma, status (`Todos`, `Contabilizando`, `Processando`, `Não elegível`, `Excluído`) e conta, e repete a regra `200 novas views aceitas = 1 XP`. Nesta conta, mostrou `0 vídeos nesta página`, porque a única conta YouTube confirmada tinha acompanhamento iniciado em 3 de agosto de 2026 e não havia publicações curtas posteriores elegíveis. O site explica que não conta a mesma visualização duas vezes e que só aparecem vídeos publicados após a confirmação.

A ficha [Bloco do Garimpo — Eleição despolitizada](https://criadores.missao.org.br/garimpo/blocos/c676c351-f492-4b48-b5e7-64da20fc49ba) é a referência mais útil para o produto. Ela contém título/tese, resumo, fonte, data, duração do bloco, botão para lista, vídeo de origem no YouTube, download MP4, uma lista de “momentos selecionados para navegar”, um painel de “momentos fortes” e “mais potencial neste vídeo”. Cada momento forte possui título, categoria, duração, timestamp inicial e quantidade de momentos sugeridos. A ficha também exibe transcrição timestampada com links que levam ao ponto correspondente do vídeo e permite copiar transcrição e pauta.

No exemplo, o bloco selecionado tinha 3:16 e começava em 23:44. O texto do resumo apresentava a tese e seus subtemas; os momentos fortes incluíam trechos sobre segurança pública, reforma fiscal e a eleição despolitizada. A transcrição apresentava ruídos reais de reconhecimento (“republicanação”, repetições, interjeições e palavras truncadas), mas mantinha timestamps suficientes para revisão humana. A adaptação segura é o Furia Clips ter um **dossiê de candidato** com tese, resumo, subtemas, timestamp, segmentos de transcrição, alternativas temporais e ações de copiar/abrir/revisar, sem assumir que a legenda está perfeita.
