@echo off
REM ============================================================
REM  MECH - instalar la app de escritorio (doble clic).
REM
REM  Deja un icono "MECH" en el Escritorio y en el menu Inicio.
REM  Al abrirlo busca al robot solo y entra a su panel de control,
REM  en una ventana propia. No hace falta Python ni instalar nada
REM  mas: usa el Edge (o el Chrome) que ya tiene Windows.
REM
REM  Todo lo hace instalar_app.ps1; aqui solo se le llama.
REM ============================================================
title Instalar MECH
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar_app.ps1"
echo.
pause
