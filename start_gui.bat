@echo off
echo Starting Password Cracking Simulator GUI...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Install requirements if needed
if exist requirements.txt (
    echo Installing requirements...
    pip install -r requirements.txt
)

REM Start the GUI
echo Launching GUI...
python gui_dashboard.py

if errorlevel 1 (
    echo.
    echo Error occurred while running the application.
    pause
)