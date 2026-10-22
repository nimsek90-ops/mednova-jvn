param([switch]$ConfigureNewDatabase)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 and its Windows launcher first.' }
}
& ./.venv/Scripts/python.exe -m pip install -r requirements.lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
if ($ConfigureNewDatabase) {
    if (Test-Path -LiteralPath '.runtime/local_mysql.json') { throw 'Existing prepared database detected. Use Start-MedNova.ps1; do not reconfigure it.' }
    & ./.venv/Scripts/python.exe configure.py
    if ($LASTEXITCODE -ne 0) { throw 'Database configuration failed.' }
} else {
    Write-Host 'Dependencies ready. Existing data/configuration was preserved. See OPEN_IN_VSCODE.md for database configuration.'
}
