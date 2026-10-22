param([string]$Email = 'jayesh@gmail.com')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (Test-Path -LiteralPath '.runtime/local_mysql.json') {
    & ./.venv/Scripts/python.exe tools/local_mysql.py ensure_admin --email $Email
} else {
    & ./.venv/Scripts/python.exe manage.py ensure_admin --email $Email
}
if ($LASTEXITCODE -ne 0) { throw 'Admin provisioning stopped. Existing conflicting accounts were not changed.' }
