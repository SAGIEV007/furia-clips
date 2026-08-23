# Relatório do ciclo 10 — validação real do Furia contra Garimpo/Campaign Hub

**Autor:** Manus AI
**Data:** 2026-08-17
**Projeto:** Furia Clips
**Branch:** `manus/rebuild-opus-parity`
**Baseline:** `40c78b1`
**Release documental/operacional:** `2.0`

## Resultado da rodada

Este ciclo não alterou o motor de seleção, ranking ou renderização. O objetivo foi executar o repositório real com um MP4 do fluxo de blocos da Missão, observar o comportamento ponta a ponta e comparar o resultado com o registro correspondente do Campaign Hub. A validação confirmou que o Furia já possui um núcleo técnico executável, mas ainda não possui a memória editorial nem o fluxo de download seletivo necessários para equivaler ao Garimpo e superá-lo.

A hipótese de diagnóstico foi:

> Se o mesmo bloco for processado pelo Furia como MP4 local e comparado com a unidade QA-gated do Campaign Hub, será possível separar o que já funciona tecnicamente do que ainda falta em contexto, locutor, seleção e proveniência.

A hipótese foi **reproduzida**. O upload local, transcrição, seleção, renderização e validação FFprobe funcionaram. A integração rica ainda não existe: o Furia usou somente um snapshot local pequeno, e não o bloco QA-gated do Campaign Hub durante o job.

## Ambiente e testes

O repositório foi clonado diretamente de `https://github.com/SAGIEV007/furia-clips`, na branch `manus/rebuild-opus-parity`, commit `40c78b1`. As dependências Python foram instaladas em ambiente isolado. O modelo oficial `blaze_face_short_range.tflite` foi baixado fora do commit e validado pelo SHA-256 previsto no teste.

A suíte completa terminou com **306 testes aprovados**. O servidor Flask local respondeu na porta 3001. O MP4 foi enviado pela API de upload, e o job de cortes foi iniciado pela API usada pela interface.

| Verificação | Resultado |
| --- | --- |
| Clone GitHub | confirmado |
| Branch e commit | confirmados |
| Dependências | instaladas |
| Suíte | 306 aprovados |
| Upload de MP4 | concluído |
| Job de corte | concluído |
| FFprobe dos outputs | aprovado |
| Inspeção visual dos outputs | realizada |
| Consulta de bloco no Campaign Hub | realizada em modo somente leitura |
| Área interna do Garimpo | bloqueada na sessão Sandbox; screenshot e URL foram usados como referência |

## Mídia processada

O arquivo recebido foi `Kim-transforma-a-campanha-de-Renan-em-guerra-e-convoca-45-dias-de-mobili-57nyfP9IDW4-6142-6692.mp4`. Ele tem aproximadamente 251 MB, duração de 553,527 segundos, resolução 1920×1080, H.264 e AAC.

O segundo ciclo local usou Whisper, aspecto original, facetracking desligado para esta prioridade e o contexto:

> Evento Primeiro Ato de Campanha do MBL com público e múltiplos oradores. Priorizar falas completas do Renan Santos, perguntas e respostas com contexto, começo compreensível e conclusão; não assumir que todo trecho forte é do Renan.

A execução terminou em aproximadamente quatro minutos, gerou sete cortes e preservou o aspecto 16:9. Um primeiro ciclo anterior, com o mesmo arquivo e parâmetros, gerou oito cortes. A variação é relevante: a seleção ainda não é suficientemente determinística ou estável para ser tratada como calibrada.

## Resultado local do Furia

O segundo ciclo produziu estes intervalos:

| ID | Início | Fim | Duração | Texto inicial |
| --- | ---: | ---: | ---: | --- |
| 1 | 96,296s | 139,540s | 43,244s | “Eu quero dizer, o Renan está prestes a chegar…” |
| 2 | 372,873s | 394,060s | 21,187s | “A candidatura vai vai dar traço…” |
| 3 | 514,147s | 539,072s | 24,925s | “Olha, está vindo aquele produto vagabundo do Brasil.” |
| 4 | 0s | 40,320s | 40,320s | “Para finalizar o próximo presidente…” |
| 5 | 308,870s | 331,570s | 22,700s | “A gente não tem…” |
| 6 | 417,083s | 441,741s | 24,658s | “Um bando de…” |
| 7 | 441,741s | 474,674s | 32,933s | “Nós vamos passar o tratou…” |

A análise audiovisual independente confirmou que Vinicius Poit faz o abre, Kim Kataguiri fala nos discursos e Renan é apresentado como candidato, mas não discursa nos intervalos testados. Também confirmou que não existe Q&A nesse bloco; é um comício com fala unidirecional e reações do público.

O Furia, entretanto, não identificou os locutores. Os registros persistidos mantiveram `speaker_boundary_score=50`, `question_answer_complete=false` e, em vários casos, `context_complete=true` apesar de a identidade do orador permanecer incerta. Isso é uma diferença importante entre um gate estrutural textual e uma compreensão editorial realmente confiável.

A folha de contato dos outputs confirmou que os sete arquivos preservaram 1920×1080, H.264, aproximadamente 29,97 fps e enquadramento original. O núcleo técnico de corte é funcional; a deficiência principal está na interpretação e na escolha editorial.

## Registro correspondente no Campaign Hub

