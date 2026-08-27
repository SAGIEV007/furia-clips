# Auditoria de reintegração do Furia 1

**Data da auditoria:** 27/08/2026  
**Repositório analisado:** `SAGIEV007/furia-clips`  
**Branch de origem:** `claude/repo-access-commits-imgjmk`  
**Objetivo:** reaproveitar a base funcional do Furia 1 sem importar código, arquitetura, launcher ou experiência do Furia 2.

## Decisão de proveniência

O branch fornecido está atualmente no commit `67b64c538fdb1889efe4f8ca6901b957871b7fd7`, cujo assunto começa explicitamente com `furia2:`. A primeira implementação de código do Furia 2 foi identificada no commit `cf3e256067b03a3f3e229d1b75c04891ae5495c8`, de 25/08/2026, que adicionou a pasta `furia2/`, seus templates, CSS, JavaScript e testes próprios.

Antes desse commit existem dois commits documentais do Furia 2: `cb30fbb5f66345039a40c1778dc67ff4fbf978e1` (`docs: o conceito do Furia 2`) e `02eb36a45f7de765d68a7d96c251520881c691e0` (`docs: o prompt de construção do Furia 2`). Por segurança, a base funcional inicial será tratada como o último estado anterior à concepção do Furia 2, o commit `fb51dae` e seus ancestrais, enquanto `cb30fbb`, `02eb36a` e todos os descendentes serão considerados material pós-Furia 2 até que uma análise de dependência prove o contrário.

> Regra de integração: nenhum arquivo será copiado apenas por estar no branch mais recente. Cada capacidade será reintroduzida a partir do estado Furia 1 e validada contra o fluxo local atual.

## Estrutura encontrada no branch

O repositório possui uma aplicação principal legada no topo (`app.py`, `config.py`, `database.py`, `templates/`, `static/`, `modules/`), uma grande suíte de módulos editoriais e a pasta separada `furia2/`. Também contém dados locais, workspace, scripts de coleta/análise e documentação histórica.

A pasta `furia2/` contém `app.py`, `static/css/furia2.css`, `static/js/bancada.js`, `static/js/galaxia.js`, `templates/bancada.html` e testes com nomes explícitos de telas do Furia 2. Esses elementos serão excluídos da nova aplicação. Também serão excluídos os scripts/artefatos que só servem à operação paralela do Furia 2 ou a integrações remotas não necessárias ao produto Windows local.

O núcleo Furia 1 contém candidatos relevantes para análise posterior: `database.py`, `modules/audio_analyzer.py`, `modules/clip_selector.py`, `modules/editorial_ranker.py`, `modules/editorial_learning_store.py`, `modules/headline_studio.py`, `modules/silence_remover.py`, `modules/source_ingest.py`, `modules/source_interval.py`, `modules/transcriber.py`, `modules/transcript_parser.py`, `modules/video_cutter.py`, `modules/thumbnail_generator.py`, `modules/render_presets.py` e `modules/job_manager.py`. Cada módulo será comparado com a implementação do Furia Studio antes de ser incorporado.

## Anexos recebidos para a integração

| Arquivo | Tamanho aproximado | Uso planejado |
| --- | ---: | --- |
| `PENÉLOPENOVAXSESTAROXREGISTADEU：ODEBATESOBRERENANSANTOSNABAND.mp4` | 359,5 MB | Teste de importação, transcrição/análise, seleção e exportação |
| `RenanSantosDETONALulaeFlávioAusentesNoDebatedaBand？.mp4` | 159,1 MB | Segundo teste independente de pipeline e qualidade de cortes |
| `selecao-PENÉLOPENOVAXSESTAROXREGISTADEU：ODEBATESOBRERENAN-20260824T185842.json` | 149 KB | Referência de cortes, intervalos, títulos e possíveis sinais editoriais |
| `selecao-Renan_Santos_DETONA_Lula_e_Flavio_Ausentes_No_Debate_da_Band-20260825T165949.json` | 143 KB | Referência do segundo vídeo para comparação e regressão |
| `editorial_learning.sqlite3` | 8,8 MB | Auditoria e migração seletiva da aprendizagem editorial, sem copiar workspace ou dados operacionais cegamente |

