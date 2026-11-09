@echo off
setlocal
cd /d "%~dp0"
set "PY=%~dp0.venv\Scripts\python.exe"
if exist "%PY%" (
  start "" "%PY%" "%~dp0main.py"
) else (
  start "" python "%~dp0main.py"
)
