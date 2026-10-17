@echo off
setlocal
set "ROOT=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { . '%ROOT%launchers\environment.ps1'; & '%ROOT%engine\.venv\Scripts\python.exe' '%ROOT%tests\layer_keys_integration.py'; exit $LASTEXITCODE }"
exit /b %ERRORLEVEL%
