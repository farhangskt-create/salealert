@echo off
title Sale Alert Scraper Launcher
echo ===================================================
echo   Sale Alert Pakistani Deals Scraper Launcher
echo ===================================================
echo.

cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not added to PATH.
    echo Please install Python 3.9+ and try again.
    pause
    exit /b 1
)

echo [1/2] Installing required dependencies...
python -m pip install -r requirements.txt --quiet

echo.
echo [2/2] Running Sale Alert Scraper...
python main.py

echo.
echo Scraper execution completed. Output generated in 'output/' directory.
pause
