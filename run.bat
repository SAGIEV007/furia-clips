@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Furia Clips - Corte. Ranqueie. Domine.
color 0E
cd /d "%~dp0"

set "RUNTIME_DIR=%~dp0.runtime"
set "PYTHON_EXE="
set "FFMPEG_DIR="

if exist "%RUNTIME_DIR%\python_path.txt" for /f "usebackq delims=" %%P in ("%RUNTIME_DIR%\python_path.txt") do set "PYTHON_EXE=%%P"
if exist "%RUNTIME_DIR%\ffmpeg_path.txt" for /f "usebackq delims=" %%F in ("%RUNTIME_DIR%\ffmpeg_path.txt") do set "FFMPEG_DIR=%%F"

set "NEEDS_BOOTSTRAP=0"
if not defined PYTHON_EXE set "NEEDS_BOOTSTRAP=1"
if defined PYTHON_EXE if not exist "!PYTHON_EXE!" set "NEEDS_BOOTSTRAP=1"
if not defined FFMPEG_DIR set "NEEDS_BOOTSTRAP=1"
if defined FFMPEG_DIR if not exist "!FFMPEG_DIR!\ffmpeg.exe" set "NEEDS_BOOTSTRAP=1"
if defined FFMPEG_DIR if not exist "!FFMPEG_DIR!\ffprobe.exe" set "NEEDS_BOOTSTRAP=1"

if "%NEEDS_BOOTSTRAP%"=="1" (
    echo ==================================================
    echo    Primeiro uso: preparando Python e FFmpeg...
    echo ==================================================
    echo.
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0bootstrap_windows.ps1"
    if errorlevel 1 goto :bootstrap_failed

    set "PYTHON_EXE="
    set "FFMPEG_DIR="
    for /f "usebackq delims=" %%P in ("%RUNTIME_DIR%\python_path.txt") do set "PYTHON_EXE=%%P"
    for /f "usebackq delims=" %%F in ("%RUNTIME_DIR%\ffmpeg_path.txt") do set "FFMPEG_DIR=%%F"
)

if not defined PYTHON_EXE goto :bootstrap_failed
if not exist "%PYTHON_EXE%" goto :bootstrap_failed
if not defined FFMPEG_DIR goto :bootstrap_failed
if not exist "%FFMPEG_DIR%\ffmpeg.exe" goto :bootstrap_failed
if not exist "%FFMPEG_DIR%\ffprobe.exe" goto :bootstrap_failed

set "PATH=%FFMPEG_DIR%;%PATH%"

"%PYTHON_EXE%" _setup.py
if errorlevel 1 goto :setup_failed

if not exist "venv\Scripts\python.exe" goto :setup_failed

set "PATH=%~dp0venv\Scripts;%PATH%"

echo ==================================================
echo    Iniciando Furia Clips...
echo ==================================================
echo.
echo [Furia Clips] Acesse: http://localhost:3001
echo [Furia Clips] Para parar: feche esta janela ou Ctrl+C
echo.

start "" cmd /c "timeout /t 3 /nobreak >nul ^&^& start http://localhost:3001"

"%~dp0venv\Scripts\python.exe" app.py

if errorlevel 1 goto :app_failed

echo.
echo ==================================================
echo    Furia Clips encerrado.
echo ==================================================
echo.
exit /b 0

:bootstrap_failed
echo.
echo [ERRO] Nao foi possivel preparar automaticamente Python e FFmpeg.
echo Verifique a conexao com a internet e tente executar run.bat novamente.
echo.
pause
exit /b 1

:setup_failed
echo.
echo [ERRO] Falha na instalacao das dependencias Python.
echo Os detalhes aparecem acima; execute run.bat novamente para tentar corrigir.
echo.
pause
exit /b 1

:app_failed
echo.
echo [ERRO] O aplicativo foi encerrado com erro.
echo.
pause
exit /b 1
