@echo off
title Furia Clips - Corte. Ranqueie. Domine.
color 0E

:: Check Python exists
python --version >nul 2>&1
if errorlevel 1 goto :no_python

:: Run setup via Python (avoids CMD parsing issues)
python _setup.py
if errorlevel 1 goto :setup_failed

:: Activate venv and start app
call venv\Scripts\activate.bat

echo ==================================================
echo    Iniciando Furia Clips...
echo ==================================================
echo.
echo [Furia Clips] Acesse: http://localhost:3001
echo [Furia Clips] Para parar: feche esta janela ou Ctrl+C
echo.

:: Open browser after short delay
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:3001"

:: Run the app
python app.py

echo.
echo ==================================================
echo    Furia Clips encerrado.
echo ==================================================
echo.
pause
goto :eof

:no_python
echo.
echo [ERRO] Python nao encontrado!
echo Instale Python 3.10+ de: https://www.python.org/downloads/
echo IMPORTANTE: Marque "Add Python to PATH" na instalacao!
echo.
pause
exit /b 1

:setup_failed
echo.
echo [ERRO] Falha no setup. Verifique os erros acima.
echo.
pause
exit /b 1
