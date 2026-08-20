# PROJECT_STATE — Furia Clips

> Este é o estado vivo do projeto. Atualize-o ao final de cada rodada verificável. O histórico detalhado permanece nos relatórios de ciclo; não misture instruções antigas, hashes obsoletos ou alterações locais já encerradas com o estado corrente.

## Estado corrente

| Campo | Valor |
| --- | --- |
| Projeto | Furia Clips |
| Repositório | `SAGIEV007/furia-clips` |
| Versão pública atual | `6.13` |
| Última release funcional anterior | `6.12` |
| Natureza da release atual | Gate observável Renan-first: identidade de locutor ausente deixa de passar como contexto completo e corte pronto |
| Fonte da versão | [`VERSION`](../../VERSION) |
| Branch de trabalho | `claude/repo-access-commits-imgjmk` |
| Última publicação conhecida | `c434802` — `fix: exigir identidade de locutor no modo Renan-first (6.13)` |
| Commit funcional 2.6 | `fec34fe` — `feat: primeira ponte funcional Campaign Hub para propostas (2.6)` |
| Commit funcional 2.7 | `a0452d3` — `fix: declarar confiabilidade da medição no benchmark editorial (2.7)` |
| Commit funcional 2.8 | `fdf5e6b` — `fix: alinhar seeds do Campaign Hub com a mídia local em processamento (2.8)` |
| Commit funcional 2.9 | `10c1fad` — `feat: medir recall em fonte longa inteira e descartar não-conteúdo rotulado (2.9)` |
| Commit funcional 3.0 | `f83d1fb` — `feat: governar o orçamento de candidatos pela fonte, com precisão medida (3.0)` |
| Commit funcional 3.1 | `a170aab` — `feat: entregar todo candidato com contexto, locutor e veredito de revisão (3.1)` |
| Última atualização | 2026-08-20 |
| Baseline editorial | Duas fontes medidas na 3.1. `3XJfcqn56Rw` (live 98 min): recall `50/66`, cobertura `25/27`. `j9FRVbb8CAI` (entrevista 31 min): recall `30/34`, cobertura `11/11`. Precisão `1.00`, zero fora de bloco e zero desperdício **nas duas**. O ciclo 6.13 mediu uma transcrição sem diarização: no modo Renan-first, `9/9` candidatos ficaram para revisão de locutor. |
| Suíte no checkout | 537 aprovados, 4 ignorados após provisionamento temporário do asset BlazeFace; sem asset, 1 falha ambiental |
| Objetivo | Gerar cortes Renan Santos/MBL concisos, autossuficientes, contextualizados e editorialmente úteis |

A branch de trabalho deve ser confirmada no checkout real. O GitHub é a fonte da revisão técnica; este arquivo não pode manter um hash diferente do `HEAD` final publicado. Antes de alterar qualquer arquivo, preserve mudanças locais e confirme `git status`.

## Norte imediato

A release 6.13 corrige uma permissividade real do modo Renan-first: uma transcrição sem diarização não pode ser tratada como prova de que o trecho é fala do Renan. Os candidatos continuam disponíveis para diagnóstico, mas entram explicitamente na revisão e não podem ser tratados como cortes prontos. O download autenticado da 6.12 continua pendente de teste no notebook do usuário e permanece separado desta hipótese editorial.

A próxima hipótese única é usar, quando houver snapshot local autorizado e alinhado, a evidência temporal do Acervo (`renanSpeaking`, `speakersNote`, tier e intervalos) para resolver parte da identidade sem liberar automaticamente candidatos de baixa confiança. O Campaign Hub continua como memória, seed e benchmark; contexto, payoff, locutor e evidência vencem viralidade.

As prioridades editoriais Renan-first continuam preservadas: contexto e payoff antes de hook, gates de locutor antes do ranking, Campaign Hub como memória/seed e não como aprovação, e uma hipótese principal por ciclo.

## Release atual — 6.13