A consulta read-only do Acervo por `45 dias guerra política manifestação oito pessoas` encontrou o bloco `b3545938-e3a5-4287-82b1-5f7dcdc218c3`, ligado ao mesmo vídeo do YouTube `57nyfP9IDW4`.

| Campo do Acervo | Valor |
| --- | --- |
| Título | Kim transforma a campanha de Renan em guerra e convoca 45 dias de mobilização |
| Fonte | Primeiro ato de Campanha — Renan Santos Presidente |
| Intervalo na fonte longa | 6142,56s–6692s |
| Duração | 549,44s |
| Frases na janela | 121 |
| Pergunta-gatilho | Como Kim apresenta a campanha de Renan e mobiliza os apoiadores para os 45 dias? |
| Autossuficiência | `needsContext=false`; `selfContainedRank=90` |
| Densidade | `densityRank=98` |
| Possíveis cortes | 3 |
| Locutor Renan | `renanSpeaking=false` |
| Riscos | jurídico sensível, linguagem ofensiva, ataque pessoal |
| Destaques | três frases com timestamp e motivo editorial |

Os três destaques do Acervo, convertidos para a timeline do MP4 local, foram aproximadamente `146,80–150,80s`, `223,24–228,40s` e `488,48–495,20s`.

O segundo ciclo do Furia não cobriu nenhum dos três destaques. O primeiro ciclo, perdido após a reinicialização do Sandbox, produziu um intervalo `139,48–159,74s` que cobria o primeiro destaque, mas não cobriu os outros dois. Isso mostra que o Furia pode encontrar uma frase forte por heurística, mas não está orientado pelo conjunto completo de evidências do bloco.

O Campaign Hub ainda exige conferência: sua transcrição é automática, a legenda não é citação perfeita e `turn`/`speakerChange` não são identidade garantida. A vantagem do Acervo é fornecer uma unidade editorial estruturada com resumo, pergunta, riscos, destaques, autossuficiência e proveniência, algo que o snapshot atual do Furia não possui.

## Estado da integração atual

A rota `/api/campaign-hub/status` confirmou que o Furia carregou apenas `data/editorial_priors.json`, em modo read-only, com 12 observações de hooks para cada uma das contas principal e Reserva, zero exemplos e zero coortes. O job local não chamou o MCP.

Isso confirma a arquitetura econômica recomendada: não consultar o Campaign Hub a cada corte, mas construir um exportador incremental e um snapshot local mais rico. O snapshot deve guardar texto, timestamps, blocos, destaques, perguntas, riscos, proveniência e métricas compactadas, sem baixar a mídia integral nem guardar credenciais.

## Entrada por link e download seletivo

O endpoint `/api/source/probe` recebeu o link público do YouTube, mas retornou HTTP 400 porque o `yt-dlp` foi bloqueado pelo desafio anti-bot do YouTube. O Furia não possui, no código executável atual, uma rota específica de download seletivo por `start`/`end` ou por ID de bloco. Os intervalos existentes são de cortes derivados depois que a fonte já está disponível.

Portanto, o gap principal foi confirmado:

> **O Garimpo oferece a experiência de escolher um bloco e baixar apenas aquele momento; o Furia atual baixa a fonte completa quando a entrada é por link e só depois corta localmente.**

## Classificação das conclusões

| Classificação | Conclusão |
| --- | --- |
| Confirmado | O clone GitHub, dependências, suíte, upload, transcrição local, seleção, renderização e FFprobe funcionaram. |
| Reproduzido | O Furia preserva 16:9 e gera cortes tecnicamente válidos, mas não resolve o locutor nos trechos do evento. |
| Confirmado | O Campaign Hub possui o bloco b354, com 121 frases, três destaques, pergunta-gatilho, riscos e `renanSpeaking=false`. |
| Confirmado | O snapshot local atual do Furia é pequeno: hooks agregados, sem exemplos ou coortes. |
| Confirmado | Não existe download seletivo de bloco no código executável atual. |
| Provável | A variação de 8 para 7 cortes vem de diferenças de segmentação/energia e do ranking heurístico; precisa de benchmark de reprodutibilidade. |
| Não verificado | A área autenticada interna do Garimpo não pôde ser inspecionada pela sessão Sandbox. |
| Bloqueado | O probe do YouTube foi bloqueado pelo anti-bot do provedor neste ambiente. |

## Decisão para a release 2.0

A release 2.0 é uma mudança de continuidade e operação: `START_HERE.md` passa a ser o prompt mestre canônico; `AGENTS.md` aponta para ele; os prompts antigos ficam como histórico; a versão de runtime é atualizada de 1.9 para 2.0; e o ciclo real fica registrado para impedir que uma IA futura trate o pipeline como maduro.

Nenhum motor de seleção, ranking ou renderização foi declarado melhorado nesta release. A próxima alteração de processamento deve ser o benchmark temporal/editorial entre candidatos locais e blocos QA-gated, com uma única hipótese por rodada.

## Referências

[1]: https://github.com/SAGIEV007/furia-clips — repositório e branch de trabalho.

[2]: https://criadores.missao.org.br/garimpo — referência pública do fluxo Garimpo; a área interna exige autenticação.

[3]: https://www.youtube.com/watch?v=57nyfP9IDW4 — fonte pública identificada no Campaign Hub.

[4]: https://chub-api.missao.org.br/mcp/wk_a07206ced171ac72acb18d6746e735486790ea98a2a2f51b — Campaign Hub autorizado para consultas read-only nesta sessão.
