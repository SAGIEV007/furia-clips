# Pesquisa MCP + Campaign Hub para o Furia Clips — notas de investigação

## Estado da pesquisa

Documento de trabalho do ciclo iniciado após a release 6.21. Ainda não é conclusão final nem autorização para alterar o ranking. A hipótese central é avaliar se o MCP pode ampliar a utilidade do Campaign Hub para descoberta, contexto, benchmark e calibração, mantendo o job do Furia local e offline-first.

## Evidências já confirmadas

O MCP oficial é um padrão aberto para conectar aplicações de IA a sistemas externos, expondo fontes de dados, ferramentas e workflows. A documentação oficial separa o papel de conectar a aplicação de IA ao sistema externo do papel da aplicação que decide quando e como usar os dados. Fonte: https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro.

O servidor `chub-api-missao` está habilitado nesta sessão e expõe 18 operações. Entre as mais relevantes estão contas, busca textual/semântica, transcrições de posts, métricas, top posts, performance por tag e conceito, SQL somente leitura, blocos QA-gated do Acervo, transcrição do Acervo, pauta interna, busca de longform do YouTube e estatísticas de qualidade/frescor.

A cobertura reportada por `chub_accounts` é separada por conta e plataforma, sem mistura silenciosa. Para `@renansantosmbl`, o Chub reportou 984 vídeos no Facebook, 2.022 no Instagram, 982 no TikTok e 23.643 no X; 1.992 Reels do Instagram têm transcrição e 1.967 são pesquisáveis. Para `@renansantosreserva`, reportou 299 vídeos no Facebook e 338 no Instagram. Para `@partidomissao`, reportou 197 vídeos no Facebook e 281 no Instagram. As próprias regras do servidor determinam que comparações entre contas sejam feitas separadamente e que ausência de TikTok em Reserva/Missão não seja tratada como zero.

`chub_acervo_stats(groupBy=trustTier)` reportou 3.309 blocos e 5.486 highlights na tier allied, cobrindo 95 vídeos rotulados, além de 522 itens na fila de label. A latência mediana de rotulagem na semana foi 35,16 minutos para owner e 780,83 minutos para third_party. Isso indica que frescor e tier precisam entrar na proveniência de qualquer snapshot, não apenas no score editorial.

A busca textual `chub_search` para `crime organizado` no canal principal encontrou 309 menções. Os resultados retornam URL, plataforma, data, ratio e trecho de transcrição; portanto, mesmo quando embeddings estão indisponíveis, existe um caminho determinístico de recuperação lexical para descoberta e comparação.

A consulta semântica `chub_cohort_stats` para `crime organizado e segurança pública` falhou com `embeddings unavailable (OPENAI_API_KEY missing)`. Isso é uma limitação observada do serviço remoto naquele momento, não uma falha do Furia. A integração deve ter fallback explícito para busca textual, tags e SQL, e registrar a indisponibilidade sem transformar o resultado em falso zero.

`chub_top_posts` retornou criativos crosspost-deduplicados por `settledRatio`, preservando URLs e métricas por plataforma. Nos dez primeiros exemplos observados apareceram famílias como `revelacao-de-local`, `news-peg`, `desafio-ao-espectador` e `tese-provocativa`, mas os ratios variaram muito por plataforma; isso reforça que métrica agregada não deve virar aprovação automática nem ser comparada entre contas sem normalização.

## Limites de arquitetura já vistos no código

O contrato local de `modules/campaign_hub.py` afirma que o Furia não chama o MCP durante um job. O job carrega um snapshot autorizado fora do checkout, normaliza coleções bounded como sources, transcripts, sentences, blocks, highlights, possible_cuts, posts, metrics, entities, topics e benchmarks, e usa os dados como memória/evidência/prior fraco.

O código atual já calcula evidência de bloco por sobreposição temporal/textual e prior de família de hook, com limites conservadores. A ponte atual alimenta seeds/propostas guiadas antes do ranking, enquanto os gates de locutor/contexto/payoff continuam decidindo se algo pode ser publicável. Portanto, a especialização Chub já existe, mas ainda é predominantemente uma ponte de descoberta e evidência local, não um ciclo fechado de aprendizado com decisões humanas.

