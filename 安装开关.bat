@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在给插件安装本机开关服务…
"D:\WKLZHONYING\python\3.10.11\python.exe" desktop\native_host.py --register
if errorlevel 1 (
  echo 安装失败。请确认已安装 Python。
  pause
  exit /b 1
)
echo.
echo 装好了。请到 chrome://extensions 重新加载「浏览器立体声修复」，
echo 然后用插件开关。打开/关闭会重启当前这个浏览器用户，
echo VoiceMeeter / AUX / CABLE / Line 1 的系统默认设置不会改。
pause
