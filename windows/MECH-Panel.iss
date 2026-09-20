; Instalador de Windows para "MECH Panel".
;
; Esto es el paso OPCIONAL despues del .exe. El .exe suelto ya funciona
; copiandolo a cualquier lado; esto hace un instalador de verdad:
;
;   - se instala en Archivos de programa,
;   - deja acceso directo en el menu inicio (y en el escritorio si lo piden),
;   - aparece en "Agregar o quitar programas" con su desinstalador,
;   - y al actualizar reemplaza la version anterior en vez de dejar copias.
;
; Vale la pena para la maquina del stand, donde el operador no deberia tener
; que acordarse de en que carpeta dejo un .exe.
;
; COMO COMPILARLO
;   1. Instala Inno Setup (gratis): https://jrsoftware.org/isdl.php
;   2. Construye antes el .exe:
;        powershell -ExecutionPolicy Bypass -File windows\construir_exe.ps1
;   3. Doble click en este archivo (lo abre el Inno Setup Compiler) y pulsa
;      "Compile". O por linea de comandos:
;        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" windows\MECH-Panel.iss
;
; Resultado: windows\instalador\MECH-Panel-Setup.exe

#define MiNombre     "MECH Panel"
#define MiVersion    "1.0.0"
#define MiEquipo     "Equipo MECH"
#define MiEjecutable "MECH Panel.exe"

[Setup]
AppId={{8F3C2A91-7D4E-4B2A-9C15-MECHPANEL0001}
AppName={#MiNombre}
AppVersion={#MiVersion}
AppPublisher={#MiEquipo}
DefaultDirName={autopf}\MECH Panel
DefaultGroupName=MECH
; Sin pagina de "elige la carpeta": nadie quiere decidir eso.
DisableDirPage=yes
DisableProgramGroupPage=yes
; Se instala solo para el usuario actual, asi no pide permisos de
; administrador (en un portatil prestado eso es media batalla).
PrivilegesRequired=lowest
OutputDir=instalador
OutputBaseFilename=MECH-Panel-Setup
SetupIconFile=mech.ico
UninstallDisplayIcon={app}\{#MiEjecutable}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; El panel es de 64 bits porque lo es el Python con el que se construye.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"; \
  GroupDescription: "Accesos directos:"

[Files]
Source: "dist\{#MiEjecutable}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MiNombre}"; Filename: "{app}\{#MiEjecutable}"
Name: "{group}\Desinstalar {#MiNombre}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MiNombre}"; Filename: "{app}\{#MiEjecutable}"; \
  Tasks: escritorio

[Run]
Filename: "{app}\{#MiEjecutable}"; \
  Description: "Abrir {#MiNombre} ahora"; \
  Flags: nowait postinstall skipifsilent

[UninstallDelete]
; La direccion de la Pi que guarda la app. Se borra al desinstalar para no
; dejar basura, pero NO al actualizar (ahi no corre el desinstalador).
Type: filesandordirs; Name: "{userappdata}\MECH"
