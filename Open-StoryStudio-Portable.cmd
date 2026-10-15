@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launchers\open-portable.ps1" %*
