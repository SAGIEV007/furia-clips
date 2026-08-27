# Furia Studio: processamento e QA do frontend — 27 de agosto de 2026

Esta rodada consolidou o **Furia Studio local baseado exclusivamente no motor canônico Furia 1**. O programa continua sendo uma única aplicação para Windows, com um processo local, uma porta e uma aba do navegador. A interface Poolsuite permanece a camada visual; o fluxo editorial continua sendo uma sugestão explicável para revisão humana, não uma promessa de viralidade nem uma aprovação automática.

## Causa do processamento aparentemente travado

O travamento observado depois de `Cortando clip 1/31` foi reproduzido em uma fonte curta durante a detecção de cenas. A etapa usava uma chamada bloqueante do FFmpeg: enquanto esse processo não retornasse, o botão de cancelamento só conseguia registrar `Cancelando…`, sem interromper imediatamente a operação. A demora era agravada pelo fato de a detecção visual ser um enriquecimento, não uma condição necessária para formar candidatos.

O detector agora usa um processo monitorado por polling, verifica o cancelamento cooperativo durante a execução e encerra o processo filho quando o usuário cancela. A análise de cenas tem um limite proporcional à duração da fonte, registra heartbeat no Console e, quando expira ou falha, retorna uma linha de base segura para que o Furia 1 continue com transcrição e sinais locais. A renderização de cada clip também tem limite finito e heartbeat. Se um clip individual falhar ou exceder o limite, ele é registrado como rejeitado e a fila continua com os demais clips.

| Situação | Comportamento do Studio |
|---|---|
| FFmpeg de cenas demora | Console mostra limite e heartbeat; ao expirar, a seleção prossegue sem fronteiras visuais |
| Usuário cancela durante cenas | O processo filho é encerrado e o job termina como cancelado |
| Um clip falha na renderização | O arquivo inválido é removido, o motivo fica no diagnóstico e a fila tenta os próximos |
| Fonte sem faixa de áudio | O perfil de energia fica vazio com explicação; transcrição, seleção e renderização continuam |
| Whisper não encontra CUDA no Windows | O motor usa o fallback CPU disponível, sem tratar a ausência de `cublas64_12.dll` como erro fatal |

## Fluxo visual auditado

O fluxo recomendado está explícito na Mesa. O operador importa um vídeo local, escolhe **Usar transcript pronto** para SRT/VTT/TXT ou **Executar Whisper local**, acompanha cada etapa no Console e então usa **Encontrar cortes — Furia 1**. Os candidatos aparecem em Cortes; cada cartão pode ser aberto em Revisão, reproduzido, ajustado no intervalo, aprovado ou rejeitado com motivo. Depois da aprovação, **Exportar 9:16** renderiza o arquivo na pasta local e o cartão passa a indicar **Exportado na pasta local**; não há promessa de download automático pelo navegador.

A interface separa agora as ações ocupadas. Durante uma transcrição, o botão informa `Whisper em execução…`; durante a análise, informa `Análise em execução…`. Ações concorrentes ficam desabilitadas enquanto o job está ativo. Console, cancelamento, limpeza do log, navegação Mesa/Biblioteca/Projeto/Cortes/Revisão/Ajustes, importação de SRT, reprodução, SEO local, headline, aprovação e exportação foram exercitados na QA local.

| Ação | O que faz | Resultado esperado |
|---|---|---|
| Importar vídeo | Copia ou registra a fonte local na sessão | A fonte continua disponível ao navegar entre telas |
| Usar transcript pronto | Importa SRT, VTT ou TXT já existente | Segmentos com timestamps aparecem sem executar Whisper |
| Executar Whisper local | Produz a transcrição canônica no computador | O Console informa o motor e o fallback utilizado |
| Encontrar cortes — Furia 1 | Forma, filtra e ranqueia candidatos editoriais | O resultado aparece progressivamente e fica salvo no projeto |
| Revisar cortes | Abre o player, a legenda, os motivos e os controles de intervalo | A decisão continua humana |
| Gerar SEO local | Sugere headline, descrição e hashtags usando a legenda | A sugestão pode ser aplicada e editada |
| Aprovar | Registra a decisão humana | Habilita a exportação do clip |
| Exportar 9:16 | Renderiza uma cópia local vertical | O cartão informa que o arquivo foi exportado na pasta local |

## Diagnóstico de zero resultados

Quando todos os candidatos são filtrados antes da renderização, o Console não deve dizer que os motivos não foram registrados. A mensagem agora combina rejeições dos gates de renderização com os diagnósticos do seletor, incluindo hard negatives e a razão geral da seleção. Assim, duplicação por mesmo fechamento, fingerprint já exportado, fonte curta, sobreposição ou necessidade de revisão técnica podem ser apresentados de modo rastreável, sem expor transcrição integral, credenciais ou caminhos privados.

Essa explicação não muda o score técnico nem transforma o diagnóstico em decisão automática. Ela apenas torna legível por que um pool de candidatos não se converteu em clips entregues e orienta a próxima revisão do editor.

## Gemini configurável e opcional

Gemini é configurado dentro de **Ajustes**, com campo de chave, modelo configurável e uma opção separada para **Interpretar vídeo com transcript manual**. A opção começa desligada. Sem uma chave válida, o Studio informa a indisponibilidade e continua com os sinais locais; sem a opção explícita, um transcript manual ou persistido não dispara um segundo envio audiovisual.

