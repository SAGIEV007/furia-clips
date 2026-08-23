# Validação e Correção: Orçamento de Candidatos (2026-08-21)

## O Problema
Ao comparar o site Criadores (que exibia ~18 momentos para o vídeo de Maceió) com o pipeline do Furia Clips (que gerou apenas 4 cortes no nosso teste sintético), investigamos a causa da discrepância.

Havia dois motivos principais:
1. **Ambiente de Teste Sintético:** Nosso teste rodou com uma transcrição manual contendo apenas 3 segmentos e 5 sentenças. O motor de fallback NLP só conseguiu extrair 5 candidatos válidos dessa massa minúscula de texto, descartou 1 por sobreposição e entregou os 4 restantes. O vídeo real tem horas de fala e milhares de sentenças.
2. **Estrangulamento Prematuro no Funil:** O código do Furia Clips possuía três pontos de descarte que destruíam candidatos antes da revisão humana:
   - `clip_selector.py` cortava a lista bruta usando o limite adaptativo logo após a deduplicação.
   - `editorial_ranker.py` destruía candidatos se a pontuação de diversidade fosse muito baixa (ex: o mesmo assunto discutido várias vezes).
   - `campaign_hub_guidance.py` possuía um limite estrito de 30 sementes.

O site Criadores exibe *momentos* brutos e teses editoriais extraídas pelo Campaign Hub, não vídeos finais renderizados. O Furia Clips, por outro lado, estava matando as opções cedo demais para economizar processamento.

## A Solução
Para garantir que o Furia Clips ofereça a mesma abundância de opções que o Chub, fizemos as seguintes alterações:
- **Remoção do Teto Prematuro:** `clip_selector.py` agora não limita a quantidade de candidatos gerados pelo fallback NLP. Ele apenas repassa a lista.
- **Tolerância à Diversidade:** O ranqueador não apaga mais os candidatos repetitivos. Ele apenas diminui a pontuação deles (`viral_score`), garantindo que o editor ainda possa vê-los na tela final se quiser.
- **Aumento de Sementes do Chub:** `campaign_hub_guidance.py` agora permite até 250 sementes de destaque, em vez de 30.
- **Teto Apenas na Exportação:** O limite adaptativo (ex: 36 cortes para um vídeo longo) agora é aplicado *apenas no momento da renderização física* em `app.py`. Ou seja, o sistema ranqueia centenas de candidatos, mas só processa o vídeo dos N melhores, deixando o restante disponível nos logs para diagnóstico ou exportação futura.

## Resultado
A infraestrutura agora está destravada. Quando você rodar o Furia Clips com o vídeo completo e a chave do Gemini ativa, ele produzirá uma lista farta de candidatos (limitada apenas pela duração do vídeo), comparável aos blocos exibidos no site.
