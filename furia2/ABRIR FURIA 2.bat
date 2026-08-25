@echo off
REM ===========================================================================
REM  FURIA 2 — clique duas vezes neste arquivo e pronto.
REM
REM  Ele liga a bancada e abre sozinho no navegador. Nada para digitar.
REM  O Furia 1 continua funcionando normalmente ao mesmo tempo: um usa a porta
REM  5000 e o outro a 5001, entao os dois podem ficar abertos lado a lado.
REM ===========================================================================
title Furia 2
cd /d "%~dp0"

REM A janela do navegador sobe um segundo depois, com o servidor ja de pe.
start "" /b cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:5001/"

python app.py
if errorlevel 1 (
    echo.
    echo A bancada nao subiu. Copie o texto acima e mande.
    pause
)
