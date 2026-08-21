# Backlog de ideias — Furia Clips

> Este documento contém ideias e desejos de produto. **Nenhum item deve ser implementado apenas por estar listado aqui.** A implementação só começa quando o usuário solicitar explicitamente um item ou uma rodada de itens.

## Regra de execução

As ideias abaixo são referência para planejamento futuro. Ao implementar qualquer item, preservar o código existente, escolher uma hipótese principal, criar testes, comparar antes/depois, validar o resultado e registrar a alteração em uma rodada própria. Itens não solicitados permanecem apenas como backlog.

## Ideia registrada pelo usuário

### I-001 — Estúdio de revisão pós-renderização

Permitir que o usuário envie um corte pronto junto com a transcrição correspondente e abra uma área de revisão dentro do Furia Clips. Essa área deve permitir corrigir legendas erradas, ajustar timestamps, revisar palavras, editar ou substituir headlines desalinhadas com a fala, conferir a composição 1:1 e exportar uma nova versão sem destruir o arquivo original.

O fluxo ideal inclui vídeo, SRT, waveform/timeline, edição por bloco e por palavra, preview sincronizado, histórico de versões, comparação antes/depois, validação de safe area, checagem de sobreposição e exportação corrigida. A headline deve ser avaliada separadamente quanto a fidelidade, contexto, legibilidade e compatibilidade com o formato 1:1.

**Status:** ideia; não implementar sem solicitação explícita.

## Ideias adicionais sugeridas

### I-002 — Editor visual de legendas com sincronização

Permitir editar texto diretamente sobre a timeline, arrastar início e fim de cada bloco, dividir/mesclar legendas e ajustar a legenda a uma palavra específica. O sistema deve alertar sobre sobreposição, lacunas, duração curta demais, excesso de caracteres e leitura rápida demais.

**Status:** ideia; não implementar sem solicitação explícita.

### I-003 — Correção assistida de transcrição com confirmação humana

Comparar a transcrição com o áudio, sugerir correções de nomes próprios, siglas, entidades políticas, números e palavras de baixa confiança, mas nunca aplicar automaticamente alterações sensíveis sem mostrar o original, a sugestão e o motivo.

**Status:** ideia; não implementar sem solicitação explícita.

### I-004 — Verificador de fidelidade da headline

Antes da exportação, comparar a headline com a transcrição e o contexto do corte. Detectar exagero, atribuição incorreta, afirmação não sustentada, ausência de sujeito, falta de especificidade e incompatibilidade com a fala. Oferecer alternativas por formato sem transformar alegações em fatos independentes.

**Status:** ideia; não implementar sem solicitação explícita.

### I-005 — Preview específico por formato editorial

Para o mesmo corte, mostrar previews separados de `16:9 original`, `1:1 Alfinetei` e `fake tweet`, com regras de texto, safe area, quebra de linha e enquadramento próprias. O sistema deve explicar por que um formato é recomendado ou rejeitado.

**Status:** ideia; não implementar sem solicitação explícita.

### I-006 — Comparador antes/depois

Exibir lado a lado o corte original e a versão corrigida, incluindo vídeo, legenda, headline, duração, intervalo original e alterações feitas. Permitir retornar a qualquer versão sem perder o histórico.

**Status:** ideia; não implementar sem solicitação explícita.

### I-007 — Lint audiovisual antes da publicação

Criar uma validação automática para detectar legenda cortada, texto fora da safe area, headline encoberta, rosto ou evidência visual removidos, tela preta, áudio ausente, codec inválido, proporção incorreta, duração inesperada, frames congelados e problemas de FFprobe.

**Status:** ideia; não implementar sem solicitação explícita.

### I-008 — Ajuste inteligente de enquadramento com revisão

Quando o corte for vertical ou quadrado, mostrar o enquadramento aplicado e permitir mover o foco manualmente. O sistema deve sinalizar quando o reframe ameaça cortar rosto, documento, tela, gráfico ou outra evidência necessária.

**Status:** ideia; não implementar sem solicitação explícita.

### I-009 — Biblioteca de correções aprovadas

Guardar pares de transcrição original versus corrigida, headline rejeitada versus aprovada, motivo da correção, formato e versão do processamento. Esses dados podem formar feedback editorial privado e versionado para melhorar regras futuras.

**Status:** ideia; não implementar sem solicitação explícita.

### I-010 — Pacote de diagnóstico exportável

Gerar um pacote sanitizado contendo vídeo ou hash da mídia, SRT, JSON do corte, versão, branch/revisão, eventos do job, validações, erros e decisões da revisão, sem cookies, tokens, dados pessoais ou URLs privadas.

**Status:** ideia; não implementar sem solicitação explícita.

### I-011 — Reprocessamento seletivo

Permitir corrigir apenas legendas, apenas headline, apenas enquadramento ou apenas áudio, sem repetir download, transcrição e ranking quando essas etapas não mudaram.

**Status:** ideia; não implementar sem solicitação explícita.

### I-012 — Aprovação por checklist editorial

Antes de marcar o corte como pronto, apresentar checklist para contexto completo, início natural, tese/payoff, pergunta e resposta, locutor correto, fidelidade da headline, legibilidade, safe area, enquadramento e qualidade técnica.

**Status:** ideia; não implementar sem solicitação explícita.

### I-013 — Fila de revisão e prioridades

