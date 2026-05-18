@echo off
REM ============================================================
REM  MECH — Panel de control (modo aplicacion / ventana sin barra)
REM
REM  Abre el panel del robot MECH en Microsoft Edge usando --app,
REM  que oculta la barra de direcciones y pestanas. Se siente como
REM  una app nativa.
REM
REM  La URL del servidor se lee de windows\config.txt. Editala con
REM  el IP de tu Raspberry Pi.
REM ============================================================
setlocal EnableDelayedExpansion

set "CONFIG=%~dp0config.txt"

REM --- Leer URL del archivo de config ---
if not exist "%CONFIG%" goto :ask_url

set "MECH_URL="
for /f "usebackq delims=" %%L in ("%CONFIG%") do (
  if "!MECH_URL!"=="" set "MECH_URL=%%L"
)
if "%MECH_URL%"=="" goto :ask_url
goto :launch

:ask_url
echo.
echo No encontre la configuracion. Necesito la URL del servidor MECH.
echo Ejemplo: http://192.168.1.42:8000
echo.
set /p MECH_URL=URL:
if "%MECH_URL%"=="" (
  echo Error: URL vacia. Saliendo.
  pause
  exit /b 1
)
echo %MECH_URL%>"%CONFIG%"
echo Guardado en %CONFIG%

:launch
echo.
echo Abriendo MECH Control: %MECH_URL%
echo.

REM --- Buscar Edge ---
set "EDGE="
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"     set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"

if defined EDGE (
  start "" "%EDGE%" --app="%MECH_URL%" --new-window --window-size=1280,800
  exit /b 0
)

REM --- Fallback a Chrome ---
set "CHROME="
if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "CHROME=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe"     set "CHROME=%ProgramFiles%\Google\Chrome\Application\chrome.exe"

if defined CHROME (
  start "" "%CHROME%" --app="%MECH_URL%" --new-window --window-size=1280,800
  exit /b 0
)

REM --- Ultimo recurso: navegador por defecto ---
echo No encontre Edge ni Chrome. Abriendo con el navegador por defecto.
start "" "%MECH_URL%"
exit /b 0
