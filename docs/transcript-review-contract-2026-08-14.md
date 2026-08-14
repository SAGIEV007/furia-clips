# Contrato de revisão textual não destrutiva — 14/08/2026

## Princípio

A linha do tempo original continua sendo a fonte canônica. Um ajuste de entrada ou saída é um **rascunho persistente de revisão**, não uma substituição do arquivo de vídeo nem uma alteração irreversível do candidato. O editor deve conseguir fechar e reabrir o programa sem perder a decisão, enquanto o arquivo renderizado original permanece disponível para comparação.

## Estados

| Estado | Persistência | Significado para o editor |
| --- | --- | --- |
| `pending` | Registro do clip | Candidato ainda não revisado |
| `preview` | Somente estado da interface | Limites calculados, mas ainda não salvos como decisão |
| `adjusted` | Evento em `clip_feedback` | Entrada/saída revisadas e armazenadas como último rascunho; o vídeo original ainda não foi sobrescrito |
| `approved` | `review_status` e evento de feedback | Candidato aceito com os limites atuais; se houver ajuste, ele continua visível como revisão persistente |
| `rejected` | `review_status` e evento de feedback | Candidato recusado; o rascunho não é apagado para manter a explicação histórica |
| `needs_review` | `review_status` e evento de feedback | O editor solicitou contexto ou revisão adicional |

## Payload de ajuste

O endpoint de preview recebe `clip`, `start`, `end`, `duration`, `transcript_segments`, `snap_tolerance` e `min_duration`. O retorno normalizado contém `start`, `end`, `duration` e `boundary_adjustment`, incluindo valores solicitados, indicação de snap, fonte (`manual` ou `transcript`) e limites resultantes.

Para persistir a decisão, o frontend envia `action: "adjusted"` no endpoint do clip, junto com `adjustments` contendo o payload normalizado e uma nota opcional. O banco não altera `clips.start_time`, `clips.end_time` ou o arquivo renderizado. Em consultas posteriores, `get_clips` expõe `latest_adjustment` derivado do último evento `adjusted`, sem esconder os campos canônicos originais.

## Regras de segurança

O servidor deve rejeitar um ajuste sem clip existente, sem intervalo positivo ou fora da duração conhecida. O ajuste persistido deve ser validado pelo mesmo helper do preview, de modo que o cliente não consiga gravar um intervalo inválido apenas alterando JSON. A operação de persistência deve ser idempotente por evento do editor, mas não apagar o histórico anterior.

A interface deve distinguir **“prévia ajustada”** de **“arquivo renderizado ajustado”**. Nesta etapa, salvar a decisão não promete um novo MP4: o editor continua podendo levar o arquivo original ao CapCut, e o próximo ciclo pode acrescentar uma exportação explícita a partir do rascunho.

## Feedback e aprendizado

Um evento `adjusted` é evidência de que a seleção temporal precisava de intervenção, mas não deve ser tratado automaticamente como rejeição. A aprovação posterior pode registrar a combinação `action: "approved"` e manter o `latest_adjustment`, permitindo que o ranking futuro aprenda separadamente sobre seleção e sobre limites temporais.

## Critérios de aceite

A revisão é considerada pronta quando: o preview continua sem mutação; um ajuste válido pode ser salvo; o servidor impede intervalos inválidos; a consulta do projeto expõe o último ajuste sem substituir a linha do tempo original; a interface mostra claramente salvo versus apenas pré-visualizado; a aprovação/rejeição continua funcionando; e backup/restore inclui os eventos porque eles já pertencem ao histórico editorial persistente.
