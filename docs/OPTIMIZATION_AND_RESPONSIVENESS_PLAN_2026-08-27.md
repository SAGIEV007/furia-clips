# Furia Studio — plano final de otimização, responsividade e confiabilidade

**Data:** 27 de agosto de 2026

**Branch:** `furia-studio-f1-integration`
**Status:** implementado e validado em sandbox Linux; validação final na máquina Windows do editor ainda é necessária.

## 1. Decisão de produto

O Furia Studio permanece uma única aplicação local para Windows: um processo, uma porta, uma aba e um frontend ativo. O **Furia 1 é o único motor canônico** para transcrição editorial, formação do pool, ranking, gates de contexto e decisão técnica. O visual retro inspirado em Poolsuite organiza a experiência, mas não substitui legibilidade, acessibilidade ou feedback operacional.

O fluxo oficial é importar a fonte, preservá-la no workspace, gerar ou anexar uma transcrição timestampada, formar e ordenar candidatos, revisar o contexto, aprovar/rejeitar humanamente e exportar o corte vertical. Headline, SEO e memória de campanha são auxiliares explicáveis; não prometem viralidade nem aprovam cortes automaticamente.

> **Regra editorial:** uma pergunta isolada, uma interrupção, um break de transmissão, o começo no meio do raciocínio ou o fim antes do payoff não pode se tornar um corte aprovado. Se um corte anterior termina em pergunta, a oportunidade posterior continua disponível para avaliação independente na linha do tempo.

## 2. Resultado da auditoria

O log de uso revelou dois riscos materiais: retries 503/429 do Gemini que consumiam muitos minutos e um render FFmpeg que permanecia apenas em heartbeat por tempo excessivo. A implementação final substitui a mensagem ambígua de “fila protegida” por monitoramento, prazo, cancelamento, erro de etapa e recuperação. A análise também confirmou que o Chub não era executado por clip e não foi a causa do bloqueio observado.

A rodada de validação terminou com **872 testes aprovados, 27 ignorados e 2 xfails**, além de `py_compile`, `node --check static/app.js` e `git diff --check` aprovados. A UI foi carregada no shell ativo e inspecionada em 320, 375, 768, 1024 e 1440 pixels; Ajustes permaneceu dentro do mesmo Studio e `Escape` fechou o modal sem perder a Mesa.

O endereço público de Garimpo redirecionou para login. A auditoria só pôde verificar o HTML público da autenticação e sua chamada para ação. Não houve login, bypass, captcha, scraping de conteúdo protegido ou conclusão sobre a área interna.

## 3. Arquitetura operacional consolidada

| Etapa | Fonte da verdade | Garantia implementada | Fallback aceitável |
|---|---|---|---|
| Importação | arquivo local e workspace | projeto persistido e fonte original preservada | erro acionável, sem projeto fantasma |
| Transcrição | Whisper/faster-whisper ou arquivo escolhido pelo editor | chunks de 300 s com timestamps absolutos e cancelamento | fallback explicitamente nomeado |
| Pré-análise | FFmpeg/ffprobe e sinais locais | energia PCM em streaming, turnos, perguntas e fronteiras | fonte sem áudio segue com perfil vazio |
| Seleção | Furia 1 | pool, gates editoriais, score explicável e diversidade temporal | zero resultados diagnosticado |
| Evidência opcional | Gemini ou snapshot Chub | opt-in, orçamento finito e sem autoridade sobre o score | caminho local continua disponível |
| Decisão | editor | Aprovar, Rejeitar ou manter em revisão | motivo opcional persistido |
| Exportação | VideoCutter + captions | somente aprovado exporta; `export_path` persistido | cleanup de saída parcial, timeout e cancelamento |

## 4. Implementações P0 — confiabilidade

A primeira prioridade foi impedir que uma operação longa pareça infinita ou deixe o processo em estado indefinido. O runner compartilhado do FFmpeg faz polling, heartbeat, cancelamento cooperativo, coleta segura de `stderr` em arquivo temporário e cleanup. O teto padrão de render passou a ser derivado da duração, com **mínimo de 90 s e máximo de 300 s**; variáveis de ambiente também são limitadas para não reintroduzir o teto histórico de quinze minutos.

