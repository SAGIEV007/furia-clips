# Furia Studio — plano completo da próxima evolução

## 1. Objetivo e princípio de continuidade

A próxima rodada deve transformar o estado atual do Furia Studio em uma ferramenta mais previsível, legível, rápida e agradável de usar, sem perder o que foi recuperado. O princípio técnico inegociável é que o **Furia 1 permanece como único motor canônico** para transcrição, formação de candidatos, regras de contexto, score, gates, seleção e exportação. O trabalho com os demais vídeos privados servirá para calibrar e validar as regras do Furia 1; não haverá reintrodução de fluxos, nomenclaturas ou dependências do Furia 2.

Gemini continuará sendo uma evidência multimodal opcional. O Chub continuará sendo uma memória histórica autorizada, local, read-only e explicável. Nenhum dos dois poderá aprovar cortes, substituir o score técnico, decidir sozinho a quantidade de cortes ou publicar mídia.

> Critério central: melhorar a qualidade e a compreensão do processo sem criar uma caixa-preta que pareça inteligente, mas seja difícil de revisar, cancelar ou corrigir.

## 2. Escopo, entradas e proteção de dados

Antes da execução será feito um inventário dos vídeos, transcrições, cortes humanos, legendas, headlines e eventuais arquivos de referência já presentes no diretório privado de upload. Cada conjunto será identificado apenas por um nome sanitizado e por metadados agregados, como duração, resolução, presença de áudio, existência de transcrição e quantidade de referências. Mídia, transcript, bancos SQLite, caches, logs detalhados, tokens, URLs privadas e credenciais permanecerão fora do GitHub.

A calibração será feita em workspaces temporários separados. Cada rodada terá um manifesto sanitizado contendo apenas: identificador local não reversível, duração, quantidade de segmentos, quantidade de candidatos, quantidade de adiamentos, quantidade de exports, tempos por etapa e métricas de comparação. Os arquivos temporários serão removidos depois da extração dos resultados.

| Regra | Aplicação |
|---|---|
| Furia 1 | Único caminho de decisão canônica |
| Gemini | Evidência auxiliar, opt-in, cancelável e com orçamento |
| Chub | Snapshot local, read-only, descritivo e não preditivo |
| Dados privados | Somente QA local; nunca versionar ou publicar |
| Branch | Apenas `furia-studio-f1-integration` |
| Publicação | Código, testes e documentação sanitizada בלבד |

## 3. Fase A — inventário e matriz de referência

Será criada uma matriz dos vídeos adicionais. Para cada vídeo serão registrados, de forma agregada, duração, formato, fonte provável, presença de entrevistador/jornalista, número aproximado de interrupções, disponibilidade de referência humana e tipo de material. A matriz servirá para evitar calibrar uma regra para um único timestamp.

Os cortes humanos serão normalizados para uma representação comum. A comparação não será reduzida a uma única métrica: haverá IoU temporal, diferença de início, diferença de fim, cobertura de referências, sobreposição excessiva, cortes adiados e revisão editorial amostral. IoU será tratada como uma medida de proximidade temporal, não como prova de qualidade.

**Critérios de aceite da fase:** todos os vídeos disponíveis estarão catalogados; nenhuma referência será confundida com mídia de produção; cada vídeo terá um conjunto de métricas agregadas; o processo poderá ser repetido sem modificar o repositório.

## 4. Fase B — auditoria do Furia 1 e contratos internos

Antes de mudar regras, será revisado o fluxo completo: entrada do arquivo, persistência do projeto, seleção da fonte de transcrição, parser manual, detecção de turnos, criação de candidatos, reparo de bordas, gates, ranking, render, captions, payload Studio e recuperação após troca de aba ou recarga.

A auditoria verificará especialmente se existe mais de um servidor, porta, aba ou instância sendo iniciado pelo `run.bat`; se o projeto atual permanece selecionado ao navegar entre Mesa, Cortes, Console e Configurações; se as configurações são carregadas do mesmo banco; e se um job em andamento pode ser iniciado duas vezes.

Também serão conferidos contratos de dados para impedir divergências entre snake_case no backend e camelCase no frontend. Flags editoriais não podem desaparecer entre o selector, o banco, o adapter e o cartão Studio.

**Critérios de aceite da fase:** uma única aplicação e uma única porta; uma única aba inicial; estado do projeto preservado na navegação; nenhum endpoint inicia uma segunda execução silenciosa; todos os contratos relevantes possuem teste de regressão.

## 5. Fase C — calibração com os demais vídeos

