# `pi/` — usar MECH sin la terminal

Cinco iconos en el escritorio de la Raspberry Pi para no tener que teclear
comandos cada vez que se enciende el robot. Con el arranque automático
activado, ni siquiera hace falta el doble click: se enciende la Pi y MECH
queda escuchando «ok MECH».

## Instalación (una sola vez)

Abrí la carpeta `MECH/pi` en el explorador de archivos de la Pi y hacé
**doble click en `instalar-accesos.sh`** → «Ejecutar en terminal».

O, si preferís la terminal:

```bash
bash ~/MECH/pi/instalar-accesos.sh
```

Eso crea los cinco iconos en el escritorio. A partir de ahí, todo con doble
click.

> Si al primer doble click el sistema pregunta qué hacer con el archivo,
> elegí **«Ejecutar»** (o «Ejecutar en terminal»). Solo lo pregunta una vez.

## Los cinco iconos

### 🟢 Iniciar MECH

Hace de una vez lo que antes se tecleaba a mano:

```bash
cd ~/MECH && git pull && python -m backend.server
```

Y además:

- **Cierra un MECH anterior si lo había.** Si no, el puerto 8000 sigue
  ocupado y el nuevo no arranca.
- **Arranca aunque no haya internet.** Si el `git pull` falla (wifi del
  recinto, o cambios sin guardar en la Pi), lo avisa y sigue con el código
  que ya está en la Pi. Quedarse sin robot por culpa del wifi sería lo peor
  que podría pasar en el evento.
- **Dice en qué versión está** (`git log --oneline -1`), para saber de un
  vistazo si la Pi tiene lo último.
- **Muestra la dirección del panel** para abrirlo desde la laptop.

La ventana se queda abierta con el log del servidor. Para parar MECH:
**Ctrl+C** ahí, o cerrar la ventana.

### 🖥️ Panel MECH

Abre el **panel de control** en la Pi: la barra de fase de voz arriba
(EN REPOSO / PUEDES HABLAR / GRABANDO / PENSANDO / HABLANDO), los chips de
idioma, la tarjeta del traductor y los Ajustes.

Se abre en modo aplicación (sin barra de direcciones ni pestañas) pero **no**
en kiosko: hay que poder usar los botones y cambiar de vista.

> Desde la **laptop** el equivalente es `windows\MECH Control.bat`.

### 📽️ Proyector MECH

Abre `http://localhost:8000/projector` a pantalla completa (modo kiosko).

⚠️ Lleva el flag **`--autoplay-policy=no-user-gesture-required`**, que **no
es opcional**: sin él los navegadores no dejan reproducir con sonido sin un
clic previo, los videos del slot de marketing se ven **mudos** y la pantalla
muestra «toca la pantalla para activar el sonido». Es un fallo que ya costó
una prueba entera.

Espera a que el servidor responda antes de abrir, así que se puede lanzar
justo después de «Iniciar MECH» sin esperar a mano. Para salir: **Alt+F4**.

### 🔴 Apagar MECH

Para el servidor. Es lo mismo que Ctrl+C en la ventana de «Iniciar MECH»,
pero sin tener que buscarla entre las ventanas abiertas.

Le da unos segundos para cerrar bien (suelta el micrófono, manda STOP al
Arduino) y solo si no cierra lo fuerza. También cierra la proyección en
kiosko si estaba abierta — **solo esa**, no otros navegadores que tengas.

⚠️ Apaga **el servidor, no la Raspberry Pi**. Para apagar la Pi: menú del
sistema → Shutdown.

### ⚡ MECH al encender

Interruptor del **arranque automático**. Doble click cambia el estado y te
dice cuál quedó:

- **ENCENDIDO** → al prender la Pi, MECH arranca solo y queda escuchando
  «ok MECH». Cero terminal, cero clicks: encendés la Pi y ya está listo.
- **APAGADO** → vuelve a arrancarse solo con el icono «Iniciar MECH».

El arranque automático usa `--sin-actualizar` **a propósito**: en un evento
no querés que el robot cambie de comportamiento al encenderlo solo porque
alguien subió algo. Actualizar sigue siendo un acto deliberado (el icono
«Iniciar MECH»).

## Si algo no funciona

| Síntoma | Qué pasa |
|---|---|
| El icono no hace nada al doble click | Falta marcarlo como ejecutable/confiable: volvé a correr `instalar-accesos.sh` |
| `bad interpreter: /bin/bash^M` | El script llegó con finales de línea de Windows. Lo previene el `.gitattributes` del repo; si aparece, `dos2unix ~/MECH/pi/*.sh` |
| «no encuentro Chromium» | `sudo apt install chromium` |
| Arranca pero el panel sale viejo | En el navegador: **Ctrl+Shift+R** (recarga sin caché) |
| Arranca solo y no quiero | Doble click en «MECH al encender» para apagarlo |
| No arranca solo aunque lo activé | El arranque automático va con la SESIÓN de escritorio: la Pi tiene que entrar al escritorio sola (sin pedir contraseña) |
| Dice que no pudo actualizar | Sin internet, o hay cambios sin guardar en la Pi. Arranca igual; para verlo: `cd ~/MECH && git status` |

## Lo que estos scripts NO hacen

- **No flashean el Arduino.** Eso sigue siendo desde la laptop.
- **No corren el chequeo previo.** Ese va aparte y con el server APAGADO:
  `python -m backend.preflight`.
- **No tocan el `.env`.** Los ajustes del evento se cambian desde el panel
  (Ajustes), en vivo.
