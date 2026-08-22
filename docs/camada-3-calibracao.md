# Camada 3 — calibração editorial do Furia Clips

## Objetivo

A Camada 3 transforma decisões reais do editor em **observabilidade e priors agregados**, sem fazer fine-tuning automático, sem inventar um dataset de 3.000 cortes e sem alterar o Campaign Hub. O modo genérico continua sendo o padrão seguro de favorabilidade.

## O que já existia

A Camada 2 já fornecia favorabilidade bounded, coice pergunta–resposta revisável, seeds temporais do Acervo com revisão obrigatória, Headline Studio 2.0 e um importador local básico. Esses comportamentos foram preservados.

## O que esta camada acrescenta

O importador agora aceita CSV, JSON, JSONL, itens JSON inline e upload multipart. Ele exige `clip_id`, `label` e `duration_sec` quando operado em modo estrito, normaliza labels, rejeita linhas inválidas com motivo e deduplica por `clip_id` usando a última ocorrência. Somente features bounded e a forma estatística da headline são gravadas em `~/FuriaClipsData/learning`; transcript, headline bruta, URL, path, token, cookie e mídia são descartados.

`GET /api/editorial/learning` devolve somente agregados: amostras, duração, família, formato, padrão de abertura, ponte QA, motivos de rejeição, limites do Headline Studio e diferenças de fatores. `POST /api/editorial/learning/import` devolve `accepted`, `rejected_rows`, `errors`, tamanhos de amostra, `priors_updated` e `store_path_hint`.

Cada chamada de `/api/batch/rank` recebe ou gera um `run_id`, registra `favorability_mode`, `ai_backend` e `seeds_enabled`, e grava um artefato sanitizado em `~/FuriaClipsData/analyses/ab-runs/`. Também existe `POST /api/editorial/runs/export` para exportação explícita e `GET /api/editorial/runs/<run_id>/export?format=json|csv` para leitura do resultado.

## Protocolo A/B

Use a mesma fonte, transcrição, backend, limites de duração, `max_clips` e configuração de seeds em três runs: `off`, `prioritize` e `require`. O editor preenche `templates/ab_metrics_template.csv` após revisar os três lotes. Não altere o default com base em uma única live; a mudança de peso só deve ser considerada após duas fontes e métricas comparáveis.

> `prioritize` é uma prioridade revisável. `require` é um gate estrito opt-in. Nenhum dos dois substitui contexto, payoff, locutor, evidência técnica ou revisão humana.

## Dados ainda pendentes

O Furia não recebeu automaticamente os cerca de 3.000 cortes reais. Para ativar uma amostra de aprendizagem, o editor deve preencher `templates/learning_import_template.csv` ou `templates/learning_import_template.jsonl` com 50–150 decisões reais, mantendo o arquivo fora do Git. Depois, o editor deve revisar duas lives e preencher a planilha A/B.

## Segurança e escopo

Campaign Hub/Chub permanece somente leitura. A camada não cria detector final de risada, cavalo, berrante ou objetos, não baixa milhares de vídeos e não publica nada no GitHub. Sinais visuais, acústicos e multimodais continuam evidências auxiliares revisáveis.
