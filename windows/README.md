# MECH — Control desde Windows

Cuatro formas de tener el panel de control de MECH en tu equipo Windows, de más a menos recomendada:

| Modo | Cómo se ve | Setup | Recomendado para |
|---|---|---|---|
| **App `MECH Panel.exe`** ⭐ | Ventana propia; **encuentra la Pi sola** | Doble click | **Todo el mundo.** Es lo que hay que repartir |
| **Instalador** | Igual, pero en el menú inicio y con desinstalador | Compilar una vez | La laptop fija del stand |
| **Launcher .bat** | Ventana sin barras (parece app) | Doble click + editar la IP a mano | Si no quieres construir nada |
| **PWA instalada** | Acceso directo en menú inicio + ícono | 30 s desde Edge | Alternativa al .exe, sin construir |

> **Lo nuevo (sep 2026): `MECH Panel.exe`.** Antes había que saberse la IP de
> la Pi y editar `config.txt` a mano — y esa IP cambia cada vez que se cambia
> de wifi. La app la **busca sola**: prueba `mech.local`, `mech`, la última
> dirección que funcionó y, si hace falta, barre la red local buscando quién
> responde. Se salta ese paso entero.

## 0. La app: `MECH Panel.exe` (recomendado)

### Usarla

Doble click y ya. Al abrir busca la Pi sola; cuando el punto se pone **verde**
los tres botones se habilitan:

| Botón | Qué abre |
|---|---|
| **ABRIR EL PANEL** | El panel de control, en ventana de aplicación (sin barra de direcciones ni pestañas). |
| **Abrir la proyección** | La página `/projector`, por si proyectas desde el Windows en vez de desde la Pi. |
| **Panel a pantalla completa** | El panel en modo kiosko. Se sale con `Alt + F4`. |

Si no la encuentra (redes con *client isolation*, muy común en colegios y
eventos — ver `handoff.md` §6), escribe la dirección a mano en el campo y pulsa
**Probar**. Acepta cualquier forma: `192.168.1.42`, `mech`, `mech.local:8000`,
`http://192.168.1.42:8000`. La recuerda para la próxima.

La dirección se guarda en `%APPDATA%\MECH\config.json`.

### Construir el .exe

Hace falta **una** máquina con Python para construirlo; el .exe que sale no
necesita Python en ninguna otra.

```powershell
powershell -ExecutionPolicy Bypass -File windows\construir_exe.ps1
```

Deja `windows\dist\MECH Panel.exe` (~10 MB). Ese archivo es lo que se le pasa
a quien sea: se copia y funciona, no instala nada.

La primera vez que se abre, **Windows SmartScreen dirá «editor desconocido»**
(el .exe no está firmado — firmarlo cuesta dinero y no aporta nada aquí):
*Más información* → *Ejecutar de todas formas*. Solo pasa una vez por equipo.

### Instalador (opcional)

Para la laptop fija del stand, donde no conviene depender de en qué carpeta
quedó el .exe:

