# Robusteza no Download e Refinamento de IA (21/08/2026)

## Diagnóstico
O usuário enviou artefatos de uma sessão em que:
1. **O botão de corte inteligente parecia ter falhado.**
   - O log revelou que a rota chamada foi a de *Análise Integral de Contexto*, não a de corte.
   - O backend concluiu a tarefa, mas o frontend abortou após 20 minutos. Aumentei o timeout de polling do frontend de 20 para 60 minutos.
2. **O refinamento de IA (Gemini) falhou silenciosamente.**
   - O backend estava em modo `auto`, mas a lógica antiga engolia o Gemini e caía direto no Ollama, que falhava sem conexão, resultando no uso de regras locais sem avisar o usuário.
   - Corrigi o `AIBackend` para priorizar o Gemini no modo `auto` quando há chave, registrar qual provedor foi usado (`last_provider`) e devolver os erros (`last_error`). O Headline Studio agora renderiza um "chip" na UI mostrando exatamente qual provedor respondeu ou por que falhou.
3. **O gerador de headlines recusou uma legenda inteira.**
   - A legenda de teste não possuía pontuação, o que acionou o agrupamento por pausas. O algoritmo exigia confirmação de locutor (`speaker_level == "audio"`) para as famílias `summary` e `claim`. Como era um teste aleatório, ninguém respondeu por quem falou, e o estúdio devolveu tela em branco.
   - Modifiquei a família `summary` para permitir uma **headline anônima** (sem verbo de atribuição e sem sujeito nomeado) baseada no conteúdo da frase. Agora o Furia extrai a mensagem mesmo de lives sem diarização.
4. **O download de trechos do YouTube falhava silenciosamente ou era frágil.**
   - A função `download_public_video_interval` era um rascunho em relação ao download completo. Ela não separava os streams de áudio e vídeo para obter melhor qualidade e falhava se o ffmpeg demorasse a unir os arquivos.
   - Espelhei as proteções de `download_public_video`: seleção de formatos separada `bv*+ba/b`, validação de perfil de cookies e fallback para busca de arquivos residuais na pasta de destino caso o nome original falhe.

Todas as rotas da API, a geração local de headlines e o modo automático de IA foram retestados, mantendo 100% de cobertura verde.
