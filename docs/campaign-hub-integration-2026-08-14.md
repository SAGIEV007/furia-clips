# Integração do Campaign Hub — 14/08/2026

## Objetivo

O Furia Clips agora pode usar um snapshot autorizado do Campaign Hub como evidência histórica de hooks e performance observada, sem depender da conexão MCP durante o processamento local. A integração foi desenhada para funcionar nos dois notebooks e para continuar offline quando o arquivo persistente estiver disponível.

## O que é usado

O conector fornece cobertura separada para `@renansantosmbl`, `@renansantosreserva` e `@partidomissao`, com transcrições, métricas, tags, hooks, coortes semânticas, audiência e superfícies de busca. Nesta rodada foram consultados: cobertura de contas; top posts por views no Instagram dos dois perfis; performance agregada de tags/hooks; coorte semântica de segurança pública/crime organizado; busca semântica de transcrições; transcrições de quatro vencedores; e a superfície QA-gated do Acervo.

## Contrato de segurança editorial

As métricas do Campaign Hub são observações pós-publicação. Elas não são a fórmula privada de uma plataforma, não garantem viralização e não substituem contexto, completude, fala identificada, evidência audiovisual ou revisão factual. O adaptador exige pelo menos três observações do mesmo hook antes de construir um prior. O impacto máximo do prior no score é deliberadamente pequeno, e a origem, a conta, o hook, a amostra e a base aparecem em `campaign_hub_prior` e `review_flags`.

As contas nunca são misturadas. Razões devem ser comparadas dentro da mesma plataforma e baseline. Ausência de cobertura é tratada como desconhecida, nunca como zero. Transcrições sem verificação de áudio são material de recall e calibração, não citações automáticas.

## Arquivos

O código publicado contém `modules/campaign_hub.py`, que carrega o arquivo externo apontado por `FURIA_CAMPAIGN_HUB_SNAPSHOT` ou, por padrão, `~/FuriaClipsData/campaign_hub/profile.json`. O snapshot de dados não pertence ao checkout e não deve ser commitado. O card de revisão informa quando o histórico observado foi aplicado, sem exibir dados sensíveis nem inventar precisão.

O backup persistente contém os dados de performance e análise em `~/FuriaClipsData/analyses/`, incluindo `campaign-hub-coverage-2026-08-14.md` e `campaign-hub-performance-2026-08-14.md`. Esses arquivos devem sobreviver a substituições do checkout.

## Limitações conhecidas

A busca semântica pode recuperar transcrições ruidosas ou sociais, e a superfície QA-gated do Acervo pode não conter os Reels do Instagram. O snapshot atual é uma amostra de alto desempenho, não um censo integral nem uma regra causal. A expansão correta é continuar coletando snapshots por conta, plataforma, hook e janela temporal, sempre preservando `n`, intervalo e proveniência.
