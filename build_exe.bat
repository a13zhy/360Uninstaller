@echo off
setlocal
cd /d "%~dp0"
set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" tools\make_icon.py
"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed --name "ResidualCleaner" --icon "assets\app_icon.ico" --uac-admin --add-data "assets;assets" --distpath "dist" --workpath "build" --specpath "build" --exclude-module tkinter main.py
echo.
echo BUILD DONE: dist\ResidualCleaner.exe
pause
