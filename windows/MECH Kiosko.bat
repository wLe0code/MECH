@echo off
REM ============================================================
REM  MECH — Panel de control (modo KIOSKO — pantalla completa)
REM
REM  Util para una tablet o laptop dedicada al control del robot
REM  durante la exhibicion. No deja salir facilmente (Alt+F4 para
REM  cerrar).
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

set "EDGE="
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"     set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"

if defined EDGE (
  start "" "%EDGE%" --kiosk "%MECH_URL%" --edge-kiosk-type=fullscreen --no-first-run
  exit /b 0
)

set "CHROME="
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe"     set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"

if defined CHROME (
  start "" "%CHROME%" --kiosk "%MECH_URL%" --no-first-run
  exit /b 0
)

echo No encontre Edge ni Chrome.
pause
exit /b 1
