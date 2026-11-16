# MECH — Control desde Windows

Formas de tener el panel de control de MECH en una laptop Windows:

| Modo | Cómo se ve | Setup |
|---|---|---|
| **App «MECH»** ⭐ (`Instalar MECH.bat`) | Icono en el Escritorio; ventana propia; **encuentra al robot sola** | Doble clic, **sin instalar nada** |
| **PWA instalada** | Acceso directo en el menú Inicio | 30 s desde Edge (respaldo) |

> Hasta oct 2026 también estaban `MECH Panel.exe` (había que construirlo con
> Python) y los lanzadores `MECH Control/Kiosko/Proyector.bat` (había que
> escribir la IP a mano en `config.txt`). Se quitaron en nov 2026: la app
> «MECH» hace lo mismo sin construir ni configurar nada. Siguen en el
> historial de git (último commit que los tiene: `5df6fa5`).

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

Lo que NO hace: no puede averiguar en qué
red está la laptop (una página no tiene permiso), así que no barre la red
actual a ciegas; barre la de la última vez y, si se le pide, las habituales.

### El icono

`mech.ico` sale del logo oficial (`branding/MECH true black.png`) con
`python scripts/mklogo.py`: el logo entero centrado en los tamaños grandes y
solo la «M» con su marco en los pequeños (16-32 px), donde la palabra completa
no se lee. El mismo script genera `app/logo-mech.png` (la pantalla de
búsqueda) y `frontend/icon.svg` (panel y escritorio de la Pi). Tras
regenerarlo hay que volver a correr `Instalar MECH.bat` en cada laptop.

## Respaldo: instalar el panel como PWA

Microsoft Edge puede "instalar" el panel como si fuera una aplicación de Windows con ícono en el menú inicio y entrada en "Aplicaciones".

**Pasos:**

1. Abre Edge (o Chrome).
2. Ve a `http://<IP-de-la-Pi>:8000` (o `http://mech.local:8000`).
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

## Atajos del panel

Una vez dentro del panel, sirven estos:

| Tecla | Acción |
|---|---|
| **Barra espaciadora** | PARO DE EMERGENCIA |
| **V** | Activar / desactivar bucle de voz |
| **1** | Vista de voz / comandos |
| **2** | Vista de proyección stand |
| **3** | Vista de espacio inmersivo |

## Solución de problemas

| Problema | Solución |
|---|---|
| "No encontre Edge ni Chrome" | Instala Microsoft Edge (viene con Windows 10/11 actualizado) o Chrome. |
| El panel dice "Sin servidor" | Verifica que el servidor corre en la Pi (`python -m backend.server`) y que la dirección es correcta. Prueba abrir esa URL en cualquier navegador desde el Windows. |
| "Reconectando…" sin parar | Firewall de Windows bloqueando WebSocket. Acepta el permiso de red privada o desactiva temporalmente. |
| La página carga pero el PARO no responde | Botones REST: el servidor debe estar activo. Mira los logs del panel a la derecha — si no aparecen logs nuevos al pulsar emergencia, el servidor no recibe. Revisa la consola Python en la Pi. |
| Quiero salir del modo kiosko | `Alt + F4` cierra Edge. Si está bloqueado, `Ctrl + Alt + Supr` → Administrador de tareas → cierra `msedge.exe`. |
