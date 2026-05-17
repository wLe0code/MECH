@echo off
REM ============================================================
REM  MECH — Pantalla de PROYECTOR (no es el panel de control)
REM
REM  Abre /projector en modo kiosko fullscreen. Util si conectas
REM  un proyector al equipo Windows en lugar de a la Pi.
REM  Lo que esta pantalla muestra es lo que el robot quiere
REM  proyectar (imagenes generadas, videos del stand, etc.).
REM ============================================================
setlocal EnableDelayedExpansion

set "CONFIG=%~dp0config.txt"

if not exist "%CONFIG%" (
  echo Configura primero ejecutando "MECH Control.bat"
  pause
  exit /b 1
)

set "MECH_URL="
for /f "usebackq delims=" %%L in ("%CONFIG%") do (
  if "!MECH_URL!"=="" set "MECH_URL=%%L"
)

set "PROJ_URL=%MECH_URL%/projector"

set "EDGE="
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"     set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"

if defined EDGE (
  start "" "%EDGE%" --kiosk "%PROJ_URL%" --edge-kiosk-type=fullscreen --no-first-run
  exit /b 0
)

set "CHROME="
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe"     set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"

if defined CHROME (
  start "" "%CHROME%" --kiosk "%PROJ_URL%" --no-first-run
  exit /b 0
)

echo No encontre Edge ni Chrome.
pause
exit /b 1
