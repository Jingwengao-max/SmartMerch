$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

$python = $null
$installedPython = "C:\Users\10953\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if (Test-Path -LiteralPath $installedPython) {
    $python = $installedPython
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $python = (Get-Command python).Source
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $python = (Get-Command py).Source
}
if (-not $python) {
    throw "Python was not found. Install Python and try again."
}

Write-Host "[1/3] Checking Python packages..." -ForegroundColor Cyan
& $python -m pip install -r backend\requirements.txt

Write-Host "[2/3] Building web application..." -ForegroundColor Cyan
if (-not (Test-Path node_modules)) {
    npm install
}
npm run build

Write-Host "[3/3] Starting SmartMerch..." -ForegroundColor Green
Write-Host "The browser will open automatically. Close this window to stop the server."
Write-Host "A free port will be selected automatically and opened in a proxy-free preview window."
Set-Location -LiteralPath (Join-Path $PSScriptRoot "backend")
& $python api.py
