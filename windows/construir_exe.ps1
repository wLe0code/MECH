# Construye "MECH Panel.exe" a partir de windows/mech_panel.py.
#
# Se corre UNA vez (o cada vez que se cambie el lanzador) en una maquina
# Windows con Python instalado. El .exe que sale NO necesita Python: se lo
# lleva dentro. Es lo que se le pasa a alguien del equipo para que tenga el
# panel sin instalar nada.
#
#   powershell -ExecutionPolicy Bypass -File windows\construir_exe.ps1
#
# Resultado: windows\dist\MECH Panel.exe  (~10 MB)
#
# Por que un venv aparte: PyInstaller mete en el .exe lo que encuentra en el
# entorno. Construyendo desde el Python de diario se colarian paquetes que no
# pintan nada (numpy, opencv...) y el .exe pasaria de 10 MB a cientos.
# mech_panel.py no usa NADA fuera de la libreria estandar justo por esto.

$ErrorActionPreference = "Stop"
$aqui = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $aqui

Write-Host ""
Write-Host "=== MECH Panel - construir .exe ===" -ForegroundColor Cyan
Write-Host ""

# 1. Python
$python = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $python) {
    Write-Host "No encuentro Python. Instalalo desde python.org (marca" -ForegroundColor Red
    Write-Host "'Add Python to PATH' al instalar) y vuelve a correr esto." -ForegroundColor Red
    exit 1
}
Write-Host ("Python: " + $python.Source)

# 2. Entorno de construccion limpio
$venv = Join-Path $aqui ".venv-build"
if (-not (Test-Path $venv)) {
    Write-Host "Creando entorno de construccion..."
    & python -m venv $venv
    if (-not $?) { Write-Host "No pude crear el entorno." -ForegroundColor Red; exit 1 }
}
$vpy = Join-Path $venv "Scripts\python.exe"

Write-Host "Instalando PyInstaller (necesita internet la primera vez)..."
& $vpy -m pip install --quiet --disable-pip-version-check --upgrade pip
& $vpy -m pip install --quiet --disable-pip-version-check pyinstaller
if (-not $?) { Write-Host "No pude instalar PyInstaller." -ForegroundColor Red; exit 1 }

# 3. Icono (se regenera por si cambio el logo)
Write-Host "Generando el icono..."
& python (Join-Path $aqui "hacer_icono.py")
if (-not $?) {
    Write-Host "No pude generar el icono (falta Pillow?). Sigo sin el." -ForegroundColor Yellow
}

# 4. Construir
Write-Host "Construyendo el .exe..."
$args = @(
    "-m", "PyInstaller",
    "--onefile",            # un solo archivo, nada que instalar
    "--windowed",           # sin ventana negra de consola detras
    "--name", "MECH Panel",
    "--distpath", (Join-Path $aqui "dist"),
    "--workpath", (Join-Path $aqui "build"),
    "--specpath", (Join-Path $aqui "build"),
    "--noconfirm"
)
$ico = Join-Path $aqui "mech.ico"
if (Test-Path $ico) {
    # --icon pone el icono del .exe; --add-data lo mete DENTRO para que la
    # ventana tambien lo tenga (los lee de sitios distintos).
    $args += @("--icon", $ico, "--add-data", ($ico + ";."))
}
$args += (Join-Path $aqui "mech_panel.py")

& $vpy @args
if (-not $?) { Write-Host "La construccion fallo." -ForegroundColor Red; exit 1 }

$exe = Join-Path $aqui "dist\MECH Panel.exe"
if (-not (Test-Path $exe)) {
    Write-Host "Termino sin errores pero no encuentro el .exe." -ForegroundColor Red
    exit 1
}

$mb = [math]::Round((Get-Item $exe).Length / 1MB, 1)
Write-Host ""
Write-Host "Listo: $exe  ($mb MB)" -ForegroundColor Green
Write-Host ""
Write-Host "Para repartirlo:"
Write-Host "  - Basta con copiar ese .exe. No necesita Python ni instalacion."
Write-Host "  - Para un instalador de verdad (menu inicio, desinstalador),"
Write-Host "    instala Inno Setup y compila windows\MECH-Panel.iss"
Write-Host ""
Write-Host "Aviso: Windows SmartScreen dira 'editor desconocido' la primera" -ForegroundColor Yellow
Write-Host "vez (el .exe no esta firmado). Mas informacion > Ejecutar de todas formas." -ForegroundColor Yellow
