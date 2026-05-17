# MECH — Control desde Windows

Tres formas de tener el panel de control de MECH en tu equipo Windows, de menos a más "nativa":

| Modo | Cómo se ve | Setup | Recomendado para |
|---|---|---|---|
| **Launcher .bat (app)** | Ventana sin barras (parece app) | Doble click | Operador del stand (laptop normal) |
| **Launcher .bat (kiosko)** | Pantalla completa, sin escape fácil | Doble click | Tablet/pantalla dedicada |
| **PWA instalada** | Acceso directo en menú inicio + ícono | 30s desde Edge | Uso permanente |

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

## 6. ¿Por qué no una app .exe nativa de verdad?

Lo consideramos. Las opciones nativas son:

- **Tauri** — Rust + webview. Binario pequeño (~10 MB). Requiere instalar Rust + Visual Studio Build Tools para compilar, ~1 GB de setup. Sobrecarga para el caso.
- **Electron** — Chromium empaquetado. Pesado (~150 MB), pero familiar. Necesita Node.js para construir.
- **PyWebView / NeutralinoJS** — alternativas ligeras pero menos pulidas.

Para un proyecto de competencia con plazo, el modo `--app` de Edge + PWA da el 95% de la experiencia nativa con 0% del setup. Si más adelante quieres un `.exe` distribuible, [Tauri](https://tauri.app/) es el camino más limpio: el HTML/CSS/JS que ya tenemos sirve sin cambios.
