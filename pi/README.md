# `pi/` — usar MECH sin la terminal

**Tres iconos** en el escritorio de la Raspberry Pi. Con ellos no hace falta
teclear ningún comando para usar el robot.

## Instalación (una sola vez)

Abrí la carpeta `MECH/pi` en el explorador de archivos de la Pi y hacé
**doble click en `instalar-accesos.sh`** → «Ejecutar en terminal».

O, si preferís la terminal:

```bash
bash ~/MECH/pi/instalar-accesos.sh
```

> Si al primer doble click el sistema pregunta qué hacer con el archivo,
> elegí **«Ejecutar»** (o «Ejecutar en terminal»). Solo lo pregunta una vez.

Se puede volver a correr sin problema: reescribe los iconos y **borra los de
versiones anteriores**, para que no queden botones sueltos.

## Los tres iconos

### 🟢 Iniciar MECH

Lo hace todo de una vez:

1. Baja los últimos cambios (`git pull`).
2. Arranca el servidor.
3. **Abre el panel de control solo**, en cuanto el servidor responde.

El panel es la ventana con la barra de fase de voz arriba (EN REPOSO /
PUEDES HABLAR / GRABANDO / PENSANDO / HABLANDO), los chips de idioma, la
tarjeta del traductor y los Ajustes. Se abre sin barra de direcciones ni
pestañas, pero **no** en kiosko: hay que poder usar los botones.

Y además:

- **Arranca aunque no haya internet.** Si el `git pull` falla, lo avisa y
  sigue con el código que ya está en la Pi. Quedarse sin robot por culpa del
  wifi del recinto sería lo peor que podría pasar en un evento.
- **Cierra un MECH anterior** si lo había — si no, el puerto 8000 sigue
  ocupado y el nuevo no levanta.
- **Dice qué versión está corriendo** y las direcciones del panel, para
  abrirlo también desde la laptop.

La ventana de terminal se queda abierta con el log del servidor. Es normal:
ahí se ve todo lo que hace MECH.

### 📽️ Proyectar MECH

Abre la ventana con **lo que MECH proyecta**, a pantalla completa.

⚠️ Lleva el flag **`--autoplay-policy=no-user-gesture-required`**, que **no
es opcional**: sin él los navegadores no dejan reproducir con sonido sin un
clic previo, los videos del slot de marketing se ven **mudos** y la pantalla
muestra «toca la pantalla para activar el sonido». Es un fallo que ya costó
una prueba entera.

Espera a que el servidor responda, así que se puede lanzar justo después de
«Iniciar MECH». Para salir: **Alt+F4**.

### 🔴 Apagar MECH

Para el servidor. Es lo mismo que Ctrl+C en la ventana de «Iniciar MECH»,
pero sin tener que buscarla entre las ventanas abiertas.

Le da unos segundos para cerrar bien (soltar el micrófono, mandar STOP al
Arduino) y solo lo fuerza si no cierra. Cierra también la proyección si
estaba abierta — **solo esa**, no otros navegadores que tengas.

⚠️ Apaga **el servidor, no la Raspberry Pi**. Para apagar la Pi: menú del
sistema → Shutdown.

## Extra: arrancar solo al encender la Pi

Sin icono, para no llenar el escritorio. Doble click en
**`pi/autoarranque.sh`** desde el explorador de archivos: cambia el estado y
te dice cuál quedó.

- **ENCENDIDO** → al prender la Pi, MECH arranca solo y queda escuchando
  «ok MECH». Ni terminal ni clicks.
- **APAGADO** → vuelve a arrancarse con el icono «Iniciar MECH».

El arranque automático va **sin actualizar y sin abrir el panel**, a
propósito: en un evento el robot no debe cambiar de comportamiento solo
porque alguien subió algo, y la pantalla de la Pi es la superficie de
proyección — abrir el panel ahí la taparía.

## Extra: volumen de la Pi al máximo

Doble click en **`pi/volumen-max.sh`** desde el explorador de archivos.

El audio pasa por varias etapas de volumen antes de llegar al parlante (el
sink de PipeWire y uno o varios mezcladores de ALSA). Basta con que UNA esté
al 40 % para que todo suene flojo, y no hay un sitio único donde mirarlo. El
script las enumera todas y las pone a tope; dice qué encontró y qué cambió.

Es ganancia **gratis**: no distorsiona, solo deja de desperdiciar margen. Es
lo primero que hay que hacer con un parlante flojo.

**No sube por encima del 100 %** a propósito: eso sería ganancia digital sin
limitador y la voz saldría rota. Para subir más está **Ajustes → «Volumen
voz»** en el panel, que hace lo mismo pero con un limitador suave.

Orden recomendado si suena bajo:

1. La rueda de volumen **física** del parlante, arriba del todo.
2. `pi/volumen-max.sh`.
3. Panel → Ajustes → **«Volumen voz»** a +6 dB.
4. Si aún no alcanza, es el parlante (los S150 son de 1,2 W por canal); uno
   amplificado de 10-20 W lo resuelve de verdad.

## Si algo no funciona

| Síntoma | Qué pasa |
|---|---|
| No me salen los iconos nuevos | Falta `git pull` en la Pi y volver a correr `instalar-accesos.sh` |
| El icono no hace nada al doble click | Falta marcarlo como ejecutable/confiable: volvé a correr `instalar-accesos.sh` |
| `bad interpreter: /bin/bash^M` | El script llegó con finales de línea de Windows. Lo previene el `.gitattributes`; si aparece, `dos2unix ~/MECH/pi/*.sh` |
| «no encuentro Chromium» | `sudo apt install chromium` |
| Arranca pero el panel sale viejo | En el navegador: **Ctrl+Shift+R** (recarga sin caché) |
| Arranca solo y no quiero | Doble click en `pi/autoarranque.sh` para apagarlo |
| No arranca solo aunque lo activé | El arranque automático va con la SESIÓN de escritorio: la Pi tiene que entrar al escritorio sola (sin pedir contraseña) |
| Dice que no pudo actualizar | Sin internet, o hay cambios sin guardar en la Pi. Arranca igual; para verlo: `cd ~/MECH && git status` |

## Lo que estos scripts NO hacen

- **No flashean el Arduino.** Eso sigue siendo desde la laptop.
- **No corren el chequeo previo.** Ese va aparte y con el server APAGADO:
  `python -m backend.preflight`.
- **No tocan el `.env`.** Los ajustes del evento se cambian desde el panel
  (Ajustes), en vivo.
