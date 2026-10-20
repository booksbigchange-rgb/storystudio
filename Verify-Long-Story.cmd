@echo off
setlocal
set "ROOT=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { . '%ROOT%launchers\environment.ps1'; $py='%ROOT%engine\.venv\Scripts\python.exe'; & $py '%ROOT%tests\mixed_endurance_integration.py' --sections 40; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; & $py '%ROOT%tests\mixed_long_gui_integration.py'; exit $LASTEXITCODE }"
exit /b %ERRORLEVEL%
