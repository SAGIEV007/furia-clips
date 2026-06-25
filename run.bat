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
    echo Adicione ao PATH do sistema.
    echo O programa vai iniciar mas cortes de video nao funcionarao.
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

:: Check if model is available (flat structure - no nesting)
ollama list 2>nul | find "llama3.2" >nul 2>&1
if errorlevel 1 (
    echo [Setup] Modelo llama3.2:3b nao encontrado. Baixando...
    echo    Isso pode demorar alguns minutos - modelo de ~2GB
    call ollama pull llama3.2:3b
    if errorlevel 1 (
        echo [AVISO] Nao foi possivel baixar o modelo.
        echo    Tente manualmente: ollama pull llama3.2:3b
    ) else (
        echo [OK] Modelo llama3.2:3b instalado com sucesso!
    )
) else (
    echo [OK] Modelo llama3.2:3b disponivel
)

:after_ollama
echo.

:: Create virtual environment if needed
if not exist "venv" (
    echo [Setup] Criando ambiente virtual...
    python -m venv venv
    if errorlevel 1 (
        echo [ERRO] Falha ao criar ambiente virtual.
        echo Tente: python -m pip install --user virtualenv
        pause
        exit /b 1
    )
    echo [Setup] Ambiente criado!
    echo.
)

:: Activate venv
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERRO] Falha ao ativar ambiente virtual.
    pause
    exit /b 1
)

:: Install/upgrade dependencies
set "DEPS_VERSION=v4_camadas"
if not exist "venv\.deps_%DEPS_VERSION%" (
    echo ==================================================
    echo    Instalando/atualizando dependencias...
    echo ==================================================
    echo.
    echo [Setup] Atualizando pip...
    pip install --quiet --upgrade pip

    echo [Setup] Instalando faster-whisper (transcricao rapida)...
    pip install --quiet "faster-whisper>=1.0.0"

    echo [Setup] Instalando demais dependencias...
    pip install --quiet -r requirements.txt
    if errorlevel 1 (
        echo [AVISO] Algumas dependencias podem ter falhado.
        echo    Tentando instalar individualmente...
        pip install flask flask-socketio gevent gevent-websocket --quiet
        pip install numpy scipy Pillow requests pydub --quiet
        pip install mediapipe scenedetect[opencv] --quiet
    )
    echo.

    echo [Setup] Baixando modelo Whisper (small)...
    echo    Isso pode demorar na primeira vez.
    echo    Apos isso, tudo funciona 100%% OFFLINE!
    python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')" 2>nul
    if errorlevel 1 (
        echo [Setup] Tentando com openai-whisper como fallback...
        pip install --quiet openai-whisper 2>nul
    )
    echo.
    echo [Setup] Instalacao completa!

    :: Mark deps as installed
    del /q "venv\.deps_v*" 2>nul
    type nul > "venv\.deps_%DEPS_VERSION%"
    echo.
    echo ==================================================
    echo    SETUP COMPLETO! Tudo pronto para uso offline.
    echo ==================================================
    echo.
)

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
echo [Furia Clips] Para parar: feche esta janela ou pressione Ctrl+C
echo.

:: Open browser after a short delay
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:3001"

:: Run the app
python app.py

:: If we get here, python exited (error or Ctrl+C)
echo.
echo ==================================================
echo    Furia Clips encerrado.
echo ==================================================
echo.
pause