## Riscos identificados

A árvore principal mistura uma evolução longa do Furia 1 com mudanças posteriores de produto, coleta, Campaign Hub, auto-framing, recursos experimentais e a pasta Furia 2. O risco mais importante é importar uma melhoria pós-Furia 2 por engano porque ela parece funcional isoladamente. A mitigação será manter uma matriz de proveniência por arquivo, comparar diffs contra `fb51dae` e usar testes de comportamento, não somente nomes de módulos.

Os JSON de seleção podem representar decisões editoriais e não necessariamente o formato interno atual do Studio. A base `editorial_learning.sqlite3` pode ter tabelas, colunas ou dados derivados de múltiplas fases do produto. Ela será aberta somente em modo de leitura durante a auditoria e migrada para um banco separado/compatível depois da inspeção de schema, contagens, chaves e registros.

Os vídeos são grandes e não serão embutidos no pacote final. Serão usados em workspace temporário para comparar candidatos gerados e referências fornecidas. A validação será considerada positiva quando o sistema encontrar cortes temporalmente próximos e editorialmente equivalentes aos exemplos, ou melhores segundo critérios explícitos; não será feita uma comparação superficial por score.

## Próximas decisões obrigatórias

A próxima etapa é reconstruir a linha do tempo entre `fb51dae` e `cf3e256`, identificar quais mudanças pós-Furia 1 são realmente independentes de UI e examinar o schema das duas bases SQLite. Só depois disso será criada a branch de integração, com nome separado do branch Claude, e publicado o primeiro checkpoint funcional antes dos testes com os vídeos.

## Linha do tempo confirmada

| Marco | Commit | Data | Interpretação |
| --- | --- | --- | --- |
| Último estado funcional anterior ao Furia 2 | `fb51dae` | 25/08/2026 18:17 UTC−3 | Base conservadora para auditar o Furia 1 |
| Prompt do Furia 2 | `02eb36a` | 25/08/2026 20:59 UTC−3 | Material conceitual pós-Furia 1; não será incorporado |
| Conceito do Furia 2 | `cb30fbb` | 25/08/2026 21:55 UTC−3 | Material conceitual pós-Furia 1; não será incorporado |
| Primeiro código explícito do Furia 2 | `cf3e256` | 25/08/2026 22:17 UTC−3 | Adiciona `furia2/` e testes próprios; será descartado |
| Estado atual enviado pelo usuário | `67b64c5` | 26/08/2026 12:17 UTC | Inclui múltiplas iterações Furia 2; não será usado como base direta |

Entre `fb51dae` e `cf3e256^` existem somente os dois commits documentais do Furia 2. Isso torna `fb51dae` uma fronteira prática e rastreável para o núcleo anterior. A análise de capacidades do Furia 1 seguirá pelos ancestrais de `fb51dae`, enquanto a árvore pós-`02eb36a` será tratada como referência histórica de problemas e não como fonte de implementação.

O primeiro commit de código Furia 2 adicionou seis artefatos diretamente identificáveis: `furia2/ABRIR FURIA 2.bat`, `furia2/app.py`, `furia2/static/css/furia2.css`, `furia2/static/js/bancada.js`, `furia2/templates/bancada.html` e `tests/test_a_bancada_do_furia2.py`. Commits seguintes adicionaram `galaxia.js`, `mesa`, `talho`, mapa e demais superfícies Furia 2. Nenhum deles será iniciado pelo launcher do novo Studio.

## Baseline funcional verificado

Foi criado um worktree descartável exatamente em `fb51dae` e executada a suíte original desse estado, antes de qualquer integração no Studio. Resultado: **861 testes aprovados, 30 ignorados e 2 esperados como falha (`xfail`) em 15,53 s**. Esse resultado não prova que todo módulo deve entrar no novo produto, mas confirma que a fronteira escolhida representa uma base Furia 1 testável e muito mais rica que a implementação mínima atual.

