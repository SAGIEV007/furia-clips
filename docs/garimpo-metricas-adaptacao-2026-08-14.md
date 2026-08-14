# Adaptação de métricas do Criadores ao Furia Clips

**Data:** 14 de agosto de 2026
**Autor:** Manus AI

## Conclusão

É possível aproveitar parte importante do modelo público do Criadores no Furia Clips, mas não é correto afirmar que a fórmula interna do Garimpo foi reproduzida. A rota `https://criadores.missao.org.br/garimpo` e a rota de ranking redirecionam para autenticação com ID Missão. A análise realizada sem login confirmou somente os conceitos divulgados publicamente: views, variação temporal, XP, ranking, posição, estado de coleta e histórico auditável de desempenho.

O Furia Clips agora trata esses dados como **métricas observadas pós-publicação**, mantendo-as separadas do score editorial pré-publicação. Assim, um vídeo que teve alcance alto pode ensinar o sistema sobre formato e momento, mas não transforma automaticamente alcance em qualidade ou garante viralidade futura.

## Correspondência de conceitos

| Conceito público | Adaptação no Furia Clips | Limite explícito |
|---|---|---|
| Views | `views` por snapshot | Depende de dado fornecido por exportação autorizada ou anotação manual. |
| Histórico de views | Série em `performance_snapshots` | O sistema não coleta contas sem autorização. |
| Variação entre coletas | `views_delta` e `views_growth_rate` | Requer pelo menos dois snapshots do mesmo conteúdo. |
| Velocidade de alcance | `view_velocity_per_hour` | Calculada somente quando publicação e coleta possuem timestamp. |
| Curtidas, comentários, compartilhamentos e salvamentos | `engagement_rate` e `engagement_actions` | Só usa campos realmente informados; não infere retenção. |
| Ranking | `ranking_position` opcional | Armazena a posição informada, sem alegar conhecer o peso do ranking. |
| XP | `xp` opcional | Armazena o valor informado, sem reproduzir a fórmula proprietária. |
| Estado de coleta | `collection_state` | Indica observado, pendente ou outro estado fornecido pela fonte. |
| Comparação por grupo | `cohort_observed_score` | Percentil relativo apenas à coorte real fornecida; não é previsão de viralidade. |

## Como isso influencia o programa

O motor editorial continua sendo responsável pela seleção antes da publicação, usando contexto, conclusão, clareza, conflito, formato, energia e revisão humana. As métricas observadas entram como uma segunda camada: ajudam a comparar formatos 9:16, 1:1 e fake tweet depois que houver dados reais suficientes; ajudam a identificar velocidade e engajamento observado; e podem orientar o aprendizado persistente de preferência por formato.

O aprendizado de headline é conservador. Uma recomendação automática só pode ser calibrada por escolhas anteriores quando houver amostra mínima de quatro escolhas aprovadas no histórico geral. Uma escolha explícita do editor sempre vence a preferência aprendida. O sistema não reutiliza automaticamente textos privados anteriores, apenas agregados por formato.

## Endpoints locais

`POST /api/performance/snapshots` recebe um objeto ou uma lista de snapshots. Os campos principais são `content_key`, `platform`, `format_id`, `views`, `likes`, `comments`, `shares`, `saves`, `published_at`, `collected_at`, `ranking_position`, `xp`, `collection_state` e `source`.

`GET /api/performance/summary` retorna o resumo local e os snapshots recentes. O painel **Métricas observadas** no dashboard aceita JSON e exibe conteúdos, snapshots, views, engajamento informado e velocidade média.

## Segurança e privacidade

Nenhum login do Criadores foi solicitado, nenhuma conta foi conectada e nenhuma barreira foi contornada. O Furia Clips não deve coletar métricas de Instagram, YouTube ou TikTok sem autorização oficial. Os snapshots ficam no banco editorial persistente local e entram no backup; não devem ser publicados no GitHub.

## Referências

[1]: https://criadores.missao.org.br/ "Criadores · Missão — página pública"

[2]: https://criadores.missao.org.br/garimpo "Garimpo — rota protegida por autenticação"

[3]: https://criadores.missao.org.br/ranking "Ranking — rota protegida por autenticação"

[4]: https://www.instagram.com/partidomissao/p/Db3Ej-oFfU_/ "Publicação pública da Missão sobre views, XP e ranking de criadores"