A origem persistida `manual_confirmed` agora recebe a mesma política de `manual`: somente o checkbox `gemini_manual_video_analysis` permite a segunda análise audiovisual. A correção vale tanto para o caminho **Encontrar cortes — Furia 1** quanto para **Executar Tudo**. O resultado multimodal é anexado como evidência auxiliar limitada, com identidade da fonte, momentos coincidentes e flags de revisão; ele não altera score, não remove silenciosamente candidatos e nunca aprova um clip.

| Configuração | Efeito |
|---|---|
| Backend local/sem chave | Furia 1 usa transcript e sinais locais; nenhuma chamada online é necessária |
| Gemini configurado, checkbox desligado | Gemini pode ser usado para a rota inicial sem transcript, conforme o backend, mas não há segundo envio de uma fonte já transcrita manualmente |
| Gemini configurado, checkbox ligado | Uma segunda leitura audiovisual pode enriquecer a revisão do transcript manual ou `manual_confirmed` |
| Modelo vazio ou inválido | O Studio usa um identificador seguro padrão compatível |
| Falha, limite ou indisponibilidade online | O Console explica o fallback e a seleção local continua |

Chaves fornecidas para QA nunca devem ser incluídas em código, logs, documentos, diagnósticos ou commits. A chave temporária usada nesta validação foi mantida apenas na instância de teste e deve ser revogada; uma nova chave deve ser criada para uso real.

## Chub e snapshot

O Chub é uma memória opcional, somente leitura e baseada em um snapshot autorizado. Ele pode fornecer referências históricas e blocos previamente revisados quando o operador já possui esse JSON, mas **não é necessário para o fluxo normal**. O Furia não depende de Chub para importar vídeo, reconhecer fontes fora do Chub, transcrever, encontrar cortes, revisar, aprovar ou exportar.

O Console deixou de exibir comandos de linha de comando como instrução no caminho normal. Quando não há snapshot ou a fonte não tem identificador reconhecível, a mensagem informa que o Acervo opcional não foi aplicado e que a edição seguirá com a fonte e os sinais locais. Nenhuma consulta ao conector é feita por clip, nenhuma autenticação protegida é contornada e o snapshot não determina o score técnico.

| Se o operador... | Deve fazer... |
|---|---|
| Não conhece o Chub | Ignorar o bloco e seguir com vídeo → transcript/Whisper → cortes → revisão → aprovação → exportação |
| Já possui JSON autorizado | Importá-lo em Ajustes para obter contexto histórico limitado |
| Tem vídeo fora do Chub | Processá-lo normalmente; o Furia 1 não exige ID do YouTube |
| Precisa de blocos do Acervo | Confirmar manualmente que o snapshot corresponde à mesma fonte antes de usar seus intervalos |

## Validação executada

Foram aprovados testes direcionados para entrega progressiva corte a corte, VideoCutter, cancelamento, análise de áudio, energia, validação de mídia, ajustes de clip, auditoria editorial local, rotas do Studio, política Gemini e revisão multimodal. Também foram executados `py_compile` dos módulos alterados, verificação de sintaxe do JavaScript e `git diff --check` nos checkpoints desta rodada.

A QA funcional percorreu importação de vídeo, persistência ao navegar pelas áreas, importação de SRT, análise NLP, Console, filtro e ordenação da Biblioteca, Whisper local com fallback para CPU, fonte sem áudio, revisão, reprodução, SEO, headline, aprovação e exportação local. A conectividade Gemini foi confirmada em uma execução curta e o pipeline terminou em 100%; os candidatos do fixture foram descartados por duplicação e fonte curta, não por erro de conexão ou parse do Gemini.

| Gate | Resultado registrado nesta rodada |
|---|---|
| Testes automatizados | Gate completo: 856 aprovados, 27 ignorados e 2 xfail; o checkpoint direcionado mais recente teve 50 aprovados |
| Cancelamento de cenas | Processo filho encerrado por teste determinístico |
| Fonte silenciosa | Perfil vazio explicado e clip renderizado na QA |
| Gemini | Modelo conectado, seleção textual concluída e flag manual persistida |
| Frontend | Dispatcher estrutural sem ações visuais sem handler; navegação e ações principais exercitadas |
| Exportação | Aprovação permanece pendente de exportação; após o job explícito, o arquivo vertical e `export_path` ficam registrados localmente |
| Privacidade | Nenhuma mídia, legenda, transcript, banco, cache, log de QA ou chave deve ser versionado |

## Limite de validação no Windows

A aplicação está preparada para tratar a ausência de CUDA com fallback CPU, mas a confirmação final do launcher, permissões de pasta, associação de FFmpeg, disponibilidade do Whisper e comportamento do navegador precisa ser feita na máquina Windows do usuário. O job que já estava em execução antes deste patch não pode ser corrigido em memória: é necessário substituir a pasta pelo pacote atualizado, executar `run.bat` e iniciar um novo job.

O roteiro operacional mínimo é: importar o vídeo; usar um SRT ou executar Whisper; clicar em **Encontrar cortes — Furia 1**; acompanhar o Console; revisar e ajustar os clips; aprovar os momentos escolhidos; e exportar para a pasta local. O snapshot Chub não é requisito, e Gemini só deve ser habilitado em Ajustes quando a interpretação audiovisual complementar for desejada.
