@echo off
title Hub Financeiro
echo ========================================
echo    Hub Financeiro - Iniciando...
echo ========================================
echo.

cd /d "%~dp0"

REM Definir o caminho do Python da venv
set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"

REM Verificar se a venv existe
if not exist "%VENV_PYTHON%" (
    echo Ambiente virtual nao encontrado. Criando...
    echo.
    python -m venv .venv 2>nul
    if not exist "%VENV_PYTHON%" (
        echo ERRO: Nao foi possivel criar o ambiente virtual.
        echo.
        echo Por favor, crie manualmente pelo terminal:
        echo   python -m venv .venv
        echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
)

echo Usando: %VENV_PYTHON%
echo.

echo Verificando dependencias...
"%VENV_PYTHON%" -m pip install -r requirements.txt >nul 2>&1

echo Aplicando migracoes...
"%VENV_PYTHON%" main.py migrate --run-syncdb >nul 2>&1

echo.
echo Abrindo navegador...
start "" "http://127.0.0.1:8000/"

echo.
echo Servidor rodando em http://127.0.0.1:8000/
echo Feche esta janela para parar o servidor.
echo.

"%VENV_PYTHON%" main.py runserver
if errorlevel 1 (
    echo.
    echo Ocorreu um erro ao iniciar o servidor.
    pause
)
