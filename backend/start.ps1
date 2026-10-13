$ErrorActionPreference = "Stop"
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
Write-Host "正在检查并安装项目依赖……"
py -m pip install -r backend\requirements.txt
if (-not (Test-Path node_modules)) {
    npm install
}
Write-Host "正在构建前端……"
npm run build
Write-Host "正在启动，浏览器将自动打开 http://127.0.0.1:8000/studio"
Set-Location -LiteralPath (Join-Path (Get-Location) "backend")
py api.py