O estado atual do branch não será executado como produto: além da pasta explícita `furia2/`, o `app.py` pós-Furia 2 registra o blueprint da bancada e o `run.bat` abre deliberadamente duas URLs. Ambos os comportamentos são incompatíveis com a exigência de um único programa e serão substituídos pela integração do novo Studio sobre o motor Furia 1 selecionado.

## Matriz de separação de proveniência

| Grupo | Decisão | Motivo |
| --- | --- | --- |
| `app.py`, `config.py`, `database.py` no estado `fb51dae` | Reaproveitar seletivamente | Motor local, schema editorial, jobs e contratos editoriais do Furia 1 |
| `modules/` no estado `fb51dae` | Auditar e incorporar por capacidade | A pasta contém o núcleo de áudio, transcrição, seleção, ranking, headlines, timeline, corte, captions e aprendizagem |
| `static/`, `templates/` e testes no estado `fb51dae` | Usar como referência funcional, não como UI final | A experiência será reformulada no frontend Poolsuite-only do Studio |
| `furia2/` em qualquer commit | Descartar | É uma segunda aplicação, com blueprint, CSS, JS, galáxia, bancada e templates próprios |
| `docs/CONCEITO-FURIA-2.md`, `docs/PROMPT-FURIA-2.md` | Descartar como fonte de implementação | São concepção/prompt pós-Furia 1 |
| `tests/test_a_*furia2*` e testes das telas novas | Não incluir no produto | Testam a arquitetura visual do Furia 2, não o núcleo reaproveitado |
| `app.py` pós-Furia 2 | Não copiar | Registra o blueprint Furia 2 na mesma aplicação, criando a bifurcação `/` e `/2` |
| `run.bat` pós-Furia 2 | Reverter a lógica de duas abas | O diff adiciona duas chamadas `start` e abre `/2` e `/` simultaneamente; o Studio final terá uma chamada única |
| `modules/face_tracker.py`, publicação, coleta remota e analytics | Manter apenas se forem necessários ao fluxo local e explicitamente testados | Não serão expostos como promessa, aba ou dependência do editor mínimo |

## Contrato de integração escolhido

A integração não será um segundo servidor Flask nem um iframe/blueprint dentro do app legado. O Studio continuará sendo um único processo local e receberá uma camada de persistência compatível com o schema Furia 1, uma camada de serviços editoriais selecionados e uma única superfície HTML/CSS/JS. O launcher chamará uma única instância de Python e uma única abertura de navegador.

A base `editorial_learning.sqlite3` enviada será tratada como fonte de aprendizagem editorial. Projetos, clips, jobs e transcrições serão preservados por uma migração explícita; caminhos para mídia original serão reescritos para o workspace local somente quando o arquivo correspondente existir. Nenhum registro será apagado silenciosamente e o banco original permanecerá intacto como backup.

## Comparação dos bancos

A base enviada `editorial_learning.sqlite3` contém as tabelas `projects` (29 registros), `clips` (175), `transcriptions` (19), `clip_feedback` (35), `jobs` (49), `job_events` (510), `settings` (48), além de `processing_history`, `headline_feedback` e `performance_snapshots`. O Studio atual tinha somente `projects`, `clips` e `jobs`, com um modelo simplificado e IDs textuais.

A conclusão é que não será feita uma conversão destrutiva para o schema mínimo atual. A persistência integrada deverá manter os campos editoriais Furia 1 — intervalos, transcrição, fatores do score, confiança, chave editorial, feedback, headline feedback, histórico e eventos de job — e acrescentar somente campos locais necessários à UX Poolsuite, como estado de janela ou referência de thumbnail, quando não houver equivalente.