## Perguntas ainda abertas

É necessário confirmar se o MCP possui paginação/cursors suficientes para sincronização incremental confiável, se há um export sanitizado oficial que inclua todos os campos necessários para benchmark e se o servidor distingue claramente publicado, QA-gated, rejected, pending e stale. Também é necessário medir quais campos realmente predizem aprovação humana, em vez de assumir que views, ratio, hook ou density sejam causalmente úteis.

## Evidências oficiais do MCP

A documentação oficial descreve uma arquitetura host–cliente–servidor: a aplicação de IA atua como host, cria um cliente dedicado para cada servidor MCP e o servidor fornece contexto. O protocolo separa camada de dados JSON-RPC da camada de transporte/autorização. Para o Furia, isso indica que o MCP deve ser tratado como uma fronteira de aquisição/orquestração, não como uma dependência embutida no seletor de cortes.

As três primitivas de servidor são `tools` para funções executáveis, `resources` para dados contextuais endereçáveis e `prompts` para templates reutilizáveis. Isso sugere uma divisão clara: consultas Chub que buscam ou calculam dados podem continuar como tools read-only; um snapshot ou manifesto de memória editorial seria melhor modelado como recurso versionado; e um contrato de calibração Renan/MBL poderia ser um prompt/documento de referência, não lógica escondida em cada chamada.

A documentação também descreve notificações de mudança e acompanhamento de progresso como capacidades opcionais. Isso poderia, no futuro, alimentar um botão “atualizar memória” ou informar que a memória remota mudou, mas não justifica chamar o MCP a cada candidato durante um job de corte. O Furia deve sincronizar uma versão local, registrar cursor/freshness/proveniência e cortar contra uma cópia estável.

Fonte principal: https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro. Arquitetura: https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture.

## Descoberta sobre a pauta e o feedback

`chub_acervo_pauta` retornou uma pauta de até 40 candidatos por chamada. O contrato exposto é determinístico e sem reposição, com pesos declarados para `densityRank`, `selfContainedRank` e `cutPotential`; também separa `primaryCandidates` de `responseCandidates`, limita fontes repetidas, mantém categorias e expõe `highlights`, `triggerQuestion`, `possibleCuts`, `renanSpeaking`, riscos, duração e tier de confiança. Isso é uma excelente fonte de recall-first e contexto para o Furia, mas não deve ser copiado como ranking final porque o próprio contrato diz que o resultado é uma superfície interna de pauta.

A pauta declara um mecanismo de outcome learning com mínimo de 20 impressões e multiplicador limitado entre 0,8 e 1,25, sem alterar a qualidade do conteúdo. Contudo, uma consulta SQL real encontrou `0` linhas em `acervo_pauta_outcomes`, portanto esse aprendizado de outcome não está alimentando a instância neste momento. O mesmo inventário encontrou 34.579 highlights, 1.774 scores de previsão, 562 outcomes de previsão e apenas 2 rejeições QA. Esses números sugerem que há muita evidência editorial e de performance publicada, mas pouca observação explícita do funil de pauta/decisão que seria diretamente útil para treinar aprovação de cortes.

As colunas de `blocks` incluem exatamente campos relevantes para o Furia: `start_s`, `end_s`, `duration_s`, `title`, `summary`, `category`, `topics`, `renan_speaking`, `trigger_question`, `self_contained`, `needs_context`, `density_rank`, `self_contained_rank`, `possible_cuts`, `risk_flags`, `gate_warnings`, `corpus_verdict`, `corpus_keep`, `noise_regions`, `speakers_note` e temporality metadata. `block_highlights` preserva texto, motivo, versão do labeler e prompt. `sentences` preserva timestamp, turn e `speaker_change`. Essa estrutura é mais valiosa para alinhar e expandir janelas do que para somar um bônus bruto no ranking.

