# Quality gates do Furia Clips

## Objetivo

Um artefato só pode ser marcado como pronto quando passar por validações técnicas e editoriais compatíveis com sua etapa. O sistema deve conservar o resultado de cada gate para que o usuário saiba por que um clip foi aceito, rejeitado ou marcado para revisão.

## Gates obrigatórios

| Gate | Regra | Estado em caso de falha |
| --- | --- | --- |
| Entrada segura | Arquivo existe, está dentro do workspace permitido, não é symlink externo e respeita tamanho/MIME/extensão | Job falha antes do processamento |
| Mídia legível | `ffprobe` encontra stream de vídeo e, quando exigido, áudio | Job falha com diagnóstico |
| Timeline | Intervalo possui início menor que fim e está dentro da duração canônica | Candidato rejeitado |
| Limite de palavra | Início/fim coincidem com palavra, pausa ou decisão explícita do usuário | Candidato recebe revisão obrigatória |
| Contexto | Clip contém contexto suficiente ou a IA explica por que o contexto é deliberadamente curto | Score reduzido ou revisão |
| Duração | Clip respeita preset mínimo/máximo e tolerância do renderizador | Candidato rejeitado ou ajustado |
| Diversidade | Resultado não duplica excessivamente outro clip aprovado | Candidato removido ou penalizado |
| Renderização | Arquivo final existe, tem tamanho maior que zero e é legível | Render marcado como falho |
| Streams | Arquivo final contém vídeo e áudio conforme preset | Render marcado como falho |
| Geometria | Resolução e aspecto correspondem ao preset de plataforma | Render marcado como falho |
| Legendas | Timestamps das legendas estão na mesma timeline do vídeo final | Render marcado para revisão |
| Enquadramento | Crop não corta sujeito principal com confiança acima do limite | Render marcado para revisão |
| Score | Fatores, score, confiança e origem do motor estão registrados | Candidato não pode ser apresentado como ranqueado |
| Segurança | Logs, resposta da API e arquivos não expõem segredos | Job falha e exige correção |
| Reprodutibilidade | Configuração, versões de modelos e hash da entrada estão registrados | Artefato não pode ser usado para calibração |

## Estados de saída

`pronto` significa que todos os gates obrigatórios passaram. `revisao` significa que o arquivo é tecnicamente utilizável, mas precisa de aprovação humana por contexto, locutor, enquadramento ou legenda. `falho` significa que o artefato não deve ser entregue. `cancelado` significa que o usuário interrompeu o job antes da conclusão.

## Critério de score

O score é editorial e explicável. Ele não deve ser interpretado como garantia de alcance. Cada candidato precisa exibir fatores individuais, confiança, origem dos sinais e eventuais penalidades. Se a confiança do locutor ou do enquadramento for baixa, isso deve aparecer antes da aprovação.
