# Gemini API: plano Google AI Pro e HTTP 503 — achados oficiais

## Evidências do log do usuário

O Furia Clips iniciou a análise multimodal online às 16:54:30, concluiu o upload às 16:58:02 e recebeu respostas de processamento aos 0, 30, 60 e 90 segundos. Às 17:01:03, a API retornou `HTTP 503` com a mensagem `This model is currently experiencing high demand`. O aplicativo então acionou corretamente o fallback local faster-whisper.

A captura do usuário mostra `Google AI Pro (5 TB)`, `R$ 0/mês`, com oferta por 12 meses e preço posterior de `R$ 96,99/mês`. A imagem confirma uma assinatura do produto de consumo Google AI/Google One; não comprova quota, tier ou faturamento da Gemini Developer API.

## Documentação oficial consultada

| Tema | Achado verificável | Fonte |
|---|---|---|
| Autenticação | A Gemini API exige uma API key ou chave de autorização; chaves estão associadas a projeto Google Cloud para quota e billing. | [Google — Using Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key) |
| Segurança | A chave deve ser tratada como senha; não deve ser publicada no Git nem exposta no cliente em produção. | [Google — Using Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key) |
| Preços | O Gemini Developer API possui oferta Free para começar e camadas Paid para maior volume, recursos e limites; isso é separado de uma assinatura de consumo Google AI Pro. | [Google — Gemini Developer API pricing](https://ai.google.dev/gemini-api/docs/pricing) |
| Quotas | RPM, TPM e RPD são medidos por projeto; limites variam por modelo/tier e a capacidade real pode variar. | [Google — Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) |
| Tiers | A passagem do Free para Tier 1 exige configurar e vincular billing ativo no projeto; tiers superiores dependem de histórico de pagamento. | [Google — Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) |
| 503 | A documentação recomenda exponential backoff com jitter e retry limitado para 503/5xx; não recomenda repetir indefinidamente. | [Google — Troubleshooting](https://ai.google.dev/gemini-api/docs/troubleshooting) |

## Conclusão operacional

O 503 do log é compatível com indisponibilidade/capacidade transitória do modelo, não com evidência de que o plano Google AI Pro esteja inválido. O plano pode ser bom para o aplicativo Gemini de consumo, mas não deve ser interpretado automaticamente como uma quota paga ou prioridade de capacidade para a Gemini Developer API.

A evolução recomendada para o Furia Clips é: retry online limitado com backoff e jitter; fallback imediato para análise textual/transcrição quando o vídeo multimodal falhar; seleção de um modelo Flash estável e de menor latência; e configuração separada de billing/quota no projeto da Developer API quando a operação de aproximadamente oito lives por dia exigir previsibilidade.
