@echo off
if "%~1"=="" (
  echo Drag a UTF-8 .txt script onto this file to generate offline narration.
  pause
  exit /b 1
)
powershell -NoProfile -File "%~dp0launchers\narrate-file.ps1" -InputFile "%~1"
pause