A 6.13 adiciona um contrato explícito de identidade de locutor ao fluxo Renan-first. O sistema diferencia uma fronteira de fala limpa de uma identidade realmente disponível. Quando o perfil/foco é Renan Santos/MBL e a transcrição não tem diarização ou marcador de locutor, `context_complete` e `qa_bridge` não passam, o candidato recebe `review_required=true` e o ranker registra a razão técnica. O modo genérico não recebe esse bloqueio.

A mudança foi medida em uma transcrição persistida real com 247 segmentos e nenhum locutor identificado: `9/9` candidatos Renan-first ficaram com identidade indisponível, revisão obrigatória e contexto não completo. A rota genérica preservou `5/5` candidatos completos. A suíte terminou com 537 testes aprovados e 4 ignorados após asset ambiental temporário. Relatório em [`CYCLE_28_REPORT_2026-08-20.md`](CYCLE_28_REPORT_2026-08-20.md).

## Release anterior — 6.12

A 6.12 adiciona a ponte operacional que faltava entre a interface de Link público e o suporte local do yt-dlp. O usuário pode escolher Chrome/Chromium, Firefox, Edge, Opera/Opera GX ou Brave; o valor é normalizado, validado e usado apenas localmente pelo processo. Um User-Agent opcional é encaminhado com limite de tamanho e permanece vazio por padrão.

O probe, a importação de vídeo, a importação de áudio, a transcrição por URL e a busca de legendas recebem os mesmos parâmetros. Anti-bot e HTTP 403 agora produzem mensagens diferentes e acionáveis. A mudança foi testada com 27 regressões focadas e 532 testes aprovados em suíte completa, com 4 testes ignorados; o modelo BlazeFace usado para separar a falha ambiental foi removido antes do commit.

O download com a sessão real do notebook do usuário permanece **não verificado** no sandbox. O relatório da rodada está em [`CYCLE_27_REPORT_2026-08-20.md`](CYCLE_27_REPORT_2026-08-20.md).

## Release anterior — 3.3

A 3.3 destilou o corpus do Acervo — 517 vídeos, 16.559 blocos, 885.215 frases — em
`data/chub_priors/acervo_priors.json`, com **3 KB**. O cálculo roda no servidor do
Chub em consulta somente leitura; volta apenas estatística agregada e não reversível.

O léxico aprendido descobriu categorias que a lista manual não tinha — publicidade,
doações, jargão do canal — com log-odds até `5.05`. Também mostrou que **o que torna um
trecho um destaque não é lexical**: log-odds máximo de `0.89`, por isso nenhum léxico de
destaque foi incluído.

**A hipótese da rodada foi refutada.** O léxico não leva o detector a patamar
utilizável: teto de 11% de recall, e no nível de unidade a separação é *invertida* na
fonte com amostra suficiente. O score passou a ser evidência reportada, nunca veredito,
com regressão travando esse contrato. Relatório em
[`CYCLE_23_REPORT_2026-08-17.md`](CYCLE_23_REPORT_2026-08-17.md).

## Release anterior — 3.2

A 3.2 ataca a dependência de rótulo externo. Até a 3.1, tudo que o Furia sabia sobre
estrutura vinha pronto do Acervo — e some numa fonte que o Acervo não processou. O
tamanho da dependência estava medido desde a 2.9: `11/66` sozinho contra `50/66` com
os rótulos, ou seja, 4,5×.

A primeira tentativa — reconhecer não-conteúdo por vocabulário — falhou com 3.4% de
recall, e a falha mostrou que o problema estava mal formulado: região sem conteúdo é o
complemento dos blocos, então a capacidade real é **segmentar**.

`modules/topic_segmenter.py` encontra fronteiras por vale de coesão lexical. Calibrado
só na live de 98 minutos, cobre **23/27 blocos (85%)** ali e **9/11 (82%)** na
entrevista de 31 minutos, que nunca entrou na calibração, com precisão temporal de 75%
e 85%.

O segmentador **ainda não está ligado ao seletor**: esta rodada entrega e mede a
capacidade. Relatório em [`CYCLE_22_REPORT_2026-08-17.md`](CYCLE_22_REPORT_2026-08-17.md).

## Release anterior — 3.1

