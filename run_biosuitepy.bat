@echo off
REM ============================================================
REM  BioSuitePy - one-click launcher for Windows
REM  Double-click this file to run the app. No terminal typing needed.
REM ============================================================
cd /d "%~dp0"

REM First-time setup: install dependencies if not already installed
python -c "import PyQt6" 2>NUL
if errorlevel 1 (
    echo Installing required packages the first time... this may take a minute.
    python -m pip install -r requirements.txt
)

python main.py
pause
