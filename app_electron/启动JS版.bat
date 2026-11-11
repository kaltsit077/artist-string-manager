@echo off
cd /d "%~dp0"
set "ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/"
if not exist node_modules\electron\dist\electron.exe (
  echo 正在从 Electron 镜像安装桌面运行时…
  call npx install-electron --no
  if errorlevel 1 goto failed
)
npm start
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo 启动失败。请检查上方错误信息；日志位置：
echo %%APPDATA%%\artist-string-manager\artist-manager-startup.log
pause
exit /b 1
