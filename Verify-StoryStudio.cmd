@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launchers\verify.ps1" %*
set "verificationExit=%ERRORLEVEL%"
if "%verificationExit%"=="0" (echo StoryStudio verification PASSED.) else (echo StoryStudio verification FAILED. Read the saved report and logs.)
pause
exit /b %verificationExit%
