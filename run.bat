@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Furia Clips - Corte. Ranqueie. Domine.
color 0E
cd /d "%~dp0"
chcp 65001 >nul

set "RUNTIME_DIR=%~dp0.runtime"

set "LOG_DIR=%~dp0logs"
set "RUN_LOG=%LOG_DIR%\run-latest.log"
set "PYTHON_EXE="
set "FFMPEG_DIR="
set "FFPROBE_EXE="
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
call :log "Launcher iniciado. Pasta: %~dp0"

if exist "%RUNTIME_DIR%\python_path.txt" for /f "usebackq delims=" %%P in ("%RUNTIME_DIR%\python_path.txt") do if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
if exist "%RUNTIME_DIR%\ffmpeg_path.txt" for /f "usebackq delims=" %%F in ("%RUNTIME_DIR%\ffmpeg_path.txt") do if not defined FFMPEG_DIR set "FFMPEG_DIR=%%F"
if exist "%RUNTIME_DIR%\ffprobe_path.txt" for /f "usebackq delims=" %%Q in ("%RUNTIME_DIR%\ffprobe_path.txt") do if not defined FFPROBE_EXE set "FFPROBE_EXE=%%Q"
if defined FFMPEG_DIR if not defined FFPROBE_EXE if exist "!FFMPEG_DIR!\ffprobe.exe" set "FFPROBE_EXE=!FFMPEG_DIR!\ffprobe.exe"

set "NEEDS_BOOTSTRAP=0"
if not defined PYTHON_EXE set "NEEDS_BOOTSTRAP=1"
if defined PYTHON_EXE if not exist "!PYTHON_EXE!" set "NEEDS_BOOTSTRAP=1"
if not defined FFMPEG_DIR set "NEEDS_BOOTSTRAP=1"
if not defined FFPROBE_EXE set "NEEDS_BOOTSTRAP=1"
if defined FFMPEG_DIR if not exist "!FFMPEG_DIR!\ffmpeg.exe" set "NEEDS_BOOTSTRAP=1"
if defined FFPROBE_EXE if not exist "!FFPROBE_EXE!" set "NEEDS_BOOTSTRAP=1"

if "%NEEDS_BOOTSTRAP%"=="1" (
    echo ==================================================
    echo    Primeiro uso: preparando Python e FFmpeg...
    echo ==================================================
    echo.
        call :log "Bootstrap necessario. Python=!PYTHON_EXE! FFmpeg=!FFMPEG_DIR! ffprobe=!FFPROBE_EXE!"

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0bootstrap_windows.ps1"
    set "BOOTSTRAP_CODE=!ERRORLEVEL!"
    call :log "Bootstrap terminou com codigo !BOOTSTRAP_CODE!"
    if not "!BOOTSTRAP_CODE!"=="0" goto :bootstrap_failed

        set "PYTHON_EXE="
    set "FFMPEG_DIR="
    set "FFPROBE_EXE="
    if exist "%RUNTIME_DIR%\python_path.txt" for /f "usebackq delims=" %%P in ("%RUNTIME_DIR%\python_path.txt") do if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
    if exist "%RUNTIME_DIR%\ffmpeg_path.txt" for /f "usebackq delims=" %%F in ("%RUNTIME_DIR%\ffmpeg_path.txt") do if not defined FFMPEG_DIR set "FFMPEG_DIR=%%F"
    if exist "%RUNTIME_DIR%\ffprobe_path.txt" for /f "usebackq delims=" %%Q in ("%RUNTIME_DIR%\ffprobe_path.txt") do if not defined FFPROBE_EXE set "FFPROBE_EXE=%%Q"

)

call :validate_runtime
if errorlevel 1 goto :bootstrap_failed

call :log "Verificando modelo facial opcional do MediaPipe."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\ensure_face_model.ps1" -ProjectRoot "%~dp0"
set "FACE_MODEL_CODE=!ERRORLEVEL!"
call :log "Preparação do modelo facial terminou com codigo !FACE_MODEL_CODE!"

for %%Q in ("!FFPROBE_EXE!") do set "FFPROBE_DIR=%%~dpQ"

