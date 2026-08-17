# PROJECT_STATE — Furia Clips

> Este é o estado vivo do projeto. Atualize-o ao final de cada rodada verificável. O histórico detalhado permanece nos relatórios de ciclo; não misture instruções antigas, hashes obsoletos ou alterações locais já encerradas com o estado corrente.

## Estado corrente

| Campo | Valor |
| --- | --- |
| Projeto | Furia Clips |
| Repositório | `SAGIEV007/furia-clips` |
| Versão documental atual | `2.3` |
| Última release funcional de código | `2.2` |
| Fonte da versão | [`VERSION`](../../VERSION) |
| Branch de trabalho | `manus/rebuild-opus-parity` |
| Revisão de código-base observada | `074a129` — `feat: persist editorial benchmark and export highlights (2.2)` |
| Revisão final da documentação 2.3 | Atualizar após o commit desta rodada e conferir com `git rev-parse --short HEAD` |
| Última atualização | 2026-08-17 |
| Natureza da revisão 2.3 | Documental/operacional; nenhum módulo de processamento foi alterado |
| Objetivo | Gerar cortes Renan Santos/MBL concisos, autossuficientes, contextualizados e editorialmente úteis |

A branch de trabalho deve ser confirmada no checkout real. O GitHub é a fonte da revisão técnica; este arquivo não pode manter um hash diferente do `HEAD` final publicado. Antes de alterar qualquer arquivo, preserve mudanças locais e confirme `git status`.

## Norte imediato

A release 2.2 tornou mensurável o caso b354: sete candidatos locais cobriram `0/3` highlights QA-gated do Campaign Hub, com IoU médio `0.0`, embora o mapeamento da timeline e a exportação individual tenham funcionado. A lacuna atual é **cobertura da seleção**, não renderização.

A hipótese única da próxima rodada está em [`NEXT_CYCLE.md`](NEXT_CYCLE.md): transformar cada highlight em uma semente de proposta e expandi-la até a menor janela completa da transcrição, mantendo frase, tese, pergunta–resposta quando necessária e payoff. A rodada não deve misturar ranking, diarização, reframe, headlines, editor estilo CapCut, tradução, avatars, voz, música, branding, publicação automática, múltiplas câmeras ou download remoto por range.

O caso b354 deve preservar `renanSpeaking=false` quando Kim ou outro terceiro fala. O fato de um bloco ser sobre Renan não autoriza atribuir a fala a Renan. Propostas guiadas devem permanecer separadas de cortes aprovados e não podem apagar candidatos de terceiros.

## Última release funcional — 2.2

A release 2.2 implementou `modules/editorial_benchmark.py`, `scripts/run_editorial_benchmark.py`, persistência local de comparações, exportação individual de highlights e ações correspondentes no painel de Blocos. O benchmark real usou sete candidatos persistidos pelo Furia e três destaques QA-gated do snapshot local autorizado.

Os destaques foram mapeados para `146.80–150.80s`, `223.24–228.40s` e `488.48–495.20s` no MP4 local de `549.449s`. O recall temporal foi `0/3`; o IoU médio foi `0.0`; os três casos foram classificados como `Campaign Hub melhor` na métrica temporal. O resultado não aumenta o peso do Campaign Hub no ranking e não consulta MCP durante o corte.

Os três exports individuais foram validados em 1920×1080 H.264/AAC, com durações aproximadas de `4.004s`, `5.172s` e `6.740s`. A suíte da release 2.2 terminou com **327 testes aprovados**. O modelo pequeno de facetracking permanece um asset externo e não deve ser incluído no Git.

## Release documental — 2.3

Esta revisão criou [`PROMPT_MESTRE_IA.md`](PROMPT_MESTRE_IA.md), uma versão copiável que consolida o `START_HERE`, os prompts históricos, as decisões permanentes, o norte do benchmark 2.2, as regras do Campaign Hub, o ciclo obrigatório de engenharia, o contrato de documentação, segurança e formato de entrega.

