# MECH — Control desde Windows

Formas de tener el panel de control de MECH en tu equipo Windows, de más a menos recomendada:

| Modo | Cómo se ve | Setup | Recomendado para |
|---|---|---|---|
| **App «MECH»** ⭐ (`Instalar MECH.bat`) | Icono en el Escritorio; ventana propia; **encuentra al robot sola** | Doble clic, **sin instalar nada** | **Todo el mundo** |
| **App `MECH Panel.exe`** | Ventana con cuatro botones; encuentra la Pi sola | Hay que **construirla** (hace falta Python) | Quien ya la tenga construida |
| **Launcher .bat** | Ventana sin barras (parece app) | Doble click + editar la IP a mano | Respaldo |
| **PWA instalada** | Acceso directo en menú inicio + ícono | 30 s desde Edge | Respaldo |

## La app «MECH» (recomendado, oct 2026)

**Instalarla** (una vez por laptop): doble clic en **`Instalar MECH.bat`**.
Tarda dos segundos y deja un icono **MECH** en el Escritorio y en el menú
Inicio. **No hace falta Python, ni construir nada, ni permisos de
administrador**: usa el Edge (o el Chrome) que ya trae Windows.

**Usarla**: abre el icono. Sale una ventana propia, sin barra de direcciones
ni pestañas, que:

1. **Busca al robot sola**: la última dirección que funcionó, `mech.local`,
   `mech`, y si hace falta la red donde estaba la última vez.
2. Cuando lo encuentra, **entra al panel**.
3. Si no lo encuentra, enseña qué revisar y un campo para escribir la
   dirección (`192.168.1.42`, `mech.local`…). **Sigue buscando sola** cada
   pocos segundos: se puede abrir la app antes de encender el robot.
   El botón «Buscar en redes habituales» prueba una a una las redes típicas
   de casa y de los puntos de acceso de celular (tarda medio minuto).

Desde el panel, el menú de la izquierda abre la **Biblioteca** de videos y la
**Proyección** en otra ventana. Si se pierde la conexión, el aviso de abajo
trae **«Buscar de nuevo»**.

**Quitarla**: doble clic en `Quitar MECH.bat`.

### Cómo está hecha (para quien la mantenga)

- La app es **una página**, [`app/index.html`](app/index.html): la pantalla
  que busca al robot. Un solo archivo, sin nada externo.
- El icono es un **acceso directo a Edge en modo aplicación** (`--app=…`),
  apuntando a esa página. Lo crea [`instalar_app.ps1`](instalar_app.ps1), que
  antes la copia a `%APPDATA%\MECH\app` (así el icono no depende de dónde esté
  la carpeta del proyecto). El perfil del navegador va aparte, en
  `%APPDATA%\MECH\navegador`: ahí se recuerda la dirección del robot.
- **El panel se sigue cargando desde el robot** (`http://mech.local:8000`), y
  es a propósito: así la app y el robot son siempre la misma versión. La app
  solo lo encuentra y entra (con `?app=1`, que es como el panel sabe que debe
  ofrecer «Buscar de nuevo»).
- Desde una página no se puede *leer* lo que contesta otro servidor, pero sí
  saber si contestó y cargar una imagen suya: así comprueba que quien
  responde es MECH (le pide `/static/icon.svg`).
- ⚠️ Si se cambia `app/index.html`, hay que **volver a instalar** en cada
  laptop para que llegue la copia nueva.
- Para probarla sin robot: abrir
  `app/index.html?candidatos=http://localhost:8765&barrido=0`.

Lo que NO hace, a diferencia de `MECH Panel.exe`: no puede averiguar en qué
red está la laptop (una página no tiene permiso), así que no barre la red
actual a ciegas; barre la de la última vez y, si se le pide, las habituales.

## 0. La app antigua: `MECH Panel.exe`

> Sigue funcionando, pero hay que **construirla** en una máquina con Python.
> Para repartir entre el equipo es más fácil `Instalar MECH.bat`.

### Usarla

Doble click y ya. Al abrir busca la Pi sola; cuando el punto se pone **verde**
los cuatro botones se habilitan:

| Botón | Qué abre |
|---|---|
| **ABRIR EL PANEL** | El panel de control, en ventana de aplicación (sin barra de direcciones ni pestañas). |
| **Abrir la proyección** | La página `/projector`, por si proyectas desde el Windows en vez de desde la Pi. |
| **Panel a pantalla completa** | El panel en modo kiosko. Se sale con `Alt + F4`. |
| **Biblioteca de videos (en el navegador)** | La página `/library`, en tu navegador de siempre (pestaña normal, con la dirección a la vista). Ahí se suben los videos de cada obra arrastrándolos. |

Si no la encuentra (redes con *client isolation*, muy común en colegios y
eventos: la laptop no ve a la Pi aunque estén en la misma wifi — el hotspot
del celular es el respaldo), escribe la dirección a mano en el campo y pulsa
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