Cada vídeo adicional será processado primeiro com o caminho local do Furia 1, reutilizando transcrições fornecidas quando disponíveis. O objetivo será observar padrões, não memorizar timestamps. Serão analisados casos de entrevista, sabatina, fala contínua, perguntas fragmentadas, sobreposição de falantes, intervalos, chamadas de retorno, mudanças de assunto e respostas longas interrompidas.

A calibração será feita em camadas. Primeiro serão corrigidos defeitos de fronteira: início no meio da frase, início apenas com pergunta de jornalista, fim durante intervenção, atravessamento de break, perda do payoff e consumo indevido de uma oportunidade posterior por sobreposição. Depois serão ajustadas regras de seleção e diversidade, preservando o limite de duração e a possibilidade de um raciocínio longo permanecer inteiro quando a conclusão justificar o tamanho.

Nenhuma regra nova poderá conter timestamps específicos de um vídeo. Toda correção deverá ser expressa como condição generalizável, acompanhada de um fixture mínimo e de um teste que demonstre tanto o caso positivo quanto um caso negativo próximo.

| Dimensão | O que será medido |
|---|---|
| Contexto | Pergunta, premissa ou frase de entrada suficiente |
| Continuidade | Ausência de início/fim no meio do raciocínio |
| Locutor | Presença substantiva de Renan quando exigida |
| Interrupção | Intervenção detectada e tratada na borda |
| Payoff | Conclusão ou unidade argumentativa preservada |
| Diversidade | Não consumir todas as oportunidades por sobreposição |
| Comprimento | Duração compatível com contexto e fechamento |
| Operação | Tempo, cancelamento, retry e recuperação |

## 6. Fase D — revisão audiovisual e ciclo de correção

Após cada rodada serão escolhidas amostras de maior risco, não apenas as mais bem pontuadas. A amostragem incluirá o primeiro corte, o último corte, cortes muito longos, cortes próximos a breaks, cortes com interrupção, candidatos adiados e cortes com maior divergência em relação à referência humana.

A revisão registrará apenas conclusões sanitizadas: “pergunta isolada”, “contexto suficiente”, “resposta interrompida”, “payoff completo”, “início atrasado”, “duplicação aceitável” ou “fim prematuro”. Quando surgir uma falha, será feita a sequência: reproduzir em fixture, formular regra geral, adicionar teste, reprocessar o vídeo e revisar novamente.

A análise multimodal não será usada para gerar um novo score. Quando Gemini for usado, o resultado será exibido como evidência de revisão, com estado `válido`, `parcial`, `indisponível` ou `falhou`; uma resposta incompleta nunca será convertida em fatos ou timestamps confiáveis.

**Critério de aceite:** nenhum falso positivo conhecido poderá reaparecer; os candidatos de risco terão motivo legível; a seleção local permanecerá reproduzível com as mesmas entradas e configurações.

## 7. Fase E — precisão editorial do sistema de cortes

O sistema de cortes será organizado em quatro camadas claras: geração de oportunidades, reparo de bordas, gates obrigatórios e ranking editorial. Gates obrigatórios continuarão impedindo pergunta isolada, falta de fala substantiva quando exigida, travessia de break, início no meio de frase, final no meio de intervenção e perda de contexto mínimo.

O ranking poderá ordenar candidatos aprovados, mas não poderá ressuscitar um candidato reprovado por gate. Duração será uma preferência limitada, nunca um motivo para cortar uma conclusão forte. A diversidade será aplicada depois dos gates e antes do render, com diagnóstico de quais candidatos foram descartados por sobreposição e quais ficaram disponíveis para revisão.

A interface deverá diferenciar “não selecionado”, “adiado para revisão”, “reprovado por gate” e “não renderizado por falha técnica”. Hoje esses estados podem parecer equivalentes para o usuário; a próxima versão deverá torná-los explícitos.

## 8. Fase F — redesign de UX e fluxo operacional

A experiência deverá ser guiada por um fluxo principal simples: **Importar vídeo → Confirmar fonte/transcrição → Processar cortes → Revisar shortlist → Ajustar bordas → Gerar headline/SEO local → Exportar**. Cada etapa mostrará o que está acontecendo, por que está acontecendo, quanto já avançou e qual ação o usuário pode tomar.

O usuário não deverá precisar conhecer termos como snapshot, Acervo, proxy ou job para executar a tarefa. Termos técnicos continuarão disponíveis em uma área “Detalhes”, mas a interface principal usará linguagem operacional: “memória histórica do Chub”, “revisar vídeo com Gemini”, “transcrição fornecida”, “transcrição local” e “acompanhar processamento”.