A seleção textual do Gemini agora trabalha em lotes de até oito blocos, com timeout de 60 s por requisição, retries curtos e teto global de **180 s**. Quota 429 interrompe os lotes condenados e permite fallback local; falhas 503/timeout não descartam resultados parciais. A análise multimodal é separada: o orçamento total fica entre **180 s e 600 s**, cobrindo sondagem, proxy FFmpeg, handshake/upload, ativação do arquivo e geração de conteúdo. No vídeo crítico de aproximadamente 44 minutos, a compactação do proxy levou cerca de 91 s, o upload cerca de 1,2 s e a espera/processamento remoto cerca de 171 s adicionais; a resposta ainda chegou em JSON truncado. O gargalo é preparar e processar uma fonte longa, não enviar o arquivo original pela rede. O deadline não pode ser ultrapassado por piso artificial de espera ou chamada adicional.

O cliente agora diferencia uma falha transitória de polling de um erro definitivo. Depois de seis falhas ou 120 s desconectado, mantém o `currentJobId`, marca o job como desacoplado, bloqueia nova análise/transcrição e oferece **Retomar acompanhamento** no Console. Na recarga, um job `queued`, `running` ou `cancel_requested` é reidratado do servidor; a UI não inicia automaticamente uma segunda execução.

## 5. Implementações P1 — desempenho percebido

A transcrição longa usa janelas Whisper independentes e desloca os timestamps de volta à linha do tempo original. A análise de energia não materializa um WAV inteiro: lê PCM em blocos menores, verifica cancelamento e suporta fontes sem áudio. `ffprobe`, extração legada, proxy multimodal, captions e render têm limites finitos.

O frontend passou a usar `AbortController` para requests, timeout por operação, mensagens contextuais, retry/backoff para a fila, locks idempotentes por ação de clip/Chub/transcript e `requestAnimationFrame` para coalescer o movimento da galáxia. Upload de vídeo recebeu timeout de cliente maior, enquanto ações curtas permanecem limitadas. O SEO anuncia o estado de geração e preserva a legenda como evidência visível.

| Operação | Limite/estratégia | Resultado esperado na UI |
|---|---|---|
| Upload local | até 15 min no cliente | não repetir upload silenciosamente se a resposta atrasar |
| Polling de job | requests de 15 s; backoff; 6 falhas ou 120 s | job desacoplado e retomável |
| Seleção Gemini | 60 s por chamada; 180 s global | resultados parciais + Furia 1 local |
| Proxy multimodal | 90–600 s proporcional à fonte | cancelamento e remoção do proxy |
| Gemini multimodal | 180–600 s total | evidência auxiliar ou fallback local |
| Render/captions | 90–300 s | erro explícito e saída parcial removida |

A recomendação operacional para fontes longas é manter **NLP local/Furia 1** como caminho padrão e oferecer a revisão audiovisual Gemini como ação explícita, cancelável e limitada. O multimodal não deve ser iniciado automaticamente junto com cada renderização quando a transcrição manual já está disponível: na medição crítica, ele adicionou vários minutos e quase não alterou o conjunto final de cortes.

## 6. Implementações P1 — UX, responsividade e acessibilidade

A experiência preserva janelas físicas, textura, cores coral/amarelo/ciano e o mapa central, mas aplica reflow mobile-first. O breakpoint é orientado pelo conteúdo: em telas estreitas, os painéis viram fluxo vertical; em telas maiores, a composição sobreposta retorna. A implementação segue o princípio de layout responsivo fluido recomendado pela [orientação de Responsive Design da MDN][2].

| Viewport | Composição validada | Critério de aceite |
|---|---|---|
| 320 × 900 | uma coluna; Source Desk antes do Signal Board; dock fixo | sem overflow horizontal; CTA e cinco destinos legíveis |
| 375 × 900 | uma coluna com mais respiro | título, importação e início do segundo painel acessíveis |
| 768 × 1000 | fluxo vertical de painéis | nenhum cartão espremido em duas colunas |
| 1024 × 1000 | janelas retro sobrepostas | sobreposição não bloqueia ação crítica |
| 1440 × 1100 | composição completa e espaço negativo | hierarquia visual e CTA principal evidentes |

O modal de Ajustes permanece dentro da aplicação e explica Whisper, Gemini e Chub antes do uso. O Chub aparece como **opcional, ignorável, somente leitura e não preditivo**. Inputs de arquivo ocultos receberam nomes acessíveis; diálogos têm `role="dialog"`, `aria-modal` e título associado; o Console e o resultado SEO usam regiões de atualização; foco visível e `Escape` foram verificados.

