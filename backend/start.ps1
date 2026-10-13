$ErrorActionPreference = "Stop"
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$python = "C:\Users\10953\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $python = (Get-Command python -ErrorAction Stop).Source
}
Write-Host "Checking project dependencies..."
& $python -m pip install -r backend\requirements.txt
if (-not (Test-Path node_modules)) {
    npm install
}
Write-Host "Building web application..."
npm run build
Write-Host "Starting http://127.0.0.1:8000/studio"
Set-Location -LiteralPath (Join-Path (Get-Location) "backend")
& $python api.py
