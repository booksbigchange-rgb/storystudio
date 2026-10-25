@echo off
setlocal
set "ROOT=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { . '%ROOT%launchers\environment.ps1'; $py='%ROOT%engine\.venv\Scripts\python.exe'; & $py '%ROOT%tests\mixed_edit_integration.py'; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; & $py '%ROOT%tests\mixed_edit_gui_integration.py'; exit $LASTEXITCODE }"
exit /b %ERRORLEVEL%
