$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

Write-Host "[1/3] 检查 Python 依赖……" -ForegroundColor Cyan
py -m pip install -r backend\requirements.txt

Write-Host "[2/3] 构建网页……" -ForegroundColor Cyan
if (-not (Test-Path node_modules)) {
    npm install
}
npm run build

Write-Host "[3/3] 启动海报工作室……" -ForegroundColor Green
Write-Host "浏览器将自动打开；关闭此窗口即可停止服务。"
Set-Location -LiteralPath (Join-Path $PSScriptRoot "backend")
py api.py