1. Instala [Inno Setup](https://jrsoftware.org/isdl.php) (gratis).
2. Construye el .exe con el comando de arriba.
3. Doble click en [`MECH-Panel.iss`](MECH-Panel.iss) → **Compile**.

Sale `windows\instalador\MECH-Panel-Setup.exe`: menú inicio, acceso directo
opcional en el escritorio y desinstalador. **No pide permisos de
administrador** (se instala solo para el usuario actual).

### Por qué está hecha así

`windows/mech_panel.py` **no usa nada fuera de la librería estándar de
Python**. Es lo que permite que el .exe pese 10 MB y se construya en un
minuto. Las alternativas (Tauri, Electron, pywebview) meten un navegador
entero dentro del ejecutable para acabar mostrando la misma página que Edge ya
sabe mostrar. Aquí Edge/Chrome ponen la ventana (modo `--app`) y el .exe solo
se encarga de lo que faltaba: encontrar la Pi y recordar la dirección.

⚠️ Si corres `python windows\mech_panel.py` directamente **con el Python de la
Microsoft Store**, Windows le virtualiza `%APPDATA%` y guarda la dirección en
otro sitio que el .exe. No es un problema real (cada uno es coherente consigo
mismo), pero explica que la app "se olvide" de la dirección al pasar del
script al .exe.

## 1. Preparar la conexión

Antes de cualquiera de los modos, asegúrate de que:

1. La Raspberry Pi está corriendo el servidor (`python -m backend.server`).
2. Tu equipo Windows está en la **misma red wifi** que la Pi.
3. Conoces la **IP de la Pi**: en la Pi corre `hostname -I`, copia el primer número (ej. `192.168.1.42`).

Edita [`config.txt`](config.txt) en esta carpeta y pon:

```
http://<IP-de-la-Pi>:8000
```

Ejemplo: `http://192.168.1.42:8000`

## 2. Launchers (.bat)

Doble click en uno de estos archivos:

- **`MECH Control.bat`** — Modo aplicación. Abre Edge sin barra de URL ni pestañas. Funciona como ventana redimensionable. Cierre normal con la X.
- **`MECH Kiosko.bat`** — Pantalla completa. No hay forma fácil de salir (usa `Alt+F4`). Úsalo para una tablet o pantalla dedicada que solo controla el robot.
- **`MECH Proyector.bat`** — Abre la **página del proyector** (`/projector`), no el panel. Útil solo si vas a conectar un proyector a un equipo Windows; normalmente esto se hace en la Pi.

**Cómo funciona internamente:** los .bat detectan si tienes Edge o Chrome instalado y los lanzan con `--app` (modo aplicación) o `--kiosk` (pantalla completa). No instalan nada.

## 3. Modo PWA (recomendado para uso permanente)

Microsoft Edge puede "instalar" el panel como si fuera una aplicación de Windows con ícono en el menú inicio y entrada en "Aplicaciones".

**Pasos:**

1. Abre Edge (o Chrome).
2. Ve a `http://<IP-de-la-Pi>:8000` (tu URL del config.txt).
3. Espera a que cargue el panel.
4. Click en el botón **"Instalar app"** que aparece a la derecha de la barra de direcciones (ícono de monitor con flecha). Si no aparece:
   - En Edge: menú `…` → **Aplicaciones** → **Instalar este sitio como aplicación**.
   - En Chrome: menú `⋮` → **Transmitir, guardar y compartir** → **Instalar página como aplicación**.
5. Confirma. Edge crea un acceso directo en escritorio y en el menú inicio.
6. Ahora puedes abrir "MECH" como cualquier aplicación de Windows.

**Ventajas del modo PWA:**
- Ícono fijo en el menú inicio (la del SVG `frontend/icon.svg`).
- Se abre en ventana propia sin barra de Edge.
- Service Worker muestra una página offline si la Pi se desconecta (en lugar del error genérico del navegador).
- Atajos del manifest (paro de emergencia) accesibles con click derecho en el ícono de la barra de tareas.

## 4. Atajos del panel

Una vez dentro del panel, sirven estos:

| Tecla | Acción |
|---|---|
| **Barra espaciadora** | PARO DE EMERGENCIA |
| **V** | Activar / desactivar bucle de voz |
| **1** | Vista de voz / comandos |
| **2** | Vista de proyección stand |
| **3** | Vista de espacio inmersivo |

## 5. Solución de problemas

| Problema | Solución |
|---|---|
| "No encontre Edge ni Chrome" | Instala Microsoft Edge (viene con Windows 10/11 actualizado) o Chrome. |
| El panel dice "Sin servidor" | Verifica que el servidor corre en la Pi (`python -m backend.server`) y que la IP del `config.txt` es correcta. Prueba abrir esa URL en cualquier navegador desde el Windows. |
| "Reconectando…" sin parar | Firewall de Windows bloqueando WebSocket. Acepta el permiso de red privada o desactiva temporalmente. |
| La página carga pero el PARO no responde | Botones REST: el servidor debe estar activo. Mira los logs del panel a la derecha — si no aparecen logs nuevos al pulsar emergencia, el servidor no recibe. Revisa la consola Python en la Pi. |
| Quiero salir del modo kiosko | `Alt + F4` cierra Edge. Si está bloqueado, `Ctrl + Alt + Supr` → Administrador de tareas → cierra `msedge.exe`. |

## 6. Historial: por qué antes no había .exe

Hasta sep 2026 el panel se abría solo con los `.bat` y la PWA, y este README
explicaba que un .exe nativo no compensaba: Tauri pedía instalar Rust + Visual
Studio Build Tools (~1 GB) y Electron empaquetaba Chromium entero (~150 MB).

Eso **sigue siendo cierto para esas dos opciones**. Lo que cambió es el
enfoque: en vez de meter un navegador dentro del ejecutable, el .exe solo
resuelve lo que los `.bat` no podían (encontrar la Pi, recordar la dirección) y
deja la ventana en manos de Edge. Con eso, un ejecutable de 10 MB sin
dependencias hace el trabajo — y los `.bat` siguen ahí para quien no quiera
construir nada.
