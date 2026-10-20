@echo off
setlocal
set "ROOT=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { . '%ROOT%launchers\environment.ps1'; $py='%ROOT%engine\.venv\Scripts\python.exe'; & $py -m unittest discover -s '%ROOT%integrations\lemo-lite\tests' -v; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; & $py '%ROOT%tests\cartoon_keys_integration.py'; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; & $py '%ROOT%tests\cartoon_keys_gui_integration.py'; exit $LASTEXITCODE }"
exit /b %ERRORLEVEL%
