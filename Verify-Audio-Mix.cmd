@echo off
setlocal
set "ROOT=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { . '%ROOT%launchers\environment.ps1'; & '%ROOT%engine\.venv\Scripts\python.exe' '%ROOT%tests\mixed_audio_integration.py' --cartoon; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; & '%ROOT%engine\.venv\Scripts\python.exe' '%ROOT%tests\mixed_audio_gui_integration.py'; exit $LASTEXITCODE }"
exit /b %ERRORLEVEL%
