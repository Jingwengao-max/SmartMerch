$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot ".env"))) {
    Write-Host "提示：可复制 .env.example 为 .env 并填写 AI_API_KEY，后端启动时会自动读取。"
}
Write-Host "正在检查并安装项目依赖……"
py -m pip install -r requirements.txt
Write-Host "启动完成后，请在浏览器打开 http://127.0.0.1:8000"
py -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
