$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
Write-Host "正在检查并安装项目依赖……"
py -m pip install -r requirements.txt
Write-Host "启动完成后，请在浏览器打开 http://127.0.0.1:8000"
py -m uvicorn api:app --host 127.0.0.1 --port 8000 --reload
