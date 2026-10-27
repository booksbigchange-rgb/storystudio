@echo off
setlocal
rem Usage: Install-StoryStudio-Unified-Portable.cmd -Zip "D:\path\StoryStudio-Unified-2.0.0-xxxxxxx-windows-portable.zip"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launchers\install-unified-portable.ps1" %*
exit /b %ERRORLEVEL%
