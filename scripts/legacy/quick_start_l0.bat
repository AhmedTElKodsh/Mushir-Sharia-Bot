@echo off
REM L0 Quick Start Script for Windows
REM Run this to set up and test L0 in one go

echo ============================================================
echo L0 Quick Start - Mushir Sharia Bot
echo ============================================================
echo.

REM Check if virtual environment exists
if not exist ".venv" (
    echo [1/7] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo       Done!
) else (
    echo [1/7] Virtual environment already exists
)
echo.

REM Activate virtual environment
echo [2/7] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo       Done!
echo.

REM Install dependencies
echo [3/7] Installing dependencies...
echo       This may take 2-3 minutes on first run...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo       Done!
echo.

REM Check for .env file
if not exist ".env" (
    echo [4/7] Creating .env file...
    copy .env.example .env >nul
    echo       Done!
    echo.
    echo       IMPORTANT: Edit .env and add your API key:
    echo       - OPENAI_API_KEY=sk-...
    echo       - OR ANTHROPIC_API_KEY=sk-ant-...
    echo.
    echo       Press any key after adding your API key...
    pause >nul
) else (
    echo [4/7] .env file already exists
)
echo.

REM Verify setup
echo [5/7] Verifying setup...
python scripts\setup_l0.py
if errorlevel 1 (
    echo.
    echo ERROR: Setup verification failed
    echo Please fix the issues above and run this script again
    pause
    exit /b 1
)
echo.

REM Ingest corpus
echo [6/7] Ingesting AAOIFI corpus...
python scripts\ingest.py
if errorlevel 1 (
    echo ERROR: Ingestion failed
    pause
    exit /b 1
)
echo.

REM Run tests
echo [7/7] Running tests...
pytest -v
if errorlevel 1 (
    echo ERROR: Tests failed
    pause
    exit /b 1
)
echo.

echo ============================================================
echo SUCCESS! L0 is ready to use
echo ============================================================
echo.
echo Try a query:
echo   python -m src.chatbot.cli --query "What does AAOIFI require for murabaha cost disclosure?"
echo.
echo Or run the setup verification again:
echo   python scripts\setup_l0.py
echo.
pause
