@echo off
REM Project FIGMENT - Development server startup script for Windows

setlocal enabledelayedexpansion

REM Colors and formatting (requires Windows 10+ with ANSI support)
set "BLUE=[34m"
set "GREEN=[32m"
set "RED=[31m"
set "RESET=[0m"

echo.
echo %BLUE%========================================%RESET%
echo %BLUE%Project FIGMENT - Development Setup%RESET%
echo %BLUE%========================================%RESET%
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo %BLUE%Creating virtual environment...%RESET%
    python -m venv venv
)

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo %GREEN%√ Virtual environment activated%RESET%
) else (
    echo %RED%× Could not activate virtual environment%RESET%
    exit /b 1
)

REM Install dependencies
echo %BLUE%Installing dependencies...%RESET%
pip install -r requirements.txt > nul 2>&1
echo %GREEN%√ Dependencies installed%RESET%

REM Check if .env exists
if not exist ".env" (
    echo %RED%× .env file not found%RESET%
    echo %BLUE%Creating .env from .env.example...%RESET%
    copy .env.example .env > nul
    echo %RED%⚠ Please edit .env with your credentials%RESET%
    exit /b 1
)

REM Create data directory
if not exist "data\" mkdir data

echo %GREEN%√ Setup complete!%RESET%
echo.
echo %BLUE%Starting services...%RESET%
echo %GREEN%Backend will run on http://localhost:8002%RESET%
echo %GREEN%Frontend will run on http://localhost:8501%RESET%
echo %BLUE%Press Ctrl+C to stop both services%RESET%
echo.

REM Start backend in a new window
start "FIGMENT Backend" cmd /k "python -c \"import main; import uvicorn; uvicorn.run(main.app, host='0.0.0.0', port=8002)\""

REM Wait for backend to start
timeout /t 2 /nobreak > nul

REM Start frontend (in the current window)
echo %GREEN%√ Backend started%RESET%
echo.
python -m streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0