A 3.1 tratou de **entrega**, não de cobertura. `precision@k` foi medida primeiro e
mostrou que o ranqueamento já funciona: 100% dos 20 primeiros colocados carregam um
destaque QA-gated, em blocos de densidade 76–83. O Renan-first também já opera, com
20% do top 20 vindo dos blocos com Renan falando, que são só 9% dos destaques. Nenhum
peso de ranking foi alterado.

O defeito real era outro: só os candidatos nascidos de seed do Chub carregavam
proveniência; os demais chegavam ao revisor sem tema, sem risco e sem dizer quem fala
— num acervo onde 24 de 27 blocos têm `renan_speaking=false`. Agora 121 de 121 (100%)
chegam com contexto completo e veredito de revisão, sempre como `evidence_only`.
Relatório em [`CYCLE_21_REPORT_2026-08-17.md`](CYCLE_21_REPORT_2026-08-17.md).

## Release anterior — 3.0

A 3.0 removeu o teto fixo de candidatos. `_selection_coverage_plan()` calculava
`min(36, ...)`, o que dava a uma fonte de 4 horas praticamente a mesma cota de uma de
1 hora: quanto mais longa a live, maior a fração dela que nunca era examinada.

A precisão foi medida **antes** de mexer no teto. Numa varredura de 20 a 160
candidatos, `precision_on_block` ficou em `1.00` em todos os pontos, com zero
candidatos fora de bloco, e o IoU médio subiu de `0.0772` para `0.2730`. A oferta
satura em 121: o teto não continha excesso, cortava material já aprovado pelos gates.

Resultado na mesma fonte: recall de `27/66` para `50/66`, cobertura de `20/27` para
`25/27`, precisão inalterada em `1.00`. Somando as rodadas: `11/66` → `24/66` →
`27/66` → `50/66`, **4,5× o ponto de partida**. Relatório em
[`CYCLE_20_REPORT_2026-08-17.md`](CYCLE_20_REPORT_2026-08-17.md).

## Release anterior — 2.9

A 2.9 produziu o primeiro número de recall comparável em uma fonte longa inteira. O
bloqueio de todas as rodadas anteriores era a falta do MP4; a observação que o removeu
é que a seleção roda sobre a **transcrição**, não sobre os pixels, então uma
transcrição autorizada do Acervo já permite medir a seleção.

Medido em `3XJfcqn56Rw` ("O ÚLTIMO ANÁLISES RENAIS", 98 minutos, 27 blocos, 66
destaques): a seleção local recupera `11/66`; a ponte `campaign_hub_guided` leva a
`24/66` — **primeira evidência quantitativa de que a integração da 2.6 funciona**; e o
descarte de não-conteúdo rotulado leva a `27/66`, com cobertura de blocos `20/27`, IoU
`0.16` e **zero** candidatos desperdiçados, contra 14 no início.

O recall é binário: 24 destaques inteiros, 42 nunca tocados, zero parciais. O gargalo
é cobertura, não borda de janela. Relatório em
[`CYCLE_19_REPORT_2026-08-17.md`](CYCLE_19_REPORT_2026-08-17.md).

## Release anterior — 2.8

A 2.8 corrigiu a causa do recall travado: as seeds do Campaign Hub nasciam no eixo de
tempo errado. `_map_interval()` decidia o mapeamento pela duração declarada em
`records.sources[].duration_s` — a live inteira — e não pela duração do arquivo em
processamento. No b354 a live tem `11230s` (valor conferido no Acervo; a documentação
anterior registrava `7241s`) e o bloco tem `549.44s`: a condição nunca fechava.

Reproduzido em execução real: as três seeds ficavam em `6289.36` / `6365.80` /
`6631.04` enquanto a transcrição do MP4 do bloco ia de `0` a `497s`. Nenhuma seed caía
dentro da transcrição.

