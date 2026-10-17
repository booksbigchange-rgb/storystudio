@echo off
setlocal
set "ROOT=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { . '%ROOT%launchers\environment.ps1'; & '%ROOT%engine\.venv\Scripts\python.exe' '%ROOT%engine\studio_hub.py' %* }"