A referência de acessibilidade é WCAG 2.2: contraste mínimo de 4,5:1 para texto normal, foco visível, teclado, reflow e alvos de toque devem ser tratados como critérios de aceite, não como acabamento visual [1]. A prioridade de reduzir tarefas longas no thread principal e responder rapidamente a clique/toque/teclado segue a métrica INP do web.dev [3].

| Área | Checklist final |
|---|---|
| Teclado | Tab alcança ações; Enter/Space ativam controles; `Escape` fecha Import e Ajustes |
| Foco | `:focus-visible` perceptível; nenhum foco fica preso em elemento oculto |
| Nomes | labels/`aria-label` em inputs e botões; títulos associados aos diálogos |
| Status | progresso, warning, erro, cancelamento e retomada aparecem no Console |
| Alvos | ações móveis têm área confortável e espaçamento suficiente |
| Movimento | decoração não bloqueia clique; próxima rodada deve adicionar `prefers-reduced-motion` explícito |

## 7. Gemini, Chub e segurança

Gemini só é usado quando configurado pelo editor. A chave não aparece em código, logs, documentação, URL ou resposta de settings; o diagnóstico agora envia a credencial somente no header `x-goog-api-key`, nunca em query string. Qualquer chave colada em conversa ou log deve ser **revogada e recriada** antes de uso continuado.

O snapshot Chub é uma memória editorial auxiliar, instalada localmente e read-only. Ele pode fornecer referências históricas de hooks, temas e nomes para explicação e desempate editorial limitado, mas não altera o score técnico, não é previsão e não é consultado por clip. Propostas temporais guiadas pelo Acervo ficam desativadas por padrão e só entram no pool mediante `campaign_hub_guided_selection` explicitamente ativado pelo editor. Garimpo protegido não deve ser contornado; uma futura integração precisa de autorização explícita e escopo read-only.

## 8. Roadmap P2–P3

A base P0/P1 está pronta para publicação. As etapas seguintes devem aprofundar a qualidade sem reintroduzir complexidade obrigatória.

| Prioridade | Próxima melhoria | Métrica de conclusão |
|---|---|---|
| P2 | aprendizado editorial por decisões humanas | agregados suficientes, motivos persistidos e nenhuma aprovação automática |
| P2 | diagnóstico exportável sanitizado | não contém mídia, transcript, banco, cache, paths privados ou credenciais |
| P2 | cobertura visual de estados internos | vídeo, transcript, zero resultados, shortlist, revisão, Chub, job e export |
| P3 | matriz de instalação Windows | bootstrap, permissões, FFmpeg, antivírus, Opera e `%LOCALAPPDATA%` verificados na máquina alvo |
| P3 | `prefers-reduced-motion` e foco restaurado em modais | navegação acessível sem animação obrigatória |

## 9. Gate e limitações honestas

O gate executado nesta rodada foi:

| Verificação | Resultado |
|---|---|
| `PYTHONPATH=. pytest -q` | **872 passed, 27 skipped, 2 xfailed** |
| `python3 -m py_compile` nos entrypoints e módulos runtime | **aprovado** |
| `node --check static/app.js` | **aprovado** |
| `git diff --check` | **aprovado** |
| inspeção das linhas adicionadas | sem chave, token, mídia, transcript, banco, cache ou log privado |
| QA visual 320/375/768/1024/1440 | carregamento e reflow observados; estado vazio sem overflow crítico |
| Ajustes e `Escape` | mesmo Studio, sem segunda aba/janela |
| Windows | **não declarado**: requer máquina Windows real |

A sandbox Linux valida código, contratos, servidor, HTML/CSS/JS e renderizações headless. Ela não pode garantir performance em CPU/GPU Windows, interferência de antivírus, permissões de `%LOCALAPPDATA%`, associação de Opera ou comportamento do FFmpeg no hardware do editor. Essa é a única etapa relevante que permanece fora do alcance desta rodada.

## References

[1]: https://www.w3.org/TR/WCAG22/ "Web Content Accessibility Guidelines (WCAG) 2.2 — W3C"
[2]: https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/CSS_layout/Responsive_Design "Responsive web design — MDN"
[3]: https://web.dev/articles/inp "Interaction to Next Paint — web.dev"
