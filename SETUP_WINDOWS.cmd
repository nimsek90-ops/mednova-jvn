@echo off
setlocal
cd /d "%~dp0"
py -3.12 --version >nul 2>&1
if errorlevel 1 (
 echo Install Python 3.12 from python.org, then run this file again.
 pause
 exit /b 1
)
if not exist .venv\Scripts\python.exe py -3.12 -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install --upgrade "pip>=26.2"
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe configure.py
if errorlevel 1 goto failed
.venv\Scripts\python.exe manage.py collectstatic --noinput
if errorlevel 1 goto failed
.venv\Scripts\python.exe manage.py ensure_admin
if errorlevel 1 goto failed
echo Setup complete. Run START_WINDOWS.cmd to open MedNova.
pause
exit /b 0
:failed
echo Setup stopped. Read the error above. No default account password was created.
pause
exit /b 1
