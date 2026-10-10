@echo off
setlocal
set "ROOT=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { . '%ROOT%launchers\environment.ps1'; & '%ROOT%engine\.venv\Scripts\python.exe' '%ROOT%engine\desktop_app.py' }"
if errorlevel 1 (
  echo.
  echo StoryStudio could not start. Check that the Python environment includes tkinter.
  pause
)
