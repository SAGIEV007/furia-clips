@echo off
chcp 65001 >nul
title Furia Clips - Corte. Ranqueie. Domine.
color 0E

echo ══════════════════════════════════════════════════
echo    FURIA CLIPS - Corte. Ranqueie. Domine.
echo ══════════════════════════════════════════════════
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo Instale Python 3.10+ de: https://www.python.org/downloads/
    echo IMPORTANTE: Marque "Add Python to PATH" na instalacao!
    pause
    exit /b 1
)

:: Check FFmpeg
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [AVISO] FFmpeg nao encontrado no PATH.
    echo Instale de: https://ffmpeg.org/download.html
    echo Adicione ao PATH do sistema.
    echo.
    echo O programa vai iniciar mas cortes de video nao funcionarao.
    echo.
)

:: Create virtual environment if needed
if not exist "venv" (
    echo [Setup] Criando ambiente virtual...
    python -m venv venv
    echo [Setup] Ambiente criado!
    echo.
)

:: Activate venv
call venv\Scripts\activate.bat

:: Install dependencies if needed
if not exist "venv\.deps_installed" (
    echo ══════════════════════════════════════════════════
    echo    PRIMEIRO USO - Instalando dependencias...
    echo    (isso so acontece uma vez^)
    echo ══════════════════════════════════════════════════
    echo.
    echo [Setup] Instalando pacotes Python...
    pip install --quiet --upgrade pip
    pip install --quiet torch torchaudio --index-url https://download.pytorch.org/whl/cpu
    pip install --quiet -r requirements.txt
    echo.
    echo [Setup] Baixando modelo Whisper (small^)...
    echo    Isso pode demorar alguns minutos na primeira vez.
    echo    Apos isso, tudo funciona 100%% OFFLINE!
    python -c "import whisper; whisper.load_model('small')"
    echo.
    echo [Setup] Instalacao completa!
    echo. > venv\.deps_installed
    echo.
    echo ══════════════════════════════════════════════════
    echo    SETUP COMPLETO! Tudo pronto para uso offline.
    echo ══════════════════════════════════════════════════
    echo.
)

:: Start the server
echo [Furia Clips] Iniciando servidor...
echo [Furia Clips] Acesse: http://localhost:3001
echo [Furia Clips] Para parar: feche esta janela ou pressione Ctrl+C
echo.

:: Open browser after a short delay
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:3001"

:: Run the app
python app.py

pause
