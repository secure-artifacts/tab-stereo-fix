@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "%~dp0立体声修复.exe" (
  start "" "%~dp0立体声修复.exe"
  exit /b 0
)
call "%~dp0run-app.bat"
