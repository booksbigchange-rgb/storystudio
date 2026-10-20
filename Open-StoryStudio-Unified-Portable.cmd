@echo off
setlocal
rem Opens the newest installed exports\unified-portable-* build. Add -SelfTest to run its built-in check instead.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launchers\open-unified-portable.ps1" %*
exit /b %ERRORLEVEL%
