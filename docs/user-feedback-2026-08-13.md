# Diagnóstico da execução e requisitos — 2026-08-13

## Problemas observados nos anexos

O launcher encontra Python 3.12 e FFmpeg/ffprobe corretamente. O erro de pip aparece ao executar `venv\\Scripts\\pip.exe install --upgrade pip`; versões recentes do pip no Windows exigem a chamada `venv\\Scripts\\python.exe -m pip install --upgrade pip` para atualizar o próprio pip. A instalação não abortou porque o setup ignorou o retorno dessa etapa, mas o console ficou com um erro enganoso.

O launcher atual agenda `start http://localhost:3001` três segundos antes de iniciar o Flask. Isso é frágil: o navegador pode abrir antes da porta estar pronta, pode respeitar uma associação diferente do Opera GX e pode não gerar uma nova aba quando uma instância existente não recebe o comando como esperado. A correção deve esperar uma resposta HTTP 200 e usar `Start-Process` ou detecção explícita do Opera GX, com fallback ao navegador padrão.

A aplicação abre corretamente quando o usuário acessa manualmente `http://127.0.0.1:3001`, conforme os logs HTTP 200. O problema está na automação do launcher, não na rota principal do Flask.

O frontend atualmente importa mídia por `input type=file` e configura a pasta de saída por um campo/modal de texto. O backend já possui criação de pasta dentro do workspace e abertura da pasta de exports, mas não possui um endpoint de diálogo nativo para escolher uma pasta arbitrária ou um arquivo de transcrição. Esse é o ponto correto para acrescentar uma ponte local controlada: Tkinter/PowerShell no Windows e fallback para o workspace nos demais sistemas.

## Requisitos editoriais confirmados

O perfil político deve ser padrão, não uma opção que o usuário precise repetir. O campo de contexto deve permanecer, mas como instrução adicional opcional para casos específicos. Antes de selecionar cortes, o sistema deve gerar ou receber uma transcrição segmentada e uma descrição global do vídeo; a seleção deve usar ambas.

Para entrevistas, o alvo editorial é o Renan Santos. O pipeline deve identificar quem é o Renan, distinguir pergunta e resposta, preservar a pergunta quando ela for necessária para a resposta, expandir o início e o fim até o raciocínio ficar autossuficiente e penalizar respostas isoladas ou falas sem locutor identificável.

O vídeo pode ter mais de duas horas, mas a entrevista relevante pode durar cerca de quarenta minutos. O sistema deve permitir marcar um intervalo de interesse, detectar blocos de conversa e evitar enviar repetidamente o vídeo inteiro ao modelo. A transcrição externa fornecida pelo usuário segue o padrão Tactiq: uma linha de timestamp seguida pelo texto; esse formato deve ser importável diretamente.

Gemini online é uma opção viável para a primeira versão multimodal, especialmente para inspeção global e validação de candidatos. Ainda assim, a ferramenta deve guardar uma rota offline: transcrição local opcional, análise determinística e fila de revisão. A análise de tom, sobreposição de fala e troca de locutor deve ser tratada como sinal de apoio, não como verdade absoluta; VAD/energia/pausas e diarização local devem complementar o Gemini quando disponíveis.