Também criou [`COMMIT_MESSAGE_TEMPLATE.md`](COMMIT_MESSAGE_TEMPLATE.md), que torna obrigatório registrar hipótese, baseline, implementação, escopo excluído, validação, resultado, limitações e continuidade no corpo dos commits relevantes.

`README.md`, `AGENTS.md` e `START_HERE.md` agora encaminham qualquer IA que receba apenas o link do GitHub para o prompt mestre, o estado vivo, a próxima hipótese, as decisões e o modelo de commit. O `PROJECT_STATE.md` foi normalizado para manter uma única seção corrente e corrigir o hash da release 2.2 para `074a129`.

## Estado funcional conhecido

O projeto é uma aplicação local Flask com Socket.IO, SQLite, FFmpeg/FFprobe, faster-whisper, MediaPipe/BlazeFace, yt-dlp e fallbacks locais/online opcionais. O princípio de timeline canônica mantém intervalos derivados vinculados ao vídeo original.

O pipeline conhecido contém ingestão e validação de fonte, download público, transcrição timestampada, análise de contexto, geração de candidatos, ranking editorial explicável, revisão humana, renderização por preset, legendas, validação audiovisual e persistência de jobs/feedback. A release 2.1 adicionou memória local offline-first do Campaign Hub, blocos editoriais e exportação seletiva; a release 2.2 adicionou benchmark persistente e exportação individual de highlights.

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

A validação histórica recente da release 2.2 incluiu suíte com 327 testes, `compileall`, `node --check`, `git diff --check`, benchmark b354, três exports individuais e FFprobe. Esses resultados são evidências históricas e não substituem a execução atual após qualquer alteração.

A revisão 2.3 é somente documental. Ela não afirma novo ganho de recall, nova execução funcional ou melhoria editorial. O relatório está em [`CYCLE_13_REPORT_2026-08-17.md`](CYCLE_13_REPORT_2026-08-17.md). Em qualquer rodada futura, classifique conclusões como `confirmado`, `reproduzido`, `corrigido`, `provável`, `não verificado` ou `bloqueado`.

## Histórico resumido

| Release | Foco | Resultado principal | Relatório |
| --- | --- | --- | --- |
| 2.3 | Prompt mestre e contrato de continuidade | Documentação consolidada; sem alteração de processamento | [`CYCLE_13_REPORT_2026-08-17.md`](CYCLE_13_REPORT_2026-08-17.md) |
| 2.2 | Benchmark persistente e highlights individuais | `0/3` highlights cobertos; mapeamento e exports funcionaram | [`CYCLE_12_REPORT_2026-08-17.md`](CYCLE_12_REPORT_2026-08-17.md) |
| 2.1 | Memória local, blocos e exportação seletiva | b354 exportado e validado; 322 testes | [`CYCLE_11_REPORT_2026-08-17.md`](CYCLE_11_REPORT_2026-08-17.md) |
| 2.0 | START_HERE canônico e diagnóstico prático | Contexto operacional formalizado; 306 testes | [`CYCLE_10_REPORT_2026-08-17.md`](CYCLE_10_REPORT_2026-08-17.md) |
| 1.9 | Prompt executor e benchmark como direção | Regras de continuidade e benchmark especificadas | Histórico no `CHANGELOG.md` |

## Leitura obrigatória para a próxima IA

Leia [`AGENTS.md`](../../AGENTS.md), [`README.md`](../../README.md), [`VERSION`](../../VERSION), [`docs/VERSIONING.md`](../VERSIONING.md), [`START_HERE.md`](START_HERE.md), [`PROMPT_MESTRE_IA.md`](PROMPT_MESTRE_IA.md), este arquivo, [`DECISIONS.md`](DECISIONS.md), [`NEXT_CYCLE.md`](NEXT_CYCLE.md), [`COMMIT_MESSAGE_TEMPLATE.md`](COMMIT_MESSAGE_TEMPLATE.md) e o relatório mais recente. Depois confirme `git status`, branch, commit e testes no checkout real antes de propor qualquer alteração.
