# Fontes do bootstrap automático

## WinGet

A documentação oficial da Microsoft confirma que o WinGet está disponível no Windows 10 1809 ou posterior, no Windows 11 e no Windows Server 2025 como parte do App Installer. Ela documenta `winget install`, os argumentos `--silent`, `--accept-source-agreements`, `--accept-package-agreements` e `--disable-interactivity`, além de alertar que alguns instaladores podem exigir elevação do Windows.

Fonte: [Microsoft Learn — Use WinGet to install and manage applications](https://learn.microsoft.com/en-us/windows/package-manager/winget/).

## Python no Windows

A documentação oficial do Python explica que o Windows não inclui uma instalação de Python suportada pelo sistema e recomenda o Python Install Manager ou uma distribuição CPython. Também documenta a criação de ambientes virtuais com `python -m venv` e a possibilidade de instalar runtimes por mecanismos oficiais do Windows.

Fonte: [Python documentation — Using Python on Windows](https://docs.python.org/3/using/windows.html).

## FFmpeg

O site oficial do FFmpeg informa que o projeto publica o código-fonte e referencia builds executáveis para Windows, incluindo os builds de gyan.dev. O bootstrap usa o pacote WinGet `Gyan.FFmpeg` quando disponível e, como fallback, o arquivo `ffmpeg-release-essentials.zip` do endereço público de builds referenciado pelo projeto.

Fonte: [FFmpeg — Download](https://ffmpeg.org/download.html).

## Limites honestos

O bootstrap ainda depende de conexão com a internet na primeira execução, da disponibilidade do WinGet ou dos endereços oficiais de download e de eventuais permissões de instalação do Windows. Em computadores corporativos com políticas restritivas, o usuário pode precisar autorizar ou liberar os instaladores; o launcher informa a falha sem exigir uma chave Gemini.
