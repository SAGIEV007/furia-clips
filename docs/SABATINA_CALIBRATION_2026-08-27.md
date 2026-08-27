# Calibração editorial da sabatina — 27 de agosto de 2026

## Escopo e princípio editorial

Esta rodada calibra o motor canônico do **Furia 1** para entrevistas com perguntas fragmentadas, interrupções, mudanças de assunto e chamadas de intervalo. O motor continua sendo um mecanismo explicável de descoberta e ordenação de **candidatos para revisão humana**; ele não estima viralidade nem transforma memória histórica do Campaign Hub em score técnico.

A validação foi feita com o transcript e a fonte audiovisual privados fornecidos para a sabatina crítica. Nenhuma mídia, transcript integral, export, diagnóstico original, banco editorial, log privado ou credencial foi incorporado ao repositório.

## Problemas reproduzidos e contratos implementados

| Problema observado | Regra calibrada | Resultado esperado |
| --- | --- | --- |
| O primeiro export continha essencialmente a pergunta da jornalista e nenhum trecho substancial de Renan. | O selector mede a fala posterior à última pergunta detectada e marca `starts_with_interviewer_question`, `answer_words_after_last_question` e `starts_with_question_only`. | Pergunta isolada fica disponível para diagnóstico, mas é adiada pelo gate de renderização; não vira clip pronto por padrão. |
| A janela de 34:30 atravessava chamada, vinheta e retorno de intervalo. | O detector reconhece vocabulário estreito de chamada/retorno, cria `broadcast_break`, `broadcast_return` e `hard_boundary`, e o alinhamento nunca cruza essa região. | Um candidato anterior termina antes da chamada; um candidato posterior começa na primeira frase editorial depois do retorno. |
| Recuo de abertura podia voltar para dentro de uma região de intervalo. | O reparo de abertura também consulta as fronteiras duras antes de recuar. | Retorno e chamada não são fundidos com a resposta anterior. |
| O candidato equivalente ao início ruidoso de 19:00 começava em uma intervenção e só depois estabilizava em “vou dar um exemplo... denúncia anônima”. | Quando há uma interjeição na entrada, o selector procura um marcador semântico posterior de resposta estabilizada, exige deslocamento mínimo e prefere essa alternativa quando o fechamento é compartilhado. | A simulação passou a preferir 19:34.56–20:26.02, em vez de 18:59.63–20:26.02; o trecho começa no argumento efetivo e termina antes da intervenção seguinte. |
| Respostas interrompidas eram tratadas como se tivessem payoff completo. | O passe final marca `ending_interruption`, `ends_at_interviewer_turn` e códigos de revisão estáveis. | A interrupção reduz a confiança de fechamento e mantém o material para revisão; não há descarte universal de toda resposta interrompida. |
| Candidatos contíguos e alternativas com a mesma pergunta pareciam oportunidades independentes. | O diagnóstico registra relações bounded `continuation_of` e `alternative_of`, preservando as razões legadas de overlap. | O ranking pode escolher uma janela, enquanto o editor ainda consegue auditar a continuação ou alternativa que perdeu. |

## Evidência audiovisual da rodada

A prévia do primeiro candidato foi avaliada como exclusivamente uma pergunta da jornalista, sem resposta do convidado. A prévia do intervalo mostrou conclusão de fala antes da chamada, chamada de programa, vinheta e retorno, confirmando que a região precisa de uma fronteira editorial dura. A prévia da abertura estabilizada começou com o convidado dizendo “Vou dar um exemplo. Vou de um a um. Denúncia anônima.”, desenvolveu a explicação e terminou antes de uma nova intervenção. A prévia longa aprovada pelo usuário, sobre a analogia com clubes de futebol e reformas econômicas, manteve contexto, desenvolvimento e conclusão; por isso continua elegível como candidato longo revisável.

Essas observações não são usadas como rótulos automáticos para outras fontes. Elas validam que os sinais implementados correspondem ao caso crítico sem codificar timestamps específicos da sabatina.

## Resultado da simulação no transcript crítico

A execução local em modo NLP reutilizou o transcript fornecido e não iniciou Whisper, Gemini, Campaign Hub ou upload de mídia. A fonte tinha aproximadamente **44,5 minutos** e foi normalizada em **510 sentenças**. O pool primário teve 99 candidatos; 89 permaneceram após o filtro de conteúdo não editorial; 39 permaneceram após overlap, alternativas e relações de continuação.

| Indicador | Resultado |
| --- | ---: |
| Candidatos primários | 99 |
| Fallback pesado utilizado | Não |
| Após filtro de conteúdo | 89 |
| Antes do overlap final | 89 |
| Resultado final da simulação | 39 |
| Fronteiras duras de intervalo detectadas | 1 região composta de chamada e retorno |
| Relações registradas no diagnóstico | Limitadas a 80 entradas |
| Candidato de pergunta isolada no render gate | Adiado para revisão |
| Candidato estabilizado de “denúncia anônima” | 19:34.56–20:26.02 |

O número final de 39 não é uma promessa de quantidade de exports. Ele representa oportunidades que sobreviveram ao selector local antes dos gates de identidade, revisão editorial e decisões humanas do Studio. Um editor ainda pode aprovar, rejeitar, alterar IN/OUT ou escolher uma alternativa.

## Regressões automatizadas

Foram adicionados testes determinísticos para classificação de chamada e retorno, fronteira dura, movimento para a primeira frase pós-retorno, pergunta sem resposta substancial, interrupção sem payoff completo, preservação de perguntas vizinhas, relações de continuação/alternativa e comportamento do gate backend.

O release gate completo passou com **837 testes aprovados, 27 ignorados e 2 xfails em 16,06 segundos**. Também passaram a compilação Python, `node --check static/app.js` e `git diff --check`.

## Limitações e próximos cuidados

A transcrição crítica não possui diarização confiável em todos os trechos. Por isso, a implementação expõe sinais de revisão em vez de afirmar identidade do locutor. Perguntas sem vocativo ou muito fragmentadas continuam sendo tratadas de modo conservador; uma menção genérica a “intervalo” não é suficiente para criar uma quebra dura.

A validação audiovisual desta rodada foi feita no ambiente Linux isolado com prévias temporárias privadas. O bootstrap, permissões, FFmpeg instalado, navegador e comportamento do `run.bat` ainda devem ser reconfirmados em uma máquina Windows real depois da publicação. A credencial Gemini temporária não foi necessária para a calibração final; recomenda-se revogá-la por precaução.

O resultado mantém a arquitetura de **um único Studio local baseado no Furia 1**, sem reintroduzir Furia 2 e sem criar uma segunda porta ou aba.
