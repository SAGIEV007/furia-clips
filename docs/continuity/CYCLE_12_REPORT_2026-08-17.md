# Ciclo 12 — Benchmark persistente e highlights individuais

**Data:** 17 de agosto de 2026  
**Projeto:** Furia Clips  
**Branch:** `manus/rebuild-opus-parity`  
**Baseline:** release 2.1, commit `2018867`  
**Release:** 2.2

## Objetivo e hipótese

A hipótese desta rodada foi:

> Se o Furia persistir a comparação entre candidatos locais e os três destaques do b354, usando o mapeamento da fonte longa para o MP4 local e exportando highlights individuais, será possível medir recall e precisão editorial antes de aumentar a influência do Campaign Hub no ranking.

A rodada não tentou resolver diarização, reconhecimento de voz, reframe, formatos sociais, headlines ou download remoto por range.

## Baseline reproduzido

O baseline da release 2.1 já possuía memória local rica do Campaign Hub, 64 blocos reais do vídeo `57nyfP9IDW4`, exportação seletiva de um intervalo e 322 testes aprovados. O caso de trabalho foi o bloco `b3545938-e3a5-4287-82b1-5f7dcdc218c3`, intitulado **“Kim transforma a campanha de Renan em guerra e convoca 45 dias de mobilização”**.

O bloco ocupa `6142.56–6692.0s` na fonte longa, tem `549.44s`, três destaques QA-gated, `renanSpeaking=false` e riscos de linguagem ofensiva, ataque pessoal e sensibilidade jurídica. O MP4 local correspondente tem 1920×1080, H.264/AAC e duração medida de `549.449s`. O arquivo foi tratado como fonte de processamento, não como mídia versionada.

Os candidatos comparados foram os sete cortes já persistidos pelo Furia no projeto local do b354. Eles ocupavam as seguintes janelas da timeline local: `0.0–40.32s`, `96.2962–139.54s`, `308.87–331.57s`, `372.873–394.06s`, `417.083–441.741s`, `441.741–474.674s` e `514.147–539.072s`.

## Implementações

Foi criado `modules/editorial_benchmark.py`. O módulo normaliza intervalos, converte timestamps absolutos para a timeline de um MP4 de bloco quando a duração da fonte confirma o vínculo, calcula IoU, mede erro de início/fim, identifica cobertura, conta duplicatas e classifica cada divergência como `furia_better`, `campaign_hub_better` ou `both_need_review`. A classificação é diagnóstica; não aprova cortes e não altera o ranking.

Foi criado `scripts/run_editorial_benchmark.py`, um comando local que recebe a memória autorizada, o arquivo de candidatos e a fonte MP4. O relatório é salvo atomicamente em `FuriaClipsData/benchmarks`, fora do checkout. Também foram adicionadas rotas `GET/POST /api/editorial/benchmark` e `GET /api/editorial/benchmark/<id>` para consulta e persistência local.

A rota `POST /api/editorial/blocks/highlights/export` encontra um destaque pelo `block_id` e `highlight_id`, mapeia sua timeline e chama o mesmo caminho de renderização local do Furia. O painel de Blocos agora exibe os highlights de referência e oferece uma ação de exportação individual, mantendo 16:9 original como padrão.

## Destaques mapeados

| Highlight | Texto resumido | Timeline absoluta | Timeline local no MP4 |
| --- | --- | --- | --- |
| `1350` | “Nós somos um exército indestrutível.” | `6289.36–6293.36s` | `146.80–150.80s` |
| `1367` | “Nós fundamos o nosso partido para representar as nossas próprias ideias.” | `6365.80–6370.96s` | `223.24–228.40s` |
| `1426` | Esforço de 45 dias e consequências dos próximos 20 anos | `6631.04–6637.76s` | `488.48–495.20s` |

O mapeamento foi confirmado pelo benchmark e pela rota operacional de exportação. Não houve deslocamento ou extrapolação para fora dos limites do MP4.

## Resultado medido

| Métrica | Resultado |
| --- | ---: |
| Candidatos locais comparados | 7 |
| Destaques de referência | 3 |
| Destaques cobertos por um candidato | 0 |
| Recall de cobertura | 0,0000 |
| IoU médio do melhor candidato por destaque | 0,0000 |
| Erro médio de fronteira entre os melhores candidatos | 52,972 s |
| Duplicatas por IoU ≥ 0,8 | 0 |
| Classificação temporal | 3 `Campaign Hub melhor` |