| Necessidade do novo Studio | Fonte de verdade escolhida |
| --- | --- |
| Projetos e fontes | Schema Furia 1, com caminhos reescritos para o workspace local quando necessário |
| Candidatos e cortes | Schema Furia 1, preservando `start_time`, `end_time`, `duration`, `viral_score`, fatores e estado de revisão |
| Transcrição | Tabela `transcriptions`, com segmentos e proveniência |
| Feedback editorial | `clip_feedback` e `headline_feedback`, sem perder decisões antigas |
| Fila | `jobs` e `job_events`, adaptados à visualização de fila do Studio |
| Configurações | `settings`, filtrando chaves não usadas pela superfície local |
| Analytics/publicação | Não serão expostos como áreas do produto; tabelas históricas não serão misturadas ao score local |

A base enviada não será modificada durante a auditoria. A migração final criará cópia de backup e será idempotente, com relatório de registros importados, ignorados, caminhos não encontrados e campos preservados.

## Atualização da referência canônica e primeiro teste real

Em 27/08/2026 foi clonado via GitHub CLI o branch `claude/furia-1-antes-do-furia-2`. O HEAD é `fb51dae57cf8726de929ed771a44019b2bc9e031`, confirmando a fronteira Furia 1 já escolhida. A branch contém a aplicação legada, módulos editoriais, scripts e documentação do Furia 1, sem uma pasta `furia2/`; ela passa a ser a referência canônica para qualquer comparação posterior.

Os dois JSON têm estruturas diferentes no resultado: o primeiro possui `cortes_renderizados` vazio e candidatos adiados, enquanto o segundo possui 9 `cortes_renderizados` e 5 `candidatos_adiados`. Portanto, a comparação de qualidade deve usar a coleção `cortes_renderizados` como referência primária, mantendo adiados como material de análise e não como cortes já aprovados.

O primeiro teste real da branch integrada foi executado com `RenanSantosDETONALulaeFlávioAusentesNoDebatedaBand？.mp4`, 1.035,47 s, com Whisper local e um snapshot Campaign Hub local separado. O pipeline concluiu com 361 segmentos de transcrição e 9 candidatos. Os 9 intervalos gerados foram distintos, sem pares com sobreposição excessiva; 8 deles se alinharam temporalmente aos 9 cortes renderizados da referência com sobreposição igual ou superior a 25%, embora a comparação ainda precise ser refinada por texto, ordem editorial e cobertura de perguntas. O snapshot chub foi aceito como contexto histórico e não alterou diretamente o score técnico.

Esse primeiro resultado confirma que o motor Furia 1 integrado é funcional, mas também revela o próximo trabalho de calibração: distinguir uma unidade editorial completa de uma simples janela de energia, preservar perguntas e pontes para candidatos futuros e comparar a produção final contra os cortes renderizados corretos, sem contar o mesmo candidato várias vezes por sobreposição.

## Revalidação pós-correção e critérios de leitura

Depois do primeiro teste, a transcrição local baseada em `openai-whisper` passou a extrair janelas WAV de cinco minutos para fontes com pelo menos dez minutos. A janela é liberada antes da próxima, e os timestamps são recolocados na linha do tempo original. Isso evita o pico de memória observado na entrevista de 44,5 minutos sem alterar o contrato de segmentos usado por captions, busca, seleção ou exportação. O fallback `faster-whisper` continua disponível quando instalado.

A seleção também passou a dividir blocos longos em sentenças de pergunta quando há uma fronteira verificável. Um bloco usado por um vencedor não marca uma pergunta na sua junta como inventário consumido; a etapa posterior de overlap continua sendo a autoridade para eliminar duplicação. A exceção não vale para uma pergunta retórica explicitamente atribuída ao mesmo locutor: ela permanece no argumento, enquanto uma pergunta independente de outro locutor abre a próxima oportunidade. Essa política tem regressões unitárias específicas para pergunta na borda, pontuação ruidosa e retórica do mesmo locutor.

