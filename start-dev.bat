@echo off
set "PATH=%LOCALAPPDATA%\Programs\nodejs;%PATH%"
cd /d "%~dp0frontend"
npm run dev
pause

