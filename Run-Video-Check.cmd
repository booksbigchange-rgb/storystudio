@echo off
setlocal
set "ROOT=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { . '%ROOT%launchers\environment.ps1'; & '%ROOT%engine\.venv\Scripts\python.exe' '%ROOT%tests\master_video.py' --gui; exit $LASTEXITCODE }"
if errorlevel 1 (echo Video check FAILED. Read the error and report above.) else (echo Video check PASSED.)
pause
