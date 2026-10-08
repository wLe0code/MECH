@echo off
REM ============================================================
REM  MECH - quitar la app de escritorio (doble clic).
REM
REM  Borra el icono "MECH" del Escritorio y del menu Inicio, y la
REM  copia de la app. No toca el proyecto ni el robot.
REM ============================================================
title Quitar MECH
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar_app.ps1" -Quitar
echo.
pause
