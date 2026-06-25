@echo off
title Furia Clips - Corte. Ranqueie. Domine.
color 0E

echo ==================================================
echo    FURIA CLIPS - Corte. Ranqueie. Domine.
echo ==================================================
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
echo [OK] Python encontrado

:: Check FFmpeg
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [AVISO] FFmpeg nao encontrado no PATH.
    echo Instale de: https://ffmpeg.org/download.html
    echo O programa vai iniciar mas cortes nao funcionarao.
    echo.
) else (
    echo [OK] FFmpeg encontrado
)

:: Check Ollama
echo.
echo --------------------------------------------------
echo    Verificando Ollama (IA local)...
echo --------------------------------------------------

set "OLLAMA_OK=0"
ollama list >nul 2>&1
if not errorlevel 1 set "OLLAMA_OK=1"

if "%OLLAMA_OK%"=="0" (
    echo [AVISO] Ollama NAO encontrado.
    echo    Sem o Ollama, o programa usara selecao NLP basica.
    echo    Para selecao INTELIGENTE com IA, instale o Ollama:
    echo    https://ollama.com
    echo    Apos instalar, rode: ollama pull llama3.2:3b
    echo.
    goto :after_ollama
)

echo [OK] Ollama detectado
ollama list 2>nul | find "llama3.2" >nul 2>&1
if not errorlevel 1 (
    echo [OK] Modelo llama3.2:3b disponivel
    goto :after_ollama
)

echo [Setup] Modelo llama3.2:3b nao encontrado. Baixando...
echo    Isso pode demorar alguns minutos - modelo de ~2GB
call ollama pull llama3.2:3b
if not errorlevel 1 (
    echo [OK] Modelo llama3.2:3b instalado com sucesso!
) else (
    echo [AVISO] Nao foi possivel baixar o modelo.
    echo    Tente manualmente: ollama pull llama3.2:3b
)

:after_ollama
echo.

:: Create virtual environment if needed
if exist "venv\Scripts\activate.bat" goto :activate_venv
echo [Setup] Criando ambiente virtual...
python -m venv venv
if errorlevel 1 (
    echo [ERRO] Falha ao criar ambiente virtual.
    pause
    exit /b 1
)
echo [Setup] Ambiente criado!
echo.

:activate_venv
call venv\Scripts\activate.bat

:: Check if deps are installed
set "DEPS_VERSION=v4_camadas"
if exist "venv\.deps_%DEPS_VERSION%" goto :start_app

echo ==================================================
echo    Instalando/atualizando dependencias...
echo ==================================================
echo.
echo [Setup] Atualizando pip...
pip install --quiet --upgrade pip

echo [Setup] Instalando faster-whisper...
pip install --quiet faster-whisper
if errorlevel 1 echo [AVISO] faster-whisper pode ter falhado

echo [Setup] Instalando demais dependencias...
pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo [AVISO] Algumas dependencias falharam. Tentando individualmente...
    pip install flask flask-socketio gevent gevent-websocket --quiet
    pip install numpy scipy Pillow requests pydub python-dotenv --quiet
    pip install mediapipe --quiet
    pip install ffmpeg-python --quiet
)
echo.

echo [Setup] Baixando modelo Whisper (small)...
echo    Pode demorar na primeira vez.
echo    Depois disso tudo funciona OFFLINE!
python -c "from faster_whisper import WhisperModel; m=WhisperModel('small', device='cpu', compute_type='int8')" 2>nul
if errorlevel 1 (
    echo [AVISO] faster-whisper falhou, tentando openai-whisper...
    pip install --quiet openai-whisper 2>nul
)
echo.
echo [Setup] Instalacao completa!

:: Mark deps installed
del /q "venv\.deps_v*" 2>nul
type nul > "venv\.deps_%DEPS_VERSION%"
echo.
echo ==================================================
echo    SETUP COMPLETO! Tudo pronto para uso offline.
echo ==================================================
echo.

:start_app
:: Create workspace directories
if not exist "workspace\uploads" mkdir "workspace\uploads"
if not exist "workspace\processed" mkdir "workspace\processed"
if not exist "workspace\exports" mkdir "workspace\exports"
if not exist "workspace\thumbnails" mkdir "workspace\thumbnails"
if not exist "workspace\cache" mkdir "workspace\cache"

:: Start the server
echo ==================================================
echo    Iniciando Furia Clips...
echo ==================================================
echo.
echo [Furia Clips] Acesse: http://localhost:3001
echo [Furia Clips] Para parar: feche esta janela ou Ctrl+C
echo.

:: Open browser after a short delay
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:3001"

:: Run the app
python app.py

:: If we get here, python exited
echo.
echo ==================================================
echo    Furia Clips encerrado.
echo ==================================================
echo.
pause