O Console será reorganizado por severidade e etapa. Mensagens normais serão compactas; avisos de revisão terão cor e ícone consistentes; erros incluirão causa provável, impacto, ação recomendada e botão de repetição quando seguro. Um job desacoplado terá “Retomar acompanhamento”, não “Iniciar novamente”.

| Fluxo | Estado mínimo visível |
|---|---|
| Importação | arquivo, duração, áudio, fonte e projeto atual |
| Transcrição | origem, modelo, progresso, cancelamento e resultado |
| Seleção | etapa, candidatos, adiados, gates e tempo estimado |
| Gemini | motivo do uso, orçamento restante, etapa remota e cancelamento |
| Revisão | risco, flags, transcript sincronizado, player e decisão |
| Exportação | formato, qualidade, destino e recuperação de falha |

## 9. Fase G — sistema visual e dashboard editorial

A atmosfera visual poderá continuar inspirada pela textura retrô e pixelada do Pool Suite, combinada com a organização espacial do Furia Studio. O visual deve servir à leitura: contraste maior, tipografia menos comprimida, estados de foco evidentes, menos elementos decorativos competindo com o player e uso consistente de coral, amarelo, ciano e tons de risco.

O dashboard da Mesa não deverá virar uma página de métricas genéricas. Ele mostrará informações úteis para a decisão da sessão: quantidade de candidatos, aprovados, adiados, riscos principais, duração média, cortes longos, oportunidades posteriores preservadas e estado do processamento. O score será sempre apresentado como um sinal auxiliar, nunca como garantia de qualidade.

O sistema de revisão terá um cartão compacto e um inspetor detalhado. O cartão responderá “o que é este corte?”; o inspetor responderá “por que entrou?”, “qual é o risco?” e “como ajustar?”. Flags como pergunta isolada potencial, interrupção final, início tardio ou contexto incompleto deverão aparecer em linguagem humana.

## 10. Fase H — edição, headlines e blocos

O player de revisão deverá permitir ajuste de início e fim com marcadores, reprodução do intervalo, loop, alinhamento às bordas de fala e restauração do intervalo original. Alterar a borda para revisão não deverá alterar silenciosamente o candidato canônico nem o score original; a UI deve diferenciar “intervalo sugerido” de “ajuste manual”.

O sistema de headlines e SEO deverá continuar local e baseado no texto visível do corte. O usuário deverá poder comparar a headline original, a sugestão gerada e sua edição manual. A geração não poderá transformar informação não presente na legenda em afirmação factual.

O sistema de blocos deverá ser navegável e didático. Cada bloco deve explicar tema, hook, entidades e relação com o trecho, com indicação clara de origem. Blocos Chub serão referências históricas; não serão apresentados como uma justificativa automática de publicação.

## 11. Fase I — desempenho, cancelamento e Windows

O pipeline será medido por etapa: descoberta do arquivo, ffprobe, transcrição, análise de energia, seleção, proxy, upload, espera remota, render e persistência. O frontend mostrará progresso real por etapa, não apenas um spinner. Operações longas terão cancelamento cooperativo; o botão deverá mudar para “cancelando” e terminar em “cancelado” ou “finalizado”.

O caminho local continuará sendo priorizado quando houver transcrição manual. Gemini deverá ser uma ação explícita e limitada por orçamento. A criação do proxy deverá ser pulável quando a operação não exigir multimodalidade. Retries deverão distinguir quota, indisponibilidade temporária, timeout e erro definitivo.

No Windows será validado o `run.bat`, localização de dados em `%LOCALAPPDATA%`, descoberta de FFmpeg, permissões de escrita, caminhos com espaços, caracteres acentuados, fechamento do processo e abertura de uma única aba. O programa deverá apresentar uma mensagem acionável quando uma dependência estiver ausente.

## 12. Fase J — integração Chub segura e útil

O Chub poderá contribuir com memória agregada de famílias de hook, temas, nomes e exemplos comparáveis, desde que o dado esteja no snapshot local autorizado. A contribuição será apresentada como explicação ou desempate editorial limitado. Não haverá consulta remota por clip, scraping, bypass de proteção, previsão de desempenho ou alteração do score técnico.

A configuração segura será desativada por padrão para propostas guiadas pelo Acervo. O usuário verá claramente a diferença entre “usar memória histórica para contexto” e “permitir propostas guiadas entrarem no pool”; esta segunda ação exigirá opt-in explícito e continuará subordinada aos gates do Furia 1.

