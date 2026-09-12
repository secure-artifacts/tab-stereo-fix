@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PYTHON="
if exist "config\python.exe.path" (
  set /p PYTHON=<"config\python.exe.path"
)
if defined PYTHON if exist "%PYTHON%" goto :run

if exist "D:\WKLZHONYING\python\3.10.11\python.exe" (
  set "PYTHON=D:\WKLZHONYING\python\3.10.11\python.exe"
  goto :save
)
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
  set "PYTHON=%LocalAppData%\Programs\Python\Python311\python.exe"
  goto :save
)
if exist "%LocalAppData%\Programs\Python\Python310\python.exe" (
  set "PYTHON=%LocalAppData%\Programs\Python\Python310\python.exe"
  goto :save
)

for /f "delims=" %%I in ('where python 2^>nul') do (
  echo %%I | find /i "\WindowsApps\" >nul
  if errorlevel 1 (
    set "PYTHON=%%I"
    goto :save
  )
)

where py >nul 2>nul
if not errorlevel 1 (
  for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do (
    echo %%I | find /i "\WindowsApps\" >nul
    if errorlevel 1 (
      set "PYTHON=%%I"
      goto :save
    )
  )
)

echo 没有找到可用的 Python 3。请安装 Python，或把 python.exe 路径写到 config\python.exe.path
pause
exit /b 1

:save
if not exist "config" mkdir "config"
> "config\python.exe.path" echo %PYTHON%

:run
"%PYTHON%" -m desktop.app %*
if errorlevel 1 (
  echo.
  echo 启动失败。
  if exist "config\last-error.txt" type "config\last-error.txt"
  pause
)
