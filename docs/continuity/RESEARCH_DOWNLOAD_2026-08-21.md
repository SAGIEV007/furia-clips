# Pesquisa técnica: downloads, cookies e intervalos
Data: 21/08/2026

## Evidências consultadas
A documentação oficial do yt-dlp descreve seleção de formatos com vídeo e áudio separados e recomenda FFmpeg para mesclar os streams. O projeto também recomenda manter o yt-dlp atualizado, porque mudanças frequentes nos sites podem quebrar versões antigas. [1]

A FAQ oficial do yt-dlp explica que o download e a reprodução de URLs extraídas podem depender do mesmo IP, cookies e User-Agent. Para YouTube, recomenda `--cookies-from-browser` ou arquivo de cookies Netscape/Mozilla, sem expor esse arquivo. A mesma FAQ registra que respostas 429 normalmente indicam bloqueio temporário por excesso de requisições e que o 403 pode exigir cookies recém-atualizados, User-Agent atual e a mesma origem de rede. [2]

A FAQ também deixa explícito que cortes sem reencodificação não são frame-accurate; para cortes precisos, `--force-keyframes-at-cuts` força reencodificação e tem custo de tempo. Portanto, o Furia deve distinguir entre download seletivo rápido e exportação editorial frame-accurate. [2]

## Diagnóstico do caso do usuário
O log mostrou duas falhas diferentes na importação da URL:

1. O aplicativo tentou usar `cookies-from-browser=opera`, mas o perfil configurado não existia no caminho Windows informado: `C:\Users\nandi\AppData\Roaming\Opera Software\Opera Stable`. Isso é erro de configuração de perfil, não de credencial.
2. Na segunda tentativa, sem conseguir usar esse banco de cookies, o stream foi recusado pelo YouTube com HTTP 403 depois dos metadados. O próprio yt-dlp orienta usar cookies recentes do navegador e User-Agent correspondente quando a fonte exige autenticação ou há bloqueio por fingerprint.

A implementação deve, portanto, validar o perfil antes de iniciar várias tentativas, detectar caminhos Windows inexistentes, apresentar uma mensagem acionável e não repetir cegamente o mesmo método. Também deve manter fallback sem cookies quando a fonte pública permitir, e preservar o caminho local como opção segura.

## Decisões para o Furia

| Decisão | Motivo | Critério de aceite |
|---|---|---|
| Não prometer que qualquer vídeo do YouTube sempre baixará | 403/429 são bloqueios do servidor, fora do controle do aplicativo | UI distingue `metadata_ok`, `stream_denied`, `cookie_profile_missing` e `network_blocked` |
| Melhor qualidade deve significar melhor combinação de vídeo+áudio disponível até o limite escolhido | YouTube normalmente separa streams de alta qualidade | O arquivo final possui stream de vídeo e áudio e a altura efetiva é reportada |
| Download de trecho deve ser separado de corte editorial | `download_ranges` pode ser rápido e dependente de keyframes | O sistema reporta se o trecho foi reencodado/ajustado e valida duração |
| Cookies devem ser locais e nunca persistidos em código | São credenciais sensíveis | Nenhum token/cookie aparece em log, commit ou resposta JSON |
| Tentativas devem variar estratégia e parar quando a causa é configuração | Repetições idênticas não corrigem banco ausente | Máximo de tentativas por estratégia, diagnóstico por estratégia e fallback explícito |

## Referências
[1]: https://github.com/yt-dlp/yt-dlp — yt-dlp: README, instalação, dependências e seleção de formatos.
[2]: https://github.com/yt-dlp/yt-dlp/wiki/FAQ — yt-dlp FAQ: cookies, User-Agent, 403/429 e cortes por intervalo.
[3]: https://ffmpeg.org/ffmpeg.html — FFmpeg documentation: accurate seeking e opções de transcodificação.
