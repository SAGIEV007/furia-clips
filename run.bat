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
    echo.
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
ollama list >nul 2>&1
if errorlevel 1 (
    echo [AVISO] Ollama NAO encontrado.
    echo    Sem o Ollama, o programa usara selecao NLP basica.
    echo    Para selecao INTELIGENTE com IA, instale o Ollama:
    echo    https://ollama.com
    echo    Apos instalar, rode: ollama pull llama3.2:3b
    echo.
) else (
    echo [OK] Ollama detectado
    ollama list 2>nul | find "llama3.2" >nul 2>&1
    if errorlevel 1 (
        echo [Setup] Modelo llama3.2:3b nao encontrado. Baixando...
        echo    Isso pode demorar alguns minutos (modelo de ~2GB)
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
)
echo.

:: Create virtual environment if needed
if not exist "venv" (
    echo [Setup] Criando ambiente virtual...
    python -m venv venv
    echo [Setup] Ambiente criado!
    echo.
)

:: Activate venv
call venv\Scripts\activate.bat

:: Install/upgrade dependencies
:: Uses a version marker to detect when requirements change
set "DEPS_VERSION=v4_camadas"
if not exist "venv\.deps_%DEPS_VERSION%" (
    echo ==================================================
    echo    Instalando/atualizando dependencias...
    echo ==================================================
    echo.
    echo [Setup] Atualizando pip...
    pip install --quiet --upgrade pip

    :: Install faster-whisper (4x mais rapido que openai-whisper)
    echo [Setup] Instalando faster-whisper (transcricao rapida)...
    pip install --quiet "faster-whisper>=1.0.0"

    :: Install remaining dependencies
    echo [Setup] Instalando demais dependencias...
    pip install --quiet -r requirements.txt
    echo.

    :: Pre-download the Whisper model so first use is faster
    echo [Setup] Baixando modelo Whisper (small)...
    echo    Isso pode demorar alguns minutos na primeira vez.
    echo    Apos isso, tudo funciona 100%% OFFLINE!
    python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')" 2>nul
    if errorlevel 1 (
        echo [Setup] Tentando com openai-whisper como fallback...
        pip install --quiet openai-whisper torch torchaudio --index-url https://download.pytorch.org/whl/cpu 2>nul
        python -c "import whisper; whisper.load_model('small')" 2>nul
    )
    echo.
    echo [Setup] Instalacao completa!

    :: Clean up old markers and create new one
    del /q venv\.deps_* 2>nul
    echo. > "venv\.deps_%DEPS_VERSION%"
    echo.
    echo ==================================================
    echo    SETUP COMPLETO! Tudo pronto para uso offline.
    echo ==================================================
    echo.
)

:: Create workspace directories
if not exist "workspace\uploads" mkdir workspace\uploads
if not exist "workspace\processed" mkdir workspace\processed
if not exist "workspace\exports" mkdir workspace\exports
if not exist "workspace\thumbnails" mkdir workspace\thumbnails
if not exist "workspace\cache" mkdir workspace\cache

:: Start the server
echo ==================================================
echo    Iniciando Furia Clips...
echo ==================================================
echo.
echo [Furia Clips] Acesse: http://localhost:3001
echo [Furia Clips] Para parar: feche esta janela ou pressione Ctrl+C
echo.

:: Open browser after a short delay
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:3001"

:: Run the app
python app.py

pause
