# Furia Clips — gates de contexto e feedback estruturado

## Objetivo

Esta versão transforma a revisão editorial em uma fonte de aprendizado mais útil sem fingir que poucos clipes constituem um modelo estatístico robusto. A seleção continua priorizando Gemini quando configurado, com Ollama e NLP como alternativas, mas todos os caminhos agora expõem o mesmo contrato mínimo de qualidade contextual.

## Contrato contextual por clip

Cada candidato pode carregar flags explicáveis: `starts_mid_sentence`, `question_detected`, `question_answer_complete`, `evidence_present`, `payoff_complete`, `context_complete` e `qa_bridge`. A seleção NLP e a resposta dos modelos recebem esses sinais a partir da transcrição. Quando um bloco começa com uma continuação e o bloco anterior está próximo, dentro do teto técnico, o seletor tenta recuperar o contexto anterior em vez de publicar uma abertura abrupta.

O ranqueador adiciona o fator `context_quality`. Ele aumenta o score de candidatos autossuficientes, com pergunta–resposta, evidência e payoff; reduz candidatos que começam no meio da frase, deixam uma pergunta sem resposta ou terminam como cliffhanger. A duração continua sendo preferência, não limite absoluto: um corte mais longo pode permanecer elegível quando a estrutura editorial é forte.

> O score contextual é um gate de revisão e uma explicação editorial, não uma afirmação de que o sistema compreendeu perfeitamente o vídeo ou a veracidade de uma alegação.

## Feedback estruturado

A tabela `clip_feedback` agora preserva `reason_code` e `quality_tags`, com migração automática para bancos existentes. O editor ainda pode aprovar, rejeitar ou marcar para revisão em um clique, mas cada card apresenta um seletor visual opcional com motivos como `missing_context`, `starts_late`, `no_payoff`, `wrong_speaker`, `bad_framing`, `audio_overlap`, `duplicate`, `too_long`, `excellent_context` e `fact_review`.

A calibração exclui estados pendentes e de revisão contextual. Ela continua elegível somente após amostra mínima equilibrada e mantém influência limitada sobre o score. Além do sinal de duração, o HUD passa a exibir o motivo de rejeição mais frequente quando existe evidência suficiente. As decisões ficam fora do checkout em `~/FuriaClipsData` por meio do banco e dos backups editoriais.

## Revisão de contexto

O fluxo completo devolve `factors`, `confidence`, `editorial_score_version`, flags contextuais e os segmentos timestampados do próprio intervalo. Assim, o botão **Revisar contexto** pode mostrar o trecho e a transcrição completa mesmo quando o estado global do navegador perdeu a transcrição manual.

## Validação desta versão

A suíte completa passou com **189 testes**. Também foram executados `py_compile`, `node --check` e `git diff --check` sem erros. Foram adicionados testes para a recuperação de contexto, os gates contextuais e a persistência de motivos/tags de feedback.

## Limitações conscientes

A análise dos Reels públicos feita pelo navegador continua sendo observacional e, na sessão atual, o áudio dos Reels ficou mutado. Portanto, padrões de música, timbre, entonação e sobreposição sonora devem ser aprendidos a partir de arquivos/transcrições processados no Furia, não inferidos da coleta visual. Métricas públicas de alcance e comentários são priors de pesquisa, não rótulos causais de qualidade.

## Pacote editorial portátil

O repositório agora inclui `data/editorial_priors.json`, gerado por `scripts/build_sanitized_priors.py`. Esse arquivo contém somente estatísticas agregadas de hooks, conta/plataforma, padrões editoriais e gates de qualidade. Ele não inclui mídia, transcrições, IDs de posts, URLs, queries ou textos de publicações.

O adaptador `campaign_hub.load_snapshot()` continua priorizando o snapshot detalhado do usuário em `~/FuriaClipsData/campaign_hub/profile.json`. Quando esse arquivo não existe, o pacote agregado versionado é carregado como fallback. Os priors agregados são convertidos em observações limitadas apenas para reutilizar a lógica conservadora já existente; o impacto permanece limitado e nunca substitui contexto, completude ou composição.

Esse desenho permite baixar o código em outro notebook e começar com um comportamento editorial coerente. Para transportar o aprendizado completo — decisões individuais, transcrições arquivadas e histórico — deve-se restaurar o backup editorial fora do GitHub. O pacote versionado é a camada compartilhável; o backup local é a camada completa e privada.

## Dataset editorial dos Reels

As observações visuais individuais foram formalizadas em `~/FuriaClipsData/analyses/instagram-editorial-dataset-v1-2026-08-15.json`. O schema separa conta, alcance público observado, família narrativa, hook, contexto necessário, payoff, layout, política de composição, evidência, confiança e estado do áudio. O arquivo não contém vídeo nem transcrição bruta.

O módulo `modules/instagram_editorial_priors.py` agrega esse dataset por família e layout. O ranqueador passa a expor `instagram_pattern_prior` e seus metadados de amostra no resultado e no HUD. Esse prior fica limitado entre 42 e 58, funcionando como desempate editorial, enquanto contexto, completude, pergunta–resposta, evidência, enquadramento e feedback humano permanecem dominantes.

Como os Reels foram observados com o navegador mutado, o campo `audio` permanece `pending`. Não há inferência de música, timbre ou sobreposição sonora nesse dataset. Esses campos só devem ser preenchidos quando o arquivo/transcrição for processado pelo pipeline multimodal ou local do Furia.
