# Relatório do ciclo 6 — Furia Clips

**Data:** 16 de agosto de 2026
**Versão candidata:** 1.6
**Branch:** `manus/rebuild-opus-parity`
**Escopo:** detecção conservadora de pré-roll/propaganda antes da seleção editorial de cortes do Renan Santos/MBL.

## Resumo executivo

O ciclo testou uma única hipótese: **uma live longa que contém propaganda ou intro antes do conteúdo editorial não deve produzir cortes iniciados dentro desse material promocional**. A alteração foi implementada no novo módulo `modules/source_boundary.py` e integrada ao pipeline para manter a transcrição integral arquivada, mas entregar à análise de contexto, seleção e ranking somente a parte da timeline que começa na fronteira segura.

A hipótese foi confirmada na amostra renal de 15 minutos. O detector localizou a abertura inequívoca da live em **169,5 segundos**, depois de uma saudação promocional ambígua. No baseline do projeto 42, um dos três exports começava em **66,0333 segundos**, atravessava o pré-roll e terminava em **215,29 segundos**; esse arquivo correspondia ao material promocional que o usuário identificou como já existente e que não deveria ser contado como novo corte editorial. Na repetição final do projeto 47, foram gerados quatro exports e **nenhum começou antes de 169,5 segundos**.

A mudança não usou Gemini, não usa Reels publicados como fontes operacionais e não adiciona arquivos de mídia ao Git. A suíte completa passou com **299 testes**, e os quatro exports finais foram validados por FFprobe como H.264/AAC, 1920×1080.

## Hipótese, baseline e critério de sucesso

A fronteira de pré-roll é um problema anterior ao ranking: um hook forte dentro de uma propaganda não deve competir com cortes editoriais da live. O critério de sucesso foi temporal e verificável: o benchmark final deveria eliminar candidatos cujo início estivesse antes da fronteira detectada, sem alterar artificialmente uma coletiva ou uma live que não apresentasse evidência forte de pré-roll.

| Medida | Baseline — projeto 42 | Após a melhoria — projeto 47 | Resultado |
| --- | ---: | ---: | --- |
| Fonte | Amostra renal de 15 min | Mesma mídia, nome distinto para evitar deduplicação | Comparável |
| Fronteira segura | Não aplicada | 169,5 s; confiança 0,90 | Detectada |
| Exports | 3 | 4 | Aumento não é o objetivo isolado |
| Exports iniciados antes de 169,5 s | 1 | 0 | **Falha eliminada** |
| Material promocional reutilizado | Presente no export `1. se não ser na rua, porque pode ser.mp4` | Ausente da seleção | **Corrigido** |
| Validação dos exports | Não usada como critério desta comparação | H.264/AAC 1920×1080, FFprobe | Aprovado |

O aumento de três para quatro exports não representa uma piora: o baseline continha um arquivo promocional longo que atravessava a fronteira, enquanto a nova seleção passou a poder escolher o bloco real de abertura e os demais blocos editoriais sem contaminar a timeline. A comparação correta é a eliminação do overlap promocional, não a maximização do número bruto de arquivos.

## Implementação

O detector recebe segmentos timestampados e a duração da fonte. Ele procura candidatos de abertura somente depois de uma margem mínima de 45 segundos, identifica sinais de saudação e abertura, e privilegia uma abertura forte, como `sejam bem-vindos` combinada com uma expressão que indique a live ou o programa. No caso renal, o primeiro sinal promocional apareceu por volta de 118 segundos; a fronteira escolhida foi a abertura em 169,5 segundos: “Sejam bem-vindos ao último análise de renais da história”.

A integração separa dois escopos. `full_transcription` continua disponível para arquivo, auditoria e futura inspeção; `selection_transcription` recebe `selection_scope=live_content` e só alimenta contexto, geração de candidatos, ranking e auditoria de headline. O pré-roll não é apagado do disco nem da transcrição, apenas impedido de entrar silenciosamente na seleção editorial.

A regra foi endurecida depois do primeiro benchmark: **“boa noite a todos” isolado não confirma uma fronteira**. Quando a evidência é insuficiente, a aplicação não corta automaticamente a timeline. Essa escolha segue o princípio de preferir revisão segura a um falso positivo que remova conteúdo válido da live.

## Validação em mídia real

A fonte operacional foi a amostra `workspace/calibration_sources/ultimo-analises-renais-15m.mp4`, com aproximadamente 900 segundos. A execução final usou o hardlink `ultimo-analises-renais-15m-boundary-v2.mp4` apenas para impedir que a deduplicação de fonte reaproveitasse um projeto anterior. O projeto final foi o **47**.

