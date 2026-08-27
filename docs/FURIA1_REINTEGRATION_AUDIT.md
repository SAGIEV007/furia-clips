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
