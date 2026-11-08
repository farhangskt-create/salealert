@echo off
cd /d "%~dp0"
python run_due.py
exit /b %ERRORLEVEL%
