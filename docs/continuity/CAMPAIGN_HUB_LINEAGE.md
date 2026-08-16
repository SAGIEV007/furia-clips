# Linhagem do Campaign Hub no Furia Clips

## Princípio

O Campaign Hub é a memória editorial estruturada do ecossistema Renan/MBL. No Furia Clips, ele entra como **observação e prior fraco**, nunca como autorização automática para publicar um corte.

## Fluxo atual

```text
snapshot autorizado do Campaign Hub
        ↓
modules/campaign_hub.py
  normalização de contas, hooks, ratios e amostras
        ↓
editorial_context.py
  famílias de hook, evidência textual e janelas de contexto
        ↓
editorial_ranker.py / viral_ranker.py
  prior de performance limitado e padrão Instagram limitado
        ↓
gates de contexto, payoff, pergunta/resposta, técnico e visual
        ↓
revisão humana e/ou renderização
```

O aplicativo local não chama o MCP diretamente. Ele carrega um snapshot autorizado fora do checkout, configurado por `FURIA_CAMPAIGN_HUB_SNAPSHOT`, pelo caminho persistente `~/FuriaClipsData/campaign_hub/profile.json` ou pelo pacote agregado `data/editorial_priors.json`. O adaptador aceita apenas `@renansantosmbl`, `@renansantosreserva` e `@partidomissao`.

## O que é usado

O snapshot pode fornecer observações de hook, exemplos e cohorts. O Furia classifica o texto por famílias determinísticas como `tese-provocativa`, `news-peg`, `acusacao-direta`, `revelacao-de-local`, `curiosity-gap`, `desafio-ao-espectador` e `callback`. Quando há pelo menos três observações da mesma família, o prior de performance pode produzir um sinal limitado entre 42 e 58; o ajuste máximo no score permanece deliberadamente pequeno. O padrão editorial/Instagram também é um sinal separado e limitado.

## O que não é usado como verdade

Métrica histórica não substitui transcrição, contexto, tese, payoff, locutor, evidência visual ou revisão humana. Um Reel publicado é evidência de seleção editorial, não prova absoluta de qualidade nem licença para recortar novamente o Reel. Reels continuam `reference_only`; lives longas e cruas continuam `processing_source`.

## Linhagem do lote renal

Na execução renal, alguns candidatos registraram `campaign_hub_prior_available` e `instagram_pattern_prior_available`. Isso significa que o ranker encontrou prior aplicável ao texto e ao snapshot local; não significa que o Campaign Hub aprovou o candidato. A aprovação dos dois cortes avaliados veio da revisão humana do usuário, apoiada pelo diagnóstico do Furia.

## Relação com Gemini

Gemini é um enriquecimento multimodal opcional. O lote renal que originou os três exports pós-gate foi transcrito e ranqueado sem chamada ao Gemini. O Furia funciona com faster-whisper, FFmpeg/FFprobe e regras locais quando Gemini está indisponível; a presença do Campaign Hub não depende da API Gemini.
