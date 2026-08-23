# Ciclo 18 — Alinhamento temporal das seeds do Campaign Hub

**Data:** 17 de agosto de 2026
**Projeto:** Furia Clips
**Branch:** `claude/repo-access-commits-imgjmk`
**Baseline:** release 2.7, commit `a0452d3`
**Release:** 2.8

## Objetivo e hipótese

> Se `build_campaign_hub_guided_seeds()` receber a duração real da mídia local em
> processamento e `_map_interval()` usar essa duração — em vez da duração declarada
> no snapshot — então as seeds do b354 passarão a cair dentro da transcrição local e
> propostas guiadas serão geradas.

A rodada não alterou ranking, gates editoriais, diarização, reframe, headlines,
renderização nem download remoto por range.

## Verificação prévia contra a fonte autorizada

O conector CHUB esteve disponível nesta rodada — o que não aconteceu nos ciclos 16 e
17, ambos bloqueados por indisponibilidade. Antes de escrever qualquer código, os
dados do b354 foram conferidos direto no Acervo via `chub_acervo_blocks`:

| Campo | Valor no Acervo | Conferência |
| --- | --- | --- |
| Bloco | `b3545938-e3a5-4287-82b1-5f7dcdc218c3` | confere |
| Intervalo | `6142.56–6692.0` (span `549.44`) | confere |
| `renanSpeaking` | `false` — quem fala é Kim | confere |
| `trustTier` | `owner` | confere |
| `riskFlags` | `juridico_sensivel`, `linguagem_ofensiva`, `ataque_pessoal` | confere |
| Destaques | `sentenceIdx` 1350 / 1367 / 1426, em `6289.36` / `6365.80` / `6631.04` | confere |
| **Duração da live `57nyfP9IDW4`** | **`11230s`** | **divergente** |

A documentação e o prompt operacional registravam `~7241s` para a live. O valor real
é `11230s`. A divergência não muda o mecanismo da falha — `11230` está tão longe de
`549.44` quanto `7241` —, mas os testes desta rodada usam o número verificado.

## Reprodução do baseline

O caminho guiado foi executado com o snapshot no formato real e uma transcrição na
timeline local do bloco (`0–497s`):

```
Seeds construidas  : 3
  1350     6289.36 -   6293.36  source_timeline
  1367     6365.80 -   6370.96  source_timeline
  1426     6631.04 -   6637.76  source_timeline
Seeds DENTRO da transcricao local: 0
Propostas guiadas geradas        : 3
     488.48 -    497.00  review_required=True
     488.48 -    497.00  review_required=True
     488.48 -    497.00  review_required=True
```

A hipótese está **confirmada**: nenhuma seed cai dentro da transcrição local, e o
mapeamento sai como `source_timeline`.

### Segunda falha, não prevista na hipótese

O relatório esperado era "nenhuma proposta". O que apareceu foi pior: **três
propostas idênticas**, todas em `488.48–497.00`, carimbadas com a proveniência do
Campaign Hub.

A causa está em `_build_campaign_hub_proposal()`. Quando nenhuma frase se sobrepõe à
seed, o código ancorava na frase mais próxima, sem limite de distância. Com as seeds
em `6289s+` e a transcrição terminando em `497s`, a frase "mais próxima" é sempre a
última — então os três destaques distintos colapsavam na mesma janela, que não tem
relação nenhuma com o conteúdo deles.

Isso não é apenas recall perdido: é **proposta errada com procedência falsa**, algo
que o contrato do projeto proíbe explicitamente. A correção entrou nesta rodada por
ser a mesma falha de alinhamento se manifestando na camada seguinte.

## Implementações

| Arquivo | Alteração |
| --- | --- |
| `modules/campaign_hub_guidance.py` | `_map_interval()` e `build_campaign_hub_guided_seeds()` aceitam `media_duration` e preferem a duração medida sobre a declarada no snapshot; o recorte também passa a usar a duração real. |
| `modules/clip_selector.py` | Nova constante `MAX_SEED_ANCHOR_GAP_S = 60.0` e novo `_media_duration()`; a âncora na frase mais próxima só vale dentro dessa distância, e a duração medida é repassada às seeds. |
| `app.py` | O job grava `settings["media_duration"]` com a duração obtida por `ffprobe`, que já existia na rota e nunca chegava à camada de orientação. |
| `tests/test_campaign_hub_guidance.py` | Seis regressões novas com os dados verificados do b354. |
| `tests/test_runtime_version.py` | Passa a ler `VERSION` em vez de repetir o número. |

A decisão do mapeamento tem uma regra só: a duração **medida** da mídia vence a
**declarada**; quando não há medição, o comportamento anterior é preservado
integralmente.

## Correção de um defeito publicado na 2.7

A suíte no checkout real deu **328 aprovados e 9 falhas**, não os `330/7` que o
relatório da 2.7 afirmava. As duas falhas extras eram `test_runtime_version.py`,
que fixava a string `"2.6"` e não foi atualizado quando a 2.7 alterou `VERSION`.

