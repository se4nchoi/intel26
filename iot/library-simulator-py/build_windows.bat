@echo off
setlocal
set "PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo Virtual environment not found. Run: py -m venv .venv
    exit /b 1
)

"%PYTHON%" -m PyInstaller --noconfirm --windowed --name LibrarySimulator "%~dp0main.py"