set "PATH=!FFMPEG_DIR!;!FFPROBE_DIR!;%PATH%"

call :log "Executando setup Python: !PYTHON_EXE!"
"%PYTHON_EXE%" _setup.py
set "SETUP_CODE=!ERRORLEVEL!"
call :log "Setup terminou com codigo !SETUP_CODE!"
if not "!SETUP_CODE!"=="0" goto :setup_failed

if not exist "venv\Scripts\python.exe" (
    call :log "ERRO: venv\Scripts\python.exe nao foi criado."
    goto :setup_failed
)

set "PATH=%~dp0venv\Scripts;%PATH%"
call :log "Ambiente virtual validado. Iniciando aplicacao."

echo ==================================================
echo    Iniciando Furia Clips...
echo ==================================================
echo.
echo [Furia Clips] Acesse: http://localhost:3001
echo [Furia Clips] Para parar: feche esta janela ou Ctrl+C
echo [Furia Clips] Log do launcher: %RUN_LOG%
echo.

start "" powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0scripts\open_browser_windows.ps1" -Url "http://127.0.0.1:3001" -TimeoutSeconds 120 -LogFile "%RUN_LOG%"
"%~dp0venv\Scripts\python.exe" app.py

set "APP_CODE=!ERRORLEVEL!"
call :log "Aplicacao terminou com codigo !APP_CODE!"
if not "!APP_CODE!"=="0" goto :app_failed

call :log "Launcher encerrado normalmente."
echo.
echo ==================================================
echo    Furia Clips encerrado.
echo ==================================================
echo.
exit /b 0

:validate_runtime
if not defined PYTHON_EXE (
    call :log "ERRO: caminho Python vazio."
    exit /b 1
)
if not exist "!PYTHON_EXE!" (
    call :log "ERRO: Python nao existe no caminho: !PYTHON_EXE!"
    exit /b 1
)
if not defined FFMPEG_DIR (
    call :log "ERRO: diretorio FFmpeg vazio."
    exit /b 1
)
if not exist "!FFMPEG_DIR!\ffmpeg.exe" (
    call :log "ERRO: ffmpeg.exe nao existe em: !FFMPEG_DIR!"
    exit /b 1
)
if not defined FFPROBE_EXE (
    call :log "ERRO: caminho ffprobe vazio."
    exit /b 1
)
if not exist "!FFPROBE_EXE!" (
    call :log "ERRO: ffprobe.exe nao existe em: !FFPROBE_EXE!"
    exit /b 1
)
call :log "Runtime validado. Python=!PYTHON_EXE! FFmpeg=!FFMPEG_DIR! ffprobe=!FFPROBE_EXE!"

exit /b 0

:bootstrap_failed
echo.
echo ==================================================
echo [ERRO] Bootstrap incompleto.
echo [ERRO] Log detalhado: %LOG_DIR%\bootstrap-latest.log
echo [ERRO] Log do launcher: %RUN_LOG%
echo ==================================================
call :show_log "%LOG_DIR%\bootstrap-latest.log"
echo.
echo Envie os dois arquivos .log se precisar de diagnostico.
pause
exit /b 1

:setup_failed
echo.
echo ==================================================
echo [ERRO] Falha na instalacao das dependencias Python.
echo [ERRO] Log do launcher: %RUN_LOG%
echo ==================================================
call :show_log "%RUN_LOG%"
echo.
echo Execute run.bat novamente para tentar corrigir.
pause
exit /b 1

:app_failed
echo.
echo ==================================================
echo [ERRO] O aplicativo foi encerrado com erro.
echo [ERRO] Log do launcher: %RUN_LOG%
echo ==================================================
call :show_log "%RUN_LOG%"
pause
exit /b 1

:show_log
if not exist "%~1" exit /b 0
powershell.exe -NoProfile -Command "Get-Content -LiteralPath '%~1' -Tail 80"
exit /b 0

:log
for /f "delims=" %%T in ('powershell.exe -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH:mm:ss"') do set "LOG_TIME=%%T"
>>"%RUN_LOG%" echo [!LOG_TIME!] %~1
exit /b 0
