@echo off
setlocal
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Python environment is missing. Run setup.ps1 first.
  exit /b 1
)
"%~dp0.venv\Scripts\python.exe" "%~dp0fanboxWrite.py" --setup
exit /b %ERRORLEVEL%
