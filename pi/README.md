# `pi/` — usar MECH sin la terminal

Dos iconos en el escritorio de la Raspberry Pi para no tener que teclear
comandos cada vez que se enciende el robot.

## Instalación (una sola vez)

Abrí la terminal en la Pi y pegá esto **una vez**:

```bash
bash ~/MECH/pi/instalar-accesos.sh
```

Eso crea los dos iconos en el escritorio. A partir de ahí, todo con doble
click.

> Si al primer doble click el sistema pregunta qué hacer con el archivo,
> elegí **«Ejecutar»** (o «Ejecutar en terminal»). Solo lo pregunta una vez.

## Los dos iconos

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

### 📽️ Proyector MECH

Abre `http://localhost:8000/projector` a pantalla completa (modo kiosko).

⚠️ Lleva el flag **`--autoplay-policy=no-user-gesture-required`**, que **no
es opcional**: sin él los navegadores no dejan reproducir con sonido sin un
clic previo, los videos del slot de marketing se ven **mudos** y la pantalla
muestra «toca la pantalla para activar el sonido». Es un fallo que ya costó
una prueba entera.

Espera a que el servidor responda antes de abrir, así que se puede lanzar
justo después de «Iniciar MECH» sin esperar a mano. Para salir: **Alt+F4**.

## Si algo no funciona

| Síntoma | Qué pasa |
|---|---|
| El icono no hace nada al doble click | Falta marcarlo como ejecutable/confiable: volvé a correr `instalar-accesos.sh` |
| `bad interpreter: /bin/bash^M` | El script llegó con finales de línea de Windows. Lo previene el `.gitattributes` del repo; si aparece, `dos2unix ~/MECH/pi/*.sh` |
| «no encuentro Chromium» | `sudo apt install chromium` |
| Arranca pero el panel sale viejo | En el navegador: **Ctrl+Shift+R** (recarga sin caché) |
| Dice que no pudo actualizar | Sin internet, o hay cambios sin guardar en la Pi. Arranca igual; para verlo: `cd ~/MECH && git status` |

## Lo que estos scripts NO hacen

- **No flashean el Arduino.** Eso sigue siendo desde la laptop.
- **No corren el chequeo previo.** Ese va aparte y con el server APAGADO:
  `python -m backend.preflight`.
- **No tocan el `.env`.** Los ajustes del evento se cambian desde el panel
  (Ajustes), en vivo.
