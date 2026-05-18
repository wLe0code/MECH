@echo off
REM ============================================================
REM  MECH — Demo del frontend en modo KIOSKO (pantalla completa)
REM
REM  Abre frontend\index.html directamente con file:// en Microsoft Edge
REM  modo kiosko. NO necesita backend. Sirve para probar la UI.
REM
REM  Modo de salida:  Alt + F4
REM  (En modo kiosko de Edge, Escape no funciona.)
REM ============================================================
setlocal

set "HTML=%~dp0..\frontend\index.html"

if not exist "%HTML%" (
  echo No encontre frontend\index.html en:
  echo   %HTML%
  pause
  exit /b 1
)

REM Busca Edge
set "EDGE="
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"     set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"

if defined EDGE (
  start "" "%EDGE%" --kiosk "file:///%HTML:\=/%" --edge-kiosk-type=fullscreen --no-first-run --disable-features=msEdgeSidebar
  exit /b 0
)

REM Fallback Chrome
set "CHROME="
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe"     set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"

if defined CHROME (
  start "" "%CHROME%" --kiosk "file:///%HTML:\=/%" --no-first-run --allow-file-access-from-files
  exit /b 0
)

echo No encontre Edge ni Chrome.
pause
exit /b 1
