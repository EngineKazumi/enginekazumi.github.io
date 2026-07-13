@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0update_and_publish.ps1"
exit /b %ERRORLEVEL%
