@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe goto setup
if not exist .env goto setup
.venv\Scripts\python.exe manage.py check_database
if errorlevel 1 (
 pause
 exit /b 1
)
echo MedNova is starting at http://127.0.0.1:8000
echo Keep this window open. Press Ctrl+C to stop.
.venv\Scripts\python.exe launch.py
pause
exit /b 0
:setup
echo Run SETUP_WINDOWS.cmd first.
pause
exit /b 1
