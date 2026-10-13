@echo off
setlocal
cd /d "%~dp0backend"
set "PYTHON_EXE=C:\Users\10953\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if not exist "%PYTHON_EXE%" (
  echo Python not found: %PYTHON_EXE%
  pause
  exit /b 1
)
echo Starting SmartMerch on an automatically selected free port.
echo A separate proxy-free Edge preview window will open automatically.
echo Keep this window open while using the website.
"%PYTHON_EXE%" api.py
echo.
echo The server stopped or failed to start. Read the message above.
pause