A reprodução revelou uma segunda falha não prevista. Em vez de zero propostas, o
seletor devolvia **três propostas idênticas** em `488.48–497.00`, porque
`_build_campaign_hub_proposal()` ancorava qualquer seed órfã na frase mais próxima sem
limite de distância — e a frase mais próxima de uma seed em `6289s` é sempre a última
da transcrição. Três destaques distintos viravam a mesma janela errada carregando
proveniência do Campaign Hub. Isso é proposta errada com procedência falsa, não apenas
recall perdido.

Com a duração medida da mídia informada pelo job, os três destaques mapeiam para
`146.80` / `223.24` / `488.48` e geram três propostas distintas, cada uma abrindo antes
do destaque para recuperar a pergunta ou o antecedente, todas `review_required=true`
porque o bloco tem `renanSpeaking=false`.

O recall real continua **não verificado**: a transcrição das regressões é sintética e
exercita o alinhamento, não a seleção. O MP4 local do b354 não está no ambiente.
Nenhum ganho sobre o baseline `0/3` é reivindicado. Relatório em
[`CYCLE_18_REPORT_2026-08-17.md`](CYCLE_18_REPORT_2026-08-17.md).

## Release anterior — 2.7

A release 2.7 corrigiu um modo de falha da **medição**, não da seleção. O benchmark
podia devolver `recall 0/3` por dois motivos completamente diferentes — a seleção
realmente errou os destaques, ou as referências nunca foram mapeadas para a timeline
local — e o relatório não distinguia os dois casos.

O caso foi reproduzido em execução real: sem `--source` legível pelo `ffprobe`,
`map_interval_to_local()` mantém os destaques em segundos absolutos (`6289.36`)
enquanto os candidatos estão na timeline local (`146.80`). O relatório então
acusava `mean_boundary_error_s: 5904.771` — o deslocamento do bloco dentro da live,
não erro editorial — e mesmo assim exibia `coverage_recall: 0.0` como se fosse
comparável ao baseline.

`assess_measurement()` em `modules/editorial_benchmark.py` passou a declarar
`measurement.reliable`, `status`, `mapping_required`, `mapping_applied`,
`source_is_full_length` e avisos em português. A decisão tem três vias: MP4 do
bloco (mapeia), fonte longa completa (coerente sem mapear) e qualquer outro caso
com bloco fora do início (incoerente, avisa). `metrics` repete
`measurement_reliable` porque `list_benchmarks()` expõe apenas `metrics`.

`scripts/run_editorial_benchmark.py` passou a expandir `~` em `--memory` e
`--source` — antes falhava silenciosamente com "Bloco não encontrado" — e emite os
avisos em `stderr`. `app.py` devolve `measurement` na rota de benchmark.

Suíte: **330 aprovados, 7 falhas ambientais** (`ffmpeg`/`ffprobe` ausentes e asset
externo BlazeFace). As mesmas 7 falhas foram reproduzidas com `git stash` no código
original (`326 aprovados`), confirmando que não têm relação com a mudança.
`compileall`, `node --check` e `git diff --check` passaram.

O recall real do b354 continua **não verificado**: o MP4 local do bloco não estava
presente no ambiente e o conector CHUB ficou indisponível durante a rodada. O
baseline permanece `0/3`, sem reivindicação de ganho. Seleção, ranking, expansão de
seeds e renderização não foram alterados. Relatório em
[`CYCLE_17_REPORT_2026-08-17.md`](CYCLE_17_REPORT_2026-08-17.md).

## Histórico funcional anterior — 2.2

A release 2.2 implementou `modules/editorial_benchmark.py`, `scripts/run_editorial_benchmark.py`, persistência local de comparações, exportação individual de highlights e ações correspondentes no painel de Blocos. O benchmark real usou sete candidatos persistidos pelo Furia e três destaques QA-gated do snapshot local autorizado.

Os destaques foram mapeados para `146.80–150.80s`, `223.24–228.40s` e `488.48–495.20s` no MP4 local de `549.449s`. O recall temporal foi `0/3`; o IoU médio foi `0.0`; os três casos foram classificados como `Campaign Hub melhor` na métrica temporal. O resultado não aumenta o peso do Campaign Hub no ranking e não consulta MCP durante o corte. Isso é uma limitação consciente da release 2.2, não o norte final: a próxima integração deve usar snapshot Chub antes do score para gerar propostas contextualizadas, mantendo o job offline-first.