O teste passou a ler o arquivo `VERSION`, de modo que a asserção continua valendo
(app e repositório precisam concordar) sem transformar cada release em uma falsa
regressão.

## Resultado

Com a duração da mídia local informada, o mesmo caminho devolve:

```
### COM MP4 do bloco (549.449s)
   1350              146.80 -    150.80  downloaded_block_timeline
   1367              223.24 -    228.40  downloaded_block_timeline
   1426              488.48 -    495.20  downloaded_block_timeline
   seeds dentro da transcricao: 3/3
```

Os três valores coincidem exatamente com os do baseline documentado
(`146.80` / `223.24` / `488.48`). As propostas resultantes:

| Janela | Duração | Seed | Revisão |
| --- | --- | --- | --- |
| `140.00–152.40` | 12.4s | `sentence-1350` | obrigatória |
| `218.00–231.00` | 13.0s | `sentence-1367` | obrigatória |
| `482.00–497.00` | 15.0s | `sentence-1426` | obrigatória |

Cada proposta cobre o seu destaque e **abre antes dele**, recuperando a pergunta ou
o antecedente em vez de começar no meio da resposta. Todas continuam
`review_required=true`, porque o bloco tem `renanSpeaking=false`: é sobre Renan, mas
quem fala é Kim.

Os três cenários de duração se comportam como esperado:

| Mídia processada | Mapeamento | Propostas |
| --- | --- | --- |
| MP4 do bloco (`549.449s`) | `downloaded_block_timeline` | 3 |
| Live completa (`11230s`) | `source_timeline` | 0 (candidatos locais já são absolutos) |
| Duração não informada | `source_timeline` | 0 — antes eram 3 falsas |

## Validação

| Verificação | Resultado |
| --- | --- |
| Regressões focadas (`tests/test_campaign_hub_guidance.py`) | 12 aprovados |
| Suíte completa | **336 aprovados, 7 falhas ambientais** |
| Suíte antes da rodada | 328 aprovados, 9 falhas |
| `compileall` | aprovado |
| `node --check static/js/app.js` | aprovado |
| `git diff --check` | aprovado |
| Segredos e mídia | nenhum token, cookie, chave, vídeo ou banco versionado |

A diferença de `+8` aprovados é exata: `+2` dos testes de versão corrigidos e `+6`
das regressões novas. As 7 falhas restantes são as mesmas de sempre — `ffmpeg` e
`ffprobe` ausentes no container e o asset externo BlazeFace.

## Classificação das conclusões

| Classificação | Conclusão |
| --- | --- |
| Confirmado | As seeds do b354 nasciam em segundos absolutos e nenhuma caía dentro da transcrição local. |
| Confirmado | Os dados do b354 no Acervo conferem com a documentação, exceto a duração da live (`11230s`, não `7241s`). |
| Confirmado | Seeds fora da transcrição geravam três propostas idênticas com proveniência do Campaign Hub. |
| Corrigido | A duração medida da mídia local passou a decidir o mapeamento temporal. |
| Corrigido | Uma seed distante da transcrição deixou de ser ancorada em uma frase não relacionada. |
| Corrigido | `test_runtime_version.py` deixou de quebrar a cada release. |
| Reproduzido | As 7 falhas ambientais da suíte existem sem esta mudança. |
| **Não verificado** | **O recall real do b354.** A transcrição usada nas regressões é sintética, construída para exercitar o alinhamento. Ela não mede seleção, e nenhum ganho sobre o baseline `0/3` é reivindicado aqui. |
| Bloqueado | O MP4 local do b354 não está neste ambiente (`workspace/exports/` vazio). |

## Próxima hipótese única

> **Se o MP4 local do bloco b354 (`549.449s`) for instalado e o Furia reprocessar o
> caso com a ponte da 2.6 e o alinhamento da 2.8, exigindo
> `measurement.reliable=true`, então o recall temporal medido será o recall real da
> seleção e poderá enfim ser confrontado com o baseline `0/3`.**

Só o MP4 falta: o alinhamento está corrigido, a medição já se declara confiável ou
não desde a 2.7, e o snapshot pode ser gerado a partir do conector CHUB, que voltou
a responder. A rodada seguinte não deve alterar seleção nem ranking antes de obter
essa medição.

Um sinal para o Ciclo C ficou registrado: quando o texto da transcrição não traz a
pergunta-gatilho, a expansão tende a juntar dois destaques vizinhos em uma janela só.
Isso é qualidade de janela, não alinhamento, e não foi tocado aqui.

## Referências

[1]: `CYCLE_17_REPORT_2026-08-17.md` — confiabilidade declarada da medição.
[2]: `CYCLE_16_REPORT_2026-08-17.md` — primeira ponte funcional da release 2.6.
[3]: `CYCLE_12_REPORT_2026-08-17.md` — origem do baseline b354.
[4]: `CHUB_INTEGRATION_CONTRACT.md` — contrato funcional da integração.