| Export final | Início | Fim | Duração do trecho | Score | Diagnóstico |
| --- | ---: | ---: | ---: | ---: | --- |
| `As pessoas querem vingança...` | 636,42 s | 687,62 s | 51,20 s | 78 | Candidato aprovado anteriormente pelo usuário |
| `Sejam bem-vindos ao último análise...` | 169,50 s | 215,29 s | 45,79 s | 76 | Abertura real da live, exatamente na fronteira |
| `Ah, mas é o aluno que ameaçou você` | 523,08 s | 590,98 s | 67,90 s | 74 | Candidato aprovado anteriormente pelo usuário |
| `é um dos raros momentos...` | 489,24 s | 523,08 s | 33,84 s | 73 | Bloco editorial posterior à fronteira |

Os quatro arquivos finais possuem stream de vídeo `h264` 1920×1080 e stream de áudio `aac`. As durações reportadas pelo FFprobe foram, respectivamente, 52,3 s, 46,9 s, 69,0 s e 34,97 s. O fato de o arquivo iniciado em 169,5 s existir não é uma falha do gate: ele começa na própria abertura forte identificada como conteúdo da live, não dentro da propaganda.

## Regressões e suíte

Foram adicionados seis testes focados ao módulo de fronteira. Eles cobrem a detecção da abertura renal, a preferência pela abertura forte após um sinal promocional ambíguo, a ausência de fronteira em uma coletiva, o comportamento de uma saudação normal no início da fonte, a rejeição de uma saudação genérica isolada e o limite seguro de uma fronteira manual.

A suíte completa foi executada com `PYTHONPATH=. python3 -m pytest -q` e terminou com **299 passed em 7,14 segundos**. A execução específica do módulo terminou com **6 passed**. O benchmark final integrado completou o job `6bfb837e-487c-4b51-b72e-9fb331537ce5` com estado `completed` e quatro artefatos de corte.

## O que foi confirmado, corrigido e não foi verificado

| Classificação | Resultado |
| --- | --- |
| Confirmado | A live renal teve fronteira detectada em 169,5 s; nenhum export final começou antes dela; coletiva sem intro não recebeu fronteira artificial; saudação isolada não causa corte automático. |
| Corrigido | O candidato promocional iniciado em 66,0333 s deixou de entrar na seleção editorial do benchmark final. |
| Confirmado | O resultado foi obtido com Whisper/NLP local e FFmpeg/FFprobe; Gemini não foi necessário. |
| Não verificado | A qualidade semântica de cada palavra da transcrição não foi recalibrada neste ciclo; isso pertence à hipótese de ASR do próximo ciclo. |
| Limitação | `source_boundary` ainda não é uma coluna própria da tabela `projects`; o diagnóstico é emitido no fluxo de seleção e preservado nos artefatos de benchmark, mas não reaparece como campo dedicado na API de projeto. |
| Bloqueado | Não houve nova aquisição de live longa pelo YouTube/Criadores nesta rodada; a fonte renal já existente foi suficiente para o benchmark comparável. |

## Decisão editorial

A alteração é aprovada para publicação como versão 1.6. Ela remove uma classe concreta de falso candidato — propaganda tratada como live — sem transformar qualquer saudação em fronteira automática. A seleção continua subordinada aos gates de contexto, payoff, pergunta/resposta e revisão técnica; o pré-roll agora é mais uma fronteira anterior à análise editorial.

O Campaign Hub permanece no papel definido anteriormente: memória estruturada e prior fraco para padrões do Renan/MBL, nunca autorização automática. Os dois clips avaliados pelo usuário continuam sendo evidência de aprovação humana, não uma aprovação do Campaign Hub. Nenhum Reel publicado foi recortado novamente.

## Próxima hipótese única

A próxima rodada deve detectar **erros semânticos de ASR em nomes próprios, entidades políticas e termos raros antes da geração de headlines**. O sistema deverá marcar baixa confiança lexical para revisão humana, comparar os candidatos reais da coletiva e da live renal com uma fonte corrigida quando disponível, e impedir headline definitiva baseada somente em uma palavra suspeita. O gate de contexto, o gate técnico e o gate de pré-roll devem permanecer ativos; não misturar essa hipótese com o Estúdio de Texto de Arte, pesos visuais ou novos presets.