| Caso real revalidado | Entrada observada | Saída do motor integrado | Leitura responsável |
| --- | ---: | ---: | --- |
| Debate Band — arquivo com 9 cortes renderizados | 1.035,47 s; 354 segmentos | 10 clips persistidos; 14 candidatos finais; 9/9 referências com correspondência; 4/9 com IoU ≥ 0,50; 3/9 com score combinado ≥ 0,50; 0 pares duplicados ≥ 0,35 | O novo pipeline recupera todas as referências aprovadas e acrescenta uma oportunidade local. A preservação automática de perguntas ainda é imperfeita (4/8 no alinhamento textual), por isso a Revisão mantém a evidência timestampada e exige confirmação humana; não há promessa de viralidade |
| Debate Band — projeto histórico 29 da base | 13 clips históricos | 10 clips finais; 10/13 referências receberam correspondência; 5/13 com IoU ≥ 0,50; 4/9 perguntas preservadas pelo alinhamento textual; não cobriu suficientemente os intervalos históricos de 555,93–612,53 s, 716,60–754,32 s e 855,04–910,55 s | A contagem maior que 9 não foi forçada. O CTA final de 989,08–1.027,92 s recebeu cobertura; três janelas históricas intermediárias seguem como lacunas de calibração, não foram apagadas silenciosamente |
| Debate longo Penélope | 1.772,10 s; 521–542 segmentos conforme a execução Whisper | 11 clips persistidos no render final pós anti-overlap; 14 candidatos finais no diagnóstico; 4/15 itens adiados com overlap ≥ 0,50 e 5/15 com overlap ≥ 0,25; um par parcial ficou sinalizado para revisão | O JSON fornecido tinha 15 itens somente em `candidatos_adiados` e zero em `cortes_renderizados`; os itens adiados foram usados como diagnóstico, não como aprovação. O pipeline terminou em uma fonte de 29,5 minutos, com chunking de áudio e sem OOM; a cobertura de alguns intervalos iniciais/intermediários ainda depende de revisão editorial |
| Entrevista crítica fora do Chub | 2.670,55 s; 1.038 segmentos | 35 clips persistidos no processamento real; 42 candidatos finais no diagnóstico antes de adiamentos de contexto; 41 hard negatives; sem snapshot Chub. A reseleção determinística posterior do transcript final produziu 37 candidatos com o código atual | A fonte foi aceita, transcrita e selecionada sem depender de associação ao Campaign Hub. O resultado não prova identidade do participante nem potencial viral; prova que a entrada local funciona sem Chub e que o motor mantém um pool amplo para revisão |

Os números de correspondência acima são diagnósticos de cobertura temporal e textual, não métricas de previsão de audiência. O Campaign Hub permanece contextual: seus hooks, posts e coortes aparecem como memória opcional, mas não entram na pontuação técnica local. Nos dois debates, o snapshot local foi aceito sem abrir uma segunda aplicação ou processo.

## Workflow funcional verificado fora da análise pesada

No caso fora do Chub, o mesmo processo local executou um clip real pelo ciclo de Revisão: o range foi alterado e o arquivo anterior foi invalidado; a resposta voltou para `needs_review`; a aprovação posterior restaurou o gate de exportação; três alternativas de headline foram geradas a partir da legenda timestampada; e a renderização vertical com captions terminou em arquivo MP4 de 19.721.171 bytes. O payload devolve a URL interna única `/studio-file?path=...`, sem caminho público inseguro. O botão de exportação continua bloqueado enquanto o clip não está aprovado.

A Revisão agora mostra até três headlines alternativas, uma citação curta da legenda, intervalo temporal e a indicação explícita de que a sugestão não é previsão de viralidade. O operador pode escolher uma alternativa e salvá-la como título local. Também foi otimizada a listagem da Biblioteca: `/api/projects` preserva contagens, status e metadados, mas carrega clips/transcript completos somente no detalhe do projeto.

A suíte dirigida posterior às alterações inclui **33 testes aprovados** nos módulos de perguntas, pool, overlap e raciocínio. A suíte completa atual do branch passou com **818 testes aprovados, 27 skips e 2 xfails em 13,93 s**, incluindo transcriber chunked, adapter HTTP, frontend Poolsuite e regressões Furia 1. Nenhum vídeo, JSON privado, SQLite enviado ou workspace temporário será incluído no repositório.
