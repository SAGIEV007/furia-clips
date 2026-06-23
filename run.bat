@echo off
title Furia Clips - Corte. Ranqueie. Domine.
color 0E

echo ============================================
echo    FURIA CLIPS - Corte. Ranqueie. Domine.
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado!
    echo Instale o Python em: https://www.python.org/downloads/
    echo Marque "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)

:: Check FFmpeg
ffmpeg -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [AVISO] FFmpeg nao encontrado!
    echo Instale o FFmpeg em: https://ffmpeg.org/download.html
    echo Adicione ao PATH do sistema.
    echo.
    echo Tentando continuar mesmo assim...
)

:: Define venv path
set VENV_DIR=.venv

:: Create venv if needed
if not exist "%VENV_DIR%" (
    echo [SETUP] Criando ambiente virtual...
    python -m venv "%VENV_DIR%"
)

:: Activate venv
echo [SETUP] Ativando ambiente virtual...
call "%VENV_DIR%\Scripts\activate.bat"

:: Upgrade pip
pip install --upgrade pip -q 2>nul

:: Install dependencies
echo [SETUP] Verificando dependencias...
pip install -r requirements.txt -q 2>nul

:: Start the app
echo.
echo ============================================
echo    Iniciando Furia Clips...
echo    Acesse: http://localhost:3001
echo ============================================
echo.

:: Open browser after delay
start "" cmd /c "timeout /t 3 >nul && start http://localhost:3001"

:: Run the server
python app.py

pause
