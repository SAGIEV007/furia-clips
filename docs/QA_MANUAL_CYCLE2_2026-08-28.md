# Observações sanitizadas — QA manual ciclo 2

A tela inicial da branch experimental carregou em uma única instância local e mostrou os controles principais: importar vídeo, console, ajustes, Mesa, Biblioteca, Cortes e Revisão.

O fluxo inicial está operacionalmente claro no nível estrutural, mas a inspeção visual indica alta densidade de elementos decorativos, janelas sobrepostas e textos em caixa alta. O Console está visível e explica que etapas do Whisper, Furia 1, captions e exportação aparecem ali. Os contadores começam em zero e há ações de importação em mais de um ponto.

Próximo teste manual: abrir o modal de importação, verificar nomes acessíveis, fechar sem selecionar arquivo, testar navegação entre telas e confirmar que a fonte ativa permanece disponível. Não foram usados arquivos privados nesta inspeção.

## Teste manual do modal

O botão principal de importação abriu o modal correto, com explicação de que o arquivo será copiado para o workspace local, formatos aceitos, área de arraste e botão de confirmação. O fechamento pelo controle X retornou à Mesa sem alterar a tela, sem criar projeto e sem abrir uma segunda aba ou instância.

Achado visual: a composição continua densa e decorativa, mas os textos e ações principais estão presentes. A próxima inspeção deve testar Ajustes, Console, Biblioteca e uma importação real em workspace descartável.

## Teste manual de Ajustes

A tela de Ajustes abriu no mesmo Studio e mostrou configuração de transcrição, motor de análise, chave Gemini opcional, modelo, interpretação audiovisual, explicação do snapshot Chub, duração, captions e perfil editorial. A descrição deixa claro que o Furia 1 continua local sem serviço online e que o Chub é opcional.

O modal fechou corretamente pelo X, retornando à Mesa sem perda de estado. Achado de melhoria: a tela é funcional, mas o volume de opções pode ser melhor agrupado por intenção e estados dependentes podem ser ocultados até que o usuário escolha Gemini ou snapshot Chub. Isso deve ser tratado em um ciclo de UX posterior, depois da estabilização da calibração.

## Teste manual de Biblioteca e Cortes

A navegação para Biblioteca carregou a tela de fontes locais, filtros, ordenação e ação Nova fonte. A navegação para Cortes carregou o estado vazio com a orientação “Escolha uma fonte primeiro” e o botão Abrir Biblioteca. Não houve erro, segunda aba ou perda inesperada de estado.

Achado de UX: os estados vazios são compreensíveis, mas há repetição de janelas decorativas e controles minimizados que competem com a ação principal. Isso reforça a prioridade de um ciclo posterior para densidade visual, hierarquia e modo responsivo simplificado.

## Teste manual de Console e retorno

O Console foi recolhido na tela de Cortes sem erro. O retorno à Mesa funcionou normalmente; o estado vazio continuou consistente e nenhuma nova aba foi aberta. O fluxo básico de navegação Mesa → Biblioteca → Cortes → Mesa está funcional no QA local.

## Regressão automatizada da calibração

A suíte focada em gates, fronteiras, divisão de segmentos, turnos de entrevista, perguntas, fechamento do raciocínio, volume de candidatos, pool e palavras temporais passou com **96 testes aprovados**. A execução foi feita com `PYTHONPATH=.` e não utilizou mídia privada.

## Regressão de integrações opcionais

A suíte de Chub, memória histórica, vínculo de Acervo, batching e revisão Gemini, quota, espera, multimodalidade e backend auxiliar passou com **81 testes aprovados**. O resultado confirma o contrato esperado: Furia 1 local permanece o caminho canônico; Chub e Gemini continuam auxiliares e opt-in.

## Verificação visual após o passe de legibilidade

A Mesa recarregou corretamente após a atualização de CSS. Os controles Importar, Console, Ajustes, navegação inferior, contadores, estado vazio e janelas de trabalho continuam presentes em uma única instância. O layout desktop não apresentou quebra visível; as regras responsivas e os alvos de toque foram ampliados sem alterar o contrato do backend.

## Suíte completa após o ciclo

A execução completa passou com **880 testes aprovados**, **27 ignorados** e **2 falhas esperadas (xfail)**, em 17,74 segundos. `git diff --check` também passou. Não foram adicionados dados privados, mídia, transcripts ou credenciais.
