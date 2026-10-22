$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) { throw 'Run Setup-MedNova.ps1 first.' }
if (Test-Path -LiteralPath '.runtime/local_mysql.json') {
    & ./.venv/Scripts/python.exe tools/local_mysql.py serve
} elseif (Test-Path -LiteralPath '.env') {
    & ./.venv/Scripts/python.exe manage.py check_database
    if ($LASTEXITCODE -ne 0) { throw 'Database check failed.' }
    & ./.venv/Scripts/python.exe launch.py
} else { throw 'No private database configuration. Read OPEN_IN_VSCODE.md before configuring an existing database.' }
if ($LASTEXITCODE -ne 0) { throw 'Startup stopped. Check the error above; port 8000 may already be in use.' }