Os três exports individuais foram validados em 1920×1080 H.264/AAC, com durações aproximadas de `4.004s`, `5.172s` e `6.740s`. A suíte da release 2.2 terminou com **327 testes aprovados**. O modelo pequeno de facetracking permanece um asset externo e não deve ser incluído no Git.

## Release atual — 2.6

A release 2.6 adicionou `modules/campaign_hub_guidance.py`, os caminhos `_select_with_campaign_hub_guidance()` e `_build_campaign_hub_proposal()` em `modules/clip_selector.py`, o diagnóstico de seeds em `modules/editorial_context.py` e a carga única do snapshot em `app.py`. As propostas carregam `source=campaign_hub_guided`, `candidate_origin=campaign_hub_guided`, proveniência completa e gates de contexto, payoff, locutor, timing, risco, técnico, proveniência e avisos.

A suíte terminou com **333 testes aprovados**, incluindo seis regressões novas. Também passaram `compileall`, `node --check static/js/app.js`, `git diff --check` e a verificação SHA-256 do BlazeFace temporário. O payload real do Chub para `gVrW6a5e6Tc` produziu duas seeds e duas propostas: `426.4–451.52s` e `511.0–566.12s`, ambas com `context_complete=true`. Como eram `third_party` e tinham `start_continuation`, ambas ficaram com `review_required=true`.

O recall do b354 continua **não verificado nesta release**, porque o snapshot autorizado correspondente não estava instalado localmente durante o job normal. O baseline permanece `0/3`, sem reivindicação de ganho. Sem snapshot em `~/FuriaClipsData/campaign_hub/profile.json`, o caminho legado permanece disponível.

## Release documental — 2.3

A revisão 2.3 criou [`PROMPT_MESTRE_IA.md`](PROMPT_MESTRE_IA.md), uma versão copiável que consolida o `START_HERE`, os prompts históricos, as decisões permanentes, o norte do benchmark 2.2, as regras do Campaign Hub, o ciclo obrigatório de engenharia, o contrato de documentação, segurança e formato de entrega.

A revisão 2.4 criou [`CHUB_INTEGRATION_CONTRACT.md`](CHUB_INTEGRATION_CONTRACT.md) e reorientou o prompt mestre e o `START_HERE`: a prioridade agora é fazer o contexto do Campaign Hub alimentar seeds, alinhamento, expansão, gates, propostas e renderização de cortes; blocos permanecem como superfície de diagnóstico e revisão.

A revisão 2.5 criou [`PROMPT_EXECUCAO_CHUB_CORTES.md`](PROMPT_EXECUCAO_CHUB_CORTES.md), um roteiro copiável para implementar a ponte funcional Chub→cortes sem misturar escopo. A release 2.6 executou a primeira implementação funcional desse roteiro; o benchmark b354 permanece em `0/3` até ser reprocessado com snapshot local.

Também permanece vigente [`COMMIT_MESSAGE_TEMPLATE.md`](COMMIT_MESSAGE_TEMPLATE.md), que torna obrigatório registrar hipótese, baseline, implementação, escopo excluído, validação, resultado, limitações e continuidade no corpo dos commits relevantes.

`README.md`, `AGENTS.md` e `START_HERE.md` agora encaminham qualquer IA que receba apenas o link do GitHub para o prompt mestre, o estado vivo, a próxima hipótese, as decisões e o modelo de commit. O `PROJECT_STATE.md` foi normalizado para manter uma única seção corrente e corrigir o hash da release 2.2 para `074a129`.

## Estado funcional conhecido

O projeto é uma aplicação local Flask com Socket.IO, SQLite, FFmpeg/FFprobe, faster-whisper, MediaPipe/BlazeFace, yt-dlp e fallbacks locais/online opcionais. O princípio de timeline canônica mantém intervalos derivados vinculados ao vídeo original.

