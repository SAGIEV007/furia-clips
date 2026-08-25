@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
chcp 65001 >nul
title Furia Clips - CHUB

REM ---------------------------------------------------------------------------
REM  Furia Clips - Acervo do Campaign Hub
REM
REM  CLIQUE DUAS VEZES e escolha pelo numero. O editor perguntou "como eu rodo
REM  esse chub.bat --espelho?", e a pergunta estava certa: passar argumento exige
REM  abrir um terminal, e ninguem deveria precisar de terminal para ver o que o
REM  proprio programa sabe. Quem quiser continua podendo escrever direto:
REM
REM      chub.bat --testar
REM      chub.bat --espelho
REM      chub.bat --listar
REM      chub.bat KpjvWf9SsWQ
REM      chub.bat --tudo --limite 50
REM      chub.bat --vincular "MEU VIDEO.mp4" KpjvWf9SsWQ
REM
REM  O endereco do CHUB carrega a credencial dentro dele, entao ele NAO fica
REM  guardado nesta pasta (que vai para o GitHub). Fica em
REM  %USERPROFILE%\FuriaClipsData\, junto com os outros dados locais do Furia.
REM ---------------------------------------------------------------------------

set "GUARDA=%USERPROFILE%\FuriaClipsData"
set "ARQUIVO=%GUARDA%\chub-endpoint.txt"

if not exist "%GUARDA%" mkdir "%GUARDA%" >nul 2>&1

if not exist "venv\Scripts\python.exe" (
    echo.
    echo   O ambiente do Furia ainda nao existe. Rode run.bat uma vez primeiro.
    echo.
    pause
    exit /b 1
)

REM O espelho ja vem dentro do programa e nao precisa de conexao para ser lido.
REM Perguntar o endereco antes de mostra-lo seria cobrar uma senha para abrir a
REM porta que ja esta aberta.
if /i "%~1"=="--espelho" goto :executar

if not exist "%ARQUIVO%" (
    echo.
    echo   Primeira vez. Cole o endereco do CHUB - o mesmo que voce usou
    echo   como conector, inteiro, terminando em wk_...
    echo.
    set /p ENDERECO="   endereco: "
    if "!ENDERECO!"=="" (
        echo.
        echo   Nada colado. Saindo sem gravar.
        echo.
        pause
        exit /b 2
    )
    > "%ARQUIVO%" echo !ENDERECO!
    echo.
    echo   Guardado em %ARQUIVO%
    echo   Nas proximas vezes nao vai perguntar de novo.
    echo.
)

if exist "%ARQUIVO%" set /p FURIA_CHUB_MCP_URL=<"%ARQUIVO%"

REM Com argumento, executa direto. Sem argumento, mostra o menu.
if not "%~1"=="" goto :executar

:menu
cls
echo.
echo   ================================================================
echo      FURIA CLIPS  ·  CHUB
echo   ================================================================
echo.
echo      [1]  Ver o que o Furia sabe          (espelho: ganchos, temas, nomes)
echo      [2]  Testar a conexao                (nao baixa nada)
echo      [3]  Listar os videos do Acervo
echo      [4]  Baixar os blocos de UM video    (pede o id do YouTube)
echo      [5]  Baixar os blocos de VARIOS      (pede quantos)
echo      [6]  Vincular um arquivo a um video  (quando o nome nao tem o id)
echo.
echo      [0]  Sair
echo.
set "ESCOLHA="
set /p ESCOLHA="   escolha o numero: "

if "%ESCOLHA%"=="0" exit /b 0
if "%ESCOLHA%"=="1" ( set "ARGUMENTOS=--espelho" & goto :executar )
if "%ESCOLHA%"=="2" ( set "ARGUMENTOS=--testar"  & goto :executar )
if "%ESCOLHA%"=="3" ( set "ARGUMENTOS=--listar --limite 40" & goto :executar )

if "%ESCOLHA%"=="4" (
    echo.
    echo   O id sao os 11 caracteres depois de "watch?v=" no endereco do YouTube.
    set "VIDEO="
    set /p VIDEO="   id do video: "
    if "!VIDEO!"=="" goto :menu
    set "ARGUMENTOS=!VIDEO!"
    goto :executar
)

if "%ESCOLHA%"=="5" (
    echo.
    set "QUANTOS="
    set /p QUANTOS="   quantos videos baixar (ex: 50): "
    if "!QUANTOS!"=="" set "QUANTOS=25"
    set "ARGUMENTOS=--tudo --limite !QUANTOS!"
    goto :executar
)

if "%ESCOLHA%"=="6" (
    echo.
    echo   Arraste o arquivo de video para esta janela e solte, depois de Enter.
    set "ARQ="
    set /p ARQ="   arquivo: "
    if "!ARQ!"=="" goto :menu
    echo.
    set "VIDEO="
    set /p VIDEO="   id do video no YouTube: "
    if "!VIDEO!"=="" goto :menu
    set "ARGUMENTOS=--vincular !ARQ! !VIDEO!"
    goto :executar
)

echo.
echo   Nao entendi "%ESCOLHA%". Escolha um numero da lista.
timeout /t 2 >nul
goto :menu

:executar
echo.
if "%~1"=="" (
    "venv\Scripts\python.exe" scripts\sincronizar_acervo.py !ARGUMENTOS!
) else (
    "venv\Scripts\python.exe" scripts\sincronizar_acervo.py %*
)
set CODIGO=!ERRORLEVEL!

echo.
if not "!CODIGO!"=="0" (
    echo   ----------------------------------------------------------------
    echo   Terminou com erro ^(codigo !CODIGO!^). Copie o texto acima e mande.
    echo   A chave sai mascarada como "wk_..." nas mensagens de erro, entao
    echo   pode colar sem medo.
    echo   ----------------------------------------------------------------
)
echo.

REM Chamado do menu: volta para o menu. Chamado com argumento: encerra.
if "%~1"=="" (
    pause
    goto :menu
)
pause
exit /b !CODIGO!
