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