Serão adicionados testes que provem três propriedades: sem snapshot, o Furia funciona; com snapshot, a memória não bloqueia processamento; com snapshot e default, propostas Chub não alteram o pool canônico. Um teste separado demonstrará que o opt-in, quando usado conscientemente, permanece auditável e não ignora gates.

## 13. Fase K — acessibilidade, responsividade e legibilidade

A interface será revisada em larguras de 320, 375, 768, 1024 e 1440 pixels. Serão verificados overflow horizontal, ordem de leitura, player, cartões, modal de configurações, console, tabelas e botões de exportação. A decoração da galáxia e o movimento do mapa não poderão bloquear controles.

Serão verificadas navegação por teclado, foco visível, labels, nomes acessíveis, `Escape` em modais, regiões de status, contraste, redução de movimento e alvos de toque. O objetivo não é apenas “caber na tela”, mas permitir que o usuário compreenda o estado sem depender de cor, animação ou memória do fluxo.

## 14. Fase L — testes e observabilidade

A suíte será expandida em quatro níveis. Testes unitários cobrirão parser, turnos, gates, score, Gemini e Chub. Testes de contrato cobrirão banco, adapter, payload e frontend. Testes de integração executarão um projeto pequeno com vídeo e transcript fixture. Testes de aceitação reproduzirão a navegação real: importar, sair da Mesa, voltar, processar, revisar, ajustar, gerar headline e exportar.

Será criado um diagnóstico sanitizado de job com contagens e tempos, sem transcript, mídia, caminhos privados, banco ou credencial. O sistema deverá preservar `job_id`, etapa, estado e causa final. Logs detalhados continuarão locais e temporários, com limpeza segura após a rodada.

## 15. Fase M — critérios de decisão e publicação

A publicação só ocorrerá quando a matriz dos vídeos adicionais estiver processada, as falhas editoriais concretas tiverem regressões, os fluxos de navegação estiverem testados, o Windows tiver verificação de processo único e a suíte completa passar. Se uma alteração visual exigir mudanças de contrato, ela será separada da calibração editorial para facilitar rollback.

Antes do commit final haverá revisão de `git status`, `git diff --check`, padrões de credenciais, arquivos grandes, mídia acidental, transcrições, bancos, caches e URLs privadas. O commit será feito somente na branch `furia-studio-f1-integration`, seguido de push e verificação de sincronização. O branch default não será alterado.

| Gate de publicação | Condição |
|---|---|
| Qualidade editorial | Sem regressão nos casos críticos conhecidos |
| Precisão | Métricas agregadas comparáveis em todos os vídeos disponíveis |
| UX | Fluxo principal compreensível sem conhecimento técnico |
| Confiabilidade | Cancelamento, retry, recarga e retomada testados |
| Windows | Uma instância, uma porta e uma aba |
| Segurança | Nenhum segredo ou dado privado rastreável |
| Chub | Read-only, opt-in quando necessário e sem previsão |
| Gemini | Secundário, orçamentado e com fallback local |
| Regressão | Suíte completa, sintaxe e checks frontend aprovados |

## 16. Ordem recomendada de execução

A ordem será: inventário privado; auditoria do Furia 1; calibração local com os vídeos adicionais; revisão audiovisual das amostras; correções generalizáveis; validação de seleção e gates; melhoria de UX e estados; redesign visual com foco em legibilidade; desempenho e Windows; Chub; headlines e blocos; testes de aceitação; limpeza; commit e publicação.

Essa ordem evita gastar tempo refinando aparência sobre uma regra editorial ainda instável. Também evita usar Gemini ou Chub para mascarar falhas que devem ser resolvidas pelo motor canônico. O plano poderá ser ajustado se os vídeos adicionais revelarem uma classe de falha nova, mas cada mudança deverá preservar a separação entre decisão local, evidência auxiliar e revisão humana.

## 17. Entregáveis esperados

Ao final da rodada, os entregáveis serão: código atualizado do Furia 1; testes de regressão e aceitação; interface mais legível e explicativa; fluxo de processamento recuperável; diagnóstico sanitizado; documentação de operação e orçamento; matriz agregada de calibração; relatório crítico sem dados privados; e commit publicado exclusivamente na branch dedicada.

Não será entregue como resultado público nenhum vídeo, transcript, SRT, banco, log bruto, export, snapshot privado, chave, token, URL interna ou arquivo de diagnóstico reversível.
