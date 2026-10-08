# Instala (o quita) la app de escritorio de MECH en este Windows.
#
# Que deja: un icono "MECH" en el Escritorio y en el menu Inicio. Al abrirlo
# sale una ventana propia (Edge o Chrome en modo aplicacion, sin barra de
# direcciones ni pestanas) que BUSCA AL ROBOT SOLA y entra a su panel.
#
# NO hace falta Python ni construir ningun .exe: la app es una pagina
# (windows\app\index.html) y el icono es un acceso directo al navegador que
# ya trae Windows. Por eso se instala en dos segundos en cualquier laptop.
#
# Se usa con doble clic en "Instalar MECH.bat". A mano:
#   powershell -ExecutionPolicy Bypass -File windows\instalar_app.ps1
#   powershell -ExecutionPolicy Bypass -File windows\instalar_app.ps1 -Quitar
#
# La app se COPIA a %APPDATA%\MECH\app, asi el icono sigue funcionando aunque
# se mueva o se borre la carpeta del proyecto. Si se actualiza
# windows\app\index.html, hay que volver a instalar para que llegue la copia
# nueva.
#
# (Este archivo va SIN tildes a proposito: PowerShell 5 lee los .ps1 sin
# marca de codificacion como ANSI y las tildes saldrian rotas.)

param(
    [switch]$Quitar,
    # Los tres de abajo son para probar el instalador sin tocar el equipo.
    [string]$Destino = "",        # donde se copia la app
    [string]$Escritorio = "",     # donde va el icono
    [switch]$SinMenuInicio
)

$ErrorActionPreference = "Stop"
$aqui = Split-Path -Parent $MyInvocation.MyCommand.Path
$nombre = "MECH"

if (-not $Destino)    { $Destino = Join-Path $env:APPDATA "MECH\app" }
if (-not $Escritorio) { $Escritorio = [Environment]::GetFolderPath("Desktop") }
$menu = Join-Path ([Environment]::GetFolderPath("Programs")) "MECH"

$accesos = @((Join-Path $Escritorio "$nombre.lnk"))
if (-not $SinMenuInicio) { $accesos += (Join-Path $menu "$nombre.lnk") }

Write-Host ""
Write-Host "=== MECH - app de escritorio ===" -ForegroundColor Cyan
Write-Host ""

# -- Quitar ------------------------------------------------------------------
if ($Quitar) {
    foreach ($lnk in $accesos) {
        if (Test-Path -LiteralPath $lnk) {
            Remove-Item -LiteralPath $lnk -Force
            Write-Host "Quitado: $lnk"
        }
    }
    if ((-not $SinMenuInicio) -and (Test-Path -LiteralPath $menu) -and
        -not (Get-ChildItem -LiteralPath $menu -Force)) {
        Remove-Item -LiteralPath $menu -Force
    }
    if (Test-Path -LiteralPath $Destino) {
        Remove-Item -LiteralPath $Destino -Recurse -Force
        Write-Host "Quitada la copia de la app: $Destino"
    }
    Write-Host ""
    Write-Host "Listo: MECH ya no esta instalado en este equipo." -ForegroundColor Green
    exit 0
}

# -- 1. La app y el icono tienen que estar junto a este script ---------------
$origen = Join-Path $aqui "app"
$icono = Join-Path $aqui "mech.ico"
if (-not (Test-Path -LiteralPath (Join-Path $origen "index.html"))) {
    Write-Host "No encuentro windows\app\index.html. Descarga el proyecto completo." -ForegroundColor Red
    exit 1
}

# -- 2. El navegador: Edge viene con Windows; si no, Chrome ------------------
$navegador = $null
foreach ($base in @(${env:ProgramFiles(x86)}, $env:ProgramFiles, $env:LOCALAPPDATA)) {
    if (-not $base) { continue }
    foreach ($rel in @("Microsoft\Edge\Application\msedge.exe", "Google\Chrome\Application\chrome.exe")) {
        $ruta = Join-Path $base $rel
        if ((-not $navegador) -and (Test-Path -LiteralPath $ruta)) { $navegador = $ruta }
    }
}
if (-not $navegador) {
    Write-Host "No encuentro Microsoft Edge ni Google Chrome en este equipo." -ForegroundColor Red
    Write-Host "Instala uno de los dos y vuelve a abrir este instalador."
    exit 1
}
Write-Host "Navegador: $navegador"

# -- 3. Copiar la app a su sitio ---------------------------------------------
New-Item -ItemType Directory -Force -Path $Destino | Out-Null
Copy-Item -Path (Join-Path $origen "*") -Destination $Destino -Recurse -Force
if (Test-Path -LiteralPath $icono) { Copy-Item -LiteralPath $icono -Destination $Destino -Force }
Write-Host "App copiada a: $Destino"

# -- 4. Los accesos directos --------------------------------------------------
# La pagina se abre como archivo local. AbsoluteUri la deja en forma
# file:///C:/... y cambia los espacios por %20 (hay usuarios con espacio en
# el nombre).
$pagina = ([System.Uri](Join-Path $Destino "index.html")).AbsoluteUri
# Perfil de navegador aparte: la ventana de MECH no arrastra las pestanas, las
# sesiones ni las extensiones del navegador personal de nadie, y ahi se guarda
# la ultima direccion del robot.
$perfil = Join-Path (Split-Path -Parent $Destino) "navegador"
# --autoplay-policy: sin el, los videos de marketing se reproducen MUDOS si se
# proyecta desde este equipo (mismo flag que usa el script de la Pi).
$argumentos = "--app=`"$pagina`" --user-data-dir=`"$perfil`" " +
              "--autoplay-policy=no-user-gesture-required --window-size=1400,900 " +
              "--no-first-run --no-default-browser-check"

$shell = New-Object -ComObject WScript.Shell
foreach ($lnk in $accesos) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $lnk) | Out-Null
    $acceso = $shell.CreateShortcut($lnk)
    $acceso.TargetPath = $navegador
    $acceso.Arguments = $argumentos
    $acceso.WorkingDirectory = $Destino
    $acceso.Description = "Panel de control del robot MECH"
    $rutaIcono = Join-Path $Destino "mech.ico"
    if (Test-Path -LiteralPath $rutaIcono) { $acceso.IconLocation = "$rutaIcono,0" }
    $acceso.Save()
    Write-Host "Icono creado: $lnk"
}

Write-Host ""
Write-Host "Listo. Abre el icono MECH del Escritorio (o buscalo en el menu Inicio)." -ForegroundColor Green
Write-Host "La primera vez busca al robot sola; tiene que estar encendido y en la misma wifi."
Write-Host ""
exit 0
