@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

REM ---------------------------------------------------------------------------
REM  Furia Clips - Acervo do Campaign Hub
REM
REM  Clique duas vezes para testar a conexao. Ou, no terminal:
REM      chub.bat --testar
REM      chub.bat --listar
REM      chub.bat --tudo --limite 50
REM      chub.bat KpjvWf9SsWQ
REM
REM  O endereco do CHUB carrega a credencial dentro dele, entao ele NAO fica
REM  guardado nesta pasta (que vai para o GitHub). Fica em
REM  %USERPROFILE%\FuriaClipsData\, junto com os outros dados locais do Furia.
REM ---------------------------------------------------------------------------

set "GUARDA=%USERPROFILE%\FuriaClipsData"
set "ARQUIVO=%GUARDA%\chub-endpoint.txt"

if not exist "%GUARDA%" mkdir "%GUARDA%" >nul 2>&1

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

set /p FURIA_CHUB_MCP_URL=<"%ARQUIVO%"

if not exist "venv\Scripts\python.exe" (
    echo.
    echo   O ambiente do Furia ainda nao existe. Rode run.bat uma vez primeiro.
    echo.
    pause
    exit /b 1
)

REM Sem argumento nenhum, o util e testar a conexao.
if "%~1"=="" (
    "venv\Scripts\python.exe" scripts\sincronizar_acervo.py --testar
) else (
    "venv\Scripts\python.exe" scripts\sincronizar_acervo.py %*
)

set CODIGO=%ERRORLEVEL%
echo.
if not "%CODIGO%"=="0" (
    echo   Terminou com erro ^(codigo %CODIGO%^). Copie o texto acima e mande.
    echo   A chave sai mascarada como "wk_..." nas mensagens de erro, entao
    echo   pode colar sem medo.
) else (
    echo   OK.
)
echo.
pause
exit /b %CODIGO%
