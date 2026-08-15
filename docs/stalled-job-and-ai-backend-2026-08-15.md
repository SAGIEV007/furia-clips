# Correção de job travado e decisão sobre backends de IA

## Diagnóstico

O log anexado mostrou dois problemas distintos. O primeiro era uma exceção de decodificação no Windows (`UnicodeDecodeError` em `cp1252`) durante a leitura da saída de um subprocesso. O segundo, mais importante para a sensação de travamento, era o fluxo de análise: depois que uma transcrição pública, manual ou local já estava disponível, o job ainda podia iniciar uma segunda análise multimodal do mesmo vídeo no Gemini. Essa segunda chamada podia fazer novo upload, aguardar processamento e atingir limite de tokens antes de retornar ao pipeline local.

O `JobManager` também podia conservar no SQLite um job em `running` quando o processo do Windows era encerrado ou quando o worker desaparecia. Ao abrir novamente o programa, esse registro antigo continuava parecendo ativo.

## Correções

O Furia agora considera a transcrição canônica suficiente para a linha do tempo. Uma nova análise multimodal posterior ficou desativada por padrão para fontes `manual`, `public_subtitles` e `whisper`. Ela só pode ser reativada explicitamente por configuração avançada, usando `gemini_manual_video_analysis` para transcrição manual ou `gemini_video_analysis_with_transcript` para as demais fontes.

Na inicialização, o gerenciador reconcilia registros antigos em `running` ou `cancel_requested`. Apenas jobs sem atualização por uma janela conservadora de 12 horas são marcados como `failed`, com o estágio `stale_recovered` e o erro `stale_job_recovered`. Jobs recentes não são interrompidos.

O tratamento de diálogos nativos já usa saída binária e decodificação tolerante, evitando que a página receba HTTP 500 por causa da página de código do Windows. As melhorias deste lote não enviam dados ao Campaign Hub.

## Gemini versus Manus

A chave Gemini é atualmente a opção mais direta para este programa porque o Furia já possui integração multimodal com a API do Gemini para receber um vídeo, analisar áudio/imagem e retornar segmentos timestampados. Uma chave do Manus não é uma substituição direta: a API do Manus é orientada a tarefas e agentes, não a uma chamada equivalente de análise de vídeo. Ela poderia futuramente orquestrar tarefas externas ou agentes, mas acrescentaria uma camada, latência e dependência de integração.

Portanto, a recomendação técnica atual é manter Gemini para a análise multimodal e usar a arquitetura local do Furia para fallback, ranking e persistência. Uma credencial do Manus só deve ser adicionada depois de definir um caso concreto de orquestração e um adaptador separado; ela não deve ser colocada no campo da chave Gemini nem publicada no repositório.

## Validação

As regressões direcionadas do `JobManager` e do fluxo de prioridade online foram aprovadas. O comportamento agora é explícito: transcrição pronta não dispara upload duplicado, e jobs abandonados não permanecem ativos indefinidamente após reiniciar o programa.

> Campaign Hub permanece exclusivamente em modo de leitura. Nenhuma credencial, mídia, transcrição privada ou dado bruto foi incluído no commit.

Autor: Manus AI
Data: 15 de agosto de 2026

## Referências

[1]: https://api.manus.ai "Manus API"
[2]: https://ai.google.dev/gemini-api/docs "Google Gemini API"
[3]: https://criadores.missao.org.br/garimpo "Garimpo — Criadores Missão"

As referências são apenas documentação e contexto técnico; nenhuma delas foi usada para enviar ou alterar dados durante esta correção.

### Sources:

- [1] [Manus API](https://api.manus.ai)
- [2] [Google Gemini API](https://ai.google.dev/gemini-api/docs)
- [3] [Garimpo — Criadores Missão](https://criadores.missao.org.br/garimpo)
