@echo off
set "APP=%~dp0release-js-dropdown\artist-string-manager-win32-x64\artist-string-manager.exe"
if not exist "%APP%" (
  echo 找不到 JS 版程序。请先在 app_electron 目录运行 npm install 和 npm run pack:dir。
  pause
  exit /b 1
)
start "" "%APP%"