As tabelas `prediction_scores` e `prediction_outcomes` parecem ser sobre performance de posts já publicados, com plataforma, checkpoint, features, versão do modelo, previsão e outcome maduro. Elas podem servir como prior separado de performance por formato/plataforma, mas não devem ser confundidas com rótulo de corte aprovado.

As fontes ativas do Acervo incluem o canal de lives do Renan (`UCMLluq-qSne85Un73ToYI2w`, `format=live`, `trust=owner`, sincronização contínua), o canal de vídeos próprios, uma playlist de entrevistas e uma playlist de material variado. Isso confirma que o MCP pode localizar fontes longas e metadados, mas a busca longform semântica falhou ao desserializar a resposta nesta sessão; a rota SQL/textual permanece alternativa verificável.

## Segurança e operação remota

A documentação oficial de segurança do MCP destaca riscos específicos de proxies OAuth, token passthrough, SSRF, sequestro de handles e comprometimento de servidores locais. Para este projeto, a consequência prática é não colocar token do Chub no frontend, não aceitar URL arbitrária para consulta, não repassar credenciais do usuário a ferramentas e não permitir que uma resposta do servidor altere diretamente o ranking ou publique conteúdo.

A documentação de conexão remota recomenda verificar a autenticidade do servidor, revisar escopos e permissões, selecionar explicitamente quais tools ficam habilitadas e tratar o servidor remoto como fonte externa. O desenho adequado para o Furia é um sincronizador/adapter com allowlist de operações read-only, timeout, retry limitado, cache local atômico, manifesto com hash/freshness e fallback para a última memória válida. O processo de corte deve consumir a memória local imutável daquele job.

Isso também responde à ideia de um botão “atualizar dados do Chub”: ele é viável e útil, mas deve ser uma operação separada do processamento. O botão pode buscar apenas as coleções permitidas, validar e instalar uma nova versão, mostrar o que mudou e só então liberar futuros jobs para usá-la. Não deve abrir conexão remota a cada candidato nem bloquear uma live por indisponibilidade do MCP.

Fonte: https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices. Conexão remota: https://modelcontextprotocol.io/docs/2026-07-28/develop/connect-remote-servers.

## Resources do MCP e desenho de memória

A especificação mais recente trata resources como contexto orientado pela aplicação, identificado por URI. A listagem e leitura suportam paginação e cache; o servidor pode informar TTL e escopo de cache. Há notificações de alteração da lista e atualizações de recursos específicos por assinatura, mas essas capacidades são opcionais.

A aplicação disso no Furia é direta: o Chub pode ser consultado como uma fonte versionada de recursos editoriais, mas o Furia deve materializar localmente um `campaign_hub_memory` com URI lógica, versão, hash, `last_sync_at`, TTL/freshness, conta, plataforma, tier e coleções selecionadas. O job usa a versão congelada; um aviso de atualização apenas torna a memória elegível para novo sync. Não há motivo para carregar transcrições completas ou conteúdo binário inteiro como contexto automático: o recurso deve entregar metadados, intervalos, highlights, frases limitadas e proveniência, com busca/paginação sob demanda.

Fonte: https://modelcontextprotocol.io/specification/2026-07-28/server/resources.

## Recuperação contextual sob demanda

`chub_acervo_transcript` foi testado com uma live real (`VLGrdyM_A7s`) e uma janela de 98–140 segundos. O retorno trouxe a fonte, duração total, trust tier owner, `sentenceTable` com 2.031 frases, `transcriptSource`, `tokenizerVersion`, qualidade automática, paginação e 11 frases temporizadas. O servidor também avisa explicitamente que `turn` e `speakerChange` não provam identidade e que captions exigem conferência no áudio, com `audioCheckRanges` para tokens de risco.

Esse contrato permite uma integração muito mais inteligente: quando um seed Chub aponta para um bloco, o Furia pode recuperar apenas a janela anterior/posterior necessária para resolver setup, anáfora, pergunta, tese e payoff, preservando a transcrição local como fonte de corte. Assim, o MCP funciona como índice/consultor de contexto e não como substituto cego da transcrição usada para renderização.