O pipeline conhecido contém ingestão e validação de fonte, download público, transcrição timestampada, análise de contexto, geração de candidatos, ranking editorial explicável, revisão humana, renderização por preset, legendas, validação audiovisual e persistência de jobs/feedback. A release 2.1 adicionou memória local offline-first do Campaign Hub, blocos editoriais e exportação seletiva; a release 2.2 adicionou benchmark persistente e exportação individual de highlights; a release 2.6 adicionou a primeira ponte para propostas guiadas.

O Furia consegue receber MP4 local, transcrever, selecionar e renderizar arquivos tecnicamente válidos, mas ainda não oferece uma experiência diária equivalente ao Garimpo + Campaign Hub. A seleção ainda precisa melhorar em contexto, cobertura, identidade do locutor, completude Q&A, autossuficiência e estabilidade entre reprocessamentos.

## Regras permanentes

As decisões duráveis estão em [`DECISIONS.md`](DECISIONS.md). As mais importantes são:

- contexto e payoff vencem slogan, duração curta ou palavra viral;
- gates de contexto, timing, locutor, transcrição, mídia e risco vêm antes do ranking;
- o Campaign Hub é prior fraco e benchmark read-only, nunca aprovador automático;
- uma rodada deve testar uma hipótese principal e comparar antes/depois;
- a transcrição fornecida pelo editor é a timeline canônica;
- `quem fala`, `quem aparece` e `quem é foco editorial` são campos distintos;
- em ambiguidade de enquadramento, preserve `16:9 original` em vez de crop central arbitrário;
- o job normal não chama MCP; snapshots autorizados devem ser locais, sanitizados e versionados;
- contas, plataformas, crossposts, métricas e proveniência permanecem separados;
- vídeos grandes, bancos, tokens, cookies, chaves, transcrições privadas e dados pessoais ficam fora do Git;
- trabalho ocorre em branch, commits são pequenos e merge na principal exige autorização explícita;
- todo commit relevante deve seguir [`COMMIT_MESSAGE_TEMPLATE.md`](COMMIT_MESSAGE_TEMPLATE.md).

## Validação e evidências

A validação da release 2.6 incluiu suíte com **333 testes aprovados**, `compileall`, `node --check static/js/app.js`, `git diff --check` e verificação SHA-256 do BlazeFace temporário. O payload real do Campaign Hub confirmou duas seeds e duas propostas guiadas com `context_complete=true`, mas o benchmark b354 não foi reprocessado porque o snapshot correspondente não estava instalado localmente. Esses resultados não substituem a medição futura de recall em mídia b354.

Em qualquer rodada, classifique conclusões como `confirmado`, `reproduzido`, `corrigido`, `provável`, `não verificado` ou `bloqueado`. O relatório desta rodada está em [`CYCLE_28_REPORT_2026-08-20.md`](CYCLE_28_REPORT_2026-08-20.md).

## Histórico resumido

