@echo off
title Sale Alert Scraper Test Suite
echo ===================================================
echo   Sale Alert Python Scraper Unit Test Suite
echo ===================================================
echo.

cd /d "%~dp0"

python -m unittest discover -s tests -p "test_*.py"

if %errorlevel% neq 0 (
    echo.
    echo Tests FAILED!
    pause
    exit /b 1
)

echo.
echo ALL TESTS PASSED SUCCESSFULLY!
pause
