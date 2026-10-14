@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File ".\start.ps1" -Quick
if errorlevel 1 (
  echo.
  echo SmartMerch failed to start. Read the message above.
  pause
)
