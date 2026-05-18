@echo off
REM ============================================================
REM  MECH — Demo del frontend en modo APP (ventana sin barras)
REM
REM  Abre frontend\index.html con file:// en Edge en modo aplicacion.
REM  Sin barra de URL ni pestanas; se siente como app, pero se puede
REM  cerrar facilmente con la X o Alt+F4.
REM
REM  NO necesita backend. Sirve para probar la UI.
REM ============================================================
setlocal

set "HTML=%~dp0..\frontend\index.html"

if not exist "%HTML%" (
  echo No encontre frontend\index.html en:
  echo   %HTML%
  pause
  exit /b 1
)

set "EDGE="
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"     set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"

if defined EDGE (
  start "" "%EDGE%" --app="file:///%HTML:\=/%" --new-window --window-size=1400,900
  exit /b 0
)

set "CHROME="
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe"     set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"

if defined CHROME (
  start "" "%CHROME%" --app="file:///%HTML:\=/%" --new-window --window-size=1400,900 --allow-file-access-from-files
  exit /b 0
)

echo No encontre Edge ni Chrome.
pause
exit /b 1