O resultado mostra uma falha editorial mensurável: o Furia produziu sete cortes tecnicamente válidos, mas nenhum alcançou os três momentos destacados pelo Acervo. Isso não prova que os sete cortes sejam inúteis nem que o Acervo seja infalível. Prova apenas que a seleção local atual não recuperou essas referências no mesmo intervalo.

Os três melhores candidatos por proximidade foram o candidato 1 para o primeiro highlight, o candidato 5 para o segundo e o candidato 7 para o terceiro; todos apresentaram IoU `0,0`. O problema aparece antes do render: os limites escolhidos ficaram em regiões diferentes da timeline. O mapeamento e a exportação individual funcionaram corretamente.

## Exports individuais e validação audiovisual

Os três highlights foram exportados a partir do MP4 local pelo backend real. Todos preservaram 1920×1080, H.264, AAC e aproximadamente 30 fps (`30000/1001`). As durações medidas pelo FFprobe foram:

| Highlight | Duração solicitada | Duração medida | Resultado |
| --- | ---: | ---: | --- |
| `1350` | 4,000 s | 4,004 s | válido |
| `1367` | 5,160 s | 5,172 s | válido |
| `1426` | 6,720 s | 6,740 s | válido |

O aspecto original foi preservado. Nenhum formato 1:1 ou 9:16 foi introduzido nesta rodada.

## Validação de código e segurança

A suíte completa terminou com **327 testes aprovados**. Também passaram `compileall`, `node --check static/js/app.js` e `git diff --check`. A revisão de arquivos rastreados não encontrou mídia grande nova, banco local, cookie, chave Gemini ou credencial concreta. O identificador público do endpoint autorizado do Campaign Hub permanece apenas como referência documental já existente; não foi usado como segredo de runtime.

A memória real, o benchmark gerado, o banco SQLite, o MP4 de 549 segundos e os três exports permanecem fora do Git. O código publicado contém somente o leitor, o comparador, o comando, as rotas, a interface e os testes.

## Classificação das conclusões

| Classificação | Conclusão |
| --- | --- |
| Confirmado | Os três highlights QA-gated podem ser mapeados para a timeline local do MP4 b354. |
| Confirmado | A exportação individual funciona para cada highlight e preserva o aspecto original. |
| Confirmado | O benchmark persiste métricas e comparações sem chamada externa durante o corte. |
| Reproduzido | Os sete candidatos locais do baseline cobrem `0/3` highlights do b354. |
| Corrigido | A ausência de uma ação própria para exportar highlights individuais foi corrigida. |
| Corrigido | A comparação deixou de depender de leitura manual de logs e passou a ser um artefato JSON local. |
| Limitado | IoU e recall medem alinhamento temporal, não relevância semântica nem qualidade audiovisual completa. |
| Não verificado | Se o Garimpo consulta o Campaign Hub em tempo real ou usa outra memória intermediária. |
| Bloqueado | Download remoto seletivo por range continua dependente do provedor e de seus limites de acesso. |

## Próxima hipótese única

> **Se a geração de candidatos usar os highlights locais como sementes de proposta e expandir cada semente até a menor janela completa da transcrição, o Furia aumentará o recall temporal do b354 sem alterar o ranking, inventar locutor ou depender de download remoto.**

A próxima rodada deve implementar somente essa proposta offline-first, executar os gates de contexto, payoff, pergunta/resposta e locutor e repetir o mesmo benchmark. Download remoto por range, diarização robusta, reframe, headlines e editor pós-renderização continuam fora do escopo.

## Referências

[1]: `START_HERE.md` — contrato canônico de continuidade e prioridades do Furia Clips.  
[2]: `NEXT_CYCLE.md` — procedimento e hipótese da próxima rodada.  
[3]: `CYCLE_11_REPORT_2026-08-17.md` — primeira onda operacional da ponte Campaign Hub–Furia.  
[4]: `https://github.com/SAGIEV007/furia-clips/tree/manus/rebuild-opus-parity` — branch pública de trabalho.