| Release | Foco | Resultado principal | Relatório |
| --- | --- | --- | --- |
| 6.13 | Identidade Renan-first | `9/9` candidatos sem diarização ficaram para revisão; modo genérico preservado | [`CYCLE_28_REPORT_2026-08-20.md`](CYCLE_28_REPORT_2026-08-20.md) |
| 6.12 | Ingestão pública segura | Cookies locais opcionais e diagnóstico anti-bot/403; download com sessão do usuário ainda não verificado | [`CYCLE_27_REPORT_2026-08-20.md`](CYCLE_27_REPORT_2026-08-20.md) |
| 3.3 | Destilação do corpus | 885k frases em 3 KB; ganho no detector refutado e o sinal mantido fora do veredito | [`CYCLE_23_REPORT_2026-08-17.md`](CYCLE_23_REPORT_2026-08-17.md) |
| 3.2 | Interpretação própria | Segmentação temática nativa cobre 85% e 82% dos blocos do Acervo em duas fontes | [`CYCLE_22_REPORT_2026-08-17.md`](CYCLE_22_REPORT_2026-08-17.md) |
| 3.1 | Corte pronto e ranqueado | 100% dos candidatos com contexto, locutor e veredito; ranqueamento confirmado (top 20 = 100% com destaque) | [`CYCLE_21_REPORT_2026-08-17.md`](CYCLE_21_REPORT_2026-08-17.md) |
| 3.0 | Orçamento governado pela fonte | Recall `27/66`→`50/66` e cobertura `20/27`→`25/27` com precisão inalterada em `1.00` | [`CYCLE_20_REPORT_2026-08-17.md`](CYCLE_20_REPORT_2026-08-17.md) |
| 2.9 | Recall medido em fonte longa | Ponte Chub dobra o recall (`11/66`→`24/66`); filtro de não-conteúdo leva a `27/66` | [`CYCLE_19_REPORT_2026-08-17.md`](CYCLE_19_REPORT_2026-08-17.md) |
| 2.8 | Alinhamento temporal das seeds | Seeds do b354 passam a cair na timeline local; três propostas falsas idênticas eliminadas | [`CYCLE_18_REPORT_2026-08-17.md`](CYCLE_18_REPORT_2026-08-17.md) |
| 2.7 | Confiabilidade declarada da medição | Benchmark passa a distinguir `0/3` de seleção de `0/3` por timeline não mapeada | [`CYCLE_17_REPORT_2026-08-17.md`](CYCLE_17_REPORT_2026-08-17.md) |
| 2.6 | Primeira ponte Campaign Hub→seeds→propostas | 2 seeds e 2 propostas reproduzidas em payload real; recall b354 ainda não medido | [`CYCLE_16_REPORT_2026-08-17.md`](CYCLE_16_REPORT_2026-08-17.md) |
| 2.5 | Prompt operacional Chub→cortes | Roteiro copiável; sem alteração funcional | [`CYCLE_15_REPORT_2026-08-17.md`](CYCLE_15_REPORT_2026-08-17.md) |
| 2.4 | Contrato Chub→cortes e reorientação do prompt | Norte funcional atualizado; sem alteração de processamento | [`CYCLE_14_REPORT_2026-08-17.md`](CYCLE_14_REPORT_2026-08-17.md) |
| 2.3 | Prompt mestre e contrato de continuidade | Documentação consolidada; sem alteração de processamento | [`CYCLE_13_REPORT_2026-08-17.md`](CYCLE_13_REPORT_2026-08-17.md) |
| 2.2 | Benchmark persistente e highlights individuais | `0/3` highlights cobertos; mapeamento e exports funcionaram | [`CYCLE_12_REPORT_2026-08-17.md`](CYCLE_12_REPORT_2026-08-17.md) |
| 2.1 | Memória local, blocos e exportação seletiva | b354 exportado e validado; 322 testes | [`CYCLE_11_REPORT_2026-08-17.md`](CYCLE_11_REPORT_2026-08-17.md) |
| 2.0 | START_HERE canônico e diagnóstico prático | Contexto operacional formalizado; 306 testes | [`CYCLE_10_REPORT_2026-08-17.md`](CYCLE_10_REPORT_2026-08-17.md) |
| 1.9 | Prompt executor e benchmark como direção | Regras de continuidade e benchmark especificadas | Histórico no `CHANGELOG.md` |

## Leitura obrigatória para a próxima IA

Leia [`AGENTS.md`](../../AGENTS.md), [`README.md`](../../README.md), [`VERSION`](../../VERSION), [`docs/VERSIONING.md`](../VERSIONING.md), [`START_HERE.md`](START_HERE.md), [`PROMPT_MESTRE_IA.md`](PROMPT_MESTRE_IA.md), [`PROMPT_PROXIMOS_CICLOS_6_13.md`](PROMPT_PROXIMOS_CICLOS_6_13.md), este arquivo, [`DECISIONS.md`](DECISIONS.md), [`NEXT_CYCLE.md`](NEXT_CYCLE.md), [`COMMIT_MESSAGE_TEMPLATE.md`](COMMIT_MESSAGE_TEMPLATE.md) e o relatório mais recente. Depois confirme `git status`, branch, commit e testes no checkout real antes de propor qualquer alteração.