Organizar cortes por urgência, risco, baixa confiança de transcrição, headline pendente, problema técnico e necessidade de revisão humana. A fila deve mostrar por que cada item precisa de atenção.

**Status:** ideia; não implementar sem solicitação explícita.

### I-014 — Busca de cortes e correções anteriores

Permitir localizar projetos por tema, entidade, fala, headline, conta, formato, data, estado de revisão ou motivo de rejeição, preservando a separação entre perfil principal, Reserva e Partido Missão.

**Status:** ideia; não implementar sem solicitação explícita.

### I-015 — Métricas de qualidade editorial

Acompanhar taxa de legendas corrigidas, headlines rejeitadas, cortes com começo abrupto, perguntas sem resposta, problemas de safe area, reexports e preferências humanas. Usar as métricas para priorizar correções, não para substituir avaliação editorial.

**Status:** ideia; não implementar sem solicitação explícita.

## Ordem sugerida quando o usuário pedir implementação

A ideia I-001 deve ser dividida em ciclos pequenos. A primeira entrega recomendada seria um fluxo mínimo de importação de vídeo + SRT, preview sincronizado, correção de texto por bloco, edição de headline e exportação sem destruir o original. Depois podem entrar ajuste fino de timestamps, comparação antes/depois, lint audiovisual e aprendizado a partir das correções aprovadas.

## Novo eixo de plataforma — 2026-08-21

As ideias abaixo foram consolidadas em [`PLATFORM_NORTH_2026-08-21.md`](PLATFORM_NORTH_2026-08-21.md) e permanecem propostas até serem escolhidas para um ciclo próprio. O documento completo organiza automações de cortes, transcrição canônica, Context Composer, lint audiovisual, dossiês, pesquisa recente, GDELT, fontes primárias, watchlists, briefings, fila de revisão, feedback, Telegram, WhatsApp, control plane, worker local e notificações de smartwatch.

### I-016 — Missões editoriais de ponta a ponta

Receber uma intenção em linguagem natural, transformar em plano de etapas, executar ingestão, transcrição, contexto, seleção, renderização e revisão, e devolver um pacote auditável. A missão deve ser idempotente, cancelável, versionada e limitada por permissões.

**Status:** proposta; não implementar sem escolher hipótese e critério de sucesso.

### I-017 — Dossiê de última hora com rastreabilidade

Pesquisar notícias, publicações, vídeos e imagens recentes, agrupar as fontes, separar fato, alegação, inferência e contradição, montar timeline e entregar links, créditos, horários e nível de confirmação. Nunca transformar uma única postagem em prova.

**Status:** proposta; depende de camada de pesquisa e política de fontes.

### I-018 — Monitor de pautas e watchlists

Acompanhar pessoas, eventos, locais, expressões e variações linguísticas, alertar apenas sobre mudanças relevantes e responder “o que mudou desde a última coleta?”.

**Status:** proposta; depende de serviço persistente ou agendamento apropriado.

### I-019 — Acionamento por mensageria

Permitir comandos como `/cortar`, `/pesquisar`, `/dossie`, `/status`, `/cancelar`, `/aprovar` e `/rejeitar`, com allowlist de usuários, confirmação de ações destrutivas e respostas com links e previews.

**Status:** proposta; Telegram é a prova técnica mais leve; WhatsApp exige configuração empresarial, webhook, opt-in e tokens.

### I-020 — Ponte control plane + worker local

Manter o motor de mídia no computador autorizado e usar um serviço remoto apenas para receber missões, armazenar estados, entregar alertas e sincronizar artefatos sanitizados. A mídia bruta permanece local por padrão.

**Status:** proposta; depende de autenticação, disponibilidade do computador e decisão de hospedagem.

### I-021 — Notificações de smartwatch

Entregar no relógio apenas alertas curtos e ações reversíveis, como visualizar que há cortes prontos, cancelar uma missão ou abrir a revisão no telefone. Não processar vídeo nem editar timeline no relógio.

**Status:** proposta; depende de canal móvel e notificações do telefone.

### I-022 — Kit de mídia e evidência

Para cada pauta, reunir matérias, imagens, vídeos, thumbnails, créditos, datas, OCR, origem, possível reutilização e relação com a afirmação pesquisada.

**Status:** proposta; depende de busca e armazenamento seguro.

### I-023 — Saúde editorial e aprendizado de feedback

Medir recall, aprovação, rejeição por motivo, locutor incerto, contexto insuficiente, headline rejeitada, reexportação e tempo economizado. Usar os dados para regressões e calibração, sem transformar uma preferência isolada em verdade.

**Status:** proposta; pode ser dividida em ciclos locais.

### I-024 — Reprocessamento seletivo por etapa

Reexecutar somente a etapa afetada quando mudar legenda, headline, enquadramento ou contexto, usando cache e invalidadores por versão.

**Status:** proposta; depende de identidade de artefatos e intervalo.

### I-025 — Dossiê vivo de evento

Manter um histórico de fontes, correções, contraditórios, imagens repetidas e mudanças de vocabulário para responder automaticamente o que mudou desde a última atualização.

**Status:** proposta; depende de watchlist e coleta incremental.

A implementação de qualquer item deve seguir a regra deste documento: uma hipótese principal, baseline, regressão, validação, documentação e publicação apenas se a melhoria for comprovada.
